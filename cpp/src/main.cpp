#include <QtWidgets>
#include <QtNetwork/QLocalServer>
#include <QtNetwork/QLocalSocket>

#include <algorithm>

#ifdef Q_OS_WIN
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#endif

namespace {

const char* kTitleUtf8 = u8"日历笔记本";
const char* kOrganization = "calendarNote";
const char* kApplication = "calendarNote";
const char* kSingleInstanceServer = "calendarNote.calendarNote.single-instance";
const char* kThemeKey = "ui/theme_mode";

constexpr int kAutoSaveIntervalMs = 30000;
constexpr int kMaxSearchResults = 100;
constexpr qint64 kMaxSearchableFileSize = 1024 * 1024;
constexpr qint64 kMaxPreviewFileSize = 512 * 1024;
constexpr int kMaxContentLength = 200000;

QString u8s(const char* text)
{
    return QString::fromUtf8(text);
}

QString titleBase()
{
    return u8s(kTitleUtf8);
}

QString isoDate(const QDate& date)
{
    return date.toString(QStringLiteral("yyyy-MM-dd"));
}

QString weekdayLabel(const QDate& date)
{
    switch (date.dayOfWeek()) {
    case 1: return u8s(u8"周一");
    case 2: return u8s(u8"周二");
    case 3: return u8s(u8"周三");
    case 4: return u8s(u8"周四");
    case 5: return u8s(u8"周五");
    case 6: return u8s(u8"周六");
    case 7: return u8s(u8"周日");
    default: return {};
    }
}

QString formatDateDisplay(const QDate& date)
{
    return isoDate(date) + u8s(u8" · ") + weekdayLabel(date);
}

QString diaryBaseDir()
{
    return QStringLiteral("diary_entries");
}

QString newPathForDate(const QDate& date)
{
    return QDir(diaryBaseDir()).filePath(
        date.toString(QStringLiteral("yyyy")) + QLatin1Char('/') +
        date.toString(QStringLiteral("MM")) + QLatin1Char('/') +
        isoDate(date) + QStringLiteral(".txt"));
}

QString legacyPathForDate(const QDate& date)
{
    return QDir(diaryBaseDir()).filePath(isoDate(date) + QStringLiteral(".txt"));
}

bool ensureParentDir(const QString& filePath)
{
    return QDir().mkpath(QFileInfo(filePath).absolutePath());
}

bool validDiaryFileName(const QString& fileName)
{
    if (!fileName.endsWith(QStringLiteral(".txt"))) {
        return false;
    }
    return QDate::fromString(fileName.left(fileName.size() - 4), QStringLiteral("yyyy-MM-dd")).isValid();
}

QString readUtf8File(const QString& filePath, qint64 maxBytes = -1, bool* truncated = nullptr)
{
    if (truncated) {
        *truncated = false;
    }

    QFile file(filePath);
    if (!file.open(QIODevice::ReadOnly)) {
        return {};
    }

    const qint64 size = file.size();
    QByteArray bytes = maxBytes >= 0 ? file.read(qMin(size, maxBytes)) : file.readAll();
    if (truncated && maxBytes >= 0 && size > maxBytes) {
        *truncated = true;
    }
    return QString::fromUtf8(bytes);
}

bool writeUtf8File(const QString& filePath, const QString& text)
{
    if (!ensureParentDir(filePath)) {
        return false;
    }

    QFile file(filePath);
    if (!file.open(QIODevice::WriteOnly | QIODevice::Truncate)) {
        return false;
    }
    return file.write(text.toUtf8()) >= 0;
}

int pathDepth(const QString& filePath)
{
    return filePath.count(QLatin1Char('/')) + filePath.count(QLatin1Char('\\'));
}

QString monthKey(int year, int month)
{
    return QStringLiteral("%1-%2").arg(year, 4, 10, QLatin1Char('0')).arg(month, 2, 10, QLatin1Char('0'));
}

struct Theme {
    QColor window;
    QColor card;
    QColor elevated;
    QColor muted;
    QColor input;
    QColor border;
    QColor text;
    QColor secondaryText;
    QColor primary;
    QColor primaryText;
    QColor selection;
    QColor success;
    QColor danger;
    QColor info;
    QColor dot;
};

Theme themeFor(bool dark)
{
    if (dark) {
        return {
            QColor(QStringLiteral("#09090B")),
            QColor(QStringLiteral("#111827")),
            QColor(QStringLiteral("#18181B")),
            QColor(QStringLiteral("#18181B")),
            QColor(QStringLiteral("#3F3F46")),
            QColor(QStringLiteral("#27272A")),
            QColor(QStringLiteral("#FAFAFA")),
            QColor(QStringLiteral("#A1A1AA")),
            QColor(QStringLiteral("#FAFAFA")),
            QColor(QStringLiteral("#09090B")),
            QColor(QStringLiteral("#3F3F46")),
            QColor(QStringLiteral("#4ADE80")),
            QColor(QStringLiteral("#F87171")),
            QColor(QStringLiteral("#60A5FA")),
            QColor(QStringLiteral("#4ADE80")),
        };
    }
    return {
        QColor(QStringLiteral("#FAFAFA")),
        QColor(QStringLiteral("#FFFFFF")),
        QColor(QStringLiteral("#FCFCFD")),
        QColor(QStringLiteral("#F4F4F5")),
        QColor(QStringLiteral("#E4E4E7")),
        QColor(QStringLiteral("#E4E4E7")),
        QColor(QStringLiteral("#18181B")),
        QColor(QStringLiteral("#71717A")),
        QColor(QStringLiteral("#18181B")),
        QColor(QStringLiteral("#FAFAFA")),
        QColor(QStringLiteral("#D4D4D8")),
        QColor(QStringLiteral("#15803D")),
        QColor(QStringLiteral("#DC2626")),
        QColor(QStringLiteral("#2563EB")),
        QColor(QStringLiteral("#15803D")),
    };
}

void polish(QWidget* widget)
{
    widget->style()->unpolish(widget);
    widget->style()->polish(widget);
    widget->update();
}

struct SearchResult {
    QDate date;
    QString content;
    QString context;
};

class EntryCalendar : public QCalendarWidget {
public:
    explicit EntryCalendar(QWidget* parent = nullptr) : QCalendarWidget(parent) {}

    void setEntryDates(const QSet<QDate>& dates)
    {
        entryDates_ = dates;
        updateCells();
    }

    void setDotColor(const QColor& color)
    {
        dotColor_ = color;
        updateCells();
    }

protected:
    void paintCell(QPainter* painter, const QRect& rect, const QDate& date) const override
    {
        QCalendarWidget::paintCell(painter, rect, date);
        if (!entryDates_.contains(date)) {
            return;
        }

        painter->save();
        painter->setRenderHint(QPainter::Antialiasing, true);
        painter->setPen(Qt::NoPen);
        painter->setBrush(dotColor_);
        painter->drawEllipse(QPoint(rect.center().x(), rect.bottom() - 5), 3, 3);
        painter->restore();
    }

private:
    QSet<QDate> entryDates_;
    QColor dotColor_ = QColor(QStringLiteral("#4ADE80"));
};

class MainWindow : public QMainWindow {
public:
    explicit MainWindow(QWidget* parent = nullptr)
        : QMainWindow(parent),
          settings_(QString::fromLatin1(kOrganization), QString::fromLatin1(kApplication)),
          currentDate_(QDate::currentDate()),
          lastSystemDate_(QDate::currentDate())
    {
        darkMode_ = settings_.value(QString::fromLatin1(kThemeKey), QStringLiteral("dark")).toString() != QStringLiteral("light");
        lastEditMs_ = QDateTime::currentMSecsSinceEpoch();

        createUi();
        ensureBaseDiaryFolder();
        loadEntryForDate(currentDate_);
        refreshCalendarEntries();
        applyTheme();
        updateTexts();

        autoSaveTimer_.setParent(this);
        autoSaveTimer_.setInterval(kAutoSaveIntervalMs);
        connect(&autoSaveTimer_, &QTimer::timeout, this, [this] { autoSave(); });
        autoSaveTimer_.start();

        dateTimer_.setParent(this);
        dateTimer_.setInterval(60000);
        connect(&dateTimer_, &QTimer::timeout, this, [this] { checkForDateUpdate(); });
        dateTimer_.start();

        statusTimer_.setParent(this);
        statusTimer_.setSingleShot(true);
        connect(&statusTimer_, &QTimer::timeout, this, [this] { clearStatus(); });
    }

    void bringToFront()
    {
        if (isMinimized()) {
            showNormal();
        } else {
            show();
        }
        raise();
        activateWindow();
        activateNativeWindow(static_cast<quintptr>(winId()));
    }

protected:
    void closeEvent(QCloseEvent* event) override
    {
        if (!confirmPendingChanges(u8s(u8"退出确认"), u8s(u8"当前日记尚未保存，是否在退出前保存？"))) {
            event->ignore();
            return;
        }
        event->accept();
    }

private:
    static void activateNativeWindow(quintptr hwnd)
    {
#ifdef Q_OS_WIN
        if (!hwnd) {
            return;
        }
        HWND handle = reinterpret_cast<HWND>(hwnd);
        if (IsIconic(handle)) {
            ShowWindow(handle, SW_RESTORE);
        } else {
            ShowWindow(handle, SW_SHOW);
        }
        SetForegroundWindow(handle);
#else
        Q_UNUSED(hwnd);
#endif
    }

    void createUi()
    {
        resize(1320, 860);
        setMinimumSize(820, 620);

        auto* central = new QWidget(this);
        auto* mainLayout = new QVBoxLayout(central);
        mainLayout->setContentsMargins(22, 16, 22, 14);
        mainLayout->setSpacing(14);

        auto* header = new QHBoxLayout;
        header->setSpacing(12);
        auto* titleColumn = new QVBoxLayout;
        titleColumn->setSpacing(4);
        titleLabel_ = new QLabel(titleBase(), central);
        QFont titleFont = titleLabel_->font();
        titleFont.setPointSize(18);
        titleFont.setBold(true);
        titleLabel_->setFont(titleFont);
        subtitleLabel_ = new QLabel(u8s(u8"左侧导航与检索，右侧专注编辑。"), central);
        titleColumn->addWidget(titleLabel_);
        titleColumn->addWidget(subtitleLabel_);
        header->addLayout(titleColumn, 1);

        saveBadge_ = new QLabel(central);
        saveBadge_->setObjectName(QStringLiteral("saveBadge"));
        saveBadge_->setAlignment(Qt::AlignCenter);
        saveBadge_->setMinimumHeight(30);
        saveBadge_->setContentsMargins(10, 4, 10, 4);
        header->addWidget(saveBadge_);

        themeButton_ = new QPushButton(central);
        connect(themeButton_, &QPushButton::clicked, this, [this] { toggleTheme(); });
        header->addWidget(themeButton_);
        mainLayout->addLayout(header);

        splitter_ = new QSplitter(Qt::Horizontal, central);
        splitter_->setChildrenCollapsible(false);
        mainLayout->addWidget(splitter_, 1);

        auto* sidebar = new QFrame(splitter_);
        sidebar->setObjectName(QStringLiteral("card"));
        auto* sidebarLayout = new QVBoxLayout(sidebar);
        sidebarLayout->setContentsMargins(18, 18, 18, 18);
        sidebarLayout->setSpacing(14);

        auto* searchRow = new QHBoxLayout;
        searchEdit_ = new QLineEdit(sidebar);
        searchEdit_->setPlaceholderText(u8s(u8"搜索所有日记内容…"));
        searchButton_ = new QPushButton(u8s(u8"搜索"), sidebar);
        searchRow->addWidget(searchEdit_, 1);
        searchRow->addWidget(searchButton_);
        sidebarLayout->addLayout(searchRow);
        connect(searchEdit_, &QLineEdit::returnPressed, this, [this] { performGlobalSearch(); });
        connect(searchButton_, &QPushButton::clicked, this, [this] { performGlobalSearch(); });

        todayButton_ = new QPushButton(sidebar);
        connect(todayButton_, &QPushButton::clicked, this, [this] { returnToToday(); });
        sidebarLayout->addWidget(todayButton_);

        calendar_ = new EntryCalendar(sidebar);
        calendar_->setFirstDayOfWeek(Qt::Monday);
        calendar_->setGridVisible(false);
        calendar_->setVerticalHeaderFormat(QCalendarWidget::NoVerticalHeader);
        calendar_->setSelectedDate(currentDate_);
        sidebarLayout->addWidget(calendar_, 1);
        connect(calendar_, &QCalendarWidget::selectionChanged, this, [this] {
            selectDate(calendar_->selectedDate());
        });
        connect(calendar_, &QCalendarWidget::currentPageChanged, this, [this](int year, int month) {
            ensureMonthCache(year, month);
            refreshCalendarEntries();
        });

        auto* editorCard = new QFrame(splitter_);
        editorCard->setObjectName(QStringLiteral("card"));
        auto* editorLayout = new QVBoxLayout(editorCard);
        editorLayout->setContentsMargins(18, 18, 18, 18);
        editorLayout->setSpacing(12);

        auto* editorHeader = new QHBoxLayout;
        auto* editorTitleColumn = new QVBoxLayout;
        editorTitleColumn->setSpacing(4);
        dateLabel_ = new QLabel(editorCard);
        QFont dateFont = dateLabel_->font();
        dateFont.setPointSize(18);
        dateFont.setBold(true);
        dateLabel_->setFont(dateFont);
        pathLabel_ = new QLabel(editorCard);
        editorTitleColumn->addWidget(dateLabel_);
        editorTitleColumn->addWidget(pathLabel_);
        editorHeader->addLayout(editorTitleColumn, 1);

        saveButton_ = new QPushButton(u8s(u8"保存"), editorCard);
        autoSaveButton_ = new QPushButton(editorCard);
        findButton_ = new QPushButton(u8s(u8"页面内查找"), editorCard);
        editorHeader->addWidget(saveButton_);
        editorHeader->addWidget(autoSaveButton_);
        editorHeader->addWidget(findButton_);
        editorLayout->addLayout(editorHeader);
        connect(saveButton_, &QPushButton::clicked, this, [this] { saveCurrentEntry(); });
        connect(autoSaveButton_, &QPushButton::clicked, this, [this] { toggleAutoSave(); });
        connect(findButton_, &QPushButton::clicked, this, [this] { openFindDialog(); });

        editor_ = new QTextEdit(editorCard);
        editor_->setAcceptRichText(false);
        editor_->setLineWrapMode(QTextEdit::WidgetWidth);
        editor_->setPlaceholderText(u8s(u8"请在这里开始记录今天的想法、计划与回顾…"));
        QFont editorFont(QStringLiteral("Consolas"));
        editorFont.setPointSize(11);
        editor_->setFont(editorFont);
        editorLayout->addWidget(editor_, 1);
        connect(editor_, &QTextEdit::textChanged, this, [this] { onEditorTextChanged(); });

        splitter_->addWidget(sidebar);
        splitter_->addWidget(editorCard);
        splitter_->setStretchFactor(0, 0);
        splitter_->setStretchFactor(1, 1);
        splitter_->setSizes(QList<int>() << 390 << 900);

        auto* footer = new QHBoxLayout;
        statusLabel_ = new QLabel(central);
        statusLabel_->setTextInteractionFlags(Qt::TextSelectableByMouse);
        autoSaveLabel_ = new QLabel(central);
        footer->addWidget(statusLabel_, 1);
        footer->addWidget(autoSaveLabel_);
        mainLayout->addLayout(footer);

        setCentralWidget(central);

        auto* saveShortcut = new QShortcut(QKeySequence::Save, this);
        connect(saveShortcut, &QShortcut::activated, this, [this] { saveCurrentEntry(); });
        auto* findShortcut = new QShortcut(QKeySequence::Find, this);
        connect(findShortcut, &QShortcut::activated, this, [this] { openFindDialog(); });
        auto* nextShortcut = new QShortcut(QKeySequence(Qt::Key_F3), this);
        connect(nextShortcut, &QShortcut::activated, this, [this] { findNext(false); });
        auto* prevShortcut = new QShortcut(QKeySequence(QStringLiteral("Shift+F3")), this);
        connect(prevShortcut, &QShortcut::activated, this, [this] { findNext(true); });
        auto* autoSaveShortcut = new QShortcut(QKeySequence(QStringLiteral("Ctrl+Shift+A")), this);
        connect(autoSaveShortcut, &QShortcut::activated, this, [this] { toggleAutoSave(); });
    }

    void applyTheme()
    {
        const Theme t = themeFor(darkMode_);
        calendar_->setDotColor(t.dot);

        QPalette palette;
        palette.setColor(QPalette::Window, t.window);
        palette.setColor(QPalette::WindowText, t.text);
        palette.setColor(QPalette::Base, t.elevated);
        palette.setColor(QPalette::AlternateBase, t.muted);
        palette.setColor(QPalette::Text, t.text);
        palette.setColor(QPalette::Button, t.card);
        palette.setColor(QPalette::ButtonText, t.text);
        palette.setColor(QPalette::Highlight, t.primary);
        palette.setColor(QPalette::HighlightedText, t.primaryText);
        qApp->setPalette(palette);

        qApp->setStyleSheet(QStringLiteral(
            "QWidget { background:%1; color:%2; font-family:'Microsoft YaHei UI','Segoe UI',sans-serif; }"
            "QFrame#card { background:%3; border:1px solid %4; border-radius:8px; }"
            "QLabel { background:transparent; }"
            "QLabel#saveBadge { border-radius:8px; font-weight:600; }"
            "QLabel#saveBadge[state='saved'] { color:%5; background:%6; border:1px solid %5; }"
            "QLabel#saveBadge[state='dirty'] { color:%7; background:%6; border:1px solid %7; }"
            "QLineEdit, QTextEdit { background:%8; color:%2; border:1px solid %9; border-radius:8px; padding:8px; selection-background-color:%9; }"
            "QPushButton { background:%3; color:%2; border:1px solid %4; border-radius:8px; padding:8px 12px; font-weight:600; }"
            "QPushButton:hover { background:%6; }"
            "QPushButton:pressed { background:%9; }"
            "QCalendarWidget QWidget { background:%3; color:%2; }"
            "QCalendarWidget QToolButton { background:%3; color:%2; border:1px solid %4; border-radius:6px; padding:5px; }"
            "QCalendarWidget QAbstractItemView { background:%8; color:%2; selection-background-color:%1; selection-color:%2; border:1px solid %4; border-radius:8px; }"
            "QSplitter::handle { background:%1; }")
            .arg(t.window.name(), t.text.name(), t.card.name(), t.border.name(), t.success.name(),
                 t.muted.name(), t.danger.name(), t.elevated.name(), t.input.name()));

        subtitleLabel_->setStyleSheet(QStringLiteral("color:%1;").arg(t.secondaryText.name()));
        pathLabel_->setStyleSheet(QStringLiteral("color:%1;").arg(t.secondaryText.name()));
        statusLabel_->setStyleSheet(QStringLiteral("color:%1;").arg(t.secondaryText.name()));
        updateTexts();
    }

    void ensureBaseDiaryFolder()
    {
        if (!QDir().mkpath(diaryBaseDir())) {
            QMessageBox::critical(this, u8s(u8"错误"), u8s(u8"无法创建日记目录：\n") + diaryBaseDir());
        }
    }

    QString fileNameForDate(const QDate& date)
    {
        const QString newFile = newPathForDate(date);
        const QString oldFile = legacyPathForDate(date);
        if (QFileInfo::exists(oldFile) && !QFileInfo::exists(newFile)) {
            ensureParentDir(newFile);
            QFile::copy(oldFile, newFile);
        }
        return newFile;
    }

    void loadEntryForDate(const QDate& date)
    {
        const QString filePath = fileNameForDate(date);
        const QString content = QFileInfo::exists(filePath) ? readUtf8File(filePath) : QString();

        QSignalBlocker blocker(editor_);
        editor_->setPlainText(content);
        currentContent_ = content;
        lastSavedContent_ = content;
        setModified(false);
        updateTexts();
    }

    bool saveEntryForDate(const QDate& date, const QString& statusText = u8s(u8"已保存"))
    {
        currentContent_ = editor_->toPlainText();
        const QString filePath = fileNameForDate(date);
        const bool shouldSave = !currentContent_.trimmed().isEmpty() || QFileInfo::exists(filePath);

        if (!shouldSave) {
            lastSavedContent_ = currentContent_;
            setModified(false);
            return true;
        }

        if (!writeUtf8File(filePath, currentContent_)) {
            QMessageBox::warning(this, u8s(u8"保存错误"), u8s(u8"无法保存 ") + isoDate(date) + u8s(u8" 的日记。"));
            return false;
        }

        lastSavedContent_ = currentContent_;
        setModified(false);
        invalidateMonthCache(date.year(), date.month());
        if (!statusText.isEmpty()) {
            setStatus(statusText + u8s(u8" · ") + isoDate(date), 2000);
        }
        return true;
    }

    void saveCurrentEntry()
    {
        saveEntryForDate(currentDate_, u8s(u8"已保存"));
    }

    void onEditorTextChanged()
    {
        currentContent_ = editor_->toPlainText();
        lastEditMs_ = QDateTime::currentMSecsSinceEpoch();
        setModified(currentContent_ != lastSavedContent_);
        updateFindCount();
    }

    void setModified(bool modified)
    {
        if (modified_ == modified) {
            return;
        }
        modified_ = modified;
        updateTexts();
    }

    void updateTexts()
    {
        setWindowTitle(titleBase() + u8s(u8" · ") + isoDate(currentDate_) + (modified_ ? QStringLiteral(" *") : QString()));
        dateLabel_->setText(formatDateDisplay(currentDate_));
        pathLabel_->setText(newPathForDate(currentDate_).replace(QLatin1Char('\\'), QLatin1Char('/')));
        saveBadge_->setText(modified_ ? u8s(u8"未保存更改") : u8s(u8"已保存"));
        saveBadge_->setProperty("state", modified_ ? "dirty" : "saved");
        polish(saveBadge_);

        todayButton_->setText(u8s(u8"今天 · ") + isoDate(lastSystemDate_));
        themeButton_->setText(darkMode_ ? u8s(u8"切换浅色模式") : u8s(u8"切换深色模式"));
        autoSaveButton_->setText(autoSaveEnabled_ ? u8s(u8"关闭自动保存") : u8s(u8"开启自动保存"));
        autoSaveLabel_->setText(autoSaveEnabled_
            ? u8s(u8"自动保存：已开启（30 秒）")
            : u8s(u8"自动保存：已关闭"));
        const Theme t = themeFor(darkMode_);
        autoSaveLabel_->setStyleSheet(QStringLiteral("color:%1; font-weight:600;")
            .arg(autoSaveEnabled_ ? t.success.name() : t.danger.name()));

        statusLabel_->setText(statusMessage_.isEmpty()
            ? saveBadge_->text() + u8s(u8" · ") + pathLabel_->text()
            : statusMessage_);
    }

    bool selectDate(const QDate& target)
    {
        if (!target.isValid() || target == currentDate_) {
            return true;
        }
        if (!confirmPendingChanges(u8s(u8"未保存内容"), u8s(u8"当前日记尚未保存，是否先保存再切换日期？"))) {
            QSignalBlocker blocker(calendar_);
            calendar_->setSelectedDate(currentDate_);
            return false;
        }

        currentDate_ = target;
        {
            QSignalBlocker blocker(calendar_);
            calendar_->setSelectedDate(currentDate_);
        }
        loadEntryForDate(currentDate_);
        ensureMonthCache(currentDate_.year(), currentDate_.month());
        refreshCalendarEntries();
        updateTexts();
        return true;
    }

    bool returnToToday()
    {
        const QDate today = QDate::currentDate();
        if (today == currentDate_) {
            ensureMonthCache(today.year(), today.month());
            refreshCalendarEntries();
            return true;
        }
        return selectDate(today);
    }

    bool confirmPendingChanges(const QString& title, const QString& message)
    {
        if (!modified_) {
            return true;
        }

        const QMessageBox::StandardButton reply = QMessageBox::question(
            this,
            title,
            message,
            QMessageBox::Save | QMessageBox::Discard | QMessageBox::Cancel,
            QMessageBox::Save);

        if (reply == QMessageBox::Cancel) {
            return false;
        }
        if (reply == QMessageBox::Save) {
            return saveEntryForDate(currentDate_, u8s(u8"已保存"));
        }
        return true;
    }

    void toggleAutoSave()
    {
        autoSaveEnabled_ = !autoSaveEnabled_;
        setStatus(autoSaveEnabled_ ? u8s(u8"自动保存已开启") : u8s(u8"自动保存已关闭"), 2000);
        updateTexts();
    }

    void toggleTheme()
    {
        darkMode_ = !darkMode_;
        settings_.setValue(QString::fromLatin1(kThemeKey), darkMode_ ? QStringLiteral("dark") : QStringLiteral("light"));
        applyTheme();
        setStatus(darkMode_ ? u8s(u8"已切换到深色模式") : u8s(u8"已切换到浅色模式"), 1800);
    }

    void autoSave()
    {
        if (!autoSaveEnabled_ || !modified_ || isAutoSaving_) {
            return;
        }
        if (QDateTime::currentMSecsSinceEpoch() - lastEditMs_ < 2500) {
            return;
        }

        isAutoSaving_ = true;
        saveEntryForDate(currentDate_, u8s(u8"自动保存完成"));
        isAutoSaving_ = false;
    }

    void checkForDateUpdate()
    {
        const QDate systemDate = QDate::currentDate();
        if (systemDate == lastSystemDate_) {
            return;
        }

        const QDate previousSystemDate = lastSystemDate_;
        lastSystemDate_ = systemDate;
        if (currentDate_ == previousSystemDate) {
            if (modified_) {
                saveEntryForDate(currentDate_, QString());
            }
            currentDate_ = systemDate;
            {
                QSignalBlocker blocker(calendar_);
                calendar_->setSelectedDate(currentDate_);
            }
            loadEntryForDate(currentDate_);
            ensureMonthCache(currentDate_.year(), currentDate_.month());
            refreshCalendarEntries();
            setStatus(u8s(u8"已切换到今天 ") + isoDate(currentDate_), 2000);
        } else {
            ensureMonthCache(systemDate.year(), systemDate.month());
            refreshCalendarEntries();
        }
        updateTexts();
    }

    void setStatus(const QString& message, int timeoutMs)
    {
        statusMessage_ = message;
        updateTexts();
        statusTimer_.stop();
        if (!message.isEmpty() && timeoutMs > 0) {
            statusTimer_.start(timeoutMs);
        }
    }

    void clearStatus()
    {
        statusMessage_.clear();
        updateTexts();
    }

    QSet<QDate> ensureMonthCache(int year, int month)
    {
        const QString key = monthKey(year, month);
        if (!monthEntryCache_.contains(key)) {
            monthEntryCache_.insert(key, scanMonthEntries(year, month));
        }
        return monthEntryCache_.value(key);
    }

    void invalidateMonthCache(int year, int month)
    {
        monthEntryCache_.remove(monthKey(year, month));
        refreshCalendarEntries();
    }

    QSet<QDate> scanMonthEntries(int year, int month) const
    {
        QSet<QDate> dates;
        const QString prefix = QStringLiteral("%1-%2-").arg(year, 4, 10, QLatin1Char('0')).arg(month, 2, 10, QLatin1Char('0'));
        const QString monthFolder = QDir(diaryBaseDir()).filePath(
            QStringLiteral("%1/%2").arg(year, 4, 10, QLatin1Char('0')).arg(month, 2, 10, QLatin1Char('0')));

        const auto scanDir = [&dates, year, month](const QDir& dir, const QString& requiredPrefix) {
            const QFileInfoList files = dir.entryInfoList(QStringList() << QStringLiteral("*.txt"), QDir::Files);
            for (const QFileInfo& info : files) {
                const QString name = info.fileName();
                if (!requiredPrefix.isEmpty() && !name.startsWith(requiredPrefix)) {
                    continue;
                }
                if (!validDiaryFileName(name) || info.size() <= 0) {
                    continue;
                }
                const QDate date = QDate::fromString(name.left(name.size() - 4), QStringLiteral("yyyy-MM-dd"));
                if (date.isValid() && date.year() == year && date.month() == month) {
                    dates.insert(date);
                }
            }
        };

        QDir newDir(monthFolder);
        if (newDir.exists()) {
            scanDir(newDir, QString());
        }

        QDir oldDir(diaryBaseDir());
        if (oldDir.exists()) {
            scanDir(oldDir, prefix);
        }
        return dates;
    }

    void refreshCalendarEntries()
    {
        calendar_->setEntryDates(ensureMonthCache(calendar_->yearShown(), calendar_->monthShown()));
    }

    QStringList collectAllDiaryFiles() const
    {
        QHash<QString, QString> filesByName;
        QDir base(diaryBaseDir());
        if (!base.exists()) {
            return {};
        }

        QDirIterator it(diaryBaseDir(), QStringList() << QStringLiteral("*.txt"), QDir::Files, QDirIterator::Subdirectories);
        while (it.hasNext()) {
            const QString filePath = it.next();
            const QString fileName = QFileInfo(filePath).fileName();
            if (!validDiaryFileName(fileName)) {
                continue;
            }

            const QString existing = filesByName.value(fileName);
            if (existing.isEmpty() || pathDepth(filePath) > pathDepth(existing)) {
                filesByName.insert(fileName, filePath);
            }
        }

        QStringList files = filesByName.values();
        std::sort(files.begin(), files.end());
        return files;
    }

    QVector<SearchResult> searchDiaryEntries(const QString& keyword)
    {
        QVector<SearchResult> results;
        const QString loweredKeyword = keyword.toLower();
        const QStringList files = collectAllDiaryFiles();

        for (int i = 0; i < files.size() && results.size() < kMaxSearchResults; ++i) {
            if (i == 0 || i % 8 == 0) {
                setStatus(u8s(u8"正在搜索… ") + QString::number(i + 1) + QLatin1Char('/') + QString::number(files.size()), 0);
                qApp->processEvents();
            }

            const QFileInfo info(files.at(i));
            if (info.size() > kMaxSearchableFileSize) {
                continue;
            }

            SearchResult result;
            if (searchInFile(info.filePath(), keyword, loweredKeyword, &result)) {
                results.append(result);
            }
        }

        std::sort(results.begin(), results.end(), [](const SearchResult& a, const SearchResult& b) {
            return a.date > b.date;
        });
        if (results.size() > kMaxSearchResults) {
            results.resize(kMaxSearchResults);
        }
        return results;
    }

    bool searchInFile(const QString& filePath, const QString& keyword, const QString& loweredKeyword, SearchResult* result) const
    {
        const QString fileName = QFileInfo(filePath).fileName();
        const QDate date = QDate::fromString(fileName.left(fileName.size() - 4), QStringLiteral("yyyy-MM-dd"));
        if (!date.isValid()) {
            return false;
        }

        bool truncated = false;
        QString content = readUtf8File(filePath, kMaxPreviewFileSize, &truncated);
        if (truncated) {
            content += u8s(u8"\n\n[文件较大，预览已截断...]");
        }

        if (!content.toLower().contains(loweredKeyword)) {
            return false;
        }

        if (content.size() > kMaxContentLength) {
            content = content.left(kMaxContentLength) + u8s(u8"\n\n[内容过长，已截断显示...]");
        }

        result->date = date;
        result->content = content;
        result->context = extractContext(content, keyword);
        return true;
    }

    QString extractContext(const QString& content, const QString& keyword) const
    {
        const int contextChars = 42;
        const int position = content.toLower().indexOf(keyword.toLower());
        if (position < 0) {
            return {};
        }

        const int start = qMax(0, position - contextChars);
        const int end = qMin(content.size(), position + keyword.size() + contextChars);
        QString snippet = content.mid(start, end - start).replace(QLatin1Char('\n'), QLatin1Char(' ')).trimmed();
        if (start > 0) {
            snippet.prepend(QStringLiteral("..."));
        }
        if (end < content.size()) {
            snippet.append(QStringLiteral("..."));
        }
        return snippet;
    }

    QString highlightedHtml(const QString& content, const QString& keyword) const
    {
        if (keyword.isEmpty()) {
            return QStringLiteral("<pre style=\"white-space:pre-wrap;\">%1</pre>").arg(content.toHtmlEscaped());
        }

        QRegularExpression re(QRegularExpression::escape(keyword), QRegularExpression::CaseInsensitiveOption);
        QRegularExpressionMatchIterator it = re.globalMatch(content);
        QString html;
        int lastEnd = 0;
        while (it.hasNext()) {
            const QRegularExpressionMatch match = it.next();
            html += content.mid(lastEnd, match.capturedStart() - lastEnd).toHtmlEscaped();
            html += QStringLiteral("<span style=\"background:#FDE68A;color:#7C2D12;font-weight:600;\">");
            html += content.mid(match.capturedStart(), match.capturedLength()).toHtmlEscaped();
            html += QStringLiteral("</span>");
            lastEnd = match.capturedEnd();
        }
        html += content.mid(lastEnd).toHtmlEscaped();
        return QStringLiteral("<pre style=\"white-space:pre-wrap; font-family:Consolas,monospace;\">%1</pre>").arg(html);
    }

    void performGlobalSearch()
    {
        const QString keyword = searchEdit_->text().trimmed();
        if (keyword.isEmpty()) {
            QMessageBox::information(this, u8s(u8"搜索提示"), u8s(u8"请输入要搜索的关键词"));
            return;
        }

        if (!saveEntryForDate(currentDate_, QString())) {
            return;
        }

        setStatus(u8s(u8"正在搜索“") + keyword + u8s(u8"”…"), 0);
        QVector<SearchResult> results = searchDiaryEntries(keyword);
        clearStatus();

        if (results.isEmpty()) {
            QMessageBox::information(this, u8s(u8"搜索结果"), u8s(u8"未找到包含“") + keyword + u8s(u8"”的日记"));
            return;
        }

        showSearchResults(results, keyword);
    }

    void showSearchResults(const QVector<SearchResult>& results, const QString& keyword)
    {
        QDialog dialog(this);
        dialog.setWindowTitle(u8s(u8"搜索结果"));
        dialog.resize(980, 640);

        auto* layout = new QVBoxLayout(&dialog);
        auto* titleRow = new QHBoxLayout;
        auto* countLabel = new QLabel(u8s(u8"找到 ") + QString::number(results.size()) + u8s(u8" 个结果"), &dialog);
        QFont countFont = countLabel->font();
        countFont.setPointSize(14);
        countFont.setBold(true);
        countLabel->setFont(countFont);
        auto* openButton = new QPushButton(u8s(u8"跳转到日期"), &dialog);
        auto* closeButton = new QPushButton(u8s(u8"关闭"), &dialog);
        titleRow->addWidget(countLabel, 1);
        titleRow->addWidget(openButton);
        titleRow->addWidget(closeButton);
        layout->addLayout(titleRow);

        auto* body = new QSplitter(Qt::Horizontal, &dialog);
        auto* list = new QListWidget(body);
        auto* preview = new QTextEdit(body);
        preview->setReadOnly(true);
        preview->setLineWrapMode(QTextEdit::WidgetWidth);
        preview->setFont(QFont(QStringLiteral("Consolas"), 10));
        body->addWidget(list);
        body->addWidget(preview);
        body->setSizes(QList<int>() << 360 << 600);
        layout->addWidget(body, 1);

        for (int i = 0; i < results.size(); ++i) {
            const SearchResult& result = results.at(i);
            auto* item = new QListWidgetItem(isoDate(result.date) + QStringLiteral("\n") + result.context, list);
            item->setData(Qt::UserRole, i);
        }

        const auto updatePreview = [&results, preview, this, keyword](int row) {
            if (row < 0 || row >= results.size()) {
                preview->clear();
                return;
            }
            preview->setHtml(highlightedHtml(results.at(row).content, keyword));
        };

        connect(list, &QListWidget::currentRowChanged, &dialog, updatePreview);
        connect(closeButton, &QPushButton::clicked, &dialog, &QDialog::reject);
        connect(openButton, &QPushButton::clicked, &dialog, [&] {
            const int row = list->currentRow();
            if (row >= 0 && row < results.size()) {
                selectDate(results.at(row).date);
                dialog.accept();
            }
        });
        connect(list, &QListWidget::itemDoubleClicked, &dialog, [&](QListWidgetItem*) {
            const int row = list->currentRow();
            if (row >= 0 && row < results.size()) {
                selectDate(results.at(row).date);
                dialog.accept();
            }
        });

        list->setCurrentRow(0);
        dialog.exec();
    }

    void openFindDialog()
    {
        if (!findDialog_) {
            createFindDialog();
        }

        const QString seed = editor_->textCursor().selectedText();
        if (!seed.isEmpty()) {
            findEdit_->setText(seed);
        }

        findDialog_->show();
        findDialog_->raise();
        findDialog_->activateWindow();
        findEdit_->setFocus();
        findEdit_->selectAll();
        updateFindCount();
    }

    void createFindDialog()
    {
        findDialog_ = new QDialog(this);
        findDialog_->setWindowTitle(u8s(u8"页面内查找"));
        findDialog_->setWindowFlag(Qt::Tool, true);
        findDialog_->resize(420, 150);

        auto* layout = new QVBoxLayout(findDialog_);
        auto* row = new QHBoxLayout;
        findEdit_ = new QLineEdit(findDialog_);
        findEdit_->setPlaceholderText(u8s(u8"在当前日记中查找…"));
        auto* closeButton = new QPushButton(u8s(u8"关闭"), findDialog_);
        row->addWidget(findEdit_, 1);
        row->addWidget(closeButton);
        layout->addLayout(row);

        auto* controlRow = new QHBoxLayout;
        findCaseCheck_ = new QCheckBox(u8s(u8"区分大小写"), findDialog_);
        findCountLabel_ = new QLabel(findDialog_);
        auto* previousButton = new QPushButton(u8s(u8"上一个"), findDialog_);
        auto* nextButton = new QPushButton(u8s(u8"下一个"), findDialog_);
        controlRow->addWidget(findCaseCheck_);
        controlRow->addWidget(findCountLabel_, 1);
        controlRow->addWidget(previousButton);
        controlRow->addWidget(nextButton);
        layout->addLayout(controlRow);

        connect(findEdit_, &QLineEdit::textChanged, findDialog_, [this] { updateFindCount(); });
        connect(findEdit_, &QLineEdit::returnPressed, findDialog_, [this] { findNext(false); });
        connect(findCaseCheck_, &QCheckBox::toggled, findDialog_, [this] { updateFindCount(); });
        connect(previousButton, &QPushButton::clicked, findDialog_, [this] { findNext(true); });
        connect(nextButton, &QPushButton::clicked, findDialog_, [this] { findNext(false); });
        connect(closeButton, &QPushButton::clicked, findDialog_, &QDialog::hide);
    }

    int countMatches(const QString& query) const
    {
        if (query.isEmpty()) {
            return 0;
        }

        const Qt::CaseSensitivity cs = findCaseCheck_ && findCaseCheck_->isChecked() ? Qt::CaseSensitive : Qt::CaseInsensitive;
        const QString text = editor_->toPlainText();
        int count = 0;
        int from = 0;
        while (from <= text.size() - query.size()) {
            const int pos = text.indexOf(query, from, cs);
            if (pos < 0) {
                break;
            }
            ++count;
            from = pos + qMax(1, query.size());
        }
        return count;
    }

    int currentMatchOrdinal(const QString& query) const
    {
        if (query.isEmpty()) {
            return 0;
        }

        QTextCursor cursor = editor_->textCursor();
        if (!cursor.hasSelection()) {
            return 0;
        }

        const Qt::CaseSensitivity cs = findCaseCheck_ && findCaseCheck_->isChecked() ? Qt::CaseSensitive : Qt::CaseInsensitive;
        if (QString::compare(cursor.selectedText(), query, cs) != 0) {
            return 0;
        }

        const QString before = editor_->toPlainText().left(cursor.selectionStart());
        int count = 0;
        int from = 0;
        while (from <= before.size() - query.size()) {
            const int pos = before.indexOf(query, from, cs);
            if (pos < 0) {
                break;
            }
            ++count;
            from = pos + qMax(1, query.size());
        }
        return count + 1;
    }

    void updateFindCount()
    {
        if (!findDialog_ || !findCountLabel_) {
            return;
        }

        const QString query = findEdit_->text();
        if (query.isEmpty()) {
            findCountLabel_->clear();
            return;
        }

        const int total = countMatches(query);
        if (total == 0) {
            findCountLabel_->setText(u8s(u8"未找到"));
            return;
        }

        const int current = currentMatchOrdinal(query);
        findCountLabel_->setText(current > 0
            ? QStringLiteral("%1/%2").arg(current).arg(total)
            : u8s(u8"找到 ") + QString::number(total) + u8s(u8" 处"));
    }

    void findNext(bool backward)
    {
        if (!findDialog_ || !findDialog_->isVisible()) {
            openFindDialog();
            return;
        }

        const QString query = findEdit_->text();
        if (query.isEmpty()) {
            return;
        }

        QTextDocument::FindFlags flags;
        if (backward) {
            flags |= QTextDocument::FindBackward;
        }
        if (findCaseCheck_->isChecked()) {
            flags |= QTextDocument::FindCaseSensitively;
        }

        if (!editor_->find(query, flags)) {
            QTextCursor cursor = editor_->textCursor();
            cursor.movePosition(backward ? QTextCursor::End : QTextCursor::Start);
            editor_->setTextCursor(cursor);
            editor_->find(query, flags);
        }
        updateFindCount();
    }

    QSettings settings_;
    QDate currentDate_;
    QDate lastSystemDate_;
    QString currentContent_;
    QString lastSavedContent_;
    QString statusMessage_;
    bool modified_ = false;
    bool autoSaveEnabled_ = true;
    bool isAutoSaving_ = false;
    bool darkMode_ = true;
    qint64 lastEditMs_ = 0;
    QHash<QString, QSet<QDate>> monthEntryCache_;

    QTimer autoSaveTimer_;
    QTimer dateTimer_;
    QTimer statusTimer_;

    QSplitter* splitter_ = nullptr;
    EntryCalendar* calendar_ = nullptr;
    QTextEdit* editor_ = nullptr;
    QLabel* titleLabel_ = nullptr;
    QLabel* subtitleLabel_ = nullptr;
    QLabel* saveBadge_ = nullptr;
    QLabel* dateLabel_ = nullptr;
    QLabel* pathLabel_ = nullptr;
    QLabel* statusLabel_ = nullptr;
    QLabel* autoSaveLabel_ = nullptr;
    QLineEdit* searchEdit_ = nullptr;
    QPushButton* searchButton_ = nullptr;
    QPushButton* themeButton_ = nullptr;
    QPushButton* todayButton_ = nullptr;
    QPushButton* saveButton_ = nullptr;
    QPushButton* autoSaveButton_ = nullptr;
    QPushButton* findButton_ = nullptr;

    QDialog* findDialog_ = nullptr;
    QLineEdit* findEdit_ = nullptr;
    QCheckBox* findCaseCheck_ = nullptr;
    QLabel* findCountLabel_ = nullptr;
};

quintptr nativeHandle(QWidget* widget)
{
    return widget ? static_cast<quintptr>(widget->winId()) : 0;
}

void activateNativeHandle(quintptr hwnd)
{
#ifdef Q_OS_WIN
    if (!hwnd) {
        return;
    }
    HWND handle = reinterpret_cast<HWND>(hwnd);
    if (IsIconic(handle)) {
        ShowWindow(handle, SW_RESTORE);
    } else {
        ShowWindow(handle, SW_SHOW);
    }
    SetForegroundWindow(handle);
#else
    Q_UNUSED(hwnd);
#endif
}

bool notifyExistingInstance()
{
    QLocalSocket socket;
    socket.connectToServer(QString::fromLatin1(kSingleInstanceServer));
    if (!socket.waitForConnected(250)) {
        return false;
    }

    socket.write("activate\n");
    socket.flush();
    socket.waitForBytesWritten(250);
    if (socket.waitForReadyRead(500)) {
        const QString reply = QString::fromUtf8(socket.readAll()).trimmed();
        for (const QString& line : reply.split(QLatin1Char('\n'))) {
            if (!line.startsWith(QStringLiteral("hwnd:"))) {
                continue;
            }
            bool ok = false;
            const quintptr hwnd = line.mid(5).toULongLong(&ok);
            if (ok) {
                activateNativeHandle(hwnd);
            }
        }
    }
    socket.disconnectFromServer();
    return true;
}

} // namespace

int main(int argc, char* argv[])
{
    QApplication app(argc, argv);
    app.setStyle(QStringLiteral("Fusion"));
    app.setOrganizationName(QString::fromLatin1(kOrganization));
    app.setApplicationName(QString::fromLatin1(kApplication));
    app.setApplicationDisplayName(titleBase());
    app.setWindowIcon(QIcon(QStringLiteral(":/icon.ico")));

    if (notifyExistingInstance()) {
        return 0;
    }

    QLocalServer server;
    server.setSocketOptions(QLocalServer::UserAccessOption);
    if (!server.listen(QString::fromLatin1(kSingleInstanceServer))) {
        QLocalServer::removeServer(QString::fromLatin1(kSingleInstanceServer));
        if (!server.listen(QString::fromLatin1(kSingleInstanceServer))) {
            QMessageBox::critical(nullptr, titleBase(), u8s(u8"无法启动单应用监听：") + server.errorString());
            return 1;
        }
    }

    MainWindow window;
    QObject::connect(&server, &QLocalServer::newConnection, &window, [&] {
        while (server.hasPendingConnections()) {
            QLocalSocket* socket = server.nextPendingConnection();
            if (!socket) {
                continue;
            }
            socket->write(QStringLiteral("hwnd:%1\n").arg(nativeHandle(&window)).toUtf8());
            socket->flush();
            socket->waitForBytesWritten(100);
            socket->disconnectFromServer();
            socket->deleteLater();
        }
        window.bringToFront();
    });

    window.show();
    return app.exec();
}
