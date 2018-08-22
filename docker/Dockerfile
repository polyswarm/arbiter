FROM python:3.5-jessie
LABEL maintainer="PolySwarm Developers <info@polyswarm.io>"

RUN apt-get update && apt-get install -y \
        curl \
        jq && \
    rm -rf /var/lib/apt/lists/*

ADD /requirements.txt /requirements.txt
RUN pip install -r requirements.txt
ADD . .
CMD ["python3", "arbiter.py", "--backend", "verbatim"]
