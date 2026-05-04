FROM ubuntu:24.04

ARG TARGETPLATFORM

ENV SHELL /bin/bash
ENV GOPATH=/root/go

USER root

RUN apt-get -y update && \
    mkdir -p /tmp/sib && \
    apt-get install -y lsb-release sudo vim curl wget git libc6

RUN echo "Targetplatform is ${TARGETPLATFORM}"

RUN cd /tmp/sib && \
    HUGO_ARCH=$(case "${TARGETPLATFORM}" in "linux/arm64") echo "arm64" ;; *) echo "amd64" ;; esac) && \
    wget https://github.com/gohugoio/hugo/releases/download/v0.161.1/hugo_extended_0.161.1_linux-${HUGO_ARCH}.tar.gz && \
    tar -xf hugo_extended_0.161.1_linux-${HUGO_ARCH}.tar.gz hugo && \
    mv hugo /usr/bin/hugo && \
    rm -rf hugo_extended_0.161.1_linux-${HUGO_ARCH}.tar.gz && \
    echo "#!/bin/bash\ncd /mnt/sib; /usr/bin/hugo server -w --bind 0.0.0.0 -b http://localhost:8080/ --disableFastRender --appendPort=false" > /tmp/sib/run_local.sh && \
    chmod 755 /tmp/sib/run_local.sh && \
    echo "#!/bin/bash\necho \"Run 'docker exec -it sib_shell /bin/bash'\"\n echo \"Press [CTRL+C] to stop..\"\nwhile true\ndo\n   sleep 1\ndone" > /tmp/sib/run_shell.sh && \
    chmod 755 /tmp/sib/run_shell.sh && \
    echo "#!/bin/bash\ncd /mnt/sib; /usr/bin/hugo && /usr/bin/hugo deploy\n" > /tmp/sib/deploy.sh && \
    chmod 755 /tmp/sib/deploy.sh

CMD ["/bin/bash"]
ENTRYPOINT ["/bin/bash", "-c"]
