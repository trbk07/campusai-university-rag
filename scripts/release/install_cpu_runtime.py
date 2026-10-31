"""Install the frozen runtime with official CPU PyTorch wheels in the image."""
import subprocess
import tomllib
from pathlib import Path


def cpu_plan(lock):
    packages={item['name']:item['version'] for item in lock['package']}
    if 'torch' not in packages:
        raise ValueError('frozen_torch_version_required')
    omitted=sorted(name for name in packages if name.startswith('nvidia-') or name in {'triton','torch','torchvision','torchaudio'})
    wheels=[name+'=='+packages[name] for name in ('torch','torchvision','torchaudio') if name in packages]
    return omitted,wheels


def main():
    omitted,wheels=cpu_plan(tomllib.loads(Path('uv.lock').read_text(encoding='utf-8')))
    command=['uv','sync','--frozen','--extra','feasibility','--extra','ocr','--no-editable']
    for name in omitted:command+=['--no-install-package',name]
    subprocess.run(command,check=True)
    subprocess.run(['uv','pip','install','--python','.venv/bin/python','--no-deps',
        '--index-url','https://download.pytorch.org/whl/cpu',*wheels],check=True)
    subprocess.run(['uv','pip','check','--python','.venv/bin/python'],check=True)


if __name__=='__main__':main()
