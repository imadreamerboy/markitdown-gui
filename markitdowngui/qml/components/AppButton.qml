import QtQuick
import QtQuick.Controls

Button {
    id: control

    property bool primary: false
    property bool subtle: false
    property color accentColor: "#88C0D0"
    property color surfaceColor: "#FFFFFF"
    property color borderColor: "#D8E1E8"
    property color focusColor: primary ? textColor : accentColor
    property color textColor: "#18212B"
    property color primaryTextColor: "#FFFFFF"
    property color disabledTextColor: "#8A96A3"
    property color disabledPrimaryColor: Qt.rgba(accentColor.r, accentColor.g, accentColor.b, 0.16)
    property string iconName: ""
    property int iconSize: 16
    property int iconSpacing: 7
    property bool reduceMotion: ApplicationWindow.window ? ApplicationWindow.window.reduceMotion : false
    property color hoverColor: Qt.rgba(accentColor.r, accentColor.g, accentColor.b, 0.10)

    scale: control.down && control.enabled && !control.reduceMotion ? 0.98 : 1
    hoverEnabled: true
    Accessible.role: Accessible.Button
    Accessible.name: control.text

    HoverHandler {
        cursorShape: Qt.PointingHandCursor
        enabled: control.enabled
    }

    Behavior on scale {
        NumberAnimation {
            duration: control.reduceMotion ? 0 : 110
            easing.type: Easing.OutCubic
        }
    }

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
                return control.subtle
                    ? "transparent"
                    : (control.primary ? control.disabledPrimaryColor : control.surfaceColor)
            if (control.primary)
                return control.down
                    ? Qt.darker(control.accentColor, 1.12)
                    : (control.hovered ? Qt.lighter(control.accentColor, 1.06) : control.accentColor)
            if (control.subtle)
                return control.down ? Qt.darker(control.hoverColor, 1.08) : (control.hovered ? control.hoverColor : "transparent")
            return control.down ? Qt.darker(control.hoverColor, 1.08) : (control.hovered ? control.hoverColor : control.surfaceColor)
        }
        border.color: control.activeFocus && control.enabled
            ? control.focusColor
            : (control.subtle && control.hovered && control.enabled
                ? Qt.rgba(control.accentColor.r, control.accentColor.g, control.accentColor.b, 0.45)
                : (control.primary || control.subtle ? "transparent" : control.borderColor))
        border.width: control.activeFocus && control.enabled ? 2 : 1

        Behavior on color {
            ColorAnimation {
                duration: control.reduceMotion ? 0 : 110
            }
        }

        Behavior on border.color {
            ColorAnimation {
                duration: control.reduceMotion ? 0 : 110
            }
        }
    }
}
