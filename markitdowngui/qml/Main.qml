import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import "components"

ApplicationWindow {
    id: root

    width: 1180
    height: 760
    minimumWidth: 820
    minimumHeight: 560
    visible: true
    title: root.tr("qml_app_title")
    color: colors.window
    font.family: Qt.platform.os === "windows" ? "Segoe UI" : Qt.platform.os === "osx" ? ".AppleSystemUIFont" : "Noto Sans"
    onClosing: close => close.accepted = app.requestShutdown()

    property int pageIndex: 0
    property bool compactLayout: width < 1040
    property bool reduceMotion: app.reduceMotion
    property bool dark: app.darkMode
    property int pageMargin: compactLayout ? 14 : 22
    property int panelRadius: 8
    property int controlRadius: 8
    property int motionFastDuration: reduceMotion ? 0 : 120
    property int motionStandardDuration: reduceMotion ? 0 : 180
    property bool instantPageTransition: false
    property var colors: ({
        window: dark ? Qt.color("#2E3440") : Qt.color("#FBF4E1"),
        nav: dark ? Qt.color("#242A34") : Qt.color("#EEE8D5"),
        surface: dark ? Qt.color("#343B48") : Qt.color("#FFFCF0"),
        surfaceAlt: dark ? Qt.color("#3B4252") : Qt.color("#F7F0D8"),
        document: dark ? Qt.color("#2B313C") : Qt.color("#FFFEF7"),
        input: dark ? Qt.color("#2E3440") : Qt.color("#FFF9EA"),
        border: dark ? Qt.color("#4C566A") : Qt.color("#D8CEB5"),
        text: dark ? Qt.color("#ECEFF4") : Qt.color("#073642"),
        muted: dark ? Qt.color("#D8DEE9") : Qt.color("#586E75"),
        subtle: dark ? Qt.color("#AEB8C8") : Qt.color("#5D6E72"),
        accent: dark ? Qt.color("#88C0D0") : Qt.color("#687700"),
        accentAlt: dark ? Qt.color("#8FBCBB") : Qt.color("#7C6F00"),
        action: dark ? Qt.color("#88C0D0") : Qt.color("#687700"),
        actionSoft: dark ? Qt.color("#415867") : Qt.color("#E8EBC8"),
        onAccent: dark ? Qt.color("#2E3440") : Qt.color("#FDF6E3"),
        onAction: dark ? Qt.color("#2E3440") : Qt.color("#FDF6E3"),
        danger: dark ? Qt.color("#E8949C") : Qt.color("#C82624"),
        success: dark ? Qt.color("#A3BE8C") : Qt.color("#397D54"),
        warning: dark ? Qt.color("#EBCB8B") : Qt.color("#7A5900")
    })

    Timer {
        id: pageTransitionResetTimer
        interval: 0
        onTriggered: root.instantPageTransition = false
    }

    function navigateToPage(index, animate) {
        pageTransitionResetTimer.stop()
        root.instantPageTransition = !animate
        root.pageIndex = index
        if (!animate)
            pageTransitionResetTimer.restart()
    }

    function requestSave() {
        if (!app.hasResults) {
            app.notifyNoOutputToSave()
            return
        }
        if (!app.hasSuccessfulResults) {
            app.notifyNoSuccessfulOutputToSave()
            return
        }

        if (app.saveCombined)
            saveCombinedDialog.open()
        else if (app.canSaveSeparateWithoutDialog)
            app.saveSeparateOutputs("")
        else
            saveSeparateDialog.open()
    }

    function showAzureTesseractSettings() {
        return app.ocrEnabled
            && (app.ocrProvider === "azure_tesseract" || app.ocrFallbackProvider === "azure_tesseract")
    }

    function showHttpOcrSettings() {
        return app.ocrEnabled
            && (app.ocrProvider === "http" || app.ocrFallbackProvider === "http")
    }

    function ocrProviderIndex(provider) {
        if (provider === "glmocr")
            return 1
        if (provider === "http")
            return 2
        return 0
    }

    function ocrProviderFromIndex(index) {
        if (index === 1)
            return "glmocr"
        if (index === 2)
            return "http"
        return "azure_tesseract"
    }

    function ocrProviderLabel(provider) {
        if (provider === "glmocr")
            return root.tr("settings_ocr_provider_glmocr")
        if (provider === "http")
            return root.tr("conversion_backend_http_ocr")
        return root.tr("settings_ocr_provider_azure_tesseract")
    }

    function tr(key) {
        var language = app.currentLanguage
        return app.translate(key)
    }

    function ocrFallbackIndex(provider) {
        if (app.ocrProvider === "http" && provider === "http")
            return 0
        if (provider === "azure_tesseract")
            return 1
        if (app.ocrProvider !== "http" && provider === "http")
            return 2
        return 0
    }

    function ocrFallbackFromIndex(index) {
        if (index === 1)
            return "azure_tesseract"
        if (app.ocrProvider !== "http" && index === 2)
            return "http"
        return "none"
    }

    function ocrFallbackLabels() {
        if (app.ocrProvider === "http")
            return [root.tr("qml_none"), root.tr("settings_ocr_provider_azure_tesseract")]
        return [root.tr("qml_none"), root.tr("settings_ocr_provider_azure_tesseract"), root.tr("conversion_backend_http_ocr")]
    }

    function ocrFallbackDetail() {
        if (app.ocrProvider === "http")
            return root.tr("qml_ocr_fallback_http_detail")
        return root.tr("qml_ocr_fallback_glm_detail")
    }

    function focusedTextControl() {
        var item = root.activeFocusItem
        if (!item)
            return false
        try {
            return item.selectedText !== undefined
        } catch (error) {
            return false
        }
    }

    function conversionProgressText() {
        if (app.totalCount <= 0)
            return ""
        return root.tr("qml_conversion_progress")
            .replace("{completed}", app.completedCount)
            .replace("{total}", app.totalCount)
    }

    function conversionStatusText() {
        var progressText = root.conversionProgressText()
        return progressText.length > 0 ? app.statusText + " · " + progressText : app.statusText
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
        title: root.tr("home_add_files_button")
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
        title: root.tr("save_combined_title")
        fileMode: FileDialog.SaveFile
        defaultSuffix: "md"
        currentFolder: app.outputFolderUrl
        selectedFile: app.suggestedCombinedOutputUrl
        nameFilters: ["Markdown files (*.md)"]
        onAccepted: app.saveCombinedOutput(selectedFile)
    }

    FolderDialog {
        id: saveSeparateDialog
        title: root.tr("select_directory_title")
        currentFolder: app.suggestedSeparateOutputFolderUrl
        onAccepted: app.saveSeparateOutputs(selectedFolder)
    }

    Dialog {
        id: discardResultsDialog
        property string actionDescription: ""

        title: root.tr("qml_discard_unsaved_title")
        modal: true
        focus: true
        width: 440
        standardButtons: Dialog.NoButton
        closePolicy: Popup.CloseOnEscape
        anchors.centerIn: parent
        onRejected: app.cancelPendingResultDiscard()

        background: Rectangle {
            radius: root.panelRadius
            color: colors.surface
            border.color: colors.border
        }

        contentItem: Label {
            text: root.tr("qml_discard_unsaved_message").replace(
                "{action}",
                discardResultsDialog.actionDescription
            )
            color: colors.text
            wrapMode: Text.WordWrap
            padding: 4
        }

        footer: Item {
            implicitHeight: discardResultsButtons.implicitHeight + 20

            RowLayout {
                id: discardResultsButtons
                anchors.fill: parent
                anchors.margins: 10
                spacing: 8

                Item {
                    Layout.fillWidth: true
                }

                AppButton {
                    text: root.tr("qml_keep_results")
                    subtle: true
                    accentColor: colors.action
                    textColor: colors.text
                    onClicked: discardResultsDialog.reject()
                }

                AppButton {
                    text: root.tr("qml_discard_results")
                    primary: true
                    accentColor: colors.danger
                    primaryTextColor: colors.onAccent
                    onClicked: {
                        app.discardPendingResults()
                        discardResultsDialog.accept()
                    }
                }
            }
        }
    }

    FolderDialog {
        id: outputFolderDialog
        title: root.tr("settings_output_folder_dialog")
        currentFolder: app.outputFolderUrl
        onAccepted: app.setOutputFolderFromUrl(selectedFolder)
    }

    FileDialog {
        id: exportSettingsProfileDialog
        title: root.tr("qml_export_settings_profile")
        fileMode: FileDialog.SaveFile
        defaultSuffix: "json"
        currentFolder: app.outputFolderUrl
        selectedFile: app.outputFolderUrl ? app.outputFolderUrl + "/markitdown-settings-profile.json" : ""
        nameFilters: ["JSON files (*.json)"]
        onAccepted: app.exportSettingsProfile(selectedFile)
    }

    FileDialog {
        id: importSettingsProfileDialog
        title: root.tr("qml_import_settings_profile")
        fileMode: FileDialog.OpenFile
        currentFolder: app.outputFolderUrl
        nameFilters: ["JSON files (*.json)", "All files (*)"]
        onAccepted: app.importSettingsProfile(selectedFile)
    }

    Connections {
        target: app
        function onToastRequested(kind, message) {
            toast.kind = kind
            toast.message = message
            toast.showing = true
            toastTimer.restart()
        }

        function onDiscardResultsRequested(actionDescription) {
            discardResultsDialog.actionDescription = actionDescription
            discardResultsDialog.open()
        }

        function onCloseApproved() {
            root.close()
        }
    }

    Rectangle {
        id: updateBanner
        visible: app.hasUpdateNotification || opacity > 0
        opacity: app.hasUpdateNotification ? 1 : 0
        z: 20
        width: Math.min(480, root.width - 48)
        height: updateBannerRow.implicitHeight + 24
        radius: 8
        color: colors.surface
        border.color: colors.border
        anchors.top: parent.top
        anchors.right: parent.right
        anchors.topMargin: 22
        anchors.rightMargin: 22

        Behavior on opacity {
            NumberAnimation {
                duration: root.motionStandardDuration
                easing.type: Easing.OutCubic
            }
        }

        RowLayout {
            id: updateBannerRow
            anchors.fill: parent
            anchors.margins: 12
            spacing: 10

            Rectangle {
                width: 30
                height: 30
                radius: 7
                color: Qt.rgba(colors.action.r, colors.action.g, colors.action.b, dark ? 0.18 : 0.14)

                Icon {
                    anchors.centerIn: parent
                    name: "external-link"
                    size: 15
                    color: colors.action
                }
            }

            ColumnLayout {
                spacing: 1
                Layout.fillWidth: true

                Label {
                    text: root.tr("qml_update_available").replace("{version}", app.availableUpdateVersion)
                    color: colors.text
                    font.pixelSize: 13
                    font.weight: Font.DemiBold
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }

                Label {
                    text: app.updateInstallRunning
                        ? app.updateInstallStatus
                        : app.canInstallPreferredUpdate
                        ? root.tr("qml_update_install_detail")
                        : root.tr("qml_update_source_detail")
                    color: colors.muted
                    font.pixelSize: 12
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }

                ProgressBar {
                    visible: app.updateInstallRunning
                    from: 0
                    to: 100
                    value: app.updateInstallProgress
                    Layout.fillWidth: true
                    Layout.preferredHeight: 4
                }
            }

            AppButton {
                text: app.updateInstallRunning
                    ? root.tr("qml_installing")
                    : app.canInstallPreferredUpdate
                    ? root.tr("qml_install")
                    : app.preferredReleaseAsset.url ? app.preferredReleaseAsset.installLabel || root.tr("qml_download") : root.tr("qml_releases")
                primary: true
                iconName: app.updateInstallRunning || app.canInstallPreferredUpdate ? "rotate-ccw" : "external-link"
                accentColor: colors.action
                primaryTextColor: colors.onAction
                enabled: !app.updateInstallRunning
                onClicked: app.canInstallPreferredUpdate
                    ? app.installPreferredUpdate()
                    : app.preferredReleaseAsset.url
                    ? app.openReleaseAsset(app.preferredReleaseAsset.url)
                    : app.openReleases()
            }

            AppButton {
                text: ""
                subtle: true
                iconName: "x"
                accentColor: colors.action
                textColor: colors.muted
                Accessible.name: root.tr("qml_dismiss_update")
                ToolTip.visible: hovered
                ToolTip.delay: 550
                ToolTip.text: root.tr("qml_dismiss")
                onClicked: app.dismissUpdateNotification()
            }

            AppButton {
                text: root.tr("qml_dont_notify")
                subtle: true
                accentColor: colors.action
                textColor: colors.muted
                onClicked: app.disableUpdateNotifications()
            }
        }
    }

    Shortcut {
        sequences: [StandardKey.Open]
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
        sequences: [StandardKey.Save]
        context: Qt.ApplicationShortcut
        enabled: app.hasSuccessfulResults
        onActivated: root.requestSave()
    }

    Shortcut {
        sequences: [StandardKey.Copy]
        context: Qt.ApplicationShortcut
        enabled: root.pageIndex === 0 && app.hasResults && !root.focusedTextControl()
        onActivated: app.copySelectedMarkdown()
    }

    Shortcut {
        sequence: "Ctrl+R"
        context: Qt.ApplicationShortcut
        enabled: root.pageIndex === 0 && app.hasFailedResults && !app.converting
        onActivated: app.retryFailedResults()
    }

    Shortcut {
        sequence: "Ctrl+L"
        context: Qt.ApplicationShortcut
        enabled: root.pageIndex === 0 && !app.converting && !root.focusedTextControl()
        onActivated: app.clearQueue()
    }

    Shortcut {
        sequence: "Ctrl+K"
        context: Qt.ApplicationShortcut
        onActivated: root.navigateToPage(2, false)
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        SideNav {
            currentIndex: root.pageIndex
            compact: root.compactLayout
            reduceMotion: root.reduceMotion
            brandTitle: root.tr("qml_brand_title")
            brandSubtitle: root.tr("qml_brand_subtitle")
            workspaceLabel: root.tr("qml_workspace_label")
            workspaceDescription: root.tr("qml_workspace_description")
            workspaceDetail: root.tr("qml_workspace_detail")
            workspaceHelp: root.tr("qml_workspace_help")
            helpLabel: root.tr("nav_help")
            helpDescription: root.tr("qml_help_nav_description")
            settingsLabel: root.tr("nav_settings")
            settingsDescription: root.tr("qml_settings_nav_description")
            backgroundColor: colors.nav
            activeColor: colors.surface
            textColor: colors.text
            mutedTextColor: colors.muted
            accentColor: colors.accent
            borderColor: colors.border
            utilityHoverColor: Qt.rgba(colors.accent.r, colors.accent.g, colors.accent.b, dark ? 0.16 : 0.10)
            accentTextColor: colors.onAccent
            Layout.fillHeight: true
            Layout.preferredWidth: root.compactLayout ? 68 : 224
            Layout.minimumWidth: root.compactLayout ? 68 : 224
            onPageRequested: index => root.navigateToPage(index, true)
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

            Item {
                id: pageStack
                Layout.fillWidth: true
                Layout.fillHeight: true

                Loader {
                    id: workspacePageLoader
                    objectName: "workspacePageLoader"
                    anchors.fill: parent
                    active: root.pageIndex === 0 || status === Loader.Ready
                    sourceComponent: workspacePageComponent
                    visible: root.pageIndex === 0 || opacity > 0
                    opacity: root.pageIndex === 0 ? 1 : 0
                    z: root.pageIndex === 0 ? 1 : 0

                    Behavior on opacity {
                        NumberAnimation {
                            duration: root.instantPageTransition ? 0 : root.motionStandardDuration
                            easing.type: Easing.OutCubic
                        }
                    }
                }

                Loader {
                    id: settingsPageLoader
                    objectName: "settingsPageLoader"
                    anchors.fill: parent
                    active: root.pageIndex === 1 || status === Loader.Ready
                    sourceComponent: settingsPageComponent
                    visible: root.pageIndex === 1 || opacity > 0
                    opacity: root.pageIndex === 1 ? 1 : 0
                    z: root.pageIndex === 1 ? 1 : 0

                    Behavior on opacity {
                        NumberAnimation {
                            duration: root.instantPageTransition ? 0 : root.motionStandardDuration
                            easing.type: Easing.OutCubic
                        }
                    }
                }

                Loader {
                    id: helpPageLoader
                    objectName: "helpPageLoader"
                    anchors.fill: parent
                    active: root.pageIndex === 2 || status === Loader.Ready
                    sourceComponent: helpPageComponent
                    visible: root.pageIndex === 2 || opacity > 0
                    opacity: root.pageIndex === 2 ? 1 : 0
                    z: root.pageIndex === 2 ? 1 : 0

                    Behavior on opacity {
                        NumberAnimation {
                            duration: root.instantPageTransition ? 0 : root.motionStandardDuration
                            easing.type: Easing.OutCubic
                        }
                    }
                }
            }
        }
    }

    Component {
        id: workspacePageComponent
        WorkspacePage {}
    }

    Component {
        id: settingsPageComponent
        SettingsPage {}
    }

    Component {
        id: helpPageComponent
        HelpPage {}
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
        property int maxWidth: 260

        implicitWidth: Math.min(maxWidth, label.implicitWidth + 18)
        implicitHeight: 26
        radius: 13
        color: Qt.rgba(tint.r, tint.g, tint.b, 0.12)

        Label {
            id: label
            anchors.fill: parent
            anchors.leftMargin: 9
            anchors.rightMargin: 9
            text: parent.text
            color: parent.tint
            font.pixelSize: 12
            font.weight: Font.Medium
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideMiddle
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

    component PreviewModeButton: AppButton {
        property bool selected: false

        primary: selected
        subtle: !selected
        accentColor: colors.actionSoft
        primaryTextColor: colors.text
        surfaceColor: colors.surfaceAlt
        borderColor: colors.border
        focusColor: colors.action
        textColor: selected ? colors.text : colors.muted
        Accessible.name: root.tr("qml_preview_accessible")
            .replace("{name}", text)
            .replace("{selected}", selected ? root.tr("qml_selected") : "")
    }

    component UtilitySectionPanel: SectionPanel {
        surfaceColor: colors.surface
        borderColor: colors.border
        textColor: colors.text
        mutedTextColor: colors.muted
        panelPadding: 14
        contentSpacing: 10
        bodySpacing: 9
        borderOpacity: dark ? 0.90 : 0.72
        Layout.fillWidth: true
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
                    ? (app.hasResults ? root.tr("qml_review_markdown") : root.tr("nav_convert"))
                    : root.pageIndex === 1 ? root.tr("settings_title") : root.tr("help_title")
                detail: root.pageIndex === 0
                    ? (app.hasResults
                        ? root.tr("qml_review_markdown_detail")
                        : root.tr("qml_convert_detail"))
                    : root.pageIndex === 1
                        ? root.tr("qml_settings_detail")
                        : root.tr("qml_help_detail")
                Layout.fillWidth: true
            }

            Pill {
                visible: root.pageIndex === 0 || app.converting
                text: app.statusText
                tint: app.converting ? colors.accent : colors.muted
                maxWidth: Math.min(300, Math.max(180, root.width * 0.30))
            }
        }
    }

    component WorkspaceStats: GridLayout {
        columns: 3
        columnSpacing: 8
        rowSpacing: 8
        Layout.fillWidth: true
        Layout.minimumWidth: 0

        MetricPill {
            compact: root.compactLayout
            label: root.tr("qml_stats_inputs")
            value: app.queueCount.toString()
            backgroundColor: "transparent"
            borderColor: colors.border
            borderOpacity: 0
            textColor: colors.text
            mutedTextColor: colors.muted
            Layout.fillWidth: true
            Layout.minimumWidth: 0
        }

        MetricPill {
            compact: root.compactLayout
            label: root.tr("qml_stats_done")
            value: app.totalCount > 0
                ? app.completedCount + "/" + app.totalCount
                : app.progress + "%"
            backgroundColor: "transparent"
            borderColor: colors.border
            borderOpacity: 0
            textColor: colors.text
            mutedTextColor: colors.muted
            Layout.fillWidth: true
            Layout.minimumWidth: 0
        }

        MetricPill {
            compact: root.compactLayout
            label: root.tr("qml_stats_save")
            value: app.saveCombined ? root.tr("home_save_mode_combined") : root.tr("home_save_mode_separate")
            backgroundColor: "transparent"
            borderColor: colors.border
            borderOpacity: 0
            textColor: colors.text
            mutedTextColor: colors.muted
            Layout.fillWidth: true
            Layout.minimumWidth: 0
        }
    }

    component ThemeToggleRow: ToggleRow {
        Layout.minimumWidth: 0
        Layout.preferredWidth: 0
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

        property bool busy: false
        property bool reducedMotion: root.reduceMotion

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
                id: determinateProgressFill
                visible: !progressControl.busy
                width: progressControl.visualPosition * parent.width
                height: parent.height
                radius: 3
                color: colors.accent
            }

            Rectangle {
                id: indeterminateProgressFill
                property real busyOffset: -width
                visible: progressControl.busy
                width: progressControl.reducedMotion ? parent.width * 0.42 : parent.width * 0.28
                height: parent.height
                x: progressControl.reducedMotion
                    ? (parent.width - width) / 2
                    : busyOffset
                radius: 3
                color: colors.accent

                NumberAnimation on busyOffset {
                    from: -indeterminateProgressFill.width
                    to: indeterminateProgressFill.parent.width
                    duration: 1050
                    loops: Animation.Infinite
                    running: progressControl.busy
                        && !progressControl.reducedMotion
                        && indeterminateProgressFill.parent.width > 0
                }
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

    component SettingsField: RowLayout {
        id: settingsField

        property string label: ""
        property string detail: ""
        property int labelColumnWidth: 220
        default property alias content: settingsFieldBody.data

        spacing: 18
        Layout.fillWidth: true

        ColumnLayout {
            spacing: 2
            Layout.preferredWidth: settingsField.labelColumnWidth
            Layout.alignment: Qt.AlignTop

            Label {
                text: settingsField.label
                visible: settingsField.label.length > 0
                color: colors.text
                font.pixelSize: 12
                font.weight: Font.Medium
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            Label {
                text: settingsField.detail
                visible: settingsField.detail.length > 0
                color: colors.muted
                font.pixelSize: 11
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }
        }

        ColumnLayout {
            id: settingsFieldBody

            spacing: 8
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignTop
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
                    placeholderText: urlBar.compact ? root.tr("home_add_url_placeholder") : root.tr("home_url_placeholder")
                    surfaceColor: colors.input
                    borderColor: colors.border
                    accentColor: colors.accent
                    textColor: colors.text
                    placeholderColor: colors.subtle
                    Accessible.name: root.tr("qml_webpage_url")
                    Accessible.description: root.tr("qml_webpage_url_description")
                    Layout.fillWidth: true
                    onAccepted: {
                        if (app.addUrl(text))
                            text = ""
                    }
                }

                Connections {
                    target: app

                    function onUrlQueued(url) {
                        if (compactUrlInput.text.trim() === url)
                            compactUrlInput.text = ""
                    }
                }

                AppButton {
                    text: root.tr("qml_add_webpage")
                    enabled: !app.converting
                    iconName: "link"
                    accentColor: colors.action
                    primaryTextColor: colors.onAction
                    surfaceColor: colors.surfaceAlt
                    borderColor: colors.border
                    textColor: colors.text
                    Accessible.name: root.tr("qml_add_webpage")
                    onClicked: {
                        if (app.addUrl(compactUrlInput.text))
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
            surfaceColor: colors.document
            borderColor: colors.border
            textColor: colors.text
            mutedTextColor: colors.muted
            borderOpacity: dark ? 0.88 : 0.68
            Layout.fillWidth: true
            Layout.fillHeight: true

            Item {
                Layout.fillWidth: true
                Layout.fillHeight: true

                ColumnLayout {
                    anchors.centerIn: parent
                    width: Math.min(parent.width - 80, 460)
                    spacing: 13

                    Rectangle {
                        width: 50
                        height: 50
                        radius: 10
                        color: Qt.rgba(colors.action.r, colors.action.g, colors.action.b, dark ? 0.14 : 0.12)
                        border.color: Qt.rgba(colors.action.r, colors.action.g, colors.action.b, dark ? 0.32 : 0.28)
                        Layout.alignment: Qt.AlignHCenter

                        Icon {
                            anchors.centerIn: parent
                            name: "folder-plus"
                            size: 22
                            color: colors.action
                        }
                    }

                    Label {
                        text: root.tr("home_empty_state_title")
                        color: colors.text
                        font.pixelSize: 18
                        font.weight: Font.DemiBold
                        horizontalAlignment: Text.AlignHCenter
                        Layout.fillWidth: true
                    }

                    Label {
                        text: root.tr("home_empty_subtitle")
                        color: colors.muted
                        font.pixelSize: 13
                        lineHeight: 1.16
                        wrapMode: Text.WordWrap
                        horizontalAlignment: Text.AlignHCenter
                        Layout.fillWidth: true
                    }

                    AppButton {
                        text: root.tr("home_add_files_button")
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
                    title: root.tr("home_queue_title")
                    subtitle: root.tr("qml_queue_detail")
                    surfaceColor: colors.surface
                    borderColor: colors.border
                    textColor: colors.text
                    mutedTextColor: colors.muted
                    borderOpacity: dark ? 0.88 : 0.68
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    RowLayout {
                        Layout.fillWidth: true

                        AppButton {
                            text: root.tr("home_add_files_button")
                            enabled: !app.converting
                            iconName: "folder-plus"
                            accentColor: colors.action
                            primaryTextColor: colors.onAction
                            surfaceColor: colors.surfaceAlt
                            borderColor: colors.border
                            textColor: colors.text
                            onClicked: openFileDialog.open()
                        }

                        AppButton {
                            text: root.tr("home_clear_queue_button")
                            enabled: !app.converting
                            subtle: true
                            iconName: "x"
                            accentColor: colors.action
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
                                    text: root.tr("home_remove_selected_button")
                                    enabled: !app.converting
                                    subtle: true
                                    iconName: "trash-2"
                                    accentColor: colors.action
                                    textColor: colors.muted
                                    Accessible.name: root.tr("qml_remove_from_queue").replace("{name}", name)
                                    onClicked: app.removeQueued(index)
                                }
                            }
                        }
                    }
                }

                SectionPanel {
                    title: root.tr("home_markdown_preview_label")
                    subtitle: root.height < 700 ? "" : root.tr("qml_preview_before_export")
                    surfaceColor: colors.surface
                    borderColor: colors.border
                    textColor: colors.text
                    mutedTextColor: colors.muted
                    borderOpacity: dark ? 0.88 : 0.68
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
                                    text: root.tr("qml_preview_after_conversion")
                                    color: colors.text
                                    font.pixelSize: 12
                                    font.weight: Font.Medium
                                    Layout.fillWidth: true
                                }

                                Label {
                                    text: root.height < 700
                                        ? root.tr("qml_preview_empty_detail")
                                        : root.tr("qml_preview_queue_detail")
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
                title: app.converting ? root.tr("qml_converting") : root.tr("nav_convert")
                subtitle: root.tr("qml_items_queued").replace("{count}", app.queueCount)
                surfaceColor: colors.window
                borderColor: colors.border
                textColor: colors.text
                mutedTextColor: colors.muted
                Layout.preferredWidth: root.compactLayout ? 280 : 360
                Layout.minimumWidth: root.compactLayout ? 250 : 330
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
                            title: root.tr("settings_ocr_group")
                            detail: root.tr("qml_ocr_toggle_detail").replace(
                                "{provider}",
                                root.ocrProviderLabel(app.ocrProvider)
                            )
                            enabled: !app.converting
                            checked: app.ocrEnabled
                            textColor: colors.text
                            mutedTextColor: colors.muted
                            onToggled: checked => app.setOcrEnabled(checked)
                            Layout.fillWidth: true
                            Layout.minimumWidth: 0
                        }

                        ThemeToggleRow {
                            id: fastPdfConversionToggle
                            title: root.tr("home_fast_pdf_conversion_label")
                            detail: root.tr("home_fast_pdf_conversion_detail")
                            enabled: !app.converting && !app.preservePdfImages
                            checked: app.fastPdfConversion
                            textColor: colors.text
                            mutedTextColor: colors.muted
                            Layout.fillWidth: true
                            Layout.minimumWidth: 0
                        }

                        Connections {
                            target: fastPdfConversionToggle

                            function onToggled(enabled) {
                                app.setFastPdfConversion(enabled)
                            }
                        }

                        ThemeToggleRow {
                            title: root.tr("home_anydoc_conversion_label")
                            detail: root.tr("home_anydoc_conversion_detail")
                            enabled: !app.converting
                            checked: app.anydocForConversion
                            textColor: colors.text
                            mutedTextColor: colors.muted
                            onToggled: checked => app.setAnydocForConversion(checked)
                            Layout.fillWidth: true
                            Layout.minimumWidth: 0
                        }

                        ThemeToggleRow {
                            title: root.tr("home_preserve_pdf_images_label")
                            detail: root.tr("home_preserve_pdf_images_tooltip")
                            enabled: !app.converting
                            checked: app.preservePdfImages
                            textColor: colors.text
                            mutedTextColor: colors.muted
                            onToggled: checked => app.setPreservePdfImages(checked)
                            Layout.fillWidth: true
                            Layout.minimumWidth: 0
                        }

                        ThemeToggleRow {
                            title: root.tr("home_preserve_docx_images_label")
                            detail: root.tr("home_preserve_docx_images_tooltip")
                            enabled: !app.converting
                            checked: app.preserveDocxImages
                            textColor: colors.text
                            mutedTextColor: colors.muted
                            onToggled: checked => app.setPreserveDocxImages(checked)
                            Layout.fillWidth: true
                            Layout.minimumWidth: 0
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
                                text: root.tr("qml_output_label")
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
                                    text: app.saveCombined
                                        ? root.tr("qml_combined_markdown_file")
                                        : root.tr("qml_separate_markdown_files")
                                    color: colors.muted
                                    font.pixelSize: 12
                                    elide: Text.ElideRight
                                    Layout.fillWidth: true
                                }
                            }

                            Label {
                                text: app.saveToSourceFolder
                                    ? root.tr("qml_default_source_folders")
                                    : (app.outputFolder.length > 0
                                        ? app.outputFolder
                                        : root.tr("qml_choose_location_when_saving"))
                                color: colors.subtle
                                font.pixelSize: 11
                                elide: Text.ElideMiddle
                                Layout.fillWidth: true
                            }

                            AppButton {
                                text: root.tr("qml_set_folder")
                                subtle: true
                                iconName: "folder-plus"
                                accentColor: colors.action
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
                        busy: app.progressIndeterminate
                        reducedMotion: root.reduceMotion
                        Layout.fillWidth: true
                    }

                    Label {
                        text: root.conversionStatusText()
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
                        text: app.paused ? root.tr("resume_button") : root.tr("pause_button")
                        enabled: app.converting
                        iconName: app.paused ? "play" : "pause"
                        accentColor: colors.action
                        surfaceColor: colors.surfaceAlt
                        borderColor: colors.border
                        textColor: colors.text
                        onClicked: app.togglePause()
                    }

                    AppButton {
                        text: root.tr("qml_stop_after_current")
                        enabled: app.converting
                        iconName: "x"
                        accentColor: colors.action
                        surfaceColor: colors.surfaceAlt
                        borderColor: colors.border
                        textColor: colors.text
                        Accessible.name: root.tr("qml_stop_after_current_accessible")
                        Accessible.description: root.tr("qml_stop_after_current_description")
                        onClicked: app.cancel()
                    }
                }

                AppButton {
                    visible: !app.converting
                    text: app.converting
                        ? root.tr("qml_converting")
                        : (app.queueCount === 1
                            ? root.tr("qml_convert_one").replace("{count}", app.queueCount)
                            : root.tr("qml_convert_many").replace("{count}", app.queueCount))
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
                title: root.tr("qml_converted_files")
                subtitle: root.tr("qml_converted_files_detail")
                surfaceColor: colors.surface
                borderColor: colors.border
                textColor: colors.text
                mutedTextColor: colors.muted
                borderOpacity: dark ? 0.88 : 0.68
                Layout.preferredWidth: 300
                Layout.fillHeight: true

                Rectangle {
                    visible: app.converting
                    implicitHeight: activeResultControls.implicitHeight + 20
                    radius: 8
                    color: colors.surfaceAlt
                    border.color: colors.border
                    Layout.fillWidth: true

                    ColumnLayout {
                        id: activeResultControls
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 7

                        Label {
                            text: root.conversionStatusText()
                            color: colors.muted
                            font.pixelSize: 12
                            elide: Text.ElideMiddle
                            Layout.fillWidth: true
                        }

                        ThemeProgressBar {
                            value: app.progress
                            busy: app.progressIndeterminate
                            reducedMotion: root.reduceMotion
                            Layout.fillWidth: true
                        }

                        RowLayout {
                            spacing: 8
                            Layout.fillWidth: true

                            AppButton {
                                text: app.paused ? root.tr("resume_button") : root.tr("pause_button")
                                iconName: app.paused ? "play" : "pause"
                                accentColor: colors.action
                                surfaceColor: colors.surface
                                borderColor: colors.border
                                textColor: colors.text
                                Layout.fillWidth: true
                                onClicked: app.togglePause()
                            }

                            AppButton {
                                text: root.tr("qml_stop_after_current")
                                iconName: "x"
                                accentColor: colors.action
                                surfaceColor: colors.surface
                                borderColor: colors.border
                                textColor: colors.text
                                Accessible.name: root.tr("qml_stop_after_current_accessible")
                                Accessible.description: root.tr("qml_stop_after_current_description")
                                Layout.fillWidth: true
                                onClicked: app.cancel()
                            }
                        }
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 6

                    RowLayout {
                        Layout.fillWidth: true

                        AppButton {
                            text: root.tr("home_back_to_queue_button")
                            enabled: !app.converting
                            subtle: true
                            iconName: "rotate-ccw"
                            accentColor: colors.action
                            textColor: colors.text
                            onClicked: app.backToQueue()
                        }

                        AppButton {
                            text: root.tr("home_start_over_button")
                            enabled: !app.converting
                            subtle: true
                            iconName: "file-text"
                            accentColor: colors.action
                            textColor: colors.muted
                            onClicked: app.startNew()
                        }

                        Item {
                            Layout.fillWidth: true
                        }
                    }

                    AppButton {
                        visible: app.hasFailedResults
                        enabled: !app.converting
                        text: root.tr("qml_retry_failed_conversions")
                        subtle: true
                        iconName: "rotate-ccw"
                        accentColor: colors.danger
                        textColor: colors.danger
                        Layout.fillWidth: true
                        onClicked: app.retryFailedResults()
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
                        required property string backendKey
                        required property bool failed
                        required property int wordCount
                        property bool selected: index === resultList.currentIndex
                        property color emphasisColor: failed ? colors.danger : colors.accent

                        width: resultList.width
                        height: 68
                        radius: 9
                        activeFocusOnTab: true
                        color: selected
                            ? Qt.rgba(emphasisColor.r, emphasisColor.g, emphasisColor.b, dark ? 0.12 : 0.08)
                            : rowMouse.containsMouse
                                ? Qt.rgba(emphasisColor.r, emphasisColor.g, emphasisColor.b, dark ? 0.08 : 0.06)
                                : colors.surfaceAlt
                        border.color: activeFocus
                            ? Qt.rgba(emphasisColor.r, emphasisColor.g, emphasisColor.b, dark ? 0.92 : 0.76)
                            : selected
                                ? Qt.rgba(emphasisColor.r, emphasisColor.g, emphasisColor.b, dark ? 0.70 : 0.62)
                                : colors.border
                        border.width: activeFocus ? 2 : 1
                        Accessible.role: Accessible.ListItem
                        Accessible.name: failed
                            ? root.tr("qml_failed_conversion_accessible").replace("{name}", name)
                            : root.tr("qml_converted_words_accessible")
                                .replace("{name}", name)
                                .replace("{count}", wordCount)

                        Behavior on color {
                            ColorAnimation {
                                duration: root.motionFastDuration
                            }
                        }

                        Behavior on border.color {
                            ColorAnimation {
                                duration: root.motionFastDuration
                            }
                        }

                        Keys.onReturnPressed: app.selectResult(index)
                        Keys.onEnterPressed: app.selectResult(index)
                        Keys.onSpacePressed: app.selectResult(index)

                        MouseArea {
                            id: rowMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                resultRow.forceActiveFocus()
                                app.selectResult(index)
                            }
                        }

                        Rectangle {
                            visible: resultRow.selected
                            width: 3
                            height: parent.height - 18
                            radius: 2
                            color: resultRow.emphasisColor
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
                                        text: failed ? root.tr("qml_failed") : (backendKey ? root.tr(backendKey) : backend)
                                        color: failed ? colors.danger : colors.muted
                                        font.pixelSize: 11
                                    }

                                    Label {
                                        visible: !failed
                                        text: root.tr("qml_word_count").replace("{count}", wordCount)
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
                title: app.selectedResultFailed
                    ? root.tr("qml_conversion_failed")
                    : root.tr("qml_markdown_preview")
                subtitle: app.selectedResultFailed
                    ? root.tr("qml_conversion_failed_detail")
                    : root.tr("qml_markdown_preview_detail")
                surfaceColor: colors.surface
                borderColor: colors.border
                textColor: colors.text
                mutedTextColor: colors.muted
                borderOpacity: dark ? 0.88 : 0.68
                Layout.fillWidth: true
                Layout.fillHeight: true

                ColumnLayout {
                    id: previewToolbar

                    property bool compactActions: root.compactLayout || width < 420

                    Layout.fillWidth: true
                    Layout.minimumWidth: 0
                    spacing: 8

                    RowLayout {
                        Layout.fillWidth: true
                        Layout.minimumWidth: 0

                        PreviewModeButton {
                            visible: !app.selectedResultFailed
                            text: root.tr("home_rendered_view_button")
                            selected: app.previewMode === "rendered"
                            onClicked: app.setPreviewMode("rendered")
                        }

                        PreviewModeButton {
                            visible: !app.selectedResultFailed
                            text: root.tr("home_raw_view_button")
                            selected: app.previewMode === "raw"
                            onClicked: app.setPreviewMode("raw")
                        }

                        Item {
                            Layout.fillWidth: true
                        }

                        AppButton {
                            visible: !previewToolbar.compactActions
                            text: app.selectedResultFailed
                                ? root.tr("qml_copy_details")
                                : root.tr("home_copy_markdown_button")
                            iconName: "copy"
                            accentColor: app.selectedResultFailed ? colors.danger : colors.action
                            primaryTextColor: colors.onAction
                            surfaceColor: colors.surfaceAlt
                            borderColor: app.selectedResultFailed ? colors.danger : colors.border
                            textColor: app.selectedResultFailed ? colors.danger : colors.text
                            onClicked: app.copySelectedMarkdown()
                        }

                        AppButton {
                            visible: !previewToolbar.compactActions
                            text: app.saveCombined
                                ? root.tr("qml_save_as_one_file")
                                : root.tr("qml_save_files")
                            enabled: app.hasSuccessfulResults
                            primary: app.hasSuccessfulResults
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
                        Layout.minimumWidth: 0

                        Item {
                            Layout.fillWidth: true
                        }

                        AppButton {
                            text: app.selectedResultFailed
                                ? root.tr("qml_copy_details")
                                : root.tr("home_copy_markdown_button")
                            iconName: "copy"
                            accentColor: app.selectedResultFailed ? colors.danger : colors.action
                            primaryTextColor: colors.onAction
                            surfaceColor: colors.surfaceAlt
                            borderColor: app.selectedResultFailed ? colors.danger : colors.border
                            textColor: app.selectedResultFailed ? colors.danger : colors.text
                            onClicked: app.copySelectedMarkdown()
                        }

                        AppButton {
                            text: root.tr("save_button")
                            enabled: app.hasSuccessfulResults
                            primary: app.hasSuccessfulResults
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

                Item {
                    id: previewFrame

                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    ScrollView {
                        id: previewScroll

                        property bool canScroll: contentHeight > height + 1

                        anchors.fill: parent
                        clip: true
                        contentWidth: availableWidth
                        contentHeight: previewCanvas.height
                        ScrollBar.vertical: ScrollBar {
                            id: previewScrollBar

                            policy: previewScroll.canScroll ? ScrollBar.AlwaysOn : ScrollBar.AlwaysOff
                            minimumSize: 0.08

                            contentItem: Rectangle {
                                implicitWidth: 6
                                radius: 3
                                color: Qt.rgba(colors.muted.r, colors.muted.g, colors.muted.b, dark ? 0.52 : 0.36)
                            }

                            background: Rectangle {
                                implicitWidth: 8
                                radius: 4
                                color: Qt.rgba(colors.border.r, colors.border.g, colors.border.b, dark ? 0.20 : 0.26)
                            }
                        }

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
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.top: parent.top
                                height: Math.min(
                                    parent.height,
                                    Math.max(190, failedContent.implicitHeight + 36)
                                )
                                radius: 9
                                color: colors.document
                                border.color: Qt.rgba(colors.danger.r, colors.danger.g, colors.danger.b, dark ? 0.55 : 0.40)

                                ColumnLayout {
                                    id: failedContent

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
                                                text: root.tr("qml_input_conversion_failed")
                                                color: colors.text
                                                font.pixelSize: 15
                                                font.weight: Font.DemiBold
                                                wrapMode: Text.WordWrap
                                                Layout.fillWidth: true
                                            }

                                            Label {
                                                text: root.tr("qml_failure_details_help")
                                                color: colors.muted
                                                font.pixelSize: 12
                                                wrapMode: Text.WordWrap
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

                                    RowLayout {
                                        Layout.fillWidth: true

                                        Label {
                                            text: app.failedResultCount === 1
                                                ? root.tr("qml_retry_one_detail")
                                                : root.tr("qml_retry_many_detail").replace("{count}", app.failedResultCount)
                                            color: colors.muted
                                            font.pixelSize: 12
                                            wrapMode: Text.WordWrap
                                            Layout.fillWidth: true
                                        }

                                        AppButton {
                                            text: root.tr("qml_retry_failed")
                                            iconName: "rotate-ccw"
                                            accentColor: colors.danger
                                            surfaceColor: colors.surfaceAlt
                                            borderColor: colors.danger
                                            textColor: colors.danger
                                            onClicked: app.retryFailedResults()
                                        }
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

                    Item {
                        id: previewScrollIndicator

                        visible: previewScroll.canScroll
                        width: 8
                        anchors.top: parent.top
                        anchors.topMargin: 12
                        anchors.right: parent.right
                        anchors.rightMargin: 13
                        anchors.bottom: parent.bottom
                        anchors.bottomMargin: 12
                        z: 3
                        Accessible.role: Accessible.Indicator
                        Accessible.name: root.tr("qml_preview_scroll_position")

                        Rectangle {
                            width: 3
                            radius: 2
                            color: Qt.rgba(colors.border.r, colors.border.g, colors.border.b, dark ? 0.42 : 0.48)
                            anchors.top: parent.top
                            anchors.bottom: parent.bottom
                            anchors.horizontalCenter: parent.horizontalCenter
                        }

                        Rectangle {
                            width: 5
                            height: Math.max(28, previewScrollIndicator.height * previewScrollBar.size)
                            radius: 3
                            color: Qt.rgba(colors.action.r, colors.action.g, colors.action.b, dark ? 0.66 : 0.58)
                            anchors.horizontalCenter: parent.horizontalCenter
                            y: Math.max(
                                0,
                                Math.min(
                                    previewScrollIndicator.height - height,
                                    (previewScrollIndicator.height - height)
                                        * previewScrollBar.position
                                        / Math.max(0.0001, 1 - previewScrollBar.size)
                                )
                            )
                        }
                    }

                    Rectangle {
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.bottom: parent.bottom
                        anchors.rightMargin: previewScroll.canScroll ? 18 : 0
                        height: 34
                        visible: previewScroll.canScroll && previewScrollBar.position + previewScrollBar.size < 0.98
                        radius: 8
                        gradient: Gradient {
                            orientation: Gradient.Vertical
                            GradientStop {
                                position: 0.0
                                color: app.previewMode === "raw"
                                    ? Qt.rgba(colors.input.r, colors.input.g, colors.input.b, 0.0)
                                    : Qt.rgba(colors.document.r, colors.document.g, colors.document.b, 0.0)
                            }
                            GradientStop {
                                position: 1.0
                                color: app.previewMode === "raw" ? colors.input : colors.document
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
                title: root.tr("qml_output_title")
                subtitle: root.tr("qml_output_detail")
                surfaceColor: colors.surface
                borderColor: colors.border
                textColor: colors.text
                mutedTextColor: colors.muted
                panelPadding: 14
                contentSpacing: 10
                bodySpacing: 9
                borderOpacity: dark ? 0.90 : 0.72
                Layout.fillWidth: true

                SettingsField {
                    label: root.tr("qml_default_folder")
                    detail: root.tr("qml_default_folder_detail")
                    Layout.fillWidth: true

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10

                        AppTextField {
                            text: app.outputFolder
                            placeholderText: root.tr("qml_no_default_folder")
                            Accessible.name: root.tr("qml_default_output_folder")
                            surfaceColor: colors.input
                            borderColor: colors.border
                            accentColor: colors.accent
                            textColor: colors.text
                            placeholderColor: colors.subtle
                            Layout.fillWidth: true
                            onEditingFinished: app.setOutputFolder(text)
                        }

                        AppButton {
                            text: root.tr("browse_button_compact")
                            accentColor: colors.action
                            surfaceColor: colors.surfaceAlt
                            borderColor: colors.border
                            textColor: colors.text
                            onClicked: outputFolderDialog.open()
                        }
                    }
                }

                ThemeToggleRow {
                    title: root.tr("qml_combined_save_mode")
                    detail: root.tr("qml_combined_save_mode_detail")
                    checked: app.saveCombined
                    textColor: colors.text
                    mutedTextColor: colors.muted
                    onToggled: checked => app.setSaveCombined(checked)
                    Layout.fillWidth: true
                }

                ThemeToggleRow {
                    title: root.tr("settings_save_to_source_folder_label")
                    detail: root.tr("settings_save_to_source_folder_tooltip")
                    checked: app.saveToSourceFolder
                    textColor: colors.text
                    mutedTextColor: colors.muted
                    onToggled: checked => app.setSaveToSourceFolder(checked)
                    Layout.fillWidth: true
                }

                ThemeToggleRow {
                    title: root.tr("qml_update_notifications")
                    detail: root.tr("qml_update_notifications_detail")
                    checked: app.updateNotificationsEnabled
                    textColor: colors.text
                    mutedTextColor: colors.muted
                    onToggled: checked => app.setUpdateNotificationsEnabled(checked)
                    Layout.fillWidth: true
                }
            }

            SectionPanel {
                title: root.tr("settings_conversion_group")
                subtitle: root.tr("settings_conversion_detail")
                surfaceColor: colors.surface
                borderColor: colors.border
                textColor: colors.text
                mutedTextColor: colors.muted
                panelPadding: 14
                contentSpacing: 10
                bodySpacing: 9
                borderOpacity: dark ? 0.90 : 0.72
                Layout.fillWidth: true

                ThemeToggleRow {
                    title: root.tr("settings_anydoc_default_label")
                    detail: root.tr("settings_anydoc_default_detail")
                    checked: app.anydocDefaultEnabled
                    textColor: colors.text
                    mutedTextColor: colors.muted
                    onToggled: checked => app.setAnydocDefaultEnabled(checked)
                    Layout.fillWidth: true
                }
            }

            SectionPanel {
                title: root.tr("settings_appearance_group")
                subtitle: root.tr("settings_appearance_detail")
                surfaceColor: colors.surface
                borderColor: colors.border
                textColor: colors.text
                mutedTextColor: colors.muted
                panelPadding: 14
                contentSpacing: 10
                bodySpacing: 9
                borderOpacity: dark ? 0.90 : 0.72
                Layout.fillWidth: true

                SettingsField {
                    label: root.tr("settings_theme_label")
                    detail: root.tr("settings_theme_detail")
                    Layout.fillWidth: true

                    ThemeComboBox {
                        Accessible.name: root.tr("qml_application_theme")
                        model: [root.tr("qml_theme_light"), root.tr("qml_theme_dark"), root.tr("qml_theme_system")]
                        currentIndex: app.themeMode === "dark" ? 1 : app.themeMode === "system" ? 2 : 0
                        onActivated: index => app.setThemeMode(index === 1 ? "dark" : index === 2 ? "system" : "light")
                        Layout.fillWidth: true
                        Layout.maximumWidth: 380
                        Layout.alignment: Qt.AlignLeft
                    }
                }

                SettingsField {
                    label: root.tr("settings_language_label")
                    detail: root.tr("settings_language_detail")
                    Layout.fillWidth: true

                    ThemeComboBox {
                        Accessible.name: root.tr("settings_language_label")
                        model: app.availableLanguageLabels
                        currentIndex: Math.max(0, app.availableLanguageCodes.indexOf(app.currentLanguage))
                        onActivated: index => app.setLanguage(app.availableLanguageCodes[index])
                        Layout.fillWidth: true
                        Layout.maximumWidth: 380
                        Layout.alignment: Qt.AlignLeft
                    }
                }

                ThemeToggleRow {
                    title: root.tr("qml_reduce_motion")
                    detail: root.tr("qml_reduce_motion_detail")
                    checked: app.reduceMotion
                    textColor: colors.text
                    mutedTextColor: colors.muted
                    onToggled: checked => app.setReduceMotion(checked)
                    Layout.fillWidth: true
                }
            }

            SectionPanel {
                title: root.tr("settings_ocr_group")
                subtitle: root.tr("qml_ocr_settings_detail")
                surfaceColor: colors.surface
                borderColor: colors.border
                textColor: colors.text
                mutedTextColor: colors.muted
                panelPadding: 14
                contentSpacing: 10
                bodySpacing: 9
                borderOpacity: dark ? 0.90 : 0.72
                Layout.fillWidth: true

                ThemeToggleRow {
                    title: root.tr("qml_ocr_enabled")
                    detail: root.tr("settings_ocr_enable_tooltip")
                    checked: app.ocrEnabled
                    textColor: colors.text
                    mutedTextColor: colors.muted
                    onToggled: checked => app.setOcrEnabled(checked)
                    Layout.fillWidth: true
                }

                FieldGroup {
                    label: root.tr("qml_ocr_presets")
                    detail: root.tr("qml_ocr_presets_detail")
                    Layout.fillWidth: true

                    ColumnLayout {
                        spacing: 8
                        Layout.fillWidth: true

                        Repeater {
                            model: app.ocrPresetActions

                            delegate: RowLayout {
                                spacing: 10
                                Layout.fillWidth: true

                                ColumnLayout {
                                    spacing: 2
                                    Layout.fillWidth: true

                                    Label {
                                        text: modelData.label
                                        color: colors.text
                                        font.pixelSize: 12
                                        font.weight: Font.DemiBold
                                        elide: Text.ElideRight
                                        Layout.fillWidth: true
                                    }

                                    Label {
                                        text: modelData.detail
                                        color: colors.muted
                                        font.pixelSize: 11
                                        wrapMode: Text.WordWrap
                                        Layout.fillWidth: true
                                    }
                                }

                                AppButton {
                                    text: root.tr("qml_apply")
                                    iconName: "file-check"
                                    accentColor: colors.action
                                    surfaceColor: colors.surfaceAlt
                                    borderColor: colors.border
                                    textColor: colors.text
                                    onClicked: app.applyOcrPreset(modelData.id)
                                }
                            }
                        }
                    }
                }

                FieldGroup {
                    label: root.tr("qml_primary_provider")
                    detail: root.tr("qml_primary_provider_detail")
                    visible: app.ocrEnabled
                    Layout.fillWidth: true

                    ThemeComboBox {
                        Accessible.name: root.tr("qml_primary_ocr_provider")
                        model: [
                            root.tr("settings_ocr_provider_azure_tesseract"),
                            root.tr("settings_ocr_provider_glmocr"),
                            root.tr("conversion_backend_http_ocr")
                        ]
                        currentIndex: root.ocrProviderIndex(app.ocrProvider)
                        onActivated: index => app.setOcrProvider(root.ocrProviderFromIndex(index))
                        Layout.fillWidth: true
                    }
                }

                FieldGroup {
                    label: root.tr("qml_fallback_provider")
                    detail: root.ocrFallbackDetail()
                    visible: app.ocrEnabled && app.ocrProvider !== "azure_tesseract"
                    Layout.fillWidth: true

                    ThemeComboBox {
                        Accessible.name: root.tr("qml_fallback_ocr_provider")
                        model: root.ocrFallbackLabels()
                        currentIndex: root.ocrFallbackIndex(app.ocrFallbackProvider)
                        onActivated: index => app.setOcrFallbackProvider(root.ocrFallbackFromIndex(index))
                        Layout.fillWidth: true
                    }
                }

                FieldGroup {
                    label: root.tr("qml_provider_capabilities")
                    visible: app.ocrEnabled
                    Layout.fillWidth: true

                    ColumnLayout {
                        spacing: 5
                        Layout.fillWidth: true

                        Repeater {
                            model: app.ocrProviderOptions

                            delegate: RowLayout {
                                spacing: 8
                                Layout.fillWidth: true
                                opacity: modelData.id === app.ocrProvider ? 1.0 : 0.68

                                Label {
                                    text: modelData.label
                                    color: colors.text
                                    font.pixelSize: 12
                                    font.weight: modelData.id === app.ocrProvider ? Font.DemiBold : Font.Normal
                                    Layout.preferredWidth: 118
                                    elide: Text.ElideRight
                                }

                                Label {
                                    text: modelData.capabilities.join(" / ")
                                    color: colors.muted
                                    font.pixelSize: 11
                                    wrapMode: Text.WordWrap
                                    Layout.fillWidth: true
                                }
                            }
                        }
                    }
                }

                FieldGroup {
                    label: root.tr("qml_setup_actions")
                    detail: root.tr("qml_setup_actions_detail")
                    visible: app.ocrEnabled
                    Layout.fillWidth: true

                    ColumnLayout {
                        spacing: 8
                        Layout.fillWidth: true

                        Repeater {
                            model: app.ocrSetupActions

                            delegate: RowLayout {
                                spacing: 10
                                Layout.fillWidth: true

                                ColumnLayout {
                                    spacing: 2
                                    Layout.fillWidth: true

                                    Label {
                                        text: modelData.label
                                        color: colors.text
                                        font.pixelSize: 12
                                        font.weight: Font.DemiBold
                                        elide: Text.ElideRight
                                        Layout.fillWidth: true
                                    }

                                    Label {
                                        text: modelData.detail
                                        color: colors.muted
                                        font.pixelSize: 11
                                        wrapMode: Text.WordWrap
                                        Layout.fillWidth: true
                                    }
                                }

                                AppButton {
                                    text: modelData.action === "open"
                                        ? root.tr("qml_open")
                                        : root.tr("home_copy_markdown_button")
                                    iconName: modelData.action === "open" ? "external-link" : "copy"
                                    accentColor: colors.action
                                    surfaceColor: colors.surfaceAlt
                                    borderColor: colors.border
                                    textColor: colors.text
                                    onClicked: app.runOcrSetupAction(
                                        modelData.action,
                                        modelData.value,
                                        modelData.label
                                    )
                                }
                            }
                        }
                    }
                }

                FieldGroup {
                    label: app.ocrProvider === "glmocr"
                        ? root.tr("qml_fallback_azure_endpoint")
                        : root.tr("qml_azure_endpoint")
                    detail: app.ocrProvider === "glmocr"
                        ? root.tr("qml_fallback_azure_endpoint_detail")
                        : root.tr("qml_azure_endpoint_detail")
                    visible: root.showAzureTesseractSettings()
                    Layout.fillWidth: true

                    AppTextField {
                        text: app.docintelEndpoint
                        placeholderText: "https://example.cognitiveservices.azure.com/"
                        Accessible.name: app.ocrProvider === "glmocr"
                            ? root.tr("qml_fallback_azure_endpoint")
                            : root.tr("qml_azure_endpoint")
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
                    label: app.ocrProvider === "glmocr"
                        ? root.tr("qml_fallback_tesseract_languages")
                        : root.tr("qml_tesseract_languages")
                    detail: app.ocrProvider === "glmocr"
                        ? root.tr("qml_fallback_tesseract_languages_detail")
                        : ""
                    visible: root.showAzureTesseractSettings()
                    Layout.fillWidth: true

                    AppTextField {
                        text: app.ocrLanguages
                        placeholderText: "eng or eng+deu"
                        Accessible.name: app.ocrProvider === "glmocr"
                            ? root.tr("qml_fallback_tesseract_languages")
                            : root.tr("qml_tesseract_languages")
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
                    label: app.ocrProvider === "glmocr"
                        ? root.tr("qml_fallback_tesseract_executable")
                        : root.tr("qml_tesseract_executable")
                    detail: app.ocrProvider === "glmocr"
                        ? root.tr("qml_fallback_tesseract_executable_detail")
                        : ""
                    visible: root.showAzureTesseractSettings()
                    Layout.fillWidth: true

                    AppTextField {
                        text: app.tesseractPath
                        placeholderText: root.tr("qml_optional_executable_path")
                        Accessible.name: app.ocrProvider === "glmocr"
                            ? root.tr("qml_fallback_tesseract_executable")
                            : root.tr("qml_tesseract_executable")
                        surfaceColor: colors.input
                        borderColor: colors.border
                        accentColor: colors.accent
                        textColor: colors.text
                        placeholderColor: colors.subtle
                        Layout.fillWidth: true
                        onEditingFinished: app.setTesseractPath(text)
                    }
                }

                RowLayout {
                    visible: app.ocrEnabled
                    spacing: 10
                    Layout.fillWidth: true

                    Label {
                        text: root.tr("qml_ocr_validation_detail")
                        color: colors.muted
                        font.pixelSize: 12
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }

                    AppButton {
                        text: root.tr("qml_validate_ocr")
                        iconName: "file-check"
                        accentColor: colors.action
                        surfaceColor: colors.surfaceAlt
                        borderColor: colors.border
                        textColor: colors.text
                        onClicked: app.validateOcrSetup()
                    }

                    AppButton {
                        text: root.tr("qml_test_connection")
                        iconName: "external-link"
                        accentColor: colors.action
                        surfaceColor: colors.surfaceAlt
                        borderColor: colors.border
                        textColor: colors.text
                        onClicked: app.testOcrConnection()
                    }
                }
            }

            SectionPanel {
                title: root.tr("settings_glmocr_group")
                subtitle: root.tr("qml_glmocr_detail")
                surfaceColor: colors.surface
                borderColor: colors.border
                textColor: colors.text
                mutedTextColor: colors.muted
                panelPadding: 14
                contentSpacing: 10
                bodySpacing: 9
                borderOpacity: dark ? 0.90 : 0.72
                visible: app.ocrEnabled && app.ocrProvider === "glmocr"
                Layout.fillWidth: true

                FieldGroup {
                    label: root.tr("settings_glmocr_mode_label")
                    detail: app.glmocrMode === "ollama"
                        ? root.tr("qml_glmocr_ollama_detail")
                        : app.glmocrMode === "sdk_server"
                            ? root.tr("qml_glmocr_sdk_detail")
                            : root.tr("qml_glmocr_api_detail")
                    Layout.fillWidth: true

                    ThemeComboBox {
                        Accessible.name: root.tr("qml_glmocr_mode")
                        model: [
                            root.tr("settings_glmocr_mode_maas"),
                            root.tr("settings_glmocr_mode_ollama"),
                            root.tr("settings_glmocr_mode_sdk_server")
                        ]
                        currentIndex: app.glmocrMode === "ollama" ? 1 : app.glmocrMode === "sdk_server" ? 2 : 0
                        onActivated: index => app.setGlmocrMode(index === 1 ? "ollama" : index === 2 ? "sdk_server" : "maas")
                        Layout.fillWidth: true
                    }
                }

                FieldGroup {
                    label: root.tr("settings_glmocr_ollama_host_label")
                    visible: app.glmocrMode === "ollama"
                    Layout.fillWidth: true

                    AppTextField {
                        text: app.glmocrOllamaHost
                        placeholderText: "127.0.0.1"
                        Accessible.name: root.tr("qml_glmocr_ollama_host")
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
                        label: root.tr("settings_glmocr_ollama_port_label")
                        Layout.preferredWidth: 150
                        Layout.fillWidth: false

                        ThemeSpinBox {
                            Accessible.name: root.tr("qml_glmocr_ollama_port")
                            from: 1
                            to: 65535
                            value: app.glmocrOllamaPort
                            textFromValue: function(value, locale) { return value.toString() }
                            onValueModified: app.setGlmocrOllamaPort(value)
                        }
                    }

                    FieldGroup {
                        label: root.tr("settings_glmocr_ollama_model_label")
                        Layout.fillWidth: true

                        AppTextField {
                            text: app.glmocrOllamaModel
                            placeholderText: "glm-ocr:latest"
                            Accessible.name: root.tr("qml_glmocr_ollama_model")
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
                    label: root.tr("settings_glmocr_sdk_server_url_label")
                    visible: app.glmocrMode === "sdk_server"
                    Layout.fillWidth: true

                    AppTextField {
                        text: app.glmocrSdkServerUrl
                        placeholderText: "http://127.0.0.1:5002/glmocr/parse"
                        Accessible.name: root.tr("qml_glmocr_sdk_server_endpoint")
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

            SectionPanel {
                title: root.tr("conversion_backend_http_ocr")
                subtitle: root.tr("qml_http_ocr_detail")
                surfaceColor: colors.surface
                borderColor: colors.border
                textColor: colors.text
                mutedTextColor: colors.muted
                panelPadding: 14
                contentSpacing: 10
                bodySpacing: 9
                borderOpacity: dark ? 0.90 : 0.72
                visible: root.showHttpOcrSettings()
                Layout.fillWidth: true

                FieldGroup {
                    label: root.tr("qml_endpoint")
                    detail: root.tr("qml_http_ocr_endpoint_detail")
                    Layout.fillWidth: true

                    AppTextField {
                        text: app.httpOcrEndpoint
                        placeholderText: "http://127.0.0.1:8000/ocr"
                        Accessible.name: root.tr("qml_http_ocr_endpoint")
                        surfaceColor: colors.input
                        borderColor: colors.border
                        accentColor: colors.accent
                        textColor: colors.text
                        placeholderColor: colors.subtle
                        Layout.fillWidth: true
                        onEditingFinished: app.setHttpOcrEndpoint(text)
                    }
                }

                RowLayout {
                    spacing: 10
                    Layout.fillWidth: true

                    FieldGroup {
                        label: root.tr("qml_model")
                        detail: root.tr("qml_optional_model_detail")
                        Layout.fillWidth: true

                        AppTextField {
                            text: app.httpOcrModel
                            placeholderText: "surya, doctr, paddleocr, ..."
                            Accessible.name: root.tr("qml_http_ocr_model")
                            surfaceColor: colors.input
                            borderColor: colors.border
                            accentColor: colors.accent
                            textColor: colors.text
                            placeholderColor: colors.subtle
                            Layout.fillWidth: true
                            onEditingFinished: app.setHttpOcrModel(text)
                        }
                    }

                    FieldGroup {
                        label: root.tr("qml_timeout")
                        detail: root.tr("qml_seconds_detail")
                        Layout.preferredWidth: 150
                        Layout.fillWidth: false

                        ThemeSpinBox {
                            Accessible.name: root.tr("qml_http_ocr_timeout")
                            from: 1
                            to: 3600
                            value: app.httpOcrTimeoutSeconds
                            textFromValue: function(value, locale) { return value.toString() }
                            onValueModified: app.setHttpOcrTimeoutSeconds(value)
                        }
                    }
                }

                FieldGroup {
                    label: root.tr("qml_api_key_environment_variable")
                    detail: root.tr("qml_api_key_environment_variable_detail")
                    Layout.fillWidth: true

                    AppTextField {
                        text: app.httpOcrApiKeyEnv
                        placeholderText: "OCR_HTTP_API_KEY"
                        Accessible.name: root.tr("qml_http_ocr_api_key_environment_variable")
                        surfaceColor: colors.input
                        borderColor: colors.border
                        accentColor: colors.accent
                        textColor: colors.text
                        placeholderColor: colors.subtle
                        Layout.fillWidth: true
                        onEditingFinished: app.setHttpOcrApiKeyEnv(text)
                    }
                }
            }

            SectionPanel {
                title: root.tr("qml_settings_profile")
                subtitle: root.tr("qml_settings_profile_detail")
                surfaceColor: colors.surface
                borderColor: colors.border
                textColor: colors.text
                mutedTextColor: colors.muted
                panelPadding: 14
                contentSpacing: 10
                bodySpacing: 9
                borderOpacity: dark ? 0.90 : 0.72
                Layout.fillWidth: true

                RowLayout {
                    spacing: 10
                    Layout.fillWidth: true

                    Label {
                        text: root.tr("qml_settings_profile_explanation")
                        color: colors.muted
                        font.pixelSize: 12
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }

                    AppButton {
                        text: root.tr("qml_export")
                        iconName: "save"
                        accentColor: colors.action
                        surfaceColor: colors.surfaceAlt
                        borderColor: colors.border
                        textColor: colors.text
                        onClicked: exportSettingsProfileDialog.open()
                    }

                    AppButton {
                        text: root.tr("qml_import")
                        iconName: "folder-plus"
                        accentColor: colors.action
                        surfaceColor: colors.surfaceAlt
                        borderColor: colors.border
                        textColor: colors.text
                        onClicked: importSettingsProfileDialog.open()
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
            width: Math.min(helpPage.width - 48, 820)
            x: 24
            y: 24
            spacing: 16

            UtilitySectionPanel {
                title: root.tr("qml_common_tasks")
                subtitle: root.tr("qml_common_tasks_detail")

                Repeater {
                    model: [
                        { icon: "folder-plus", title: root.tr("qml_task_add_documents"), detail: root.tr("qml_task_add_documents_detail") },
                        { icon: "link", title: root.tr("qml_task_convert_webpage"), detail: root.tr("qml_task_convert_webpage_detail") },
                        { icon: "file-text", title: root.tr("qml_task_use_ocr"), detail: root.tr("qml_task_use_ocr_detail") },
                        { icon: "save", title: root.tr("qml_task_save_markdown"), detail: root.tr("qml_task_save_markdown_detail") }
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

            UtilitySectionPanel {
                title: root.tr("qml_reference_links")
                subtitle: root.tr("qml_reference_links_detail")

                RowLayout {
                    spacing: 10
                    Layout.fillWidth: true

                    Label {
                        text: app.availableReleaseAssets.length > 0
                            ? root.tr("qml_packaged_assets_available").replace("{version}", app.availableUpdateVersion)
                            : root.tr("qml_check_new_release")
                        color: colors.muted
                        font.pixelSize: 12
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }

                    AppButton {
                        text: root.tr("menu_check_updates")
                        iconName: "external-link"
                        accentColor: colors.action
                        surfaceColor: colors.surfaceAlt
                        borderColor: colors.border
                        textColor: colors.text
                        onClicked: app.checkForUpdates()
                    }
                }

                Label {
                    visible: !!app.availableReleaseNotes
                    text: app.availableReleaseNotes
                    color: colors.text
                    font.pixelSize: 12
                    wrapMode: Text.WordWrap
                    maximumLineCount: 4
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }

                GridLayout {
                    visible: app.preferredReleaseAssetPreflightItems.length > 0
                    columns: helpPage.width < 760 ? 1 : 2
                    columnSpacing: 16
                    rowSpacing: 8
                    Layout.fillWidth: true

                    Repeater {
                        model: app.preferredReleaseAssetPreflightItems

                        delegate: RowLayout {
                            spacing: 10
                            Layout.fillWidth: true

                            Label {
                                text: modelData.label
                                color: colors.text
                                font.pixelSize: 12
                                font.weight: Font.DemiBold
                                Layout.preferredWidth: 104
                                elide: Text.ElideRight
                            }

                            Label {
                                text: modelData.value
                                color: colors.muted
                                font.pixelSize: 12
                                wrapMode: Text.WordWrap
                                Layout.fillWidth: true
                            }
                        }
                    }
                }

                GridLayout {
                    visible: app.availableReleaseAssets.length > 0
                    columns: 2
                    columnSpacing: 10
                    rowSpacing: 10
                    Layout.fillWidth: true

                    Repeater {
                        model: app.availableReleaseAssets

                        delegate: AppButton {
                            text: modelData.name
                            iconName: "external-link"
                            accentColor: colors.action
                            surfaceColor: colors.surfaceAlt
                            borderColor: colors.border
                            textColor: colors.text
                            Layout.fillWidth: true
                            onClicked: app.openReleaseAsset(modelData.url)
                        }
                    }
                }

                RowLayout {
                    spacing: 10
                    Layout.fillWidth: true

                    Label {
                        text: app.sourceUpdateRunning
                            ? app.sourceUpdateStatus
                            : app.sourceUpdateCommand
                            ? root.tr("qml_source_update_detail")
                            : root.tr("qml_source_update_unavailable")
                        color: colors.muted
                        font.pixelSize: 12
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }

                    AppButton {
                        text: app.sourceUpdateRunning
                            ? root.tr("qml_updating")
                            : root.tr("qml_run_source_update")
                        iconName: "rotate-ccw"
                        accentColor: colors.action
                        surfaceColor: colors.surfaceAlt
                        borderColor: colors.border
                        textColor: colors.text
                        enabled: app.canRunSourceUpdate && !app.converting
                        onClicked: app.runSourceUpdate()
                    }

                    AppButton {
                        text: root.tr("qml_restart_app")
                        iconName: "rotate-ccw"
                        accentColor: colors.action
                        surfaceColor: colors.surfaceAlt
                        borderColor: colors.border
                        textColor: colors.text
                        visible: app.sourceUpdateNeedsRestart
                        enabled: app.sourceUpdateNeedsRestart
                            && !app.sourceUpdateRunning
                            && !app.updateInstallRunning
                            && !app.converting
                        onClicked: app.restartApp()
                    }

                    AppButton {
                        text: root.tr("qml_copy_command")
                        iconName: "copy"
                        accentColor: colors.action
                        surfaceColor: colors.surfaceAlt
                        borderColor: colors.border
                        textColor: colors.text
                        enabled: !!app.sourceUpdateCommand && !app.sourceUpdateRunning
                        onClicked: app.copySourceUpdateCommand()
                    }
                }

                ProgressBar {
                    visible: app.sourceUpdateRunning
                    from: 0
                    to: 100
                    value: app.sourceUpdateProgress
                    Layout.fillWidth: true
                    Layout.preferredHeight: 4
                }

                GridLayout {
                    columns: 2
                    columnSpacing: 10
                    rowSpacing: 10
                    Layout.fillWidth: true

                    Repeater {
                        model: [
                            { label: root.tr("help_open_repository"), url: "https://github.com/imadreamerboy/markitdown-gui" },
                            { label: root.tr("help_open_releases"), url: "https://github.com/imadreamerboy/markitdown-gui/releases" },
                            { label: root.tr("help_open_glmocr"), url: "https://github.com/zai-org/GLM-OCR" },
                            { label: root.tr("help_open_tesseract"), url: "https://github.com/tesseract-ocr/tesseract" },
                            { label: root.tr("help_open_defuddle_docs"), url: "https://defuddle.md/docs" },
                            { label: root.tr("help_open_azure_ocr_pricing"), url: "https://azure.microsoft.com/en-us/products/ai-foundry/tools/document-intelligence#Pricing" }
                        ]

                        delegate: AppButton {
                            text: modelData.label
                            iconName: "external-link"
                            accentColor: colors.action
                            surfaceColor: colors.surfaceAlt
                            borderColor: colors.border
                            textColor: colors.text
                            Layout.fillWidth: true
                            onClicked: app.openExternalUrl(modelData.url)
                        }
                    }
                }
            }

            UtilitySectionPanel {
                title: root.tr("qml_licensing")
                subtitle: root.tr("qml_licensing_detail")

                Label {
                    text: root.tr("qml_mit_license_text")
                    color: colors.text
                    font.pixelSize: 13
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }

                Label {
                    text: root.tr("qml_third_party_license_text")
                    color: colors.muted
                    font.pixelSize: 12
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }

                GridLayout {
                    columns: helpPage.width < 640 ? 1 : 2
                    columnSpacing: 10
                    rowSpacing: 10
                    Layout.fillWidth: true

                    Repeater {
                        model: [
                            { label: root.tr("qml_project_licence"), url: "https://github.com/imadreamerboy/markitdown-gui/blob/main/LICENSE" },
                            { label: root.tr("qml_third_party_notices"), url: "https://github.com/imadreamerboy/markitdown-gui/blob/main/THIRD_PARTY_NOTICES.md" }
                        ]

                        delegate: AppButton {
                            text: modelData.label
                            iconName: "external-link"
                            accentColor: colors.action
                            surfaceColor: colors.surfaceAlt
                            borderColor: colors.border
                            textColor: colors.text
                            Layout.fillWidth: true
                            onClicked: app.openExternalUrl(modelData.url)
                        }
                    }
                }
            }

            UtilitySectionPanel {
                title: root.tr("qml_diagnostics")
                subtitle: root.tr("qml_diagnostics_detail")

                GridLayout {
                    columns: helpPage.width < 840 ? 1 : 2
                    columnSpacing: 14
                    rowSpacing: 10
                    Layout.fillWidth: true

                    Repeater {
                        model: app.diagnosticReadinessItems

                        delegate: RowLayout {
                            spacing: 10
                            Layout.fillWidth: true

                            Label {
                                text: modelData.label
                                color: colors.text
                                font.pixelSize: 12
                                font.weight: Font.DemiBold
                                Layout.preferredWidth: 112
                                elide: Text.ElideRight
                            }

                            Label {
                                text: modelData.status
                                color: modelData.severity === "ok"
                                    ? colors.success
                                    : modelData.severity === "warn"
                                    ? colors.warning
                                    : colors.muted
                                font.pixelSize: 12
                                font.weight: Font.DemiBold
                                Layout.preferredWidth: 112
                                elide: Text.ElideRight
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

                RowLayout {
                    spacing: 10
                    Layout.fillWidth: true

                    Label {
                        text: root.tr("qml_diagnostics_actions_detail")
                        color: colors.muted
                        font.pixelSize: 12
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }

                    AppButton {
                        text: root.tr("qml_open_logs")
                        iconName: "external-link"
                        accentColor: colors.action
                        surfaceColor: colors.surfaceAlt
                        borderColor: colors.border
                        textColor: colors.text
                        onClicked: app.openLogFolder()
                    }

                    AppButton {
                        text: root.tr("qml_copy_diagnostics")
                        iconName: "copy"
                        accentColor: colors.action
                        surfaceColor: colors.surfaceAlt
                        borderColor: colors.border
                        textColor: colors.text
                        onClicked: app.copyDiagnostics()
                    }

                    AppButton {
                        text: root.tr("qml_export_bundle")
                        iconName: "save"
                        accentColor: colors.action
                        surfaceColor: colors.surfaceAlt
                        borderColor: colors.border
                        textColor: colors.text
                        onClicked: app.exportSupportBundle()
                    }
                }

                ColumnLayout {
                    visible: app.hasLastPackagedUpdateResult
                    spacing: 8
                    Layout.fillWidth: true

                    RowLayout {
                        spacing: 10
                        Layout.fillWidth: true

                        Label {
                            text: root.tr("qml_last_packaged_update")
                            color: colors.text
                            font.pixelSize: 12
                            font.weight: Font.DemiBold
                            Layout.fillWidth: true
                        }

                        AppButton {
                            text: root.tr("qml_open_backup_folder")
                            iconName: "external-link"
                            accentColor: colors.action
                            surfaceColor: colors.surfaceAlt
                            borderColor: colors.border
                            textColor: colors.text
                            visible: app.hasLastPackagedUpdateBackupPath
                            onClicked: app.openLastPackagedUpdateBackup()
                        }

                        AppButton {
                            text: root.tr("clear_list_button")
                            iconName: "x"
                            accentColor: colors.action
                            surfaceColor: colors.surfaceAlt
                            borderColor: colors.border
                            textColor: colors.text
                            onClicked: app.clearLastPackagedUpdateResult()
                        }
                    }

                    Label {
                        text: app.lastPackagedUpdateResult
                        color: colors.muted
                        font.pixelSize: 12
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                }
            }

            UtilitySectionPanel {
                title: root.tr("shortcuts_title")
                subtitle: root.tr("qml_shortcuts_detail")

                GridLayout {
                    columns: helpPage.width < 760 ? 1 : 2
                    columnSpacing: 18
                    rowSpacing: 10
                    Layout.fillWidth: true

                    Repeater {
                        model: [
                            { key: "Ctrl+O", action: root.tr("qml_shortcut_add_files") },
                            { key: "Ctrl+B", action: root.tr("qml_shortcut_convert_queue") },
                            { key: "Ctrl+P", action: root.tr("qml_shortcut_pause_resume") },
                            { key: "Ctrl+S", action: root.tr("qml_shortcut_save_markdown") },
                            { key: "Ctrl+C", action: root.tr("qml_shortcut_copy_result") },
                            { key: "Ctrl+R", action: root.tr("qml_shortcut_retry_failed") },
                            { key: "Ctrl+L", action: root.tr("qml_shortcut_clear_queue") },
                            { key: "Ctrl+K", action: root.tr("qml_shortcut_open_help") },
                            { key: "Esc", action: root.tr("qml_shortcut_cancel_conversion") }
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
        property bool showing: false

        visible: showing || opacity > 0
        opacity: showing ? 1 : 0
        width: Math.min(420, parent.width - 48)
        height: toastLabel.implicitHeight + 24
        radius: 10
        color: kind === "error" ? (dark ? "#3A1E22" : "#FFF2F0") : (dark ? "#153222" : "#EEF8F0")
        border.color: kind === "error" ? colors.danger : colors.success
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: 24
        z: 20

        Behavior on opacity {
            NumberAnimation {
                duration: root.motionStandardDuration
                easing.type: Easing.OutCubic
            }
        }

        transform: Translate {
            y: toast.showing ? 0 : 8

            Behavior on y {
                NumberAnimation {
                    duration: root.motionStandardDuration
                    easing.type: Easing.OutCubic
                }
            }
        }

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
        onTriggered: toast.showing = false
    }
}
