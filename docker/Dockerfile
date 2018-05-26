FROM golang:latest
LABEL maintainer="PolySwarm Developers <info@polyswarm.io>"

ENV GOPATH /go
ENV PATH $GOPATH/bin:$PATH

RUN mkdir -p $GOPATH/src/arbiter-verbatim/
ADD . $GOPATH/src/arbiter-verbatim/

#RUN set -x && \
#    cd $GOPATH/src/arbiter-verbatim && \
#    go get . && \
#    go install
ADD arbiter-verbatim $GOPATH/bin/arbiter-verbatim

RUN useradd -ms /bin/bash arbiter
WORKDIR /home/arbiter
USER arbiter

ENTRYPOINT $GOPATH/bin/arbiter-verbatim
