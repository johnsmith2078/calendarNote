import sys
import os
import time  # 添加时间模块用于性能监控
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout,
    QCalendarWidget, QTextEdit, QMessageBox, QPushButton, QVBoxLayout, QSizePolicy,
    QLineEdit, QListWidget, QListWidgetItem, QDialog, QLabel, QGridLayout,
    QCheckBox
)
from PyQt6.QtCore import QDate, Qt, QDir, QResource, QDirIterator, QTimer
from PyQt6.QtGui import QCloseEvent, QFont, QIcon, QTextCharFormat, QColor, QTextDocument, QKeySequence, QAction, QShortcut

class PlainTextEdit(QTextEdit):
    """
    自定义的文本编辑器，强制纯文本粘贴，忽略所有格式
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        # 设置为纯文本模式，但仍然允许一些基本的文本操作
        self.setAcceptRichText(False)

    def insertFromMimeData(self, source):
        """
        重写粘贴方法，只粘贴纯文本内容，忽略所有格式
        """
        if source.hasText():
            # 获取纯文本内容
            plain_text = source.text()
            # 插入纯文本，忽略任何格式
            self.insertPlainText(plain_text)
        else:
            # 如果没有文本内容，调用父类方法
            super().insertFromMimeData(source)

    def keyPressEvent(self, event):
        """
        处理键盘事件，确保Ctrl+V也使用纯文本粘贴
        """
        if event.matches(QKeySequence.StandardKey.Paste):
            # 使用系统剪贴板进行纯文本粘贴
            clipboard = QApplication.clipboard()
            mime_data = clipboard.mimeData()
            if mime_data.hasText():
                self.insertPlainText(mime_data.text())
                return

        # 对于其他按键，调用父类方法
        super().keyPressEvent(event)

class SearchResultItem:
    """表示搜索结果中的一个条目"""
    def __init__(self, date: QDate, content: str, match_text: str):
        self.date = date
        self.content = content
        self.match_text = match_text
        
    def __str__(self):
        """返回用于显示的字符串表示"""
        date_str = self.date.toString('yyyy-MM-dd')
        if self.match_text:
            # 截断过长的匹配文本
            display_text = self.match_text
            if len(display_text) > 60:
                display_text = display_text[:57] + "..."
            return f"{date_str}: {display_text}"
        else:
            return date_str

class SearchDialog(QDialog):
    """搜索结果对话框"""
    def __init__(self, parent=None, results=None, keyword=None):
        super().__init__(parent)
        self.setWindowTitle("搜索结果")
        self.setGeometry(300, 300, 600, 400)
        self.selected_date = None
        self.keyword = keyword  # 保存搜索关键词以便高亮
        self.initUI()
        
        if results:
            self.display_results(results)
    
    def initUI(self):
        layout = QVBoxLayout(self)
        
        # 搜索结果数量标签
        self.result_count_label = QLabel("找到 0 个结果", self)
        layout.addWidget(self.result_count_label)
        
        # 搜索结果列表
        self.result_list = QListWidget(self)
        self.result_list.setWordWrap(True)  # 允许文本换行
        self.result_list.setTextElideMode(Qt.TextElideMode.ElideMiddle)  # 太长时在中间显示省略号
        # 允许列表项显示 HTML 富文本
        self.result_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)  # 禁用水平滚动条
        self.result_list.itemDoubleClicked.connect(self.item_double_clicked)
        # 设置等宽字体
        monospace_font = QFont("Consolas", 10)
        if not monospace_font.exactMatch():
            monospace_font = QFont()
            monospace_font.setFamily("monospace")
            monospace_font.setPointSize(10)
            monospace_font.setStyleHint(QFont.StyleHint.TypeWriter)
        self.result_list.setFont(monospace_font)
        layout.addWidget(self.result_list)

        # 预览区域
        preview_label = QLabel("预览:", self)
        layout.addWidget(preview_label)

        self.preview_text = QTextEdit(self)
        self.preview_text.setReadOnly(True)
        # 设置等宽字体
        preview_font = QFont("Consolas", 11)
        if not preview_font.exactMatch():
            preview_font = QFont()
            preview_font.setFamily("monospace")
            preview_font.setPointSize(11)
            preview_font.setStyleHint(QFont.StyleHint.TypeWriter)
        self.preview_text.setFont(preview_font)
        layout.addWidget(self.preview_text)
        
        # 关闭按钮
        close_button = QPushButton("关闭", self)
        close_button.clicked.connect(self.reject)
        
        # 跳转按钮
        self.goto_button = QPushButton("跳转到日期", self)
        self.goto_button.clicked.connect(self.accept)
        self.goto_button.setEnabled(False)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.goto_button)
        button_layout.addWidget(close_button)
        layout.addLayout(button_layout)
        
    def display_results(self, results):
        """显示搜索结果"""
        self.results = results
        self.result_list.clear()
        self.preview_text.clear()
        
        # 更新结果数量
        count = len(results)
        self.result_count_label.setText(f"找到 {count} 个结果")
        
        # 添加结果到列表
        for result in results:
            # 创建带有日期的项目文本
            date_text = result.date.toString('yyyy-MM-dd')
            
            # 创建基本列表项
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, result)
            
            # 如果有匹配文本，显示带有匹配文本的项目
            if result.match_text:
                # 使用简单文本格式，避免HTML高亮导致的性能问题
                item_text = f"{date_text}: {result.match_text}"
                item.setText(item_text)
            else:
                # 没有匹配文本，只显示日期
                item.setText(date_text)
                
            self.result_list.addItem(item)
    
    def _escape_html(self, text):
        """转义HTML特殊字符"""
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&#39;")

    def item_double_clicked(self, item):
        """当用户双击结果项时"""
        result = item.data(Qt.ItemDataRole.UserRole)
        if result:
            self.selected_date = result.date
            
            # 显示文本内容，如果有关键词则高亮显示
            if self.keyword and self.keyword.strip():
                self.show_highlighted_content(result.content, self.keyword)
            else:
                self.preview_text.setPlainText(result.content)
                
            self.goto_button.setEnabled(True)
    
    def show_highlighted_content(self, content, keyword):
        """显示带有高亮的内容"""
        # 避免处理过长的内容导致UI卡死
        MAX_TEXT_LENGTH = 100000  # 限制处理的最大文本长度
        if len(content) > MAX_TEXT_LENGTH:
            # 对过长的内容，只显示前面的部分，不进行高亮处理
            self.preview_text.setPlainText(content[:MAX_TEXT_LENGTH] + "\n\n[文本过长，已截断显示...]")
            return
            
        try:
            # 清空当前内容
            self.preview_text.clear()
            
            # 先设置普通文本
            self.preview_text.setPlainText(content)
            
            # 如果关键词为空，不进行高亮处理
            if not keyword or not keyword.strip():
                return
                
            # 处理不区分大小写的搜索
            # keyword_lower = keyword.lower()  # 这个变量在当前实现中未使用
            
            # 创建高亮格式
            highlight_format = self.preview_text.textCursor().charFormat()
            highlight_format.setBackground(QColor(255, 255, 0))  # 黄色背景
            highlight_format.setForeground(QColor(0, 0, 0))      # 黑色文字
            
            # 设置初始搜索位置
            cursor = self.preview_text.textCursor()
            cursor.movePosition(cursor.MoveOperation.Start)  # 移动到文档开始
            self.preview_text.setTextCursor(cursor)
            
            # 限制高亮次数，避免无限循环
            max_highlights = 500
            highlight_count = 0
            
            # 查找并高亮内容
            while highlight_count < max_highlights:
                # 执行不区分大小写的搜索
                found = self.preview_text.find(keyword, QTextDocument.FindFlag(0))  # 不区分大小写
                if not found:
                    break  # 没有找到更多匹配，退出循环
                    
                # 获取当前光标并应用高亮格式
                cursor = self.preview_text.textCursor()
                if cursor.hasSelection():
                    cursor.mergeCharFormat(highlight_format)
                    highlight_count += 1
                else:
                    break  # 没有选中文本，退出循环
                    
            # 重置光标到文档开始
            cursor = self.preview_text.textCursor()
            cursor.movePosition(cursor.MoveOperation.Start)
            self.preview_text.setTextCursor(cursor)
            
        except Exception as e:
            # 异常处理
            print(f"高亮文本时出错: {e}")
            # 确保至少显示原始内容
            self.preview_text.setPlainText(content)
    
    def get_selected_date(self):
        """返回用户选择的日期"""
        return self.selected_date

class InPageSearchDialog(QDialog):
    """页面内搜索对话框"""
    def __init__(self, parent=None, text_edit=None):
        super().__init__(parent)
        self.text_edit = text_edit
        self.current_match_index = -1
        self.previous_match_index = -1  # 添加：跟踪上一个匹配项的索引
        self.matches = []
        self.original_format = QTextCharFormat()  # 保存原始格式
        self.search_format = QTextCharFormat()   # 搜索高亮格式

        # 设置搜索高亮格式
        self.search_format.setBackground(QColor(255, 255, 0))  # 黄色背景
        self.search_format.setForeground(QColor(0, 0, 0))      # 黑色文字

        self.current_format = QTextCharFormat()  # 当前匹配高亮格式
        self.current_format.setBackground(QColor(0, 100, 255))  # 更鲜艳的蓝色背景
        self.current_format.setForeground(QColor(255, 255, 255))  # 白色文字，提高对比度

        # 添加搜索防抖定时器
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.delayed_search)
        self.search_delay = 300  # 300ms 延迟

        self.initUI()

    def initUI(self):
        """初始化用户界面"""
        self.setWindowTitle("页面内搜索")
        self.setFixedSize(400, 120)

        # 设置窗口标志，使其保持在父窗口前面
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint)

        layout = QVBoxLayout(self)

        # 搜索输入区域
        search_layout = QHBoxLayout()
        search_label = QLabel("查找:", self)
        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText("输入要查找的文本...")
        self.search_input.textChanged.connect(self.on_search_text_changed)
        self.search_input.returnPressed.connect(self.find_next)

        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input, 1)
        layout.addLayout(search_layout)

        # 选项区域
        options_layout = QHBoxLayout()
        self.case_sensitive_cb = QCheckBox("区分大小写", self)
        self.case_sensitive_cb.stateChanged.connect(self.on_search_text_changed)
        options_layout.addWidget(self.case_sensitive_cb)
        options_layout.addStretch()  # 添加弹性空间
        layout.addLayout(options_layout)

        # 按钮区域
        button_layout = QHBoxLayout()

        self.prev_button = QPushButton("上一个", self)
        self.prev_button.clicked.connect(self.find_previous)
        self.prev_button.setEnabled(False)

        self.next_button = QPushButton("下一个", self)
        self.next_button.clicked.connect(self.find_next)
        self.next_button.setEnabled(False)

        self.close_button = QPushButton("关闭", self)
        self.close_button.clicked.connect(self.close_search)

        # 结果计数标签
        self.result_label = QLabel("", self)

        button_layout.addWidget(self.result_label)
        button_layout.addStretch()
        button_layout.addWidget(self.prev_button)
        button_layout.addWidget(self.next_button)
        button_layout.addWidget(self.close_button)
        layout.addLayout(button_layout)

        # 设置焦点到搜索输入框
        self.search_input.setFocus()

    def on_search_text_changed(self):
        """搜索文本变化时的处理（使用防抖）"""
        search_text = self.search_input.text()
        if not search_text:
            self.clear_highlights()
            self.update_ui_state(0)
            self.search_timer.stop()
            return

        # 重启定时器，实现防抖效果
        self.search_timer.stop()
        self.search_timer.start(self.search_delay)

    def delayed_search(self):
        """延迟执行的搜索"""
        search_text = self.search_input.text()
        if search_text:
            # 显示搜索进度
            self.result_label.setText("搜索中...")
            self.prev_button.setEnabled(False)
            self.next_button.setEnabled(False)

            # 使用 QTimer 来异步执行搜索，避免阻塞UI
            QTimer.singleShot(10, lambda: self.perform_search(search_text))

    def perform_search(self, search_text):
        """执行搜索（优化版本）"""
        if not self.text_edit or not search_text:
            return

        # 清除之前的高亮
        self.clear_highlights()

        # 获取文档内容和长度
        document = self.text_edit.document()
        full_text = document.toPlainText()
        text_length = len(full_text)

        # 对于超长文本，限制搜索范围但不限制匹配数量
        MAX_TEXT_LENGTH = 50000  # 最大搜索文本长度

        if text_length > MAX_TEXT_LENGTH:
            self.result_label.setText(f"文本过长，仅搜索前{MAX_TEXT_LENGTH//1000}K字符")

        # 获取搜索标志
        flags = QTextDocument.FindFlag(0)
        if self.case_sensitive_cb.isChecked():
            flags |= QTextDocument.FindFlag.FindCaseSensitively

        # 使用优化的搜索算法（取消匹配数量限制）
        self.matches = []
        cursor = self.text_edit.textCursor()
        cursor.movePosition(cursor.MoveOperation.Start)

        # 搜索所有匹配项，不限制数量
        while True:
            cursor = document.find(search_text, cursor, flags)
            if cursor.isNull():
                break

            # 检查是否超出搜索范围
            if text_length > MAX_TEXT_LENGTH and cursor.position() > MAX_TEXT_LENGTH:
                break

            self.matches.append(cursor)

        # 批量高亮匹配项（优化版本）
        self.highlight_matches_optimized()

        # 更新UI状态
        total_matches = len(self.matches)
        if text_length > MAX_TEXT_LENGTH:
            # 对于超长文本，显示特殊提示
            self.update_ui_state_with_limit(total_matches)
        else:
            self.update_ui_state(total_matches)

        # 如果有匹配项，跳转到第一个
        if self.matches:
            self.current_match_index = 0
            self.previous_match_index = -1  # 初始化时没有上一个匹配项
            self.highlight_current_match()

    def highlight_matches_optimized(self):
        """优化的批量高亮方法"""
        if not self.matches:
            return

        # 暂时禁用文本编辑器的更新，提高批量操作性能
        self.text_edit.setUpdatesEnabled(False)

        try:
            # 创建一个临时的格式化对象
            temp_cursor = self.text_edit.textCursor()

            # 批量应用格式，减少重绘次数
            for match_cursor in self.matches:
                temp_cursor.setPosition(match_cursor.selectionStart())
                temp_cursor.setPosition(match_cursor.selectionEnd(), temp_cursor.MoveMode.KeepAnchor)
                temp_cursor.mergeCharFormat(self.search_format)
        finally:
            # 重新启用更新并强制刷新
            self.text_edit.setUpdatesEnabled(True)
            self.text_edit.update()

    def update_ui_state_with_limit(self, match_count):
        """更新UI状态（超长文本提示）"""
        has_matches = match_count > 0
        self.prev_button.setEnabled(has_matches)
        self.next_button.setEnabled(has_matches)

        if match_count == 0:
            self.result_label.setText("未找到")
        else:
            self.result_label.setText(f"1/{match_count} (仅搜索部分文本)")

    def highlight_current_match(self):
        """高亮当前匹配项（优化版本）"""
        if 0 <= self.current_match_index < len(self.matches):
            # 优化：只更新需要改变的匹配项，而不是遍历所有匹配项

            # 1. 如果有上一个匹配项且与当前不同，将其恢复为普通搜索高亮
            if (0 <= self.previous_match_index < len(self.matches) and
                self.previous_match_index != self.current_match_index):
                prev_cursor = self.matches[self.previous_match_index]
                prev_cursor.mergeCharFormat(self.search_format)

            # 2. 将当前匹配项设置为当前高亮（只有在需要时才设置）
            current_cursor = self.matches[self.current_match_index]
            if self.previous_match_index != self.current_match_index:
                current_cursor.mergeCharFormat(self.current_format)

            # 3. 滚动到当前匹配位置
            self.text_edit.setTextCursor(current_cursor)
            self.text_edit.ensureCursorVisible()

            # 4. 确保文本编辑器获得焦点，这样蓝色高亮才会显示
            self.text_edit.setFocus()

            # 5. 更新结果标签
            self.result_label.setText(f"{self.current_match_index + 1}/{len(self.matches)}")

            # 6. 更新上一个匹配项索引
            self.previous_match_index = self.current_match_index

    def find_next(self):
        """查找下一个（优化版本）"""
        if self.matches:
            # 性能监控：记录开始时间
            start_time = time.time()

            # 保存当前索引作为上一个索引
            self.previous_match_index = self.current_match_index
            # 移动到下一个匹配项
            self.current_match_index = (self.current_match_index + 1) % len(self.matches)
            self.highlight_current_match()

            # 性能监控：计算耗时
            elapsed_time = (time.time() - start_time) * 1000  # 转换为毫秒
            if elapsed_time > 10:  # 只记录超过10ms的操作
                print(f"find_next 耗时: {elapsed_time:.2f}ms (匹配数: {len(self.matches)})")

    def find_previous(self):
        """查找上一个（优化版本）"""
        if self.matches:
            # 性能监控：记录开始时间
            start_time = time.time()

            # 保存当前索引作为上一个索引
            self.previous_match_index = self.current_match_index
            # 移动到上一个匹配项
            self.current_match_index = (self.current_match_index - 1) % len(self.matches)
            self.highlight_current_match()

            # 性能监控：计算耗时
            elapsed_time = (time.time() - start_time) * 1000  # 转换为毫秒
            if elapsed_time > 10:  # 只记录超过10ms的操作
                print(f"find_previous 耗时: {elapsed_time:.2f}ms (匹配数: {len(self.matches)})")

    def clear_highlights(self):
        """清除所有高亮（优化版本）"""
        if not self.text_edit:
            return

        # 只有在有匹配项时才清除格式，避免不必要的操作
        if self.matches:
            # 暂时禁用更新，提高批量操作性能
            self.text_edit.setUpdatesEnabled(False)

            try:
                # 只清除之前高亮的部分，而不是整个文档
                for match_cursor in self.matches:
                    temp_cursor = self.text_edit.textCursor()
                    temp_cursor.setPosition(match_cursor.selectionStart())
                    temp_cursor.setPosition(match_cursor.selectionEnd(), temp_cursor.MoveMode.KeepAnchor)
                    temp_cursor.setCharFormat(self.original_format)
            finally:
                # 重新启用更新并强制刷新
                self.text_edit.setUpdatesEnabled(True)
                self.text_edit.update()

        # 清空匹配列表
        self.matches = []
        self.current_match_index = -1
        self.previous_match_index = -1  # 重置上一个匹配项索引

    def update_ui_state(self, match_count):
        """更新UI状态"""
        has_matches = match_count > 0
        self.prev_button.setEnabled(has_matches)
        self.next_button.setEnabled(has_matches)

        if match_count == 0:
            self.result_label.setText("未找到")
        else:
            self.result_label.setText(f"1/{match_count}")

    def close_search(self):
        """关闭搜索"""
        self.clear_highlights()
        self.close()

    def keyPressEvent(self, event):
        """处理键盘事件"""
        if event.key() == Qt.Key.Key_Escape:
            self.close_search()
        elif event.key() == Qt.Key.Key_F3:
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                self.find_previous()
            else:
                self.find_next()
        else:
            super().keyPressEvent(event)

class DiaryApp(QMainWindow):
    """
    A simple diary application with a calendar using PyQt6.
    """
    def __init__(self):
        super().__init__()
        self.current_date = QDate.currentDate()
        # 日记存储结构： diary_entries/YYYY/MM/YYYY-MM-DD.txt
        self.diary_folder_base = "diary_entries"
        # self.diary_folder is now dynamically determined based on current_date or calendar view
        self.old_diary_folder = "diary_entries"  # 旧版日志存储路径 (根目录)

        # 定义高亮格式 (彩色)
        self.highlight_format = QTextCharFormat()
        # 使用更鲜艳的颜色
        self.highlight_format.setForeground(QColor(0, 85, 255))  # 鲜艳的蓝色
        self.highlight_format.setFontWeight(QFont.Weight.Bold)
        # 使用更鲜艳的背景色
        self.highlight_format.setBackground(QColor(220, 235, 255))  # 淡蓝色背景

        # 添加状态栏显示
        self.statusBar().showMessage("就绪")

        # 添加内容变更跟踪
        self.last_saved_content = ""  # 上次保存的内容
        self.content_modified = False  # 内容是否已修改

        # 自动保存功能
        self.auto_save_enabled = True  # 是否启用自动保存
        self.auto_save_interval = 30000  # 自动保存间隔（毫秒），默认30秒
        self.auto_save_timer = QTimer()
        self.auto_save_timer.setSingleShot(False)  # 重复触发
        self.auto_save_timer.timeout.connect(self.auto_save)
        self.last_auto_save_time = time.time()  # 上次自动保存时间
        self.is_auto_saving = False  # 是否正在自动保存

        # 初始化搜索对话框
        self.search_dialog = None

        self.initUI()
        self.ensure_base_diary_folder() # 确保基础目录存在
        self.load_entry_for_date(self.current_date)  # Load today's entry initially

        # 确保在完全初始化后调用高亮
        print("开始初始化日历高亮...")
        self.update_calendar_highlighting() # 初始化时高亮一次
        print("初始化日历高亮完成")

    def initUI(self):
        """Initialize the user interface."""
        self.setWindowTitle('日历笔记本 (Calendar Diary)')
        self.setGeometry(200, 200, 800, 500)  # x, y, width, height

        # 设置程序图标 - 通过多种方法尝试加载图标
        self.load_application_icon()

        # 设置全局等宽字体
        self.setup_monospace_font()

        # --- Central Widget and Layout ---
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # 设置布局边距和间距，使界面更加紧凑
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # --- Vertical Layout for Calendar and Button ---
        v_layout = QVBoxLayout()  # Create a vertical layout for the button and calendar

        # --- Button to Return to Today's Date ---
        show_date = self.current_date.toString("yyyy-MM-dd")
        self.today_button = QPushButton(f"今天 ({show_date})", self)
        self.today_button.clicked.connect(self.return_to_today)

        # --- 搜索区域 ---
        search_layout = QHBoxLayout()
        search_label = QLabel("搜索日记:", self)
        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText("输入关键词...")
        self.search_input.returnPressed.connect(self.perform_search)  # 回车键触发搜索
        
        self.search_button = QPushButton("搜索", self)
        self.search_button.clicked.connect(self.perform_search)
        
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input, 1)  # 分配更多空间给搜索框
        search_layout.addWidget(self.search_button)
        v_layout.addLayout(search_layout)
        
        # --- 自动保存状态区域 ---
        auto_save_layout = QHBoxLayout()
        self.auto_save_status_label = QLabel("自动保存: 已启用", self)
        self.auto_save_status_label.setStyleSheet("color: green; font-size: 10px;")
        
        self.auto_save_toggle_button = QPushButton("关闭自动保存", self)
        self.auto_save_toggle_button.setMaximumWidth(100)
        self.auto_save_toggle_button.clicked.connect(self.toggle_auto_save)
        
        auto_save_layout.addWidget(self.auto_save_status_label)
        auto_save_layout.addStretch()  # 添加弹性空间
        auto_save_layout.addWidget(self.auto_save_toggle_button)
        v_layout.addLayout(auto_save_layout)
        
        # 添加今天按钮
        v_layout.addWidget(self.today_button)  # Add today button

        # --- Calendar Widget ---
        self.calendar = QCalendarWidget(self)
        self.calendar.setGridVisible(True)

        # 设置默认风格但保持当前大小的日历控件
        self.calendar.setSelectedDate(self.current_date)  # 设置初始选中日期为今天

        # 基本视图设置
        self.calendar.setFirstDayOfWeek(Qt.DayOfWeek.Monday)  # 设置每周第一天为周一
        self.calendar.setHorizontalHeaderFormat(QCalendarWidget.HorizontalHeaderFormat.ShortDayNames)  # 显示短日期名
        self.calendar.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)  # 不显示垂直表头
        self.calendar.setNavigationBarVisible(True)  # 确保导航栏可见

        # 设置日历控件字体为等宽字体
        calendar_font = QFont("Consolas", 9)
        if not calendar_font.exactMatch():
            calendar_font = QFont()
            calendar_font.setFamily("monospace")
            calendar_font.setPointSize(9)
            calendar_font.setStyleHint(QFont.StyleHint.TypeWriter)
        self.calendar.setFont(calendar_font)

        # 设置日历控件大小
        self.calendar.setFixedWidth(350)
        self.calendar.setMinimumHeight(280)

        # 使用合适的尺寸策略
        self.calendar.setSizePolicy(
            QSizePolicy.Policy.Fixed,  # 水平方向固定
            QSizePolicy.Policy.Fixed   # 垂直方向固定
        )

        # 将日历加入垂直布局
        v_layout.addWidget(self.calendar)      # Add calendar below the button

        # --- Text Edit Widget ---
        self.text_edit = PlainTextEdit(self)
        self.text_edit.setPlaceholderText("请在此处输入您的日记内容...")
        # 设置等宽字体
        self.text_edit.setFont(self.monospace_font)

        # --- Add widgets to main horizontal layout ---
        main_layout.addLayout(v_layout, 1)  # Add vertical layout (button + calendar)
        main_layout.addWidget(self.text_edit, 2)  # Add text editor to the right side

        # --- Connect Signals ---
        # selectionChanged fires when the user clicks a date
        self.calendar.selectionChanged.connect(self.handle_date_change)
        # currentPageChanged fires when the month/year view changes
        self.calendar.currentPageChanged.connect(self.update_calendar_highlighting)
        # 连接文本变更信号来跟踪内容修改状态
        self.text_edit.textChanged.connect(self.on_text_changed)
        
        # 启动自动保存定时器
        if self.auto_save_enabled:
            self.auto_save_timer.start(self.auto_save_interval)
            
        # 更新自动保存UI状态
        self.update_auto_save_ui()

        # --- 添加快捷键 ---
        self.setup_shortcuts()

        print("UI初始化完成，所有信号已连接")

    def setup_monospace_font(self):
        """设置全局等宽字体"""
        # 创建等宽字体，优先使用 Consolas，如果不可用则使用系统默认等宽字体
        self.monospace_font = QFont("Consolas", 12)
        if not self.monospace_font.exactMatch():
            # 如果 Consolas 不可用，尝试其他等宽字体
            fallback_fonts = ["Courier New", "Monaco", "Menlo", "DejaVu Sans Mono", "Liberation Mono"]
            for font_name in fallback_fonts:
                test_font = QFont(font_name, 12)
                if test_font.exactMatch():
                    self.monospace_font = test_font
                    break
            else:
                # 如果都不可用，使用系统默认等宽字体
                self.monospace_font = QFont()
                self.monospace_font.setFamily("monospace")
                self.monospace_font.setPointSize(12)

        # 确保字体是等宽的
        self.monospace_font.setStyleHint(QFont.StyleHint.TypeWriter)
        print(f"设置等宽字体: {self.monospace_font.family()}")

    def setup_shortcuts(self):
        """设置键盘快捷键"""
        # Ctrl+F 页面内搜索
        find_shortcut = QShortcut(QKeySequence.StandardKey.Find, self)
        find_shortcut.activated.connect(self.show_in_page_search)

        # F3 查找下一个（如果搜索对话框已打开）
        find_next_shortcut = QShortcut(QKeySequence(Qt.Key.Key_F3), self)
        find_next_shortcut.activated.connect(self.find_next_in_search)

        # Shift+F3 查找上一个（如果搜索对话框已打开）
        find_prev_shortcut = QShortcut(QKeySequence("Shift+F3"), self)
        find_prev_shortcut.activated.connect(self.find_previous_in_search)

        # Escape 关闭搜索对话框
        escape_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        escape_shortcut.activated.connect(self.close_in_page_search)

        # Ctrl+S 保存当前日记
        save_shortcut = QShortcut(QKeySequence.StandardKey.Save, self)
        save_shortcut.activated.connect(self.save_current_entry)
        
        # Ctrl+Shift+A 切换自动保存
        auto_save_shortcut = QShortcut(QKeySequence("Ctrl+Shift+A"), self)
        auto_save_shortcut.activated.connect(self.toggle_auto_save)

        print("快捷键设置完成")

    def show_in_page_search(self):
        """显示页面内搜索对话框"""
        # 如果搜索对话框已存在，关闭它
        if hasattr(self, 'search_dialog') and self.search_dialog:
            self.search_dialog.close()

        # 创建新的搜索对话框
        self.search_dialog = InPageSearchDialog(self, self.text_edit)

        # 如果文本编辑器中有选中的文本，将其作为默认搜索词
        cursor = self.text_edit.textCursor()
        if cursor.hasSelection():
            selected_text = cursor.selectedText()
            self.search_dialog.search_input.setText(selected_text)

        # 显示对话框
        self.search_dialog.show()

        # 将对话框定位在主窗口的右上角
        main_geometry = self.geometry()
        dialog_width = self.search_dialog.width()

        x = main_geometry.x() + main_geometry.width() - dialog_width - 20
        y = main_geometry.y() + 50

        self.search_dialog.move(x, y)

    def find_next_in_search(self):
        """在搜索对话框中查找下一个"""
        if hasattr(self, 'search_dialog') and self.search_dialog and self.search_dialog.isVisible():
            self.search_dialog.find_next()

    def find_previous_in_search(self):
        """在搜索对话框中查找上一个"""
        if hasattr(self, 'search_dialog') and self.search_dialog and self.search_dialog.isVisible():
            self.search_dialog.find_previous()

    def close_in_page_search(self):
        """关闭页面内搜索对话框"""
        if hasattr(self, 'search_dialog') and self.search_dialog and self.search_dialog.isVisible():
            self.search_dialog.close_search()
    
    def toggle_auto_save(self):
        """切换自动保存状态"""
        self.set_auto_save_enabled(not self.auto_save_enabled)
        self.update_auto_save_ui()
        status = "已启用" if self.auto_save_enabled else "已禁用"
        self.statusBar().showMessage(f"自动保存{status}", 2000)
        print(f"自动保存{status}")
    
    def update_auto_save_ui(self):
        """更新自动保存UI状态"""
        if self.auto_save_enabled:
            self.auto_save_status_label.setText(f"自动保存: 已启用 ({self.auto_save_interval//1000}秒)")
            self.auto_save_status_label.setStyleSheet("color: green; font-size: 10px;")
            self.auto_save_toggle_button.setText("关闭自动保存")
        else:
            self.auto_save_status_label.setText("自动保存: 已禁用")
            self.auto_save_status_label.setStyleSheet("color: red; font-size: 10px;")
            self.auto_save_toggle_button.setText("启用自动保存")

    def on_text_changed(self):
        """文本内容变更时的处理"""
        current_content = self.text_edit.toPlainText()
        was_modified = self.content_modified
        self.content_modified = (current_content != self.last_saved_content)

        # 可选：在窗口标题中显示修改状态
        if self.content_modified:
            if not self.windowTitle().endswith(" *"):
                self.setWindowTitle(self.windowTitle() + " *")
            # 如果内容刚开始修改，重置自动保存定时器
            if not was_modified and self.auto_save_enabled:
                self.auto_save_timer.start(self.auto_save_interval)
        else:
            if self.windowTitle().endswith(" *"):
                self.setWindowTitle(self.windowTitle()[:-2])

    def is_content_saved(self):
        """检查当前内容是否已保存"""
        return not self.content_modified

    def mark_content_as_saved(self):
        """标记内容为已保存状态"""
        self.last_saved_content = self.text_edit.toPlainText()
        self.content_modified = False
        # 移除窗口标题中的修改标记
        if self.windowTitle().endswith(" *"):
            self.setWindowTitle(self.windowTitle()[:-2])

    def load_application_icon(self):
        """尝试多种方式加载应用图标"""
        # 1. 尝试从当前运行目录加载
        if os.path.exists('icon.ico'):
            self.setWindowIcon(QIcon('icon.ico'))
            return
            
        # 2. 尝试从脚本所在目录加载
        script_dir = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(script_dir, 'icon.ico')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
            return
            
        # 3. 尝试从父目录加载
        parent_dir = os.path.dirname(script_dir)
        icon_path = os.path.join(parent_dir, 'icon.ico')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
            return
            
        # 4. 尝试从打包资源加载
        try:
            # 尝试从PyInstaller或Nuitka打包的资源中加载
            base_path = getattr(sys, '_MEIPASS', script_dir)
            icon_path = os.path.join(base_path, 'icon.ico')
            if os.path.exists(icon_path):
                self.setWindowIcon(QIcon(icon_path))
                return
        except:
            pass
            
        print("警告：无法找到图标文件icon.ico")

    def ensure_base_diary_folder(self):
        """Create the base diary_entries folder if it doesn't exist."""
        if not QDir(self.diary_folder_base).exists():
            try:
                QDir().mkpath(self.diary_folder_base)
                print(f"Created base directory: {self.diary_folder_base}")
            except Exception as e:
                QMessageBox.critical(self, "错误 (Error)", f"无法创建日记存储基础目录:\n{self.diary_folder_base}\n\n{e}")
                # Optionally exit or disable saving
                # sys.exit(1)

    def get_filename_for_date(self, date: QDate) -> str:
        """Generate the filename for a given date (e.g., diary_entries/YYYY/MM/YYYY-MM-DD.txt)."""
        year_str = date.toString('yyyy')
        month_str = date.toString('MM')
        day_str = date.toString('yyyy-MM-dd')
        target_folder = os.path.join(self.diary_folder_base, year_str, month_str)
        new_file = os.path.join(target_folder, day_str + ".txt")

        # 检查旧版日志存储位置
        old_file = os.path.join(self.old_diary_folder, day_str + ".txt")

        # 如果旧文件存在但新文件不存在，则执行按需迁移
        if os.path.isfile(old_file) and not os.path.exists(new_file):
             # 确保目标目录存在
            if not QDir(target_folder).exists():
                try:
                    QDir().mkpath(target_folder)
                    print(f"按需迁移时创建目录: {target_folder}")
                except Exception as e:
                    print(f"错误: 按需迁移时无法创建目录 {target_folder}: {e}")
                    # 如果无法创建目录，可能应该返回旧路径或抛出错误？
                    # 暂时返回新路径，保存时会再次尝试创建。

            # 复制内容
            try:
                with open(old_file, 'r', encoding='utf-8') as src:
                    content = src.read()
                with open(new_file, 'w', encoding='utf-8') as dst:
                    dst.write(content)
                print(f"按需迁移日志: {old_file} -> {new_file}")
                # 选择性删除旧文件
                # os.remove(old_file)
            except Exception as e:
                print(f"按需迁移文件时出错: {e}")
                # 如果迁移失败，是返回旧路径还是新路径？
                # 返回新路径，加载/保存会失败，可能更安全。

        # 始终返回新版结构的文件路径
        return new_file

    def load_entry_for_date(self, date: QDate):
        """加载指定日期的日记内容到文本编辑器。"""
        filename = self.get_filename_for_date(date)
        try:
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    content = f.read()
                    self.text_edit.setPlainText(content)
                    print(f"加载日记成功: {date.toString('yyyy-MM-dd')}")
            else:
                self.text_edit.clear()  # 该日期没有日记
                print(f"没有找到日记: {date.toString('yyyy-MM-dd')}")
        except Exception as e:
            error_msg = f"无法加载日期 {date.toString('yyyy-MM-dd')} 的日记:\n\n{e}"
            print(f"错误: {error_msg}")
            QMessageBox.warning(self, "加载错误 (Load Error)", error_msg)
            self.text_edit.clear()

        # 加载完成后，标记内容为已保存状态
        self.mark_content_as_saved()

        # 确保日历高亮状态正确
        # 检查当前显示的月份是否包含加载的日期
        current_year_shown = self.calendar.yearShown()
        current_month_shown = self.calendar.monthShown()

        if date.year() == current_year_shown and date.month() == current_month_shown:
            # 如果日期在当前显示的月份内，更新高亮
            self.update_calendar_highlighting()

    def save_entry_for_date(self, date: QDate):
        """保存指定日期的日记内容。"""
        # 首先，确保目标目录存在
        year_str = date.toString('yyyy')
        month_str = date.toString('MM')
        target_folder = os.path.join(self.diary_folder_base, year_str, month_str)
        
        if not os.path.exists(target_folder):
            try:
                os.makedirs(target_folder, exist_ok=True)
                print(f"保存前创建目录: {target_folder}")
            except Exception as e:
                print(f"创建目录失败: {target_folder} - {e}")
                QMessageBox.warning(self, "保存错误", f"无法创建目录:\n{target_folder}\n\n{e}")
                return False
                
        # 获取文件名并保存内容
        filename = self.get_filename_for_date(date)
        content = self.text_edit.toPlainText().strip()  # 获取文本并去除首尾空白

        # 决定是否保存空内容
        should_save = bool(content) or os.path.exists(filename)

        if not should_save:
            print(f"跳过保存空内容的新日记: {date.toString('yyyy-MM-dd')}")
            return True  # 对于从未有过内容的日期，不创建空文件

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(self.text_edit.toPlainText())  # 保存确切内容
            print(f"保存日记成功: {date.toString('yyyy-MM-dd')} -> {filename}")

            # 保存成功后，标记内容为已保存状态
            self.mark_content_as_saved()

            # 保存后强制更新高亮
            print("保存后更新日历高亮...")
            self.update_calendar_highlighting()
            return True
        except Exception as e:
            error_msg = f"无法保存日期 {date.toString('yyyy-MM-dd')} 的日记:\n\n{e}"
            print(f"错误: {error_msg}")
            QMessageBox.warning(self, "保存错误 (Save Error)", error_msg)
            return False

    def save_current_entry(self):
        """保存当前日期的日记内容（Ctrl+S快捷键调用）"""
        success = self.save_entry_for_date(self.current_date)
        if success:
            self.statusBar().showMessage("日记已保存", 2000)  # 显示2秒
        else:
            self.statusBar().showMessage("保存失败", 2000)
    
    def auto_save(self):
        """自动保存功能"""
        # 检查是否需要自动保存
        if not self.auto_save_enabled or not self.content_modified or self.is_auto_saving:
            return
            
        # 避免在用户正在输入时自动保存
        current_time = time.time()
        if current_time - self.last_auto_save_time < 5:  # 至少间隔5秒
            return
            
        self.is_auto_saving = True
        # 临时更新状态标签显示正在保存
        original_text = self.auto_save_status_label.text()
        self.auto_save_status_label.setText("自动保存: 保存中...")
        self.auto_save_status_label.setStyleSheet("color: orange; font-size: 10px;")
        
        try:
            success = self.save_entry_for_date(self.current_date)
            if success:
                self.last_auto_save_time = current_time
                # 显示自动保存成功的提示
                self.statusBar().showMessage("自动保存完成", 1500)
                print(f"自动保存成功: {self.current_date.toString('yyyy-MM-dd')}")
                # 临时显示成功状态
                self.auto_save_status_label.setText(f"自动保存: 已保存 ({time.strftime('%H:%M:%S')})")
                self.auto_save_status_label.setStyleSheet("color: blue; font-size: 10px;")
                # 2秒后恢复正常状态
                QTimer.singleShot(2000, self.update_auto_save_ui)
            else:
                print(f"自动保存失败: {self.current_date.toString('yyyy-MM-dd')}")
                # 恢复原状态
                self.update_auto_save_ui()
        except Exception as e:
            print(f"自动保存时发生异常: {e}")
            # 恢复原状态
            self.update_auto_save_ui()
        finally:
            self.is_auto_saving = False
    
    def set_auto_save_enabled(self, enabled):
        """启用或禁用自动保存"""
        self.auto_save_enabled = enabled
        if enabled:
            if self.content_modified:
                self.auto_save_timer.start(self.auto_save_interval)
        else:
            self.auto_save_timer.stop()
    
    def set_auto_save_interval(self, interval_seconds):
        """设置自动保存间隔（秒）"""
        self.auto_save_interval = interval_seconds * 1000  # 转换为毫秒
        if self.auto_save_enabled and self.auto_save_timer.isActive():
            self.auto_save_timer.start(self.auto_save_interval)  # 重启定时器以应用新间隔

    def handle_date_change(self):
        """日历日期选择变化时的处理。"""
        new_date = self.calendar.selectedDate()
        if new_date != self.current_date:
            print(f"日期变更: {self.current_date.toString('yyyy-MM-dd')} -> {new_date.toString('yyyy-MM-dd')}")
            
            # 1. 保存当前日期的日记
            save_result = self.save_entry_for_date(self.current_date)
            if not save_result:
                # 保存失败，询问用户是否仍要切换日期
                reply = QMessageBox.question(
                    self, 
                    "保存失败", 
                    f"保存 {self.current_date.toString('yyyy-MM-dd')} 的日记失败。\n是否仍要切换到新日期？",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.No:
                    # 用户选择不切换，恢复日历选择
                    self.calendar.blockSignals(True)  # 阻止信号触发新的事件
                    self.calendar.setSelectedDate(self.current_date)
                    self.calendar.blockSignals(False)  # 恢复信号处理
                    return

            # 2. 更新当前日期
            self.current_date = new_date

            # 3. 加载新日期的日记
            self.load_entry_for_date(self.current_date)
            
            # 4. 日期变化后，确保高亮正确显示
            # 注意：这里不需要显式调用 update_calendar_highlighting
            # 因为 load_entry_for_date 和 save_entry_for_date 内部会处理

    def return_to_today(self):
        """Return the calendar to today's date when the 'Today' button is clicked."""
        today_date = QDate.currentDate()
        if today_date != self.current_date:
            print(f"Returning to today: saving {self.current_date.toString('yyyy-MM-dd')}")
            self.save_entry_for_date(self.current_date) # Save current entry first
            self.current_date = today_date
            self.calendar.setSelectedDate(today_date) # Update calendar selection
            self.load_entry_for_date(self.current_date) # Load today's entry
            # No need to update highlighting here, save/load handles it, and selection doesn't change month view
        else:
             # If already on today, just ensure calendar shows it and reload
             self.calendar.setSelectedDate(today_date)
             self.load_entry_for_date(today_date) # Reload in case content was changed but not saved

    def closeEvent(self, event: QCloseEvent):
        """Handle the application closing event."""
        # 停止自动保存定时器
        if hasattr(self, 'auto_save_timer'):
            self.auto_save_timer.stop()
            
        # 检查内容是否已保存
        if self.is_content_saved():
            # 内容已保存，直接关闭
            print("内容已保存，直接关闭应用")
            event.accept()
            return

        # 内容未保存，询问用户
        reply = QMessageBox.question(self, '退出确认 (Confirm Exit)',
                                     '当前日记内容尚未保存，您想在退出前保存吗？\n(Current diary content is not saved. Save before exiting?)',
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
                                     QMessageBox.StandardButton.Yes)

        if reply == QMessageBox.StandardButton.Yes:
            # 尝试保存
            save_success = self.save_entry_for_date(self.current_date)
            if save_success:
                event.accept()  # 保存成功，关闭应用
            else:
                # 保存失败，询问是否仍要关闭
                force_close = QMessageBox.question(
                    self, '保存失败',
                    '保存失败，是否仍要关闭应用？\n(Save failed. Close anyway?)',
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                if force_close == QMessageBox.StandardButton.Yes:
                    event.accept()
                else:
                    event.ignore()
        elif reply == QMessageBox.StandardButton.No:
            event.accept()  # 不保存，直接关闭
        else:
            event.ignore()  # 取消关闭

    # --- Highlighting Logic ---
    def get_dates_with_entries(self, year: int, month: int) -> set[QDate]:
        """
        扫描指定年月的日记目录，返回有日记内容的日期集合。
        """
        dates = set()
        month_folder = os.path.join(self.diary_folder_base, f"{year:04d}", f"{month:02d}")
        
        print(f"正在扫描目录: {month_folder}")
        
        # 检查目录是否存在
        if not os.path.exists(month_folder):
            print(f"目录不存在: {month_folder}")
            # 也检查旧版目录中的文件
            self.check_old_directory_entries(year, month, dates)
            return dates
            
        if not QDir(month_folder).exists():
            print(f"QDir报告目录不存在: {month_folder}")
            # 同样检查旧版目录
            self.check_old_directory_entries(year, month, dates)
            return dates

        try:
            # 直接使用 Python 的 os 模块列出文件
            text_files = [f for f in os.listdir(month_folder) if f.endswith('.txt')]
            print(f"找到 {len(text_files)} 个文本文件: {text_files}")
            
            for file_name in text_files:
                try:
                    # 从文件名提取日期 (YYYY-MM-DD.txt 格式)
                    date_str = file_name.replace(".txt", "")
                    entry_date = QDate.fromString(date_str, "yyyy-MM-dd")
                    
                    # 验证日期有效性
                    if entry_date.isValid() and entry_date.year() == year and entry_date.month() == month:
                        file_path = os.path.join(month_folder, file_name)
                        # 可选：检查文件是否为空
                        if os.path.getsize(file_path) > 0:  # 只有非空文件才算有内容
                            dates.add(entry_date)
                            print(f"有效日记文件: {file_name}")
                        else:
                            print(f"空日记文件: {file_name}")
                except Exception as e:
                    print(f"处理文件 {file_name} 时出错: {e}")
        except Exception as e:
            print(f"列出目录 {month_folder} 内容时出错: {e}")
            
        # 检查旧版目录中的文件（可能有未迁移完成的）
        self.check_old_directory_entries(year, month, dates)
            
        return dates
        
    def check_old_directory_entries(self, year: int, month: int, dates_set: set):
        """
        检查旧版目录中是否有指定年月的日记文件
        """
        if not os.path.exists(self.old_diary_folder):
            return
            
        try:
            # 查找格式为 YYYY-MM-DD.txt 的文件
            old_files = os.listdir(self.old_diary_folder)
            month_prefix = f"{year:04d}-{month:02d}-"
            
            for file_name in old_files:
                if file_name.endswith('.txt') and file_name.startswith(month_prefix):
                    try:
                        date_str = file_name.replace(".txt", "")
                        entry_date = QDate.fromString(date_str, "yyyy-MM-dd")
                        
                        if entry_date.isValid():
                            file_path = os.path.join(self.old_diary_folder, file_name)
                            # 只添加非空文件
                            if os.path.getsize(file_path) > 0:
                                dates_set.add(entry_date)
                                print(f"旧目录中的有效日记文件: {file_name}")
                            else:
                                print(f"旧目录中的空日记文件: {file_name}")
                    except Exception as e:
                        print(f"处理旧目录文件 {file_name} 时出错: {e}")
        except Exception as e:
            print(f"列出旧目录 {self.old_diary_folder} 内容时出错: {e}")

    def update_calendar_highlighting(self):
        """
        为日历中有日记内容的日期应用彩色高亮显示。
        """
        year = self.calendar.yearShown()
        month = self.calendar.monthShown()
        
        print(f"开始更新日历高亮：{year}年{month}月")
        
        # 获取有日记内容的日期集合
        dates_with_entries = self.get_dates_with_entries(year, month)
        print(f"找到 {len(dates_with_entries)} 个有日记的日期")
        
        if dates_with_entries:
            print(f"有日记的日期: {[date.toString('yyyy-MM-dd') for date in dates_with_entries]}")
        
        # 首先清除当前月份所有日期的格式
        # 这可以解决有些日期高亮不会被清除的问题
        default_format = QTextCharFormat()
        
        # 迭代当前显示月份的所有天
        current_day = QDate(year, month, 1)
        while current_day.month() == month and current_day.year() == year:
            # 首先重置所有日期为默认格式
            self.calendar.setDateTextFormat(current_day, default_format)
            
            # 然后为有日记的日期设置高亮
            if current_day in dates_with_entries:
                self.calendar.setDateTextFormat(current_day, self.highlight_format)
                print(f"高亮日期: {current_day.toString('yyyy-MM-dd')}")
            
            # 前进到下一天
            current_day = current_day.addDays(1)
        
        # 强制刷新日历显示
        self.calendar.updateCells()
        
        print(f"完成日历高亮更新: {year}-{month:02d}")

    # --- 搜索功能 ---
    def perform_search(self):
        """执行日记内容搜索"""
        keyword = self.search_input.text().strip()
        if not keyword:
            QMessageBox.information(self, "搜索提示", "请输入要搜索的关键词")
            return
            
        # 保存当前内容
        self.save_entry_for_date(self.current_date)
        
        # 显示搜索中的提示
        self.statusBar().showMessage(f"正在搜索 '{keyword}'...")
        self.search_button.setEnabled(False)
        self.search_input.setEnabled(False)
        QApplication.processEvents()  # 确保UI更新
        
        try:
            # 执行搜索
            print(f"开始搜索关键词: {keyword}")
            results = self.search_diary_entries(keyword)
            
            # 恢复UI状态
            self.search_button.setEnabled(True)
            self.search_input.setEnabled(True)
            self.statusBar().clearMessage()
            
            if not results:
                QMessageBox.information(self, "搜索结果", f"未找到包含 '{keyword}' 的日记")
                return
                
            # 显示搜索结果对话框，传递关键词用于高亮显示
            dlg = SearchDialog(self, results, keyword)
            # 设置对话框标题包含搜索关键词
            dlg.setWindowTitle(f"搜索结果 - '{keyword}'")
            
            if dlg.exec() == QDialog.DialogCode.Accepted:
                # 用户选择了一个结果并点击了跳转
                selected_date = dlg.get_selected_date()
                if selected_date and selected_date.isValid():
                    # 切换到选定的日期
                    self.calendar.setSelectedDate(selected_date)
                    # handle_date_change 会通过信号自动触发
        except Exception as e:
            QMessageBox.critical(self, "搜索错误", f"搜索过程中发生错误:\n{e}")
        finally:
            # 无论如何都确保UI恢复
            self.search_button.setEnabled(True)
            self.search_input.setEnabled(True)
            self.statusBar().clearMessage()

    def search_diary_entries(self, keyword):
        """
        在所有日记文件中搜索关键词
        返回: 搜索结果列表 [SearchResultItem, ...]
        """
        results = []
        keyword = keyword.lower()  # 不区分大小写
        total_files_searched = 0
        
        try:
            # 获取所有可能的日记文件路径
            diary_files = self._collect_all_diary_files()
            total_files = len(diary_files)
            
            if total_files == 0:
                print("未找到任何日记文件")
                return results
                
            print(f"开始搜索 {total_files} 个文件...")
            
            # 搜索每个文件
            for idx, file_path in enumerate(diary_files):
                # 更新状态栏显示搜索进度
                if idx % 3 == 0:  # 每3个文件更新一次，避免过于频繁的UI更新
                    self.statusBar().showMessage(f"正在搜索... ({idx+1}/{total_files})")
                    QApplication.processEvents()  # 确保UI响应
                
                # 添加超时检测，避免大文件卡死
                try:
                    # 限制文件大小，跳过过大的文件
                    file_size = os.path.getsize(file_path)
                    if file_size > 1024 * 1024:  # 跳过大于1MB的文件
                        print(f"跳过大文件 {file_path} ({file_size / 1024:.1f} KB)")
                        continue
                        
                    self._search_in_file(file_path, keyword, results)
                    total_files_searched += 1
                except Exception as e:
                    print(f"搜索文件 {file_path} 时出错: {e}")
                
            print(f"搜索完成: 共搜索 {total_files_searched} 个文件，找到 {len(results)} 个结果")
            
        except Exception as e:
            print(f"搜索过程中出错: {e}")
            raise
            
        # 按日期排序结果（从新到旧）
        results.sort(key=lambda x: x.date, reverse=True)
        
        # 限制返回结果数量，避免显示过多结果导致UI卡死
        MAX_RESULTS = 100
        if len(results) > MAX_RESULTS:
            print(f"结果过多，只显示前 {MAX_RESULTS} 个")
            return results[:MAX_RESULTS]
            
        return results
    
    def _collect_all_diary_files(self):
        """收集所有日记文件路径"""
        diary_files = []
        
        # 1. 从新目录结构中收集
        try:
            for year_dir in self._get_valid_dirs(self.diary_folder_base):
                year_path = os.path.join(self.diary_folder_base, year_dir)
                
                for month_dir in self._get_valid_dirs(year_path):
                    month_path = os.path.join(year_path, month_dir)
                    
                    for file_name in os.listdir(month_path):
                        if file_name.endswith('.txt'):
                            file_path = os.path.join(month_path, file_name)
                            diary_files.append(file_path)
        except Exception as e:
            print(f"收集新目录结构文件时出错: {e}")
                
        return diary_files
    
    def _is_valid_diary_filename(self, filename):
        """检查文件名是否为有效的日记文件名 (YYYY-MM-DD.txt)"""
        if not filename.endswith('.txt'):
            return False
            
        date_str = filename.replace(".txt", "")
        parts = date_str.split("-")
        
        if len(parts) != 3:
            return False
            
        try:
            _, month, day = map(int, parts)
            # 简单校验日期格式
            return 1 <= month <= 12 and 1 <= day <= 31
        except ValueError:
            return False
    
    def _file_exists_in_new_structure(self, filename):
        """检查文件是否已存在于新目录结构中"""
        date_str = filename.replace(".txt", "")
        parts = date_str.split("-")
        
        if len(parts) != 3:
            return False
            
        year, month, _ = parts
        new_path = os.path.join(self.diary_folder_base, year, month, filename)
        return os.path.exists(new_path)
        
    def _get_valid_dirs(self, path):
        """获取目录中的所有有效子目录"""
        if not os.path.exists(path) or not os.path.isdir(path):
            return []
            
        return [d for d in os.listdir(path) if os.path.isdir(os.path.join(path, d))]
        
    def _search_in_file(self, file_path, keyword, results):
        """在单个文件中搜索关键词并将结果添加到结果列表"""
        try:
            # 从文件名中提取日期
            file_name = os.path.basename(file_path)
            date_str = file_name.replace(".txt", "")
            entry_date = QDate.fromString(date_str, "yyyy-MM-dd")
            
            if not entry_date.isValid():
                return
            
            # 限制文件大小，避免处理超大文件
            max_file_size = 512 * 1024  # 512KB
            file_size = os.path.getsize(file_path)
            if file_size > max_file_size:
                print(f"文件过大，部分处理: {file_path} ({file_size/1024:.1f}KB)")
                # 对大文件只读取前面部分
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read(max_file_size)
                    content += "\n\n[文件过大，未显示完整内容...]"
            else:
                # 读取完整文件内容
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
            
            # 搜索关键词
            content_lower = content.lower()
            if keyword.lower() in content_lower:
                # 提取关键词周围的上下文
                match_text = self._extract_context(content, keyword)
                
                # 对过长的内容进行截断，避免存储和显示过多内容
                MAX_CONTENT_LENGTH = 200000  # 限制最大内容长度为200KB
                if len(content) > MAX_CONTENT_LENGTH:
                    content = content[:MAX_CONTENT_LENGTH] + "\n\n[内容过长，已截断显示...]"
                    
                results.append(SearchResultItem(entry_date, content, match_text))
        except UnicodeDecodeError:
            print(f"无法解码文件: {file_path} (可能是二进制文件)")
        except Exception as e:
            print(f"在文件 {file_path} 中搜索时出错: {e}")
            
    def _extract_context(self, content, keyword, context_chars=40):
        """从文本中提取关键词周围的上下文，限制上下文长度"""
        content_lower = content.lower()
        keyword_lower = keyword.lower()
        
        # 限制搜索长度，避免处理超长文本
        MAX_SEARCH_TEXT = 100000  # 最多搜索10万字符
        if len(content) > MAX_SEARCH_TEXT:
            search_content = content[:MAX_SEARCH_TEXT]
            search_content_lower = search_content.lower()
        else:
            search_content = content
            search_content_lower = content_lower
        
        pos = search_content_lower.find(keyword_lower)
        if pos < 0:
            return "..."
            
        # 计算上下文的起始和结束位置
        start = max(0, pos - context_chars)
        end = min(len(search_content), pos + len(keyword) + context_chars)
        
        # 提取上下文
        context = search_content[start:end]
        
        # 添加省略号指示这是内容的一部分
        if start > 0:
            context = "..." + context
        if end < len(search_content):
            context = context + "..."
            
        return context

# --- Main Execution ---
if __name__ == '__main__':
    app = QApplication(sys.argv)
    mainWin = DiaryApp()
    mainWin.show()
    sys.exit(app.exec())