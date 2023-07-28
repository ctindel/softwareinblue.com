FROM ubuntu:20.04

ARG TARGETPLATFORM

ENV SHELL /bin/bash
ENV GOPATH=/root/go

USER root

RUN apt-get -y update && \
    mkdir -p /tmp/sib && \
    apt-get install -y lsb-release sudo vim curl git make build-essential

RUN echo "Targetplatform is ${TARGETPLATFORM}"

RUN if [ "$TARGETPLATFORM" = "linux/amd64" ]; then ARCHITECTURE=linux-amd64; elif [ "$TARGETPLATFORM" = "linux/arm64" ]; then ARCHITECTURE=linux-arm64; else exit 1; fi && \
 curl https://storage.googleapis.com/golang/go1.19.5.${ARCHITECTURE}.tar.gz -o /tmp/sib/go.${ARCHITECTURE}.tar.gz && \
    tar zxpvf /tmp/sib/go.${ARCHITECTURE}.tar.gz -C /usr/local

RUN cd /tmp/sib && \
    git clone https://github.com/gohugoio/hugo.git && \
    cd hugo && \
    /usr/local/go/bin/go install --tags extended && \
    echo "#!/bin/bash\ncd /mnt/sib; /root/go/bin/hugo server -w --bind 0.0.0.0 -b http://localhost:8080/ --disableFastRender --appendPort=false" > /tmp/sib/run_local.sh && \
    chmod 755 /tmp/sib/run_local.sh && \
    echo "#!/bin/bash\necho \"Run 'docker exec -it sib_shell /bin/bash'\"\n echo \"Press [CTRL+C] to stop..\"\nwhile true\ndo\n   sleep 1\ndone" > /tmp/sib/run_shell.sh && \
    chmod 755 /tmp/sib/run_shell.sh && \
    echo "#!/bin/bash\ncd /mnt/sib; /root/go/bin/hugo && /root/go/bin/hugo deploy\n" > /tmp/sib/deploy.sh && \
    chmod 755 /tmp/sib/deploy.sh

CMD ["/bin/bash"]
ENTRYPOINT ["/bin/bash", "-c"]
