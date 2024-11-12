#!/bin/bash

# Stop VNC server if running
pkill Xtigervnc || true

# Clean up only specific X server files
rm -f /tmp/.X1-lock /tmp/.X11-unix/X1 || true

# Start dbus daemon using sudo
sudo dbus-daemon --system --nofork --nopidfile &

# Wait for DBus to start properly
sleep 2

# Check if DBus is running
if ! pgrep -x "dbus-daemon" > /dev/null; then
    echo "Error: dbus-daemon failed to start!"
    exit 1
fi

# Initialize Xauthority
touch ~/.Xauthority
chmod 600 ~/.Xauthority

# Validate and set VNC password
if [ ! -z "$VNC_PASSWORD" ]; then
    if [ ${#VNC_PASSWORD} -lt 6 ]; then
        echo "Error: VNC password must be at least 6 characters long"
        exit 1
    fi
    echo "$VNC_PASSWORD" | vncpasswd -f > ~/.vnc/passwd
    chmod 600 ~/.vnc/passwd
fi

# Validate and set code-server password
if [ ! -z "$PASSWORD" ]; then
    if [ ${#PASSWORD} -lt 6 ]; then
        echo "Error: Code-server password must be at least 6 characters long"
        exit 1
    fi
    mkdir -p ~/.config/code-server
    echo "bind-addr: 0.0.0.0:8443
auth: password
password: $PASSWORD
cert: false" > ~/.config/code-server/config.yaml
    chmod 600 ~/.config/code-server/config.yaml
fi

# Start VNC server
if ! vncserver :1 -geometry 1280x800 -depth 24 -localhost no -xstartup ~/.vnc/xstartup; then
    echo "Error: VNC server failed to start!"
    exit 1
fi

# Start supervisord
exec supervisord -n -c /etc/supervisor/conf.d/supervisord.conf