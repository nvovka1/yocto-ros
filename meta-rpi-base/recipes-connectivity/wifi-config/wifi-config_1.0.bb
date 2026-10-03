SUMMARY = "Wi-Fi client configuration for wlan0, from WIFI_SSID / WIFI_PASSWORD in local.conf"
DESCRIPTION = "Does on the build machine what Part 1 step 9.2 did by hand on the Pi: \
writes wpa_supplicant-wlan0.conf and 25-wlan.network and enables wpa_supplicant@wlan0. \
With WIFI_SSID empty the package is empty and the image has no Wi-Fi credentials."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

# Set these in build/conf/local.conf only. Never commit them, and never put them in an image you publish.
WIFI_SSID ??= ""
WIFI_PASSWORD ??= ""
WIFI_COUNTRY ??= "UA"

# Same as `wpa_passphrase`: the 256-bit key derived from password + SSID, so the plain password is not stored on the Pi.
def wifi_psk(d):
    import hashlib
    ssid = d.getVar('WIFI_SSID')
    password = d.getVar('WIFI_PASSWORD')
    if not ssid:
        return ''
    if not 8 <= len(password) <= 63:
        bb.fatal('WIFI_PASSWORD must be 8 to 63 characters (WPA2 passphrase)')
    return hashlib.pbkdf2_hmac('sha1', password.encode(), ssid.encode(), 4096, 32).hex()

WIFI_PSK = "${@wifi_psk(d)}"
# Only the derived key goes into task signatures, not the plain password.
do_install[vardepsexclude] += "WIFI_PASSWORD"

inherit allarch

S = "${WORKDIR}"

# Note: no heredoc here. BitBake ends a shell function at the first line that starts with "}",
# so the "}" closing network={...} must not be at column 0 of the recipe.
do_install() {
    if [ -z "${WIFI_SSID}" ]; then
        bbnote "WIFI_SSID is not set: building without Wi-Fi credentials"
        return
    fi

    install -d -m 0755 ${D}${sysconfdir}/wpa_supplicant
    printf '%s\n' \
        'ctrl_interface=/var/run/wpa_supplicant' \
        'country=${WIFI_COUNTRY}' \
        '' \
        'network={' \
        '    ssid="${WIFI_SSID}"' \
        '    psk=${WIFI_PSK}' \
        '}' \
        > ${D}${sysconfdir}/wpa_supplicant/wpa_supplicant-wlan0.conf
    chmod 0600 ${D}${sysconfdir}/wpa_supplicant/wpa_supplicant-wlan0.conf

    install -d -m 0755 ${D}${sysconfdir}/systemd/network
    printf '[Match]\nName=wlan0\n\n[Network]\nDHCP=yes\n' > ${D}${sysconfdir}/systemd/network/25-wlan.network

    # What `systemctl enable wpa_supplicant@wlan0` does: a symlink in multi-user.target.wants.
    # (The wpa_supplicant@.service template itself comes from the wpa-supplicant package.)
    install -d -m 0755 ${D}${sysconfdir}/systemd/system/multi-user.target.wants
    ln -sf ${systemd_system_unitdir}/wpa_supplicant@.service \
        ${D}${sysconfdir}/systemd/system/multi-user.target.wants/wpa_supplicant@wlan0.service
}

FILES:${PN} = "${sysconfdir}"
ALLOW_EMPTY:${PN} = "1"
RDEPENDS:${PN} = "wpa-supplicant"
