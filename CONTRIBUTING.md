# Contributing

Thank you. Every correction, review, translation and article here may one day be read by someone who has nobody else to ask.

## Ways to help

| You are | Most useful thing you can do |
|---|---|
| Anyone | [Report an error](../../issues/new?template=error-report.yml). Spread the library: print it, share the file, set up a hotspot. |
| Medical, rescue, fire, military, farming, engineering, radio professional | Review the articles in your field (see [Reviewing](#reviewing)). |
| Speaker of any language besides English | [Translate](#translating), critical (★) articles first. |
| Writer | Write a 📝 planned topic from [ROADMAP.md](ROADMAP.md). |
| Programmer or maker | Improve the build tool, or build new readers (e-paper, Pico W, LoRa). See [hardware/](hardware/). |

## Writing or editing an article

1. Read [STYLE_GUIDE.md](STYLE_GUIDE.md). It's short, and it's strict for a reason.
2. Pick a topic from [ROADMAP.md](ROADMAP.md). Open an issue saying you're working on it, so two people don't write the same article.
3. Create `content/en/<category>/<id>.md` using the id in the roadmap. Copy the structure of [purify-water.md](content/en/water/purify-water.md).
4. Check it:

   ```
   python3 tools/build.py --check
   ```

5. Build and read it as a reader would:

   ```
   python3 tools/build.py
   ```

   Open `dist/just-in-case.html` in a browser, and also read your article in `dist/just-in-case.txt`. If it isn't clear as plain text, it isn't clear.
6. Open a pull request. Fill in the checklist, including **where every number came from**.

### Drawings and pocket cards

- **Drawings** are small hand-written SVG files in `content/images/`, with numbers instead of words so they never need translating. The rules are in the "Pictures" section of [STYLE_GUIDE.md](STYLE_GUIDE.md); `--check` enforces them. Wanted next: any procedure that is hard to follow from words alone.
- **Pocket cards** live in `content/en/cards.md`. Each `## ` heading starts a card. A card must stay consistent with its full article. Keep it under about 110 words so it fits when printed.

### Device editions

Each device gets an edition cut from the same articles, set in [`tools/editions.ini`](tools/editions.ini): which articles, full or short (warnings and quick steps only), drawings or not, and a size limit the build enforces. To support a new device, add a section there; no new code is needed for the existing formats. Because of short editions, the opening callout and quick steps of every article must make sense on their own (see the style guide).

### Rules for facts

- **Every number needs a source.** Doses, times, distances, temperatures, ratios. Put the source in `## Sources`.
- **Use your own words.** You may copy only from public domain sources (US government works such as CDC, FEMA, NOAA and US Army manuals) or CC BY-SA compatible sources (such as Wikipedia), and you must cite them. Never copy from copyrighted books or websites, even free ones.
- **When sources disagree**, follow the most recent guidance from the main international bodies (WHO, IFRC, ILCOR), and say so if regional guidance differs.
- **When evidence is weak**, say so in the article. Honesty about uncertainty saves lives. False confidence costs them.

## Reviewing

Each article has a `reviewed:` field:

| Value | Meaning | How an article gets it |
|---|---|---|
| `no` | Draft | Default |
| `community` | Checked line by line by at least 2 contributors other than the author | Two approving reviews on a pull request that sets it, each confirming they checked every number against a source |
| `expert` | Checked by a qualified professional in that field | The reviewer states their qualification in the pull request (for example "emergency physician, 12 years"). Maintainers may ask for verification. |

When you review, **check every number against its source**, look for missing deadly mistakes, and read it as a frightened beginner would. Any factual change resets the article to `reviewed: no` unless the reviewer re-checks it.

## Translating

The whole system is built for translation. Each language lives in its own folder with identical file names, so translators can work in parallel and the build links everything automatically.

1. Copy `content/en/categories.txt` and `content/en/strings.txt` to `content/<code>/`. `<code>` is a two-letter [ISO 639-1](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes) code: `ar`, `es`, `fr`, `hi`, `sw`, `zh`, `pt`, `bn`, `ru`, `id`, `ur`...
2. Translate the text in both files. Never translate the ids or keys. For right-to-left languages (Arabic, Urdu, Persian, Hebrew), set `direction = rtl` in `strings.txt`.
3. Translate articles into `content/<code>/<category>/<same-file-name>.md`. **Start with the ★ critical articles.** Keep the front matter keys in English, and translate the values of `title`, `summary` and `tags`.
4. The `## Sources` heading must match the translated `sources` value in your `strings.txt`.
5. Use plain, everyday words, the way you would explain it to a neighbor. Keep numbers and units exactly as they are. Never "round" a dose.
6. Run `python3 tools/build.py --check --lang <code>`. Links to articles that are not translated yet are allowed: they show as plain text until the translation exists.
7. Open a pull request titled `Translation (<language>): <articles>`. A second speaker of the language should review it.

The build creates `dist/just-in-case.<code>.html`, `.epub` and `.txt`, plus `dist/site/<code>/`.

## Code

- The build tool (`tools/`) uses the **Python standard library only**, and must keep working on Python 3.8 and on a Raspberry Pi with no internet. Don't add dependencies.
- Run the tests: `python3 -m unittest discover -s tools -p "test_*.py"`
- The firmware (`hardware/esp32/`) must compile for ESP32, ESP32-C3, ESP32-S3 and ESP8266, with only the libraries that come with the board packages.
- Generated output (`dist/`, `hardware/esp32/JustInCase/data/`) is never committed. Releases publish it.

## Releases (maintainers)

Push a tag such as `v1.0.0`. The release workflow checks and builds every edition, makes the Kindle (AZW3) and PDF versions, and attaches everything to a GitHub release with checksums.

## Conduct

Be kind, be precise, and assume good intent. See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
