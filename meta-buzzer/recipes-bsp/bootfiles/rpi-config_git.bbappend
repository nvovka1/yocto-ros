# Route GPIO 12 (physical pin 32) and GPIO 13 (pin 33) to the Raspberry Pi 5 hardware PWM
# (RP1 PWM0, channels 0 and 1). The buzzer is on GPIO 12; GPIO 13 is free for a second one.
RPI_EXTRA_CONFIG:append = "\n# Buzzer: hardware PWM on GPIO 12 and 13\ndtoverlay=pwm-2chan,pin=12,func=4,pin2=13,func2=4\n"
