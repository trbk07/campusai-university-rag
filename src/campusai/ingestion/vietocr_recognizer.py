"""Inference-only adapter for the pinned VietOCR VGG/Seq2Seq checkpoint.

Adapted from pbcquoc/vietocr 0.3.13 (Apache-2.0); see vietocr.LICENSE.
Retains checkpoint names and math, without the training package's conflicting
Pillow pins, training dependencies, downloads or unused ImageNet classifier.
Imported only inside the explicitly selected local OCR worker.
"""
import math
import time

import numpy as np
from PIL import Image
import torch
from torch import nn

VOCAB = 'aAàÀảẢãÃáÁạẠăĂằẰẳẲẵẴắẮặẶâÂầẦẩẨẫẪấẤậẬbBcCdDđĐeEèÈẻẺẽẼéÉẹẸêÊềỀểỂễỄếẾệỆfFgGhHiIìÌỉỈĩĨíÍịỊjJkKlLmMnNoOòÒỏỎõÕóÓọỌôÔồỒổỔỗỖốỐộỘơƠờỜởỞỡỠớỚợỢpPqQrRsStTuUùÙủỦũŨúÚụỤưƯừỪửỬữỮứỨựỰvVwWxXyYỳỲỷỶỹỸýÝỵỴzZ0123456789!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~ '


class Backbone(nn.Module):
    def __init__(self):
        super().__init__()
        layers, channels, pool = [], 3, 0
        for width in [64,64,0,128,128,0,256,256,256,256,0,512,512,512,512,0,512,512,512,512,0]:
            if width:
                layers += [nn.Conv2d(channels,width,3,padding=1),nn.BatchNorm2d(width),nn.ReLU(inplace=True)]
                channels = width
            else:
                shape = [(2,2),(2,2),(2,1),(2,1),(1,1)][pool]
                layers.append(nn.AvgPool2d(shape,stride=shape)); pool += 1
        self.features = nn.Sequential(*layers)
        self.last_conv_1x1 = nn.Conv2d(512,256,1)

    def forward(self, image):
        value = self.last_conv_1x1(self.features(image))
        return value.transpose(-1,-2).flatten(2).permute(-1,0,1)


class Encoder(nn.Module):
    def __init__(self):
        super().__init__()
        self.rnn = nn.GRU(256,256,bidirectional=True)
        self.fc = nn.Linear(512,256)

    def forward(self, value):
        output, hidden = self.rnn(value)
        return output, torch.tanh(self.fc(torch.cat((hidden[-2],hidden[-1]),dim=1)))


class Attention(nn.Module):
    def __init__(self):
        super().__init__()
        self.attn = nn.Linear(768,256)
        self.v = nn.Linear(256,1,bias=False)

    def forward(self, hidden, encoded):
        hidden = hidden.unsqueeze(1).repeat(1,encoded.shape[0],1)
        energy = torch.tanh(self.attn(torch.cat((hidden,encoded.permute(1,0,2)),dim=2)))
        return self.v(energy).squeeze(2).softmax(dim=1)


class Decoder(nn.Module):
    def __init__(self, size):
        super().__init__()
        self.attention = Attention()
        self.embedding = nn.Embedding(size,256)
        self.rnn = nn.GRU(768,256)
        self.fc_out = nn.Linear(1024,size)

    def forward(self, token, hidden, encoded):
        embedded = self.embedding(token).unsqueeze(0)
        weights = self.attention(hidden,encoded).unsqueeze(1)
        weighted = torch.bmm(weights,encoded.permute(1,0,2)).permute(1,0,2)
        output, hidden = self.rnn(torch.cat((embedded,weighted),dim=2),hidden.unsqueeze(0))
        logits = self.fc_out(torch.cat((output.squeeze(0),weighted.squeeze(0),embedded.squeeze(0)),dim=1))
        return logits, hidden.squeeze(0)


class Model(nn.Module):
    def __init__(self):
        super().__init__()
        self.cnn = nn.Module(); self.cnn.model = Backbone()
        self.transformer = nn.Module()
        self.transformer.encoder = Encoder()
        self.transformer.decoder = Decoder(len(VOCAB)+4)


def prepare(image):
    if not isinstance(image,Image.Image) or min(image.size)<1:
        raise ValueError('invalid OCR crop')
    width = min(512,max(32,math.ceil(int(32*image.width/image.height)/10)*10))
    image = image.convert('RGB').resize((width,32),Image.Resampling.LANCZOS)
    return torch.from_numpy((np.asarray(image).transpose(2,0,1)/255).astype(np.float32)).unsqueeze(0)


class Recognizer:
    def __init__(self, weights, *, device=None):
        self.device = device or ('cuda:0' if torch.cuda.is_available() else 'cpu')
        # Checkpoint identity is validated before this constructor by the worker.
        self.model = Model()
        self.model.load_state_dict(torch.load(weights,map_location='cpu',weights_only=True),strict=True)
        self.model.to(self.device).eval()

    def predict(self, images, *, deadline=None, batch_size=8):
        if type(batch_size) is not int or not 1<=batch_size<=16 or len(images)>4096:
            raise ValueError('OCR batch/crop bound exceeded')
        buckets, result = {}, [('',0.) for _ in images]
        for index,image in enumerate(images):
            tensor = prepare(image)
            buckets.setdefault(tensor.shape[-1],[]).append((index,tensor))
        with torch.inference_mode():
            for group in buckets.values():
                for start in range(0,len(group),batch_size):
                    if deadline is not None and time.monotonic()>deadline:
                        raise TimeoutError('OCR recognition deadline')
                    part = group[start:start+batch_size]
                    batch = torch.cat([value for _,value in part]).to(self.device)
                    encoded, hidden = self.model.transformer.encoder(self.model.cnn.model(batch))
                    token = torch.ones(len(part),dtype=torch.long,device=self.device)
                    tokens, probabilities, finished = [], [], [False]*len(part)
                    for _ in range(129):
                        if deadline is not None and time.monotonic()>deadline:
                            raise TimeoutError('OCR recognition deadline')
                        logits, hidden = self.model.transformer.decoder(token,hidden,encoded)
                        score, token = logits.softmax(dim=-1).max(dim=-1)
                        values = token.tolist(); tokens.append(values); probabilities.append(score.tolist())
                        finished = [done or value==2 for done,value in zip(finished,values)]
                        if all(finished): break
                    for column,(index,_) in enumerate(part):
                        ids = [row[column] for row in tokens]
                        if 2 not in ids: continue  # Truncated output is never valid text.
                        end = ids.index(2); ids = ids[:end]
                        if not ids or any(value<4 or value>=len(VOCAB)+4 for value in ids): continue
                        text = ''.join(VOCAB[value-4] for value in ids)
                        confidence = sum(row[column] for row in probabilities[:end])/len(ids)
                        result[index] = (text,float(confidence))
        return result
