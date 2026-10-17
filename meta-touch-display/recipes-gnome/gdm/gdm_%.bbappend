# Automatic login: replace GDM's default custom.conf with ours.
FILESEXTRAPATHS:prepend := "${THISDIR}/files:"
SRC_URI += "file://custom.conf"

do_install:append() {
    install -m 0644 ${WORKDIR}/custom.conf ${D}${sysconfdir}/gdm/custom.conf
}
