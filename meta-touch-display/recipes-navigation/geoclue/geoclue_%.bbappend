# Location from mobile modems needs ModemManager; this board has no modem.
PACKAGECONFIG:remove = "3g modem-gps cdma"
