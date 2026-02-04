#!/bin/bash
# Build the .deb package for Clash VPN Manager

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PKG_DIR="$SCRIPT_DIR/debian-pkg/clash-vpn-manager_1.0.0"
VERSION="1.0.0"

echo "Building Clash VPN Manager v$VERSION..."

# Copy latest source files
cp "$SCRIPT_DIR"/{application.py,window.py,clash_api.py,config_reader.py,service_manager.py,quota_parser.py,tray_helper.py} \
   "$PKG_DIR/opt/clash-vpn-manager/"

# Ensure proper permissions
chmod 755 "$PKG_DIR/opt/clash-vpn-manager/clash-vpn-manager"
chmod 644 "$PKG_DIR/opt/clash-vpn-manager"/*.py
chmod 644 "$PKG_DIR/usr/share/applications/clash-vpn-manager.desktop"
chmod 644 "$PKG_DIR/usr/share/icons/hicolor/scalable/apps/clash-vpn-manager.svg"

# Build package
cd "$SCRIPT_DIR/debian-pkg"
dpkg-deb --build "clash-vpn-manager_$VERSION"

# Copy to gui folder
cp "clash-vpn-manager_$VERSION.deb" "$SCRIPT_DIR/"

echo ""
echo "Package built: $SCRIPT_DIR/clash-vpn-manager_$VERSION.deb"
echo ""
echo "Install with:"
echo "  sudo dpkg -i $SCRIPT_DIR/clash-vpn-manager_$VERSION.deb"
echo "  sudo apt-get install -f  # if dependencies are missing"
