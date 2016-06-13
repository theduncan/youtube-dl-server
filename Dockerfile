#
# youtube-dl Server Dockerfile
#
# https://github.com/kmb32123/youtube-dl-server-dockerfile
#

# Pull base image.
FROM ampervue/ffmpeg
#FROM python:3-onbuild

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

COPY requirements.txt /usr/src/app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /usr/src/app

EXPOSE 8081

VOLUME ["/dl"]

CMD [ "python", "-u", "/usr/src/app/youtube-dl-server.py" ]
