SUMMARY = "Camera: the object detector's live view in a GNOME window"
DESCRIPTION = "Shows the camera frame with the detection boxes from object_detector's MJPEG live view \
(http://127.0.0.1:8080/stream) in a GTK 4 window. Reconnects by itself when the detector restarts. \
It is pinned in GNOME's dash by touch-display-settings."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=714456307d8622c584e969bccb77dfdf"

# Source lives in this repository (apps/detection_camera), the same code that is tested on the PC.
FILESEXTRAPATHS:prepend := "${YOCTO_ROS_REPOSITORY_ROOT}/apps:"
SRC_URI = "file://detection_camera"
S = "${WORKDIR}/detection_camera"

# gtk-icon-cache updates the icon cache on the image for the app's icon.
GTKIC_VERSION = "4"
inherit allarch python3-dir gtk-icon-cache

APPLICATION_ID = "io.github.nvovka1.DetectionCamera"

do_install() {
    install -d ${D}${PYTHON_SITEPACKAGES_DIR}/detection_camera
    install -m 0644 ${S}/detection_camera/*.py ${D}${PYTHON_SITEPACKAGES_DIR}/detection_camera/

    install -d ${D}${bindir}
    install -m 0755 ${S}/detection-camera ${D}${bindir}/detection-camera

    install -d ${D}${datadir}/applications
    install -m 0644 ${S}/data/${APPLICATION_ID}.desktop ${D}${datadir}/applications/

    install -d ${D}${datadir}/icons/hicolor/scalable/apps
    install -m 0644 ${S}/data/${APPLICATION_ID}.svg ${D}${datadir}/icons/hicolor/scalable/apps/
}

FILES:${PN} += " \
    ${PYTHON_SITEPACKAGES_DIR}/detection_camera \
    ${datadir}/applications \
"

# python3-netclient: http/urllib; gtk4 + PyGObject for the window; librsvg draws the SVG icon.
RDEPENDS:${PN} = " \
    python3-core \
    python3-netclient \
    python3-pygobject \
    gtk4 \
    librsvg-gtk \
"
