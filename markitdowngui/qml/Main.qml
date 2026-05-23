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
    property var colors: ({
        window: dark ? Qt.color("#101419") : Qt.color("#F4F7FA"),
        nav: dark ? Qt.color("#151B22") : Qt.color("#EAF0F5"),
        surface: dark ? Qt.color("#171E26") : Qt.color("#FFFFFF"),
        surfaceAlt: dark ? Qt.color("#1D2630") : Qt.color("#F8FAFC"),
        input: dark ? Qt.color("#121820") : Qt.color("#FBFCFD"),
        border: dark ? Qt.color("#2A3542") : Qt.color("#D8E1E8"),
        text: dark ? Qt.color("#E8EDF3") : Qt.color("#18212B"),
        muted: dark ? Qt.color("#AAB6C3") : Qt.color("#647283"),
        subtle: dark ? Qt.color("#7D8C9D") : Qt.color("#8593A3"),
        accent: dark ? Qt.color("#66C8C4") : Qt.color("#138A87"),
        danger: dark ? Qt.color("#FF8A8A") : Qt.color("#B42318"),
        success: dark ? Qt.color("#7BD89F") : Qt.color("#197A43")
    })

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
        implicitHeight: 76
        Layout.fillWidth: true

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 24
            anchors.rightMargin: 24
            spacing: 16

            HeaderTitle {
                title: root.pageIndex === 0 ? "Convert" : root.pageIndex === 1 ? "Settings" : "Help"
                detail: root.pageIndex === 0
                    ? "Drop files, convert URLs, inspect Markdown, and export clean output."
                    : root.pageIndex === 1
                        ? "Tune output defaults and OCR behavior."
                        : "Project links and release actions."
                Layout.fillWidth: true
            }

            Pill {
                text: app.statusText
                tint: app.converting ? colors.accent : colors.muted
            }
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
            anchors.margins: 24
            spacing: 16

            UrlBar {}

            Loader {
                Layout.fillWidth: true
                Layout.fillHeight: true
                sourceComponent: app.hasResults ? resultsView : app.hasQueue ? queueView : emptyView
            }
        }
    }

    component UrlBar: SectionPanel {
        title: "Website URL"
        subtitle: "Convert readable article content through the configured web conversion path."
        surfaceColor: colors.surface
        borderColor: colors.border
        textColor: colors.text
        mutedTextColor: colors.muted
        Layout.fillWidth: true
        implicitHeight: 108

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
                text: "Add URL"
                primary: true
                accentColor: colors.accent
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
            title: "Queue inputs"
            subtitle: "Drop documents here or choose files from your system."
            surfaceColor: colors.surface
            borderColor: colors.border
            textColor: colors.text
            mutedTextColor: colors.muted
            Layout.fillWidth: true
            Layout.fillHeight: true

            Item {
                Layout.fillWidth: true
                Layout.fillHeight: true

                Rectangle {
                    anchors.fill: parent
                    radius: 14
                    color: colors.surfaceAlt
                    border.color: colors.border
                    border.width: 1

                    ColumnLayout {
                        anchors.centerIn: parent
                        width: Math.min(parent.width - 80, 520)
                        spacing: 12

                        Label {
                            text: "Start with files or a URL"
                            color: colors.text
                            font.pixelSize: 18
                            font.weight: Font.DemiBold
                            horizontalAlignment: Text.AlignHCenter
                            Layout.fillWidth: true
                        }

                        Label {
                            text: "Supported inputs include Office documents, PDFs, images, archives, text formats, and website URLs."
                            color: colors.muted
                            font.pixelSize: 13
                            wrapMode: Text.WordWrap
                            horizontalAlignment: Text.AlignHCenter
                            Layout.fillWidth: true
                        }

                        AppButton {
                            text: "Choose Files"
                            primary: true
                            accentColor: colors.accent
                            Layout.alignment: Qt.AlignHCenter
                            onClicked: openFileDialog.open()
                        }
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
                title: "Input queue"
                subtitle: "Items are processed in order."
                surfaceColor: colors.surface
                borderColor: colors.border
                textColor: colors.text
                mutedTextColor: colors.muted
                Layout.fillWidth: true
                Layout.fillHeight: true

                RowLayout {
                    Layout.fillWidth: true

                    AppButton {
                        text: "Add Files"
                        primary: true
                        accentColor: colors.accent
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
                title: "Conversion"
                subtitle: "Keep defaults lean; enable OCR only when needed."
                surfaceColor: colors.surface
                borderColor: colors.border
                textColor: colors.text
                mutedTextColor: colors.muted
                Layout.preferredWidth: 330
                Layout.fillHeight: true

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
                    text: app.converting ? "Converting" : "Convert Queue"
                    enabled: !app.converting
                    primary: true
                    accentColor: colors.accent
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
                title: "Results"
                subtitle: "Select a converted input to inspect output."
                surfaceColor: colors.surface
                borderColor: colors.border
                textColor: colors.text
                mutedTextColor: colors.muted
                Layout.preferredWidth: 330
                Layout.fillHeight: true

                RowLayout {
                    Layout.fillWidth: true

                    AppButton {
                        text: "Back to Queue"
                        subtle: true
                        textColor: colors.text
                        onClicked: app.clearResults()
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
                subtitle: "Rendered output and raw Markdown stay side by side in one workflow."
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
                        textColor: colors.text
                        onClicked: app.setPreviewMode("rendered")
                    }

                    AppButton {
                        text: "Raw"
                        primary: app.previewMode === "raw"
                        subtle: app.previewMode !== "raw"
                        accentColor: colors.accent
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
                        text: app.saveCombined ? "Save Combined" : "Save Separate"
                        primary: true
                        accentColor: colors.accent
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
                subtitle: "Set defaults that keep exports predictable."
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
                subtitle: "Use the platform window chrome and a restrained app palette."
                surfaceColor: colors.surface
                borderColor: colors.border
                textColor: colors.text
                mutedTextColor: colors.muted
                Layout.fillWidth: true

                ComboBox {
                    model: ["Light", "Dark", "System"]
                    currentIndex: app.themeMode === "dark" ? 1 : app.themeMode === "system" ? 2 : 0
                    onActivated: index => app.setThemeMode(index === 1 ? "dark" : index === 2 ? "system" : "light")
                    Layout.fillWidth: true
                }
            }

            SectionPanel {
                title: "OCR"
                subtitle: "Keep OCR disabled unless the input requires it."
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
                subtitle: "Configure local or hosted GLM-OCR connectivity."
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
                title: "Resources"
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
                subtitle: "Common conversion actions stay available from the keyboard."
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
