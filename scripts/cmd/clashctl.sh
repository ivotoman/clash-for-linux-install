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

function clashon() {
    clashstatus >&/dev/null || {
        _detect_proxy_port
        placeholder_start
        clashstatus >/dev/null || {
            _failcat 'Start failed: run clashlog to view logs'
            return 1
        }
    }
    clashproxy >/dev/null && _set_system_proxy
    _okcat 'Proxy environment enabled'
}

watch_proxy() {
    [ -z "$http_proxy" ] && {
        # [[ "$0" == -* ]] && { # 登录式shell
        [[ $- == *i* ]] && { # 交互式shell
            placeholder_watch_proxy
        }
    }
}

function clashoff() {
    clashstatus >/dev/null && {
        placeholder_stop >/dev/null || {
            _failcat 'Stop failed: run clashlog to view logs'
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

- Check system proxy status
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
            _failcat "$KERNEL_NAME is not running, run clashon first"
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
            _okcat "System proxy: on
$(env | grep -i 'proxy=')"
            ;;
        *)
            _failcat "System proxy: off"
            ;;
        esac
        ;;
    esac
}

function clashstatus() {
    placeholder_status "$@"
    placeholder_is_active
}

function clashlog() {
    placeholder_log "$@"
}

function clashui() {
    _detect_ext_addr
    clashstatus >&/dev/null || clashon >/dev/null
    local query_url='api64.ipify.org' # ifconfig.me
    local public_ip=$(curl -s --noproxy "*" --location --max-time 2 $query_url)
    local public_address="http://${public_ip:-public}:${EXT_PORT}/ui"

    local local_ip=$EXT_IP
    local local_address="http://${local_ip}:${EXT_PORT}/ui"
    printf "\n"
    printf "╔═══════════════════════════════════════════════╗\n"
    printf "║                %s                  ║\n" "$(_okcat 'Web Dashboard')"
    printf "║═══════════════════════════════════════════════║\n"
    printf "║                                               ║\n"
    printf "║     🔓 Allow port: %-5s                       ║\n" "$EXT_PORT"
    printf "║     🏠 LAN: %-31s  ║\n" "$local_address"
    printf "║     🌏 Public: %-31s  ║\n" "$public_address"
    printf "║     ☁️  Shared: %-31s  ║\n" "$URL_CLASH_UI"
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
    _valid_config "$CLASH_CONFIG_RUNTIME" || {
        cat "$CLASH_CONFIG_TEMP" >"$CLASH_CONFIG_RUNTIME"
        _error_quit "Verification failed: please check Mixin config"
    }
}

_merge_config_restart() {
    _merge_config
    placeholder_stop >/dev/null
    sleep 0.1
    placeholder_start >/dev/null
    sleep 0.1
}

function clashsecret() {
    case "$1" in
    -h | --help)
        cat <<EOF

- View Web secret
  clashsecret

- Change Web secret
  clashsecret <new_secret>

EOF
        return 0
        ;;
    esac

    case $# in
    0)
        _okcat "Current secret: $("$BIN_YQ" '.secret // ""' "$CLASH_CONFIG_RUNTIME")"
        ;;
    1)
        "$BIN_YQ" -i ".secret = \"$1\"" "$CLASH_CONFIG_MIXIN" || {
            _failcat "Secret update failed, please try again"
            return 1
        }
        _merge_config_restart
        _okcat "Secret updated, restart applied"
        ;;
    *)
        _failcat "Secret must not contain spaces or be quoted"
        ;;
    esac
}

_tunstatus() {
    local tun_status=$("$BIN_YQ" '.tun.enable' "${CLASH_CONFIG_RUNTIME}")
    case $tun_status in
    true)
        _okcat 'Tun status: enabled'
        ;;
    *)
        _failcat 'Tun status: disabled'
        ;;
    esac
}
_tunoff() {
    _tunstatus >/dev/null || return 0
    "$BIN_YQ" -i '.tun.enable = false' "$CLASH_CONFIG_MIXIN"
    _merge_config
    sudo placeholder_stop
    clashon >/dev/null
    _okcat "Tun mode disabled"
}
_sudo_restart() {
    sudo placeholder_stop
    sleep 0.3
    placeholder_sudo_start
    sleep 0.3
}
_tunon() {
    _tunstatus 2>/dev/null && return 0
    "$BIN_YQ" -i '.tun.enable = true' "$CLASH_CONFIG_MIXIN"
    _merge_config
    _sudo_restart
    local fail_msg="Start TUN listening error|unsupported kernel version"
    local ok_msg="Tun adapter listening at|TUN listening iface"
    clashlog | grep -E -m1 -qs "$fail_msg" && {
        [ "$KERNEL_NAME" = 'mihomo' ] && {
            "$BIN_YQ" -i '.tun.auto-redirect = false' "$CLASH_CONFIG_MIXIN"
            _merge_config
            _sudo_restart
        }
        clashlog | grep -E -m1 -qs "$ok_msg" || {
            clashlog | grep -E -m1 "$fail_msg"
            _tunoff >&/dev/null
            _error_quit 'System kernel does not support Tun mode'
        }
    }
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

- View raw subscription config: $CLASH_CONFIG_BASE
  clashmixin -c

- View runtime config: $CLASH_CONFIG_RUNTIME
  clashmixin -r

EOF
        return 0
        ;;
    -e)
        vim "$CLASH_CONFIG_MIXIN" && {
            _merge_config_restart && _okcat "Config updated, restart applied"
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
  -v, --verbose       Output kernel upgrade log
  -r, --release       Upgrade to stable release
  -a, --alpha         Upgrade to alpha
  -h, --help          Show help

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
        log_cmd=(placeholder_follow_log)
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
        _okcat "Kernel upgraded successfully"
        return 0
    }
    grep 'already using latest version' <<<"$res" && {
        _okcat "Already on latest version"
        return 0
    }
    _failcat "Kernel upgrade failed, check network or retry later"
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
clashsub - Clash subscription manager

Usage: 
  clashsub COMMAND [OPTIONS]

Commands:
  add <url>       Add subscription
  ls              List subscriptions
  del <id>        Delete subscription
  use <id>        Use subscription
  update [id]     Update subscription
  log             Subscription log

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
        echo -n "$(_okcat '✈️ ' 'Enter subscription URL to add: ')"
        read -r url
        [ -z "$url" ] && _error_quit "Subscription URL cannot be empty"
    }
    _get_url_by_id "$id" >/dev/null && _error_quit "Subscription URL already exists"

    _download_config "$CLASH_CONFIG_TEMP" "$url"
    _valid_config "$CLASH_CONFIG_TEMP" || _error_quit "Invalid subscription, check:
    Raw: ${CLASH_CONFIG_TEMP}.raw
    Converted: $CLASH_CONFIG_TEMP
    Log: $BIN_SUBCONVERTER_LOG"

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
    _logging_sub "➕ Subscription added: [$id] $url"
    _okcat '🎉' "Subscription added: [$id] $url"
}
_sub_del() {
    local id=$1
    [ -z "$id" ] && {
        echo -n "$(_okcat '✈️ ' 'Enter subscription id to delete: ')"
        read -r id
        [ -z "$id" ] && _error_quit "Subscription id cannot be empty"
    }
    local profile_path url
    profile_path=$(_get_path_by_id "$id") || _error_quit "Subscription id not found, check list"
    url=$(_get_url_by_id "$id")
    use=$("$BIN_YQ" '.use // ""' "$CLASH_PROFILES_META")
    [ "$use" = "$id" ] && _error_quit "Delete failed: subscription $id is in use, switch first"
    /usr/bin/rm -f "$profile_path"
    "$BIN_YQ" -i "del(.profiles[] | select(.id == \"$id\"))" "$CLASH_PROFILES_META"
    _logging_sub "➖ Subscription deleted: [$id] $url"
    _okcat '🎉' "Subscription deleted: [$id] $url"
}
_sub_list() {
    "$BIN_YQ" "$CLASH_PROFILES_META"
}
_sub_use() {
    "$BIN_YQ" -e '.profiles // [] | length == 0' "$CLASH_PROFILES_META" >&/dev/null &&
        _error_quit "No subscriptions available, add one first"
    local id=$1
    [ -z "$id" ] && {
        clashsub ls
        echo -n "$(_okcat '✈️ ' 'Enter subscription id to use: ')"
        read -r id
        [ -z "$id" ] && _error_quit "Subscription id cannot be empty"
    }
    local profile_path url
    profile_path=$(_get_path_by_id "$id") || _error_quit "Subscription id not found, check list"
    url=$(_get_url_by_id "$id")
    cat "$profile_path" >"$CLASH_CONFIG_BASE"
    _merge_config_restart
    "$BIN_YQ" -i ".use = $id" "$CLASH_PROFILES_META"
    _logging_sub "🔥 Subscription switched to: [$id] $url"
    _okcat '🔥' 'Subscription active'
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
            command -v crontab >/dev/null || _error_quit "crontab not found, install cron first"
            crontab -l | grep -qs 'clashsub update' || {
                (
                    crontab -l 2>/dev/null
                    echo "0 0 */2 * * $SHELL -i -c 'clashsub update'"
                ) | crontab -
            }
            _okcat "Scheduled subscription update enabled"
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
    url=$(_get_url_by_id "$id") || _error_quit "Subscription id not found, check list"
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
        _error_quit "Invalid subscription, check:
    Raw: ${CLASH_CONFIG_TEMP}.raw
    Converted: $CLASH_CONFIG_TEMP
    Log: $BIN_SUBCONVERTER_LOG"
    }
    _logging_sub "✅ Subscription updated: [$id] $url"
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
  ui                    Dashboard URL
  sub                   Subscription management
  log                   Kernel log
  tun                   Tun mode
  mixin                 Mixin config
  secret                Web secret
  upgrade               Upgrade kernel

Global Options:
  -h, --help            Show help

For more help, see https://github.com/nelvko/clash-for-linux-install
EOF
}
