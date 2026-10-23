# 给 AI 的一句话安装入口

你收到的任务是安装并制作节目专属素材工坊。请先读本页，再实际执行；不要只返回安装计划。网页全程使用简体中文。此入口适用于有本地文件、终端及网络权限的 AI。

## 1. 解析用户填写的值

使用 [节目需求模板](docs/节目需求模板.md) 中的字段。至少确认：项目目录、名称、正式宽高、时长／段落、FPS、遮罩白黑／透明含义。音频可为“无”；BPM 以用户数值为准，不把音频文件存在等同于已完成节拍分析。

占位符没有填写时，先搜索已提供文件，能读到的自行确认；真实舞台尺寸或遮罩语义不明时集中询问。可先创建目录和样机，但不要把示范规格当成正式交付。

## 2. 下载并安装

从 `https://github.com/Salvatore0104/stage-asset-workshop.git` 克隆到工具缓存或工作目录。读 `skills/stage-asset-workshop/SKILL.md`、`docs/目录结构.md` 和 `docs/Wowidea.md`。

使用 Python 3.10+ 执行：

```bash
python scripts/install.py --target "【节目目录】" --name "【节目名称】" --id "【英文代号】" --width 【宽】 --height 【高】 --duration 【秒】 --mask "【遮罩PNG】" --mask-channel luminance --audio "【音频路径】" --fps 【FPS】 --bpm 【BPM】 --style "【风格】"
```

无音频／遮罩时省略对应参数；Alpha 遮罩用 `--mask-channel alpha`，反相加 `--mask-invert`。

安装器先检测本机能否运行 `wowidea`。没有则按 wowidea-cli 官方方式安装。已经安装则跳过 CLI 安装，不重复执行官方脚本，然后仍然初始化项目。两条路径结束时都打印同一段使用提示词。

- macOS / Linux：`curl -fsSL https://raw.githubusercontent.com/Salvatore0104/wowidea-cli/master/scripts/install.sh | bash`
- Windows PowerShell：`irm https://raw.githubusercontent.com/Salvatore0104/wowidea-cli/master/scripts/install.ps1 | iex`

官方脚本需要 Node.js 20.3+、npm 和 Git。尚未安装 CLI 时，还需要环境变量 `WOWIDEA_API_KEY`，或在交互终端里按脚本提示输入。密钥不要写进仓库，也不要贴进聊天。已有 `wowidea` 但希望禁止自动安装时，可加 `--skip-wowidea`；此时找不到命令会停止。Node、npm、Git 或官方脚本缺失时明确报告，不宣称安装成功。

节目目录若已有 `03_资产与需求/show.json`，跳过工坊初始化，不覆盖，然后继续检查 Wowidea 项目。Wowidea 初始化是在节目根目录执行 `wowidea project init --dir . --name "节目名称"`。已有 `.wowidea/project.json`，或命令提示项目已存在时，跳过，不覆盖。

安装器会建立项目私有 Python 环境并安装 Pillow。新节目会创建 `项目记忆.md`，记录“素材使用 Wowidea CLI 默认直接接口、不要加 --direct、不要操作无限画布、默认本地交付”，并由 AGENTS.md 和交接说明引导后续 AI 读取；已有项目保留原记忆，不整文件覆盖。创建成功后，**向用户展示实际生成的目录树和每个目录用途**，给出配置文件、工坊源代码和交付网页位置；不要只说“已初始化”。

安装成功结束时会打印一段简体中文初始化提示词。全文与 [README](README.md) 的「新建项目与对话时的初始化提示词」相同，也保存在 [docs/使用提示词.txt](docs/使用提示词.txt)。新建节目并新开 AI 对话时，把整段粘贴到新对话的第一条消息。

## 3. 填入节目资料

编辑 `03_资产与需求/show.json`：屏幕区域、遮罩、段落、拍数／秒数、文案、风格、生成提示和音频描述。详情见 [配置说明](docs/配置说明.md)。正文中的 `{{…}}` 是脚本支持的提示词变量；用户输入中的 `【…】` 是交接时需要替换的占位文字，两者用途不同。

不把参考图随意当成遮罩，不拉伸错误尺寸的遮罩。多块屏幕需要分别填坐标和尺寸；自动比例适配由每块屏的宽高计算。

## 4. 生成与构建

从节目根目录，用 `05_素材工坊/.venv` 内的 Python 运行 `05_素材工坊/scripts/workshop.py plan --project .`。检查得到的模型能力、比例及任务数。

读当前安装的 Wowidea 技能和所选模型指南，再执行 `generate`。生成使用 CLI 默认的直接接口，不要加 `--direct`，不要启动或操作无限画布。每项提交一次并保留返回 ID 和下载原件。生成前确认节目根目录已有 `.wowidea/project.json`；没有则先 `wowidea project init`，已有则不要覆盖。复用 CLI API 认证；认证不足时报告诊断，不改用网站操作。

执行 `build`，找到 `04_输出交付/<版本>/web/index.html`。打开实际结果，检查原尺寸、透明度、文本、分屏和循环。交付本地素材与任务 ID。质量不符时保留记录，不自动重复付费抽卡。

## 5. 本地验收

默认交付本地 HTML 与源码，不要求提供部署仓库。优先从构建目录启动本机服务，验证持续播放、暂停、时间轴拖动和循环；不要把文件成功生成或页面成功打开当成播放已验证。音频默认不嵌入，需要在页面选择本地音频试听。自动化环境若无法直接打开 file:，应明确记录已验证 localhost 部署的范围。

## 可选：另行要求发布时

用户要求上线且提供或授权确定 `owner/repo` 时，用 `deploy --dir 网页目录 --repo owner/repo`；或已确认输入后使用 `all --repo owner/repo`。它发布静态成品到 `gh-pages`，无需把节目源目录上传到公共仓库。

必须查看 GitHub Pages 实际构建状态并访问最终 URL，确认简体中文页面和素材可载入。账号权限不足时保留本地成品并报告具体诊断；不要把已推送描述为已上线。

最后更新 `进度.md`、`成片ID记录.md`、`00_子对话说明.md`，回复目录、网页、源代码和剩余验收事项。安装技能可能需要宿主重新发现；当前任务可以直接读取 `SKILL.md` 继续，不需等待重新发现。
