FROM ubuntu:22.04
RUN apt-get update && apt-get clean
#RUN apt-get clean
#Java
#RUN apt-get update && apt-get install -y openjdk-8-jdk

#RUN apt-get install -y openjdk-8-jdk


#RUN apt-get install -y build-essential
#RUN apt-get -y install build-essential curl gnupg wget
RUN apt-get -y update && apt-get install -y build-essential curl gnupg wget python-is-python3 python3-pip python3-distutils python3-dev libffi-dev  xdg-utils libegl1 libopengl0 &&\
  pip install setuptools --upgrade &&\
  pip install cryptography &&\
  apt-get install nano -y &&\
  apt-get install -y openjdk-8-jdk

#RUN pip install cryptography

# We don't need the standalone Chromium
ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD true
#LTS (Long-Term Support) versions and will receive updates and support for an extended period. lts takes longer to install
RUN curl -fsSL https://deb.nodesource.com/setup_lts.x | bash - &&\
  #RUN curl -sL https://deb.nodesource.com/setup_16.x | bash - &&\
  apt-get install -y nodejs &&\
  npm install @daisy/ace -g


#RUN wget -nv -O- https://download.calibre-ebook.com/linux-installer.sh | sh /dev/stdin
#VERSION  7.1.0. fails to install
#RUN  wget -nv -O- https://download.calibre-ebook.com/linux-installer.sh | sh /dev/stdin version=6.26.0

RUN apt-get install -qy cabextract xfonts-utils &&\
  wget http://ftp.de.debian.org/debian/pool/contrib/m/msttcorefonts/ttf-mscorefonts-installer_3.8.1_all.deb &&\
  dpkg -i ttf-mscorefonts-installer_3.8.1_all.deb &&\
  apt-get install -y graphviz libavcodec-extra ffmpeg libxml2-dev libxslt1-dev

# Pandoc installation
# Add architecture-specific commands
RUN ARCH=$(dpkg --print-architecture) && \
  if [ "$ARCH" = "amd64" ]; then \
  wget https://github.com/jgm/pandoc/releases/download/3.1.7/pandoc-3.1.7-linux-amd64.tar.gz && \
  tar -xvzf pandoc-3.1.7-linux-amd64.tar.gz --strip-components 1 -C /usr/local && \
  rm -f pandoc-3.1.7-linux-amd64.tar.gz; \
  elif [ "$ARCH" = "arm64" ]; then \
  apt-get install -y pandoc; \
  else \
  echo "Unsupported architecture: $ARCH" && exit 1; \
  fi

# Verify Pandoc installation
RUN pandoc --version


# Verify Pandoc installation
RUN pandoc --version


#RUN apt-get install -y graphviz

#RUN apt-get install -y libavcodec-extra ffmpeg libxml2-dev libxslt1-dev
#RUN apt-get install -y ffmpeg
#RUN apt-get install -y libxml2-dev libxslt1-dev


COPY epubcheck-5.0.0 /opt/epubcheck
COPY . /usr/src/app
WORKDIR /usr/src/app

ENV TRIGGER_DIR="/tmp/trigger-produksjonssystem"
ENV QUICKBASE_DUMP_DIR="/opt/quickbase"
ENV JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64/jre
ENV EPUBCHECK_HOME="/opt/epubcheck"

# Add HEALTHCHECK
HEALTHCHECK --interval=30s --timeout=3s \
  CMD curl -f http://localhost:3800/prodsys/v1/health || exit 1


RUN pip install -r requirements.txt && python -c "import nltk; nltk.download('punkt_tab')"
CMD ["python","produksjonssystem/run.py"]