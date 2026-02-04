#!/usr/bin/env bash
# Wrapper for systemd: merge config and run mihomo (Clash + TUN at boot)
set -e
CLASH_BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
export CLASH_BASE_DIR
cd "$CLASH_BASE_DIR"
. scripts/cmd/clashctl.sh
_merge_config
# When run as root (systemd), enable TUN so all traffic (including ping) goes through VPN
[ "$(id -u)" = "0" ] && "$BIN_YQ" -i '.tun.enable = true' "$CLASH_CONFIG_RUNTIME"
exec "$BIN_KERNEL" -d "$CLASH_RESOURCES_DIR" -f "$CLASH_CONFIG_RUNTIME"
