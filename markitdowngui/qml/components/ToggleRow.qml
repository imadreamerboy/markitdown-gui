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
    signal toggled(bool checked)

    spacing: 12

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
        checked: root.checked
        onToggled: root.toggled(checked)
    }
}

