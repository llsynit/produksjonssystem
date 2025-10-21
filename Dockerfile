FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true \
    TRIGGER_DIR="/tmp/trigger-produksjonssystem" \
    QUICKBASE_DUMP_DIR="/opt/quickbase" \
    JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64/jre \
    EPUBCHECK_HOME="/opt/epubcheck"

# System deps (no recommends) + Python toolchain + JDK8 + Node LTS + utilities
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
    build-essential curl gnupg wget ca-certificates \
    python-is-python3 python3-pip python3-distutils python3-dev libffi-dev \
    xdg-utils libegl1 libopengl0 \
    openjdk-8-jdk \
    cabextract xfonts-utils graphviz libavcodec-extra ffmpeg libxml2-dev libxslt1-dev \
    nano; \
    \
    # Node.js LTS
    curl -fsSL https://deb.nodesource.com/setup_lts.x | bash -; \
    apt-get install -y --no-install-recommends nodejs; \
    \
    # DAISY Ace (global)
    npm install -g @daisy/ace; \
    npm cache clean --force; \
    \
    # Calibre (specific version)
    wget -nv -O- https://download.calibre-ebook.com/linux-installer.sh \
    | sh /dev/stdin version=6.26.0; \
    \
    # MS core fonts (remove .deb afterwards)
    wget -O /tmp/ttf-mscorefonts-installer_3.8.1_all.deb \
    http://ftp.de.debian.org/debian/pool/contrib/m/msttcorefonts/ttf-mscorefonts-installer_3.8.1_all.deb; \
    dpkg -i /tmp/ttf-mscorefonts-installer_3.8.1_all.deb || true; \
    apt-get -f install -y; \
    rm -f /tmp/ttf-mscorefonts-installer_3.8.1_all.deb; \
    \
    # Python packages kept minimal; upgrade setuptools + cryptography early
    pip install --no-cache-dir --upgrade setuptools cryptography; \
    \
    # Clean apt caches to shrink layer
    apt-get clean; \
    rm -rf /var/lib/apt/lists/* /root/.cache

# Epubcheck
COPY epubcheck-5.3.0 /opt/epubcheck

# App
WORKDIR /usr/src/app
COPY . /usr/src/app

# Healthcheck
HEALTHCHECK --interval=30s --timeout=3s CMD curl -f http://localhost:3800/prodsys/v1/health || exit 1

# Python deps (no pip cache)
RUN set -eux; \
    pip install --no-cache-dir -r requirements.txt

CMD ["python", "produksjonssystem/run.py"]