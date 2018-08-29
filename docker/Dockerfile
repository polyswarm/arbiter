FROM python:3.5-jessie
LABEL maintainer="PolySwarm Developers <info@polyswarm.io>"

RUN apt-get update && apt-get install -y \
        curl \
        jq && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN set -x && pip install --no-cache-dir -r requirements.txt

COPY . .
RUN set -x && pip install .

CMD ["arbiter"]
