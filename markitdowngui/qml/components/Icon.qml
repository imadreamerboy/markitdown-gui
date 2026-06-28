import QtQuick

Item {
    id: root

    property string name: ""
    property color color: "#18212B"
    property int size: 16
    readonly property bool useLightVariant: (color.r * 0.299 + color.g * 0.587 + color.b * 0.114) > 0.55

    width: size
    height: size
    implicitWidth: size
    implicitHeight: size

    Image {
        anchors.fill: parent
        source: root.name.length > 0
            ? Qt.resolvedUrl("../../resources/icons/" + (root.useLightVariant ? "light/" : "") + root.name + ".svg")
            : ""
        fillMode: Image.PreserveAspectFit
        smooth: true
        mipmap: true
    }
}
