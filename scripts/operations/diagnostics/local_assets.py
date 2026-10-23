"""Pin public vendor assets for optional local inference; no execution/upload."""
import argparse
import json
from pathlib import Path
from urllib.request import Request, urlopen


def read(url):
    with urlopen(Request(url,headers={'User-Agent':'CampusAI-public-asset-audit'}),timeout=30) as response:
        return json.load(response)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--engine-metadata',type=Path)
    args=parser.parse_args()
    if args.output.exists():
        parser.error('Asset manifest exists; do not overwrite')
    if args.engine_metadata:
        engine=json.loads(args.engine_metadata.read_text(encoding='utf-8'))
        assert engine['repo']=='ggml-org/llama.cpp'
    else:
        releases=read('https://api.github.com/repos/ggml-org/llama.cpp/releases?per_page=5')
        release=next(item for item in releases if any('win-cuda-12.4-x64.zip' in a['name'] for a in item['assets']))
        engine={'repo':'ggml-org/llama.cpp','tag':release['tag_name'],
                'assets':[{key:asset.get(key) for key in ('name','size','digest','browser_download_url')}
                          for asset in release['assets'] if 'win-cuda-12.4-x64.zip' in asset['name']]}
    model=read('https://huggingface.co/api/models/Qwen/Qwen3-8B-GGUF?blobs=true')
    weights=[{'filename':item['rfilename'],'size':item.get('size'),'lfs':item.get('lfs')}
             for item in model['siblings'] if 'q4_k_m' in item['rfilename'].lower() and item['rfilename'].endswith('.gguf')]
    report={'date':'2026-10-15','scope':'Optional local candidate inputs, no activation or inference',
            'engine':engine,
            'model':{'repo':'Qwen/Qwen3-8B-GGUF','revision':model['sha'],'license':model.get('cardData',{}).get('license'),'weights':weights},
            'downloads_executed':False,'software_executed':False,'live_provider_calls':0}
    assert engine['assets'] and weights and report['model']['license']=='apache-2.0'
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
