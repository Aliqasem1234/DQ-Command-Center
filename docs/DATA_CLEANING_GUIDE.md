# Data Cleaning Guide

How the **Rensa** tab works, what every operation does exactly, and the quality rules that check data. Source of truth: `backend/app/services/data_cleaning_service.py` and `backend/app/services/rule_engine.py`. Tests with known inputs and outputs: `backend/tests/test_cleaning_engine.py`, `test_rule_engine.py`, `test_cleaning_and_rules_api.py`.

No AI or machine learning is used. Every operation is deterministic: the same input and settings always give the same output.

## 1. The workflow

1. Open a dataset → **Rensa**. Add one or more operations; they run **in the order listed**.
2. Press **Förhandsgranska** (preview). Nothing is saved yet. The preview shows:
   - rows modified, rows removed and values changed, plus a count per column;
   - exact duplicates before → after, and *possible* duplicates (rows that differ only in case or spacing), which are **reported, never removed**;
   - **skipped values per operation**, with the reason (e.g. "tvetydigt datum", "ogiltigt värde");
   - the **quality score before → after**, using exactly the same checks as a scan, including your executable rules;
   - before/after pairs for changed rows and the removed rows, identified by their **row number in the original file**.
3. If you edit anything after previewing, **Tillämpa** is disabled until you preview again, so you can never save something you haven't seen.
4. **Tillämpa** saves the result as a **new version**. If rows would be removed, you must confirm first.

### Same logic for preview and save

The preview and the save call the same function (`apply_operations`), so the preview is exactly what gets saved. An API test checks that the saved file matches the preview row for row.

### Nothing is overwritten

| Action | Effect |
|---|---|
| Upload | creates version 1 (the original) |
| Cleaning | creates version N+1; the version you cleaned stays untouched |
| Restore (Versioner → ↻) | copies the chosen version into a **new** version N+1. Nothing is deleted, so a restore can itself be undone the same way |
| Delete dataset | the only destructive action; owner only, with confirmation |

Every version records the operations that produced it (shown in **Versioner → Historik**). The audit log records the operation types, columns and counts, but **not** values such as fill values or category mappings, which can contain data.

### A note on the quality score

The score is the share of cells not affected by any failing check, calculated on the rows that remain. Removing rows (duplicates, rows with missing values) can raise the score without the remaining data getting any better. The preview says so whenever rows are removed, and the row counts are shown next to the score.

## 2. Operations

"Missing" means an empty cell or text that is only spaces. Missing values are never turned into text like `nan`, and are left alone unless the operation is about missing values.

| Operation (UI name) | What it does | Input / settings | Missing values | Limits |
|---|---|---|---|---|
| **Trimma blanksteg** | Removes spaces at the start and end | columns or all | untouched | — |
| **Slå ihop flera mellanslag** | Replaces any run of whitespace with one space | columns or all | untouched | also turns tabs and newlines inside a value into one space |
| **Ta bort osynliga tecken** | Removes control characters and invisible characters (zero-width space/joiners, BOM); tab, newline and CR become a space | columns or all | untouched | — |
| **Standardisera textformat** | lower / UPPER / Title Case | columns or all; case | untouched | Title Case follows Python rules (e.g. `o'neil` → `O'Neil`) |
| **Normalisera datumformat** | Rewrites dates as `YYYY-MM-DD` (configurable) | **columns required**; optional source format (e.g. `%d.%m.%Y`); optional day order | untouched | **Ambiguous dates are never guessed.** `01/02/2024` stays unchanged and is reported as ambiguous unless you choose "dag först" or "månad först". `31/12/2024` is unambiguous and converted. Values that aren't dates are kept and reported |
| **Konvertera datatyp** | Converts to integer, decimal or true/false; output uses `.` as decimal separator | **columns required**; target; decimal separator `.` or `,`; for invalid values, keep (default) or empty | untouched | `12.5` is not an integer and is not rounded: it's kept and reported. With `.` as separator, `1,234` is ambiguous and kept. Booleans accept true/false/yes/no/1/0/ja/nej/sant/falskt |
| **Standardisera kategorivärden** | Replaces values from your list (`från = till`, one per line) | **columns required**; case-insensitive by default; leading/trailing spaces ignored when matching | untouched | Values not in the list are unchanged. Keys that collide (e.g. `A` and `a`) are rejected |
| **Ta bort dubblettrader** | Removes rows that are identical in the chosen columns (or all columns) | columns or all; keep first or last | treated as equal to each other | Exact matches only. Similar rows are only reported as "möjliga dubbletter" and are never merged |
| **Hantera saknade värden** | Fill with a fixed value, mean, median or most common value, or remove the row | **columns required**; strategy; value | this is what it changes | Fixed value must be non-empty. Mean/median refuse a column with no numbers; non-numbers are excluded from the calculation and reported; the result is rounded to 4 decimals. Most common value refuses a tie (choose a fixed value instead) |

**Validation:** unknown operations, unknown columns, invalid settings or more than 50 operations are rejected with a readable message. Nothing is saved when a run is rejected.

**Not implemented (on purpose):**
- **Phone number normalisation:** there's no country or format rule in the data model, and guessing one could corrupt numbers.
- **Fuzzy or automatic merging of similar records:** possible duplicates are reported only.

## 3. Executable quality rules (Kvalitetsregler)

Choose one of these rule types, pick a dataset and a column, and the rule runs:
- on every **scan** of that dataset;
- whenever you press **Kör** (against the dataset's latest version).

| Rule type | A row fails when… | Settings |
|---|---|---|
| Obligatoriskt värde (`not_null`) | the cell is missing | — |
| Unika värden (`unique`) | the trimmed value appears more than once (all such rows fail) | case sensitive (default yes) |
| Giltig e-postadress (`email_format`) | the value isn't a syntactically valid address | — |
| Talintervall (`numeric_range`) | the value isn't a number, or is outside [min, max] | min and/or max |
| Tillåtna värden (`allowed_values`) | the value isn't in the list | values (max 500); case sensitive (default no) |
| Datumintervall (`date_range`) | the value isn't an unambiguous date, or is outside the range | earliest and/or latest date; optional day order |

Except for "Obligatoriskt värde", missing cells are not judged by these rules (that's `not_null`'s job), so they don't count in "records checked".

**Results:**
- Each run stores a result: passed / failed / error, counts, and the first 20 failing row numbers (**never the cell values**).
- A failing rule opens an issue on the dataset, and a passing run resolves it.
- The table shows each rule's last result.
- Failing cells count in the dataset's quality score.

**Errors and documentation-only rules:**
- If the column no longer exists, the result is "error" and the rule doesn't count in the score.
- Any other rule type is saved as **documentation only** ("Endast definition"). It is never run and never affects the score; the UI won't pretend otherwise.
- Referential checks between tables aren't supported: the platform works on one uploaded table at a time.
