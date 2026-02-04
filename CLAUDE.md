# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a bash-based installation and management framework for deploying Clash/Mihomo proxy kernels on Linux systems. It provides one-click installation with automatic dependency management, service configuration, and system proxy integration.

## Commands

### Installation
```bash
bash install.sh                              # Interactive installation
bash install.sh mihomo <subscription-url>    # Install with specific kernel and subscription
```

### Uninstallation
```bash
bash uninstall.sh
```

### Linting
```bash
shellcheck scripts/*.sh scripts/**/*.sh
```

## Architecture

### Entry Points
- `install.sh` - Main installation entry point, sources other scripts
- `uninstall.sh` - Complete removal script

### Core Scripts
- `scripts/preflight.sh` - Installation/setup logic: validates environment, detects system architecture and init system, downloads binaries, installs services
- `scripts/cmd/clashctl.sh` - User-facing command interface (clashon, clashoff, clashsub, clashmixin, clashtun, etc.)
- `scripts/cmd/common.sh` - Shared utility functions for port detection, YAML manipulation, config merging, subscription handling

### Service Templates
`scripts/init/` contains service templates for different init systems:
- `systemd.sh`, `SysVinit.sh`, `OpenRC.sh`, `runit.sh`
- Templates use placeholders replaced with `sed` at install time

### Configuration Files
- `.env` - Installation variables (kernel name, paths, versions, URLs)
- `resources/mixin.yaml` - User configuration overrides, deep-merged with subscription config
- `resources/runtime.yaml` - Generated merged config used by kernel at runtime
- `resources/profiles.yaml` - Subscription metadata

### Key Patterns

**Environment Variable Configuration**: All configurable values are in `.env` and sourced at script start. Never hardcode paths.

**Multi-Init System Abstraction**: Service commands (`service_start`, `service_stop`, etc.) are set as array variables based on detected init system.

**YAML Configuration Merging**: Uses `yq` tool. Base config (subscription) + mixin config (user customizations) → runtime config. Supports prefix/suffix/override patterns for rules, proxies, proxy-groups.

**Port Conflict Resolution**: `_is_port_used()` checks availability, `_get_random_port()` generates available ports recursively.

### External Tools
Downloaded to `resources/zip/`:
- `mihomo` or `clash` - Proxy kernel
- `yq` - YAML CLI tool
- `subconverter` - Subscription conversion service

## Code Style

- 2-space indentation (see `.editorconfig`)
- LF line endings
- ShellCheck validated with disabled rules: SC1091, SC2155, SC2296, SC2153 (see `.shellcheckrc`)
