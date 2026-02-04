[Unit]
Description=placeholder_kernel_desc
After=network.target NetworkManager.service systemd-networkd.service iwd.service local-fs.target
Wants=network-online.target
# Wait for home (e.g. decrypted or network mount) so start script is not "Resource temporarily unavailable"
RequiresMountsFor=placeholder_clash_base_dir

[Service]
Type=simple
# Run as root so TUN device can be created (operation not permitted when running as user)
User=root
Group=root
WorkingDirectory=placeholder_clash_base_dir
LimitNPROC=500
LimitNOFILE=1000000
Restart=always
RestartSec=10
StartLimitIntervalSec=120
StartLimitBurst=8
ExecStartPre=/usr/bin/sleep 2
ExecStart=placeholder_clash_base_dir/scripts/start-clash-service.sh
ExecReload=/bin/kill -HUP $MAINPID
StandardOutput=append:placeholder_clash_base_dir/resources/mihomo.log
StandardError=append:placeholder_clash_base_dir/resources/mihomo.log

[Install]
WantedBy=multi-user.target
