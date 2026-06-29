import QtQuick
import QtQuick.Controls

TextField {
    id: control

    property color surfaceColor: "#FFFFFF"
    property color borderColor: "#D8E1E8"
    property color accentColor: "#88C0D0"
    property color textColor: "#18212B"
    property color placeholderColor: "#718091"

    implicitHeight: 38
    leftPadding: 12
    rightPadding: 12
    color: textColor
    placeholderTextColor: placeholderColor
    selectedTextColor: "#FFFFFF"
    selectionColor: accentColor
    font.pixelSize: 13

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
}

