#!/usr/bin/env python3
"""Build ready-to-flash library images for ESP32 boards, plus a browser installer page.

Each image holds the firmware AND the library files, so one file flashed at
address 0 gives a working hotspot. The installer page uses ESP Web Tools: plug a
board into a computer, open the page in Chrome or Edge, click Install.

    python3 tools/build.py
    python3 hardware/esp32/build_firmware.py dist/site/flash

Needs arduino-cli with the esp32 board package (for the compiler and mklittlefs).
Set ARDUINO_CLI to use a different command, for example
ARDUINO_CLI="arduino-cli --config-file my.yaml".
"""

import json
import os
import shlex
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKETCH = HERE / "JustInCase"
DATA = SKETCH / "data"


def data_size():
    return sum(p.stat().st_size for p in DATA.rglob("*") if p.is_file())

FLASH_SIZE = 0x400000
# "No OTA" layout: the hotspot never updates itself over the air, so the second
# app slot becomes file space (about 1.9 MB instead of 1.4 MB).
PARTITIONS = "PartitionScheme=no_ota"
CHIPS = {  # board id: ESP Web Tools chip family
    "esp32": "ESP32",
    "esp32c3": "ESP32-C3",
    "esp32s3": "ESP32-S3",
}
WEB_TOOLS = "https://unpkg.com/esp-web-tools@10.4.0/dist/web/install-button.js?module"

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Install the library hotspot - Just In Case</title>
<link rel="stylesheet" href="../style.css">
<script type="module" src="%(web_tools)s"></script>
</head>
<body>
<nav class="bar"><a href="../index.html">Just In Case</a></nav>
<main>
<h1>Turn an ESP32 board into a library hotspot</h1>
<p>A $2-8 ESP32 board on a USB power bank becomes a WiFi network called <strong>JustInCase-Library</strong>. Every phone that joins it can read and save the whole library, with no internet. This page installs everything in about 2 minutes. No programming tools needed.</p>
<ol>
<li>Use <strong>Chrome or Edge on a computer</strong> (not a phone).</li>
<li>Plug the ESP32 board into the computer with a USB cable that carries data, not only power.</li>
<li>Click <strong>Install</strong> below, pick the board's port, and confirm. Allow erasing the board.</li>
<li>Wait until it says it is done. Then power the board from any USB power bank or charger.</li>
<li>On a phone, join the WiFi network <strong>JustInCase-Library</strong>. The library opens by itself, or go to <strong>http://192.168.4.1</strong>.</li>
</ol>
<p><esp-web-install-button manifest="manifest.json">
<button slot="activate" style="font-size:1.2rem;padding:.7rem 1.4rem">Install</button>
<span slot="unsupported">This browser cannot talk to USB devices. Use Chrome or Edge on a computer.</span>
<span slot="not-allowed">This page must be opened over https.</span>
</esp-web-install-button></p>
<h2>Which boards work?</h2>
<ul>
<li>ESP32, ESP32-C3 (including the tiny "SuperMini") and ESP32-S3 boards with <strong>4 MB of flash or more</strong>.</li>
<li>ESP8266 boards: use the Arduino guide in the repository (hardware/esp32/README.md).</li>
<li>If the board is not found, install the USB driver for its USB chip (CP210x or CH340), or hold the BOOT button while clicking Install.</li>
</ul>
<h2>Without this page</h2>
<p>Each image is a complete 4 MB flash image. Write it at address 0 with any ESP flashing tool, for example: <code>esptool.py write_flash 0x0 just-in-case-esp32c3.bin</code></p>
<p class="meta">Library edition %(version)s. Firmware and installer: MIT license. Library content: CC BY-SA 4.0.</p>
</main>
</body>
</html>
"""


def run(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit("Failed: %s\n%s%s" % (" ".join(cmd), result.stdout[-3000:], result.stderr[-3000:]))
    return result.stdout


def find_mklittlefs(cli):
    if os.environ.get("MKLITTLEFS"):
        return os.environ["MKLITTLEFS"]
    data = run(cli + ["config", "get", "directories.data"]).strip()
    found = sorted((Path(data) / "packages" / "esp32" / "tools").glob("mklittlefs/*/mklittlefs"))
    if not found:
        sys.exit("mklittlefs not found. Install the esp32 board package: arduino-cli core install esp32:esp32")
    return str(found[-1])


def file_system_partition(image):
    """Offset and size of the 'spiffs' data partition, read from the image's partition table."""
    for i in range(0x8000, 0x8C00, 32):
        entry = image[i:i + 32]
        if entry[:2] != b"\xaa\x50":
            break
        offset, size = struct.unpack("<II", entry[4:12])
        if entry[2] == 0x01 and entry[3] == 0x82:  # data partition, subtype SPIFFS (used by LittleFS)
            return offset, size
    sys.exit("No file system partition found in the firmware image")


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    if not (DATA / "index.html.gz").exists():
        sys.exit("No library files in %s. Run: python3 tools/build.py" % DATA)
    cli = shlex.split(os.environ.get("ARDUINO_CLI", "arduino-cli"))
    version = os.environ.get("JIC_VERSION", "dev")

    mklittlefs = find_mklittlefs(cli)
    with tempfile.TemporaryDirectory() as tmp:
        builds = []
        for board, family in CHIPS.items():
            build = Path(tmp) / board
            print("Compiling for %s ..." % family)
            run(cli + ["compile", "--fqbn", "esp32:esp32:%s:%s" % (board, PARTITIONS),
                       "--build-path", str(build), str(SKETCH)])
            merged = (build / "JustInCase.ino.merged.bin").read_bytes()
            fs_offset, fs_size = file_system_partition(merged)
            if len(merged) > FLASH_SIZE or any(b != 0xFF for b in merged[fs_offset:fs_offset + fs_size]):
                sys.exit("Unexpected firmware layout for %s: it overlaps the file system" % board)
            fs = Path(tmp) / ("library-%s.bin" % board)
            run([mklittlefs, "-c", str(DATA), "-b", "4096", "-p", "256", "-s", str(fs_size), str(fs)])
            image = bytearray(b"\xff" * FLASH_SIZE)
            image[:len(merged)] = merged
            image[fs_offset:fs_offset + fs_size] = fs.read_bytes()
            print("  library: %d KB in a %d KB file system at 0x%X" % (data_size() // 1024, fs_size // 1024, fs_offset))
            name = "just-in-case-%s.bin" % board
            (out / name).write_bytes(bytes(image))
            builds.append({"chipFamily": family, "parts": [{"path": name, "offset": 0}]})

    manifest = {"name": "Just In Case library hotspot", "version": version,
                "new_install_prompt_erase": True, "builds": builds}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")
    (out / "index.html").write_text(PAGE % {"web_tools": WEB_TOOLS, "version": version}, encoding="utf-8")
    print("Wrote %d images, manifest.json and index.html to %s" % (len(builds), out))


if __name__ == "__main__":
    main()
