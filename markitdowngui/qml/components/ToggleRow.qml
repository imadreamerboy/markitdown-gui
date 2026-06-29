import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

RowLayout {
    id: root

    property string title: ""
    property string detail: ""
    property bool checked: false
    property color textColor: "#18212B"
    property color mutedTextColor: "#647283"
    property color accentColor: "#88C0D0"
    property color trackColor: "#F6EFD8"
    property color handleColor: "#FFFDF3"
    property color borderColor: "#D6CCB2"
    property color focusColor: "#88C0D0"
    signal toggled(bool checked)

    spacing: 12
    opacity: enabled ? 1 : 0.64

    Behavior on opacity {
        NumberAnimation {
            duration: 120
        }
    }

    ColumnLayout {
        spacing: 2
        Layout.fillWidth: true

        Label {
            text: root.title
            color: root.textColor
            font.pixelSize: 13
            font.weight: Font.Medium
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }

        Label {
            text: root.detail
            visible: root.detail.length > 0
            color: root.mutedTextColor
            font.pixelSize: 12
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }
    }

    Switch {
        id: switchControl

        checked: root.checked
        hoverEnabled: true
        Accessible.role: Accessible.Switch
        Accessible.name: root.title
        Accessible.description: root.detail
        onToggled: root.toggled(checked)

        indicator: Rectangle {
            implicitWidth: 46
            implicitHeight: 26
            x: switchControl.leftPadding
            y: parent.height / 2 - height / 2
            radius: height / 2
            color: switchControl.checked
                ? root.accentColor
                : (switchControl.hovered ? Qt.lighter(root.trackColor, 1.05) : root.trackColor)
            border.color: switchControl.activeFocus ? root.focusColor : root.borderColor
            border.width: switchControl.activeFocus ? 2 : 1

            Behavior on color {
                ColorAnimation {
                    duration: 120
                }
            }

            Rectangle {
                width: 20
                height: 20
                radius: 10
                x: switchControl.checked ? parent.width - width - 3 : 3
                y: 3
                color: root.handleColor
                border.color: switchControl.checked
                    ? Qt.rgba(root.accentColor.r, root.accentColor.g, root.accentColor.b, 0.35)
                    : Qt.rgba(root.borderColor.r, root.borderColor.g, root.borderColor.b, 0.8)
                border.width: 1

                Behavior on x {
                    NumberAnimation {
                        duration: 140
                        easing.type: Easing.OutCubic
                    }
                }
            }
        }

        contentItem: Item {
            implicitWidth: 46
            implicitHeight: 26
        }
    }
}

