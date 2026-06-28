import QtQuick
import QtQuick.Controls

Button {
    id: control

    property bool primary: false
    property bool subtle: false
    property color accentColor: "#138A87"
    property color surfaceColor: "#FFFFFF"
    property color borderColor: "#D8E1E8"
    property color textColor: "#18212B"
    property color primaryTextColor: "#FFFFFF"
    property color disabledTextColor: "#8A96A3"
    property string iconName: ""
    property int iconSize: 16
    property int iconSpacing: 7

    implicitHeight: 36
    leftPadding: 14
    rightPadding: 14
    topPadding: 8
    bottomPadding: 8

    contentItem: Item {
        implicitWidth: contentRow.implicitWidth
        implicitHeight: Math.max(contentRow.implicitHeight, control.iconSize)

        Row {
            id: contentRow
            anchors.centerIn: parent
            spacing: control.iconName.length > 0 ? control.iconSpacing : 0

            Icon {
                visible: control.iconName.length > 0
                name: control.iconName
                size: control.iconSize
                color: control.enabled
                    ? (control.primary ? control.primaryTextColor : control.textColor)
                    : control.disabledTextColor
                anchors.verticalCenter: parent.verticalCenter
            }

            Text {
                text: control.text
                color: control.enabled
                    ? (control.primary ? control.primaryTextColor : control.textColor)
                    : control.disabledTextColor
                font.pixelSize: 13
                font.weight: control.primary ? Font.DemiBold : Font.Medium
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                elide: Text.ElideRight
                anchors.verticalCenter: parent.verticalCenter
            }
        }
    }

    background: Rectangle {
        radius: 8
        color: {
            if (!control.enabled)
                return control.subtle ? "transparent" : control.surfaceColor
            if (control.primary)
                return control.down ? Qt.darker(control.accentColor, 1.12) : control.accentColor
            if (control.subtle)
                return control.hovered ? Qt.rgba(0.5, 0.6, 0.7, 0.12) : "transparent"
            return control.hovered ? Qt.rgba(0.5, 0.6, 0.7, 0.14) : control.surfaceColor
        }
        border.color: control.primary || control.subtle ? "transparent" : control.borderColor
        border.width: 1
    }
}

