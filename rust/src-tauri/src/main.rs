#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use serde::Serialize;
use std::{
    collections::BTreeMap,
    env, fs, io,
    path::{Path, PathBuf},
};
use tauri::Manager;

const TITLE_BASE: &str = "日历笔记本";
const DIARY_DIR: &str = "diary_entries";
const MAX_SEARCH_RESULTS: usize = 100;
const MAX_SEARCHABLE_FILE_SIZE: u64 = 1024 * 1024;
const MAX_PREVIEW_FILE_SIZE: u64 = 512 * 1024;
const MAX_CONTENT_LENGTH: usize = 200_000;

#[derive(Clone)]
struct Backend {
    base_dir: PathBuf,
    settings_path: PathBuf,
}

#[derive(Serialize)]
struct EntryResponse {
    content: String,
    path: String,
}

#[derive(Serialize)]
struct SearchResult {
    date: String,
    content: String,
    match_text: String,
}

#[derive(Serialize)]
struct Settings {
    theme_mode: String,
}

#[tauri::command]
fn get_settings(backend: tauri::State<'_, Backend>) -> Settings {
    Settings {
        theme_mode: read_theme(&backend.settings_path),
    }
}

#[tauri::command]
fn set_theme(backend: tauri::State<'_, Backend>, theme_mode: String) -> Result<(), String> {
    let theme = if theme_mode.trim().eq_ignore_ascii_case("light") {
        "light"
    } else {
        "dark"
    };
    if let Some(parent) = backend.settings_path.parent() {
        fs::create_dir_all(parent).map_err(error_text)?;
    }
    fs::write(&backend.settings_path, theme).map_err(error_text)
}

#[tauri::command]
fn load_entry(
    backend: tauri::State<'_, Backend>,
    iso_date: String,
) -> Result<EntryResponse, String> {
    valid_iso(&iso_date).ok_or_else(|| "无效日期".to_string())?;
    let path = filename_for_date(&backend.base_dir, &iso_date).map_err(error_text)?;
    let content = match fs::read_to_string(&path) {
        Ok(text) => text,
        Err(error) if error.kind() == io::ErrorKind::NotFound => String::new(),
        Err(error) => return Err(error_text(error)),
    };
    Ok(EntryResponse {
        content,
        path: relative_diary_path(&iso_date),
    })
}

#[tauri::command]
fn save_entry(
    backend: tauri::State<'_, Backend>,
    iso_date: String,
    content: String,
) -> Result<EntryResponse, String> {
    valid_iso(&iso_date).ok_or_else(|| "无效日期".to_string())?;
    let path = filename_for_date(&backend.base_dir, &iso_date).map_err(error_text)?;
    let should_save = !content.trim().is_empty() || path.exists();
    if should_save {
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent).map_err(error_text)?;
        }
        fs::write(&path, content).map_err(error_text)?;
    }
    Ok(EntryResponse {
        content: String::new(),
        path: relative_diary_path(&iso_date),
    })
}

#[tauri::command]
fn month_entries(
    backend: tauri::State<'_, Backend>,
    year: i32,
    month: u32,
) -> Result<Vec<String>, String> {
    if !(1..=12).contains(&month) {
        return Ok(Vec::new());
    }
    let mut dates = Vec::new();
    let month_dir = backend
        .base_dir
        .join(DIARY_DIR)
        .join(format!("{year:04}"))
        .join(format!("{month:02}"));
    scan_month_dir(&month_dir, year, month, &mut dates);

    let old_dir = backend.base_dir.join(DIARY_DIR);
    let prefix = format!("{year:04}-{month:02}-");
    if let Ok(entries) = fs::read_dir(old_dir) {
        for entry in entries.flatten() {
            let name = entry.file_name().to_string_lossy().into_owned();
            if name.starts_with(&prefix)
                && valid_diary_filename(&name)
                && non_empty_file(&entry.path())
            {
                dates.push(name.trim_end_matches(".txt").to_string());
            }
        }
    }
    dates.sort();
    dates.dedup();
    Ok(dates)
}

#[tauri::command]
fn search_entries(
    backend: tauri::State<'_, Backend>,
    keyword: String,
) -> Result<Vec<SearchResult>, String> {
    let keyword = keyword.trim().to_string();
    if keyword.is_empty() {
        return Ok(Vec::new());
    }
    let lower_keyword = keyword.to_lowercase();
    let mut results = Vec::new();
    for path in collect_all_diary_files(&backend.base_dir.join(DIARY_DIR)).map_err(error_text)? {
        if results.len() >= MAX_SEARCH_RESULTS {
            break;
        }
        if fs::metadata(&path).map(|m| m.len()).unwrap_or(0) > MAX_SEARCHABLE_FILE_SIZE {
            continue;
        }
        if let Some(result) = search_in_file(&path, &lower_keyword) {
            results.push(result);
        }
    }
    results.sort_by(|a, b| b.date.cmp(&a.date));
    results.truncate(MAX_SEARCH_RESULTS);
    Ok(results)
}

#[tauri::command]
fn exit_app(app: tauri::AppHandle) {
    app.exit(0);
}

fn main() {
    let backend = Backend {
        base_dir: project_base_dir(),
        settings_path: settings_path(),
    };

    tauri::Builder::default()
        .manage(backend)
        .plugin(tauri_plugin_single_instance::init(|app, _args, _cwd| {
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.unminimize();
                let _ = window.show();
                let _ = window.set_focus();
            }
        }))
        .invoke_handler(tauri::generate_handler![
            get_settings,
            set_theme,
            load_entry,
            save_entry,
            month_entries,
            search_entries,
            exit_app
        ])
        .run(tauri::generate_context!())
        .unwrap_or_else(|error| eprintln!("{TITLE_BASE} 启动失败：{error}"));
}

fn read_theme(path: &Path) -> String {
    match fs::read_to_string(path) {
        Ok(value) if value.trim().eq_ignore_ascii_case("light") => "light".to_string(),
        _ => "dark".to_string(),
    }
}

fn settings_path() -> PathBuf {
    if let Some(appdata) = env::var_os("APPDATA") {
        return PathBuf::from(appdata)
            .join("calendarNote")
            .join("calendarNote")
            .join("settings.txt");
    }
    project_base_dir().join(".calendar_note_settings")
}

fn project_base_dir() -> PathBuf {
    let cwd = env::current_dir().unwrap_or_else(|_| PathBuf::from("."));
    for dir in cwd.ancestors() {
        if dir.join(DIARY_DIR).exists() || dir.join("icon.ico").exists() {
            return dir.to_path_buf();
        }
    }
    cwd
}

fn relative_diary_path(iso_date: &str) -> String {
    format!(
        "{}/{}/{}/{}.txt",
        DIARY_DIR,
        &iso_date[0..4],
        &iso_date[5..7],
        iso_date
    )
}

fn new_path(base: &Path, iso_date: &str) -> PathBuf {
    base.join(relative_diary_path(iso_date))
}

fn legacy_path(base: &Path, iso_date: &str) -> PathBuf {
    base.join(DIARY_DIR).join(format!("{iso_date}.txt"))
}

fn filename_for_date(base: &Path, iso_date: &str) -> io::Result<PathBuf> {
    let new_file = new_path(base, iso_date);
    let old_file = legacy_path(base, iso_date);
    if old_file.is_file() && !new_file.exists() {
        if let Some(parent) = new_file.parent() {
            fs::create_dir_all(parent)?;
        }
        fs::copy(old_file, &new_file)?;
    }
    Ok(new_file)
}

fn scan_month_dir(dir: &Path, year: i32, month: u32, dates: &mut Vec<String>) {
    if let Ok(entries) = fs::read_dir(dir) {
        for entry in entries.flatten() {
            let name = entry.file_name().to_string_lossy().into_owned();
            if !valid_diary_filename(&name) || !non_empty_file(&entry.path()) {
                continue;
            }
            let iso = name.trim_end_matches(".txt");
            if let Some((entry_year, entry_month, _)) = valid_iso(iso) {
                if entry_year == year && entry_month == month {
                    dates.push(iso.to_string());
                }
            }
        }
    }
}

fn collect_all_diary_files(base: &Path) -> io::Result<Vec<PathBuf>> {
    let mut files = BTreeMap::<String, PathBuf>::new();
    collect_recursively(base, &mut files)?;
    Ok(files.into_values().collect())
}

fn collect_recursively(dir: &Path, files: &mut BTreeMap<String, PathBuf>) -> io::Result<()> {
    if !dir.is_dir() {
        return Ok(());
    }
    for entry in fs::read_dir(dir)? {
        let entry = entry?;
        let path = entry.path();
        if path.is_dir() {
            collect_recursively(&path, files)?;
            continue;
        }
        let name = entry.file_name().to_string_lossy().into_owned();
        if !valid_diary_filename(&name) {
            continue;
        }
        match files.get(&name) {
            Some(existing) if path.components().count() <= existing.components().count() => {}
            _ => {
                files.insert(name, path);
            }
        }
    }
    Ok(())
}

fn search_in_file(path: &Path, keyword: &str) -> Option<SearchResult> {
    let file_name = path.file_name()?.to_string_lossy();
    let date = file_name.strip_suffix(".txt")?.to_string();
    valid_iso(&date)?;
    let meta = fs::metadata(path).ok()?;
    let bytes = fs::read(path).ok()?;
    let take = bytes.len().min(MAX_PREVIEW_FILE_SIZE as usize);
    let mut content = String::from_utf8_lossy(&bytes[..take]).into_owned();
    if meta.len() > MAX_PREVIEW_FILE_SIZE {
        content.push_str("\n\n[文件较大，预览已截断...]");
    }
    if !content.to_lowercase().contains(keyword) {
        return None;
    }
    if content.len() > MAX_CONTENT_LENGTH {
        content.truncate(previous_char_boundary(&content, MAX_CONTENT_LENGTH));
        content.push_str("\n\n[内容过长，已截断显示...]");
    }
    Some(SearchResult {
        date,
        match_text: extract_context(&content, keyword, 42),
        content,
    })
}

fn extract_context(content: &str, keyword: &str, context_chars: usize) -> String {
    let lower = content.to_lowercase();
    let Some(pos) = lower.find(keyword) else {
        return String::new();
    };
    let start = previous_char_boundary(content, pos.saturating_sub(context_chars));
    let end = next_char_boundary(
        content,
        (pos + keyword.len() + context_chars).min(content.len()),
    );
    let mut snippet = content[start..end].replace('\n', " ").trim().to_string();
    if start > 0 {
        snippet.insert_str(0, "...");
    }
    if end < content.len() {
        snippet.push_str("...");
    }
    snippet
}

fn previous_char_boundary(text: &str, mut index: usize) -> usize {
    index = index.min(text.len());
    while index > 0 && !text.is_char_boundary(index) {
        index -= 1;
    }
    index
}

fn next_char_boundary(text: &str, mut index: usize) -> usize {
    index = index.min(text.len());
    while index < text.len() && !text.is_char_boundary(index) {
        index += 1;
    }
    index
}

fn valid_diary_filename(name: &str) -> bool {
    name.strip_suffix(".txt").and_then(valid_iso).is_some()
}

fn non_empty_file(path: &Path) -> bool {
    fs::metadata(path).map(|m| m.len() > 0).unwrap_or(false)
}

fn valid_iso(value: &str) -> Option<(i32, u32, u32)> {
    if value.len() != 10 || &value[4..5] != "-" || &value[7..8] != "-" {
        return None;
    }
    let year = value[0..4].parse::<i32>().ok()?;
    let month = value[5..7].parse::<u32>().ok()?;
    let day = value[8..10].parse::<u32>().ok()?;
    if year < 1 || !(1..=12).contains(&month) {
        return None;
    }
    let max_day = match month {
        1 | 3 | 5 | 7 | 8 | 10 | 12 => 31,
        4 | 6 | 9 | 11 => 30,
        2 if is_leap_year(year) => 29,
        2 => 28,
        _ => return None,
    };
    (1..=max_day).contains(&day).then_some((year, month, day))
}

fn is_leap_year(year: i32) -> bool {
    (year % 4 == 0 && year % 100 != 0) || year % 400 == 0
}

fn error_text(error: impl std::fmt::Display) -> String {
    error.to_string()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn validates_iso_dates() {
        assert!(valid_iso("2024-02-29").is_some());
        assert!(valid_iso("2023-02-29").is_none());
        assert!(valid_iso("2026-13-01").is_none());
    }

    #[test]
    fn keeps_diary_path_compatible() {
        assert_eq!(
            relative_diary_path("2026-06-18"),
            "diary_entries/2026/06/2026-06-18.txt"
        );
    }

    #[test]
    fn extracts_match_context() {
        let text = "hello\ncalendar note search world";
        assert_eq!(extract_context(text, "note", 6), "...endar note searc...");
    }
}
