FROM mongo:4.0.10

ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

COPY cli /usr/local/bin/cli/
COPY dcos-docker-entrypoint.sh /usr/local/bin/
COPY requirements.txt /usr/local/bin/

RUN apt-get update && \
    apt-get install -y software-properties-common python-software-properties python3-pip && \
    pip3 install -r /usr/local/bin/requirements.txt

ENTRYPOINT ["dcos-docker-entrypoint.sh"]
