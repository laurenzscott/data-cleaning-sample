# data-cleaning-sample

Cleaning a messy invoice export with fixed, written-down rules and a change log.

This is a sample on generated data, not a client project.

## The problem

An export that several people and systems have touched: the same company spelled
three different ways, dates in five formats, amounts written as `1.299,00 €`,
`€1,299.00` or `1299,00`, statuses in random capitals, e-mail addresses with
stray spaces, empty rows and duplicated rows. Before cleaning, only 2,593 of the
9,612 rows had an amount that a spreadsheet could add up.

## Rules applied

1. Dates normalised to `YYYY-MM-DD` (agreed beforehand: `03/12/2024` is
   month/day/year, `12.03.2024` is day.month.year)
2. Amounts converted from text to plain numbers (`1299.00`), one currency, so only
   the format changes
3. Company names unified (spaces, capitals, "and" vs "&", legal forms like `Ltd`)
4. Status lower-cased (`open`, `paid`)
5. E-mail addresses trimmed and lower-cased
6. Empty rows dropped
7. Exact duplicate rows merged

Nothing invented: values that cannot be read are left empty and counted.
An ambiguous amount such as `1.299` or an impossible date such as `31.02.2024`
is not guessed. It is left empty and listed in the change log with its
customer_id and the original text.

## Before and after (last run)

| | Before | After |
|---|---|---|
| Rows | 9,612 | 9,341 |
| Company spellings | 18 | 10 |
| Rows whose amount can be summed | 2,593 | 9,341 |
| Values left empty (not readable) | - | 0 |

Changes per rule: dates 6,608 rows, amounts 8,477, company names 4,696,
status 6,271, e-mail 6,258, empty rows dropped 259, duplicates merged 12.
Sum of all amounts after cleaning: 11,556,507.40.

Five rows from the generated export, before:

```
customer_id;company;invoice_date;amount;status;email
10001;Castle and Byrne;1 April 2024;1.045,00 €;open;INFO@client1.COM
10005;Pike & Sons;12.03.2024;99,90 €;open; contact@client5.com 
10010;Northwind  Trading;03/12/2024;€1,299.00;Paid;info@client10.com
10013;Pike and Sons;2024-04-01;2.100,00 €;Open;INFO@client13.COM
10015;harbour logistics;2024-04-01;EUR 1.299,00;Paid;info@client15.com
```

and after:

```
customer_id,company,invoice_date,amount,status,email
10001,Castle & Byrne,2024-04-01,1045.00,open,info@client1.com
10005,Pike & Sons,2024-03-12,99.90,open,contact@client5.com
10010,Northwind Trading,2024-03-12,1299.00,paid,info@client10.com
10013,Pike & Sons,2024-04-01,2100.00,open,info@client13.com
10015,Harbour Logistics,2024-04-01,1299.00,paid,info@client15.com
```

## Files

- `make_messy.py` writes `data/raw-export.csv` (generated with a fixed seed, so
  every run gives the same file)
- `clean.py` reads it and writes:
  - `data/cleaned-export.csv` - the cleaned rows
  - `data/change-log.txt` - every rule with the number of rows it changed, what
    was left empty and why, and the checks run on the result (row count, all
    dates valid, all amounts numeric, the total to compare with your own)
  - `data/facts.json` - the same numbers, machine-readable
- `tests/test_clean.py` checks each rule on a few handcrafted rows

The `data/` folder is created and updated by the GitHub Action, not by hand.

## Run it locally

Python 3.12, standard library only, nothing to install:

```
python tests/test_clean.py
python make_messy.py && python clean.py
```

## Run it on GitHub

Actions -> "Clean the export" -> Run workflow. The workflow runs the tests first
(and stops if one fails), then generates the export, cleans it and commits the
updated `data/` folder. It also runs on every push to `main` that changes a
`.py` file.
