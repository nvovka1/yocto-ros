# Camera: Raspberry Pi Camera Module v2 (Sony IMX219). meta-raspberrypi then writes dtoverlay=imx219 to
# config.txt, which on a Pi 5 is the CAM/DISP 1 connector. Loading the overlay explicitly is more reliable
# than camera_auto_detect. For the CAM/DISP 0 connector use dtoverlay=imx219,cam0 instead.
RASPBERRYPI_CAMERA_V2 = "1"
