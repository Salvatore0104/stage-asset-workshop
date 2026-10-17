"""在新节目目录安装运行环境、Wowidea CLI 和项目结构。"""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys
import venv

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--target',type=Path,required=True)
    p.add_argument('--name',required=True);p.add_argument('--id',default='my_show')
    p.add_argument('--width',type=int,required=True);p.add_argument('--height',type=int,required=True)
    p.add_argument('--duration',type=float,required=True);p.add_argument('--fps',type=int,default=25);p.add_argument('--bpm',type=float,default=120)
    p.add_argument('--mask',type=Path);p.add_argument('--mask-channel',choices=['luminance','alpha'],default='luminance')
    p.add_argument('--mask-invert',action='store_true');p.add_argument('--audio',type=Path)
    p.add_argument('--style',default='根据节目主题制作适合屏幕比例的舞台视觉')
    p.add_argument('--skip-wowidea',action='store_true',help='已安装兼容 CLI 时，复用现有安装')
    a=p.parse_args();target=a.target.resolve()
    if (target/'03_资产与需求/show.json').exists():raise FileExistsError('目标已初始化，不会覆盖；直接使用现有项目。')
    runtime=target/'05_素材工坊';runtime.mkdir(parents=True,exist_ok=True)
    env=runtime/'.venv'
    if not env.exists():venv.EnvBuilder(with_pip=True).create(env)
    python=env/('Scripts/python.exe' if sys.platform=='win32' else 'bin/python')
    subprocess.run([str(python),'-m','pip','install','-r',str(ROOT/'requirements.txt')],check=True)
    if not a.skip_wowidea:
        npm=shutil.which('npm.cmd' if sys.platform=='win32' else 'npm')
        if not npm:raise RuntimeError('需要 Node.js 20+ 与 npm 来安装 Wowidea CLI。')
        version=subprocess.check_output([shutil.which('node'),'--version'],text=True).strip()
        if int(version.lstrip('v').split('.')[0])<20:raise RuntimeError('Node.js 版本需要 20 或以上。')
        subprocess.run([npm,'install','--prefix',str(runtime/'.tools/wowidea'),'@easyai/cli@0.8.0'],check=True)
    command=[str(python),str(ROOT/'scripts/workshop.py'),'init','--project',str(target),'--name',a.name,'--id',a.id,
             '--width',str(a.width),'--height',str(a.height),'--duration',str(a.duration),'--fps',str(a.fps),'--bpm',str(a.bpm),'--style',a.style,'--mask-channel',a.mask_channel]
    if a.mask:command+=['--mask',str(a.mask.resolve())]
    if a.mask_invert:command+=['--mask-invert']
    if a.audio:command+=['--audio',str(a.audio.resolve())]
    subprocess.run(command,check=True)
    print(f'安装完成。运行入口：{python} {runtime / "scripts/workshop.py"}\n先读取根目录的项目目录说明.md。生成使用 Wowidea CLI --direct，复用 CLI 的 API 登录状态；无需 Canvas 授权。')


if __name__=='__main__':
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
    try:main()
    except Exception as error:
        print(f'安装停止：{error}',file=sys.stderr);sys.exit(1)
