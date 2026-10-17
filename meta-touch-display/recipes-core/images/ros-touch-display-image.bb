# Start from the object detection image (meta-object-detection, without the buzzer) and add a GNOME desktop on the
# 3.5" touch screen, with the Camera app that shows the detector's live view.
require recipes-core/images/ros-detection-image.bb

SUMMARY = "Raspberry Pi 5 ROS 2 image with object detection, GNOME on the 3.5 inch touch screen and the Camera app"
DESCRIPTION = "${SUMMARY}"

# A lean GNOME: the shell, its session and settings daemon, GDM for the automatic login, icons and fonts.
# Left out on purpose: gnome-control-center (pulls in printing and Samba, unusable at 320x480; see the gnome-shell
# bbappend). Apps: gnome-console (terminal, for when a keyboard is plugged in), epiphany (GNOME Web, the browser; it
# brings the WebKitGTK engine, the longest part of the build), nautilus (Files) and gnome-text-editor (notes).
GNOME_DESKTOP_PACKAGES = " \
    gdm \
    gnome-session \
    gnome-shell \
    gnome-settings-daemon \
    gsettings-desktop-schemas \
    adwaita-icon-theme \
    adwaita-icon-theme-cursors \
    gnome-backgrounds \
    cantarell-fonts \
    ttf-dejavu-sans \
    gnome-console \
    epiphany \
    nautilus \
    gnome-text-editor \
    ${GNOME_RUNTIME_PACKAGES} \
"

# Needed at run time but not pulled in automatically (GNOME Shell loads some libraries through GObject introspection,
# which BitBake cannot see as dependencies; found on the board):
#   xwayland          GDM only offers a Wayland session when /usr/bin/Xwayland exists; without it, it falls back to
#                     X11 (not installed) and restarts forever
#   xkeyboard-config  keyboard layouts; without them gnome-shell crashes at start
#   ibus              GNOME Shell imports IBus at start (and starts ibus-daemon)
#   iso-codes         language and country names
#   libnma            GNOME Shell requires its NMA4 library at start when built with NetworkManager support
#   tzdata            time zones (Europe/Kyiv, tzdata bbappend); without it the clock shows UTC
GNOME_RUNTIME_PACKAGES = " \
    xwayland \
    xkeyboard-config \
    ibus \
    iso-codes \
    libnma \
    tzdata \
"

# Wi-Fi: NetworkManager manages wlan0 (GNOME's Wi-Fi menu needs it), pre-configured with WIFI_SSID / WIFI_PASSWORD
# from local.conf. meta-rpi-base's wifi-config (wpa_supplicant@wlan0 + systemd-networkd) would fight it over wlan0,
# so it is left out here. The wired port stays with systemd-networkd.
NETWORK_PACKAGES = " \
    networkmanager-daemon \
    networkmanager-wifi \
    networkmanager-nmcli \
    networkmanager-wifi-config \
"
IMAGE_INSTALL:remove = "wifi-config"

# detection-camera: the Camera app (apps/detection_camera), pinned in GNOME's dash.
# touchscreen-calibration: lets the pen reach the edges of the screen (udev rule with a libinput calibration matrix).
# touch-display-settings: GNOME at 80% text, so its dialogs fit the 480-pixel height.
# zram: compressed swap in RAM. GNOME (~0.5 GB) plus the detector (~0.45 GB) on a 2 GB Pi with no swap otherwise.
# evtest: shows raw touch events over SSH, for checking the touch calibration.
IMAGE_INSTALL:append = " \
    ${GNOME_DESKTOP_PACKAGES} \
    ${NETWORK_PACKAGES} \
    detection-camera \
    touchscreen-calibration \
    touch-display-settings \
    zram \
    evtest \
"

# Boot into the desktop (GDM) instead of the text console.
SYSTEMD_DEFAULT_TARGET = "graphical.target"

# The user GDM logs in automatically (gdm custom.conf). GNOME doesn't run as root. Empty password, so nothing ever asks
# for one: development image only, like root's empty password.
inherit extrausers
EXTRA_USERS_PARAMS = " \
    useradd -m -s /bin/sh pi; \
    usermod -p '' pi; \
"

# GNOME needs far more room than the ~860 MB root partition of the other images: leave 2 GiB free (value in KiB).
# Free space compresses away in the .wic.xz.
IMAGE_ROOTFS_EXTRA_SPACE = "2097152"
