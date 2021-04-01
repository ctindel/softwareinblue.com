FROM ubuntu:16.04
ENV SHELL /bin/bash
ENV GOPATH=/root/go

USER root

RUN apt-get -y update && \
    apt-get install -y lsb-release iproute2 sudo vim curl git make build-essential && \
    mkdir -p /tmp/sib && \
    curl https://storage.googleapis.com/golang/go1.16.2.linux-amd64.tar.gz -o /tmp/sib/go1.16.2.linux-amd64.tar.gz && \
    tar zxpvf /tmp/sib/go1.16.2.linux-amd64.tar.gz -C /usr/local && \
    cd /tmp/sib && \
    git clone https://github.com/gohugoio/hugo.git && \
    cd hugo && \
    /usr/local/go/bin/go install --tags extended && \
    echo "#!/bin/bash\ncd /mnt/sib; /root/go/bin/hugo server -w --bind 0.0.0.0 -b http://localhost:8080/ --disableFastRender --appendPort=false" > /tmp/sib/run_local.sh && \
    chmod 755 /tmp/sib/run_local.sh && \
    echo "#!/bin/bash\necho \"Run 'docker exec -it sib_shell /bin/bash'\"\n echo \"Press [CTRL+C] to stop..\"\nwhile true\ndo\n   sleep 1\ndone" > /tmp/sib/run_shell.sh && \
    chmod 755 /tmp/sib/run_shell.sh

CMD ["/bin/bash"]
ENTRYPOINT ["/bin/bash", "-c"]
