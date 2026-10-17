# 节目素材工坊 · Stage Asset Workshop

输入屏幕分辨率、舞台遮罩、段落时长、文案和音乐，让 AI 建立节目目录，调用 **Wowidea CLI direct** 生成按屏幕比例适配的视觉素材，构建可本地使用的简体中文工坊。

**[在线工坊](https://salvatore0104.github.io/stage-asset-workshop/) · [一句话安装](INSTALL.md) · [目录结构](docs/目录结构.md) · [输入替换模板](docs/节目需求模板.md)**

## 直接发给其他 AI

> 请读取 https://raw.githubusercontent.com/Salvatore0104/stage-asset-workshop/main/INSTALL.md 并安装节目素材工坊：项目目录【路径】，节目【名称】，分辨率【宽×高】，遮罩【PNG路径及白黑含义】，时长【秒数或段落表】，音频【路径/无】，FPS【数值】，BPM【数值】，风格【描述】，文案【文本】。初始化标准目录，将“本项目素材使用 Wowidea CLI --direct 生成，不使用 Canvas，默认本地交付”写入项目记忆和 AI 交接说明；生成适配素材、构建简体中文工坊并验证本地播放，交付本地入口和源码。

把 `【…】` 换成实际信息即可。没有终端、文件或网络执行能力的聊天 AI 无法直接安装。需要 Python 3.10+、Node.js 20.3+ 和 Git；在线发布另需 GitHub CLI 和发布权限。生成使用 `--direct`，不使用 Canvas；复用 CLI 当前 API 登录状态，新用户需完成一次 CLI API 认证。

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

`plan` 不提交付费任务。`generate/all` 会使用当前 Wowidea 账号生成；`all --repo` 还会创建指定公开仓库或更新该仓库的受管 Pages 分支。不要在模板仓库的在线页面期待直接使用自己的 Wowidea 密钥：生成在本机 AI／CLI 中执行，网页只负责素材操作。

## 开发与演示构建

```bash
python -m pip install -r requirements.txt
python scripts/workshop.py build --project examples/demo --out _site
python -m http.server 8765 --bind 127.0.0.1 --directory _site
python -m unittest discover -s tests -v
```

正式项目请保留自己原始资料；公共演示不包含旧节目 PSD 或音乐。配置、用法和验证范围见 [文档入口](docs/索引.md)。
