require ${COREBASE}/meta/recipes-core/images/core-image-minimal.bb

SUMMARY = "Raspberry Pi 5 base image with SSH, Wi-Fi, Python and tools"
DESCRIPTION = "${SUMMARY}"
LICENSE = "MIT"

# SSH server; root may log in with an empty password (development only!)
IMAGE_FEATURES += "ssh-server-openssh allow-empty-password allow-root-login empty-root-password"

# Extra packages
IMAGE_INSTALL:append = " \
    kernel-modules \
    avahi-daemon \
    python3 \
    python3-modules \
    python3-pip \
    python3-pyyaml \
    i2c-tools \
    nano \
    htop \
"

# Wi-Fi: firmware for the Pi 5 Wi-Fi chip + wpa_supplicant
# (needs LICENSE_FLAGS_ACCEPTED += "synaptics-killswitch" in local.conf)
IMAGE_INSTALL:append = " \
    wpa-supplicant \
    linux-firmware-rpidistro-bcm43455 \
    linux-firmware-rpidistro-bcm43456 \
    wireless-regdb-static \
"

# Wi-Fi network: joins WIFI_SSID at boot. Empty (no credentials) unless WIFI_SSID / WIFI_PASSWORD are set in local.conf.
IMAGE_INSTALL:append = " wifi-config"
