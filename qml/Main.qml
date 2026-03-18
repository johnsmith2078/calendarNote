import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: root
    visible: true
    width: 1320
    height: 860
    minimumWidth: 820
    minimumHeight: 620
    title: root.backendSafe.windowTitle
    color: backgroundColor

    property color backgroundColor: "#FFF8F4"
    property color surfaceColor: "#FFFDFC"
    property color elevatedColor: "#FFF2E8"
    property color borderColor: "#EFDCCD"
    property color primaryColor: "#2B211D"
    property color secondaryTextColor: "#7A625A"
    property color accentColor: "#F59E0B"
    property color accentSoftColor: "#FFE6CC"
    property color successColor: "#166534"
    property color dangerColor: "#B91C1C"
    property color mutedChipColor: "#F8E7DA"
    property color skyColor: "#60A5FA"
    property color skySoftColor: "#DBEAFE"
    property color mintColor: "#34D399"
    property color mintSoftColor: "#D1FAE5"
    property color plumColor: "#A78BFA"
    property color plumSoftColor: "#EDE9FE"
    property color coralColor: "#FB7185"
    property color coralSoftColor: "#FFE4E8"
    property bool wideLayout: width >= 1040 && width / Math.max(height, 1) >= 1.1
    property real pagePadding: Math.max(18, Math.min(width, height) * 0.022)
    property real gap: wideLayout ? 20 : 16
    property bool closeApproved: false
    property var backendRef: backend
    property bool backendReady: backendRef !== null && backendRef !== undefined

    QtObject {
        id: backendStub
        property string windowTitle: "日历笔记本"
        property string saveStateText: "已保存"
        property string statusMessage: ""
        property string currentEntryPath: ""
        property string autoSaveStatusText: ""
        property bool autoSaveEnabled: false
        property bool searchBusy: false
        property string todayLabel: "今天"
        property string currentDateDisplay: ""
        property string monospaceFamily: "Consolas"
        property string currentContent: ""
        property string searchResultCountText: "找到 0 个结果"
        property var searchResultsModel: null
        property string searchPreviewDate: ""
        property string searchPreviewContent: ""

        function preloadMonth(year, month) {}
        function requestWindowClose() {}
        function saveCurrentEntry() {}
        function toggleAutoSave() {}
        function selectSearchResult(index) {}
        function performGlobalSearch(text) {}
        function returnToToday() { return false }
        function updateContent(text) {}
        function openSearchResult(index) {}
        function selectDate(isoDate) {}
        function hasEntryForDate(isoDate) { return false }
    }

    property var backendSafe: backendReady ? backendRef : backendStub

    Rectangle {
        z: -2
        anchors.fill: parent
        color: root.backgroundColor
    }

    Rectangle {
        z: -1
        width: Math.max(220, root.width * 0.28)
        height: width
        radius: width / 2
        x: root.width - width * 0.72
        y: -height * 0.28
        color: root.accentSoftColor
        opacity: 0.45
    }

    Rectangle {
        z: -1
        width: Math.max(240, root.width * 0.24)
        height: width
        radius: width / 2
        x: -width * 0.22
        y: root.height - height * 0.62
        color: root.skySoftColor
        opacity: 0.32
    }

    Rectangle {
        z: -1
        width: Math.max(180, root.width * 0.18)
        height: width
        radius: width / 2
        x: root.width * 0.48
        y: root.height - height * 0.38
        color: root.plumSoftColor
        opacity: 0.28
    }

    component AppButton: Button {
        id: control
        property string tone: "neutral"
        readonly property color toneFill: tone === "accent"
            ? root.accentSoftColor
            : tone === "sky"
                ? root.skySoftColor
                : tone === "mint"
                    ? root.mintSoftColor
                    : tone === "plum"
                        ? root.plumSoftColor
                        : tone === "coral"
                            ? root.coralSoftColor
                            : "#FFFFFF"
        readonly property color toneHoverFill: tone === "accent"
            ? "#FFD9B3"
            : tone === "sky"
                ? "#CDE1FF"
                : tone === "mint"
                    ? "#C0F3DA"
                    : tone === "plum"
                        ? "#E4DEFF"
                        : tone === "coral"
                            ? "#FFD6DE"
                            : "#FFF7F1"
        readonly property color toneStroke: tone === "accent"
            ? "#F5B35D"
            : tone === "sky"
                ? "#A8CAFF"
                : tone === "mint"
                    ? "#9BE6C1"
                    : tone === "plum"
                        ? "#C8BAFF"
                        : tone === "coral"
                            ? "#F9A8B4"
                            : root.borderColor
        readonly property color toneText: tone === "accent"
            ? "#B45309"
            : tone === "sky"
                ? "#2563EB"
                : tone === "mint"
                    ? "#0F9F6E"
                    : tone === "plum"
                        ? "#7C3AED"
                        : tone === "coral"
                            ? "#E11D48"
                            : root.primaryColor
        implicitHeight: 42
        leftPadding: 16
        rightPadding: 16
        topPadding: 10
        bottomPadding: 10
        font.pixelSize: 13
        font.bold: true
        hoverEnabled: true

        contentItem: Text {
            text: control.text
            color: control.enabled ? control.toneText : "#A8A29E"
            font: control.font
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }

        background: Rectangle {
            radius: 12
            gradient: Gradient {
                GradientStop {
                    position: 0.0
                    color: !control.enabled
                        ? "#F5F5F4"
                        : (control.down ? Qt.darker(control.toneFill, 1.02) : Qt.lighter(control.toneFill, 1.08))
                }
                GradientStop {
                    position: 1.0
                    color: !control.enabled
                        ? "#F5F5F4"
                        : (control.hovered ? control.toneHoverFill : Qt.darker(control.toneFill, 1.01))
                }
            }
            border.color: control.activeFocus ? root.accentColor : control.toneStroke
            border.width: control.activeFocus ? 1.5 : 1
        }
    }

    component AppTextField: TextField {
        id: control
        implicitHeight: 44
        leftPadding: 14
        rightPadding: 14
        topPadding: 0
        bottomPadding: 0
        color: root.primaryColor
        font.pixelSize: 13
        placeholderTextColor: "#78716C"
        selectedTextColor: "#FAFAF9"
        selectionColor: root.primaryColor
        verticalAlignment: TextInput.AlignVCenter

        background: Rectangle {
            radius: 12
            gradient: Gradient {
                GradientStop { position: 0.0; color: "#FFFFFF" }
                GradientStop { position: 1.0; color: "#FFF7F1" }
            }
            border.color: control.activeFocus ? root.accentColor : "#E8D6CA"
            border.width: control.activeFocus ? 1.5 : 1
        }
    }

    component AppCheckBox: CheckBox {
        id: control
        implicitHeight: Math.max(20, contentItem.implicitHeight)
        padding: 0
        leftPadding: indicator.width + spacing
        rightPadding: 0
        topPadding: 0
        bottomPadding: 0
        hoverEnabled: false
        spacing: 10
        font.pixelSize: 13

        indicator: Rectangle {
            x: 0
            y: Math.round((control.height - height) / 2)
            implicitWidth: 20
            implicitHeight: 20
            radius: 6
            color: control.checked ? root.skyColor : "#FFFFFF"
            border.color: control.checked ? root.skyColor : root.borderColor
            border.width: 1

            Text {
                anchors.centerIn: parent
                text: control.checked ? "✓" : ""
                color: "#FAFAF9"
                font.pixelSize: 12
                font.bold: true
            }
        }

        contentItem: Text {
            text: control.text
            color: root.primaryColor
            font: control.font
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }

        background: Item {
        }
    }

    function syncShownMonth(dateText) {
        const jsDate = new Date(dateText + "T00:00:00")
        sidebar.shownYear = jsDate.getFullYear()
        sidebar.shownMonth = jsDate.getMonth()
        root.backendSafe.preloadMonth(sidebar.shownYear, sidebar.shownMonth)
    }

    function openInPageSearch() {
        if (inPageSearchPopup.visible) {
            inPageSearchPopup.close()
            return
        }

        const seed = editor.selectedText && editor.selectedText.length > 0 ? editor.selectedText : findField.text
        if (seed && seed.length > 0) {
            findField.text = seed
        }
        inPageSearchPopup.open()
        findField.forceActiveFocus()
        findField.selectAll()
        inPageSearchPopup.refreshMatches()
    }

    Component.onCompleted: {
        if (backendReady)
            syncShownMonth(backendRef.currentDate)
    }

    onClosing: function(close) {
        if (closeApproved) {
            close.accepted = true
            return
        }
        close.accepted = false
        root.backendSafe.requestWindowClose()
    }

    header: Rectangle {
        color: "transparent"
        implicitHeight: 82

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: root.pagePadding
            anchors.rightMargin: root.pagePadding
            anchors.topMargin: 18
            anchors.bottomMargin: 10
            spacing: 16

            ColumnLayout {
                spacing: 4
                Layout.fillWidth: true

                Label {
                    text: "日历笔记本"
                    font.pixelSize: 28
                    font.bold: true
                    color: root.primaryColor
                }

                Label {
                    text: root.wideLayout
                        ? "QML 自适应双栏布局：左侧导航与检索，右侧沉浸式编辑。"
                        : "QML 自适应纵向布局：在窄窗口下优先保证日历与编辑器可读性。"
                    color: root.secondaryTextColor
                    font.pixelSize: 13
                    wrapMode: Text.Wrap
                }
            }

            Rectangle {
                radius: 999
                color: root.backendSafe.saveStateText === "已保存" ? "#ECFDF3" : "#FEF2F2"
                border.color: root.backendSafe.saveStateText === "已保存" ? "#BBF7D0" : "#FECACA"
                implicitHeight: 40
                implicitWidth: statusChipLabel.implicitWidth + 28

                Label {
                    id: statusChipLabel
                    anchors.centerIn: parent
                    text: root.backendSafe.saveStateText
                    color: root.backendSafe.saveStateText === "已保存" ? root.successColor : root.dangerColor
                    font.pixelSize: 13
                    font.bold: true
                }
            }
        }
    }

    footer: Rectangle {
        color: "transparent"
        implicitHeight: 52

        Rectangle {
            anchors.fill: parent
            anchors.leftMargin: root.pagePadding
            anchors.rightMargin: root.pagePadding
            anchors.bottomMargin: 10
            radius: 18
            gradient: Gradient {
                GradientStop { position: 0.0; color: "#FFF9F5" }
                GradientStop { position: 1.0; color: "#FFF1E8" }
            }
            border.color: "#ECDCCC"

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 18
                anchors.rightMargin: 18
                spacing: 12

                Label {
                    Layout.fillWidth: true
                    text: root.backendSafe.statusMessage.length > 0
                        ? root.backendSafe.statusMessage
                        : root.backendSafe.saveStateText + " · " + root.backendSafe.currentEntryPath
                    color: root.secondaryTextColor
                    font.pixelSize: 12
                    elide: Text.ElideRight
                }

                Label {
                    text: root.backendSafe.autoSaveStatusText
                    color: root.backendSafe.autoSaveEnabled ? root.successColor : root.dangerColor
                    font.pixelSize: 12
                    font.bold: true
                }
            }
        }
    }

    Shortcut {
        sequences: [StandardKey.Save]
        onActivated: root.backendSafe.saveCurrentEntry()
    }

    Shortcut {
        sequences: [StandardKey.Find]
        onActivated: root.openInPageSearch()
    }

    Shortcut {
        sequence: "F3"
        enabled: inPageSearchPopup.visible && inPageSearchPopup.matchCount > 0
        onActivated: inPageSearchPopup.findNext()
    }

    Shortcut {
        sequence: "Shift+F3"
        enabled: inPageSearchPopup.visible && inPageSearchPopup.matchCount > 0
        onActivated: inPageSearchPopup.findPrevious()
    }

    Shortcut {
        sequence: "Escape"
        enabled: inPageSearchPopup.visible
        onActivated: inPageSearchPopup.close()
    }

    Shortcut {
        sequence: "Ctrl+Shift+A"
        onActivated: root.backendSafe.toggleAutoSave()
    }

    Connections {
        target: root.backendRef

        function onCurrentDateChanged() {
            if (root.backendReady)
                root.syncShownMonth(root.backendRef.currentDate)
        }

        function onSearchCompleted(hasResults, keyword) {
            if (!hasResults) {
                searchResultsPopup.close()
                return
            }
            searchResultsPopup.open()
            searchResultsList.currentIndex = 0
            root.backendSafe.selectSearchResult(0)
        }

        function onWindowCloseApproved() {
            root.closeApproved = true
            root.close()
        }

        function onCurrentContentChanged() {
            if (editor.text !== root.backendSafe.currentContent) {
                editor.text = root.backendSafe.currentContent
            }
            inPageSearchPopup.refreshMatches()
        }
    }

    GridLayout {
        anchors {
            fill: parent
            leftMargin: root.pagePadding
            rightMargin: root.pagePadding
            topMargin: root.pagePadding
            bottomMargin: root.pagePadding
        }
        columns: root.wideLayout ? 2 : 1
        columnSpacing: root.gap
        rowSpacing: root.gap

        Rectangle {
            id: sidebar
            radius: 26
            gradient: Gradient {
                GradientStop { position: 0.0; color: "#FFFFFE" }
                GradientStop { position: 1.0; color: "#FFF5EE" }
            }
            border.color: "#ECD8CF"
            Layout.fillWidth: true
            Layout.fillHeight: root.wideLayout
            Layout.preferredWidth: root.wideLayout ? Math.max(330, Math.min(root.width * 0.33, 430)) : -1
            Layout.preferredHeight: root.wideLayout ? -1 : Math.max(380, root.height * 0.44)
            Layout.minimumWidth: 300
            Layout.minimumHeight: 340
            property int shownMonth: 0
            property int shownYear: 2000

            function shiftMonth(delta) {
                let newMonth = shownMonth + delta
                let newYear = shownYear
                if (newMonth < 0) {
                    newMonth = 11
                    newYear -= 1
                } else if (newMonth > 11) {
                    newMonth = 0
                    newYear += 1
                }
                shownYear = newYear
                shownMonth = newMonth
            }

            onShownMonthChanged: root.backendSafe.preloadMonth(shownYear, shownMonth)
            onShownYearChanged: root.backendSafe.preloadMonth(shownYear, shownMonth)

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 22
                spacing: 18

                Rectangle {
                    Layout.fillWidth: true
                    radius: 18
                    gradient: Gradient {
                        GradientStop { position: 0.0; color: "#FFF4EA" }
                        GradientStop { position: 1.0; color: "#FFEADD" }
                    }
                    border.color: root.borderColor
                    implicitHeight: 124

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 16
                        spacing: 12

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10

                            AppTextField {
                                id: globalSearchField
                                Layout.fillWidth: true
                                enabled: !root.backendSafe.searchBusy
                                placeholderText: "搜索所有日记内容…"
                                selectByMouse: true
                                implicitHeight: 44
                                onAccepted: root.backendSafe.performGlobalSearch(text)
                            }

                            AppButton {
                                tone: "accent"
                                text: root.backendSafe.searchBusy ? "搜索中" : "搜索"
                                enabled: !root.backendSafe.searchBusy
                                implicitWidth: 86
                                onClicked: root.backendSafe.performGlobalSearch(globalSearchField.text)
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10

                            Label {
                                text: root.backendSafe.autoSaveStatusText
                                Layout.fillWidth: true
                                wrapMode: Text.Wrap
                                color: root.secondaryTextColor
                                font.pixelSize: 12
                            }

                            AppButton {
                                tone: root.backendSafe.autoSaveEnabled ? "coral" : "mint"
                                text: root.backendSafe.autoSaveEnabled ? "关闭自动保存" : "启用自动保存"
                                implicitHeight: 40
                                onClicked: root.backendSafe.toggleAutoSave()
                            }
                        }
                    }
                }

                AppButton {
                    tone: "plum"
                    Layout.fillWidth: true
                    implicitHeight: 48
                    text: root.backendSafe.todayLabel
                    font.pixelSize: 14
                    font.bold: true
                    onClicked: {
                        if (root.backendSafe.returnToToday())
                            root.syncShownMonth(root.backendSafe.currentDate)
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    spacing: 14

                    RowLayout {
                        Layout.fillWidth: true

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2

                            Label {
                                text: sidebar.shownYear + " 年 " + (sidebar.shownMonth + 1) + " 月"
                                color: root.primaryColor
                                font.pixelSize: 20
                                font.bold: true
                            }

                            Label {
                                text: "带圆点的日期表示已有日记内容"
                                color: root.secondaryTextColor
                                font.pixelSize: 12
                            }
                        }

                        RowLayout {
                            spacing: 8

                            AppButton {
                                tone: "sky"
                                text: "‹"
                                implicitWidth: 40
                                implicitHeight: 40
                                onClicked: sidebar.shiftMonth(-1)
                            }

                            AppButton {
                                tone: "sky"
                                text: "›"
                                implicitWidth: 40
                                implicitHeight: 40
                                onClicked: sidebar.shiftMonth(1)
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.minimumHeight: 280
                        radius: 22
                        gradient: Gradient {
                            GradientStop { position: 0.0; color: "#FFFFFF" }
                            GradientStop { position: 1.0; color: "#FFF7F5" }
                        }
                        border.color: "#ECDDD5"

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 14
                            spacing: 10

                            DayOfWeekRow {
                                id: dayHeader
                                locale: Qt.locale("zh_CN")
                                Layout.fillWidth: true
                                Layout.preferredHeight: 30

                                delegate: Label {
                                    required property var model
                                    text: model.narrowName
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                    color: root.secondaryTextColor
                                    font.pixelSize: 12
                                    font.bold: true
                                }
                            }

                            MonthGrid {
                                id: monthGrid
                                month: sidebar.shownMonth
                                year: sidebar.shownYear
                                locale: Qt.locale("zh_CN")
                                Layout.fillWidth: true
                                Layout.fillHeight: true

                                delegate: Rectangle {
                                    required property var model
                                    readonly property string isoDate: Qt.formatDate(model.date, "yyyy-MM-dd")
                                    readonly property bool isCurrentMonth: model.month === monthGrid.month
                                    readonly property bool backendAvailable: root.backendReady
                                    readonly property bool isSelected: backendAvailable && root.backendRef.currentDate === isoDate
                                    readonly property int refreshToken: backendAvailable ? root.backendRef.calendarVersion : 0
                                    readonly property bool hasEntry: {
                                        if (!backendAvailable)
                                            return false
                                        const token = refreshToken
                                        return root.backendRef.hasEntryForDate(isoDate)
                                    }
                                    radius: 16
                                    color: isSelected ? root.primaryColor : (cellArea.containsMouse ? root.mutedChipColor : "transparent")
                                    border.color: model.today && !isSelected ? root.accentColor : "transparent"
                                    border.width: model.today && !isSelected ? 1.5 : 0
                                    opacity: isCurrentMonth ? 1.0 : 0.42

                                    MouseArea {
                                        id: cellArea
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        onClicked: {
                                            if (parent.backendAvailable)
                                                root.backendRef.selectDate(parent.isoDate)
                                        }
                                    }

                                    Label {
                                        anchors.centerIn: parent
                                        text: model.day
                                        font.pixelSize: 14
                                        font.bold: parent.isSelected || parent.hasEntry
                                        color: parent.isSelected ? "#FAFAF9" : root.primaryColor
                                    }

                                    Rectangle {
                                        visible: parent.hasEntry
                                        width: 6
                                        height: 6
                                        radius: 3
                                        color: parent.isSelected ? root.accentSoftColor : root.accentColor
                                        anchors.horizontalCenter: parent.horizontalCenter
                                        anchors.bottom: parent.bottom
                                        anchors.bottomMargin: 7
                                    }
                                }
                            }
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    radius: 18
                    gradient: Gradient {
                        GradientStop { position: 0.0; color: "#F6F0FF" }
                        GradientStop { position: 1.0; color: "#EAF3FF" }
                    }
                    border.color: "#D9CCFF"
                    implicitHeight: 86

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 14
                        spacing: 4

                        Label {
                            text: "当前文件"
                            color: root.secondaryTextColor
                            font.pixelSize: 12
                        }

                        Text {
                            text: root.backendSafe.currentEntryPath
                            color: root.primaryColor
                            font.pixelSize: 13
                            wrapMode: Text.WrapAnywhere
                            Layout.fillWidth: true
                        }
                    }
                }
            }
        }

        Rectangle {
            id: editorCard
            radius: 26
            gradient: Gradient {
                GradientStop { position: 0.0; color: "#FFFFFE" }
                GradientStop { position: 1.0; color: "#FFF8FC" }
            }
            border.color: "#ECD8D6"
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.minimumWidth: 420
            Layout.minimumHeight: 260
            Layout.preferredHeight: root.wideLayout ? -1 : Math.max(280, root.height * 0.48)

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 22
                spacing: 16

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 14

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4

                        Label {
                            text: root.backendSafe.currentDateDisplay
                            color: root.primaryColor
                            font.pixelSize: 26
                            font.bold: true
                        }

                        Label {
                            text: "纯文本编辑 · Ctrl+S 保存 · Ctrl+F 页面内查找"
                            color: root.secondaryTextColor
                            font.pixelSize: 13
                        }
                    }

                    Rectangle {
                        radius: 999
                        color: root.backendSafe.autoSaveEnabled ? "#EFF6FF" : "#FEF2F2"
                        border.color: root.backendSafe.autoSaveEnabled ? "#BFDBFE" : "#FECACA"
                        implicitWidth: autoSaveChip.implicitWidth + 24
                        implicitHeight: 38

                        Label {
                            id: autoSaveChip
                            anchors.centerIn: parent
                            text: root.backendSafe.autoSaveEnabled ? "自动保存开启" : "自动保存关闭"
                            color: root.backendSafe.autoSaveEnabled ? "#1D4ED8" : root.dangerColor
                            font.pixelSize: 12
                            font.bold: true
                        }
                    }

                    AppButton {
                        tone: "accent"
                        text: "页面内查找"
                        implicitHeight: 42
                        onClicked: root.openInPageSearch()
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    radius: 22
                    gradient: Gradient {
                        GradientStop { position: 0.0; color: "#FFFFFF" }
                        GradientStop { position: 1.0; color: "#FFF7FB" }
                    }
                    border.color: "#EEDBDA"
                    clip: true

                    Flickable {
                        id: editorFlick
                        anchors.fill: parent
                        anchors.margins: 1
                        clip: true
                        contentWidth: width
                        contentHeight: Math.max(height, editor.contentHeight + editor.topPadding + editor.bottomPadding)
                        boundsBehavior: Flickable.StopAtBounds
                        interactive: contentHeight > height

                        TextArea.flickable: TextArea {
                            id: editor
                            text: ""
                            width: editorFlick.width
                            color: root.primaryColor
                            textFormat: TextEdit.PlainText
                            wrapMode: TextArea.Wrap
                            selectByMouse: true
                            persistentSelection: true
                            selectionColor: "#D6E4FF"
                            selectedTextColor: root.primaryColor
                            placeholderText: "请在这里开始记录今天的想法、计划与回顾…"
                            font.family: root.backendSafe.monospaceFamily
                            font.pixelSize: 15
                            leftPadding: 24
                            rightPadding: 24
                            topPadding: 22
                            bottomPadding: 28
                            background: null
                            Component.onCompleted: text = root.backendSafe.currentContent
                            onTextChanged: {
                                root.backendSafe.updateContent(text)
                                inPageSearchPopup.refreshMatches()
                            }
                        }

                        ScrollBar.vertical: ScrollBar {
                            policy: ScrollBar.AsNeeded
                        }
                    }
                }
            }
        }
    }

    Popup {
        id: searchResultsPopup
        modal: true
        focus: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        anchors.centerIn: Overlay.overlay
        width: root.wideLayout ? Math.min(root.width * 0.8, 1100) : root.width - root.pagePadding * 2
        height: Math.min(root.height * 0.84, 760)
        padding: 0

        background: Rectangle {
            radius: 28
            gradient: Gradient {
                GradientStop { position: 0.0; color: "#FFFFFE" }
                GradientStop { position: 1.0; color: "#FFF6F0" }
            }
            border.color: "#ECD9D0"
        }

        contentItem: ColumnLayout {
            anchors.fill: parent
            anchors.margins: 24
            spacing: 18

            RowLayout {
                Layout.fillWidth: true
                spacing: 12

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4

                    Label {
                        text: "搜索结果"
                        color: root.primaryColor
                        font.pixelSize: 24
                        font.bold: true
                    }

                    Label {
                        text: root.backendSafe.searchResultCountText
                        color: root.secondaryTextColor
                        font.pixelSize: 13
                    }
                }

                AppButton {
                    tone: "sky"
                    text: "跳转到日期"
                    enabled: searchResultsList.currentIndex >= 0
                    implicitHeight: 42
                    onClicked: {
                        root.backendSafe.openSearchResult(searchResultsList.currentIndex)
                        searchResultsPopup.close()
                    }
                }

                AppButton {
                    text: "关闭"
                    implicitHeight: 42
                    onClicked: searchResultsPopup.close()
                }
            }

            GridLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                columns: root.wideLayout ? 2 : 1
                columnSpacing: 18
                rowSpacing: 18

                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.preferredWidth: root.wideLayout ? 0 : -1
                    radius: 22
                    gradient: Gradient {
                        GradientStop { position: 0.0; color: "#FFF7F0" }
                        GradientStop { position: 1.0; color: "#FFF1E8" }
                    }
                    border.color: "#EFDACA"

                    ListView {
                        id: searchResultsList
                        anchors.fill: parent
                        anchors.margins: 10
                        clip: true
                        spacing: 8
                        model: root.backendSafe.searchResultsModel
                        currentIndex: -1
                        onCurrentIndexChanged: root.backendSafe.selectSearchResult(currentIndex)

                        delegate: Rectangle {
                            required property int index
                            required property string dateLabel
                            required property string matchText
                            width: ListView.view.width
                            height: Math.max(72, resultLayout.implicitHeight + 20)
                            radius: 18
                            color: ListView.isCurrentItem ? "#F5F3FF" : "#FAFAF9"
                            border.color: ListView.isCurrentItem ? "#C4B5FD" : root.borderColor

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: searchResultsList.currentIndex = index
                                onDoubleClicked: {
                                    searchResultsList.currentIndex = index
                                    root.backendSafe.openSearchResult(index)
                                    searchResultsPopup.close()
                                }
                            }

                            ColumnLayout {
                                id: resultLayout
                                anchors.fill: parent
                                anchors.margins: 14
                                spacing: 6

                                Label {
                                    text: dateLabel
                                    color: root.primaryColor
                                    font.pixelSize: 14
                                    font.bold: true
                                }

                                Label {
                                    text: matchText.length > 0 ? matchText : "该条结果没有可显示的摘要"
                                    color: root.secondaryTextColor
                                    font.pixelSize: 12
                                    wrapMode: Text.Wrap
                                    maximumLineCount: 3
                                    elide: Text.ElideRight
                                    Layout.fillWidth: true
                                }
                            }
                        }

                        ScrollBar.vertical: ScrollBar {
                            policy: ScrollBar.AsNeeded
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumHeight: root.wideLayout ? 0 : 240
                    radius: 22
                    gradient: Gradient {
                        GradientStop { position: 0.0; color: "#FFFFFF" }
                        GradientStop { position: 1.0; color: "#FFF8FB" }
                    }
                    border.color: "#F1DED2"

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 16
                        spacing: 12

                        Label {
                            text: root.backendSafe.searchPreviewDate.length > 0
                                ? ("预览 · " + root.backendSafe.searchPreviewDate)
                                : "预览"
                            color: root.primaryColor
                            font.pixelSize: 16
                            font.bold: true
                        }

                        ScrollView {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true

                            TextArea {
                                readOnly: true
                                text: root.backendSafe.searchPreviewContent
                                wrapMode: TextArea.Wrap
                                selectByMouse: true
                                textFormat: TextEdit.PlainText
                                font.family: root.backendSafe.monospaceFamily
                                font.pixelSize: 14
                                background: null
                            }
                        }
                    }
                }
            }
        }
    }

    Popup {
        id: inPageSearchPopup
        modal: false
        focus: true
        closePolicy: Popup.CloseOnEscape
        padding: 0
        width: Math.max(320, Math.min(420, editorCard.width - 32))
        height: 180
        property var matches: []
        property int currentMatchIndex: -1
        property int matchCount: matches.length
        property bool positionInitialized: false
        property real dragStartSceneX: 0
        property real dragStartSceneY: 0
        property real dragStartPopupX: 0
        property real dragStartPopupY: 0

        function resetPosition() {
            x = Math.max(root.pagePadding,
                         Math.min(editorCard.x + editorCard.width - width - 18,
                                  root.width - width - root.pagePadding))
            y = Math.max(root.pagePadding, root.header.height + 18)
            positionInitialized = true
        }

        function clampPosition() {
            x = Math.max(root.pagePadding,
                         Math.min(x, root.width - width - root.pagePadding))
            y = Math.max(root.pagePadding,
                         Math.min(y, root.height - height - root.pagePadding))
        }

        function refreshMatches() {
            if (!visible) {
                matches = []
                currentMatchIndex = -1
                return
            }

            const query = findField.text
            if (!query || query.length === 0) {
                matches = []
                currentMatchIndex = -1
                editor.deselect()
                return
            }

            const source = caseSensitiveCheck.checked ? editor.text : editor.text.toLowerCase()
            const needle = caseSensitiveCheck.checked ? query : query.toLowerCase()
            const found = []
            let from = 0

            while (from <= source.length - needle.length) {
                const pos = source.indexOf(needle, from)
                if (pos < 0)
                    break
                found.push({ start: pos, end: pos + query.length })
                from = pos + Math.max(needle.length, 1)
            }

            matches = found
            if (matches.length > 0) {
                const nextIndex = currentMatchIndex >= 0 && currentMatchIndex < matches.length
                    ? currentMatchIndex
                    : 0
                selectMatch(nextIndex)
            } else {
                currentMatchIndex = -1
                editor.deselect()
            }
        }

        function selectMatch(index) {
            if (index < 0 || index >= matches.length)
                return

            currentMatchIndex = index
            const match = matches[index]
            const findCursorPosition = findField.cursorPosition

            editor.forceActiveFocus()
            editor.cursorPosition = match.start
            editor.moveCursorSelection(match.end, TextEdit.SelectCharacters)

            Qt.callLater(function() {
                if (!inPageSearchPopup.visible)
                    return
                findField.forceActiveFocus()
                findField.cursorPosition = Math.min(findCursorPosition, findField.text.length)
            })
        }

        function findNext() {
            if (matches.length === 0)
                return
            selectMatch((currentMatchIndex + 1) % matches.length)
        }

        function findPrevious() {
            if (matches.length === 0)
                return
            selectMatch((currentMatchIndex - 1 + matches.length) % matches.length)
        }

        onOpened: {
            if (!positionInitialized)
                resetPosition()
            clampPosition()
            findField.forceActiveFocus()
            findField.selectAll()
            refreshMatches()
        }

        onClosed: {
            matches = []
            currentMatchIndex = -1
            editor.deselect()
            editor.forceActiveFocus()
        }

        background: Rectangle {
            radius: 22
            gradient: Gradient {
                GradientStop { position: 0.0; color: "#FFFDFC" }
                GradientStop { position: 1.0; color: "#FFF1F8" }
            }
            border.color: "#F0DDD1"
        }

        contentItem: ColumnLayout {
            id: popupContent
            anchors.fill: parent
            anchors.margins: 14
            spacing: 12

            Rectangle {
                Layout.fillWidth: true
                implicitHeight: 34
                radius: 12
                color: "#FFF4EA"
                border.color: "#F1D8C8"

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 12
                    anchors.rightMargin: 12
                    spacing: 8

                    Label {
                        text: "页面内查找"
                        color: root.primaryColor
                        font.pixelSize: 13
                        font.bold: true
                    }

                    Label {
                        Layout.fillWidth: true
                        text: "拖动此处移动"
                        color: root.secondaryTextColor
                        font.pixelSize: 12
                        horizontalAlignment: Text.AlignRight
                    }
                }

                MouseArea {
                    anchors.fill: parent
                    acceptedButtons: Qt.LeftButton
                    preventStealing: true
                    cursorShape: pressed ? Qt.ClosedHandCursor : Qt.OpenHandCursor
                    onPressed: function(mouse) {
                        const point = mapToItem(null, mouse.x, mouse.y)
                        inPageSearchPopup.dragStartSceneX = point.x
                        inPageSearchPopup.dragStartSceneY = point.y
                        inPageSearchPopup.dragStartPopupX = inPageSearchPopup.x
                        inPageSearchPopup.dragStartPopupY = inPageSearchPopup.y
                    }
                    onPositionChanged: function(mouse) {
                        if (!(mouse.buttons & Qt.LeftButton))
                            return
                        const point = mapToItem(null, mouse.x, mouse.y)
                        inPageSearchPopup.x = inPageSearchPopup.dragStartPopupX + point.x - inPageSearchPopup.dragStartSceneX
                        inPageSearchPopup.y = inPageSearchPopup.dragStartPopupY + point.y - inPageSearchPopup.dragStartSceneY
                        inPageSearchPopup.clampPosition()
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 10

                AppTextField {
                    id: findField
                    Layout.fillWidth: true
                    placeholderText: "在当前日记中查找…"
                    selectByMouse: true
                    onTextChanged: inPageSearchPopup.refreshMatches()
                    onAccepted: inPageSearchPopup.findNext()
                }

                AppButton {
                    tone: "coral"
                    text: "关闭"
                    implicitHeight: 40
                    onClicked: inPageSearchPopup.close()
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 12

                AppCheckBox {
                    id: caseSensitiveCheck
                    text: "区分大小写"
                    onToggled: inPageSearchPopup.refreshMatches()
                }

                Label {
                    Layout.fillWidth: true
                    text: inPageSearchPopup.matchCount === 0
                        ? (findField.text.length > 0 ? "未找到" : "")
                        : (inPageSearchPopup.currentMatchIndex + 1) + "/" + inPageSearchPopup.matchCount
                    color: root.secondaryTextColor
                    font.pixelSize: 12
                }

                AppButton {
                    tone: "plum"
                    text: "上一个"
                    enabled: inPageSearchPopup.matchCount > 0
                    implicitHeight: 40
                    onClicked: inPageSearchPopup.findPrevious()
                }

                AppButton {
                    tone: "plum"
                    text: "下一个"
                    enabled: inPageSearchPopup.matchCount > 0
                    implicitHeight: 40
                    onClicked: inPageSearchPopup.findNext()
                }
            }
        }
    }
}
