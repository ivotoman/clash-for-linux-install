#!/usr/bin/env bash
# Apply mihomo service fix: wait for filesystem + RestartSec to avoid "Resource temporarily unavailable"
set -e
sudo cp /home/ivo/clash-linux/mihomo.service.fixed /etc/systemd/system/mihomo.service
sudo systemctl daemon-reload
sudo systemctl restart mihomo
sleep 2
systemctl is-active mihomo && echo "mihomo service updated and running."
