# Stage Asset Workshop

这是通用工具仓库，节目源数据应放到独立节目目录；公共 examples 只放允许公开的演示素材。
网页、项目文档和目录名使用简体中文。优先读取 INSTALL.md 和 docs/索引.md。
show.json 为节目唯一输入规格；生成时使用实时 Wowidea 模型能力与 CLI direct 模式，不绕过 CLI 直接调用供应商。
改动后运行 `python -m unittest discover -s tests -v`，并在需要时实际检查浏览器。不得把模拟生成测试当成真实 Wowidea 成果。
