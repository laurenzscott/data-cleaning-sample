"""Cleans data/raw-export.csv against fixed rules and writes:

  data/cleaned-export.csv   the cleaned rows (comma-separated, UTF-8)
  data/change-log.txt       what was changed, how often, and what was left alone
  data/facts.json           the same numbers in machine-readable form

Nothing is guessed: a value that cannot be read with certainty is left empty
and counted in the change log, with its customer_id and the original text.
"""
import csv
import json
import re
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data"
SRC = DATA / "raw-export.csv"
OUT = DATA / "cleaned-export.csv"
LOG = DATA / "change-log.txt"
FACTS = DATA / "facts.json"

EUR = "\u20ac"  # the euro sign, written as an escape so this file stays plain ASCII
COLUMNS = ["customer_id", "company", "invoice_date", "amount", "status", "email"]

MONTHS = {"january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6, "july": 7,
          "august": 8, "september": 9, "october": 10, "november": 11, "december": 12}

RULES = [("Dates normalised to YYYY-MM-DD", "dates"),
         ("Amounts converted from text to numbers", "amounts"),
         ("Company names unified", "company"),
         ("Status lower-cased", "status"),
         ("E-mail trimmed and lower-cased", "email"),
         ("Empty rows dropped", "empty"),
         ("Exact duplicate rows merged", "dupes")]


def is_iso_date(s):
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        return False
    try:
        date.fromisoformat(s)
        return True
    except ValueError:
        return False


def norm_date(s):
    """Return YYYY-MM-DD, or None if the text is not a date we can read without guessing.

    Agreed before the run: 03/12/2024 is MM/DD/YYYY, 12.03.2024 is DD.MM.YYYY.
    """
    s = s.strip()
    out = None
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        out = s
    elif m := re.fullmatch(r"(\d{2})\.(\d{2})\.(\d{4})", s):            # 12.03.2024 -> DD.MM.YYYY
        out = f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    elif m := re.fullmatch(r"(\d{2})/(\d{2})/(\d{4})", s):              # 03/12/2024 -> MM/DD/YYYY
        out = f"{m.group(3)}-{m.group(1)}-{m.group(2)}"
    elif m := re.fullmatch(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", s):    # 1 April 2024
        if m.group(2).lower() in MONTHS:
            out = f"{m.group(3)}-{MONTHS[m.group(2).lower()]:02d}-{int(m.group(1)):02d}"
    elif m := re.fullmatch(r"([A-Za-z]+)\s+(\d{1,2}),\s*(\d{4})", s):   # April 1, 2024
        if m.group(1).lower() in MONTHS:
            out = f"{m.group(3)}-{MONTHS[m.group(1).lower()]:02d}-{int(m.group(2)):02d}"
    return out if out and is_iso_date(out) else None


def norm_amount(s):
    """Return the amount as '1299.00', or None if the text is not clearly one number.

    '1.299,00 EUR', 'EUR1,299.00', '1299,00' and '1299' all become '1299.00'.
    An ambiguous value such as '1.299' (1299 or 1.299?) is not guessed.
    """
    t = s.replace(EUR, "").replace("EUR", "").replace("\xa0", " ").strip()
    if re.fullmatch(r"\d{1,3}(\.\d{3})+,\d{2}", t):     # 1.299,00
        t = t.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(,\d{3})+\.\d{2}", t):   # 1,299.00
        t = t.replace(",", "")
    elif re.fullmatch(r"\d+,\d{1,2}", t):               # 1299,00 / 845,5
        t = t.replace(",", ".")
    if not re.fullmatch(r"\d+(\.\d{1,2})?", t):
        return None
    return f"{Decimal(t):.2f}"


LEGAL = {"ltd": "Ltd", "llc": "LLC", "inc": "Inc", "plc": "PLC", "it": "IT", "gmbh": "GmbH", "bv": "BV"}


def norm_company(s):
    """One spelling per company: spaces collapsed, 'and' -> '&', title case, legal forms fixed."""
    t = re.sub(r"\s+", " ", s).strip()
    t = re.sub(r"\band\b", "&", t, flags=re.I)
    t = re.sub(r"\s*&\s*", " & ", t)
    out = []
    for w in t.split(" "):
        lw = w.lower()
        if lw in LEGAL:
            out.append(LEGAL[lw])
        elif w == "&":
            out.append("&")
        else:
            out.append(w[:1].upper() + w[1:].lower())
    return " ".join(out)


def clean_rows(body):
    """Apply all rules to the data rows (header excluded). Returns a result dict."""
    counts = {"dates": 0, "amounts": 0, "company": 0, "status": 0, "email": 0, "empty": 0, "dupes": 0}
    clean, seen, unresolved, examples = [], set(), [], {}

    def ex(key, before, after):
        if key not in examples and before != after:
            examples[key] = (before, after)

    for r in body:
        if not any(c.strip() for c in r):
            counts["empty"] += 1
            continue
        if len(r) != len(COLUMNS):
            unresolved.append((r[0] if r else "", "whole row", ";".join(r)))
            continue
        num, comp, dt, amt, st, mail = r

        c2 = norm_company(comp)
        counts["company"] += (c2 != comp)
        ex("company", comp, c2)

        d2 = norm_date(dt)
        if d2 is None:
            if dt.strip():
                unresolved.append((num, "invoice_date", dt))
            d2 = ""
        else:
            counts["dates"] += (d2 != dt)
            ex("dates", dt, d2)

        a2 = norm_amount(amt)
        if a2 is None:
            if amt.strip():
                unresolved.append((num, "amount", amt))
            a2 = ""
        else:
            counts["amounts"] += (a2 != amt)
            ex("amounts", amt, a2)

        s2 = st.strip().lower()
        counts["status"] += (s2 != st)
        ex("status", st, s2)

        m2 = mail.strip().lower()
        counts["email"] += (m2 != mail)
        ex("email", mail, m2)

        row = (num.strip(), c2, d2, a2, s2, m2)
        if row in seen:                    # identical to a row we already kept
            counts["dupes"] += 1
            continue
        seen.add(row)
        clean.append(list(row))

    return {"rows": clean, "counts": counts, "unresolved": unresolved, "examples": examples}


def main():
    if not SRC.exists():
        sys.exit(f"{SRC} not found - run make_messy.py first")
    with open(SRC, newline="", encoding="utf-8") as fh:
        rows = list(csv.reader(fh, delimiter=";"))
    head, body = rows[0], rows[1:]
    res = clean_rows(body)
    clean, counts, unresolved = res["rows"], res["counts"], res["unresolved"]

    # Checks on the result. If one fails, nothing is written and the run fails.
    bad_dates = [r for r in clean if r[2] and not is_iso_date(r[2])]
    bad_amounts = [r for r in clean if r[3] and not re.fullmatch(r"\d+\.\d{2}", r[3])]
    empty_dates = sum(1 for r in clean if not r[2])
    empty_amounts = sum(1 for r in clean if not r[3])
    if bad_dates or bad_amounts or head != COLUMNS:
        sys.exit(f"CHECK FAILED: {len(bad_dates)} bad dates, {len(bad_amounts)} bad amounts, header {head}")

    total = sum(Decimal(r[3]) for r in clean if r[3])
    raw_sumable = sum(1 for r in body
                      if any(x.strip() for x in r) and len(r) > 3 and re.fullmatch(r"-?\d+(\.\d+)?", r[3].strip()))

    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(head)
        w.writerows(clean)

    def left_empty(n):
        return "" if n == 0 else f" ({n} left empty, see above)"

    lines = ["CHANGE LOG - raw-export.csv -> cleaned-export.csv", "",
             f"Rows in: {len(body)}    Rows out: {len(clean)}", "",
             "RULES APPLIED   (a row can be touched by several rules)"]
    for i, (label, k) in enumerate(RULES, 1):
        lines.append(f"  {i}  {label + ' ' + '.' * (42 - len(label))} {counts[k]} rows")
    lines += ["", "AGREED BEFORE THE RUN",
              "  slash dates read as MM/DD/YYYY, dotted dates as DD.MM.YYYY",
              "  one currency in this file, so only the format was changed",
              "", "LEFT UNTOUCHED ON PURPOSE",
              f"  {len(unresolved)} value(s) could not be read without guessing - left empty, not invented"]
    lines += [f"    customer_id {u[0]}  {u[1]}: {u[2]!r}" for u in unresolved[:20]]
    if len(unresolved) > 20:
        lines.append(f"    ... and {len(unresolved) - 20} more")
    lines += ["", "CHECKS RUN ON THE RESULT",
              f"  {len(clean)} rows, {len(head)} columns",
              f"  all values in invoice_date are valid YYYY-MM-DD dates{left_empty(empty_dates)}",
              f"  all values in amount parse as numbers{left_empty(empty_amounts)}",
              f"  sum of amount = {total:,.2f}  (compare with your own total)",
              f"  before cleaning only {raw_sumable} of {len(body)} rows could be summed at all"]
    LOG.write_text("\n".join(lines) + "\n", encoding="utf-8")

    raw_names = {r[1] for r in body if len(r) > 1 and r[1].strip()}
    clean_names = {r[1] for r in clean}
    facts = {"rows_in": len(body), "rows_out": len(clean), "counts": counts,
             "names_raw": len(raw_names), "names_clean": len(clean_names), "raw_sumable": raw_sumable,
             "unresolved": len(unresolved), "total": f"{total:,.2f}",
             "cols": len(head), "examples": res["examples"],
             "rules": [(label, counts[k]) for label, k in RULES]}
    FACTS.write_text(json.dumps(facts, indent=1) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
