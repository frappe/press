# syntax = docker/dockerfile:experimental
FROM ubuntu:20.04

{% for d in doc.dependencies %}
ENV {{ d.dependency }} {{ d.version }}
{% else %}
ENV NVM_VERSION 0.36.0
ENV NODE_VERSION 14.4.0
ENV PYTHON_VERSION 3.7
ENV WKHTMLTOPDF_VERSION 0.12.5
{% endfor %}

ENV LANG C.UTF-8
ENV DEBIAN_FRONTEND noninteractive

ENV OPENBLAS_NUM_THREADS 1
ENV MKL_NUM_THREADS 1

# Install essential packages
RUN --mount=type=cache,target=/var/cache/apt apt-get update \
  && apt-get install --yes --no-install-suggests --no-install-recommends \
  # Essentials
  build-essential \
  git \
  mariadb-client \
  libmariadb-dev \
  pv \
  ntp \
  wget \
  supervisor \
  # Dependencies for SSH access
  openssh-server \
  nano \
  vim \
  less \
  htop \
  # Dependencies for adding Python PPA
  software-properties-common \
  gnupg \
  # weasyprint dependencies
  libpango-1.0-0 \
  libharfbuzz0b \
  libpangoft2-1.0-0 \
  libpangocairo-1.0-0 \
  # wkhtmltopdf dependencies
  ca-certificates \
  fontconfig \
  libfreetype6 \
  libjpeg-turbo8 \
  libpng16-16 \
  libx11-6 \
  libxcb1 \
  libxext6 \
  libxrender1 \
  xfonts-75dpi \
  xfonts-base \
  # pycups dependencies
  gcc \
  libcups2-dev \
  python3-dev \
  # s3-attachment dependencies
  libmagic1 \
  && rm -rf /var/lib/apt/lists/* \
  `#stage-pre-essentials`

COPY --chown=root:root supervisord.conf /etc/supervisor/supervisord.conf

# Install Redis from PPA
RUN --mount=type=cache,target=/var/cache/apt add-apt-repository ppa:redislabs/redis \
  && apt-get update \
  && apt-get install --yes --no-install-suggests --no-install-recommends \
  redis-server \
  unzip \
  && rm -rf /var/lib/apt/lists/*

# Install Python from DeadSnakes PPA
RUN --mount=type=cache,target=/var/cache/apt add-apt-repository ppa:deadsnakes/ppa \
  && apt-get update \
  && apt-get install --yes --no-install-suggests --no-install-recommends \
  python${PYTHON_VERSION} \
  python3-virtualenv \
  python3-pip \
  python${PYTHON_VERSION}-dev \
  python${PYTHON_VERSION}-distutils \
  && rm -rf /var/lib/apt/lists/* \
  `#stage-pre-python`


# Install wkhtmltopdf
RUN wget https://github.com/wkhtmltopdf/wkhtmltopdf/releases/download/${WKHTMLTOPDF_VERSION}/wkhtmltox_${WKHTMLTOPDF_VERSION}-1.focal_amd64.deb \
  && dpkg -i wkhtmltox_${WKHTMLTOPDF_VERSION}-1.focal_amd64.deb \
  && rm wkhtmltox_${WKHTMLTOPDF_VERSION}-1.focal_amd64.deb \
  `#stage-pre-wkhtmltopdf`


# Install Fonts
RUN git clone --progress --depth 1 https://github.com/frappe/fonts.git /tmp/fonts \
  && rm -rf /etc/fonts && mv /tmp/fonts/etc_fonts /etc/fonts \
  && rm -rf /usr/share/fonts && mv /tmp/fonts/usr_share_fonts /usr/share/fonts \
  && rm -rf /tmp/fonts \
  && fc-cache -fv \
  `#stage-pre-fonts`


# Set max_allowed_packet to 512 MB for mysqldump
RUN echo "[mysqldump]\nmax_allowed_packet              = 512M" > /etc/mysql/conf.d/mysqldump.cnf


RUN useradd -ms /bin/bash frappe
USER frappe
WORKDIR /home/frappe


# Install Node using NVM
ENV NVM_DIR /home/frappe/.nvm
RUN wget https://raw.githubusercontent.com/nvm-sh/nvm/v${NVM_VERSION}/install.sh \
  && bash install.sh \
  && . "/home/frappe/.nvm/nvm.sh" \
  && nvm install ${NODE_VERSION} \
  && nvm use v${NODE_VERSION} \
  && nvm alias default v${NODE_VERSION} \
  && rm install.sh \
  && nvm cache clear \
  `#stage-pre-node`

ENV PATH "$PATH:/home/frappe/.nvm/versions/node/v${NODE_VERSION}/bin"

# Install Yarn
RUN --mount=type=cache,target=/home/frappe/.cache,uid=1000,gid=1000 npm install -g yarn `#stage-pre-yarn`


# Install Bench
ENV PATH "$PATH:/home/frappe/.local/bin"

RUN --mount=type=cache,target=/home/frappe/.cache,uid=1000,gid=1000 pip3 install --upgrade frappe-bench==5.2.1 `#stage-bench-bench`

RUN --mount=type=cache,target=/home/frappe/.cache,uid=1000,gid=1000 pip3 install Jinja2~=3.0.3
RUN mkdir /home/frappe/frappe-bench
WORKDIR /home/frappe/frappe-bench
RUN mkdir -p apps logs sites config/pids redis

# Install Redisearch 2.0 from precompiled binaries
COPY --chown=frappe:frappe redis /home/frappe/frappe-bench/redis

# Create virtual environment for bench
RUN virtualenv -p python${PYTHON_VERSION} env `#stage-bench-env`

COPY --chown=frappe:frappe common_site_config.json /home/frappe/frappe-bench/sites/common_site_config.json
RUN git config --global advice.detachedHead false

ENV PYTHONUNBUFFERED 1

# Install Frappe app
RUN echo '["build"]' > .bench.cmd
RUN --mount=type=cache,target=/home/frappe/.cache,uid=1000,gid=1000 /home/frappe/frappe-bench/env/bin/pip install -U pip setuptools
RUN --mount=type=cache,target=/home/frappe/.cache,uid=1000,gid=1000 --mount=type=bind,source=apps/frappe,target=/home/frappe/context/apps/frappe bench get-app /home/frappe/context/apps/frappe `#stage-apps-frappe`
RUN rm .bench.cmd

RUN --mount=type=cache,target=/home/frappe/.cache,uid=1000,gid=1000 /home/frappe/frappe-bench/env/bin/pip install pycups==2.0.1
RUN --mount=type=cache,target=/home/frappe/.cache,uid=1000,gid=1000 /home/frappe/frappe-bench/env/bin/pip install "MarkupSafe<2.1.0"

# Install other apps
{% for app in doc.apps %}
{% if app.app != "frappe" %}

RUN --mount=type=cache,target=/home/frappe/.cache,uid=1000,gid=1000 --mount=type=bind,source=apps/{{ app.app }},target=/home/frappe/context/apps/{{ app.app }} bench get-app /home/frappe/context/apps/{{ app.app }} `#stage-apps-{{ app.app }}`

{% endif %}
{% endfor %}

COPY --chown=frappe:frappe config /home/frappe/frappe-bench/config


EXPOSE 8000 9000 2200
CMD ["supervisord"]
