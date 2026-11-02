# Devices: what can carry this library

The library is plain text at heart, about 1 MB of it. Almost anything that can show words can carry it. Pick by what you have, and keep **at least two different kinds**, for example paper plus a phone.

## The device ladder

From zero power to most features:

| Device | Format | Power | Runs for | Cost | Guide |
|---|---|---|---|---|---|
| **Paper** | PDF, printed | none | forever | printing | [print/](print/) |
| **Kindle / e-reader** | AZW3 / EPUB | ~0.1–0.2 W while reading, almost nothing between pages | weeks per charge (30 min a day) | $0 if you own one | [kindle/](kindle/) |
| **Cheap MP3/MP4 player** with "E-book" mode | `just-in-case-mp3.txt` or the `mp3` folder (ASCII, short edition) | AAA battery or small cell | days | $10–20 | see "Even smaller devices" |
| **Old phone** (airplane mode) | single HTML file, EPUB | 0.5–1.5 W while reading | 10–30 hours of reading | $0 | open the file |
| **ESP32 / ESP8266 hotspot** | multi-page site | 0.3–0.6 W | 1.5–3 days on 10,000 mAh | $2–8 | [esp32/](esp32/) |
| **Raspberry Pi Zero 2 W hotspot** | multi-page site | 0.6–1.5 W | 1–2 days on 10,000 mAh | $15–20 | [raspberry-pi/](raspberry-pi/) |
| **Any laptop** | single HTML file | 5–30 W | hours | $0 | open the file |

The hotspot devices **serve many people at once**. One board at a shelter, clinic or camp can serve a whole community, and each visitor can save a full copy onto their own phone.

## Even smaller devices

What is smaller than a Raspberry Pi, and what really works today:

| Device | Size | Status | Notes |
|---|---|---|---|
| **ESP32-C3 SuperMini** | 22 × 18 mm, ~2 g | ✅ Supported | The smallest practical library server. 4 MB flash holds the whole library with no SD card. Lowest power of the ESP32 family. ~$2–4. |
| **ESP8266 (D1 mini, ESP-12)** | 34 × 26 mm | ✅ Supported | Older and cheaper. Same sketch. A 4 MB board holds the full library. |
| **ESP-01 and other boards with about 0.5 MB of file space** | 25 × 14 mm | ✅ Supported | Use the small-board edition (`dist/esp-small/`): critical articles in full, every other article as warnings and quick steps, one page per topic. About 420 KB. |
| **ESP32-S3 / ESP32 DevKit** | ~50 × 25 mm | ✅ Supported | More range, more power use. Can read from a microSD card. |
| **microSD card or USB stick** | fingernail | ✅ Works now | Not a reader, but the cheapest and most durable way to carry and pass on copies. Copy the whole `dist/` folder. |
| **MP3/MP4 player with a text reader** | matchbox | ✅ Works now | Many cheap players have an "E-book" or "Text" mode. Copy the `mp3` folder: one small ASCII file per topic with short names (`02WATER.TXT`, `08MEDICA.TXT`) and Windows line endings, which old players handle best. Or copy `just-in-case-mp3.txt` (one file) or `just-in-case-core.txt` (critical articles in full). Some players run on one AAA battery. |
| **Raspberry Pi Pico W / Pico 2 W** | 51 × 21 mm | 📝 Planned | Has WiFi, but only 2–4 MB flash and no ready-made web server in this repo yet. Help wanted. |
| **ESP32 + e-paper display** (e.g. LilyGO T5, M5Paper, Watchy) | pocket / wrist | 📝 Planned | A stand-alone reader with no phone needed. E-paper uses power only when the page changes, so it could last weeks or months. Help wanted. |
| **M5Stack Cardputer / LilyGO T-Deck** | credit card | 📝 Planned | A tiny computer with a screen, keyboard and microSD. A reader app for the TXT edition is a good first project. |
| **LoRa / Meshtastic radios** | pocket | 📝 Planned | Long-range (kilometers) text radio with no internet. Idea: a node that answers questions with short article snippets. |
| **Classic Arduino Uno / Nano** | – | ❌ Not recommended | 2 KB of RAM. It could scroll text from an SD card onto a small LCD, but reading a whole library that way is painful. Use an ESP32: same Arduino tools, about the same price, 160× the memory, plus WiFi. |

## Power: what really matters

| Power source | Approximate energy | Library hotspot (ESP32) | Kindle |
|---|---|---|---|
| 10,000 mAh power bank | ~37 Wh (~30 Wh usable) | 1.5–3 days, nonstop | ~5 full charges (months of reading) |
| Phone-sized 5 W solar panel, 6 hours of sun | ~15–20 Wh per day | runs all day in sun | 2–3 charges per sunny day |
| Car battery (60 Ah) with a 12 V USB adapter | ~700 Wh, but keep half for starting | weeks | dozens of charges |
| 4 × AA alkaline (with a USB adapter) | ~10 Wh | about half a day | 1–2 charges |

> [!WARNING]
> **Power banks switch off when the load is very small.** A Kindle, a microcontroller or an LED light may draw so little that the bank thinks nothing is plugged in. Look for a "low current" or "always on" mode (often a double press of the button), or test your bank before you need it.

## One library, sized for each device

Every file is cut from the same articles by [`tools/editions.ini`](../tools/editions.ini): full articles for laptops, phones and e-readers; the warnings and quick steps only for MP3 players, pocket booklets and tiny boards. Each edition has a size limit that the build enforces. See the table in the main [README](../README.md#one-library-an-edition-for-every-device), or the "Which file for my device?" page on the website or hotspot.

## Which should I set up today?

1. **Print** the core edition: [print/](print/).
2. **Put the EPUB or AZW3 on your phone and any e-reader**: [kindle/](kindle/).
3. **Save** `just-in-case.html` on every phone and laptop in your home.
4. For a community (school, mosque, church, clinic, camp, building): **build an ESP32 hotspot** and leave it with a power bank and a small solar panel: [esp32/](esp32/).
