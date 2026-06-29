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
    property int panelPadding: 16
    property int contentSpacing: 12
    property int headerSpacing: 3
    property int bodySpacing: 10
    property real borderOpacity: 1.0
    default property alias content: body.data

    implicitWidth: panel.implicitWidth
    implicitHeight: panel.implicitHeight

    Rectangle {
        id: panel
        anchors.fill: parent
        implicitWidth: layout.implicitWidth + (root.panelPadding * 2)
        implicitHeight: layout.implicitHeight + (root.panelPadding * 2)
        radius: 8
        color: root.surfaceColor
        border.color: Qt.rgba(root.borderColor.r, root.borderColor.g, root.borderColor.b, root.borderOpacity)
        border.width: 1
    }

    ColumnLayout {
        id: layout
        anchors.fill: parent
        anchors.margins: root.panelPadding
        spacing: root.contentSpacing

        ColumnLayout {
            visible: root.title.length > 0 || root.subtitle.length > 0
            spacing: root.headerSpacing
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
            spacing: root.bodySpacing
            Layout.fillWidth: true
            Layout.fillHeight: true
        }
    }
}

