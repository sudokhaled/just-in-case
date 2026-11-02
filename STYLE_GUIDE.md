# Style Guide

Every article in this library must work for one reader:

> A frightened, tired person with no internet and nobody to ask. They may be reading by candlelight, on a phone at 5% battery, on a Kindle, or on a printed page. English may be their second language. They may be fifteen years old.

If a sentence does not help that person act correctly, delete it.

## The 12 rules

1. **Action first.** Start with what to do. Explain why afterwards, briefly.
2. **Short sentences.** One idea per sentence. Aim for 15 words or fewer. Use plain words: "use", not "utilize"; "enough", not "sufficient".
3. **Numbered steps for procedures.** Each step starts with a verb: "Boil", "Press", "Wait".
4. **Danger first.** The mistakes that kill or injure go in a `[!CAUTION]` callout near the top.
5. **Be exact.** Give numbers, times and amounts. "Boil for 1 minute", not "boil well". "Press hard for 10 minutes", not "apply pressure".
6. **Both units.** Metric first, imperial in brackets: `1 liter (1 quart)`, `5 cm (2 in)`, `38°C (100°F)`, `20 kg (44 lb)`.
7. **Assume no special gear.** Give the proper method and the improvised method side by side.
8. **Global.** Don't assume a country, climate, religion or diet. Name regional differences when they matter. Use generic medicine names, never brands: "paracetamol (acetaminophen)", "ibuprofen".
9. **Honest.** Say when a method is unreliable, slow or low-yield, for example "a solar still makes very little water". Name common deadly myths and say clearly that they are wrong.
10. **No fluff.** No "In this article…", no history lessons, no jokes, no motivational filler.
11. **Easy to translate.** No idioms, no slang, no wordplay, no cultural references. Use US spelling and put UK spellings in `tags` so search finds both.
12. **Right length.** Usually 600–1500 words. A critical article must be usable in 5 minutes, with its "Quick steps" usable in 30 seconds.

## Safety rules (non-negotiable)

- Never present an unverified method as reliable. If the evidence is weak, say so.
- Medical content follows current mainstream guidance: WHO, IFRC/ICRC, ILCOR/AHA/ERC, CDC. When the official advice is "get professional care", say so first. Then give the best thing to do when professional care does not exist.
- Plants and mushrooms: never write "this plant is safe" without its deadly look-alikes in the same section. Never give rules for identifying mushrooms. The rule is: do not eat wild mushrooms.
- No weapons manufacturing, no explosives, no instructions meant to hurt people. Security content covers avoiding, de-escalating and defending.
- Don't give medicine doses beyond what is printed on common packages, except for oral rehydration solution and other WHO-published community-level guidance.
- Mention legal limits where they commonly apply (trapping, radio transmitting, foraging on private land), but survival comes first in a true emergency.

## File layout

```
content/<language>/<category>/<article-id>.md
```

- `<language>` is `en` for English. Translations use the same category folders and the same file names.
- `<category>` must be one of the ids in `content/en/categories.txt`.
- `<article-id>` uses lowercase letters, digits and hyphens. **24 characters at most**, because tiny microcontroller file systems have short name limits. Example: `purify-water.md`.

## Front matter

Every file starts with this block. Use simple `key: value` lines only. No quotes, no multi-line values.

```
---
title: Making Water Safe to Drink
summary: Boil, chlorinate, filter or use sunlight to kill the germs that cause diarrhea, cholera and typhoid.
priority: critical
order: 20
tags: water, boil, bleach, chlorine, iodine, sodis, filter, purification, disinfection
reviewed: no
updated: 2026-11-01
---
```

| Field | Rule |
|---|---|
| `title` | Plain words a scared person would recognize. 60 characters or fewer. |
| `summary` | One sentence, 200 characters or fewer. Says what the reader will be able to do. |
| `priority` | `critical` = knowing this saves lives in the first days. `important` = needed within weeks. `useful` = makes life better long-term. |
| `order` | A number that sorts articles inside their category (10, 20, 30…). |
| `tags` | Comma-separated lowercase search words. Include synonyms, UK spellings and words a panicked person might type ("bleeding, blood, hemorrhage, haemorrhage"). |
| `reviewed` | `no` (draft), `community` (checked by 2+ contributors), or `expert` (checked by a qualified professional, named in the pull request). |
| `updated` | The date of the last factual change, `YYYY-MM-DD`. |

## Article structure

Use this skeleton. Sections in brackets are optional.

```
---
(front matter)
---

> [!CAUTION]
> The one to three mistakes most likely to kill or injure.

## Quick steps

1. The shortest correct procedure, 3 to 8 steps.

## (Topic sections: as many as needed)

## (Common mistakes and myths)

## (When to get help)

## Sources

- Organization or author, *Title*, year.
```

- The body never starts with a heading. It starts with a callout or a short paragraph. The `title` is shown automatically.
- `## Sources` is **required** and is always the last section.
- **The opening callout and `## Quick steps` must stand alone.** Short editions (MP3 players, pocket booklet, small boards) show only them. Never write "see below", "the table below" or "(below)" there: put the essential fact in the step itself. `--check` enforces this.
- Use `##` for sections and `###` for sub-sections only. Never use `#` or `####`.

## Allowed Markdown (strict subset)

The build tool is tiny so it can run on a Raspberry Pi with no extra software. It only understands this subset, and it rejects anything else.

**Lines**

- **Never hard-wrap.** One paragraph is one line. One list item is one line. One table row is one line.
- Separate blocks with one blank line.

**Inline**

| Write | Means |
|---|---|
| `**bold**` | Strong emphasis. Use for key numbers and the words "never" and "do not". |
| `*italic*` | Light emphasis, titles of books in Sources. |
| `` `code` `` | Rare: exact text to type or see, for example a radio frequency. |
| `[text](https://example.org)` | External link. Use rarely; the reader is offline. |
| `[text](../water/purify-water.md)` | Link to another article. **Always** use the form `../<category>/<id>.md`. It works on GitHub and in every built format. |

Do not use underscores for emphasis, raw HTML, HTML entities, inline images, footnotes or reference-style links.

**Blocks**

- Sections: `## Heading`, sub-sections: `### Heading`.
- Bullet lists: `- item`. Numbered lists: `1. item`, `2. item`… Nest a list by indenting it 3 spaces under its parent item.
- Callouts use GitHub alert syntax, so they look right on GitHub too:

```
> [!CAUTION]
> Deadly danger. Shown as "DANGER".

> [!WARNING]
> Serious risk of harm.

> [!IMPORTANT]
> Must not be missed.

> [!TIP]
> A better or easier way.

> [!NOTE]
> Background or a limit of the method.
```

  Callouts can contain paragraphs and lists. Every line inside a callout starts with `> `. Put a line containing only `>` between two paragraphs or between a paragraph and a list.

- Tables: one header row, one `|---|---|` separator row, then data rows. Keep tables small. They must still make sense as plain text.
- Fenced code blocks (three backticks) are used for **ASCII diagrams** only. Keep them 60 characters wide or less, so they fit small screens.
- Horizontal rules (`---`) are not used inside articles.

## Pictures

A simple drawing often says what 100 words cannot: where to put your hands for CPR, how a knot crosses, which way a latrine slopes. Pictures also help people who read poorly or read a second language.

**In the article**, a picture goes on a line of its own:

```
![Recovery position: 1 head tilted back, 2 hand under the cheek, 3 top knee bent forward.](../../images/recovery-position.svg)
```

- The text in the square brackets is the **legend**. It is shown under the picture, read aloud by screen readers, and printed instead of the picture in the text editions. It must make sense without the picture.
- Pictures live in `content/images/` and are shared by every language. File names use lowercase letters, digits and hyphens.

**The drawing** is a small, hand-written SVG file. The build tool checks every rule below.

- **No words in the drawing.** Use numbers or single letters (1, 2, A, B) and explain them in the legend. This way, translators never need to touch a picture.
- Under **12 KB**. The `<svg>` element needs `xmlns="http://www.w3.org/2000/svg"`, `viewBox`, `width` and `height`.
- Line drawing style: `fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" color="#1a1a1a"` on the `<svg>` element.
- First element: a background `<rect class="bg" ... fill="#ffffff" stroke="none"/>` covering the whole picture, with `rx="12"`.
- Fill solid shapes with `fill="currentColor"`. Mark the dangerous or most important part in red with `class="accent" stroke="#b00020"` (or `class="accent-fill" fill="#b00020"` for filled shapes). Use `class="muted" stroke="#666666"` for ground lines and background details.
- Number labels: bold sans-serif digits about 17 px high, in a small circle, placed next to the part they name.
- Not allowed: `<script>`, `<style>`, `<image>`, `<use>`, `<a>`, `id` and `style` attributes, event attributes, and links to other files. Pictures are pasted directly into pages, so these could break or endanger them.
- The page recolors pictures for dark mode and printing. That only works if you use the colors and classes above.

See `content/images/ground-air-signals.svg` for an example.

## Punctuation and characters

- Prefer plain ASCII: straight quotes `'` and `"`, hyphen `-`. The build converts typographic characters for the ASCII edition, but less conversion is better.
- `°` is fine for temperatures. Write `38°C (100°F)`.
- Write numbers as digits: "3 minutes", not "three minutes".

## Sources

- Write in your own words. Facts are not copyrighted; sentences are.
- You can copy text only from **public domain** sources (for example US government works: CDC, FEMA, NOAA, US Army field manuals) or **CC BY-SA compatible** sources (for example Wikipedia), and you must name the source.
- Do not copy from copyrighted books or websites, even free ones (for example *Where There Is No Doctor* or wikiHow). Cite them, and rewrite the ideas in your own words.
- Prefer primary, current sources: WHO, IFRC, CDC, national health services, peer-reviewed research, official military field manuals.

## Review levels

Medical, plant and chemical articles stay `reviewed: no` until someone qualified checks them. A wrong number in this library can kill someone. Reviewers check every number against a source.
