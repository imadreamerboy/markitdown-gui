import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root

    property string label: ""
    property string value: ""
    property color backgroundColor: "#F8FAFC"
    property color borderColor: "#D8E1E8"
    property color textColor: "#18212B"
    property color mutedTextColor: "#647283"

    implicitWidth: Math.max(96, content.implicitWidth + 20)
    implicitHeight: 48
    radius: 8
    color: backgroundColor
    border.color: borderColor
    border.width: 1

    ColumnLayout {
        id: content
        anchors.fill: parent
        anchors.margins: 10
        spacing: 2

        Label {
            text: root.label
            color: root.mutedTextColor
            font.pixelSize: 10
            font.weight: Font.Medium
            elide: Text.ElideRight
            Layout.fillWidth: true
        }

        Label {
            text: root.value
            color: root.textColor
            font.pixelSize: 14
            font.weight: Font.DemiBold
            elide: Text.ElideRight
            Layout.fillWidth: true
        }
    }
}
