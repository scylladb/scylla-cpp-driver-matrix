FROM python:3.11-slim

RUN apt-get -y update \
    && apt-get install -y wget apt-transport-https \
    && apt-get -y install \
                    ca-certificates \
                    curl \
                    gnupg \
                    lsb-release \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg \
    && echo \
       "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian \
       $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null \
    && wget -O - https://packages.adoptium.net/artifactory/api/gpg/key/public | tee /etc/apt/keyrings/adoptium.asc \
    && echo "deb [signed-by=/etc/apt/keyrings/adoptium.asc] https://packages.adoptium.net/artifactory/deb $(awk -F= '/^VERSION_CODENAME/{print$2}' /etc/os-release) main" | tee /etc/apt/sources.list.d/adoptium.list \
    && apt-get -y update \
    && apt-get -y install sudo git gcc clang cmake libuv1-dev libssl-dev libkrb5-dev zlib1g-dev patch temurin-11-jdk docker-ce-cli \
    && rm -rf /var/lib/apt/lists/*

ADD requirements.txt requirements.txt
RUN sudo pip3 install -r requirements.txt
ENTRYPOINT [ "/bin/sh", "-l", "-c" ]
