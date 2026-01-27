# syntax = docker/dockerfile:experimental
FROM ubuntu:22.04

ENV FRAPPE_DOCKER_BUILD True
ENV LANG C.UTF-8
ENV DEBIAN_FRONTEND noninteractive

ENV OPENBLAS_NUM_THREADS 1
ENV MKL_NUM_THREADS 1

# Install essential packages
RUN --mount=type=cache,sharing=locked,target=/var/cache/apt apt-get update \
  && apt-get install --yes --no-install-suggests --no-install-recommends \
  # Essentials
  build-essential \
  git \
  mariadb-client \
  libmariadb-dev \
  pkg-config \
  pv \
  ntp \
  wget \
  curl \
  supervisor \
  file \
  # Dependencies for SSH access
  openssh-server \
  nano \
  vim \
  less \
  htop \
  iputils-ping \
  telnet \
  # Dependencies for adding Python PPA
  software-properties-common \
  gnupg \
  # weasyprint dependencies
  libpango-1.0-0 \
  libharfbuzz0b \
  libpangoft2-1.0-0 \
  libpangocairo-1.0-0 \
  # Chromium and dependencies
  chromium-browser \
  libnss3 \
  libatk1.0-0 \
  fonts-liberation \
  libatk-bridge2.0-0 \
  ibatspi2.0-0 \
  libgbm1 \
  libgtk-3-0 \
  libnspr4 \
  xdg-utils \
  libvulkan1 \
  libxcomposite1 \
  libxdamage1 \
  libxfixes3 \
  libxkbcommon0 \
  libxrandr2 \
  libasound2 \
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
  # s3-attachment dependencies
  libmagic1 \
  && rm -rf /var/lib/apt/lists/* \
  `#stage-pre-essentials`

COPY --chown=root:root supervisord.conf /etc/supervisor/supervisord.conf

# Install Redis from PPA
RUN --mount=type=cache,sharing=locked,target=/var/cache/apt curl -fsSL https://packages.redis.io/gpg | gpg --dearmor -o /usr/share/keyrings/redis-archive-keyring.gpg \
  && echo "deb [signed-by=/usr/share/keyrings/redis-archive-keyring.gpg] https://packages.redis.io/deb jammy main" | tee /etc/apt/sources.list.d/redis.list \
  && apt-get update \
  && apt-get install --yes --no-install-suggests --no-install-recommends \
  redis-server \
  && rm -rf /var/lib/apt/lists/* `#stage-pre-redis`

# Install Python from DeadSnakes PPA
ENV {{ doc.get_dependency_version("python", True) }}
RUN --mount=type=cache,sharing=locked,target=/var/cache/apt add-apt-repository ppa:deadsnakes/ppa \
  && apt-get update \
  && apt-get install --yes --no-install-suggests --no-install-recommends \
    python${PYTHON_VERSION} \
    python${PYTHON_VERSION}-dev \
    {% if not remove_distutils -%}
    python${PYTHON_VERSION}-distutils \
    {%- endif %}
    python${PYTHON_VERSION}-venv \
  && rm -rf /var/lib/apt/lists/* \
  `#stage-pre-python`

# Install wkhtmltopdf
ENV {{ doc.get_dependency_version("wkhtmltopdf", True) }}


{% if is_arm_build %}
  # ARM setup (0.12.5) & (0.12.6)
  {% if doc.get_dependency_version("wkhtmltopdf") == '0.12.5' %}
  RUN wget https://github.com/Aradhya-Tripathi/wkhtmltopdf/releases/download/0.12.5-arm/wkhtmltox_0.12.5-1.jammy_arm64.deb \
    && dpkg -i wkhtmltox_0.12.5-1.jammy_arm64.deb \
    && rm wkhtmltox_0.12.5-1.jammy_arm64.deb \
    `#stage-pre-wkhtmltopdf`
  {% endif %}

  {% if doc.get_dependency_version("wkhtmltopdf") == '0.12.6' %}
  RUN wget https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-2/wkhtmltox_0.12.6.1-2.jammy_arm64.deb  \
    && dpkg -i wkhtmltox_0.12.6.1-2.jammy_arm64.deb \
    && rm wkhtmltox_0.12.6.1-2.jammy_arm64.deb \
    `#stage-pre-wkhtmltopdf`
  {% endif %}
{% else %}
  # Intel setup
  {% if doc.get_dependency_version("wkhtmltopdf") == '0.12.6' %}
  RUN wget https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-2/wkhtmltox_0.12.6.1-2.jammy_amd64.deb  \
    && dpkg -i wkhtmltox_0.12.6.1-2.jammy_amd64.deb \
    && rm wkhtmltox_0.12.6.1-2.jammy_amd64.deb \
    `#stage-pre-wkhtmltopdf`
  {% elif doc.get_dependency_version("wkhtmltopdf") == '0.12.5' %}
  RUN wget https://github.com/Aradhya-Tripathi/wkhtmltopdf/releases/download/0.12.5/wkhtmltox_0.12.5-1.jammy_amd64.deb  \
    && dpkg -i wkhtmltox_0.12.5-1.jammy_amd64.deb \
    && rm wkhtmltox_0.12.5-1.jammy_amd64.deb \
    `#stage-pre-wkhtmltopdf`
  {% endif %}
{% endif %}

{% if doc.is_code_server_enabled %}
RUN curl -fsSL https://code-server.dev/install.sh | sh `#stage-pre-code-server`
{% endif %}

# Install Fonts
RUN git clone --progress --depth 1 https://github.com/frappe/fonts.git /tmp/fonts \
  && rm -rf /etc/fonts && mv /tmp/fonts/etc_fonts /etc/fonts \
  && rm -rf /usr/share/fonts && mv /tmp/fonts/usr_share_fonts /usr/share/fonts \
  && rm -rf /tmp/fonts \
  && fc-cache -fv \
  `#stage-pre-fonts`


# Set max_allowed_packet to 512 MB for mysqldump
RUN echo "[mysqldump]\nmax_allowed_packet              = 512M" > /etc/mysql/conf.d/mysqldump.cnf

# Add frappe user
RUN useradd -ms /bin/bash frappe

# Install Additional Packages
{% for p in doc.additional_packages %}

# Run before install scripts
{% if p.prerequisites %}
RUN --mount=type=cache,sharing=locked,target=/var/cache/apt {{ p.prerequisites }} \
  `#stage-pre_before-{{ p.package }}`
{% endif %}

# Install non Ubuntu packages
{% if p.package_manager not in ["apt-get", "apt"] %}
RUN {{ p.package_manager }} install {{ p.package }} \
  `#stage-pre-{{ p.package }}`

# Install Ubuntu packages
{% else %}
RUN apt-get update \
  && apt-get install --yes --no-install-suggests --no-install-recommends {{ p.package }} \
  && rm -rf /var/lib/apt/lists/* \
  `#stage-pre-{{ p.package }}`
{% endif %}

# Run after install scripts
{% if p.after_install %}
RUN  --mount=type=cache,sharing=locked,target=/var/cache/apt {{ p.after_install }} \
  && rm -rf /var/lib/apt/lists/* \
  `#stage-pre_after-{{ p.package }}`
{% endif %}

{% endfor %}


# symlink mysqldump to mariadb-dump
RUN test -f /usr/bin/mariadb-dump || ln -s /usr/bin/mysqldump /usr/bin/mariadb-dump

# Switch to frappe
USER frappe
WORKDIR /home/frappe


# Install Node using NVM
ENV NVM_DIR /home/frappe/.nvm
ENV {{ doc.get_dependency_version("nvm", True) }}
ENV {{ doc.get_dependency_version("node", True) }}

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

ENV {{ doc.get_dependency_version("pip", True) }}

{% if requires_version_based_get_pip %}
RUN wget https://bootstrap.pypa.io/pip/${PYTHON_VERSION}/get-pip.py && python${PYTHON_VERSION} get-pip.py `#stage-pre-pip`
{% else %}
RUN wget https://bootstrap.pypa.io/get-pip.py && python${PYTHON_VERSION} get-pip.py pip==${PIP_VERSION} `#stage-pre-pip`
{% endif %}

ENV {{ doc.get_dependency_version("bench", True) }}
RUN --mount=type=cache,target=/home/frappe/.cache,uid=1000,gid=1000 python${PYTHON_VERSION} -m pip install --upgrade frappe-bench==${BENCH_VERSION} `#stage-bench-bench`

RUN --mount=type=cache,target=/home/frappe/.cache,uid=1000,gid=1000 python${PYTHON_VERSION} -m pip install Jinja2~=3.0.3
RUN --mount=type=cache,target=/home/frappe/.cache,uid=1000,gid=1000 python${PYTHON_VERSION} -m pip install --upgrade setuptools

RUN git config --global advice.detachedHead false

ENV PYTHONUNBUFFERED 1

# For the sake of completing the step
RUN `#stage-bench-env`

# Set environment variables
{% for v in doc.environment_variables %}
ENV {{v.key}} {{ v.value }}
{% endfor %}

# Install Boto and Requests for Asset store access
RUN --mount=type=cache,target=/home/frappe/.cache,uid=1000,gid=1000 \
  python${PYTHON_VERSION} -m pip install boto3 botocore requests \
  `#stage-pre-Configure Asset Store`

# Install Frappe app
RUN --mount=type=cache,sharing=locked,target=/home/frappe/.cache,uid=1000,gid=1000 --mount=type=bind,source=apps/frappe,target=/home/frappe/context/apps/frappe bench init --python /usr/bin/python${PYTHON_VERSION} --no-backups --frappe-path file:///home/frappe/context/apps/frappe frappe-bench `#stage-apps-frappe`
WORKDIR /home/frappe/frappe-bench

RUN --mount=type=cache,target=/home/frappe/.cache,uid=1000,gid=1000 /home/frappe/frappe-bench/env/bin/pip install pycups==2.0.1

# Install Redisearch 2.0 from precompiled binaries
COPY --chown=frappe:frappe redis /home/frappe/frappe-bench/redis
COPY --chown=frappe:frappe .vimrc /home/frappe/.vimrc
COPY --chown=frappe:frappe common_site_config.json /home/frappe/frappe-bench/sites/common_site_config.json

# Pass control of get-app to a python file
COPY get_cached_app.py /usr/local/bin/get_cached_app.py
RUN chmod +x /usr/local/bin/get_cached_app.py

# Install other apps
{% for app in doc.apps %}
{% if app.app != "frappe"%}


{% if app.use_cached and use_asset_store %}
RUN --mount=type=bind,source=apps/{{ app.app }},target=/home/frappe/context/apps/{{ app.app }} \
    --mount=type=secret,id=build_token,mode=0444 \
    BUILD_TOKEN="$(cat /run/secrets/build_token)" && python${PYTHON_VERSION} /usr/local/bin/get_cached_app.py \
        {{ app.app }} \
        {{ app.hash }} \
        "$BUILD_TOKEN" \
        {{ site_url }} \
        {{ upload_assets }} \
        `#stage-apps-{{ app.app }}`
{% else %}
RUN --mount=type=cache,sharing=locked,target=/home/frappe/.cache,uid=1000,gid=1000 \
    --mount=type=bind,source=apps/{{ app.app }},target=/home/frappe/context/apps/{{ app.app }} \
    bench get-app file:///home/frappe/context/apps/{{ app.app }} \
    `#stage-apps-{{ app.app }}`
{% endif %}


{% endif %}
{% endfor %}

# Pull app updates from mounted repository
{% for app in doc.apps %}
{% if app.pullable_release %}
RUN --mount=type=bind,source=app_updates/{{ app.app }},target=/home/frappe/context/app_updates/{{ app.app }} \
  cd /home/frappe/frappe-bench/apps/{{ app.app }} \
  && git reset --hard \
  && git remote add -f app_update /home/frappe/context/app_updates/{{ app.app }} \
  && git fetch --depth 1 app_update {{ app.pullable_hash }} \
  && git checkout {{ app.pullable_hash }} \
  && git remote remove app_update \
  `#stage-pull-{{ app.app }}`
{% endif %}
{% endfor %}


COPY --chown=frappe:frappe config /home/frappe/frappe-bench/config
COPY --chown=frappe:frappe apps.txt /home/frappe/frappe-bench/sites/apps.txt

# Create custom mounts
{% for m in doc.container_mounts %}
RUN mkdir -p {{ m.destination }} && \
  chown -R frappe:frappe {{ m.destination }} \
  `#stage-mounts-create`
{% endfor %}

ENV FRAPPE_DOCKER_BUILD=
ENV FRAPPE_HARD_LINK_ASSETS True
ENV HISTTIMEFORMAT "%Y-%m-%d %T "

EXPOSE 8000 9000 2200 8088
CMD ["supervisord"]
