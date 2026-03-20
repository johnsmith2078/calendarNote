# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Calendar Diary** desktop application built with **PyQt6 + Qt Quick/QML**. It provides a responsive calendar-based diary UI with plain-text editing, automatic file management, full-text search, in-page find, and a light/dark theme toggle that defaults to dark mode.

## Core Architecture

### Main Application Structure
- **`main.py`** - Single Python entry point containing:
  - `DiaryBackend` - QObject backend exposed to QML via properties, slots, and signals
  - `SearchResultItem` / `SearchResultModel` - Search result data structures for QML `ListView`
  - `main()` - Creates `QApplication`, applies Qt Quick Controls style, loads the icon, and starts `QQmlApplicationEngine`
- **`qml/Main.qml`** - Main UI containing:
  - Responsive dual-pane / single-column layout
  - Calendar sidebar with month navigation and entry dots
  - Plain-text editor card
  - Global search popup and in-page search popup
  - Reusable local components such as `AppButton`, `AppTextField`, `AppCheckBox`, and `AppBadge`

### File Storage System
- **Structure**: `diary_entries/YYYY/MM/YYYY-MM-DD.txt`
- **Migration**: Automatic on-demand migration from old flat structure to hierarchical structure
- **Encoding**: UTF-8 text files for diary entries
- **Auto-save**: Content is automatically saved when switching dates or closing application
- **Theme preference**: UI theme mode is persisted through `QSettings`

### Key Features Implementation
- **Calendar highlighting**: Visual indicators for dates with diary entries
- **Search functionality**: Full-text search across all diary entries with context preview
- **In-page search**: Ctrl+F search within current diary entry with highlighting
- **Content tracking**: Tracks unsaved changes with visual indicators
- **Theme system**: Light/dark theme switch exposed from `DiaryBackend` to QML, defaulting to dark mode
- **Performance optimization**: Debounced search, batch highlighting, text length limits

## Development Commands

### Running the Application
```bash
python main.py
```

### Building Resources
```bash
python compile_resources.py  # Compiles resources.qrc to resources_rc.py
```

### Creating Executable
```bash
python build_with_nuitka.py  # Creates standalone executable using Nuitka
```

## Technical Details

### Dependencies
- **PyQt6** - Main GUI framework
- **Standard library**: os, sys, time for file operations and performance monitoring

### Resource Management
- **Icon**: `icon.ico` (Windows icon format)
- **Resource compilation**: Uses pyrcc6 or pyside6-rcc for Qt resource compilation
- **Asset inclusion**: Icon embedded in executable during build

### Performance Considerations
- **Search optimization**: File size limits, result count limits, debounced input
- **UI responsiveness**: Batch operations with disabled updates, progress indicators
- **Memory management**: Content length limits for large files, selective loading

### Font System
- **Monospace fonts**: Prioritizes Consolas, falls back to system monospace fonts
- **Global consistency**: Same font family used across calendar, text editor, and dialogs

## File Organization

```
├── main.py                 # Python backend entry point
├── qml/Main.qml           # Main Qt Quick UI
├── icon.ico               # Application icon
├── resources.qrc          # Qt resource file definition
├── resources_rc.py        # Compiled Qt resources (generated)
├── build_with_nuitka.py   # Build script for executable
├── compile_resources.py   # Resource compilation script
└── diary_entries/         # Diary storage directory
    └── YYYY/
        └── MM/
            └── YYYY-MM-DD.txt
```

## Important Implementation Notes

### Date Handling
- Uses `QDate` for all date operations
- Automatic migration from old storage format when files are accessed
- Calendar widget integration with custom highlighting system

### Search System
- **Global search**: Searches all diary files with keyword highlighting
- **In-page search**: Real-time search within current entry
- **Context extraction**: Shows surrounding text for search matches
- **Performance safeguards**: File size limits, search result limits

### Text Processing
- **Plain text enforcement**: Custom paste handling to remove formatting
- **UTF-8 encoding**: Consistent text encoding across all operations
- **Content modification tracking**: Real-time tracking of unsaved changes

### UI/UX Features
- **Keyboard shortcuts**: Ctrl+F (find), F3 (find next), Shift+F3 (find previous), Escape (close)
- **Status feedback**: Progress indicators during search operations
- **Confirmation dialogs**: Unsaved changes protection on exit
- **Calendar navigation**: Month/year navigation with persistent highlighting
- **Theme toggle**: Header action switches between dark and light themes; default is dark mode
