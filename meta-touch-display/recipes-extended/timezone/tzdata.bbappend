# The board's clock syncs over the internet (systemd-timesyncd) but showed UTC: set the local time zone.
# Applies to every image in the build directory that installs tzdata (only the touch display image does).
DEFAULT_TIMEZONE = "Europe/Kyiv"
