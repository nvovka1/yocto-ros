SUMMARY = "NetworkManager runs Wi-Fi, pre-configured with WIFI_SSID / WIFI_PASSWORD from local.conf"
DESCRIPTION = "Hands wlan0 to NetworkManager (so networks can be picked in GNOME's Wi-Fi menu) and gives it the \
network from local.conf, so the board is reachable over SSH on first boot, like with meta-rpi-base's wifi-config \
(which this image leaves out: two managers on wlan0 would fight). The wired port stays with systemd-networkd. \
Also gives systemd-timesyncd a time server, so the clock is set without systemd-networkd running Wi-Fi."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = " \
    file://90-touch-display.conf \
    file://50-networkmanager-pi.rules \
    file://90-touch-display-timesyncd.conf \
    file://90-touch-display-wired.conf \
"
S = "${WORKDIR}"

# Set these in build/conf/local.conf only (same variables as wifi-config). Never commit them.
WIFI_SSID ??= ""
WIFI_PASSWORD ??= ""

# Same as `wpa_passphrase`: the 256-bit key derived from password + SSID, so the plain password is not stored on the Pi.
# NetworkManager accepts it as psk= (64 hex digits).
def wifi_psk(d):
    import hashlib
    ssid = d.getVar('WIFI_SSID')
    password = d.getVar('WIFI_PASSWORD')
    if not ssid:
        return ''
    if not 8 <= len(password) <= 63:
        bb.fatal('WIFI_PASSWORD must be 8 to 63 characters (WPA2 passphrase)')
    return hashlib.pbkdf2_hmac('sha1', password.encode(), ssid.encode(), 4096, 32).hex()

# A stable connection id: the same SSID gives the same UUID in every build.
def wifi_connection_uuid(d):
    import uuid
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, 'wifi.' + (d.getVar('WIFI_SSID') or '')))

WIFI_PSK = "${@wifi_psk(d)}"
WIFI_CONNECTION_UUID = "${@wifi_connection_uuid(d)}"
# Task signatures (stamps, sstate siginfo, bitbake-dumpsig) record only the derived key, not the plain password:
# WIFI_PSK's signature value is its expanded value, so bitbake does not follow it into wifi_psk() and WIFI_PASSWORD.
# A new password still changes the key and rebuilds. (do_install[vardepsexclude] does not do this: the chain
# do_install -> WIFI_PSK -> WIFI_PASSWORD is still followed.)
WIFI_PSK[vardepvalue] = "${WIFI_PSK}"

# polkit owns its rules folder (polkitd, mode 0700); create it the same way so the packages don't conflict.
DEPENDS = "polkit"

# Note: no heredoc here. BitBake ends a shell function at the first line that starts with "}".
do_install() {
    install -d ${D}${sysconfdir}/NetworkManager/conf.d
    install -m 0644 ${WORKDIR}/90-touch-display.conf ${D}${sysconfdir}/NetworkManager/conf.d/

    install -d -m 0700 ${D}${datadir}/polkit-1/rules.d
    chown polkitd:root ${D}${datadir}/polkit-1/rules.d
    install -m 0644 ${WORKDIR}/50-networkmanager-pi.rules ${D}${datadir}/polkit-1/rules.d/

    # Clock: systemd-timesyncd needs a time server and an "online" verdict from systemd-networkd, which only sees the
    # wired port now. Both used to come with systemd-networkd running Wi-Fi.
    install -d ${D}${sysconfdir}/systemd/timesyncd.conf.d
    install -m 0644 ${WORKDIR}/90-touch-display-timesyncd.conf ${D}${sysconfdir}/systemd/timesyncd.conf.d/90-touch-display.conf
    install -d ${D}${sysconfdir}/systemd/network/80-wired.network.d
    install -m 0644 ${WORKDIR}/90-touch-display-wired.conf ${D}${sysconfdir}/systemd/network/80-wired.network.d/90-touch-display.conf

    if [ -z "${WIFI_SSID}" ]; then
        bbnote "WIFI_SSID is not set: no Wi-Fi network pre-configured, pick one on the screen"
        return
    fi
    # Same mode as networkmanager-daemon's own copy of this directory (else the packages conflict); the file is 0600.
    install -d ${D}${sysconfdir}/NetworkManager/system-connections
    printf '%s\n' \
        '[connection]' \
        'id=${WIFI_SSID}' \
        'uuid=${WIFI_CONNECTION_UUID}' \
        'type=wifi' \
        'interface-name=wlan0' \
        'autoconnect=true' \
        '' \
        '[wifi]' \
        'mode=infrastructure' \
        'ssid=${WIFI_SSID}' \
        '' \
        '[wifi-security]' \
        'key-mgmt=wpa-psk' \
        'psk=${WIFI_PSK}' \
        '' \
        '[ipv4]' \
        'method=auto' \
        '' \
        '[ipv6]' \
        'method=auto' \
        > ${D}${sysconfdir}/NetworkManager/system-connections/wifi.nmconnection
    chmod 0600 ${D}${sysconfdir}/NetworkManager/system-connections/wifi.nmconnection
}

FILES:${PN} += "${datadir}/polkit-1/rules.d"
RDEPENDS:${PN} = "networkmanager-daemon networkmanager-wifi polkit"
