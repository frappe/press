FROM debian:12-slim

ENV DEBIAN_FRONTEND=noninteractive

# Install required packages
RUN apt-get update && apt-get install -y \
    xfce4 \
    xfce4-terminal \
    tigervnc-standalone-server \
    tigervnc-common \
    novnc \
    websockify \
    supervisor \
    curl \
    wget \
    git \
    net-tools \
    procps \
    xauth \
    dbus-x11 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install code-server
RUN curl -fsSL https://code-server.dev/install.sh | sh

# Create necessary directories and files
RUN mkdir -p /root/.vnc /var/log/supervisor && \
    touch /root/.Xauthority

# Set up VNC configuration
COPY xstartup /root/.vnc/xstartup
RUN chmod +x /root/.vnc/xstartup

# Set VNC password
RUN echo "password" | vncpasswd -f > /root/.vnc/passwd && \
    chmod 600 /root/.vnc/passwd

# Copy supervisor configuration
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Create cleanup script
COPY cleanup.sh /cleanup.sh
RUN chmod +x /cleanup.sh

# Expose ports
EXPOSE 8080 8443 5901

CMD ["/usr/bin/supervisord", "-n", "-c", "/etc/supervisor/conf.d/supervisord.conf"]