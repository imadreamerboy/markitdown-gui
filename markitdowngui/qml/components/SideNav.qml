import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root

    property int currentIndex: 0
    property color backgroundColor: "#EEF3F7"
    property color activeColor: "#FFFFFF"
    property color textColor: "#18212B"
    property color mutedTextColor: "#647283"
    property color accentColor: "#88C0D0"
    property color borderColor: "#D8E1E8"
    property color focusColor: accentColor
    property color utilityHoverColor: Qt.rgba(0.5, 0.6, 0.7, 0.12)
    property color accentTextColor: "#FFFFFF"
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
                spacing: 1
                Layout.fillWidth: true

                Label {
                    text: "MarkItDown"
                    color: root.textColor
                    font.pixelSize: 14
                    font.weight: Font.DemiBold
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }

                Label {
                    text: "Document studio"
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
            implicitHeight: 56
            flat: true
            onClicked: root.pageRequested(0)
            ToolTip.visible: hovered
            ToolTip.delay: 550
            ToolTip.text: "Convert documents and webpages"

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
                    spacing: 1
                    Layout.fillWidth: true

                    Label {
                        text: "Workspace"
                        color: root.textColor
                        font.pixelSize: 13
                        font.weight: root.currentIndex === 0 ? Font.DemiBold : Font.Medium
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                    }

                    Label {
                        text: "Convert to Markdown"
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
                        duration: 110
                    }
                }

                Behavior on border.color {
                    ColorAnimation {
                        duration: 110
                    }
                }
            }
        }

        Rectangle {
            height: 1
            color: root.borderColor
            Layout.fillWidth: true
        }

        Label {
            text: "Add files, paste a URL, review Markdown, then export."
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
                onClicked: root.pageRequested(2)
                ToolTip.visible: hovered
                ToolTip.delay: 550
                ToolTip.text: "Help"

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
                        text: "Help"
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
                            duration: 110
                        }
                    }

                    Behavior on border.color {
                        ColorAnimation {
                            duration: 110
                        }
                    }
                }
            }

            Button {
                id: settingsButton
                Layout.fillWidth: true
                implicitHeight: 40
                flat: true
                onClicked: root.pageRequested(1)
                ToolTip.visible: hovered
                ToolTip.delay: 550
                ToolTip.text: "Settings"

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
                        text: "Settings"
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
                            duration: 110
                        }
                    }

                    Behavior on border.color {
                        ColorAnimation {
                            duration: 110
                        }
                    }
                }
            }
        }
    }
}
