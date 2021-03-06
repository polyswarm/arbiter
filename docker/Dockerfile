FROM python:3.5-jessie
LABEL maintainer="PolySwarm Developers <info@polyswarm.io>"

RUN apt-get update && apt-get install -y \
        curl \
        wget \
        jq && \
    rm -rf /var/lib/apt/lists/*

# Install dockerize
ENV DOCKERIZE_VERSION v0.6.1
RUN wget https://github.com/jwilder/dockerize/releases/download/$DOCKERIZE_VERSION/dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz \
    && tar -C /usr/local/bin -xzvf dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz \
    && rm dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN set -x && pip install --no-cache-dir -r requirements.txt

COPY . .
RUN set -x && pip install .
RUN generate_verbatim --malicious ./artifacts/malicious --benign ./artifacts/benign --output ./artifacts/truth.db
CMD ["arbiter"]
