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
    firefox-esr \
    mariadb-server \
    mariadb-client \
    python3-dev \
    python3-pip \
    redis-server \
    xvfb \
    libfontconfig \
    wkhtmltopdf \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install code-server
RUN curl -fsSL https://code-server.dev/install.sh | sh

# Install NVM, Node.js, and Yarn
RUN curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.38.0/install.sh | bash && \
    export NVM_DIR="/root/.nvm" && \
    [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh" && \
    [ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion" && \
    nvm install 18 && \
    npm install -g yarn

# Install Bench CLI
RUN pip3 install frappe-bench --break-system-packages

# Create necessary directories and files
RUN mkdir -p /root/.vnc /var/log/supervisor && \
    touch /root/.Xauthority

# Set up VNC password and xstartup
RUN echo "password" | vncpasswd -f > /root/.vnc/passwd && \
    chmod 600 /root/.vnc/passwd

# Create xstartup file
RUN echo '#!/bin/bash\nunset SESSION_MANAGER\nunset DBUS_SESSION_BUS_ADDRESS\nexec startxfce4' > /root/.vnc/xstartup && \
    chmod +x /root/.vnc/xstartup

# Copy supervisor configuration
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Expose ports
EXPOSE 8080 8443 5901

# Create startup script
RUN echo '#!/bin/bash\nrm -rf /tmp/.X* /tmp/.x* /tmp/ssh*\nexec /usr/bin/supervisord -n -c /etc/supervisor/conf.d/supervisord.conf' > /start.sh && \
    chmod +x /start.sh

# Add NVM to PATH
ENV NVM_DIR=/root/.nvm
ENV PATH="/root/.nvm/versions/node/v18/bin:${PATH}"

CMD ["/start.sh"]