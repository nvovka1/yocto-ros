# gnome-shell needs evolution-data-server for its calendar, but not online accounts: "oauth" builds against WebKitGTK
# (one of the longest builds there is) and "goa" pulls in gnome-online-accounts, which needs WebKitGTK too.
PACKAGECONFIG:remove = "goa oauth"
