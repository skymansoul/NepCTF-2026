FROM ubuntu:20.04 as compiler2

USER root

WORKDIR /root/ctf

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        wget \
        gcc \
        libc6-dev \
        make \
        ca-certificates \
        xz-utils \
        bash \
        file && \
    update-ca-certificates && \
    rm -rf /var/lib/apt/lists/*

COPY ./ls.c ./
COPY ./cat.c ./

RUN gcc ./ls.c -o ./ls && \
    gcc ./cat.c -o ./cat


FROM ubuntu:20.04 as runner

USER root

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        bash \
        xinetd \
        coreutils && \
    ln -sf "$(which bash)" /bin/sh && \
    useradd -m -u 1000 -s /bin/sh ctf && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /home/ctf

COPY ./src/d8 ./d8 

COPY ./flag ./
COPY ./run_pwn.sh /
COPY ./ctf.xinetd /etc/ctf.xinetd

# compile ls && cat
RUN mkdir ./bin && \
    cp /bin/bash ./bin/sh

COPY --from=compiler2 /root/ctf/ls ./bin/ls
COPY --from=compiler2 /root/ctf/cat ./bin/cat

RUN mkdir ./dev && \
    mknod ./dev/null c 1 3 && \
    mknod ./dev/zero c 1 5 && \
    mknod ./dev/random c 1 8 && \
    mknod ./dev/urandom c 1 9 && \
    chmod 666 ./dev/*

RUN mkdir -p ./lib/x86_64-linux-gnu ./usr/lib/x86_64-linux-gnu lib64 && \
    cp -a /lib/x86_64-linux-gnu/*.so* ./lib/x86_64-linux-gnu/ && \
    cp -a /usr/lib/x86_64-linux-gnu/*.so* ./usr/lib/x86_64-linux-gnu/ && \
    cp -a /lib64/ld-linux-x86-64.so.2 ./lib64/

RUN chmod 644 ./flag  && \
	chmod 711 /run_pwn.sh && \
    chown -R root:root .

EXPOSE 1337

CMD xinetd -f /etc/ctf.xinetd -pidfile /run/xinetd.pid -limit 1000 -reuse;sleep infinity;


