#!/bin/bash

# Stop VNC server if running
pkill Xtigervnc || true

# Clean up only specific X server files
rm -f /tmp/.X1-lock /tmp/.X11-unix/X1 || true

# Start dbus daemon using sudo
sudo dbus-daemon --system --nofork --nopidfile &

# Initialize Xauthority
touch ~/.Xauthority
chmod 600 ~/.Xauthority

# Start VNC server
vncserver :1 -geometry 1280x800 -depth 24 -localhost no -xstartup ~/.vnc/xstartup

# Start supervisord
exec supervisord -n -c /etc/supervisor/conf.d/supervisord.conf