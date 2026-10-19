SUMMARY = "GNOME defaults for the 3.5 inch 320x480 touch screen"
DESCRIPTION = "gschema override: 80% text, so GNOME's dialogs fit on the screen; the dash favourites \
(Camera, GNOME Web, Files, Text Editor, Console); the screen never blanks or locks; GNOME Web's home page. \
Session environment: GTK 4 apps draw in software (unverified, see 90-touch-display-environment.conf)."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = " \
    file://91_touch-display.gschema.override \
    file://90-touch-display-environment.conf \
"
S = "${WORKDIR}"

# gsettings compiles the override into the schema cache on the image.
inherit allarch gsettings

do_install() {
    install -d ${D}${datadir}/glib-2.0/schemas
    install -m 0644 ${WORKDIR}/91_touch-display.gschema.override ${D}${datadir}/glib-2.0/schemas/

    # Read by the user's systemd manager, which starts GNOME Shell and the apps.
    install -d ${D}${sysconfdir}/environment.d
    install -m 0644 ${WORKDIR}/90-touch-display-environment.conf ${D}${sysconfdir}/environment.d/90-touch-display.conf
}
