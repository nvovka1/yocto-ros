# Let the firmware detect the CSI camera (IMX219, ...) on either camera port and load its overlay.
RPI_EXTRA_CONFIG:append = "\n# Camera: load the overlay for the detected sensor\ncamera_auto_detect=1\n"
