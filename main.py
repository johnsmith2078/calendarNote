import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout,
    QCalendarWidget, QTextEdit, QMessageBox, QPushButton, QVBoxLayout, QSizePolicy
)
from PyQt6.QtCore import QDate, Qt, QDir, QResource, QDirIterator
from PyQt6.QtGui import QCloseEvent, QFont, QIcon, QTextCharFormat, QColor

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

        self.initUI()
        self.ensure_base_diary_folder() # 确保基础目录存在
        self.migrate_old_entries()  # 迁移旧版日志
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

        # 设置日历控件字体
        calendar_font = QFont()
        calendar_font.setPointSize(9)  # 设置字体大小
        self.calendar.setFont(calendar_font)

        # 设置日历控件大小
        self.calendar.setFixedWidth(350)
        self.calendar.setMinimumHeight(280)

        # 使用合适的尺寸策略
        self.calendar.setSizePolicy(
            QSizePolicy.Policy.Fixed,  # 水平方向固定
            QSizePolicy.Policy.Fixed   # 垂直方向固定
        )

        # 将按钮和日历加入垂直布局
        v_layout.addWidget(self.today_button)  # Add today button above calendar
        v_layout.addWidget(self.calendar)      # Add calendar below the button

        # --- Text Edit Widget ---
        self.text_edit = QTextEdit(self)
        self.text_edit.setPlaceholderText("请在此处输入您的日记内容...")
        font = self.text_edit.font()
        font.setPointSize(12)  # Set a slightly larger font
        self.text_edit.setFont(font)

        # --- Add widgets to main horizontal layout ---
        main_layout.addLayout(v_layout, 1)  # Add vertical layout (button + calendar)
        main_layout.addWidget(self.text_edit, 2)  # Add text editor to the right side

        # --- Connect Signals ---
        # selectionChanged fires when the user clicks a date
        self.calendar.selectionChanged.connect(self.handle_date_change)
        # currentPageChanged fires when the month/year view changes
        self.calendar.currentPageChanged.connect(self.update_calendar_highlighting)
        
        print("UI初始化完成，所有信号已连接")

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

    def migrate_old_entries(self):
        """检测并迁移旧版日志到新的分层目录结构中"""
        # 确保旧版目录存在
        if not QDir(self.old_diary_folder).exists():
            return

        # 获取旧版目录中的所有txt文件
        old_dir = QDir(self.old_diary_folder)
        old_dir.setNameFilters(["*.txt"])
        files = old_dir.entryList(QDir.Filter.Files)

        # 遍历所有旧版日志文件
        migrated_count = 0
        for file_name in files:
            # 解析文件名中的日期 (格式如: 2024-03-29.txt)
            try:
                date_str = file_name.replace(".txt", "")
                date_parts = date_str.split("-")
                
                if len(date_parts) == 3:
                    year, month, day = date_parts
                    entry_date = QDate(int(year), int(month), int(day))
                    
                    # 获取新旧文件路径
                    old_file_path = os.path.join(self.old_diary_folder, file_name)
                    
                    # 跳过已经在层级结构中的文件
                    if not os.path.isfile(old_file_path):
                        continue
                        
                    # 为此日期创建新目录
                    new_folder = os.path.join(self.diary_folder_base, entry_date.toString('yyyy'), entry_date.toString('MM'))
                    if not QDir(new_folder).exists():
                        if QDir().mkpath(new_folder):
                            print(f"为迁移创建了目录: {new_folder}") # 添加日志
                        else:
                             print(f"错误: 无法为迁移创建目录 {new_folder}") # 添加日志
                             continue # 跳过此文件

                    new_file_path = os.path.join(new_folder, file_name)
                    
                    # 如果新路径不存在，复制文件
                    if not os.path.exists(new_file_path):
                        with open(old_file_path, 'r', encoding='utf-8') as src:
                            content = src.read()
                            with open(new_file_path, 'w', encoding='utf-8') as dst:
                                dst.write(content)
                        migrated_count += 1
                        print(f"迁移日志: {old_file_path} -> {new_file_path}")
            except Exception as e:
                print(f"迁移文件 {file_name} 时出错: {e}")
                
        if migrated_count > 0:
            print(f"成功迁移 {migrated_count} 个旧版日志")
            self.update_calendar_highlighting() # 迁移后更新高亮

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
            
            # 保存后强制更新高亮
            print("保存后更新日历高亮...")
            self.update_calendar_highlighting()
            return True
        except Exception as e:
            error_msg = f"无法保存日期 {date.toString('yyyy-MM-dd')} 的日记:\n\n{e}"
            print(f"错误: {error_msg}")
            QMessageBox.warning(self, "保存错误 (Save Error)", error_msg)
            return False

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
        reply = QMessageBox.question(self, '退出确认 (Confirm Exit)',
                                     '您想在退出前保存当前日记吗？\n(Save current entry before exiting?)',
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
                                     QMessageBox.StandardButton.Yes)

        if reply == QMessageBox.StandardButton.Yes:
            self.save_entry_for_date(self.current_date)
            event.accept()  # Proceed with closing
        elif reply == QMessageBox.StandardButton.No:
            event.accept()  # Proceed with closing without saving
        else:
            event.ignore()  # Don't close the window

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


# --- Main Execution ---
if __name__ == '__main__':
    app = QApplication(sys.argv)
    mainWin = DiaryApp()
    mainWin.show()
    sys.exit(app.exec())