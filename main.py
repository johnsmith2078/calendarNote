from __future__ import annotations

import html
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtCore import (
    QAbstractListModel,
    QByteArray,
    QDate,
    QModelIndex,
    QObject,
    QSettings,
    QTimer,
    Qt,
    QUrl,
    pyqtProperty,
    pyqtSignal,
    pyqtSlot,
)
from PyQt6.QtGui import QColor, QIcon, QPalette
from PyQt6.QtQml import QQmlApplicationEngine
from PyQt6.QtWidgets import QApplication, QMessageBox

TITLE_BASE = "日历笔记本"
SETTINGS_ORGANIZATION = "calendarNote"
SETTINGS_APPLICATION = "calendarNote"
SETTINGS_KEY_THEME_MODE = "ui/theme_mode"
THEME_MODE_LIGHT = "light"
THEME_MODE_DARK = "dark"
DEFAULT_THEME_MODE = THEME_MODE_DARK
MAX_SEARCH_RESULTS = 100
MAX_SEARCHABLE_FILE_SIZE = 1024 * 1024
MAX_PREVIEW_FILE_SIZE = 512 * 1024
MAX_CONTENT_LENGTH = 200_000
APP_THEME_PALETTES = {
    THEME_MODE_DARK: {
        "window": "#09090B",
        "surface": "#18181B",
        "base": "#111827",
        "text": "#FAFAFA",
        "muted_text": "#A1A1AA",
        "button": "#18181B",
        "highlight": "#F4F4F5",
        "highlighted_text": "#09090B",
        "bright_text": "#FFFFFF",
        "disabled_text": "#71717A",
        "disabled_surface": "#18181B",
        "disabled_highlight": "#3F3F46",
        "tooltip": "#111827",
        "shadow": "#000000",
    },
    THEME_MODE_LIGHT: {
        "window": "#FAFAFA",
        "surface": "#FFFFFF",
        "base": "#FCFCFD",
        "text": "#18181B",
        "muted_text": "#71717A",
        "button": "#FFFFFF",
        "highlight": "#18181B",
        "highlighted_text": "#FAFAFA",
        "bright_text": "#FFFFFF",
        "disabled_text": "#A1A1AA",
        "disabled_surface": "#F4F4F5",
        "disabled_highlight": "#D4D4D8",
        "tooltip": "#FFFFFF",
        "shadow": "#A1A1AA",
    },
}
WEEKDAY_LABELS = {
    1: "周一",
    2: "周二",
    3: "周三",
    4: "周四",
    5: "周五",
    6: "周六",
    7: "周日",
}


@dataclass(slots=True)
class SearchResultItem:
    """全局搜索结果。"""

    date: QDate
    content: str
    match_text: str


class SearchResultModel(QAbstractListModel):
    """供 QML 使用的搜索结果模型。"""

    DateRole = Qt.ItemDataRole.UserRole + 1
    DateLabelRole = Qt.ItemDataRole.UserRole + 2
    MatchTextRole = Qt.ItemDataRole.UserRole + 3
    ContentRole = Qt.ItemDataRole.UserRole + 4
    DisplayRole = Qt.ItemDataRole.UserRole + 5

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._results: list[SearchResultItem] = []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._results)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._results)):
            return None

        item = self._results[index.row()]
        date_text = item.date.toString("yyyy-MM-dd")
        display_text = item.match_text or ""
        if len(display_text) > 80:
            display_text = display_text[:77] + "..."

        if role == self.DateRole:
            return date_text
        if role == self.DateLabelRole:
            return date_text
        if role == self.MatchTextRole:
            return display_text
        if role == self.ContentRole:
            return item.content
        if role in (self.DisplayRole, Qt.ItemDataRole.DisplayRole):
            return f"{date_text}  {display_text}" if display_text else date_text
        return None

    def roleNames(self) -> dict[int, QByteArray]:
        return {
            self.DateRole: QByteArray(b"date"),
            self.DateLabelRole: QByteArray(b"dateLabel"),
            self.MatchTextRole: QByteArray(b"matchText"),
            self.ContentRole: QByteArray(b"content"),
            self.DisplayRole: QByteArray(b"display"),
        }

    def set_results(self, results: list[SearchResultItem]) -> None:
        self.beginResetModel()
        self._results = list(results)
        self.endResetModel()

    def get_result(self, index: int) -> SearchResultItem | None:
        if 0 <= index < len(self._results):
            return self._results[index]
        return None

    def clear(self) -> None:
        self.set_results([])


class DiaryBackend(QObject):
    """QML 界面使用的日记后端。"""

    currentDateChanged = pyqtSignal()
    currentDateDisplayChanged = pyqtSignal()
    currentContentChanged = pyqtSignal()
    currentEntryPathChanged = pyqtSignal()
    todayLabelChanged = pyqtSignal()
    autoSaveEnabledChanged = pyqtSignal()
    autoSaveStatusTextChanged = pyqtSignal()
    saveStateTextChanged = pyqtSignal()
    windowTitleChanged = pyqtSignal()
    statusMessageChanged = pyqtSignal()
    searchBusyChanged = pyqtSignal()
    searchResultCountTextChanged = pyqtSignal()
    searchPreviewContentChanged = pyqtSignal()
    searchPreviewDateChanged = pyqtSignal()
    searchPreviewRichTextChanged = pyqtSignal()
    calendarVersionChanged = pyqtSignal()
    themeModeChanged = pyqtSignal()
    searchCompleted = pyqtSignal(bool, str)
    windowCloseApproved = pyqtSignal()

    def __init__(self, app: QApplication):
        super().__init__()
        self._app = app
        self._current_date = QDate.currentDate()
        self._last_system_date = QDate.currentDate()
        self._diary_folder_base = "diary_entries"
        self._old_diary_folder = "diary_entries"
        self._current_content = ""
        self._last_saved_content = ""
        self._content_modified = False
        self._auto_save_enabled = True
        self._auto_save_interval = 30_000
        self._is_auto_saving = False
        self._last_edit_time = time.time()
        self._status_message = ""
        self._search_busy = False
        self._search_result_count_text = "找到 0 个结果"
        self._search_preview_content = ""
        self._search_preview_date = ""
        self._search_keyword = ""
        self._calendar_version = 0
        self._month_entry_cache: dict[tuple[int, int], set[str]] = {}
        self._search_results_model = SearchResultModel(self)
        self._settings = QSettings(SETTINGS_ORGANIZATION, SETTINGS_APPLICATION)
        self._theme_mode = self._normalize_theme_mode(
            self._settings.value(SETTINGS_KEY_THEME_MODE, DEFAULT_THEME_MODE, type=str)
        )

        self._auto_save_timer = QTimer(self)
        self._auto_save_timer.setInterval(self._auto_save_interval)
        self._auto_save_timer.timeout.connect(self.auto_save)

        self._date_change_timer = QTimer(self)
        self._date_change_timer.setInterval(60_000)
        self._date_change_timer.timeout.connect(self.check_for_date_update)

        self._status_timer = QTimer(self)
        self._status_timer.setSingleShot(True)
        self._status_timer.timeout.connect(self.clearStatusMessage)

        self._apply_application_theme()
        self.ensure_base_diary_folder()
        self.load_entry_for_date(self._current_date)
        self._ensure_month_cache(self._current_date.year(), self._current_date.month())
        self._bump_calendar_version()

        if self._auto_save_enabled:
            self._auto_save_timer.start()
        self._date_change_timer.start()

    @pyqtProperty(str, notify=currentDateChanged)
    def currentDate(self) -> str:
        return self._current_date.toString("yyyy-MM-dd")

    @pyqtProperty(str, notify=currentDateDisplayChanged)
    def currentDateDisplay(self) -> str:
        return self._format_date_display(self._current_date)

    @pyqtProperty(str, notify=currentContentChanged)
    def currentContent(self) -> str:
        return self._current_content

    @pyqtProperty(str, notify=currentEntryPathChanged)
    def currentEntryPath(self) -> str:
        return self._relative_new_path_for_date(self._current_date)

    @pyqtProperty(str, notify=todayLabelChanged)
    def todayLabel(self) -> str:
        return f"今天 · {self._last_system_date.toString('yyyy-MM-dd')}"

    @pyqtProperty(str, notify=themeModeChanged)
    def themeMode(self) -> str:
        return self._theme_mode

    @pyqtProperty(bool, notify=autoSaveEnabledChanged)
    def autoSaveEnabled(self) -> bool:
        return self._auto_save_enabled

    @pyqtProperty(str, notify=autoSaveStatusTextChanged)
    def autoSaveStatusText(self) -> str:
        if self._is_auto_saving:
            return "自动保存：保存中…"
        if self._auto_save_enabled:
            return f"自动保存：已开启（{self._auto_save_interval // 1000} 秒）"
        return "自动保存：已关闭"

    @pyqtProperty(str, notify=saveStateTextChanged)
    def saveStateText(self) -> str:
        return "未保存更改" if self._content_modified else "已保存"

    @pyqtProperty(str, notify=windowTitleChanged)
    def windowTitle(self) -> str:
        suffix = " *" if self._content_modified else ""
        return f"{TITLE_BASE} · {self.currentDate}{suffix}"

    @pyqtProperty(str, notify=statusMessageChanged)
    def statusMessage(self) -> str:
        return self._status_message

    @pyqtProperty(bool, notify=searchBusyChanged)
    def searchBusy(self) -> bool:
        return self._search_busy

    @pyqtProperty(str, notify=searchResultCountTextChanged)
    def searchResultCountText(self) -> str:
        return self._search_result_count_text

    @pyqtProperty(str, notify=searchPreviewContentChanged)
    def searchPreviewContent(self) -> str:
        return self._search_preview_content

    @pyqtProperty(str, notify=searchPreviewDateChanged)
    def searchPreviewDate(self) -> str:
        return self._search_preview_date

    @pyqtProperty(str, notify=searchPreviewRichTextChanged)
    def searchPreviewRichText(self) -> str:
        return self._build_highlighted_preview_html(self._search_preview_content, self._search_keyword)

    @pyqtProperty(int, notify=calendarVersionChanged)
    def calendarVersion(self) -> int:
        return self._calendar_version

    @pyqtProperty(str, constant=True)
    def monospaceFamily(self) -> str:
        return "Consolas"

    @pyqtProperty(QObject, constant=True)
    def searchResultsModel(self) -> QObject:
        return self._search_results_model

    @pyqtSlot(str)
    def updateContent(self, text: str) -> None:
        if text == self._current_content:
            return

        self._current_content = text
        self._last_edit_time = time.time()
        self._set_content_modified(text != self._last_saved_content)

    @pyqtSlot()
    def saveCurrentEntry(self) -> None:
        self.save_entry_for_date(self._current_date, status_text="已保存")

    @pyqtSlot()
    def toggleAutoSave(self) -> None:
        self._set_auto_save_enabled(not self._auto_save_enabled)
        state_text = "已开启" if self._auto_save_enabled else "已关闭"
        self._set_status(f"自动保存{state_text}", 2000)

    @pyqtSlot()
    def toggleTheme(self) -> None:
        next_mode = THEME_MODE_LIGHT if self._theme_mode == THEME_MODE_DARK else THEME_MODE_DARK
        self._set_theme_mode(next_mode, announce=True)

    @pyqtSlot(str)
    def selectDate(self, iso_date: str) -> None:
        target = QDate.fromString(iso_date, "yyyy-MM-dd")
        if not target.isValid() or target == self._current_date:
            return
        self._select_date(target)

    @pyqtSlot(result=bool)
    def returnToToday(self) -> bool:
        today = QDate.currentDate()
        if today == self._current_date:
            self._ensure_month_cache(today.year(), today.month())
            return True
        return self._select_date(today)

    @pyqtSlot()
    def requestWindowClose(self) -> None:
        if not self._confirm_pending_changes(
            title="退出确认",
            message="当前日记尚未保存，是否在退出前保存？",
        ):
            return
        self.windowCloseApproved.emit()

    @pyqtSlot()
    def auto_save(self) -> None:
        if not self._auto_save_enabled or not self._content_modified or self._is_auto_saving:
            return

        if time.time() - self._last_edit_time < 2.5:
            return

        self._is_auto_saving = True
        self.autoSaveStatusTextChanged.emit()
        try:
            saved = self.save_entry_for_date(self._current_date, status_text="自动保存完成")
            if saved:
                self._last_edit_time = time.time()
        finally:
            self._is_auto_saving = False
            self.autoSaveStatusTextChanged.emit()

    @pyqtSlot(int, int)
    def preloadMonth(self, year: int, month_zero_based: int) -> None:
        month = month_zero_based + 1
        if year < 1 or month < 1 or month > 12:
            return
        self._ensure_month_cache(year, month)
        self._bump_calendar_version()

    @pyqtSlot(str, result=bool)
    def hasEntryForDate(self, iso_date: str) -> bool:
        date = QDate.fromString(iso_date, "yyyy-MM-dd")
        if not date.isValid():
            return False

        cache_key = (date.year(), date.month())
        cached = self._month_entry_cache.get(cache_key)
        if cached is not None:
            return iso_date in cached
        return self.date_has_entry(date)

    @pyqtSlot(str)
    def performGlobalSearch(self, keyword: str) -> None:
        keyword = keyword.strip()
        if not keyword:
            QMessageBox.information(None, "搜索提示", "请输入要搜索的关键词")
            return

        self._set_search_keyword(keyword)

        if not self.save_entry_for_date(self._current_date, status_text=""):
            return

        self._set_search_busy(True)
        self._set_status(f"正在搜索“{keyword}”...", 0)
        self._app.processEvents()

        try:
            results = self.search_diary_entries(keyword)
        except Exception as exc:  # pragma: no cover - 防御性处理
            self._set_search_busy(False)
            self.clearStatusMessage()
            QMessageBox.critical(None, "搜索错误", f"搜索过程中发生错误：\n{exc}")
            return

        self._set_search_busy(False)
        self._search_results_model.set_results(results)
        self._search_result_count_text = f"找到 {len(results)} 个结果"
        self.searchResultCountTextChanged.emit()

        if results:
            self.selectSearchResult(0)
            self._set_status(f"找到 {len(results)} 个结果", 2500)
            self.searchCompleted.emit(True, keyword)
            return

        self.selectSearchResult(-1)
        self.clearStatusMessage()
        QMessageBox.information(None, "搜索结果", f"未找到包含“{keyword}”的日记")
        self.searchCompleted.emit(False, keyword)

    @pyqtSlot(int)
    def selectSearchResult(self, index: int) -> None:
        item = self._search_results_model.get_result(index)
        if item is None:
            if self._search_preview_content:
                self._search_preview_content = ""
                self.searchPreviewContentChanged.emit()
                self.searchPreviewRichTextChanged.emit()
            if self._search_preview_date:
                self._search_preview_date = ""
                self.searchPreviewDateChanged.emit()
            return

        content = item.content
        date_text = item.date.toString("yyyy-MM-dd")
        if content != self._search_preview_content:
            self._search_preview_content = content
            self.searchPreviewContentChanged.emit()
            self.searchPreviewRichTextChanged.emit()
        if date_text != self._search_preview_date:
            self._search_preview_date = date_text
            self.searchPreviewDateChanged.emit()

    @pyqtSlot(int)
    def openSearchResult(self, index: int) -> None:
        item = self._search_results_model.get_result(index)
        if item is None:
            return
        self._select_date(item.date)

    @pyqtSlot()
    def clearStatusMessage(self) -> None:
        if not self._status_message:
            return
        self._status_message = ""
        self.statusMessageChanged.emit()

    @pyqtSlot()
    def check_for_date_update(self) -> None:
        current_system_date = QDate.currentDate()
        if current_system_date == self._last_system_date:
            return

        previous_system_date = self._last_system_date
        self._last_system_date = current_system_date
        self.todayLabelChanged.emit()

        if self._current_date == previous_system_date:
            if self._content_modified:
                self.save_entry_for_date(self._current_date, status_text="")
            self._current_date = current_system_date
            self._emit_date_related_signals()
            self.load_entry_for_date(self._current_date)
            self._ensure_month_cache(self._current_date.year(), self._current_date.month())
            self._bump_calendar_version()
            self._set_status(f"已切换到今天 {self.currentDate}", 2000)
        else:
            self._ensure_month_cache(current_system_date.year(), current_system_date.month())
            self._bump_calendar_version()

    def ensure_base_diary_folder(self) -> None:
        if os.path.isdir(self._diary_folder_base):
            return
        try:
            os.makedirs(self._diary_folder_base, exist_ok=True)
        except OSError as exc:
            QMessageBox.critical(
                None,
                "错误",
                f"无法创建日记目录：\n{self._diary_folder_base}\n\n{exc}",
            )

    def _select_date(self, target: QDate) -> bool:
        if target == self._current_date:
            return True
        if not self._confirm_pending_changes(
            title="未保存内容",
            message="当前日记尚未保存，是否先保存再切换日期？",
        ):
            return False

        self._current_date = target
        self._emit_date_related_signals()
        self.load_entry_for_date(target)
        self._ensure_month_cache(target.year(), target.month())
        self._bump_calendar_version()
        return True

    def _confirm_pending_changes(self, title: str, message: str) -> bool:
        if not self._content_modified:
            return True

        reply = QMessageBox.question(
            None,
            title,
            message,
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save,
        )
        if reply == QMessageBox.StandardButton.Cancel:
            return False
        if reply == QMessageBox.StandardButton.Save:
            return self.save_entry_for_date(self._current_date, status_text="已保存")
        return True

    def _emit_date_related_signals(self) -> None:
        self.currentDateChanged.emit()
        self.currentDateDisplayChanged.emit()
        self.currentEntryPathChanged.emit()
        self.windowTitleChanged.emit()

    def _set_content_modified(self, modified: bool) -> None:
        if modified == self._content_modified:
            return
        self._content_modified = modified
        self.saveStateTextChanged.emit()
        self.windowTitleChanged.emit()

    def _set_auto_save_enabled(self, enabled: bool) -> None:
        if enabled == self._auto_save_enabled:
            return
        self._auto_save_enabled = enabled
        if enabled:
            self._auto_save_timer.start()
        else:
            self._auto_save_timer.stop()
        self.autoSaveEnabledChanged.emit()
        self.autoSaveStatusTextChanged.emit()

    def _normalize_theme_mode(self, theme_mode: str | None) -> str:
        if isinstance(theme_mode, str) and theme_mode.strip().lower() == THEME_MODE_LIGHT:
            return THEME_MODE_LIGHT
        return THEME_MODE_DARK

    def _set_theme_mode(self, theme_mode: str, announce: bool = False) -> None:
        normalized_mode = self._normalize_theme_mode(theme_mode)
        if normalized_mode == self._theme_mode:
            return

        self._theme_mode = normalized_mode
        self._settings.setValue(SETTINGS_KEY_THEME_MODE, normalized_mode)
        self._settings.sync()
        self._apply_application_theme()
        self.themeModeChanged.emit()

        if announce:
            label = "深色模式" if normalized_mode == THEME_MODE_DARK else "浅色模式"
            self._set_status(f"已切换到{label}", 2000)

    def _build_application_palette(self, theme_mode: str) -> QPalette:
        colors = APP_THEME_PALETTES[theme_mode]
        palette = QPalette()
        role_map = {
            QPalette.ColorRole.Window: "window",
            QPalette.ColorRole.WindowText: "text",
            QPalette.ColorRole.Base: "base",
            QPalette.ColorRole.AlternateBase: "surface",
            QPalette.ColorRole.ToolTipBase: "tooltip",
            QPalette.ColorRole.ToolTipText: "text",
            QPalette.ColorRole.Text: "text",
            QPalette.ColorRole.Button: "button",
            QPalette.ColorRole.ButtonText: "text",
            QPalette.ColorRole.BrightText: "bright_text",
            QPalette.ColorRole.Highlight: "highlight",
            QPalette.ColorRole.HighlightedText: "highlighted_text",
            QPalette.ColorRole.PlaceholderText: "muted_text",
            QPalette.ColorRole.Light: "surface",
            QPalette.ColorRole.Midlight: "base",
            QPalette.ColorRole.Dark: "window",
            QPalette.ColorRole.Mid: "base",
            QPalette.ColorRole.Shadow: "shadow",
        }
        for role, key in role_map.items():
            palette.setColor(role, QColor(colors[key]))

        palette.setColor(
            QPalette.ColorGroup.Disabled,
            QPalette.ColorRole.WindowText,
            QColor(colors["disabled_text"]),
        )
        palette.setColor(
            QPalette.ColorGroup.Disabled,
            QPalette.ColorRole.Text,
            QColor(colors["disabled_text"]),
        )
        palette.setColor(
            QPalette.ColorGroup.Disabled,
            QPalette.ColorRole.ButtonText,
            QColor(colors["disabled_text"]),
        )
        palette.setColor(
            QPalette.ColorGroup.Disabled,
            QPalette.ColorRole.PlaceholderText,
            QColor(colors["disabled_text"]),
        )
        palette.setColor(
            QPalette.ColorGroup.Disabled,
            QPalette.ColorRole.Base,
            QColor(colors["disabled_surface"]),
        )
        palette.setColor(
            QPalette.ColorGroup.Disabled,
            QPalette.ColorRole.Button,
            QColor(colors["disabled_surface"]),
        )
        palette.setColor(
            QPalette.ColorGroup.Disabled,
            QPalette.ColorRole.Highlight,
            QColor(colors["disabled_highlight"]),
        )
        palette.setColor(
            QPalette.ColorGroup.Disabled,
            QPalette.ColorRole.HighlightedText,
            QColor(colors["text"]),
        )
        return palette

    def _apply_application_theme(self) -> None:
        colors = APP_THEME_PALETTES[self._theme_mode]
        self._app.setPalette(self._build_application_palette(self._theme_mode))
        self._app.setStyleSheet(
            "QToolTip {"
            f" color: {colors['text']};"
            f" background-color: {colors['tooltip']};"
            f" border: 1px solid {colors['base']};"
            " padding: 4px 8px;"
            " }"
        )

    def _set_status(self, message: str, timeout_ms: int) -> None:
        if message != self._status_message:
            self._status_message = message
            self.statusMessageChanged.emit()
        self._status_timer.stop()
        if message and timeout_ms > 0:
            self._status_timer.start(timeout_ms)

    def _set_search_busy(self, busy: bool) -> None:
        if busy == self._search_busy:
            return
        self._search_busy = busy
        self.searchBusyChanged.emit()

    def _set_search_keyword(self, keyword: str) -> None:
        if keyword == self._search_keyword:
            return
        self._search_keyword = keyword
        self.searchPreviewRichTextChanged.emit()

    def _bump_calendar_version(self) -> None:
        self._calendar_version += 1
        self.calendarVersionChanged.emit()

    def _format_date_display(self, date: QDate) -> str:
        weekday = WEEKDAY_LABELS.get(date.dayOfWeek(), "")
        return f"{date.toString('yyyy-MM-dd')} · {weekday}"

    def _new_path_for_date(self, date: QDate) -> str:
        return os.path.join(
            self._diary_folder_base,
            date.toString("yyyy"),
            date.toString("MM"),
            f"{date.toString('yyyy-MM-dd')}.txt",
        )

    def _relative_new_path_for_date(self, date: QDate) -> str:
        return self._new_path_for_date(date).replace("\\", "/")

    def _legacy_path_for_date(self, date: QDate) -> str:
        return os.path.join(self._old_diary_folder, f"{date.toString('yyyy-MM-dd')}.txt")

    def get_filename_for_date(self, date: QDate) -> str:
        new_file = self._new_path_for_date(date)
        old_file = self._legacy_path_for_date(date)

        if os.path.isfile(old_file) and not os.path.exists(new_file):
            try:
                os.makedirs(os.path.dirname(new_file), exist_ok=True)
                with open(old_file, "r", encoding="utf-8") as src:
                    legacy_content = src.read()
                with open(new_file, "w", encoding="utf-8") as dst:
                    dst.write(legacy_content)
            except OSError as exc:
                print(f"按需迁移旧日记失败：{exc}")
        return new_file

    def load_entry_for_date(self, date: QDate) -> None:
        filename = self.get_filename_for_date(date)
        content = ""
        try:
            if os.path.exists(filename):
                with open(filename, "r", encoding="utf-8") as file:
                    content = file.read()
        except OSError as exc:
            QMessageBox.warning(None, "加载错误", f"无法加载 {date.toString('yyyy-MM-dd')} 的日记：\n\n{exc}")

        content_changed = content != self._current_content
        self._current_content = content
        self._last_saved_content = content
        if content_changed:
            self.currentContentChanged.emit()
        self._set_content_modified(False)

    def save_entry_for_date(self, date: QDate, status_text: str = "已保存") -> bool:
        target_folder = os.path.dirname(self._new_path_for_date(date))
        filename = self.get_filename_for_date(date)
        raw_content = self._current_content
        stripped_content = raw_content.strip()
        should_save = bool(stripped_content) or os.path.exists(filename)

        if not should_save:
            self._last_saved_content = raw_content
            self._set_content_modified(False)
            return True

        try:
            os.makedirs(target_folder, exist_ok=True)
            with open(filename, "w", encoding="utf-8") as file:
                file.write(raw_content)
        except OSError as exc:
            QMessageBox.warning(None, "保存错误", f"无法保存 {date.toString('yyyy-MM-dd')} 的日记：\n\n{exc}")
            return False

        self._last_saved_content = raw_content
        self._set_content_modified(False)
        self._invalidate_month_cache(date.year(), date.month())
        if status_text:
            self._set_status(f"{status_text} · {date.toString('yyyy-MM-dd')}", 2000)
        return True

    def _invalidate_month_cache(self, year: int, month: int) -> None:
        self._month_entry_cache.pop((year, month), None)
        self._bump_calendar_version()

    def _ensure_month_cache(self, year: int, month: int) -> set[str]:
        key = (year, month)
        if key not in self._month_entry_cache:
            self._month_entry_cache[key] = self._scan_month_entries(year, month)
        return self._month_entry_cache[key]

    def _scan_month_entries(self, year: int, month: int) -> set[str]:
        dates: set[str] = set()
        month_folder = os.path.join(self._diary_folder_base, f"{year:04d}", f"{month:02d}")

        if os.path.isdir(month_folder):
            try:
                for file_name in os.listdir(month_folder):
                    if not self._is_valid_diary_filename(file_name):
                        continue
                    file_path = os.path.join(month_folder, file_name)
                    if not os.path.isfile(file_path):
                        continue
                    if os.path.getsize(file_path) <= 0:
                        continue
                    entry_date = QDate.fromString(file_name[:-4], "yyyy-MM-dd")
                    if entry_date.isValid() and entry_date.year() == year and entry_date.month() == month:
                        dates.add(file_name[:-4])
            except OSError as exc:
                print(f"扫描目录失败 {month_folder}: {exc}")

        if os.path.isdir(self._old_diary_folder):
            prefix = f"{year:04d}-{month:02d}-"
            try:
                for file_name in os.listdir(self._old_diary_folder):
                    if not file_name.startswith(prefix) or not self._is_valid_diary_filename(file_name):
                        continue
                    file_path = os.path.join(self._old_diary_folder, file_name)
                    if os.path.isfile(file_path) and os.path.getsize(file_path) > 0:
                        dates.add(file_name[:-4])
            except OSError as exc:
                print(f"扫描旧目录失败 {self._old_diary_folder}: {exc}")

        return dates

    def date_has_entry(self, date: QDate) -> bool:
        if not date.isValid():
            return False

        new_file = self._new_path_for_date(date)
        if os.path.isfile(new_file):
            try:
                return os.path.getsize(new_file) > 0
            except OSError:
                return False

        old_file = self._legacy_path_for_date(date)
        if os.path.isfile(old_file):
            try:
                return os.path.getsize(old_file) > 0
            except OSError:
                return False
        return False

    def search_diary_entries(self, keyword: str) -> list[SearchResultItem]:
        results: list[SearchResultItem] = []
        normalized_keyword = keyword.lower()
        diary_files = self._collect_all_diary_files()
        total_files = len(diary_files)

        for index, file_path in enumerate(diary_files, start=1):
            if index == 1 or index % 8 == 0:
                self._set_status(f"正在搜索… {index}/{total_files}", 0)
                self._app.processEvents()

            try:
                file_size = os.path.getsize(file_path)
            except OSError:
                continue

            if file_size > MAX_SEARCHABLE_FILE_SIZE:
                continue

            self._search_in_file(file_path, normalized_keyword, results)
            if len(results) >= MAX_SEARCH_RESULTS:
                break

        results.sort(key=lambda item: item.date, reverse=True)
        return results[:MAX_SEARCH_RESULTS]

    def _collect_all_diary_files(self) -> list[str]:
        files_by_name: dict[str, str] = {}

        if not os.path.isdir(self._diary_folder_base):
            return []

        for root, _, filenames in os.walk(self._diary_folder_base):
            for file_name in filenames:
                if not self._is_valid_diary_filename(file_name):
                    continue
                file_path = os.path.join(root, file_name)
                existing = files_by_name.get(file_name)
                if existing is None:
                    files_by_name[file_name] = file_path
                    continue

                existing_depth = existing.count(os.sep)
                current_depth = file_path.count(os.sep)
                if current_depth > existing_depth:
                    files_by_name[file_name] = file_path

        return sorted(files_by_name.values())

    def _is_valid_diary_filename(self, filename: str) -> bool:
        if not filename.endswith(".txt"):
            return False
        date = QDate.fromString(filename[:-4], "yyyy-MM-dd")
        return date.isValid()

    def _search_in_file(
        self,
        file_path: str,
        keyword: str,
        results: list[SearchResultItem],
    ) -> None:
        file_name = os.path.basename(file_path)
        entry_date = QDate.fromString(file_name[:-4], "yyyy-MM-dd")
        if not entry_date.isValid():
            return

        try:
            file_size = os.path.getsize(file_path)
            max_bytes = min(file_size, MAX_PREVIEW_FILE_SIZE)
            with open(file_path, "r", encoding="utf-8", errors="ignore") as file:
                content = file.read(max_bytes)
            if file_size > MAX_PREVIEW_FILE_SIZE:
                content += "\n\n[文件较大，预览已截断...]"
        except OSError:
            return

        lowered_content = content.lower()
        if keyword not in lowered_content:
            return

        if len(content) > MAX_CONTENT_LENGTH:
            content = content[:MAX_CONTENT_LENGTH] + "\n\n[内容过长，已截断显示...]"

        results.append(
            SearchResultItem(
                date=entry_date,
                content=content,
                match_text=self._extract_context(content, keyword),
            )
        )

    def _extract_context(self, content: str, keyword: str, context_chars: int = 42) -> str:
        lowered_content = content.lower()
        lowered_keyword = keyword.lower()
        position = lowered_content.find(lowered_keyword)
        if position < 0:
            return ""

        start = max(0, position - context_chars)
        end = min(len(content), position + len(keyword) + context_chars)
        snippet = content[start:end].replace("\n", " ").strip()
        if start > 0:
            snippet = "..." + snippet
        if end < len(content):
            snippet += "..."
        return snippet

    def _build_highlighted_preview_html(self, content: str, keyword: str) -> str:
        if not content:
            return ""

        pattern = re.compile(re.escape(keyword), re.IGNORECASE) if keyword else None
        segments: list[str] = []
        last_end = 0

        if pattern is not None:
            for match in pattern.finditer(content):
                start, end = match.span()
                if start > last_end:
                    segments.append(self._escape_preview_html(content[last_end:start]))
                segments.append(
                    "<span style=\"background-color:#FDE68A;color:#7C2D12;font-weight:600;\">"
                    f"{self._escape_preview_html(content[start:end])}"
                    "</span>"
                )
                last_end = end

        if last_end < len(content):
            segments.append(self._escape_preview_html(content[last_end:]))

        body = "".join(segments) if segments else self._escape_preview_html(content)
        return f"<div style=\"margin:0;\">{body}</div>"

    def _escape_preview_html(self, text: str) -> str:
        escaped = html.escape(text.replace("\t", "    "))
        while "  " in escaped:
            escaped = escaped.replace("  ", "&nbsp; ")
        return escaped.replace("\n", "<br/>")


def resolve_runtime_path(*parts: str) -> Path:
    base_dir = Path(__file__).resolve().parent
    return base_dir.joinpath(*parts)


def load_application_icon(app: QApplication) -> None:
    candidates = [
        Path.cwd() / "icon.ico",
        resolve_runtime_path("icon.ico"),
    ]
    for path in candidates:
        if path.exists():
            app.setWindowIcon(QIcon(str(path)))
            return


def main() -> int:
    if os.environ.get("QT_QUICK_CONTROLS_STYLE", "").lower() in {"", "windows", "macos", "ios", "android"}:
        os.environ["QT_QUICK_CONTROLS_STYLE"] = "Basic"
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setOrganizationName(SETTINGS_ORGANIZATION)
    app.setApplicationName(SETTINGS_APPLICATION)
    app.setApplicationDisplayName(TITLE_BASE)
    load_application_icon(app)

    backend = DiaryBackend(app)
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("backend", backend)

    main_qml = resolve_runtime_path("qml", "Main.qml")
    engine.load(QUrl.fromLocalFile(str(main_qml)))
    if not engine.rootObjects():
        return 1
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
