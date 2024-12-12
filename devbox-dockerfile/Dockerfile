FROM debian:12-slim

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=en_US.UTF-8 \
    LC_ALL=C.UTF-8 \
    PASSWORD=password \
    VNC_PASSWORD=password

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
    sudo \
    x11-xserver-utils \
    xfonts-base \
    pm-utils \
    pulseaudio \
    dbus-x11 \
    policykit-1-gnome \
    python3-venv \
    cron \
    locales \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && locale-gen en_US.UTF-8

# Configure MariaDB root password
RUN service mariadb start && \
    mysqladmin -u root password 'frappe' && \
    mysql -u root -pfrappe -e "GRANT ALL PRIVILEGES ON *.* TO 'root'@'localhost' IDENTIFIED BY 'frappe' WITH GRANT OPTION; FLUSH PRIVILEGES;"

# Add frappe user and add to sudoers
RUN useradd -m -s /bin/bash frappe && \
    echo "frappe:password" | chpasswd && \
    usermod -aG sudo frappe && \
    echo "frappe ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Create necessary directories and set permissions
RUN mkdir -p /home/frappe/.config /home/frappe/.vnc /home/frappe/.local && \
    mkdir -p /var/log/supervisor && \
    mkdir -p /run/user/1000 && \
    mkdir -p /var/run/dbus && \
    mkdir -p /var/lib/dbus && \
    touch /home/frappe/.Xauthority && \
    dbus-uuidgen > /var/lib/dbus/machine-id && \
    chown -R frappe:frappe /home/frappe && \
    chown -R frappe:frappe /var/log/supervisor && \
    chown -R frappe:frappe /run/user/1000 && \
    chmod -R 755 /home/frappe/.config && \
    chmod -R 755 /home/frappe/.local && \
    chmod 700 /run/user/1000 && \
    chmod 755 /var/run/dbus && \
    chmod -R 755 /var/lib/dbus

# Set up VNC configuration
RUN mkdir -p /home/frappe/.vnc && \
    echo "#!/bin/bash\n\
    export XDG_SESSION_TYPE=x11\n\
    export DBUS_SESSION_BUS_ADDRESS=unix:path=/run/dbus/system_bus_socket\n\
    export XDG_RUNTIME_DIR=/run/user/1000\n\
    unset SESSION_MANAGER\n\
    unset DBUS_SESSION_BUS_ADDRESS\n\
    exec dbus-launch --exit-with-session startxfce4" > /home/frappe/.vnc/xstartup && \
    chmod +x /home/frappe/.vnc/xstartup && \
    chown -R frappe:frappe /home/frappe/.vnc

# Install bench CLI
RUN pip3 install frappe-bench --break-system-packages

# Switch to frappe user for remaining operations
USER frappe
WORKDIR /home/frappe
ENV PATH="/home/frappe/.local/bin:$PATH"

# Install NVM, Node.js, and Yarn
RUN curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash && \
    export NVM_DIR="/home/frappe/.nvm" && \
    [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh" && \
    [ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion" && \
    echo 'export NVM_DIR="$HOME/.nvm"' >> ~/.bashrc && \
    echo '[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"' >> ~/.bashrc && \
    echo '[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"' >> ~/.bashrc && \
    . ~/.bashrc && \
    nvm install 18 && \
    nvm use 18 && \
    nvm alias default 18 && \
    npm install -g yarn

# Install code-server
RUN curl -fsSL https://code-server.dev/install.sh | sh

# Create code-server config directory and default config
RUN mkdir -p /home/frappe/.config/code-server && \
    echo "bind-addr: 0.0.0.0:8443\n\
    auth: password\n\
    cert: false" > /home/frappe/.config/code-server/config.yaml

# Copy supervisor configuration and startup script
COPY --chown=frappe:frappe supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY --chown=frappe:frappe start.sh /home/frappe/start.sh
RUN chmod +x /home/frappe/start.sh

# Set environment variables
ENV NVM_DIR=/home/frappe/.nvm \
    PATH="/home/frappe/.nvm/versions/node/v18/bin:/home/frappe/.local/bin:${PATH}" \
    XDG_RUNTIME_DIR=/run/user/1000 \
    DBUS_SESSION_BUS_ADDRESS=unix:path=/run/dbus/system_bus_socket

# Expose ports
EXPOSE 6969 8443 5901

# Set the default command
CMD ["/home/frappe/start.sh"]