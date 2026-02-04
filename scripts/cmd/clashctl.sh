#!/usr/bin/env bash

THIS_SCRIPT_DIR=$(dirname "$(readlink -f "${BASH_SOURCE:-${(%):-%N}}")")
. "$THIS_SCRIPT_DIR/common.sh"

_set_system_proxy() {
    local mixed_port=$("$BIN_YQ" '.mixed-port // ""' "$CLASH_CONFIG_RUNTIME")
    local http_port=$("$BIN_YQ" '.port // ""' "$CLASH_CONFIG_RUNTIME")
    local socks_port=$("$BIN_YQ" '.socks-port // ""' "$CLASH_CONFIG_RUNTIME")

    local auth=$("$BIN_YQ" '.authentication[0] // ""' "$CLASH_CONFIG_RUNTIME")
    [ -n "$auth" ] && auth=$auth@

    local bind_addr=$(_get_bind_addr)
    local http_proxy_addr="http://${auth}${bind_addr}:${http_port:-${mixed_port}}"
    local socks_proxy_addr="socks5h://${auth}${bind_addr}:${socks_port:-${mixed_port}}"
    local no_proxy_addr="localhost,127.0.0.1,::1"

    export http_proxy=$http_proxy_addr
    export HTTP_PROXY=$http_proxy

    export https_proxy=$http_proxy
    export HTTPS_PROXY=$https_proxy

    export all_proxy=$socks_proxy_addr
    export ALL_PROXY=$all_proxy

    export no_proxy=$no_proxy_addr
    export NO_PROXY=$no_proxy

    # Persist for other terminals (e.g. desktop-opened, zsh)
    cat > "${HOME}/.clash_proxy_env" << EOF
# Clash proxy env - sourced by .bashrc/.zshrc so all terminals use VPN
export http_proxy='$http_proxy_addr'
export HTTP_PROXY='$http_proxy_addr'
export https_proxy='$http_proxy_addr'
export HTTPS_PROXY='$http_proxy_addr'
export all_proxy='$socks_proxy_addr'
export ALL_PROXY='$socks_proxy_addr'
export no_proxy='$no_proxy_addr'
export NO_PROXY='$no_proxy_addr'
EOF
}
_unset_system_proxy() {
    unset http_proxy
    unset https_proxy
    unset HTTP_PROXY
    unset HTTPS_PROXY
    unset all_proxy
    unset ALL_PROXY
    unset no_proxy
    unset NO_PROXY
    rm -f "${HOME}/.clash_proxy_env"
}
_detect_proxy_port() {
    local mixed_port=$("$BIN_YQ" '.mixed-port // ""' "$CLASH_CONFIG_RUNTIME")
    local http_port=$("$BIN_YQ" '.port // ""' "$CLASH_CONFIG_RUNTIME")
    local socks_port=$("$BIN_YQ" '.socks-port // ""' "$CLASH_CONFIG_RUNTIME")
    local newPort count=0
    [ -z "$mixed_port" ] && [ -z "$http_port" ] && [ -z "$socks_port" ] && mixed_port=7890
    [ -n "$mixed_port" ] && _is_port_used "$mixed_port" && {
        ((count += 1))
        newPort=$(_get_random_port)
        _failcat '🎯' "Port conflict: [mixed-port] ${mixed_port} 🎲 Randomly assigned $newPort"
        mixed_port=$newPort
        "$BIN_YQ" -i ".mixed-port = $newPort" "$CLASH_CONFIG_MIXIN"
    }
    [ -n "$http_port" ] && _is_port_used "$http_port" && {
        ((count += 1))
        newPort=$(_get_random_port)
        _failcat '🎯' "Port conflict: [port] ${http_port} 🎲 Randomly assigned $newPort"
        http_port=$newPort
        "$BIN_YQ" -i ".port = $newPort" "$CLASH_CONFIG_MIXIN"
    }
    [ -n "$socks_port" ] && _is_port_used "$socks_port" && {
        ((count += 1))
        newPort=$(_get_random_port)
        _failcat '🎯' "Port conflict: [port] ${socks_port} 🎲 Randomly assigned $newPort [socks-port]"
        socks_port=$newPort
        "$BIN_YQ" -i ".socks-port = $newPort" "$CLASH_CONFIG_MIXIN"
    }
    ((count)) && _merge_config
}

# Use systemd when mihomo.service is installed (start at boot)
_use_systemd() {
    [ -f /etc/systemd/system/mihomo.service ]
}
_service_stop() {
    if _use_systemd; then
        sudo systemctl stop mihomo 2>/dev/null || true
    else
        sudo pkill -9 -f "$BIN_KERNEL" 2>/dev/null || true
    fi
}
_service_start() {
    if _use_systemd; then
        if sudo systemctl start mihomo 2>/dev/null; then
            return 0
        fi
        # Fallback to nohup if systemd fails (e.g. broken service file)
    fi
    ( nohup "$BIN_KERNEL" -d "$CLASH_RESOURCES_DIR" -f "$CLASH_CONFIG_RUNTIME" >& "$CLASH_RESOURCES_DIR/mihomo.log" & )
}

function clashon() {
    clashstatus >&/dev/null || {
        _detect_proxy_port
        _service_start
        sleep 0.5
        clashstatus >/dev/null || {
            _failcat 'Start failed: Run clashlog to view logs'
            return 1
        }
    }
    clashproxy >/dev/null && _set_system_proxy
    _okcat 'Proxy environment enabled'
}

watch_proxy() {
    [ -z "$http_proxy" ] && {
        # [[ "$0" == -* ]] && { # login shell
        [[ $- == *i* ]] && { # interactive shell
            clashon
        }
    }
}

function clashoff() {
    clashstatus >/dev/null && {
        _service_stop
        sleep 0.3
        clashstatus >/dev/null && {
            _failcat 'Stop failed: Run clashlog to view logs'
            return 1
        }
    }
    _unset_system_proxy
    _okcat 'Proxy environment disabled'
}

clashrestart() {
    clashoff >/dev/null
    clashon
}

function clashproxy() {
    case "$1" in
    -h | --help)
        cat <<EOF

- View system proxy status
  clashproxy

- Enable system proxy
  clashproxy on

- Disable system proxy
  clashproxy off

EOF
        return 0
        ;;
    on)
        clashstatus >&/dev/null || {
            _failcat "$KERNEL_NAME is not running, please run clashon first"
            return 1
        }
        "$BIN_YQ" -i '._custom.system-proxy.enable = true' "$CLASH_CONFIG_MIXIN"
        _set_system_proxy
        _okcat 'System proxy enabled'
        ;;
    off)
        "$BIN_YQ" -i '._custom.system-proxy.enable = false' "$CLASH_CONFIG_MIXIN"
        _unset_system_proxy
        _okcat 'System proxy disabled'
        ;;
    *)
        local system_proxy_enable=$("$BIN_YQ" '._custom.system-proxy.enable' "$CLASH_CONFIG_MIXIN" 2>/dev/null)
        case $system_proxy_enable in
        true)
            _okcat "System proxy: Enabled
$(env | grep -i 'proxy=')"
            ;;
        *)
            _failcat "System proxy: Disabled"
            ;;
        esac
        ;;
    esac
}

function clashstatus() {
    if _use_systemd 2>/dev/null; then
        if systemctl is-active --quiet mihomo 2>/dev/null; then
            pgrep -fa "$BIN_KERNEL" "$@"
            return $?
        fi
    fi
    pgrep -fa "$BIN_KERNEL" "$@"
}

function clashlog() {
    less < "$CLASH_RESOURCES_DIR/mihomo.log" "$@"
}

# Set proxy group selection via Clash API (group_name = select group, proxy_name = node to use)
_clash_api_select_proxy() {
    local group_name="$1"
    local proxy_name="$2"
    _detect_ext_addr
    clashstatus >&/dev/null || clashon >/dev/null
    local secret=$("$BIN_YQ" '.secret // ""' "$CLASH_CONFIG_RUNTIME")
    local encoded_group
    encoded_group=$(printf '%s' "$group_name" | python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.stdin.read().strip(), safe=''))" 2>/dev/null) || \
    encoded_group=$(printf '%s' "$group_name" | sed 's/ /%20/g; s/:/%3A/g')
    local res
    res=$(curl -s -w '\n%{http_code}' -X PUT \
        --noproxy "*" \
        -H "Authorization: Bearer $secret" \
        -H "Content-Type: application/json" \
        -d "$(printf '{"name":"%s"}' "$proxy_name")" \
        "http://${EXT_IP}:${EXT_PORT}/proxies/${encoded_group}")
    local code="${res##*$'\n'}"
    [ "$code" = "204" ] && return 0
    return 1
}

function clashjapan() {
    # Main selector group name (🔰 Node Selection)
    local main_selector="🔰 Node Selection"
    local japan_node="JP.Japan.D"
    if _clash_api_select_proxy "$main_selector" "$japan_node"; then
        _okcat "Switched to Japan node: $japan_node"
    else
        _failcat "Switch failed, please ensure Clash is running and the node exists (clashlog)"
    fi
}

function clashui() {
    _detect_ext_addr
    clashstatus >&/dev/null || clashon >/dev/null
    local query_url='api64.ipify.org' # ifconfig.me
    local public_ip=$(curl -s --noproxy "*" --location --max-time 2 $query_url)
    local public_address="http://${public_ip:-Public}:${EXT_PORT}/ui"

    local local_ip=$EXT_IP
    local local_address="http://${local_ip}:${EXT_PORT}/ui"
    printf "\n"
    printf "╔═══════════════════════════════════════════════╗\n"
    printf "║                %s                  ║\n" "$(_okcat 'Web Dashboard')"
    printf "║═══════════════════════════════════════════════║\n"
    printf "║                                               ║\n"
    printf "║     🔓 Ensure port is open: %-5s             ║\n" "$EXT_PORT"
    printf "║     🏠 Local: %-31s  ║\n" "$local_address"
    printf "║     🌏 Public: %-30s  ║\n" "$public_address"
    printf "║     ☁️  Cloud: %-31s  ║\n" "$URL_CLASH_UI"
    printf "║                                               ║\n"
    printf "╚═══════════════════════════════════════════════╝\n"
    printf "\n"
}

_merge_config() {
    cat "$CLASH_CONFIG_RUNTIME" >"$CLASH_CONFIG_TEMP" 2>/dev/null
    # shellcheck disable=SC2016
    "$BIN_YQ" eval-all '
      ########################################
      #              Load Files              #
      ########################################
      select(fileIndex==0) as $config |
      select(fileIndex==1) as $mixin |
      
      ########################################
      #              Deep Merge              #
      ########################################
      $mixin |= del(._custom) |
      (($config // {}) * $mixin) as $runtime |
      $runtime |
      
      ########################################
      #               Rules                  #
      ########################################
      .rules = (
        ($mixin.rules.prefix // []) +
        ($config.rules // []) +
        ($mixin.rules.suffix // [])
      ) |
      
      ########################################
      #                Proxies               #
      ########################################
      .proxies = (
        ($mixin.proxies.prefix // []) +
        (
          ($config.proxies // []) as $configList |
          ($mixin.proxies.override // []) as $overrideList |
          $configList | map(
            . as $configItem |
            (
              $overrideList[] | select(.name == $configItem.name)
            ) // $configItem
          )
        ) +
        ($mixin.proxies.suffix // [])
      ) |
      
      ########################################
      #             ProxyGroups              #
      ########################################
      .proxy-groups = (
        ($mixin.proxy-groups.prefix // []) +
        (
          ($config.proxy-groups // []) as $configList |
          ($mixin.proxy-groups.override // []) as $overrideList |
          $configList | map(
            . as $configItem |
            (
              $overrideList[] | select(.name == $configItem.name)
            ) // $configItem
          )
        ) +
        ($mixin.proxy-groups.suffix // [])
      )
    ' "$CLASH_CONFIG_BASE" "$CLASH_CONFIG_MIXIN" >"$CLASH_CONFIG_RUNTIME"
    # When run as root (systemd), ensure TUN is enabled in runtime config
    [ "$(id -u)" = "0" ] && "$BIN_YQ" -i '.tun.enable = true' "$CLASH_CONFIG_RUNTIME"
    _valid_config "$CLASH_CONFIG_RUNTIME" || {
        cat "$CLASH_CONFIG_TEMP" >"$CLASH_CONFIG_RUNTIME"
        _error_quit "Validation failed: Please check Mixin configuration"
    }
}

_merge_config_restart() {
    _merge_config
    if _use_systemd; then
        sudo systemctl restart mihomo >/dev/null
    else
        pkill -9 -f "$BIN_KERNEL" >/dev/null
        sleep 0.1
        ( nohup "$BIN_KERNEL" -d "$CLASH_RESOURCES_DIR" -f "$CLASH_CONFIG_RUNTIME" >& "$CLASH_RESOURCES_DIR/mihomo.log" & ) >/dev/null
    fi
    sleep 0.1
}

function clashsecret() {
    case "$1" in
    -h | --help)
        cat <<EOF

- View Web Secret
  clashsecret

- Modify Web Secret
  clashsecret <new_secret>

EOF
        return 0
        ;;
    esac

    case $# in
    0)
        _okcat "Current Secret: $("$BIN_YQ" '.secret // ""' "$CLASH_CONFIG_RUNTIME")"
        ;;
    1)
        "$BIN_YQ" -i ".secret = \"$1\"" "$CLASH_CONFIG_MIXIN" || {
            _failcat "Secret update failed, please try again"
            return 1
        }
        _merge_config_restart
        _okcat "Secret updated successfully, restarted to apply changes"
        ;;
    *)
        _failcat "Secret should not contain spaces or be enclosed in quotes"
        ;;
    esac
}

_tunstatus() {
    local tun_status=$("$BIN_YQ" '.tun.enable' "${CLASH_CONFIG_RUNTIME}")
    case $tun_status in
    true)
        _okcat 'Tun Status: Enabled'
        ;;
    *)
        _failcat 'Tun Status: Disabled'
        ;;
    esac
}
_tunoff() {
    _tunstatus >/dev/null || return 0
    "$BIN_YQ" -i '.tun.enable = false' "$CLASH_CONFIG_MIXIN"
    _merge_config
    if _use_systemd; then
        sudo systemctl stop mihomo 2>/dev/null || true
    else
        sudo pkill -9 -f "$BIN_KERNEL" 2>/dev/null || true
    fi
    clashon >/dev/null
    _okcat "Tun mode disabled"
}
_sudo_restart() {
    if _use_systemd; then
        sudo systemctl stop mihomo 2>/dev/null || true
        sleep 0.3
        sudo systemctl start mihomo
    else
        sudo pkill -9 -f "$BIN_KERNEL" 2>/dev/null || true
        sleep 0.5
        : > "$CLASH_RESOURCES_DIR/mihomo.log"
        # Run as root so TUN works (Antigravity/Go apps ignore proxy; TUN routes all traffic)
        ( sudo nohup "$BIN_KERNEL" -d "$CLASH_RESOURCES_DIR" -f "$CLASH_CONFIG_RUNTIME" >> "$CLASH_RESOURCES_DIR/mihomo.log" 2>&1 & )
    fi
    sleep 0.5
}
_tunon() {
    _tunstatus 2>/dev/null && return 0
    "$BIN_YQ" -i '.tun.enable = true' "$CLASH_CONFIG_MIXIN"
    _merge_config
    _sudo_restart
    sleep 1
    # Only check RECENT log lines (after restart), not old errors
    local log_tail
    log_tail=$(tail -n 80 "$CLASH_RESOURCES_DIR/mihomo.log" 2>/dev/null)
    local fail_msg="Start TUN listening error|unsupported kernel version"
    local ok_msg="Tun adapter listening at|TUN listening iface"
    if echo "$log_tail" | grep -E -m1 -qs "$fail_msg"; then
        [ "$KERNEL_NAME" = 'mihomo' ] && {
            "$BIN_YQ" -i '.tun.auto-redirect = false' "$CLASH_CONFIG_MIXIN"
            _merge_config
            _sudo_restart
            sleep 1
            log_tail=$(tail -n 80 "$CLASH_RESOURCES_DIR/mihomo.log" 2>/dev/null)
        }
        echo "$log_tail" | grep -E -m1 -qs "$ok_msg" || {
            echo "$log_tail" | grep -E -m1 "$fail_msg"
            _tunoff >&/dev/null
            _error_quit 'System kernel version does not support Tun mode'
        }
    fi
    _okcat "Tun mode enabled"
}

function clashtun() {
    case "$1" in
    -h | --help)
        cat <<EOF

- View Tun status
  clashtun

- Enable Tun mode
  clashtun on

- Disable Tun mode
  clashtun off
  
EOF
        return 0
        ;;
    on)
        _tunon
        ;;
    off)
        _tunoff
        ;;
    *)
        _tunstatus
        ;;
    esac
}

function clashmixin() {
    case "$1" in
    -h | --help)
        cat <<EOF

- View Mixin config: $CLASH_CONFIG_MIXIN
  clashmixin

- Edit Mixin config
  clashmixin -e

- View original subscription config: $CLASH_CONFIG_BASE
  clashmixin -c

- View runtime config: $CLASH_CONFIG_RUNTIME
  clashmixin -r

EOF
        return 0
        ;;
    -e)
        vim "$CLASH_CONFIG_MIXIN" && {
            _merge_config_restart && _okcat "Configuration updated successfully, restarted to apply changes"
        }
        ;;
    -r)
        less "$CLASH_CONFIG_RUNTIME"
        ;;
    -c)
        less "$CLASH_CONFIG_BASE"
        ;;
    *)
        less "$CLASH_CONFIG_MIXIN"
        ;;
    esac
}

function clashupgrade() {
    for arg in "$@"; do
        case $arg in
        -h | --help)
            cat <<EOF
Usage:
  clashupgrade [OPTIONS]

Options:
  -v, --verbose       Output kernel upgrade logs
  -r, --release       Upgrade to stable version
  -a, --alpha         Upgrade to alpha version
  -h, --help          Show help information

EOF
            return 0
            ;;
        -v | --verbose)
            local log_flag=true
            ;;
        -r | --release)
            channel="release"
            ;;
        -a | --alpha)
            channel="alpha"
            ;;
        *)
            channel=""
            ;;
        esac
    done

    _detect_ext_addr
    clashstatus >&/dev/null || clashon >/dev/null
    local secret=$("$BIN_YQ" '.secret // ""' "$CLASH_CONFIG_RUNTIME")
    _okcat '⏳' "Requesting kernel upgrade..."
    [ "$log_flag" = true ] && {
        log_cmd=(tail -f -n 0 "$CLASH_RESOURCES_DIR/mihomo.log")
        ("${log_cmd[@]}" &)

    }
    local res=$(
        curl -X POST \
            --silent \
            --noproxy "*" \
            --location \
            -H "Authorization: Bearer $secret" \
            "http://${EXT_IP}:${EXT_PORT}/upgrade?channel=$channel"
    )
    [ "$log_flag" = true ] && pkill -9 -f "${log_cmd[*]}"

    grep '"status":"ok"' <<<"$res" && {
        _okcat "Kernel upgrade successful"
        return 0
    }
    grep 'already using latest version' <<<"$res" && {
        _okcat "Already using the latest version"
        return 0
    }
    _failcat "Kernel upgrade failed, please check network or try again later"
}

function clashsub() {
    case "$1" in
    add)
        shift
        _sub_add "$@"
        ;;
    del)
        shift
        _sub_del "$@"
        ;;
    list | ls | '')
        shift
        _sub_list "$@"
        ;;
    use)
        shift
        _sub_use "$@"
        ;;
    update)
        shift
        _sub_update "$@"
        ;;
    log)
        shift
        _sub_log "$@"
        ;;
    -h | --help | *)
        cat <<EOF
clashsub - Clash Subscription Management Tool

Usage: 
  clashsub COMMAND [OPTIONS]

Commands:
  add <url>       Add subscription
  ls              List subscriptions
  del <id>        Delete subscription
  use <id>        Use subscription
  update [id]     Update subscription
  log             Subscription logs

Options:
  update:
    --auto        Configure auto-update
    --convert     Use subscription conversion
EOF
        ;;
    esac
}
_sub_add() {
    local url=$1
    [ -z "$url" ] && {
        echo -n "$(_okcat '✈️ ' 'Please enter the subscription link to add: ')"
        read -r url
        [ -z "$url" ] && _error_quit "Subscription link cannot be empty"
    }
    _get_url_by_id "$id" >/dev/null && _error_quit "This subscription link already exists"

    _download_config "$CLASH_CONFIG_TEMP" "$url"
    _valid_config "$CLASH_CONFIG_TEMP" || _error_quit "Invalid subscription, please check:
    Original subscription: ${CLASH_CONFIG_TEMP}.raw
    Converted subscription: $CLASH_CONFIG_TEMP
    Conversion log: $BIN_SUBCONVERTER_LOG"

    local id=$("$BIN_YQ" '.profiles // [] | (map(.id) | max) // 0 | . + 1' "$CLASH_PROFILES_META")
    local profile_path="${CLASH_PROFILES_DIR}/${id}.yaml"
    mv "$CLASH_CONFIG_TEMP" "$profile_path"

    "$BIN_YQ" -i "
         .profiles = (.profiles // []) + 
         [{
           \"id\": $id,
           \"path\": \"$profile_path\",
           \"url\": \"$url\"
         }]
    " "$CLASH_PROFILES_META"
    _logging_sub "➕ Added subscription: [$id] $url"
    _okcat '🎉' "Subscription added: [$id] $url"
}
_sub_del() {
    local id=$1
    [ -z "$id" ] && {
        echo -n "$(_okcat '✈️ ' 'Please enter the subscription ID to delete: ')"
        read -r id
        [ -z "$id" ] && _error_quit "Subscription ID cannot be empty"
    }
    local profile_path url
    profile_path=$(_get_path_by_id "$id") || _error_quit "Subscription ID does not exist, please check"
    url=$(_get_url_by_id "$id")
    use=$("$BIN_YQ" '.use // ""' "$CLASH_PROFILES_META")
    [ "$use" = "$id" ] && _error_quit "Delete failed: Subscription $id is in use, please switch subscriptions first"
    /usr/bin/rm -f "$profile_path"
    "$BIN_YQ" -i "del(.profiles[] | select(.id == \"$id\"))" "$CLASH_PROFILES_META"
    _logging_sub "➖ Deleted subscription: [$id] $url"
    _okcat '🎉' "Subscription deleted: [$id] $url"
}
_sub_list() {
    "$BIN_YQ" "$CLASH_PROFILES_META"
}
_sub_use() {
    "$BIN_YQ" -e '.profiles // [] | length == 0' "$CLASH_PROFILES_META" >&/dev/null &&
        _error_quit "No subscriptions available, please add one first"
    local id=$1
    [ -z "$id" ] && {
        clashsub ls
        echo -n "$(_okcat '✈️ ' 'Please enter the subscription ID to use: ')"
        read -r id
        [ -z "$id" ] && _error_quit "Subscription ID cannot be empty"
    }
    local profile_path url
    profile_path=$(_get_path_by_id "$id") || _error_quit "Subscription ID does not exist, please check"
    url=$(_get_url_by_id "$id")
    cat "$profile_path" >"$CLASH_CONFIG_BASE"
    _merge_config_restart
    "$BIN_YQ" -i ".use = $id" "$CLASH_PROFILES_META"
    _logging_sub "🔥 Subscription switched to: [$id] $url"
    _okcat '🔥' 'Subscription applied'
}
_get_path_by_id() {
    "$BIN_YQ" -e ".profiles[] | select(.id == \"$1\") | .path" "$CLASH_PROFILES_META" 2>/dev/null
}
_get_url_by_id() {
    "$BIN_YQ" -e ".profiles[] | select(.id == \"$1\") | .url" "$CLASH_PROFILES_META" 2>/dev/null
}
_sub_update() {
    local arg is_convert
    for arg in "$@"; do
        case $arg in
        --auto)
            command -v crontab >/dev/null || _error_quit "crontab command not found, please install cron service first"
            crontab -l | grep -qs 'clashsub update' || {
                (
                    crontab -l 2>/dev/null
                    echo "0 0 */2 * * $SHELL -i -c 'clashsub update'"
                ) | crontab -
            }
            _okcat "Auto-update subscription scheduled"
            return 0
            ;;
        --convert)
            is_convert=true
            shift
            ;;
        esac
    done
    local id=$1
    [ -z "$id" ] && id=$("$BIN_YQ" '.use // 1' "$CLASH_PROFILES_META")
    local url profile_path
    url=$(_get_url_by_id "$id") || _error_quit "Subscription ID does not exist, please check"
    profile_path=$(_get_path_by_id "$id")
    _okcat "✈️ " "Updating subscription: [$id] $url"

    [ "$is_convert" = true ] && {
        _download_convert_config "$CLASH_CONFIG_TEMP" "$url"
    }
    [ "$is_convert" != true ] && {
        _download_config "$CLASH_CONFIG_TEMP" "$url"
    }
    _valid_config "$CLASH_CONFIG_TEMP" || {
        _logging_sub "❌ Subscription update failed: [$id] $url"
        _error_quit "Invalid subscription, please check:
    Original subscription: ${CLASH_CONFIG_TEMP}.raw
    Converted subscription: $CLASH_CONFIG_TEMP
    Conversion log: $BIN_SUBCONVERTER_LOG"
    }
    _logging_sub "✅ Subscription update successful: [$id] $url"
    cat "$CLASH_CONFIG_TEMP" >"$profile_path"
    use=$("$BIN_YQ" '.use // ""' "$CLASH_PROFILES_META")
    [ "$use" = "$id" ] && clashsub use "$use" && return
    _okcat 'Subscription updated'
}
_logging_sub() {
    echo "$(date +"%Y-%m-%d %H:%M:%S") $1" >>"${CLASH_PROFILES_LOG}"
}
_sub_log() {
    tail <"${CLASH_PROFILES_LOG}" "$@"
}

function clashctl() {
    case "$1" in
    on)
        shift
        clashon
        ;;
    off)
        shift
        clashoff
        ;;
    ui)
        shift
        clashui
        ;;
    status)
        shift
        clashstatus "$@"
        ;;
    log)
        shift
        clashlog "$@"
        ;;
    proxy)
        shift
        clashproxy "$@"
        ;;
    tun)
        shift
        clashtun "$@"
        ;;
    mixin)
        shift
        clashmixin "$@"
        ;;
    secret)
        shift
        clashsecret "$@"
        ;;
    sub)
        shift
        clashsub "$@"
        ;;
    upgrade)
        shift
        clashupgrade "$@"
        ;;
    japan)
        shift
        clashjapan "$@"
        ;;
    *)
        (($#)) && shift
        clashhelp "$@"
        ;;
    esac
}

clashhelp() {
    cat <<EOF
    
Usage: 
  clashctl COMMAND [OPTIONS]

Commands:
  on                    Enable proxy
  off                   Disable proxy
  proxy                 System proxy
  status                Kernel status
  ui                    Dashboard address
  sub                   Subscription management
  log                   Kernel logs
  tun                   Tun mode
  japan                 Switch to Japan node (JP.Japan.D)
  mixin                 Mixin config
  secret                Web secret
  upgrade               Upgrade kernel

Global Options:
  -h, --help            Show help information

For more help on how to use clashctl, head to https://github.com/nelvko/clash-for-linux-install
EOF
}
