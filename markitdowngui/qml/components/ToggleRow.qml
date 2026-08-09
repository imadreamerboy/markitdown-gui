import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
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
    property bool reduceMotion: ApplicationWindow.window ? ApplicationWindow.window.reduceMotion : false
    property bool hovered: rowMouse.containsMouse
    signal toggled(bool checked)

    implicitWidth: 0
    implicitHeight: contentLayout.implicitHeight
    Layout.minimumWidth: 0
    Layout.preferredWidth: 0
    opacity: enabled ? 1 : 0.64

    Behavior on opacity {
        NumberAnimation {
            duration: root.reduceMotion ? 0 : 120
        }
    }

    MouseArea {
        id: rowMouse

        anchors.fill: parent
        z: -1
        acceptedButtons: Qt.LeftButton
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: root.toggled(!root.checked)
    }

    RowLayout {
        id: contentLayout

        anchors.fill: parent
        spacing: 12

        ColumnLayout {
            spacing: 2
            Layout.fillWidth: true
            Layout.minimumWidth: 0

            Label {
                text: root.title
                color: root.textColor
                font.pixelSize: 13
                font.weight: Font.Medium
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
                Layout.minimumWidth: 0
            }

            Label {
                text: root.detail
                visible: root.detail.length > 0
                color: root.mutedTextColor
                font.pixelSize: 12
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
                Layout.minimumWidth: 0
            }
        }

        Switch {
            id: switchControl

            checked: root.checked
            hoverEnabled: true
            leftPadding: 0
            rightPadding: 0
            Layout.minimumWidth: 46
            Layout.preferredWidth: 46
            Layout.maximumWidth: 46
            Accessible.role: Accessible.CheckBox
            Accessible.name: root.title
            Accessible.description: root.detail
            onToggled: root.toggled(switchControl.checked)

            indicator: Rectangle {
                implicitWidth: 46
                implicitHeight: 26
                x: 0
                y: parent.height / 2 - height / 2
                radius: height / 2
                color: switchControl.checked
                    ? root.accentColor
                    : ((switchControl.hovered || root.hovered)
                        ? Qt.lighter(root.trackColor, 1.05)
                        : root.trackColor)
                border.color: switchControl.activeFocus ? root.focusColor : root.borderColor
                border.width: switchControl.activeFocus ? 2 : 1

                Behavior on color {
                    ColorAnimation {
                        duration: root.reduceMotion ? 0 : 120
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
                            duration: root.reduceMotion ? 0 : 140
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
}
