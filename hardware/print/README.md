# Print it

Paper needs no power, can't crash, and can't run out of battery. **Print the library while you still have electricity**, and keep it with your emergency kit.

## What to print

| Print | File | What it is |
|---|---|---|
| **1. Pocket cards** | `just-in-case-cards.pdf` | 16 cards (CPR, choking, bleeding, burns, safe water, carbon monoxide, rescue signals, a family plan to fill in...), 4 per page. Cut along the dashed lines and laminate. 4 pages. |
| **2. Pocket booklet** | `just-in-case-pocket.pdf` | Every article's warnings and quick steps, on A6 pages (105 × 148 mm), about 150 pages. Print 4 pages per A4 sheet, or as a booklet, and keep it in a bag or car. |
| **3. Core book** | `just-in-case-core.pdf` | Only the ★ critical articles. About 120 A4 pages. |
| **4. Full book** | `just-in-case.pdf` | Everything. About 430 A4 pages. |

Download them from the [latest release](../../../../releases/latest). The books are laid out like real books: a contents list and an **index** with page numbers, the chapter and article name at the top of every page, and every "see" reference followed by its page number, for example "(p. 61)". Warnings, tables and drawings are never split across pages.

## Make the PDFs yourself

```
python3 tools/build.py
pip install weasyprint
weasyprint dist/just-in-case-core-book.html just-in-case-core.pdf
weasyprint dist/just-in-case-book.html just-in-case.pdf
weasyprint dist/just-in-case-pocket.html just-in-case-pocket.pdf
```

For the cards, open `dist/just-in-case-cards.html` in a browser and choose **Print > Save as PDF** with margins set to "None" or "Minimum". Without WeasyPrint, you can also print `dist/just-in-case.html` from any browser. It is formatted for paper, but has no page numbers.

## Printing tips

- Print **double-sided** to halve the paper.
- Black and white is fine: warnings are marked with words (DANGER, WARNING) as well as color.
- Put the pages in a **ring binder with plastic sheet protectors**, or have a copy shop bind it.
- Store it in a **sealed plastic bag** to keep it dry.
- **Laminate** the most-used pages (CPR, stopping bleeding, making water safe) and keep them where they will be needed: kitchen, car, go-bag.
- Make one copy per household and one for the car. Give copies to neighbors: in a disaster, the people around you matter most.
