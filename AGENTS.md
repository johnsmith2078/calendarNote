# Repository Guidelines

## Project Structure & Module Organization
- 当前项目已经演进为 **PyQt6 + Qt Quick/QML** 架构，不再是传统的 QWidget 多窗口实现。
- `main.py` 是唯一 Python 入口，主要包含：
  - `DiaryBackend`：通过 `@pyqtProperty`、`@pyqtSlot`、Qt signal 向 QML 暴露状态；负责日期切换、自动保存、跨日检测、文件读写、旧版数据迁移、全文搜索、搜索预览高亮、月度缓存、主题模式持久化与切换等核心逻辑。
  - `SearchResultItem` / `SearchResultModel`：为 QML `ListView` 提供搜索结果数据模型。
  - `main()`：初始化 `QApplication`、设置 Qt Quick Controls 样式、加载图标，并启动 `QQmlApplicationEngine` 加载 `qml/Main.qml`。
- `qml/Main.qml` 是主界面，包含响应式双栏/单栏布局、日历侧栏、纯文本编辑区、全文搜索结果弹窗、页面内搜索弹窗、浅色/深色主题 token，以及 `AppButton` / `AppTextField` / `AppCheckBox` 等局部复用组件。
- 日记文件使用 UTF-8 纯文本，存储在 `diary_entries/YYYY/MM/YYYY-MM-DD.txt`；访问某天数据时会按需兼容旧的扁平结构 `diary_entries/YYYY-MM-DD.txt`。
- 构建与资源脚本：
  - `build_with_nuitka.py`：使用 Nuitka 打包，需一并包含 `qml/` 与 `icon.ico`。
  - `compile_resources.py`：将 `resources.qrc` 编译为 `resources_rc.py`（仅在确实使用 Qt 资源嵌入时需要）。
- 根目录资源包含 `icon.ico`、`icon.svg`、`cover.png`、`resources.qrc`；`dist/`、`resources_rc.py`、`diary_entries/` 属于生成物或个人数据，除非明确需要，否则不要提交。
- 如果架构、运行方式或 UI 行为发生变化，请同步更新 `README.md`、`AGENTS.md`、`CLAUDE.md` 中的相关说明，避免文档失真。

## Build, Test, and Development Commands
- 安装依赖（Python 3.12+）：`uv sync`（优先）或 `pip install -e .`
- 本地运行：`python main.py`
- Python 语法快速检查：`python -m py_compile main.py build_with_nuitka.py compile_resources.py`
- 修改 `resources.qrc` 或其引用资源后重建：`python compile_resources.py`
- Windows 打包：`python build_with_nuitka.py`
- 涉及 QML 资源加载、运行时路径或图标加载逻辑时，除源码运行外，也应验证打包产物是否仍能找到 `qml/Main.qml` 与 `icon.ico`。

## Coding Style & Naming Conventions
- 遵循 PEP 8，使用 4 空格缩进；导入顺序保持为标准库 → 第三方 → 本地模块。
- 保留并补充类型标注；轻量数据结构优先沿用 `dataclass(slots=True)` 风格。
- Python 侧使用 snake_case，Qt/QML 类型、组件与类名使用 PascalCase。
- `main.py` 顶部的常量（标题、搜索上限、预览大小、日期文案等）应集中维护，避免把魔法数字散落到后端或 QML 中。
- 新增 QML 可见状态时，保持“字段 + signal + property/slot + 按需 emit”成套更新；只有值真正变化时才发信号，避免无效刷新。
- 修改后端暴露给 QML 的属性名、槽函数名或信号名时，必须同步检查 `qml/Main.qml` 的绑定、`Connections`、按钮事件和弹窗逻辑。
- 修改 `qml/Main.qml` 时：
  - 优先复用已有的 `AppButton`、`AppTextField`、`AppCheckBox`，保持视觉一致性；
  - 保持调色板、间距、响应式阈值等全局 token 集中在文件顶部；如果同时维护浅色/深色两套 token，尽量成对对齐，避免只改单侧主题；
  - 保留 `backendSafe` / `backendStub` 容错结构，避免界面在后端未注入时直接崩溃；
  - 优先使用声明式绑定，只有在弹窗拖动、页面内查找遍历、月份同步这类交互胶水场景下再写 JS 逻辑。
- 用户可见文案、状态提示和注释优先使用简体中文，与现有界面语气保持一致。

## Performance & Data Safety Notes
- 全文搜索有明确保护阈值：结果数量、可搜索文件大小、预览大小、单条内容长度都在 `main.py` 常量中限制；调整这些值时要说明原因，并关注 UI 响应性。
- `save_entry_for_date()` 默认不会为空白内容创建新文件；如果要改动该策略，需明确评估对日历圆点显示、历史文件兼容和搜索结果的影响。
- 月份高亮依赖 `_month_entry_cache` 与 `calendarVersion`；涉及保存、迁移、目录扫描或日历刷新逻辑时，注意同步失效缓存与刷新信号。
- `_collect_all_diary_files()` 会在新旧路径并存时做去重并优先保留层级更深的新结构文件；修改存储结构时不要破坏这层兼容性。
- 打包运行时依赖 `resolve_runtime_path()` 和 `load_application_icon()` 查找资源；变更目录布局时请同时验证源码运行与打包运行两种场景。

## Testing Guidelines
- 目前没有自动化测试；提交前请至少完成针对改动范围的手动验证，并在结果说明里写清楚“做了什么 / 没做什么”。
- 基础冒烟：
  - 运行 `python main.py`；
  - 确认主窗口能正常加载，顶部标题、底部状态栏、当前日期和“今天”按钮文本正确；
  - 确认默认以深色模式启动，并且主题切换按钮可以在浅色 / 深色之间往返切换；
  - 宽窗口下应为左右双栏，窄窗口下应自动切换为纵向布局。
- 编辑与保存：
  - 新建或修改今天的日记，确认落盘路径为 `diary_entries/YYYY/MM/YYYY-MM-DD.txt`；
  - 验证 `Ctrl+S`、自动保存状态、未保存标记、底部状态消息是否符合预期；
  - 验证 `Ctrl+Shift+A` 可以切换自动保存开关。
- 日期切换与生命周期：
  - 在有未保存内容时切换日期，确认 Save / Discard / Cancel 分支行为正确；
  - 关闭窗口时验证未保存确认逻辑；
  - 如果改到跨日检测逻辑，需确认系统日期变化后“今天”按钮、当前日期和高亮状态会刷新，必要时自动切换到新的一天。
- 搜索相关：
  - 全局搜索应能展示结果数量、上下文摘要、右侧富文本高亮预览，并支持跳转到选中日期；
  - 页面内搜索应验证 `Ctrl+F`、F3、`Shift+F3`、`Escape`、区分大小写、结果计数、选择高亮与弹窗拖动功能。
- 日历与缓存：
  - 切换月份后，已有内容的日期应显示圆点；
  - 验证 `returnToToday()` 在“已经位于今天”时也会刷新当前月份缓存和高亮；
  - 如果改动存储/迁移逻辑，请同时验证新目录结构与旧扁平文件结构的兼容行为。
- 构建验证：
  - 变更 `build_with_nuitka.py`、QML 加载方式、图标/资源路径时，尽量运行 `python build_with_nuitka.py`；
  - 若未执行打包验证，请在提交说明中明确标注。

## Commit & Pull Request Guidelines
- 当前提交历史以简短、动作导向的中文摘要为主，通常可带 scope，如：`feat(qml): ...`、`fix(gui): ...`、`feat(build): ...`。保持单个提交聚焦一个主题，不要把无关修改混在一起。
- PR 说明建议至少包含：
  - 变更目的；
  - 影响范围（如 `main.py`、`qml/Main.qml`、打包脚本、存储逻辑等）；
  - 关键行为变化；
  - 本地手动验证步骤与结果；
  - 对 UI 可见改动附带截图或 GIF。
- 修改日记存储格式、迁移策略、搜索限制、打包方式时，要在 PR 中明确说明兼容性影响和迁移注意事项。
- 除非明确要求，不要提交个人日记内容、`dist/` 下的二进制产物、缓存文件或其他机器相关生成物。
