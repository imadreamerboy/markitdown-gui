import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root

    property string title: ""
    property string subtitle: ""
    property color surfaceColor: "#FFFFFF"
    property color borderColor: "#D8E1E8"
    property color textColor: "#18212B"
    property color mutedTextColor: "#647283"
    default property alias content: body.data

    implicitWidth: 360
    implicitHeight: layout.implicitHeight

    Rectangle {
        anchors.fill: parent
        color: root.surfaceColor
        radius: 0
    }

    Rectangle {
        width: 1
        color: root.borderColor
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
    }

    ColumnLayout {
        id: layout
        anchors.fill: parent
        anchors.leftMargin: 18
        anchors.rightMargin: 2
        anchors.topMargin: 4
        anchors.bottomMargin: 2
        spacing: 14

        ColumnLayout {
            visible: root.title.length > 0 || root.subtitle.length > 0
            spacing: 4
            Layout.fillWidth: true

            Label {
                text: root.title
                visible: root.title.length > 0
                color: root.textColor
                font.pixelSize: 15
                font.weight: Font.DemiBold
                elide: Text.ElideRight
                Layout.fillWidth: true
            }

            Label {
                text: root.subtitle
                visible: root.subtitle.length > 0
                color: root.mutedTextColor
                font.pixelSize: 12
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }
        }

        ColumnLayout {
            id: body
            spacing: 12
            Layout.fillWidth: true
            Layout.fillHeight: true
        }
    }
}
