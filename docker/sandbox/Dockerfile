# helix-sandbox — Docker sandbox image
# Ubuntu 24.04 + Xvfb + x11vnc + noVNC + Python 3.12
# Provides a remote desktop environment for AI agent sandbox operations.

FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive \
    DISPLAY=:99 \
    RESOLUTION=1280x720x24 \
    VNC_PASSWORD="" \
    LANG=en_US.UTF-8 \
    LC_ALL=en_US.UTF-8

# Install all packages in a single layer
RUN apt-get update && apt-get install -y --no-install-recommends \
    xvfb \
    x11vnc \
    xfce4 \
    xfce4-terminal \
    dbus-x11 \
    novnc \
    websockify \
    python3 \
    python3-venv \
    python3-pip \
    git \
    curl \
    wget \
    vim-tiny \
    nano \
    unzip \
    build-essential \
    imagemagick \
    xdotool \
    x11-utils \
    locales \
    && locale-gen en_US.UTF-8 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Symlink python -> python3
RUN ln -sf /usr/bin/python3 /usr/bin/python 2>/dev/null || true

# Create workspace directory
RUN mkdir -p /workspace && chmod 777 /workspace

# noVNC setup: symlink for web access
RUN ln -sf /usr/share/novnc/vnc.html /usr/share/novnc/index.html 2>/dev/null || true

# Startup script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 5900 6080

WORKDIR /workspace

ENTRYPOINT ["/entrypoint.sh"]
