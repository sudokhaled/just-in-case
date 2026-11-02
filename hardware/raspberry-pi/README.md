# Raspberry Pi library hotspot

A Raspberry Pi becomes a WiFi hotspot named **JustInCase-Library**. Phones that join it see the library automatically. Compared with the ESP32 version, a Pi can also **rebuild the library itself**, hold many languages and future large additions (maps, audio), and serve more people at once.

| Model | Power (hotspot, idle to busy) | 10,000 mAh power bank |
|---|---|---|
| Pi Zero 2 W (recommended) | about 0.6–1.5 W | about 1–2 days |
| Pi Zero W | about 0.5–1.2 W | about 1–2.5 days |
| Pi 3 / 4 / 5 | 2–6 W | hours, not days |

These are estimates. Disabling HDMI, Bluetooth and LEDs lowers them (see below).

## Install (10 minutes)

1. Flash **Raspberry Pi OS Lite (Bookworm or newer)** to a microSD card with Raspberry Pi Imager. In the Imager settings, set a user name and password, and enable SSH if you want to work over the network.
2. Boot the Pi with internet access (Ethernet, or WiFi for this first step only).
3. Get the library:

   ```
   sudo apt install -y git
   git clone https://github.com/sudokhaled/just-in-case.git
   cd just-in-case
   ```

   No internet? Copy the repository folder onto the card or a USB stick from another computer instead.
4. Run the installer:

   ```
   bash hardware/raspberry-pi/install.sh
   ```

   For a password-protected network: `SSID=MyLibrary PASSWORD=atleast8chars bash hardware/raspberry-pi/install.sh`

5. On a phone, join **JustInCase-Library**. The library opens by itself, or go to **http://10.42.0.1**.

> [!WARNING]
> The installer turns the Pi's WiFi into a hotspot. If you are connected to the Pi over WiFi, that connection drops. Use Ethernet, a screen and keyboard, or reconnect through the new hotspot (SSH to `10.42.0.1`).

## Make it survive power cuts

A Pi that loses power while writing to its SD card can corrupt the card. A library device will lose power often, so make the card read-only:

```
sudo raspi-config     # Performance Options > Overlay File System > Enable
```

To update the library later, disable the overlay, `git pull`, run `python3 tools/build.py`, and enable the overlay again.

## Save power

Add to `/boot/firmware/config.txt`, then reboot:

```
dtoverlay=disable-bt
dtparam=act_led_trigger=none
dtparam=act_led_activelow=on
```

- Run headless: no screen, keyboard or mouse plugged in.
- Use a Pi Zero 2 W rather than a Pi 4 or 5.

## Update the library

```
cd just-in-case
git pull                      # if you have internet
python3 tools/build.py        # rebuild; no extra software needed
```

The service serves `dist/site/`, so updates appear immediately.

## Use it without a hotspot

On a home network, run the server on any port and open `http://<pi-address>:8080/`:

```
python3 hardware/raspberry-pi/serve.py --port 8080
```

## Undo everything

```
sudo nmcli connection delete JustInCase
sudo rm /etc/NetworkManager/dnsmasq-shared.d/just-in-case.conf
sudo systemctl disable --now just-in-case
sudo rm /etc/systemd/system/just-in-case.service
```
