# GNOME Settings (gnome-control-center) is unusable at 320x480 and alone pulls in Samba, WebKitGTK, NetworkManager
# and printing, hours of extra build. The shell runs without it; only its Settings shortcut does nothing.
# (The "nm" option stays on: NetworkManager runs Wi-Fi on this image, see networkmanager-wifi-config, and gives the
# shell its Wi-Fi menu.)
RDEPENDS:${PN}:remove = "gnome-control-center"
