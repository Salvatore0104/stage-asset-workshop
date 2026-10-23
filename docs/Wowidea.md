# Wowidea 集成与生成约定

工具调用本机已安装的 Wowidea CLI 生成图片。生成走 CLI 默认的直接接口，不要加 `--direct`，不要启动或操作无限画布。复用 CLI 保存的 API 认证，不保存用户 API Key 到项目、不在网页调用生成接口，也不直接调用第三方模型供应商。

未安装 `wowidea` 时，素材工坊安装器使用 wowidea-cli 官方脚本：macOS / Linux 为 [scripts/install.sh](https://github.com/Salvatore0104/wowidea-cli/blob/master/scripts/install.sh)，Windows 为 [scripts/install.ps1](https://github.com/Salvatore0104/wowidea-cli/blob/master/scripts/install.ps1)。已经能运行 `wowidea` 则跳过安装。官方脚本把仓库放在 `~/.wowidea-cli`（Windows 为 `%USERPROFILE%\.wowidea-cli`），可用环境变量 `WOWIDEA_CLI_REF` 指定修订。密钥只放在 `WOWIDEA_API_KEY`。

## 运行方式

1. 节目根目录必须已有 `.wowidea/project.json`。没有则执行 `wowidea project init --dir . --name "节目名称"`。文件已存在，或 init 提示项目已存在时，跳过，不要覆盖。
2. `plan` 调用 `models show <model> --json`，读取当前模型比例和分辨率。
3. 按每块屏幕选择使 `abs(log(生成比例/目标比例))` 最小的支持比例。
4. 提示词写明屏幕、正式尺寸、生成比例、风格、段落和音频摘要。请求采用 `model / prompt / aspect_ratio / resolution / n=1`；本地参考路径使用 `image_urls`，由 CLI 上传并绑定。
5. 每项使用 UTF-8 请求文件，通过 `image generate --file 请求.json --project-dir 节目根目录` 提交一次。不要加 `--direct`，也不要混用 `--file` 和 prompt/model 等直接生成参数。
6. 检查返回 `outputSpec` 及下载原图的实际宽高；API 标记 mismatch 或对数比例误差超过 3.5% 时停止，保留原任务。容差处理模型像素取整，不代表承诺原生精确舞台像素。
7. 以 `cover` 裁边或 `contain` 留透明边适配正式屏幕像素，PNG 原件及适配件分别保存。舞台画面最终根据真实遮罩裁切。

当比例差距太大或关键主体可能被裁掉，应改为分屏构图、明确调整视觉方案或使用接近比例的兼容模型；不能通过非等比拉伸宣称原生符合舞台尺寸。默认只生成背景，网页标题独立排版。

## 登录与恢复

本工具只需要 CLI API 认证。已有 `wowidea doctor --json` 可用的 API 登录可直接复用；新用户按 CLI 支持的安全方式初始化认证。不把凭证写入项目文件或让用户粘贴到聊天。

生成之前先读环境中可用的 Wowidea 技能；官方安装目录里也有 `skill/wowidea/SKILL.md` 和模型提示词指南。保持 CLI 默认的直接接口，不要为了画布改路由。

每个任务在提交前创建状态记录。已有 complete 记录和适配文件则复用；其他状态阻止重新提交。网络中断不表示服务端没收单；请从节目根目录 `.wowidea/runs` 和生成记录恢复原任务。工具不自动重试、重新抽卡、换模型或生成修补帧。

从结果记录读取 Task ID、下载文件和价格；费用未知写“接口未提供”，不要写零。最终回复给出素材、任务与节目网页位置。

## 当前范围

自动生成器支持静态图片，不承诺音频分析、自动分镜、AI 视频、PSD 精确拆层动画或动态 PGM。视频／角色多姿势／循环动画可由接手 AI 根据实际 Wowidea 视频技能另做，再接入 `src/scenes.js`；保留任务记录、逐帧检查，并以最终舞台和 AE 重新验收。
