# Google Developer Style Guide — Formatting Quick Reference

Source: https://developers.google.com/style

---

## Text Formatting

| Element | Format | Example |
|---------|--------|---------|
| Code, commands, filenames | `code font` | Run `gcloud init` |
| UI element labels | **bold** | Click **Save** |
| New terms (first use) | *italics* | The *idempotency key* ensures... |
| Book/doc titles | *italics* | See *The Chicago Manual of Style* |
| Placeholder variables | `code font` + describe | Replace `PROJECT_ID` with your project ID |
| HTTP verbs | `code font` | Send a `GET` request |
| HTTP status codes | `code font` with reason phrase | Returns `404 Not Found` |
| Environment variables | `code font` | Set `PATH` before running |

---

## Headings

| Rule | Correct | Incorrect |
|------|---------|-----------|
| Sentence case | "Getting started with OAuth" | "Getting Started With OAuth" |
| No ending punctuation | "Prerequisites" | "Prerequisites:" |
| Descriptive, not clever | "Configure authentication" | "Let's get authenticated!" |

---

## Lists

| Type | Use for | Notes |
|------|---------|-------|
| Numbered | Sequential steps, ranked items | Don't use for non-sequential content |
| Bulleted | Non-sequential items | Items don't need to be parallel to reality, but grammar must be parallel |
| Description (term: definition) | Name/value pairs, glossaries | — |

**List formatting rules:**
- Always use serial (Oxford) comma: "red, white, and blue"
- Parallel grammatical structure across all items
- No ending punctuation on fragments; periods on full sentences
- Introduce lists with a complete sentence ending in a colon

---

## Numbers

| Rule | Correct | Incorrect |
|------|---------|-----------|
| Spell out 0–9 | "three options" | "3 options" |
| Numerals for 10+ | "12 parameters" | "twelve parameters" |
| Number + unit | "100 MB" | "100MB" |
| Ranges | "1–10" (en dash) | "1-10" (hyphen) |
| Percentages | "15%" (numeral + symbol) | "fifteen percent" |

---

## Dates and Times

| Format | Example |
|--------|---------|
| Full date (preferred) | January 15, 2024 |
| Alternate unambiguous | 15 January 2024 |
| Never use | 01/15/24 or 15/01/24 |
| Time | 9:00 AM UTC |
| Time zones | Use UTC or specify zone: "3:00 PM PT (UTC−8)" |

---

## Punctuation

| Rule | Guidance |
|------|----------|
| Serial comma | Always include: "a, b, and c" |
| Em dash | Use for asides — without spaces — like this |
| En dash | Use for ranges: "pages 10–20" |
| Hyphen | Use for compound modifiers: "high-availability cluster" |
| Colon | Introduce lists and examples; capitalize what follows if it's a full sentence |
| Semicolon | Avoid; prefer two sentences |
| Exclamation mark | Avoid entirely in technical documentation |

---

## Code Samples

| Rule | Guidance |
|------|----------|
| Syntax highlighting | Use when available |
| Complete and runnable | Prefer complete, runnable examples over fragments |
| Comment the non-obvious | Add inline comments for non-obvious logic |
| Don't omit error handling | Show realistic error handling in examples |
| Language label | Always label the code block language |

---

## Links

| Rule | Correct | Incorrect |
|------|---------|-----------|
| Descriptive text | "See [Authenticating with OAuth2](...)" | "See [here](...)" |
| No bare URLs | Always wrap URLs in descriptive text | `https://example.com` |
| No "click here" | "Download the [CLI tool](...)" | "[Click here](...) to download" |

---

## Images

| Rule | Guidance |
|------|----------|
| Alt text | Required for every image; describe the content/function |
| Resolution | Use SVG or high-DPI rasters (2× minimum) |
| Captions | Add when alt text alone isn't sufficient |
| File format | SVG for diagrams; PNG/WebP for screenshots |
