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

已经安装时，跳过 CLI 安装，不重复执行官方脚本。无论 CLI 是刚装上还是本来就有，安装器都会继续做下面的初始化，并且在结束时打印首次安装话术。

1. 目标目录还没有 `03_资产与需求/show.json` 时，创建标准节目目录，并在 `05_素材工坊/.venv` 安装 Python 依赖。已经有 `show.json` 时，跳过工坊初始化，不覆盖现有目录和配置。
2. 节目根目录还没有 `.wowidea/project.json` 时，执行 `wowidea project init --dir <节目目录> --name "<节目名称>"`。该文件已存在，或 init 提示项目已存在时，跳过，不覆盖。
3. 安装成功结束时打印首次安装话术。新建节目、新开 AI 对话时，把 [docs/prompts/首次安装.txt](docs/prompts/首次安装.txt) 整段粘贴进新对话。

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

## 话术提示词

- [首次安装](docs/prompts/首次安装.txt)：工坊刚装好，新建节目并新开 AI 对话时粘贴。
- [更新](docs/prompts/更新.txt)：更新已有工坊或已有节目时粘贴。
- [部署](docs/prompts/部署.txt)：要发布节目网页时粘贴。

## 开发与演示构建

```bash
python -m pip install -r requirements.txt
python scripts/workshop.py build --project examples/demo --out _site
python -m http.server 8765 --bind 127.0.0.1 --directory _site
python -m unittest discover -s tests -v
```

正式项目请保留自己的原始资料。公共演示不包含旧节目 PSD 或音乐。配置、用法和验证范围见 [文档入口](docs/索引.md)。
