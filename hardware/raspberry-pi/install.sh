#!/bin/bash
# Turn a Raspberry Pi into a Just In Case library hotspot.
#
# Tested setup: Raspberry Pi OS (Bookworm or newer, which uses NetworkManager)
# on a Pi Zero 2 W, Pi 3, Pi 4 or Pi 5. Run from inside the repository:
#
#   bash hardware/raspberry-pi/install.sh               # open network
#   SSID=MyLibrary PASSWORD=secret123 bash hardware/raspberry-pi/install.sh
#
# What it does:
#   1. builds the library (python3 tools/build.py, standard library only)
#   2. creates a WiFi hotspot with NetworkManager
#   3. points every DNS name at the Pi, so phones open the library automatically
#   4. installs a service that serves the library on port 80 at every boot
#
# Note: the Pi's WiFi becomes a hotspot. If you are connected to the Pi over
# WiFi, you will lose that connection. Use Ethernet, a keyboard and screen, or
# be ready to reconnect to the new hotspot.

set -euo pipefail

SSID="${SSID:-JustInCase-Library}"
PASSWORD="${PASSWORD:-}"
IFACE="${IFACE:-wlan0}"
ADDRESS="10.42.0.1"
REPO="$(cd "$(dirname "$0")/../.." && pwd)"

if ! command -v nmcli >/dev/null; then
  echo "NetworkManager (nmcli) not found. Use Raspberry Pi OS Bookworm or newer." >&2
  exit 1
fi

echo "1/4 Building the library in $REPO ..."
python3 "$REPO/tools/build.py" --no-esp32

echo "2/4 Creating hotspot '$SSID' on $IFACE ..."
sudo nmcli connection delete JustInCase >/dev/null 2>&1 || true
sudo nmcli connection add type wifi ifname "$IFACE" con-name JustInCase autoconnect yes ssid "$SSID" \
  802-11-wireless.mode ap 802-11-wireless.band bg \
  ipv4.method shared ipv4.addresses "$ADDRESS/24" ipv6.method disabled
if [ -n "$PASSWORD" ]; then
  if [ "${#PASSWORD}" -lt 8 ]; then
    echo "PASSWORD must be at least 8 characters." >&2
    exit 1
  fi
  sudo nmcli connection modify JustInCase wifi-sec.key-mgmt wpa-psk wifi-sec.psk "$PASSWORD"
fi

echo "3/4 Answering every DNS name with $ADDRESS (captive portal) ..."
sudo mkdir -p /etc/NetworkManager/dnsmasq-shared.d
echo "address=/#/$ADDRESS" | sudo tee /etc/NetworkManager/dnsmasq-shared.d/just-in-case.conf >/dev/null

echo "4/4 Installing the web server service ..."
sed -e "s|@REPO@|$REPO|g" -e "s|@USER@|$(id -un)|g" "$REPO/hardware/raspberry-pi/just-in-case.service" \
  | sudo tee /etc/systemd/system/just-in-case.service >/dev/null
sudo systemctl daemon-reload
sudo systemctl enable --now just-in-case.service

sudo nmcli connection up JustInCase

echo
echo "Done. Join WiFi '$SSID' and open http://$ADDRESS/"
echo "To undo: sudo nmcli connection delete JustInCase && sudo systemctl disable --now just-in-case"
