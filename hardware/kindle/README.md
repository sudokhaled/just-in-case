# Kindle and other e-readers

An e-ink reader is one of the best survival devices there is. One charge lasts **weeks**, the screen is readable in full sun, and it has **full-text search**: type "bleeding" and it finds every page.

## Which file to use

Download from the [latest release](../../../../releases/latest):

| Device | File | How |
|---|---|---|
| Kindle (2012 or newer) | `just-in-case.azw3` | USB copy (below) |
| Kindle, via the internet | `just-in-case.epub` | Send to Kindle (below) |
| Older Kindle (Keyboard, DX, 2nd gen) | `just-in-case.pdf` or `just-in-case.txt` | USB copy |
| Kobo, PocketBook, Tolino, Boox, Nook | `just-in-case.epub` | USB copy into the main folder |
| Phone or tablet book app | `just-in-case.epub` | Open the file with Apple Books, Google Play Books, Lithium, ReadEra... |

## Kindle: copy over USB (works offline)

1. Connect the Kindle to a computer with a USB cable. It appears as a drive called "Kindle".
2. Copy `just-in-case.azw3` into the **documents** folder.
3. Eject the Kindle. The book appears in your library. On some models it shows under **Library > Downloaded** or **Docs**.

## Kindle: Send to Kindle (needs internet, do it now)

1. Go to the Amazon "Send to Kindle" web page, or email the file to your Kindle's address (found under Settings > Your Account > Send-to-Kindle Email).
2. Send `just-in-case.epub`. Amazon converts it and delivers it to all your Kindles.
3. **Open the book once** so it is downloaded to the device. Then it works offline forever.

## Make the battery last

- Turn on **Airplane Mode**. WiFi uses more power than reading.
- Turn the front light down or off in daylight.
- Use the built-in search: tap the magnifying glass and type a word.
- Add bookmarks to the articles marked ★ (critical).
- Charging later: a Kindle charges from any USB power bank, a car USB port or a small solar panel.

## Build the Kindle file yourself

The release workflow converts the EPUB with Calibre's free `ebook-convert` tool:

```
python3 tools/build.py
ebook-convert dist/just-in-case.epub dist/just-in-case.azw3
```
