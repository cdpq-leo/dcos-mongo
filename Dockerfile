FROM mongo:4.0.10

ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

COPY dcos-docker-entrypoint.sh /usr/local/bin/

COPY cli /usr/local/cli/
COPY requirements.txt /usr/local/cli/

RUN apt-get update \
 && apt-get install -y software-properties-common python-software-properties python3-pip build-essential libssl-dev libffi-dev python-dev curl \
 && pip3 install -r /usr/local/cli/requirements.txt

RUN addgroup --gid 99 nobody \
 && usermod -u 99 -g 99 nobody \
 && echo "nobody:x:65534:65534:nobody:/nonexistent:/usr/sbin/nologin" >> /etc/passwd \
 && usermod -a -G users nobody

WORKDIR /usr/local

ENTRYPOINT ["dcos-docker-entrypoint.sh"]
