---
name: google-developer-style
description: Apply the Google Developers Style Guide when writing, reviewing, or editing technical documentation, README files, API docs, code comments, or any developer-facing content. Use when the user asks to "write docs", "review documentation", "check my writing", "follow Google style", "improve technical writing", or requests help with developer documentation quality.
version: 1.0.0
---

# Google Developer Documentation Style Guide

Apply these rules when writing or reviewing any developer-facing documentation.

## Core Philosophy

Write like a knowledgeable friend — conversational and clear, not formal or pedantic. Prioritize clarity over following rules. If a rule produces awkward prose, break it.

**Priority order for style decisions:**
1. Project-specific style guide
2. This skill's rules
3. Merriam-Webster dictionary → Chicago Manual of Style → Microsoft Writing Style Guide

---

## Tone & Voice

- **Conversational but not casual**: Friendly without slang, abbreviations (no "tl;dr"), or internet shorthand.
- **No exclamation marks**: Avoid "Congratulations!" or "This is easy!" type enthusiasm.
- **No filler words**: Delete "simply," "just," "easy," "quickly," "obviously" from procedures — they're condescending.
- **No pre-announcements**: Never document unreleased features.
- **No excessive politeness**: Minimize "please" in instructions. "Click **Save**" not "Please click **Save**."
- **No buzzwords or jargon**: Write for a global audience — avoid idioms, culturally specific references, pop culture.

---

## Language & Grammar

### Person and Voice
- **Second person ("you")**: Address the reader directly. Avoid "we" for reader actions.
- **Active voice**: Make the actor the grammatical subject. "The server returns a 200" not "A 200 is returned."
- **Active voice exceptions**: Passive is OK to (1) emphasize the object, (2) de-emphasize the actor, or (3) when the actor is irrelevant.
- **Present tense**: "The API returns an error" not "The API will return an error."

### Sentence Structure
- **Conditions before instructions**: "If you want X, do Y" not "Do Y if you want X."
- **One idea per sentence**: Break complex sentences apart.
- **Parallel structure**: Keep list items grammatically consistent.

### Pronouns
- **Gender-neutral pronouns**: Use "they/them" for singular indefinite reference. Rewrite to use "you" or restructure when possible.
- **Avoid gendered examples**: "man-hours" → "person-hours"; "mankind" → "humanity."

---

## Formatting

### Headings
- **Sentence case**: "Getting started with the API" not "Getting Started With The API."
- **No ending punctuation** on headings.
- **Descriptive, not clever**: Headings are navigation aids, not prose.

### Lists
- **Numbered lists**: Only for sequential steps or ranked items.
- **Bulleted lists**: For non-sequential collections.
- **Description lists**: For name/value pairs or term definitions.
- **Serial comma (Oxford comma)**: Always. "Red, white, and blue."
- **Parallel grammar**: All items in a list must start the same way (all verbs, all nouns, etc.).
- **No ending punctuation** on list items that aren't full sentences.

### Code Formatting
Use `code font` for all of the following:
- Attribute names and values
- Class names, method names, function names
- Command-line utilities (`gcloud`, `kubectl`, `npm`)
- Data types, language keywords
- Filenames, directory paths
- HTTP verbs (`GET`, `POST`) and status codes (`404 Not Found`)
- Package names, port numbers
- Placeholder variables
- UI elements rendered from user input

**Do NOT use code font for:**
- Product/service names
- URLs the reader navigates to (use hyperlinks instead)
- Domain names in descriptive context

**Don't inflect code elements** — add a noun instead:
- ✓ "The `ADDRESS` constant's value..."
- ✗ "`ADDRESS`'s value..."

### Bold and Italics
- **Bold**: UI element labels, key terms on first use, critical warnings.
- **Italics**: Titles of books/publications, introducing new terms, emphasis (use sparingly).
- **Never bold or italicize for decoration.**

### Dates and Numbers
- **Dates**: Use unambiguous formats. "January 15, 2024" or "15 January 2024" — never "01/15/24."
- **Numbers**: Spell out zero through nine; use numerals for 10 and above.
- **Units**: Use standard abbreviations. Put a space between number and unit: "100 MB."

---

## Technical Writing Specifics

### Procedures
- **One action per step**: Don't combine multiple actions in a single numbered step.
- **Lead with the UI element**: "Click **File** > **Save**" not "To save, navigate to File and click Save."
- **Result sentences optional**: Add a sentence after a step only if the result is non-obvious.
- **Prerequisites first**: List what the user needs before starting a procedure.

### Links
- **Descriptive link text**: Never use "click here," "this link," or a bare URL as link text.
- **Link text = destination topic**: "See [Authenticating with OAuth2](...)" not "See [this guide](...)."

### API Documentation
- **Code comments**: Write full sentences. Start with a verb in third person: "Returns the user ID" not "Return the user ID."
- **Parameter descriptions**: State what the parameter does, its type, and its default/constraints.
- **HTTP status codes**: Always format as `404 Not Found` (number + reason phrase in code font).

### Images
- **Alt text required**: Every image must have descriptive alt text.
- **High resolution**: Use SVG/vector or high-DPI rasters.
- **Captions for context**: Add a caption when alt text alone isn't sufficient.

---

## Inclusive Language

- **Allowlist / denylist**: Not "whitelist" / "blacklist."
- **Parent / replica / secondary**: Not "master" / "slave."
- **No ableist language**: Avoid "crazy," "insane," "blind to," "cripple," "sanity-check" → "final check."
- **No violent metaphors**: Avoid "hang," "hit," "kill."
- **No disability euphemisms**: "Uses a wheelchair" not "wheelchair-bound." Don't label nondisabled people as "normal."
- **Age-neutral**: "Older adults" not "elderly" or "seniors."
- **Diverse examples**: Use diverse names, avoid US-centric references (holidays, sports idioms).

---

## Global Audience Considerations

- Use **American English** spelling and punctuation.
- Avoid idioms, colloquialisms, and culturally specific humor.
- Prefer literal constructions over metaphors.
- Be explicit — don't rely on cultural context the reader may not share.

---

## Quick Review Checklist

Before finalizing documentation, verify:

- [ ] Active voice used throughout?
- [ ] Second person ("you") instead of "we"?
- [ ] Present tense used?
- [ ] Filler words removed ("simply," "easy," "just")?
- [ ] Headings in sentence case?
- [ ] Serial commas present?
- [ ] Code elements formatted in `code font`?
- [ ] UI elements bolded?
- [ ] Links use descriptive text?
- [ ] Inclusive language throughout?
- [ ] No exclamation marks?
- [ ] Numbers follow the spell-out-under-10 rule?

---

## Reference Materials

- [Full word list](references/word-list.md) — specific term usage and preferred spellings
- [Formatting quick reference](references/formatting.md) — tables of formatting rules

For the authoritative source: https://developers.google.com/style
