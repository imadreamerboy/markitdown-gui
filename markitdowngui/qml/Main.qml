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
        window: dark ? Qt.color("#2E3440") : Qt.color("#FDF6E3"),
        nav: dark ? Qt.color("#242A34") : Qt.color("#EEE8D5"),
        surface: dark ? Qt.color("#343B48") : Qt.color("#FFFDF3"),
        surfaceAlt: dark ? Qt.color("#3B4252") : Qt.color("#F6EFD8"),
        input: dark ? Qt.color("#2E3440") : Qt.color("#FBF3DC"),
        border: dark ? Qt.color("#4C566A") : Qt.color("#D6CCB2"),
        text: dark ? Qt.color("#ECEFF4") : Qt.color("#073642"),
        muted: dark ? Qt.color("#D8DEE9") : Qt.color("#586E75"),
        subtle: dark ? Qt.color("#AEB8C8") : Qt.color("#839496"),
        accent: dark ? Qt.color("#88C0D0") : Qt.color("#2AA198"),
        accentAlt: dark ? Qt.color("#8FBCBB") : Qt.color("#268BD2"),
        onAccent: dark ? Qt.color("#2E3440") : Qt.color("#073642"),
        danger: dark ? Qt.color("#BF616A") : Qt.color("#DC322F"),
        success: dark ? Qt.color("#A3BE8C") : Qt.color("#859900"),
        warning: dark ? Qt.color("#EBCB8B") : Qt.color("#B58900")
    })

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
        nameFilters: ["Markdown files (*.md)"]
        onAccepted: app.saveCombinedOutput(selectedFile)
    }

    FolderDialog {
        id: saveSeparateDialog
        title: "Save separate Markdown files"
        onAccepted: app.saveSeparateOutputs(selectedFolder)
    }

    FolderDialog {
        id: outputFolderDialog
        title: "Choose output folder"
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
        onActivated: app.saveCombined ? saveCombinedDialog.open() : saveSeparateDialog.open()
    }

    Shortcut {
        sequence: "Ctrl+L"
        context: Qt.ApplicationShortcut
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
                title: root.pageIndex === 0 ? "Convert to Markdown" : root.pageIndex === 1 ? "Settings" : "Help"
                detail: root.pageIndex === 0
                    ? "Add documents or a webpage, review the Markdown, then save clean output."
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
            value: app.hasQueue ? "Ready" : "Empty"
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

    component WorkspacePage: Item {
        Layout.fillWidth: true
        Layout.fillHeight: true

        DropArea {
            anchors.fill: parent
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

            UrlBar {}

            Loader {
                Layout.fillWidth: true
                Layout.fillHeight: true
                sourceComponent: app.hasResults ? resultsView : app.hasQueue ? queueView : emptyView
            }
        }
    }

    component UrlBar: SectionPanel {
        title: "Add a webpage"
        subtitle: "Paste a URL when the source is already online."
        surfaceColor: colors.surface
        borderColor: colors.border
        textColor: colors.text
        mutedTextColor: colors.muted
        Layout.fillWidth: true
        implicitHeight: 104

        RowLayout {
            Layout.fillWidth: true
            spacing: 10

            AppTextField {
                id: urlInput
                placeholderText: "https://example.com/article"
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
                primary: true
                accentColor: colors.accent
                primaryTextColor: colors.onAccent
                surfaceColor: colors.surfaceAlt
                borderColor: colors.border
                textColor: colors.text
                onClicked: {
                    app.addUrl(urlInput.text)
                    urlInput.text = ""
                }
            }
        }
    }

    Component {
        id: emptyView

        SectionPanel {
            title: "Add documents"
            subtitle: "Drop files into the window, choose files, or add a webpage above."
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
                    width: Math.min(parent.width - 80, 560)
                    spacing: 14

                    Rectangle {
                        width: 54
                        height: 54
                        radius: 8
                        color: Qt.rgba(colors.accent.r, colors.accent.g, colors.accent.b, 0.12)
                        border.color: Qt.rgba(colors.accent.r, colors.accent.g, colors.accent.b, 0.35)
                        Layout.alignment: Qt.AlignHCenter

                        Label {
                            anchors.centerIn: parent
                            text: "MD"
                            color: colors.accent
                            font.pixelSize: 15
                            font.weight: Font.Bold
                        }
                    }

                    Label {
                        text: "Start with documents or a webpage"
                        color: colors.text
                        font.pixelSize: 18
                        font.weight: Font.DemiBold
                        horizontalAlignment: Text.AlignHCenter
                        Layout.fillWidth: true
                    }

                    Label {
                        text: "Office files, PDFs, images, archives, text formats, and webpages can all become Markdown."
                        color: colors.muted
                        font.pixelSize: 13
                        wrapMode: Text.WordWrap
                        horizontalAlignment: Text.AlignHCenter
                        Layout.fillWidth: true
                    }

                    AppButton {
                        text: "Choose files"
                        primary: true
                        accentColor: colors.accent
                        primaryTextColor: colors.onAccent
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
            spacing: 16
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
                        primary: true
                        accentColor: colors.accent
                        primaryTextColor: colors.onAccent
                        onClicked: openFileDialog.open()
                    }

                    AppButton {
                        text: "Clear"
                        subtle: true
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

                            Pill {
                                text: kind
                                tint: kind === "URL" ? colors.accent : colors.muted
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
                                subtle: true
                                textColor: colors.muted
                                onClicked: app.removeQueued(index)
                            }
                        }
                    }
                }
            }

            SectionPanel {
                title: "Conversion settings"
                subtitle: "Start with defaults; switch on OCR or asset extraction only when needed."
                surfaceColor: colors.surface
                borderColor: colors.border
                textColor: colors.text
                mutedTextColor: colors.muted
                Layout.preferredWidth: 360
                Layout.fillHeight: true

                WorkspaceStats {
                    Layout.fillWidth: true
                }

                ToggleRow {
                    title: "OCR"
                    detail: "Use configured OCR providers for scanned or image-heavy inputs."
                    checked: app.ocrEnabled
                    textColor: colors.text
                    mutedTextColor: colors.muted
                    onToggled: checked => app.setOcrEnabled(checked)
                    Layout.fillWidth: true
                }

                ToggleRow {
                    title: "Preserve PDF images"
                    detail: "Extract PDF page images and keep relative asset links on export."
                    checked: app.preservePdfImages
                    textColor: colors.text
                    mutedTextColor: colors.muted
                    onToggled: checked => app.setPreservePdfImages(checked)
                    Layout.fillWidth: true
                }

                ToggleRow {
                    title: "Preserve DOCX images"
                    detail: "Extract embedded document images and keep relative asset links on export."
                    checked: app.preserveDocxImages
                    textColor: colors.text
                    mutedTextColor: colors.muted
                    onToggled: checked => app.setPreserveDocxImages(checked)
                    Layout.fillWidth: true
                }

                Rectangle {
                    height: 1
                    color: colors.border
                    Layout.fillWidth: true
                }

                ProgressBar {
                    from: 0
                    to: 100
                    value: app.progress
                    Layout.fillWidth: true
                }

                Label {
                    text: app.statusText
                    color: colors.muted
                    font.pixelSize: 12
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }

                Item {
                    Layout.fillHeight: true
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    AppButton {
                        text: app.paused ? "Resume" : "Pause"
                        enabled: app.converting
                        surfaceColor: colors.surfaceAlt
                        borderColor: colors.border
                        textColor: colors.text
                        onClicked: app.togglePause()
                    }

                    AppButton {
                        text: "Cancel"
                        enabled: app.converting
                        surfaceColor: colors.surfaceAlt
                        borderColor: colors.border
                        textColor: colors.text
                        onClicked: app.cancel()
                    }
                }

                AppButton {
                    text: app.converting ? "Converting" : "Convert"
                    enabled: !app.converting
                    primary: true
                    accentColor: colors.accent
                    primaryTextColor: colors.onAccent
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
                        textColor: colors.text
                        onClicked: app.clearResults()
                    }

                    AppButton {
                        text: "New"
                        subtle: true
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
                        required property int index
                        required property string name
                        required property string backend
                        required property bool failed
                        required property int wordCount

                        width: resultList.width
                        height: 68
                        radius: 9
                        color: index === resultList.currentIndex ? Qt.rgba(colors.accent.r, colors.accent.g, colors.accent.b, 0.14) : colors.surfaceAlt
                        border.color: index === resultList.currentIndex ? colors.accent : colors.border

                        MouseArea {
                            anchors.fill: parent
                            onClicked: app.selectResult(index)
                        }

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 10
                            spacing: 3

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

            SectionPanel {
                title: "Markdown preview"
                subtitle: "Check the rendered view or raw Markdown before export."
                surfaceColor: colors.surface
                borderColor: colors.border
                textColor: colors.text
                mutedTextColor: colors.muted
                Layout.fillWidth: true
                Layout.fillHeight: true

                RowLayout {
                    Layout.fillWidth: true

                    AppButton {
                        text: "Rendered"
                        primary: app.previewMode === "rendered"
                        subtle: app.previewMode !== "rendered"
                        accentColor: colors.accent
                        primaryTextColor: colors.onAccent
                        textColor: colors.text
                        onClicked: app.setPreviewMode("rendered")
                    }

                    AppButton {
                        text: "Raw"
                        primary: app.previewMode === "raw"
                        subtle: app.previewMode !== "raw"
                        accentColor: colors.accent
                        primaryTextColor: colors.onAccent
                        textColor: colors.text
                        onClicked: app.setPreviewMode("raw")
                    }

                    Item {
                        Layout.fillWidth: true
                    }

                    AppButton {
                        text: "Copy"
                        surfaceColor: colors.surfaceAlt
                        borderColor: colors.border
                        textColor: colors.text
                        onClicked: app.copySelectedMarkdown()
                    }

                    AppButton {
                        text: app.saveCombined ? "Save as one file" : "Save files"
                        primary: true
                        accentColor: colors.accent
                        primaryTextColor: colors.onAccent
                        onClicked: app.saveCombined ? saveCombinedDialog.open() : saveSeparateDialog.open()
                    }
                }

                ScrollView {
                    clip: true
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    TextArea {
                        text: app.previewMode === "rendered" ? app.selectedPreviewHtml : app.selectedMarkdown
                        textFormat: app.previewMode === "rendered" ? TextEdit.RichText : TextEdit.PlainText
                        readOnly: true
                        wrapMode: TextEdit.Wrap
                        selectByMouse: true
                        color: colors.text
                        selectedTextColor: "#FFFFFF"
                        selectionColor: colors.accent
                        font.pixelSize: 13
                        padding: 14
                        background: Rectangle {
                            color: colors.input
                            radius: 9
                            border.color: colors.border
                        }
                    }
                }
            }
        }
    }

    component SettingsPage: ScrollView {
        Layout.fillWidth: true
        Layout.fillHeight: true
        clip: true

        ColumnLayout {
            width: Math.min(parent.width - 48, 900)
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

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10

                    AppTextField {
                        text: app.outputFolder
                        placeholderText: "Optional default output folder"
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

                ToggleRow {
                    title: "Combined save mode"
                    detail: "Save one Markdown document by default instead of one file per input."
                    checked: app.saveCombined
                    textColor: colors.text
                    mutedTextColor: colors.muted
                    onToggled: checked => app.setSaveCombined(checked)
                    Layout.fillWidth: true
                }

                ToggleRow {
                    title: "Prefer source folder"
                    detail: "Use each input file folder when separate exports are saved."
                    checked: app.saveToSourceFolder
                    textColor: colors.text
                    mutedTextColor: colors.muted
                    onToggled: checked => app.setSaveToSourceFolder(checked)
                    Layout.fillWidth: true
                }

                RowLayout {
                    Layout.fillWidth: true

                    Label {
                        text: "Batch size"
                        color: colors.text
                        font.pixelSize: 13
                        Layout.fillWidth: true
                    }

                    SpinBox {
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

                ComboBox {
                    model: ["Solarized Light", "Nord Dark", "System"]
                    currentIndex: app.themeMode === "dark" ? 1 : app.themeMode === "system" ? 2 : 0
                    onActivated: index => app.setThemeMode(index === 1 ? "dark" : index === 2 ? "system" : "light")
                    Layout.fillWidth: true
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

                ToggleRow {
                    title: "OCR enabled"
                    detail: "Use OCR for scanned PDFs and images."
                    checked: app.ocrEnabled
                    textColor: colors.text
                    mutedTextColor: colors.muted
                    onToggled: checked => app.setOcrEnabled(checked)
                    Layout.fillWidth: true
                }

                ComboBox {
                    model: ["Azure/Tesseract", "GLM-OCR"]
                    currentIndex: app.ocrProvider === "glmocr" ? 1 : 0
                    onActivated: index => app.setOcrProvider(index === 1 ? "glmocr" : "legacy")
                    Layout.fillWidth: true
                }

                AppTextField {
                    text: app.docintelEndpoint
                    placeholderText: "Azure Document Intelligence endpoint"
                    surfaceColor: colors.input
                    borderColor: colors.border
                    accentColor: colors.accent
                    textColor: colors.text
                    placeholderColor: colors.subtle
                    Layout.fillWidth: true
                    onEditingFinished: app.setDocintelEndpoint(text)
                }

                AppTextField {
                    text: app.ocrLanguages
                    placeholderText: "Tesseract languages, for example eng or eng+deu"
                    surfaceColor: colors.input
                    borderColor: colors.border
                    accentColor: colors.accent
                    textColor: colors.text
                    placeholderColor: colors.subtle
                    Layout.fillWidth: true
                    onEditingFinished: app.setOcrLanguages(text)
                }

                AppTextField {
                    text: app.tesseractPath
                    placeholderText: "Optional Tesseract executable path"
                    surfaceColor: colors.input
                    borderColor: colors.border
                    accentColor: colors.accent
                    textColor: colors.text
                    placeholderColor: colors.subtle
                    Layout.fillWidth: true
                    onEditingFinished: app.setTesseractPath(text)
                }
            }

            SectionPanel {
                title: "GLM-OCR"
                subtitle: "Connect to the hosted API, Ollama, or an SDK server."
                surfaceColor: colors.surface
                borderColor: colors.border
                textColor: colors.text
                mutedTextColor: colors.muted
                Layout.fillWidth: true

                ToggleRow {
                    title: "Fallback to Azure/Tesseract"
                    detail: "Use the legacy OCR path if GLM-OCR fails."
                    checked: app.ocrFallbackEnabled
                    textColor: colors.text
                    mutedTextColor: colors.muted
                    onToggled: checked => app.setOcrFallbackEnabled(checked)
                    Layout.fillWidth: true
                }

                ComboBox {
                    model: ["Official API", "Ollama", "SDK Server"]
                    currentIndex: app.glmocrMode === "ollama" ? 1 : app.glmocrMode === "sdk_server" ? 2 : 0
                    onActivated: index => app.setGlmocrMode(index === 1 ? "ollama" : index === 2 ? "sdk_server" : "maas")
                    Layout.fillWidth: true
                }

                AppTextField {
                    text: app.glmocrOllamaHost
                    placeholderText: "Ollama host"
                    surfaceColor: colors.input
                    borderColor: colors.border
                    accentColor: colors.accent
                    textColor: colors.text
                    placeholderColor: colors.subtle
                    Layout.fillWidth: true
                    onEditingFinished: app.setGlmocrOllamaHost(text)
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10

                    SpinBox {
                        from: 1
                        to: 65535
                        value: app.glmocrOllamaPort
                        onValueModified: app.setGlmocrOllamaPort(value)
                    }

                    AppTextField {
                        text: app.glmocrOllamaModel
                        placeholderText: "Ollama model"
                        surfaceColor: colors.input
                        borderColor: colors.border
                        accentColor: colors.accent
                        textColor: colors.text
                        placeholderColor: colors.subtle
                        Layout.fillWidth: true
                        onEditingFinished: app.setGlmocrOllamaModel(text)
                    }
                }

                AppTextField {
                    text: app.glmocrSdkServerUrl
                    placeholderText: "SDK server parse endpoint"
                    surfaceColor: colors.input
                    borderColor: colors.border
                    accentColor: colors.accent
                    textColor: colors.text
                    placeholderColor: colors.subtle
                    Layout.fillWidth: true
                    onEditingFinished: app.setGlmocrSdkServerUrl(text)
                }
            }

            Item {
                height: 24
            }
        }
    }

    component HelpPage: Item {
        Layout.fillWidth: true
        Layout.fillHeight: true

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 24
            spacing: 16

            SectionPanel {
                title: "Help and links"
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

                Label {
                    text: "Ctrl+O open files, Ctrl+B convert, Ctrl+P pause or resume, Ctrl+S save, Ctrl+L clear queue, Ctrl+K help, Esc cancel."
                    color: colors.muted
                    font.pixelSize: 13
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }
            }

            Item {
                Layout.fillHeight: true
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
