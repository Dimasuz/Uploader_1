#!/bin/bash

git --version
python3 --version

cp -rT . ~

apt update
apt install apt-transport-https ca-certificates curl software-properties-common
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add -
add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
apt update
apt-cache policy docker-ce
apt install docker-ce -y
systemctl start docker
systemctl enable docker
systemctl status docker --no-pager
apt update
apt install docker-compose-plugin
docker compose version

