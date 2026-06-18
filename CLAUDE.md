# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Calendar Diary** desktop application built with **PyQt6 + Qt Quick/QML**. It provides a responsive calendar-based diary UI with plain-text editing, automatic file management, full-text search, in-page find, and a light/dark theme toggle that defaults to dark mode.

The `cpp/` directory contains a Qt/C++ port built with Qt Widgets and xmake. It keeps the same diary storage layout and core behavior, and release builds package a single-file exe with `windeployqt` plus Enigma Virtual Box.

The `rust/` directory contains a Rust + Tauri port. It uses a static framework-free frontend and a Tauri command backend, keeps the same diary storage layout, and builds a no-bundle `calendarNote.exe`.

## Core Architecture

### Main Application Structure
- **`main.py`** - Single Python entry point containing:
  - `DiaryBackend` - QObject backend exposed to QML via properties, slots, and signals
  - `SearchResultItem` / `SearchResultModel` - Search result data structures for QML `ListView`
  - `main()` - Creates `QApplication`, enforces the single-instance launch guard, applies Qt Quick Controls style, loads the icon, and starts `QQmlApplicationEngine`
- **`qml/Main.qml`** - Main UI containing:
  - Responsive dual-pane / single-column layout
  - Calendar sidebar with month navigation and entry dots
  - Plain-text editor card
  - Global search popup and in-page search popup
  - Reusable local components such as `AppButton`, `AppTextField`, `AppCheckBox`, and `AppBadge`
- **`cpp/src/main.cpp`** - Qt/C++ Widgets port containing the window, diary file IO, date switching, auto-save, search, in-page find, theme persistence, calendar entry dots, and single-instance activation.
- **`cpp/xmake.lua`** - xmake build script derived from `cpp/xmake.ref.lua`; release builds deploy Qt runtime files and generate `calendarNote_single.exe`.
- **`rust/frontend/index.html`** - Static Tauri frontend containing the responsive calendar UI, editor, search dialog, in-page find panel, theme toggle, and unsaved-change dialog.
- **`rust/src-tauri/src/main.rs`** - Rust backend commands for diary file IO, legacy migration, full-text search, monthly entry scanning, theme persistence, and single-instance activation.
- **`rust/src-tauri/tauri.conf.json`** - Tauri 2 configuration with `bundle.active=false` and `withGlobalTauri=true`.

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
- **Single instance**: Re-launching the app activates the existing main window instead of opening a second one
- **Performance optimization**: Debounced search, batch highlighting, text length limits

## Development Commands

### Running the Application
```bash
python main.py
```

Running the command again while the app is already open activates the existing main window.

### Building Resources
```bash
python compile_resources.py  # Compiles resources.qrc to resources_rc.py
```

### Creating Executable
```bash
python build_with_nuitka.py  # Creates standalone executable using Nuitka
```

### Building the Qt/C++ Port
```bash
cd cpp
xmake f -m release -y
xmake -y  # outputs build/windows/x64/release/calendarNote_single.exe
```

Set `QT_DIR` before running xmake if Qt is not installed in the default path used by `cpp/xmake.lua`.

### Running and Building the Rust/Tauri Port
```bash
cd rust
npm install
npm run dev
npm run build:no-bundle  # outputs src-tauri/target/release/calendarNote.exe
npm run build:tiny       # no bundle + UPX compression when UPX is installed
```

Rust backend checks:
```bash
cd rust/src-tauri
cargo test
```

## Technical Details

### Dependencies
- **PyQt6** - Main GUI framework
- **Tauri 2** - Rust/WebView2 port under `rust/`
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
├── cpp/                   # Qt/C++ port and xmake packaging
│   ├── xmake.lua
│   └── src/main.cpp
├── rust/                  # Rust/Tauri port
│   ├── frontend/index.html
│   └── src-tauri/src/main.rs
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
