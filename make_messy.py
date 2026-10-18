"""Builds a realistic messy invoice export: data/raw-export.csv

The data is generated, not real. The seed is fixed, so every run produces
exactly the same file (9,612 rows including 12 duplicates and 259 empty rows).
"""
import csv
import random
from pathlib import Path

OUT = Path(__file__).resolve().parent / "data" / "raw-export.csv"
EUR = "\u20ac"  # the euro sign, written as an escape so this file stays plain ASCII

random.seed(7)

companies = ["Harbour Logistics", "HARBOUR LOGISTICS", "harbour logistics",
             "Castle & Byrne", "Castle and Byrne", "Northwind Trading", "Northwind  Trading",
             "Ferris Medical", "FERRIS MEDICAL", "Avoncroft Ltd", "avoncroft ltd",
             "Hensley IT", "Hensley it", "Pike & Sons", "Pike and Sons",
             "Delaney Print", "Oakmere Energy", "Quill Stationery "]

# One currency, five ways of writing it. This is what a real export looks like
# when three people and two systems have touched the same column.
amounts = ["1.299,00 " + EUR, EUR + "1,299.00", "1299,00", "1299.00", "EUR 1.299,00",
           "845,50 " + EUR, "845.5", "2.100,00 " + EUR, "2100", "99,90 " + EUR, "1.045,00 " + EUR]

dates = ["12.03.2024", "2024-03-12", "03/12/2024", "1 April 2024", "2024-04-01",
         "April 1, 2024", "04/01/2024"]

statuses = ["open", "OPEN", "Open", "paid", "Paid", "PAID"]

rows = [["customer_id", "company", "invoice_date", "amount", "status", "email"]]
for i in range(1, 9601):
    if i % 37 == 0:                                   # empty rows, as exports have
        rows.append(["", "", "", "", "", ""])
        continue
    mail = random.choice(["info@%s.com", "INFO@%s.COM", " contact@%s.com "]) % ("client%d" % (i % 240))
    rows.append([str(10000 + i), random.choice(companies), random.choice(dates),
                 random.choice(amounts), random.choice(statuses), mail])

for k in (5, 48, 102, 177, 903, 1544, 2810, 4112, 5390, 6677, 7901, 9120):   # genuine duplicate rows
    rows.append(list(rows[k]))

OUT.parent.mkdir(exist_ok=True)
with open(OUT, "w", newline="", encoding="utf-8") as fh:
    csv.writer(fh, delimiter=";").writerows(rows)
print("raw:", len(rows) - 1, "rows ->", OUT.relative_to(OUT.parent.parent))
