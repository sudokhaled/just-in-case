# ESP32 / ESP8266 library hotspot

A board about the size of a thumb, costing $2–6 and running on a USB power bank, becomes a WiFi hotspot named **JustInCase-Library**. Any phone, tablet or laptop that joins it gets the whole library in its browser. The device needs no internet, no app and no SIM card. Visitors can also **save the whole library onto their own phone** from the front page, so each copy spreads further.

```
 [power bank] --USB--> [ESP32 board] ~~~ WiFi ~~~> phones, tablets, laptops
   10,000 mAh          0.3-0.6 W                  up to 8-10 at once
```

## What you need

| Item | Notes | Price (2026, approx.) |
|---|---|---|
| ESP32 board with **4 MB flash** | Any of: ESP32-C3 SuperMini (smallest), ESP32 DevKit, ESP32-S3, or an ESP8266 D1 mini | $2–8 |
| USB cable | Must carry data, not only charge | – |
| A computer (once) | To upload the firmware and files. Windows, macOS or Linux | – |
| Power bank or USB charger | Any 5 V USB source | – |
| Optional: microSD card module + card | ESP32 only. For future libraries bigger than the flash | $1–3 |

The full English library fits in the board's internal flash. You don't need an SD card.

## Easiest: install from your browser (2 minutes)

1. On a computer, open the **[installer page](https://sudokhaled.github.io/just-in-case/flash/)** in **Chrome or Edge**.
2. Plug in the ESP32 board with a USB data cable.
3. Click **Install**, choose the board's port, and allow erasing the board.
4. When it is done, power the board from a power bank and join **JustInCase-Library** on a phone.

This works for ESP32, ESP32-C3 and ESP32-S3 boards with 4 MB of flash or more. The images use the "No OTA" layout, which gives the library about 1.9 MB of space. The release also has complete flash images (`just-in-case-esp32c3.bin` and the others) for `esptool.py write_flash 0x0 <file>`. For ESP8266 boards, for custom settings, or to build everything yourself, follow the steps below.

To rebuild the installer images yourself: `python3 tools/build.py`, then `python3 hardware/esp32/build_firmware.py dist/site/flash` (needs `arduino-cli` with the esp32 board package).

## Boards with less space

Boards with about 0.5 MB of file space, such as an ESP-01 (ESP8266 with 1 MB flash), get the small-board edition: the critical articles in full, every other article as its warnings and quick steps, and one page per topic (fewer files waste less space). `python3 tools/build.py` writes it to `dist/esp-small/`. Copy those files into `hardware/esp32/JustInCase/data/` before uploading, and choose the largest file system option your board offers (for example "1MB (FS:512KB OTA:~246KB)").

## Step 1: Build the library files

In the repository folder, run:

```
python3 tools/build.py
```

This fills `hardware/esp32/JustInCase/data/` with compressed pages, and prints how much flash they will use.

## Step 2: Upload, with the Arduino IDE (easiest)

1. Install the [Arduino IDE 2](https://www.arduino.cc/en/software).
2. Add board support. Open **File > Preferences > Additional boards manager URLs** and add:
   - ESP32: `https://espressif.github.io/arduino-esp32/package_esp32_index.json`
   - ESP8266: `https://arduino.esp8266.com/stable/package_esp8266com_index.json`

   Then open **Tools > Board > Boards Manager** and install **esp32** (by Espressif) or **esp8266**.
3. Install the file upload plugin: download the `.vsix` file from [arduino-littlefs-upload](https://github.com/earlephilhower/arduino-littlefs-upload/releases) and put it in `~/.arduinoIDE/plugins/` (on Windows, `C:\Users\<you>\.arduinoIDE\plugins\`). Restart the IDE.
4. Open `hardware/esp32/JustInCase/JustInCase.ino`.
5. Under **Tools**, choose:
   - **Board:** your board, for example "ESP32 Dev Module", "ESP32C3 Dev Module", "ESP32S3 Dev Module" or "LOLIN(WEMOS) D1 R2 & mini".
   - **Partition Scheme** (ESP32): "No OTA (2MB APP/2MB SPIFFS)". It gives the library about 1.9 MB instead of 1.4 MB. The hotspot never updates itself over the air, so nothing is lost.
   - **Flash Size** (ESP8266): "4MB (FS:2MB OTA:~1019KB)".
   - **USB CDC On Boot** (ESP32-C3/S3 with a USB-C port): "Enabled", to see messages.
   - **Port:** the board's USB port.
6. Click **Upload** (the arrow) to upload the firmware.
7. Press **Ctrl+Shift+P** (Cmd+Shift+P on a Mac), type **Upload LittleFS**, and press Enter. This uploads the `data` folder. Close the Serial Monitor first, or the upload fails.

## Step 2 (alternative): Upload with PlatformIO

```
cd hardware/esp32
pio run -e esp32 -t upload      # or esp32-c3, esp32-s3, esp8266
pio run -e esp32 -t uploadfs
```

## Step 3: Use it

1. Power the board from any USB power bank or charger.
2. On a phone, open WiFi settings and join **JustInCase-Library** (open network, no password).
3. The library opens by itself on most phones. If it doesn't, open a browser and go to **http://192.168.4.1**.
4. If the phone says "No internet connection", choose **Stay connected** or **Use this network anyway**, and turn off mobile data.

> [!TIP]
> Type an address starting with `http://`, not `https://`. A secure (https) address can't be redirected to the library, so the browser shows an error instead.

## Settings

Change these at the top of `JustInCase.ino`:

| Setting | Default | What it does |
|---|---|---|
| `AP_SSID` | `JustInCase-Library` | The network name people see. |
| `AP_PASSWORD` | empty (open) | Set 8+ characters to require a password. |
| `LOW_POWER` | `1` | Lower WiFi power and CPU speed: about 30% less power, range about 20–30 m (65–100 ft). Set `0` for maximum range. It also fixes unstable WiFi on many tiny ESP32-C3 SuperMini boards. |
| `USE_SD_CARD` | `0` | `1` = read files from a microSD card (ESP32 only). Copy the contents of the `data` folder to the root of a FAT32 card. |
| `AP_MAX_CLIENTS` | `8` | How many devices can join at once (ESP32 up to 10, ESP8266 up to 8). |

## Power and battery life

| Power source | Approximate runtime |
|---|---|
| 10,000 mAh power bank | 1.5–3 days, all day and night |
| 20,000 mAh power bank | 3–6 days |
| One 18650 cell (3,000 mAh) with a USB boost board | about 12–20 hours |
| 5–10 W USB solar panel | All day in sun. Add a power bank for nights |

These are estimates for an ESP32 hotspot drawing 0.3–0.6 W. ESP32-C3 boards use the least power.

> [!WARNING]
> **Many power banks switch off when the current is very low.** If the hotspot disappears after 30 seconds or a few minutes, your power bank thinks nothing is connected. Fixes: use the power bank's "low current" or "always on" mode (often enabled by pressing the button twice), try another power bank, use a phone charger, or add a small load such as a USB LED light.

Ways to save power:

- Run it only when people need it, for example two hours in the morning and two in the evening at a shelter.
- Keep `LOW_POWER` at `1`.
- Use an ESP32-C3 board.

## Check that it works

Open the Serial Monitor at 115200 baud. After a reset you should see:

```
Just In Case library hotspot
Join WiFi "JustInCase-Library" and open http://192.168.4.1
```

If the page says "the library files are missing", repeat the **Upload LittleFS** step.

## How it works

- The board runs a WiFi access point, a tiny DNS server that answers every name with its own address, and a web server.
- Phones check for internet by loading a known page. The board redirects that check to the library, so the phone shows the library as a "sign-in page".
- Pages are stored gzip-compressed and sent to the browser still compressed. Every browser unpacks gzip. The board never decompresses anything, so it needs very little memory.
- Files are sent in 1 KB pieces, so even the smallest boards can serve them.
