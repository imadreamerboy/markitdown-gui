import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import "components"

ApplicationWindow {
    id: root

    width: 1180
    height: 760
    minimumWidth: 980
    minimumHeight: 620
    visible: true
    title: "MarkItDown GUI"
    color: colors.window
    font.family: Qt.platform.os === "windows" ? "Segoe UI" : Qt.platform.os === "osx" ? ".AppleSystemUIFont" : "Noto Sans"
    onClosing: app.shutdown()

    property int pageIndex: 0
    property bool dark: app.darkMode
    property int pageMargin: 22
    property int panelRadius: 8
    property int controlRadius: 8
    property var colors: ({
        window: dark ? Qt.color("#2E3440") : Qt.color("#F8F1DC"),
        nav: dark ? Qt.color("#242A34") : Qt.color("#EDE4CC"),
        surface: dark ? Qt.color("#343B48") : Qt.color("#FFFCF0"),
        surfaceAlt: dark ? Qt.color("#3B4252") : Qt.color("#F2E8CD"),
        document: dark ? Qt.color("#2B313C") : Qt.color("#FFFEF7"),
        input: dark ? Qt.color("#2E3440") : Qt.color("#FFF7E4"),
        border: dark ? Qt.color("#4C566A") : Qt.color("#D3C6A8"),
        text: dark ? Qt.color("#ECEFF4") : Qt.color("#073642"),
        muted: dark ? Qt.color("#D8DEE9") : Qt.color("#586E75"),
        subtle: dark ? Qt.color("#AEB8C8") : Qt.color("#839496"),
        accent: dark ? Qt.color("#88C0D0") : Qt.color("#2AA198"),
        accentAlt: dark ? Qt.color("#8FBCBB") : Qt.color("#268BD2"),
        action: dark ? Qt.color("#88C0D0") : Qt.color("#7B6100"),
        actionSoft: dark ? Qt.color("#415867") : Qt.color("#EEE1B3"),
        onAccent: dark ? Qt.color("#2E3440") : Qt.color("#073642"),
        onAction: dark ? Qt.color("#2E3440") : Qt.color("#FDF6E3"),
        danger: dark ? Qt.color("#BF616A") : Qt.color("#DC322F"),
        success: dark ? Qt.color("#A3BE8C") : Qt.color("#859900"),
        warning: dark ? Qt.color("#EBCB8B") : Qt.color("#B58900")
    })

    function requestSave() {
        if (!app.hasResults) {
            app.notifyNoOutputToSave()
            return
        }

        if (app.saveCombined)
            saveCombinedDialog.open()
        else if (app.canSaveSeparateWithoutDialog)
            app.saveSeparateOutputs("")
        else
            saveSeparateDialog.open()
    }

    function showLegacyOcrSettings() {
        return app.ocrEnabled
            && (app.ocrProvider !== "glmocr" || app.ocrFallbackEnabled)
    }

    palette.window: colors.window
    palette.windowText: colors.text
    palette.base: colors.input
    palette.alternateBase: colors.surfaceAlt
    palette.text: colors.text
    palette.button: colors.surfaceAlt
    palette.buttonText: colors.text
    palette.highlight: colors.accent
    palette.highlightedText: colors.onAccent

    FileDialog {
        id: openFileDialog
        title: "Add files"
        fileMode: FileDialog.OpenFiles
        currentFolder: app.outputFolderUrl
        nameFilters: [
            "Supported files (*.docx *.pptx *.xlsx *.xls *.pdf *.epub *.html *.htm *.txt *.md *.csv *.json *.xml *.png *.jpg *.jpeg *.bmp *.gif *.tiff *.webp *.zip)",
            "All files (*)"
        ]
        onAccepted: app.addFiles(selectedFiles)
    }

    FileDialog {
        id: saveCombinedDialog
        title: "Save combined Markdown"
        fileMode: FileDialog.SaveFile
        defaultSuffix: "md"
        currentFolder: app.outputFolderUrl
        selectedFile: app.suggestedCombinedOutputUrl
        nameFilters: ["Markdown files (*.md)"]
        onAccepted: app.saveCombinedOutput(selectedFile)
    }

    FolderDialog {
        id: saveSeparateDialog
        title: "Save separate Markdown files"
        currentFolder: app.suggestedSeparateOutputFolderUrl
        onAccepted: app.saveSeparateOutputs(selectedFolder)
    }

    FolderDialog {
        id: outputFolderDialog
        title: "Choose output folder"
        currentFolder: app.outputFolderUrl
        onAccepted: app.setOutputFolderFromUrl(selectedFolder)
    }

    Connections {
        target: app
        function onToastRequested(kind, message) {
            toast.kind = kind
            toast.message = message
            toast.visible = true
            toastTimer.restart()
        }
    }

    Shortcut {
        sequence: "Ctrl+O"
        context: Qt.ApplicationShortcut
        enabled: !app.converting
        onActivated: openFileDialog.open()
    }

    Shortcut {
        sequence: "Ctrl+B"
        context: Qt.ApplicationShortcut
        onActivated: app.convert()
    }

    Shortcut {
        sequence: "Ctrl+P"
        context: Qt.ApplicationShortcut
        onActivated: app.togglePause()
    }

    Shortcut {
        sequence: "Esc"
        context: Qt.ApplicationShortcut
        onActivated: app.cancel()
    }

    Shortcut {
        sequence: "Ctrl+S"
        context: Qt.ApplicationShortcut
        onActivated: root.requestSave()
    }

    Shortcut {
        sequence: "Ctrl+C"
        context: Qt.ApplicationShortcut
        enabled: root.pageIndex === 0 && app.hasResults
        onActivated: app.copySelectedMarkdown()
    }

    Shortcut {
        sequence: "Ctrl+L"
        context: Qt.ApplicationShortcut
        enabled: !app.converting
        onActivated: app.clearQueue()
    }

    Shortcut {
        sequence: "Ctrl+K"
        context: Qt.ApplicationShortcut
        onActivated: root.pageIndex = 2
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        SideNav {
            currentIndex: root.pageIndex
            backgroundColor: colors.nav
            activeColor: colors.surface
            textColor: colors.text
            mutedTextColor: colors.muted
            accentColor: colors.accent
            borderColor: colors.border
            utilityHoverColor: Qt.rgba(colors.accent.r, colors.accent.g, colors.accent.b, dark ? 0.16 : 0.10)
            accentTextColor: colors.onAccent
            Layout.fillHeight: true
            onPageRequested: index => root.pageIndex = index
        }

        Rectangle {
            width: 1
            color: colors.border
            Layout.fillHeight: true
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            HeaderBar {
                Layout.fillWidth: true
            }

            StackLayout {
                currentIndex: root.pageIndex
                Layout.fillWidth: true
                Layout.fillHeight: true

                WorkspacePage {}
                SettingsPage {}
                HelpPage {}
            }
        }
    }

    component HeaderTitle: ColumnLayout {
        id: headerTitle
        property string title: ""
        property string detail: ""
        spacing: 2

        Label {
            text: headerTitle.title
            color: colors.text
            font.pixelSize: 22
            font.weight: Font.DemiBold
            elide: Text.ElideRight
            Layout.fillWidth: true
        }

        Label {
            text: headerTitle.detail
            color: colors.muted
            font.pixelSize: 12
            elide: Text.ElideRight
            Layout.fillWidth: true
        }
    }

    component Pill: Rectangle {
        property string text: ""
        property color tint: colors.accent
        implicitWidth: label.implicitWidth + 18
        implicitHeight: 26
        radius: 13
        color: Qt.rgba(tint.r, tint.g, tint.b, 0.12)

        Label {
            id: label
            anchors.centerIn: parent
            text: parent.text
            color: parent.tint
            font.pixelSize: 12
            font.weight: Font.Medium
        }
    }

    component Keycap: Rectangle {
        property string text: ""

        implicitWidth: Math.max(64, keyLabel.implicitWidth + 18)
        implicitHeight: 28
        radius: 6
        color: colors.surfaceAlt
        border.color: colors.border

        Label {
            id: keyLabel
            anchors.centerIn: parent
            text: parent.text
            color: colors.text
            font.pixelSize: 12
            font.weight: Font.DemiBold
        }
    }

    component HeaderBar: Rectangle {
        color: colors.window
        implicitHeight: 72
        Layout.fillWidth: true

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: root.pageMargin
            anchors.rightMargin: root.pageMargin
            spacing: 16

            HeaderTitle {
                title: root.pageIndex === 0
                    ? (app.hasResults ? "Review Markdown" : "Convert to Markdown")
                    : root.pageIndex === 1 ? "Settings" : "Help"
                detail: root.pageIndex === 0
                    ? (app.hasResults
                        ? "Inspect converted output, then copy or save Markdown."
                        : "Add documents or a webpage, review the Markdown, then save clean output.")
                    : root.pageIndex === 1
                        ? "Set export, theme, and OCR defaults."
                        : "Project links, OCR references, and shortcuts."
                Layout.fillWidth: true
            }

            Pill {
                text: app.statusText
                tint: app.converting ? colors.accent : colors.muted
            }
        }
    }

    component WorkspaceStats: RowLayout {
        spacing: 8

        MetricPill {
            label: "FILES"
            value: app.queueCount.toString()
            backgroundColor: colors.surfaceAlt
            borderColor: colors.border
            textColor: colors.text
            mutedTextColor: colors.muted
        }

        MetricPill {
            label: "DONE"
            value: app.progress + "%"
            backgroundColor: colors.surfaceAlt
            borderColor: colors.border
            textColor: colors.text
            mutedTextColor: colors.muted
        }

        MetricPill {
            label: "SAVE"
            value: app.saveCombined ? "Combined" : "Separate"
            backgroundColor: colors.surfaceAlt
            borderColor: colors.border
            textColor: colors.text
            mutedTextColor: colors.muted
        }
    }

    component ThemeToggleRow: ToggleRow {
        accentColor: colors.accent
        trackColor: colors.surfaceAlt
        handleColor: colors.surface
        borderColor: colors.border
        focusColor: colors.accent
    }

    component ThemeComboBox: AppComboBox {
        surfaceColor: colors.input
        popupColor: colors.surface
        hoverColor: colors.surfaceAlt
        borderColor: colors.border
        accentColor: colors.accent
        textColor: colors.text
        mutedTextColor: colors.muted
    }

    component ThemeSpinBox: AppSpinBox {
        surfaceColor: colors.input
        stepColor: colors.surfaceAlt
        hoverColor: colors.actionSoft
        borderColor: colors.border
        accentColor: colors.accent
        textColor: colors.text
        mutedTextColor: colors.muted
    }

    component ThemeProgressBar: ProgressBar {
        id: progressControl

        from: 0
        to: 100
        implicitHeight: 6

        background: Rectangle {
            implicitHeight: 6
            radius: 3
            color: colors.surfaceAlt
        }

        contentItem: Item {
            implicitHeight: 6

            Rectangle {
                width: progressControl.visualPosition * parent.width
                height: parent.height
                radius: 3
                color: colors.accent
            }
        }
    }

    component FieldGroup: ColumnLayout {
        id: fieldGroup

        property string label: ""
        property string detail: ""
        default property alias content: fieldBody.data

        spacing: 6
        Layout.fillWidth: true

        ColumnLayout {
            spacing: 2
            Layout.fillWidth: true

            Label {
                text: fieldGroup.label
                visible: fieldGroup.label.length > 0
                color: colors.text
                font.pixelSize: 12
                font.weight: Font.Medium
                Layout.fillWidth: true
            }

            Label {
                text: fieldGroup.detail
                visible: fieldGroup.detail.length > 0
                color: colors.muted
                font.pixelSize: 11
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }
        }

        ColumnLayout {
            id: fieldBody

            spacing: 8
            Layout.fillWidth: true
        }
    }

    component WorkspacePage: Item {
        Layout.fillWidth: true
        Layout.fillHeight: true

        DropArea {
            anchors.fill: parent
            enabled: !app.converting
            onDropped: drop => {
                if (drop.hasUrls)
                    app.addFiles(drop.urls)
            }
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.leftMargin: root.pageMargin
            anchors.rightMargin: root.pageMargin
            anchors.topMargin: 10
            anchors.bottomMargin: root.pageMargin
            spacing: 14

            UrlBar {
                compact: app.hasQueue || app.hasResults
            }

            Loader {
                Layout.fillWidth: true
                Layout.fillHeight: true
                sourceComponent: app.hasResults ? resultsView : app.hasQueue ? queueView : emptyView
            }
        }
    }

    component UrlBar: Item {
        id: urlBar

        property bool compact: false

        Layout.fillWidth: true
        implicitHeight: 44

        Loader {
            anchors.fill: parent
            sourceComponent: compactUrlBar
        }

        Component {
            id: compactUrlBar

            RowLayout {
                spacing: 10

                AppTextField {
                    id: compactUrlInput
                    enabled: !app.converting
                    placeholderText: urlBar.compact ? "Add webpage URL" : "Paste webpage URL"
                    surfaceColor: colors.input
                    borderColor: colors.border
                    accentColor: colors.accent
                    textColor: colors.text
                    placeholderColor: colors.subtle
                    Layout.fillWidth: true
                    onAccepted: {
                        app.addUrl(text)
                        text = ""
                    }
                }

                AppButton {
                    text: "Add webpage"
                    enabled: !app.converting
                    primary: !app.hasResults && !app.converting
                    iconName: "link"
                    accentColor: colors.action
                    primaryTextColor: colors.onAction
                    surfaceColor: colors.surfaceAlt
                    borderColor: colors.border
                    textColor: colors.text
                    onClicked: {
                        app.addUrl(compactUrlInput.text)
                        compactUrlInput.text = ""
                    }
                }
            }
        }
    }

    Component {
        id: emptyView

        SectionPanel {
            title: ""
            subtitle: ""
            surfaceColor: colors.surface
            borderColor: colors.border
            textColor: colors.text
            mutedTextColor: colors.muted
            Layout.fillWidth: true
            Layout.fillHeight: true

            Item {
                Layout.fillWidth: true
                Layout.fillHeight: true

                ColumnLayout {
                    anchors.centerIn: parent
                    width: Math.min(parent.width - 80, 520)
                    spacing: 16

                    Rectangle {
                        width: 58
                        height: 58
                        radius: 8
                        color: colors.actionSoft
                        border.color: Qt.rgba(colors.action.r, colors.action.g, colors.action.b, 0.35)
                        Layout.alignment: Qt.AlignHCenter

                        Icon {
                            anchors.centerIn: parent
                            name: "folder-plus"
                            size: 26
                            color: colors.action
                        }
                    }

                    Label {
                        text: "Start with files or a webpage"
                        color: colors.text
                        font.pixelSize: 20
                        font.weight: Font.DemiBold
                        horizontalAlignment: Text.AlignHCenter
                        Layout.fillWidth: true
                    }

                    Label {
                        text: "Drop files anywhere in this window, choose files from your system, or paste a URL above."
                        color: colors.muted
                        font.pixelSize: 13
                        wrapMode: Text.WordWrap
                        horizontalAlignment: Text.AlignHCenter
                        Layout.fillWidth: true
                    }

                    AppButton {
                        text: "Choose files"
                        primary: true
                        iconName: "folder-plus"
                        accentColor: colors.action
                        primaryTextColor: colors.onAction
                        Layout.alignment: Qt.AlignHCenter
                        onClicked: openFileDialog.open()
                    }
                }
            }
        }
    }

    Component {
        id: queueView

        RowLayout {
            spacing: 14
            Layout.fillWidth: true
            Layout.fillHeight: true

            ColumnLayout {
                spacing: 14
                Layout.fillWidth: true
                Layout.fillHeight: true

                SectionPanel {
                    title: "Documents"
                    subtitle: "Files and webpages are converted in order."
                    surfaceColor: colors.surface
                    borderColor: colors.border
                    textColor: colors.text
                    mutedTextColor: colors.muted
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    RowLayout {
                        Layout.fillWidth: true

                        AppButton {
                            text: "Add files"
                            enabled: !app.converting
                            primary: !app.converting
                            iconName: "folder-plus"
                            accentColor: colors.action
                            primaryTextColor: colors.onAction
                            surfaceColor: colors.surfaceAlt
                            borderColor: colors.border
                            textColor: colors.text
                            onClicked: openFileDialog.open()
                        }

                        AppButton {
                            text: "Clear"
                            enabled: !app.converting
                            subtle: true
                            iconName: "x"
                            textColor: colors.muted
                            onClicked: app.clearQueue()
                        }

                        Item {
                            Layout.fillWidth: true
                        }
                    }

                    ListView {
                        id: queueList
                        clip: true
                        spacing: 8
                        model: app.queueModel
                        Layout.fillWidth: true
                        Layout.fillHeight: true

                        delegate: Rectangle {
                            required property int index
                            required property string name
                            required property string source
                            required property string kind

                            width: queueList.width
                            height: 58
                            radius: 9
                            color: colors.surfaceAlt
                            border.color: colors.border

                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 10
                                spacing: 10

                                Rectangle {
                                    width: 36
                                    height: 36
                                    radius: 8
                                    color: kind === "URL"
                                        ? Qt.rgba(colors.accent.r, colors.accent.g, colors.accent.b, 0.12)
                                        : Qt.rgba(colors.muted.r, colors.muted.g, colors.muted.b, 0.12)
                                    border.color: kind === "URL"
                                        ? Qt.rgba(colors.accent.r, colors.accent.g, colors.accent.b, 0.28)
                                        : Qt.rgba(colors.muted.r, colors.muted.g, colors.muted.b, 0.22)

                                    Icon {
                                        anchors.centerIn: parent
                                        name: kind === "URL" ? "link" : "file-text"
                                        size: 17
                                        color: kind === "URL" ? colors.accent : colors.muted
                                    }
                                }

                                ColumnLayout {
                                    spacing: 2
                                    Layout.fillWidth: true

                                    Label {
                                        text: name
                                        color: colors.text
                                        font.pixelSize: 13
                                        font.weight: Font.Medium
                                        elide: Text.ElideMiddle
                                        Layout.fillWidth: true
                                    }

                                    Label {
                                        text: source
                                        color: colors.muted
                                        font.pixelSize: 11
                                        elide: Text.ElideMiddle
                                        Layout.fillWidth: true
                                    }
                                }

                                AppButton {
                                    text: "Remove"
                                    enabled: !app.converting
                                    subtle: true
                                    iconName: "trash-2"
                                    textColor: colors.muted
                                    onClicked: app.removeQueued(index)
                                }
                            }
                        }
                    }
                }

                SectionPanel {
                    title: "Markdown review"
                    subtitle: root.height < 700 ? "" : "Converted output opens here before export."
                    surfaceColor: colors.surface
                    borderColor: colors.border
                    textColor: colors.text
                    mutedTextColor: colors.muted
                    Layout.fillWidth: true
                    Layout.preferredHeight: root.height < 700 ? 112 : 178

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        radius: 8
                        color: colors.input
                        border.color: colors.border

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 12
                            spacing: 10

                            Icon {
                                name: "panel-right"
                                size: 18
                                color: colors.muted
                                Layout.alignment: Qt.AlignTop
                            }

                            ColumnLayout {
                                spacing: 3
                                Layout.fillWidth: true

                                Label {
                                    text: "Preview after conversion"
                                    color: colors.text
                                    font.pixelSize: 12
                                    font.weight: Font.Medium
                                    Layout.fillWidth: true
                                }

                                Label {
                                    text: root.height < 700
                                        ? "Converted Markdown opens here."
                                        : "Inspect rendered Markdown or source text, then export combined or separate files."
                                    color: colors.muted
                                    font.pixelSize: 12
                                    wrapMode: Text.WordWrap
                                    Layout.fillWidth: true
                                }
                            }
                        }
                    }
                }
            }

            InspectorRail {
                title: app.converting ? "Converting" : "Convert"
                subtitle: app.queueCount + " item" + (app.queueCount === 1 ? "" : "s") + " queued"
                surfaceColor: colors.window
                borderColor: colors.border
                textColor: colors.text
                mutedTextColor: colors.muted
                Layout.preferredWidth: 360
                Layout.minimumWidth: 330
                Layout.fillHeight: true

                ScrollView {
                    id: conversionRailScroll
                    clip: true
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    ColumnLayout {
                        width: conversionRailScroll.availableWidth
                        spacing: 12

                        WorkspaceStats {
                            Layout.fillWidth: true
                        }

                        Rectangle {
                            height: 1
                            color: colors.border
                            Layout.fillWidth: true
                        }

                        ThemeToggleRow {
                            title: "OCR"
                            detail: "Provider: " + (app.ocrProvider === "glmocr" ? "GLM-OCR" : "Azure/Tesseract") + ". Use for scanned or image-heavy inputs."
                            enabled: !app.converting
                            checked: app.ocrEnabled
                            textColor: colors.text
                            mutedTextColor: colors.muted
                            onToggled: checked => app.setOcrEnabled(checked)
                            Layout.fillWidth: true
                        }

                        ThemeToggleRow {
                            title: "Preserve PDF images"
                            detail: "Extract PDF page images and keep relative asset links on export."
                            enabled: !app.converting
                            checked: app.preservePdfImages
                            textColor: colors.text
                            mutedTextColor: colors.muted
                            onToggled: checked => app.setPreservePdfImages(checked)
                            Layout.fillWidth: true
                        }

                        ThemeToggleRow {
                            title: "Preserve DOCX images"
                            detail: "Extract embedded document images and keep relative asset links on export."
                            enabled: !app.converting
                            checked: app.preserveDocxImages
                            textColor: colors.text
                            mutedTextColor: colors.muted
                            onToggled: checked => app.setPreserveDocxImages(checked)
                            Layout.fillWidth: true
                        }

                        Rectangle {
                            visible: !app.converting
                            height: 1
                            color: colors.border
                            Layout.fillWidth: true
                        }

                        ColumnLayout {
                            visible: !app.converting
                            spacing: 6
                            Layout.fillWidth: true

                            Label {
                                text: "Output"
                                color: colors.text
                                font.pixelSize: 13
                                font.weight: Font.Medium
                                Layout.fillWidth: true
                            }

                            RowLayout {
                                spacing: 8
                                Layout.fillWidth: true

                                Icon {
                                    name: "save"
                                    size: 15
                                    color: colors.muted
                                }

                                Label {
                                    text: app.saveCombined ? "Combined Markdown file" : "Separate Markdown files"
                                    color: colors.muted
                                    font.pixelSize: 12
                                    elide: Text.ElideRight
                                    Layout.fillWidth: true
                                }
                            }

                            Label {
                                text: app.saveToSourceFolder
                                    ? "Default: source folders"
                                    : (app.outputFolder.length > 0 ? app.outputFolder : "Choose location when saving")
                                color: colors.subtle
                                font.pixelSize: 11
                                elide: Text.ElideMiddle
                                Layout.fillWidth: true
                            }

                            AppButton {
                                text: "Set folder"
                                subtle: true
                                iconName: "folder-plus"
                                surfaceColor: colors.surfaceAlt
                                borderColor: colors.border
                                textColor: colors.text
                                onClicked: outputFolderDialog.open()
                            }
                        }

                        Rectangle {
                            height: 1
                            color: colors.border
                            Layout.fillWidth: true
                        }

                        ThemeProgressBar {
                            visible: !app.converting && app.progress > 0
                            value: app.progress
                            Layout.fillWidth: true
                        }

                        Label {
                            visible: !app.converting
                            text: app.statusText
                            color: colors.muted
                            font.pixelSize: 12
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                        }
                    }
                }

                ColumnLayout {
                    visible: app.converting
                    Layout.fillWidth: true
                    spacing: 6

                    ThemeProgressBar {
                        value: app.progress
                        Layout.fillWidth: true
                    }

                    Label {
                        text: app.statusText
                        color: colors.muted
                        font.pixelSize: 12
                        elide: Text.ElideMiddle
                        Layout.fillWidth: true
                    }
                }

                RowLayout {
                    visible: app.converting
                    Layout.fillWidth: true
                    spacing: 8

                    AppButton {
                        text: app.paused ? "Resume" : "Pause"
                        enabled: app.converting
                        iconName: app.paused ? "play" : "pause"
                        surfaceColor: colors.surfaceAlt
                        borderColor: colors.border
                        textColor: colors.text
                        onClicked: app.togglePause()
                    }

                    AppButton {
                        text: "Cancel"
                        enabled: app.converting
                        iconName: "x"
                        surfaceColor: colors.surfaceAlt
                        borderColor: colors.border
                        textColor: colors.text
                        onClicked: app.cancel()
                    }
                }

                AppButton {
                    text: app.converting
                        ? "Converting"
                        : "Convert " + app.queueCount + " item" + (app.queueCount === 1 ? "" : "s")
                    enabled: !app.converting
                    primary: true
                    iconName: "play"
                    accentColor: colors.action
                    primaryTextColor: colors.onAction
                    Layout.fillWidth: true
                    onClicked: app.convert()
                }
            }
        }
    }

    Component {
        id: resultsView

        RowLayout {
            spacing: 16
            Layout.fillWidth: true
            Layout.fillHeight: true

            SectionPanel {
                title: "Converted files"
                subtitle: "Select an item to inspect the generated Markdown."
                surfaceColor: colors.surface
                borderColor: colors.border
                textColor: colors.text
                mutedTextColor: colors.muted
                Layout.preferredWidth: 330
                Layout.fillHeight: true

                RowLayout {
                    Layout.fillWidth: true

                    AppButton {
                        text: "Back to queue"
                        subtle: true
                        iconName: "rotate-ccw"
                        textColor: colors.text
                        onClicked: app.clearResults()
                    }

                    AppButton {
                        text: "Start new"
                        subtle: true
                        iconName: "file-text"
                        textColor: colors.muted
                        onClicked: {
                            app.clearResults()
                            app.clearQueue()
                        }
                    }

                    Item {
                        Layout.fillWidth: true
                    }
                }

                ListView {
                    id: resultList
                    model: app.resultModel
                    clip: true
                    spacing: 8
                    currentIndex: app.selectedResultIndex
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    delegate: Rectangle {
                        id: resultRow

                        required property int index
                        required property string name
                        required property string backend
                        required property bool failed
                        required property int wordCount
                        property bool selected: index === resultList.currentIndex

                        width: resultList.width
                        height: 68
                        radius: 9
                        color: selected
                            ? Qt.rgba(colors.accent.r, colors.accent.g, colors.accent.b, dark ? 0.10 : 0.08)
                            : rowMouse.containsMouse
                                ? Qt.rgba(colors.accent.r, colors.accent.g, colors.accent.b, dark ? 0.08 : 0.06)
                                : colors.surfaceAlt
                        border.color: selected
                            ? Qt.rgba(colors.accent.r, colors.accent.g, colors.accent.b, dark ? 0.70 : 0.62)
                            : colors.border

                        MouseArea {
                            id: rowMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            onClicked: app.selectResult(index)
                        }

                        Rectangle {
                            visible: resultRow.selected
                            width: 3
                            height: parent.height - 18
                            radius: 2
                            color: colors.accent
                            anchors.left: parent.left
                            anchors.leftMargin: 8
                            anchors.verticalCenter: parent.verticalCenter
                        }

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 10
                            spacing: 10

                            Rectangle {
                                width: 36
                                height: 36
                                radius: 8
                                color: failed
                                    ? Qt.rgba(colors.danger.r, colors.danger.g, colors.danger.b, 0.12)
                                    : Qt.rgba(colors.success.r, colors.success.g, colors.success.b, 0.14)
                                border.color: failed
                                    ? Qt.rgba(colors.danger.r, colors.danger.g, colors.danger.b, 0.28)
                                    : Qt.rgba(colors.success.r, colors.success.g, colors.success.b, 0.26)

                                Icon {
                                    anchors.centerIn: parent
                                    name: failed ? "file-x" : "file-check"
                                    size: 17
                                    color: failed ? colors.danger : colors.success
                                }
                            }

                            ColumnLayout {
                                spacing: 3
                                Layout.fillWidth: true

                                Label {
                                    text: name
                                    color: colors.text
                                    font.pixelSize: 13
                                    font.weight: Font.Medium
                                    elide: Text.ElideMiddle
                                    Layout.fillWidth: true
                                }

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 8

                                    Label {
                                        text: failed ? "Failed" : backend
                                        color: failed ? colors.danger : colors.muted
                                        font.pixelSize: 11
                                    }

                                    Label {
                                        text: wordCount + " words"
                                        color: colors.muted
                                        font.pixelSize: 11
                                    }
                                }
                            }
                        }
                    }
                }
            }

            SectionPanel {
                title: app.selectedResultFailed ? "Conversion failed" : "Markdown preview"
                subtitle: app.selectedResultFailed
                    ? "Review the error, then return to the queue or try another input."
                    : "Check the rendered view or source Markdown before export."
                surfaceColor: colors.surface
                borderColor: colors.border
                textColor: colors.text
                mutedTextColor: colors.muted
                Layout.fillWidth: true
                Layout.fillHeight: true

                ColumnLayout {
                    id: previewToolbar

                    property bool compactActions: width < 420

                    Layout.fillWidth: true
                    spacing: 8

                    RowLayout {
                        Layout.fillWidth: true

                        AppButton {
                            visible: !app.selectedResultFailed
                            text: "Rendered"
                            primary: app.previewMode === "rendered"
                            subtle: app.previewMode !== "rendered"
                            accentColor: colors.action
                            primaryTextColor: colors.onAction
                            textColor: colors.text
                            onClicked: app.setPreviewMode("rendered")
                        }

                        AppButton {
                            visible: !app.selectedResultFailed
                            text: "Source"
                            primary: app.previewMode === "raw"
                            subtle: app.previewMode !== "raw"
                            accentColor: colors.action
                            primaryTextColor: colors.onAction
                            textColor: colors.text
                            onClicked: app.setPreviewMode("raw")
                        }

                        Item {
                            Layout.fillWidth: true
                        }

                        AppButton {
                            visible: !previewToolbar.compactActions
                            text: app.selectedResultFailed ? "Copy details" : "Copy"
                            primary: app.selectedResultFailed
                            iconName: "copy"
                            accentColor: colors.action
                            primaryTextColor: colors.onAction
                            surfaceColor: colors.surfaceAlt
                            borderColor: colors.border
                            textColor: colors.text
                            onClicked: app.copySelectedMarkdown()
                        }

                        AppButton {
                            visible: !previewToolbar.compactActions
                            text: app.saveCombined ? "Save as one file" : "Save files"
                            primary: !app.selectedResultFailed
                            iconName: "save"
                            accentColor: colors.action
                            primaryTextColor: colors.onAction
                            surfaceColor: colors.surfaceAlt
                            borderColor: colors.border
                            textColor: colors.text
                            onClicked: root.requestSave()
                        }
                    }

                    RowLayout {
                        visible: previewToolbar.compactActions
                        Layout.fillWidth: true

                        Item {
                            Layout.fillWidth: true
                        }

                        AppButton {
                            text: app.selectedResultFailed ? "Copy details" : "Copy"
                            primary: app.selectedResultFailed
                            iconName: "copy"
                            accentColor: colors.action
                            primaryTextColor: colors.onAction
                            surfaceColor: colors.surfaceAlt
                            borderColor: colors.border
                            textColor: colors.text
                            onClicked: app.copySelectedMarkdown()
                        }

                        AppButton {
                            text: "Save"
                            primary: !app.selectedResultFailed
                            iconName: "save"
                            accentColor: colors.action
                            primaryTextColor: colors.onAction
                            surfaceColor: colors.surfaceAlt
                            borderColor: colors.border
                            textColor: colors.text
                            onClicked: root.requestSave()
                        }
                    }
                }

                ScrollView {
                    id: previewScroll
                    clip: true
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    contentWidth: availableWidth
                    contentHeight: previewCanvas.height

                    Item {
                        id: previewCanvas

                        width: previewScroll.availableWidth
                        height: Math.max(
                            previewScroll.availableHeight,
                            app.selectedResultFailed
                                ? previewScroll.availableHeight
                                : app.previewMode === "rendered"
                                ? renderedPreview.contentHeight + renderedPreview.topPadding + renderedPreview.bottomPadding
                                : rawPreview.contentHeight + rawPreview.topPadding + rawPreview.bottomPadding
                        )

                        Rectangle {
                            id: failedPreview

                            visible: app.selectedResultFailed
                            anchors.fill: parent
                            radius: 9
                            color: colors.document
                            border.color: Qt.rgba(colors.danger.r, colors.danger.g, colors.danger.b, dark ? 0.55 : 0.40)

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 18
                                spacing: 12

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 10

                                    Rectangle {
                                        width: 34
                                        height: 34
                                        radius: 8
                                        color: Qt.rgba(colors.danger.r, colors.danger.g, colors.danger.b, dark ? 0.18 : 0.10)
                                        border.color: Qt.rgba(colors.danger.r, colors.danger.g, colors.danger.b, dark ? 0.40 : 0.28)

                                        Icon {
                                            anchors.centerIn: parent
                                            name: "file-x"
                                            size: 17
                                            color: colors.danger
                                        }
                                    }

                                    ColumnLayout {
                                        spacing: 3
                                        Layout.fillWidth: true

                                        Label {
                                            text: "This input could not be converted"
                                            color: colors.text
                                            font.pixelSize: 15
                                            font.weight: Font.DemiBold
                                            Layout.fillWidth: true
                                        }

                                        Label {
                                            text: "The details below can be copied for troubleshooting."
                                            color: colors.muted
                                            font.pixelSize: 12
                                            Layout.fillWidth: true
                                        }
                                    }
                                }

                                TextArea {
                                    text: app.selectedMarkdown
                                    textFormat: TextEdit.PlainText
                                    readOnly: true
                                    wrapMode: TextEdit.Wrap
                                    selectByMouse: true
                                    color: colors.text
                                    selectedTextColor: "#FFFFFF"
                                    selectionColor: colors.danger
                                    font.pixelSize: 13
                                    padding: 12
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 100
                                    background: Rectangle {
                                        color: colors.input
                                        radius: 8
                                        border.color: colors.border
                                    }
                                }

                                Item {
                                    Layout.fillHeight: true
                                }
                            }
                        }

                        TextArea {
                            id: renderedPreview

                            visible: !app.selectedResultFailed && app.previewMode === "rendered"
                            anchors.fill: parent
                            text: app.selectedPreviewHtml
                            textFormat: TextEdit.RichText
                            readOnly: true
                            wrapMode: TextEdit.Wrap
                            selectByMouse: true
                            color: colors.text
                            selectedTextColor: "#FFFFFF"
                            selectionColor: colors.accent
                            font.pixelSize: 13
                            font.family: root.font.family
                            leftPadding: 18
                            rightPadding: 18
                            topPadding: 18
                            bottomPadding: 18
                            background: Rectangle {
                                color: colors.document
                                radius: 9
                                border.color: Qt.rgba(colors.border.r, colors.border.g, colors.border.b, dark ? 0.90 : 0.78)
                            }
                        }

                        TextArea {
                            id: rawPreview

                            visible: !app.selectedResultFailed && app.previewMode === "raw"
                            anchors.fill: parent
                            text: app.selectedMarkdown
                            textFormat: TextEdit.PlainText
                            readOnly: true
                            wrapMode: TextEdit.Wrap
                            selectByMouse: true
                            color: colors.text
                            selectedTextColor: "#FFFFFF"
                            selectionColor: colors.accent
                            font.pixelSize: 13
                            font.family: Qt.platform.os === "windows" ? "Cascadia Mono" : Qt.platform.os === "osx" ? "Menlo" : "monospace"
                            padding: 14
                            background: Rectangle {
                                color: colors.input
                                radius: 9
                                border.color: Qt.rgba(colors.border.r, colors.border.g, colors.border.b, dark ? 0.90 : 0.78)
                            }
                        }
                    }
                }
            }
        }
    }

    component SettingsPage: ScrollView {
        id: settingsPage
        Layout.fillWidth: true
        Layout.fillHeight: true
        clip: true
        ScrollBar.vertical.policy: ScrollBar.AsNeeded

        ColumnLayout {
            width: Math.min(settingsPage.width - 48, 760)
            x: 24
            spacing: 16

            SectionPanel {
                title: "Output"
                subtitle: "Set where Markdown is saved and how batches are written."
                surfaceColor: colors.surface
                borderColor: colors.border
                textColor: colors.text
                mutedTextColor: colors.muted
                Layout.fillWidth: true

                FieldGroup {
                    label: "Default folder"
                    detail: "Leave empty to choose a location when saving."
                    Layout.fillWidth: true

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10

                        AppTextField {
                            text: app.outputFolder
                            placeholderText: "No default folder set"
                            surfaceColor: colors.input
                            borderColor: colors.border
                            accentColor: colors.accent
                            textColor: colors.text
                            placeholderColor: colors.subtle
                            Layout.fillWidth: true
                            onEditingFinished: app.setOutputFolder(text)
                        }

                        AppButton {
                            text: "Browse"
                            surfaceColor: colors.surfaceAlt
                            borderColor: colors.border
                            textColor: colors.text
                            onClicked: outputFolderDialog.open()
                        }
                    }
                }

                ThemeToggleRow {
                    title: "Combined save mode"
                    detail: "Save one Markdown document by default instead of one file per input."
                    checked: app.saveCombined
                    textColor: colors.text
                    mutedTextColor: colors.muted
                    onToggled: checked => app.setSaveCombined(checked)
                    Layout.fillWidth: true
                }

                ThemeToggleRow {
                    title: "Prefer source folder"
                    detail: "Use each input file folder when separate exports are saved."
                    checked: app.saveToSourceFolder
                    textColor: colors.text
                    mutedTextColor: colors.muted
                    onToggled: checked => app.setSaveToSourceFolder(checked)
                    Layout.fillWidth: true
                }

                FieldGroup {
                    label: "Batch size"
                    detail: "Limit how many sources convert in one worker batch."
                    Layout.fillWidth: true

                    ThemeSpinBox {
                        from: 1
                        to: 10
                        value: app.batchSize
                        onValueModified: app.setBatchSize(value)
                    }
                }
            }

            SectionPanel {
                title: "Appearance"
                subtitle: "Solarized Light for daytime work, Nord Dark for low-light sessions."
                surfaceColor: colors.surface
                borderColor: colors.border
                textColor: colors.text
                mutedTextColor: colors.muted
                Layout.fillWidth: true

                FieldGroup {
                    label: "Theme"
                    detail: "Use explicit palettes or follow the operating system."
                    Layout.fillWidth: true

                    ThemeComboBox {
                        model: ["Solarized Light", "Nord Dark", "System"]
                        currentIndex: app.themeMode === "dark" ? 1 : app.themeMode === "system" ? 2 : 0
                        onActivated: index => app.setThemeMode(index === 1 ? "dark" : index === 2 ? "system" : "light")
                        Layout.fillWidth: true
                    }
                }
            }

            SectionPanel {
                title: "OCR"
                subtitle: "Use OCR only for scanned PDFs, screenshots, or image-heavy files."
                surfaceColor: colors.surface
                borderColor: colors.border
                textColor: colors.text
                mutedTextColor: colors.muted
                Layout.fillWidth: true

                ThemeToggleRow {
                    title: "OCR enabled"
                    detail: "Use OCR for scanned PDFs and images."
                    checked: app.ocrEnabled
                    textColor: colors.text
                    mutedTextColor: colors.muted
                    onToggled: checked => app.setOcrEnabled(checked)
                    Layout.fillWidth: true
                }

                FieldGroup {
                    label: "Provider"
                    detail: "GLM-OCR is best for image-heavy pages; Azure/Tesseract keeps the legacy path."
                    visible: app.ocrEnabled
                    Layout.fillWidth: true

                    ThemeComboBox {
                        model: ["Azure/Tesseract", "GLM-OCR"]
                        currentIndex: app.ocrProvider === "glmocr" ? 1 : 0
                        onActivated: index => app.setOcrProvider(index === 1 ? "glmocr" : "legacy")
                        Layout.fillWidth: true
                    }
                }

                FieldGroup {
                    label: app.ocrProvider === "glmocr" ? "Fallback Azure endpoint" : "Azure endpoint"
                    detail: app.ocrProvider === "glmocr" ? "Optional endpoint used only if GLM-OCR falls back." : ""
                    visible: root.showLegacyOcrSettings()
                    Layout.fillWidth: true

                    AppTextField {
                        text: app.docintelEndpoint
                        placeholderText: "https://example.cognitiveservices.azure.com/"
                        surfaceColor: colors.input
                        borderColor: colors.border
                        accentColor: colors.accent
                        textColor: colors.text
                        placeholderColor: colors.subtle
                        Layout.fillWidth: true
                        onEditingFinished: app.setDocintelEndpoint(text)
                    }
                }

                FieldGroup {
                    label: app.ocrProvider === "glmocr" ? "Fallback Tesseract languages" : "Tesseract languages"
                    detail: app.ocrProvider === "glmocr" ? "Optional local OCR languages used only if fallback runs." : ""
                    visible: root.showLegacyOcrSettings()
                    Layout.fillWidth: true

                    AppTextField {
                        text: app.ocrLanguages
                        placeholderText: "eng or eng+deu"
                        surfaceColor: colors.input
                        borderColor: colors.border
                        accentColor: colors.accent
                        textColor: colors.text
                        placeholderColor: colors.subtle
                        Layout.fillWidth: true
                        onEditingFinished: app.setOcrLanguages(text)
                    }
                }

                FieldGroup {
                    label: app.ocrProvider === "glmocr" ? "Fallback Tesseract executable" : "Tesseract executable"
                    detail: app.ocrProvider === "glmocr" ? "Optional local executable used only if fallback runs." : ""
                    visible: root.showLegacyOcrSettings()
                    Layout.fillWidth: true

                    AppTextField {
                        text: app.tesseractPath
                        placeholderText: "Optional executable path"
                        surfaceColor: colors.input
                        borderColor: colors.border
                        accentColor: colors.accent
                        textColor: colors.text
                        placeholderColor: colors.subtle
                        Layout.fillWidth: true
                        onEditingFinished: app.setTesseractPath(text)
                    }
                }
            }

            SectionPanel {
                title: "GLM-OCR"
                subtitle: "Connect to the hosted API, Ollama, or an SDK server."
                surfaceColor: colors.surface
                borderColor: colors.border
                textColor: colors.text
                mutedTextColor: colors.muted
                visible: app.ocrEnabled && app.ocrProvider === "glmocr"
                Layout.fillWidth: true

                ThemeToggleRow {
                    title: "Fallback to Azure/Tesseract"
                    detail: "Use the legacy OCR path if GLM-OCR fails."
                    checked: app.ocrFallbackEnabled
                    textColor: colors.text
                    mutedTextColor: colors.muted
                    onToggled: checked => app.setOcrFallbackEnabled(checked)
                    Layout.fillWidth: true
                }

                FieldGroup {
                    label: "Mode"
                    Layout.fillWidth: true

                    ThemeComboBox {
                        model: ["Official API", "Ollama", "SDK Server"]
                        currentIndex: app.glmocrMode === "ollama" ? 1 : app.glmocrMode === "sdk_server" ? 2 : 0
                        onActivated: index => app.setGlmocrMode(index === 1 ? "ollama" : index === 2 ? "sdk_server" : "maas")
                        Layout.fillWidth: true
                    }
                }

                FieldGroup {
                    label: "Ollama host"
                    visible: app.glmocrMode === "ollama"
                    Layout.fillWidth: true

                    AppTextField {
                        text: app.glmocrOllamaHost
                        placeholderText: "127.0.0.1"
                        surfaceColor: colors.input
                        borderColor: colors.border
                        accentColor: colors.accent
                        textColor: colors.text
                        placeholderColor: colors.subtle
                        Layout.fillWidth: true
                        onEditingFinished: app.setGlmocrOllamaHost(text)
                    }
                }

                RowLayout {
                    visible: app.glmocrMode === "ollama"
                    Layout.fillWidth: true
                    spacing: 10

                    FieldGroup {
                        label: "Port"
                        Layout.preferredWidth: 150
                        Layout.fillWidth: false

                        ThemeSpinBox {
                            from: 1
                            to: 65535
                            value: app.glmocrOllamaPort
                            textFromValue: function(value, locale) { return value.toString() }
                            onValueModified: app.setGlmocrOllamaPort(value)
                        }
                    }

                    FieldGroup {
                        label: "Model"
                        Layout.fillWidth: true

                        AppTextField {
                            text: app.glmocrOllamaModel
                            placeholderText: "glm-ocr:latest"
                            surfaceColor: colors.input
                            borderColor: colors.border
                            accentColor: colors.accent
                            textColor: colors.text
                            placeholderColor: colors.subtle
                            Layout.fillWidth: true
                            onEditingFinished: app.setGlmocrOllamaModel(text)
                        }
                    }
                }

                FieldGroup {
                    label: "SDK server endpoint"
                    visible: app.glmocrMode === "sdk_server"
                    Layout.fillWidth: true

                    AppTextField {
                        text: app.glmocrSdkServerUrl
                        placeholderText: "http://127.0.0.1:5002/glmocr/parse"
                        surfaceColor: colors.input
                        borderColor: colors.border
                        accentColor: colors.accent
                        textColor: colors.text
                        placeholderColor: colors.subtle
                        Layout.fillWidth: true
                        onEditingFinished: app.setGlmocrSdkServerUrl(text)
                    }
                }
            }

            Item {
                height: 24
            }
        }
    }

    component HelpPage: ScrollView {
        id: helpPage
        Layout.fillWidth: true
        Layout.fillHeight: true
        clip: true

        ColumnLayout {
            width: Math.min(helpPage.width - 48, 920)
            x: 24
            y: 24
            spacing: 16

            SectionPanel {
                title: "Common tasks"
                subtitle: "Quick guidance for the conversion workflow."
                surfaceColor: colors.surface
                borderColor: colors.border
                textColor: colors.text
                mutedTextColor: colors.muted
                Layout.fillWidth: true

                Repeater {
                    model: [
                        { icon: "folder-plus", title: "Add documents", detail: "Drop files into the window or choose files from your system." },
                        { icon: "link", title: "Convert a webpage", detail: "Paste an http:// or https:// URL in the bar at the top of the workspace." },
                        { icon: "file-text", title: "Use OCR only when needed", detail: "Enable OCR for scanned PDFs, screenshots, and image-heavy files." },
                        { icon: "save", title: "Save Markdown", detail: "Use combined mode for one document, or separate mode for one Markdown file per input." }
                    ]

                    delegate: RowLayout {
                        spacing: 10
                        Layout.fillWidth: true

                        Rectangle {
                            width: 34
                            height: 34
                            radius: 8
                            color: Qt.rgba(colors.accent.r, colors.accent.g, colors.accent.b, 0.12)
                            border.color: Qt.rgba(colors.accent.r, colors.accent.g, colors.accent.b, 0.24)

                            Icon {
                                anchors.centerIn: parent
                                name: modelData.icon
                                size: 17
                                color: colors.accent
                            }
                        }

                        ColumnLayout {
                            spacing: 2
                            Layout.fillWidth: true

                            Label {
                                text: modelData.title
                                color: colors.text
                                font.pixelSize: 13
                                font.weight: Font.Medium
                                Layout.fillWidth: true
                            }

                            Label {
                                text: modelData.detail
                                color: colors.muted
                                font.pixelSize: 12
                                wrapMode: Text.WordWrap
                                Layout.fillWidth: true
                            }
                        }
                    }
                }
            }

            SectionPanel {
                title: "Reference links"
                subtitle: "Open project, release, OCR, and conversion references."
                surfaceColor: colors.surface
                borderColor: colors.border
                textColor: colors.text
                mutedTextColor: colors.muted
                Layout.fillWidth: true

                GridLayout {
                    columns: 2
                    columnSpacing: 10
                    rowSpacing: 10
                    Layout.fillWidth: true

                    Repeater {
                        model: [
                            { label: "Repository", url: "https://github.com/imadreamerboy/markitdown-gui" },
                            { label: "Releases", url: "https://github.com/imadreamerboy/markitdown-gui/releases" },
                            { label: "GLM-OCR", url: "https://github.com/zai-org/GLM-OCR" },
                            { label: "Tesseract", url: "https://github.com/tesseract-ocr/tesseract" },
                            { label: "Defuddle", url: "https://defuddle.md/docs" },
                            { label: "Azure OCR Pricing", url: "https://azure.microsoft.com/en-us/products/ai-foundry/tools/document-intelligence#Pricing" }
                        ]

                        delegate: AppButton {
                            text: modelData.label
                            iconName: "external-link"
                            surfaceColor: colors.surfaceAlt
                            borderColor: colors.border
                            textColor: colors.text
                            Layout.fillWidth: true
                            onClicked: app.openExternalUrl(modelData.url)
                        }
                    }
                }
            }

            SectionPanel {
                title: "Shortcuts"
                subtitle: "Keyboard actions for the main workspace."
                surfaceColor: colors.surface
                borderColor: colors.border
                textColor: colors.text
                mutedTextColor: colors.muted
                Layout.fillWidth: true

                GridLayout {
                    columns: helpPage.width < 760 ? 1 : 2
                    columnSpacing: 18
                    rowSpacing: 10
                    Layout.fillWidth: true

                    Repeater {
                        model: [
                            { key: "Ctrl+O", action: "Add files" },
                            { key: "Ctrl+B", action: "Convert queue" },
                            { key: "Ctrl+P", action: "Pause or resume" },
                            { key: "Ctrl+S", action: "Save Markdown" },
                            { key: "Ctrl+C", action: "Copy Markdown" },
                            { key: "Ctrl+L", action: "Clear queue" },
                            { key: "Ctrl+K", action: "Open Help" },
                            { key: "Esc", action: "Cancel conversion" }
                        ]

                        delegate: RowLayout {
                            spacing: 10
                            Layout.fillWidth: true

                            Keycap {
                                text: modelData.key
                            }

                            Label {
                                text: modelData.action
                                color: colors.muted
                                font.pixelSize: 13
                                elide: Text.ElideRight
                                Layout.fillWidth: true
                            }
                        }
                    }
                }
            }

            Item {
                height: 24
            }
        }
    }

    Rectangle {
        id: toast
        property string kind: "success"
        property string message: ""

        visible: false
        width: Math.min(420, parent.width - 48)
        height: toastLabel.implicitHeight + 24
        radius: 10
        color: kind === "error" ? (dark ? "#3A1E22" : "#FFF2F0") : (dark ? "#153222" : "#EEF8F0")
        border.color: kind === "error" ? colors.danger : colors.success
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: 24
        z: 20

        Label {
            id: toastLabel
            anchors.fill: parent
            anchors.margins: 12
            text: toast.message
            color: toast.kind === "error" ? colors.danger : colors.success
            font.pixelSize: 13
            wrapMode: Text.WordWrap
            verticalAlignment: Text.AlignVCenter
        }
    }

    Timer {
        id: toastTimer
        interval: 3600
        onTriggered: toast.visible = false
    }
}
