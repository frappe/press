FROM ubuntu:22.04

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    redis-server \
    supervisor \
    python3 \
    python3-pip \
    python3-venv \
    nodejs \
    npm \
    openssh-server \
    git \
    curl \
    wget \
    vim \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create frappe user
RUN useradd -m -s /bin/bash frappe

# Create necessary directories
RUN mkdir -p /home/frappe/frappe-bench/sites \
    /home/frappe/frappe-bench/logs \
    /home/frappe/frappe-bench/config \
    /home/frappe/frappe-bench/config/ssh \
    /home/frappe/frappe-bench/env \
    /home/frappe/frappe-bench/apps

# Set ownership
RUN chown -R frappe:frappe /home/frappe

# Copy supervisord configuration
COPY supervisord.conf /etc/supervisor/supervisord.conf

# Expose ports
# Redis cache and redis queue ports
EXPOSE 11000 13000

# Switch to frappe user for remaining setup
USER frappe
WORKDIR /home/frappe/frappe-bench


# Install bench in .local bin
ENV PATH "$PATH:/home/frappe/.local/bin"
RUN wget https://bootstrap.pypa.io/get-pip.py && python3.10 get-pip.py
RUN pip install --upgrade frappe-bench=="5.25.1"
RUN pip install Jinja2~=3.0.3
RUN pip install --upgrade setuptools

RUN git config --global advice.detachedHead false

ENV PYTHONUNBUFFERED 1


# Switch back to root for final setup
USER root

# Create volume mount points
VOLUME ["/home/frappe/frappe-bench/sites", "/home/frappe/frappe-bench/logs", "/home/frappe/frappe-bench/config"]

# Start supervisord
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/supervisord.conf"]
