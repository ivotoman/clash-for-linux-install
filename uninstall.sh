#!/usr/bin/env bash
. .env
. "$CLASH_BASE_DIR/scripts/cmd/clashctl.sh" 2>/dev/null
. scripts/preflight.sh

<<<<<<< HEAD
pgrep -f "$BIN_KERNEL" -u 0 >/dev/null && ! _is_root && _error_quit "请先关闭 Tun 模式"
=======
pgrep -f "$BIN_KERNEL" -u 0 >/dev/null && ! _is_root && _error_quit 'Please run uninstall with sudo'
>>>>>>> zorin
clashoff 2>/dev/null
_uninstall_service
_revoke_rc

command -v crontab >&/dev/null && crontab -l | grep -v "clashsub" | crontab -

/usr/bin/rm -rf "$CLASH_BASE_DIR"

echo '✨' 'Uninstalled, related configuration cleared'
_quit
