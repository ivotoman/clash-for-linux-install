[Unit]
Description=placeholder_kernel_desc
After=network.target NetworkManager.service systemd-networkd.service iwd.service
Wants=network-online.target

[Service]
Type=simple
# Run as root so TUN device can be created (operation not permitted when running as user)
User=root
Group=root
WorkingDirectory=/home/ivo/clashctl
LimitNPROC=500
LimitNOFILE=1000000
Restart=always
ExecStartPre=/usr/bin/sleep 1s
ExecStart=placeholder_cmd_full
ExecReload=/bin/kill -HUP $MAINPID
StandardOutput=append:/home/ivo/clashctl/resources/mihomo.log
StandardError=append:/home/ivo/clashctl/resources/mihomo.log

[Install]
WantedBy=multi-user.target
