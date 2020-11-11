#!/bin/bash

GITHUB_RAW_CONTENT=https://raw.githubusercontent.com/TenFourth/LRA1-gateway/main

install_pkg() {
  local pkg=$1
  /usr/bin/dpkg -l --no-pager ${pkg}
  if [ $? -ne 0 ]; then
    /usr/bin/apt install -y ${pkg}
  fi
}

download() {
  local url=${GITHUB_RAW_CONTENT}${1}
  local dest_path=${2}
  /usr/bin/curl -L ${url} -o ${dest_path}
}

install_pkg python-rpi.gpio
install_pkg python-serial
install_pkg python-urllib3

download '/sbin/lra1-gateway.py' '/usr/local/sbin/lra1-gateway.py'
chmod 755 /usr/local/sbin/lra1-gateway.py

download '/etc/systemd/system/lra1-gateway.service' '/etc/systemd/system/lra1-gateway.service'
systemctl daemon-reload
systemctl enable lra1-gateway.service
systemctl restart lra1-gateway.service

echo "LRA1-gateway install successful"