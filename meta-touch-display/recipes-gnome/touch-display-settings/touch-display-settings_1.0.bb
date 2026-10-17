SUMMARY = "GNOME defaults for the 3.5 inch 320x480 touch screen"
DESCRIPTION = "gschema override: 80% text, so GNOME's dialogs fit on the screen, and the dash favourites \
(Camera, GNOME Web, Files, Text Editor, Console)."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = "file://91_touch-display.gschema.override"
S = "${WORKDIR}"

# gsettings compiles the override into the schema cache on the image.
inherit allarch gsettings

do_install() {
    install -d ${D}${datadir}/glib-2.0/schemas
    install -m 0644 ${WORKDIR}/91_touch-display.gschema.override ${D}${datadir}/glib-2.0/schemas/
}
