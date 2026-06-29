import QtQuick
import QtQuick.Controls

ComboBox {
    id: control

    property color surfaceColor: "#FFFFFF"
    property color popupColor: surfaceColor
    property color hoverColor: "#F6EFD8"
    property color borderColor: "#D8E1E8"
    property color accentColor: "#88C0D0"
    property color textColor: "#18212B"
    property color mutedTextColor: "#647283"

    implicitHeight: 40
    leftPadding: 12
    rightPadding: 40
    font.pixelSize: 13

    delegate: ItemDelegate {
        width: control.width - 8
        height: 34
        hoverEnabled: true

        contentItem: Label {
            text: modelData
            color: control.textColor
            font.pixelSize: 13
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }

        background: Rectangle {
            radius: 7
            color: highlighted
                ? Qt.rgba(control.accentColor.r, control.accentColor.g, control.accentColor.b, 0.16)
                : (hovered ? control.hoverColor : "transparent")

            Behavior on color {
                ColorAnimation {
                    duration: 110
                }
            }
        }
    }

    indicator: Item {
        x: control.width - width
        y: 0
        width: 36
        height: control.height

        Item {
            anchors.centerIn: parent
            width: 12
            height: 8
            rotation: control.popup.visible ? 180 : 0

            Behavior on rotation {
                NumberAnimation {
                    duration: 120
                    easing.type: Easing.OutCubic
                }
            }

            Rectangle {
                width: 7
                height: 2
                radius: 1
                color: control.textColor
                rotation: 45
                x: 1
                y: 3
            }

            Rectangle {
                width: 7
                height: 2
                radius: 1
                color: control.textColor
                rotation: -45
                x: 5
                y: 3
            }
        }
    }

    contentItem: Label {
        leftPadding: control.leftPadding
        rightPadding: control.rightPadding
        text: control.displayText
        color: control.textColor
        font.pixelSize: 13
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }

    background: Rectangle {
        radius: 8
        color: control.surfaceColor
        border.color: control.activeFocus ? control.accentColor : control.borderColor
        border.width: control.activeFocus ? 2 : 1

        Behavior on border.color {
            ColorAnimation {
                duration: 110
            }
        }
    }

    popup: Popup {
        y: control.height + 4
        width: control.width
        implicitHeight: Math.min(contentItem.implicitHeight + 8, 240)
        padding: 4

        contentItem: ListView {
            clip: true
            implicitHeight: contentHeight
            model: control.popup.visible ? control.delegateModel : null
            currentIndex: control.highlightedIndex
            boundsBehavior: Flickable.StopAtBounds
        }

        background: Rectangle {
            radius: 8
            color: control.popupColor
            border.color: control.borderColor
            border.width: 1
        }
    }
}
