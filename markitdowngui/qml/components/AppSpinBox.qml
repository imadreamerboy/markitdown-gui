import QtQuick
import QtQuick.Controls

SpinBox {
    id: control

    property color surfaceColor: "#FFFFFF"
    property color stepColor: "#F6EFD8"
    property color hoverColor: "#EFE3BC"
    property color borderColor: "#D8E1E8"
    property color accentColor: "#88C0D0"
    property color textColor: "#18212B"
    property color mutedTextColor: "#647283"
    property bool reduceMotion: ApplicationWindow.window ? ApplicationWindow.window.reduceMotion : false

    implicitWidth: 140
    implicitHeight: 40
    editable: false
    hoverEnabled: true
    font.pixelSize: 13

    HoverHandler {
        cursorShape: Qt.PointingHandCursor
    }

    contentItem: TextInput {
        z: 2
        text: control.textFromValue(control.value, control.locale)
        color: control.textColor
        selectedTextColor: "#FFFFFF"
        selectionColor: control.accentColor
        font.pixelSize: 13
        horizontalAlignment: Qt.AlignHCenter
        verticalAlignment: Qt.AlignVCenter
        readOnly: true
        validator: control.validator
        inputMethodHints: Qt.ImhFormattedNumbersOnly
    }

    up.indicator: Rectangle {
        x: control.width - width
        y: 0
        width: 40
        height: control.height
        color: control.up.pressed
            ? control.hoverColor
            : (control.up.hovered ? Qt.lighter(control.stepColor, 1.05) : control.stepColor)
        radius: 8

        Behavior on color {
            ColorAnimation {
                duration: control.reduceMotion ? 0 : 90
            }
        }

        Rectangle {
            width: 8
            height: parent.height
            color: parent.color
            anchors.left: parent.left
        }

        Icon {
            anchors.centerIn: parent
            name: "plus"
            size: 15
            color: control.textColor
        }
    }

    down.indicator: Rectangle {
        x: 0
        y: 0
        width: 40
        height: control.height
        color: control.down.pressed
            ? control.hoverColor
            : (control.down.hovered ? Qt.lighter(control.stepColor, 1.05) : control.stepColor)
        radius: 8

        Behavior on color {
            ColorAnimation {
                duration: control.reduceMotion ? 0 : 90
            }
        }

        Rectangle {
            width: 8
            height: parent.height
            color: parent.color
            anchors.right: parent.right
        }

        Icon {
            anchors.centerIn: parent
            name: "minus"
            size: 15
            color: control.textColor
        }
    }

    background: Rectangle {
        radius: 8
        color: control.surfaceColor
        border.color: control.activeFocus ? control.accentColor : control.borderColor
        border.width: control.activeFocus ? 2 : 1

        Behavior on border.color {
            ColorAnimation {
                duration: control.reduceMotion ? 0 : 110
            }
        }
    }
}
