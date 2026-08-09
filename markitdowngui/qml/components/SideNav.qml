import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root

    property int currentIndex: 0
    property bool compact: false
    property bool reduceMotion: ApplicationWindow.window ? ApplicationWindow.window.reduceMotion : false
    property color backgroundColor: "#EEF3F7"
    property color activeColor: "#FFFFFF"
    property color textColor: "#18212B"
    property color mutedTextColor: "#647283"
    property color accentColor: "#88C0D0"
    property color borderColor: "#D8E1E8"
    property color focusColor: accentColor
    property color utilityHoverColor: Qt.rgba(0.5, 0.6, 0.7, 0.12)
    property color accentTextColor: "#FFFFFF"
    property string brandTitle: "MarkItDown"
    property string brandSubtitle: "Document studio"
    property string workspaceLabel: "Workspace"
    property string workspaceDescription: "Convert documents and webpages"
    property string workspaceDetail: "Convert to Markdown"
    property string workspaceHelp: "Add files, paste a URL, review Markdown, then export."
    property string helpLabel: "Help"
    property string helpDescription: "Open help and keyboard shortcuts"
    property string settingsLabel: "Settings"
    property string settingsDescription: "Configure output, appearance, and OCR"
    signal pageRequested(int index)

    implicitWidth: 224

    Rectangle {
        anchors.fill: parent
        color: root.backgroundColor
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 18

        RowLayout {
            spacing: 10
            Layout.fillWidth: true

            Rectangle {
                width: 36
                height: 36
                radius: 8
                color: root.accentColor

                Icon {
                    anchors.centerIn: parent
                    name: "file-text"
                    size: 18
                    color: root.accentTextColor
                }
            }

            ColumnLayout {
                visible: !root.compact
                spacing: 1
                Layout.fillWidth: true

                Label {
                    text: root.brandTitle
                    color: root.textColor
                    font.pixelSize: 14
                    font.weight: Font.DemiBold
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }

                Label {
                    text: root.brandSubtitle
                    color: root.mutedTextColor
                    font.pixelSize: 11
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
            }
        }

        Button {
            id: workspaceButton
            Layout.fillWidth: true
            implicitHeight: root.compact ? 44 : 56
            flat: true
            hoverEnabled: true
            scale: pressed && !root.reduceMotion ? 0.98 : 1
            Accessible.name: root.workspaceLabel
            Accessible.description: root.workspaceDescription
            onClicked: root.pageRequested(0)
            ToolTip.visible: hovered
            ToolTip.delay: 550
            ToolTip.text: root.workspaceDescription

            HoverHandler {
                cursorShape: Qt.PointingHandCursor
            }

            contentItem: RowLayout {
                spacing: 10

                Rectangle {
                    width: 30
                    height: 30
                    radius: 7
                    color: root.currentIndex === 0 ? root.accentColor : root.activeColor
                    border.color: root.currentIndex === 0 ? root.accentColor : root.borderColor

                    Icon {
                        anchors.centerIn: parent
                        name: "file-text"
                        size: 16
                        color: root.currentIndex === 0 ? root.accentTextColor : root.mutedTextColor
                    }
                }

                ColumnLayout {
                    visible: !root.compact
                    spacing: 1
                    Layout.fillWidth: true

                    Label {
                        text: root.workspaceLabel
                        color: root.textColor
                        font.pixelSize: 13
                        font.weight: root.currentIndex === 0 ? Font.DemiBold : Font.Medium
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                    }

                    Label {
                        text: root.workspaceDetail
                        color: root.mutedTextColor
                        font.pixelSize: 11
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                    }
                }
            }

            background: Rectangle {
                radius: 8
                color: root.currentIndex === 0
                    ? root.activeColor
                    : (workspaceButton.hovered ? root.utilityHoverColor : "transparent")
                border.color: workspaceButton.activeFocus ? root.focusColor : (root.currentIndex === 0 ? root.borderColor : "transparent")
                border.width: workspaceButton.activeFocus ? 2 : 1

                Behavior on color {
                    ColorAnimation {
                        duration: root.reduceMotion ? 0 : 110
                    }
                }

                Behavior on border.color {
                    ColorAnimation {
                        duration: root.reduceMotion ? 0 : 110
                    }
                }
            }

            Behavior on scale {
                NumberAnimation {
                    duration: root.reduceMotion ? 0 : 100
                    easing.type: Easing.OutCubic
                }
            }
        }

        Rectangle {
            height: 1
            color: root.borderColor
            Layout.fillWidth: true
        }

        Label {
            visible: !root.compact
            text: root.workspaceHelp
            color: root.mutedTextColor
            font.pixelSize: 12
            lineHeight: 1.15
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }

        Item {
            Layout.fillHeight: true
        }

        ColumnLayout {
            spacing: 6
            Layout.fillWidth: true

            Button {
                id: helpButton
                Layout.fillWidth: true
                implicitHeight: 40
                flat: true
                hoverEnabled: true
                scale: pressed && !root.reduceMotion ? 0.98 : 1
                Accessible.name: root.helpLabel
                Accessible.description: root.helpDescription
                onClicked: root.pageRequested(2)
                ToolTip.visible: hovered
                ToolTip.delay: 550
                ToolTip.text: root.helpLabel

                HoverHandler {
                    cursorShape: Qt.PointingHandCursor
                }

                contentItem: RowLayout {
                    spacing: 10

                    Rectangle {
                        width: 28
                        height: 28
                        radius: 14
                        color: root.currentIndex === 2 ? root.accentColor : root.activeColor
                        border.color: root.currentIndex === 2 ? root.accentColor : root.borderColor

                        Icon {
                            anchors.centerIn: parent
                            name: "circle-question-mark"
                            size: 16
                            color: root.currentIndex === 2 ? root.accentTextColor : root.textColor
                        }
                    }

                    Label {
                        visible: !root.compact
                        text: root.helpLabel
                        color: root.textColor
                        font.pixelSize: 13
                        font.weight: root.currentIndex === 2 ? Font.DemiBold : Font.Medium
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                    }
                }

                background: Rectangle {
                    radius: 8
                    color: root.currentIndex === 2
                        ? root.activeColor
                        : (helpButton.hovered ? root.utilityHoverColor : "transparent")
                    border.color: helpButton.activeFocus ? root.focusColor : (root.currentIndex === 2 ? root.borderColor : "transparent")
                    border.width: helpButton.activeFocus ? 2 : 1

                    Behavior on color {
                        ColorAnimation {
                            duration: root.reduceMotion ? 0 : 110
                        }
                    }

                    Behavior on border.color {
                        ColorAnimation {
                            duration: root.reduceMotion ? 0 : 110
                        }
                    }
                }

                Behavior on scale {
                    NumberAnimation {
                        duration: root.reduceMotion ? 0 : 100
                        easing.type: Easing.OutCubic
                    }
                }
            }

            Button {
                id: settingsButton
                Layout.fillWidth: true
                implicitHeight: 40
                flat: true
                hoverEnabled: true
                scale: pressed && !root.reduceMotion ? 0.98 : 1
                Accessible.name: root.settingsLabel
                Accessible.description: root.settingsDescription
                onClicked: root.pageRequested(1)
                ToolTip.visible: hovered
                ToolTip.delay: 550
                ToolTip.text: root.settingsLabel

                HoverHandler {
                    cursorShape: Qt.PointingHandCursor
                }

                contentItem: RowLayout {
                    spacing: 10

                    Rectangle {
                        width: 28
                        height: 28
                        radius: 7
                        color: root.currentIndex === 1 ? root.accentColor : root.activeColor
                        border.color: root.currentIndex === 1 ? root.accentColor : root.borderColor

                        Icon {
                            anchors.centerIn: parent
                            name: "settings"
                            size: 15
                            color: root.currentIndex === 1 ? root.accentTextColor : root.textColor
                        }
                    }

                    Label {
                        visible: !root.compact
                        text: root.settingsLabel
                        color: root.textColor
                        font.pixelSize: 13
                        font.weight: root.currentIndex === 1 ? Font.DemiBold : Font.Medium
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                    }
                }

                background: Rectangle {
                    radius: 8
                    color: root.currentIndex === 1
                        ? root.activeColor
                        : (settingsButton.hovered ? root.utilityHoverColor : "transparent")
                    border.color: settingsButton.activeFocus ? root.focusColor : (root.currentIndex === 1 ? root.borderColor : "transparent")
                    border.width: settingsButton.activeFocus ? 2 : 1

                    Behavior on color {
                        ColorAnimation {
                            duration: root.reduceMotion ? 0 : 110
                        }
                    }

                    Behavior on border.color {
                        ColorAnimation {
                            duration: root.reduceMotion ? 0 : 110
                        }
                    }
                }

                Behavior on scale {
                    NumberAnimation {
                        duration: root.reduceMotion ? 0 : 100
                        easing.type: Easing.OutCubic
                    }
                }
            }
        }
    }
}
