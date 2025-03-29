import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout,
    QCalendarWidget, QTextEdit, QMessageBox, QPushButton, QVBoxLayout, QSizePolicy
)
from PyQt6.QtCore import QDate, Qt, QDir, QResource
from PyQt6.QtGui import QCloseEvent, QFont, QIcon

class DiaryApp(QMainWindow):
    """
    A simple diary application with a calendar using PyQt6.
    """
    def __init__(self):
        super().__init__()
        self.current_date = QDate.currentDate()
        self.diary_folder = f"diary_entries/{self.current_date.toString('yyyy')}/{self.current_date.toString('MM')}"  # Store entries in a folder by month
        self.old_diary_folder = "diary_entries"  # 旧版日志存储路径
        self.initUI()
        self.ensure_diary_folder()
        self.migrate_old_entries()  # 迁移旧版日志
        self.load_entry_for_date(self.current_date)  # Load today's entry initially

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

    def ensure_diary_folder(self):
        """Create the diary_entries folder if it doesn't exist."""
        if not QDir(self.diary_folder).exists():
            try:
                QDir().mkpath(self.diary_folder)
                print(f"Created directory: {self.diary_folder}")
            except Exception as e:
                QMessageBox.critical(self, "错误 (Error)", f"无法创建日记存储目录:\n{self.diary_folder}\n\n{e}")
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
                    new_folder = f"diary_entries/{entry_date.toString('yyyy')}/{entry_date.toString('MM')}"
                    if not QDir(new_folder).exists():
                        QDir().mkpath(new_folder)
                    
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

    def get_filename_for_date(self, date: QDate) -> str:
        """Generate the filename for a given date (e.g., YYYY-MM-DD.txt)."""
        new_file = os.path.join(self.diary_folder, date.toString("yyyy-MM-dd") + ".txt")
        
        # 兼容旧版日志存储方式
        old_file = os.path.join(self.old_diary_folder, date.toString("yyyy-MM-dd") + ".txt")
        
        # 检查是否存在旧版日志，如果存在且新版不存在，则迁移
        if os.path.exists(old_file) and not os.path.exists(new_file):
            # 确保新目录存在
            year_month_folder = f"diary_entries/{date.toString('yyyy')}/{date.toString('MM')}"
            if not QDir(year_month_folder).exists():
                QDir().mkpath(year_month_folder)
                
            # 复制内容
            try:
                with open(old_file, 'r', encoding='utf-8') as src:
                    content = src.read()
                    with open(new_file, 'w', encoding='utf-8') as dst:
                        dst.write(content)
                print(f"按需迁移日志: {old_file} -> {new_file}")
            except Exception as e:
                print(f"迁移文件时出错: {e}")
        
        # 始终返回新版路径
        return new_file

    def load_entry_for_date(self, date: QDate):
        """Load the diary entry for the specified date into the text editor."""
        filename = self.get_filename_for_date(date)
        try:
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    content = f.read()
                    self.text_edit.setPlainText(content)
                    print(f"Loaded entry for {date.toString('yyyy-MM-dd')}")
            else:
                self.text_edit.clear()  # No entry for this date
                print(f"No entry found for {date.toString('yyyy-MM-dd')}")
        except Exception as e:
            QMessageBox.warning(self, "加载错误 (Load Error)", f"无法加载日期 {date.toString('yyyy-MM-dd')} 的日记:\n\n{e}")
            self.text_edit.clear()

    def save_entry_for_date(self, date: QDate):
        """Save the current text editor content for the specified date."""
        filename = self.get_filename_for_date(date)
        content = self.text_edit.toPlainText().strip()  # Get text and remove leading/trailing whitespace

        # Decide whether to save empty content
        should_save = bool(content) or os.path.exists(filename)

        if not should_save:
            print(f"Skipping save for empty new entry: {date.toString('yyyy-MM-dd')}")
            return  # Don't create empty files for dates that never had an entry

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(self.text_edit.toPlainText())  # Save the exact content
            print(f"Saved entry for {date.toString('yyyy-MM-dd')}")
        except Exception as e:
            QMessageBox.warning(self, "保存错误 (Save Error)", f"无法保存日期 {date.toString('yyyy-MM-dd')} 的日记:\n\n{e}")

    def handle_date_change(self):
        """Called when the selected date in the calendar changes."""
        new_date = self.calendar.selectedDate()
        if new_date != self.current_date:
            print(f"Date changing from {self.current_date.toString('yyyy-MM-dd')} to {new_date.toString('yyyy-MM-dd')}")
            # 1. Save the entry for the *previous* date
            self.save_entry_for_date(self.current_date)

            # 2. Update the current date
            self.current_date = new_date

            # 3. Load the entry for the *new* date
            self.load_entry_for_date(self.current_date)

    def return_to_today(self):
        """Return the calendar to today's date when the 'Today' button is clicked."""
        self.calendar.setSelectedDate(QDate.currentDate())  # Set the selected date to today
        self.load_entry_for_date(QDate.currentDate())  # Load today's entry

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


# --- Main Execution ---
if __name__ == '__main__':
    app = QApplication(sys.argv)
    mainWin = DiaryApp()
    mainWin.show()
    sys.exit(app.exec())