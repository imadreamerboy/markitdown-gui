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
    property color accentColor: "#138A87"
    signal pageRequested(int index)

    implicitWidth: 220

    Rectangle {
        anchors.fill: parent
        color: root.backgroundColor
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 14
        spacing: 14

        RowLayout {
            spacing: 10
            Layout.fillWidth: true

            Rectangle {
                width: 34
                height: 34
                radius: 9
                color: root.accentColor

                Label {
                    anchors.centerIn: parent
                    text: "M"
                    color: "#FFFFFF"
                    font.pixelSize: 16
                    font.weight: Font.Bold
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
                    text: "Desktop"
                    color: root.mutedTextColor
                    font.pixelSize: 11
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
            }
        }

        ColumnLayout {
            spacing: 6
            Layout.fillWidth: true

            Repeater {
                model: [
                    { label: "Convert", detail: "Queue and preview" },
                    { label: "Settings", detail: "Output and OCR" },
                    { label: "Help", detail: "References" }
                ]

                delegate: Button {
                    id: itemButton
                    Layout.fillWidth: true
                    implicitHeight: 50
                    flat: true
                    onClicked: root.pageRequested(index)

                    contentItem: ColumnLayout {
                        spacing: 1

                        Label {
                            text: modelData.label
                            color: root.textColor
                            font.pixelSize: 13
                            font.weight: index === root.currentIndex ? Font.DemiBold : Font.Medium
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                        }

                        Label {
                            text: modelData.detail
                            color: root.mutedTextColor
                            font.pixelSize: 11
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                        }
                    }

                    background: Rectangle {
                        radius: 8
                        color: index === root.currentIndex
                            ? root.activeColor
                            : (itemButton.hovered ? Qt.rgba(0.5, 0.6, 0.7, 0.12) : "transparent")

                        Rectangle {
                            visible: index === root.currentIndex
                            width: 3
                            height: 24
                            radius: 2
                            color: root.accentColor
                            anchors.left: parent.left
                            anchors.verticalCenter: parent.verticalCenter
                        }
                    }
                }
            }
        }

        Item {
            Layout.fillHeight: true
        }
    }
}

