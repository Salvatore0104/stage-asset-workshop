# 节目素材工坊 · Stage Asset Workshop

输入屏幕分辨率、舞台遮罩、段落时长、文案和音乐，让 AI 建立节目目录，调用 **Wowidea CLI** 的默认直接接口生成按屏幕比例适配的视觉素材，构建可本地使用的简体中文工坊。

**[在线工坊](https://salvatore0104.github.io/stage-asset-workshop/) · [一句话安装](INSTALL.md) · [目录结构](docs/目录结构.md) · [输入替换模板](docs/节目需求模板.md)**

## 直接发给其他 AI

> 请读取 https://raw.githubusercontent.com/Salvatore0104/stage-asset-workshop/main/INSTALL.md 并安装节目素材工坊：项目目录【路径】，节目【名称】，分辨率【宽×高】，遮罩【PNG路径及白黑含义】，时长【秒数或段落表】，音频【路径/无】，FPS【数值】，BPM【数值】，风格【描述】，文案【文本】。未安装 wowidea 时用官方 install.sh（Windows 为 install.ps1）安装，已安装则只初始化。show.json 或 .wowidea/project.json 已存在则跳过对应初始化，不要覆盖。生成使用默认直接接口，不要加 --direct，不要操作无限画布。构建简体中文工坊并验证本地播放，交付本地入口和源码。

把 `【…】` 换成实际信息即可。没有终端、文件或网络执行能力的聊天 AI 无法直接安装。需要 Python 3.10+。尚未安装 Wowidea CLI 时还需要 Node.js 20.3+、npm、Git，以及环境变量 `WOWIDEA_API_KEY`。在线发布另需 GitHub CLI 和发布权限。生成不要加 `--direct`；复用 CLI 当前 API 登录状态。

## 交给 AI 的使用提示词

安装结束时会打印下面同一段文字。交给后续 AI 即可。

```text
请用节目素材工坊（stage-asset-workshop）配合 wowidea-cli 制作节目素材。网页和项目说明使用简体中文。每次进入一个节目目录之前先做初始化检查：缺什么补什么，已经有的不要覆盖。

初始化检查：
1. 节目工坊：目录中要有 03_资产与需求/show.json。没有，就在素材工坊仓库运行 scripts/install.py。已有 show.json 时跳过工坊初始化，不要覆盖。
2. wowidea-cli：同一节目根目录要有 .wowidea/project.json。没有再执行 init。如果提示项目已存在，说明已经初始化过，直接继续使用，不要再次执行 init。

安装素材工坊时，安装器会先检测 wowidea 命令。未安装则按官方脚本安装：macOS / Linux 使用 wowidea-cli 的 scripts/install.sh，Windows 使用 scripts/install.ps1。已经安装则跳过安装，只初始化项目。密钥只放在环境变量 WOWIDEA_API_KEY，不要写进仓库，不要贴进聊天。

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

生成默认走直接接口。不要加 --direct，不要启动或操作无限画布，不要改走网页手工出图。

典型流程：先读 项目记忆.md、00_项目简报.md、00_子对话说明.md、项目目录说明.md 和 03_资产与需求/show.json，并确认 .wowidea/project.json 已在。按真实分辨率、遮罩、段落和风格修改 show.json。运行 plan（只出计划，不付费），核对每块屏幕的生成比例和任务数。确认后再 generate：逐项提交一次，保留任务 ID 和下载原件，再按 cover 或 contain 适配到正式像素。然后 build，打开 04_输出交付/<版本>/web/index.html。在本机用 localhost 验证持续播放、暂停、时间轴拖动和循环。默认交付本地 HTML 和源码；只有用户明确要求时才部署。比例不符、认证失败或任务状态不明时停止并报告原任务，不要自动重新付费生成。
```

## 能做什么

- 自动创建 `01_分镜` 到 `99_归档` 的编号目录和根目录交接文档。
- 正式规格统一记录在 `03_资产与需求/show.json`，支持多屏、异形 PNG 遮罩、可选 PGM。
- 按每个屏幕的比例查询所选模型能力，选择接近的生成比例；保留原件，再以等比裁切／留白适配正式尺寸。
- 按段落生成背景，文字单独排版；网页可编辑标题、副标题，上传本地音频同步试听。
- 逐层透明 PNG／序列、静态单张、舞台 matte、PGM matte、WebM 预览和输出 manifest。
- 一次命令串联生成与本地构建；另行要求时可发布静态网页，不公开 CLI 认证及原始任务记录。
- 生成任务保留 ID、缓存和精确 CLI 记录；遇到失败或比例不符停止，不自动重复付费生成。

自动生成的是可用的节目工坊起点。复杂角色动画、精确分镜、音频节拍分析、PSD 特效还原与 AE 最终验收，仍由接手 AI 按节目需求完成。当前自动生成器支持图片；视频生成另按 Wowidea 工作流处理，不把静态图适配描述为 AI 动画生成。

## 安装和制作

```bash
git clone https://github.com/Salvatore0104/stage-asset-workshop.git
cd stage-asset-workshop
python scripts/install.py --target ../我的节目 --name "我的节目" --id my_show --width 3840 --height 1080 --duration 30 --mask /path/stage.png --audio /path/music.wav --bpm 120 --style "复古游戏机与霓虹城市"
```

初始化后读取新目录中的 `项目目录说明.md`。使用新目录 `05_素材工坊/.venv` 中的 Python；Windows 为 `Scripts/python.exe`，macOS/Linux 为 `bin/python`。以下以 `python` 代表该解释器，在新项目根目录执行：

```bash
python 05_素材工坊/scripts/workshop.py plan --project .
python 05_素材工坊/scripts/workshop.py generate --project .
python 05_素材工坊/scripts/workshop.py build --project .
```

或在资料已确认、且已授权生成时：

```bash
python 05_素材工坊/scripts/workshop.py all --project .
```

`plan` 不提交付费任务。`generate` 会先确认 `.wowidea/project.json`，没有则 `wowidea project init`，已有则不覆盖，然后按 CLI 默认直接接口生成；不要加 `--direct`。`all --repo` 还会创建指定公开仓库或更新该仓库的受管 Pages 分支。不要在模板仓库的在线页面期待直接使用自己的 Wowidea 密钥：生成在本机 AI／CLI 中执行，网页只负责素材操作。

## 开发与演示构建

```bash
python -m pip install -r requirements.txt
python scripts/workshop.py build --project examples/demo --out _site
python -m http.server 8765 --bind 127.0.0.1 --directory _site
python -m unittest discover -s tests -v
```

正式项目请保留自己原始资料；公共演示不包含旧节目 PSD 或音乐。配置、用法和验证范围见 [文档入口](docs/索引.md)。
