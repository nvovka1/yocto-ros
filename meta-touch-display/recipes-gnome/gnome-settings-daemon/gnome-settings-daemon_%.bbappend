# Not needed on this board, and each pulls in a lot:
#   cups      printing
#   smartcard smart card login
#   wwan      mobile broadband (needs ModemManager); there is no modem
# "nm" stays: gnome-settings-daemon refuses to build on Linux without it ("NetworkManager support is not optional").
# It only links the libnm client library; the NetworkManager service itself is not installed (Wi-Fi stays on
# wpa_supplicant + networkd, see the gnome-shell bbappend).
PACKAGECONFIG:remove = "cups smartcard"
EXTRA_OEMESON:append = " -Dwwan=false"
