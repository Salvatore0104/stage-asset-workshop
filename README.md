# 节目素材工坊

输入屏幕分辨率、舞台遮罩、段落时长、文案和音乐，建立节目目录，用 Wowidea CLI 的默认直接接口生成按屏幕比例适配的视觉素材，并构建可在本地使用的简体中文工坊。

**[在线工坊](https://salvatore0104.github.io/stage-asset-workshop/) · [一句话安装](INSTALL.md) · [目录结构](docs/目录结构.md) · [输入替换模板](docs/节目需求模板.md)**

## 能做什么

- 自动创建 `01_分镜` 到 `99_归档` 的编号目录和根目录交接文档。
- 正式规格统一记录在 `03_资产与需求/show.json`，支持多屏、异形 PNG 遮罩、可选 PGM。
- 按每个屏幕的比例查询所选模型能力，选择接近的生成比例；保留原件，再以等比裁切或留白适配正式尺寸。
- 按段落生成背景，文字单独排版；网页可编辑标题、副标题，上传本地音频同步试听。
- 逐层透明 PNG 与序列、静态单张、舞台 matte、PGM matte、WebM 预览和输出 manifest。
- 一条命令串联生成与本地构建；另行要求时可发布静态网页，不公开 CLI 认证及原始任务记录。
- 生成任务保留 ID、缓存和精确 CLI 记录；失败或比例不符时停止，不自动重复付费生成。

自动生成的是可用的节目工坊起点。复杂角色动画、精确分镜、音频节拍分析、PSD 特效还原与 AE 最终验收，仍由接手 AI 按节目需求完成。当前自动生成器支持图片；视频生成另按 Wowidea 工作流处理，不把静态图适配描述为 AI 动画生成。

## 安装

### 环境

- Python 3.10 或更新。
- 本机还没有 `wowidea` 时，还需要 Node.js 20.3 或更新、npm 和 Git。macOS / Linux 需要 bash 与 curl，Windows 需要 PowerShell。
- 首次安装 wowidea-cli 时，把密钥放在环境变量 `WOWIDEA_API_KEY`。不要把密钥写进仓库或聊天。CLI 已经安装时，安装器不会再次索取密钥。
- 发布到 GitHub Pages 时，另需 GitHub CLI 和目标仓库权限。

### 安装节目目录

在素材工坊仓库里执行：

```bash
git clone https://github.com/Salvatore0104/stage-asset-workshop.git
cd stage-asset-workshop
python scripts/install.py --target ../我的节目 --name "我的节目" --id my_show --width 3840 --height 1080 --duration 30 --mask /path/stage.png --audio /path/music.wav --bpm 120 --style "复古游戏机与霓虹城市"
```

没有音频或遮罩时，省略 `--audio`、`--mask`。透明通道遮罩使用 `--mask-channel alpha`，黑白含义相反时加上 `--mask-invert`。

### 安装器如何检测、安装和初始化

安装器先检测本机能否运行 `wowidea`。没有检测到时，用 wowidea-cli 的官方脚本安装：

- macOS / Linux：`curl -fsSL https://raw.githubusercontent.com/Salvatore0104/wowidea-cli/master/scripts/install.sh | bash`
- Windows PowerShell：`irm https://raw.githubusercontent.com/Salvatore0104/wowidea-cli/master/scripts/install.ps1 | iex`

已经安装时，跳过 CLI 安装，不重复执行官方脚本。无论 CLI 是刚装上还是本来就有，安装器都会继续做下面的初始化，并且在结束时打印同一段「交给 AI 的使用提示词」。

1. 目标目录还没有 `03_资产与需求/show.json` 时，创建标准节目目录，并在 `05_素材工坊/.venv` 安装 Python 依赖。已经有 `show.json` 时，跳过工坊初始化，不覆盖现有目录和配置。
2. 节目根目录还没有 `.wowidea/project.json` 时，执行 `wowidea project init --dir <节目目录> --name "<节目名称>"`。该文件已存在，或 init 提示项目已存在时，跳过，不覆盖。
3. 安装结束时打印使用提示词。已安装 CLI 的路径和全新安装的路径打印的是同一段文字。

本机已有 `wowidea`、且不希望在缺失时自动安装，可以加上 `--skip-wowidea`。此时找不到命令会停止，不会改写项目。

安装完成后，先读节目根目录的 `项目目录说明.md`。配置在 `03_资产与需求/show.json`，工坊源码在 `05_素材工坊/`，交付网页在 `04_输出交付/<版本>/web/index.html`。

## 使用

在节目根目录执行。Python 使用 `05_素材工坊/.venv`：Windows 为 `Scripts\python.exe`，macOS / Linux 为 `bin/python`。下面的 `python` 指这个解释器。

```bash
python 05_素材工坊/scripts/workshop.py plan --project .
python 05_素材工坊/scripts/workshop.py generate --project .
python 05_素材工坊/scripts/workshop.py build --project .
```

资料已经确认，并且同意生成时，可以一次完成生成和构建：

```bash
python 05_素材工坊/scripts/workshop.py all --project .
```

- `plan` 查询模型能力并写出生成计划，不提交付费任务。
- `generate` 先确认节目根目录已有 `.wowidea/project.json`。没有则执行 `wowidea project init`，已有则不覆盖。随后用 Wowidea CLI 的默认直接接口逐项生成图片，保留任务 ID 和下载原件，再按 `cover` 或 `contain` 适配到正式像素。
- `build` 写出 `04_输出交付/<版本>/web/index.html`。在本机打开后，检查持续播放、暂停、时间轴和循环。音频默认不嵌入，可在页面选择本地文件试听。
- `all --repo owner/name` 在构建之后，把静态网页发布到该仓库的 `gh-pages`。未提供 `--repo` 时只做本地构建。

生成在本机的 Wowidea CLI 中执行。在线示例页不能使用你的密钥。比例不符、认证失败或任务状态不明时停止，保留原任务，不自动重新付费生成。

本地预览：

```bash
python -m http.server 8765 --bind 127.0.0.1 --directory "04_输出交付/<版本>/web"
```

## 交给 AI 的使用提示词

安装结束时会打印下面同一段文字，源文件是 [docs/使用提示词.txt](docs/使用提示词.txt)。交给后续 AI 即可。

```text
请用节目素材工坊（stage-asset-workshop）配合 wowidea-cli 制作节目素材。网页和项目说明使用简体中文。每次进入一个节目目录之前先做初始化检查：缺什么补什么，已经有的不要覆盖。

初始化检查：
1. 节目工坊：目录中要有 03_资产与需求/show.json。没有，就在素材工坊仓库运行 scripts/install.py。已有 show.json 时跳过工坊初始化，不要覆盖。
2. wowidea-cli：同一节目根目录要有 .wowidea/project.json。没有再执行 init。如果提示项目已存在，说明已经初始化过，直接继续使用，不要再次执行 init。

安装素材工坊时，安装器会先检测 wowidea 命令。未安装则按官方脚本安装：macOS / Linux 使用 wowidea-cli 的 scripts/install.sh，Windows 使用 scripts/install.ps1。已经安装则跳过 CLI 安装，仍然初始化：没有 .wowidea/project.json 就执行 wowidea project init，已有则跳过且不覆盖。两条路径结束时都打印这段提示词。密钥只放在环境变量 WOWIDEA_API_KEY，不要写进仓库，不要贴进聊天。

wowidea 初始化（在节目根目录执行，把名称换成实际节目名）：
wowidea project init --dir . --name "节目名称"

素材工坊命令（在节目根目录执行。Python 用 05_素材工坊/.venv：Windows 为 Scripts\python.exe，macOS / Linux 为 bin/python）：
python 05_素材工坊/scripts/workshop.py plan --project .
python 05_素材工坊/scripts/workshop.py generate --project .
python 05_素材工坊/scripts/workshop.py build --project .

wowidea-cli 常用命令：
wowidea capabilities --brief
wowidea doctor --json
wowidea models show "Nano Banana 2" --json
wowidea project show --dir .
wowidea image generate --file 请求.json --project-dir . --dir 07_AE资产素材/生成原件 --json

生成使用 wowidea-cli 的默认直接接口。读取返回中的任务 ID 和已下载文件。

典型流程：先读 项目记忆.md、00_项目简报.md、00_子对话说明.md、项目目录说明.md 和 03_资产与需求/show.json，并确认 .wowidea/project.json 已在。按真实分辨率、遮罩、段落和风格修改 show.json。运行 plan（只出计划，不付费），核对每块屏幕的生成比例和任务数。确认后再 generate：逐项提交一次，保留任务 ID 和下载原件，再按 cover 或 contain 适配到正式像素。然后 build，打开 04_输出交付/<版本>/web/index.html。在本机用 localhost 验证持续播放、暂停、时间轴拖动和循环。默认交付本地 HTML 和源码；只有用户明确要求时才部署。比例不符、认证失败或任务状态不明时停止并报告原任务，不要自动重新付费生成。
```

## 开发与演示构建

```bash
python -m pip install -r requirements.txt
python scripts/workshop.py build --project examples/demo --out _site
python -m http.server 8765 --bind 127.0.0.1 --directory _site
python -m unittest discover -s tests -v
```

正式项目请保留自己的原始资料。公共演示不包含旧节目 PSD 或音乐。配置、用法和验证范围见 [文档入口](docs/索引.md)。
