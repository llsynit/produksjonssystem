FROM ubuntu:22.04
RUN apt-get update
RUN apt-get clean
#Java
RUN apt-get update && apt-get install -y openjdk-8-jdk

RUN apt-get install -y build-essential
RUN apt-get -y install curl gnupg wget
RUN apt-get -y update && apt-get install -y python-is-python3 python3-pip python3-distutils python3-dev libffi-dev

RUN pip install setuptools --upgrade
RUN pip install cryptography

# We don't need the standalone Chromium
ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD true

RUN curl -fsSL https://deb.nodesource.com/setup_lts.x | bash - &&\
apt-get install -y nodejs
RUN npm install @daisy/ace -g



RUN wget -nv -O- https://download.calibre-ebook.com/linux-installer.sh | sudo sh /dev/stdin | python -c "import sys; main=lambda:sys.stderr.write('Download failed\n'); exec(sys.stdin.read()); main()"



RUN apt-get install -qy cabextract xfonts-utils

RUN wget http://ftp.de.debian.org/debian/pool/contrib/m/msttcorefonts/ttf-mscorefonts-installer_3.8.1_all.deb
RUN dpkg -i ttf-mscorefonts-installer_3.8.1_all.deb


RUN apt-get install -y graphviz

RUN apt-get install -y libavcodec-extra
RUN apt-get install -y ffmpeg
RUN apt-get install -y libxml2-dev libxslt1-dev


COPY epubcheck-5.0.0 /opt/epubcheck
COPY . /usr/src/app
WORKDIR /usr/src/app

ENV TRIGGER_DIR="/tmp/trigger-produksjonssystem"
ENV QUICKBASE_DUMP_DIR="/opt/quickbase"
ENV JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64/jre
ENV EPUBCHECK_HOME="/opt/epubcheck"



RUN pip install -r requirements.txt
CMD ["python","produksjonssystem/run.py"]