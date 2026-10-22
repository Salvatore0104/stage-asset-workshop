"""在新节目目录准备 Python 环境，并按需安装、初始化 Wowidea CLI。"""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import workshop

INSTALL_SH = "https://raw.githubusercontent.com/Salvatore0104/wowidea-cli/master/scripts/install.sh"
INSTALL_PS1 = "https://raw.githubusercontent.com/Salvatore0104/wowidea-cli/master/scripts/install.ps1"


def official_install_command(platform=None):
    """wowidea-cli 官方安装入口。macOS/Linux 走 install.sh，Windows 走 install.ps1。"""
    if (platform or sys.platform) == "win32":
        return ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", f"irm {INSTALL_PS1} | iex"]
    return ["bash", "-c", f"curl -fsSL {INSTALL_SH} | bash"]


def require_install_tools(platform=None):
    platform = platform or sys.platform
    node = shutil.which("node")
    if not node:
        raise RuntimeError("未检测到 Node.js。安装 Wowidea CLI 需要 20.3 或更新。")
    version = subprocess.check_output([node, "--version"], text=True).strip()
    numbers = [int(part) for part in version.lstrip("v").split(".")[:2]]
    if numbers[0] < 20 or (numbers[0] == 20 and numbers[1] < 3):
        raise RuntimeError(f"当前 Node.js 是 {version}，需要 20.3 或更新。")
    npm = shutil.which("npm.cmd" if platform == "win32" else "npm") or shutil.which("npm")
    if not npm:
        raise RuntimeError("未检测到 npm。请安装随 Node.js 提供的 npm。")
    if not shutil.which("git"):
        raise RuntimeError("未检测到 Git。官方安装脚本需要 Git 克隆 wowidea-cli。")
    if platform == "win32":
        if not shutil.which("powershell") and not shutil.which("powershell.exe"):
            raise RuntimeError("未检测到 PowerShell，无法运行 wowidea-cli 的 scripts/install.ps1。")
    else:
        if not shutil.which("bash"):
            raise RuntimeError("未检测到 bash，无法运行 wowidea-cli 的 scripts/install.sh。")
        if not shutil.which("curl"):
            raise RuntimeError("未检测到 curl，无法下载 wowidea-cli 官方安装脚本。")


def ensure_wowidea_cli(skip=False, runner=subprocess.run, platform=None):
    found = workshop.find_wowidea()
    if found:
        print(f"已检测到 Wowidea CLI：{' '.join(found)}。跳过安装。")
        return found
    if skip:
        raise RuntimeError("未找到 wowidea。已指定 --skip-wowidea，不会自动安装。请先安装 wowidea-cli，或去掉该参数。")
    require_install_tools(platform)
    command = official_install_command(platform)
    print("未检测到 Wowidea CLI，正在使用官方安装脚本：" + " ".join(command))
    runner(command, check=True)
    found = workshop.find_wowidea()
    if not found:
        raise RuntimeError("官方安装脚本已结束，但当前进程仍找不到 wowidea。请新开终端后重试；macOS/Linux 常见位置是 ~/.local/bin，Windows 是用户 Path 中的 npm 全局目录。")
    print(f"Wowidea CLI 已安装：{' '.join(found)}")
    return found


def venv_python(target):
    env = Path(target) / "05_素材工坊" / ".venv"
    return env / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")


def prepare_python(target, runner=subprocess.run):
    target = Path(target)
    runtime = target / "05_素材工坊"
    runtime.mkdir(parents=True, exist_ok=True)
    env = runtime / ".venv"
    if not env.exists():
        venv.EnvBuilder(with_pip=True).create(env)
    python = venv_python(target)
    runner([str(python), "-m", "pip", "install", "-r", str(ROOT / "requirements.txt")], check=True)
    return python


def workshop_ready(target):
    return (Path(target) / "03_资产与需求" / "show.json").is_file()


def workshop_init_command(target, args, python):
    command = [str(python), str(ROOT / "scripts/workshop.py"), "init", "--project", str(target), "--name", args.name,
               "--id", args.id, "--width", str(args.width), "--height", str(args.height), "--duration", str(args.duration),
               "--fps", str(args.fps), "--bpm", str(args.bpm), "--style", args.style, "--mask-channel", args.mask_channel]
    if args.mask:
        command += ["--mask", str(Path(args.mask).resolve())]
    if args.mask_invert:
        command += ["--mask-invert"]
    if args.audio:
        command += ["--audio", str(Path(args.audio).resolve())]
    return command


def install_project(args, runner=subprocess.run):
    target = Path(args.target).resolve()
    ensure_wowidea_cli(skip=args.skip_wowidea, runner=runner)
    if workshop_ready(target):
        print(f"节目目录已初始化：{target / '03_资产与需求/show.json'}。跳过工坊 init，不会覆盖。")
        if not venv_python(target).exists():
            prepare_python(target, runner)
    else:
        python = prepare_python(target, runner)
        runner(workshop_init_command(target, args, python), check=True)
    workshop.ensure_wowidea_project(target, args.name)
    python = venv_python(target)
    print(f"安装完成。运行入口：{python} {target / '05_素材工坊/scripts/workshop.py'}")
    print("先读取根目录的项目目录说明.md。生成使用 Wowidea CLI 的默认直接接口，不要加 --direct，不要操作无限画布。")
    workshop.print_usage_prompt()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--id", default="my_show")
    parser.add_argument("--width", type=int, required=True)
    parser.add_argument("--height", type=int, required=True)
    parser.add_argument("--duration", type=float, required=True)
    parser.add_argument("--fps", type=int, default=25)
    parser.add_argument("--bpm", type=float, default=120)
    parser.add_argument("--mask", type=Path)
    parser.add_argument("--mask-channel", choices=["luminance", "alpha"], default="luminance")
    parser.add_argument("--mask-invert", action="store_true")
    parser.add_argument("--audio", type=Path)
    parser.add_argument("--style", default="根据节目主题制作适合屏幕比例的舞台视觉")
    parser.add_argument("--skip-wowidea", action="store_true", help="不运行官方安装脚本；本机必须已经能运行 wowidea")
    install_project(parser.parse_args())


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        main()
    except Exception as error:
        print(f"安装停止：{error}", file=sys.stderr)
        sys.exit(1)
