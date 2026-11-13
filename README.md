# 🧾 Ah Beng Cash Receipting System

A simple cash receipting and sales reconciliation system for hawker centre stalls, built with **Python** and **Streamlit**.

It was designed for a small vegetarian food stall ("Ah Beng Vegetarian Food"): the stall owner records each sale, the system calculates the change due, and daily and monthly reports show how much was sold and how customers paid. All data is kept in one plain CSV file, so there is no database to set up.

> Course project for **AN6100 Programming Essentials** (Assignment & Presentation Part 3, 2026).

## Features

**🧾 New Transaction**
- Record a sale with business date, payment type and amount
- Supports the four common Singapore hawker payment methods: **Cash, PayNow, PayLah!, payWave**
- Change is calculated automatically for cash payments; the system warns when the amount rendered is short
- "Today at a glance" shows today's sales and the last transaction

**📅 Daily Report**
- Totals for a chosen day: transactions, sales, amount rendered and change returned
- Filter by payment type
- Payment breakdown donut chart with per-payment cards
- Daily sales trend chart across all recorded days (10-day window with a slider)
- Best business day and average sales per day
- Download the payment summary and transaction listing as CSV

**📊 Monthly Report**
- Choose any date range and payment types
- Sales-by-month bar chart, best month and monthly average
- Monthly sales split by payment type, plus a daily sales summary
- CSV export for every summary table

**✏️ Manage Transactions**
- Edit a recorded receipt (date, payment type, amounts); change is recalculated
- Delete an incorrect receipt, with a confirmation step

## Project structure

```
ah-beng-receipting/
├── app.py                  # The whole application (logic + Streamlit UI)
├── data/
│   └── transactions.csv    # Sales records (includes sample data)
├── .streamlit/
│   └── config.toml         # Green theme and server settings
├── requirements.txt
└── README.md
```

## Getting started

Requirements: Python 3 and Streamlit 1.50 or newer.

```bash
git clone https://github.com/<your-username>/ah-beng-receipting.git
cd ah-beng-receipting
python3 -m pip install -r requirements.txt
python3 -m streamlit run app.py
```

Then open http://localhost:8501 in your browser. Press `Ctrl + C` in the terminal to stop the app.

Run the command from the project folder so Streamlit picks up the theme in `.streamlit/config.toml`.

## Data file

Every sale is stored in `data/transactions.csv` with these columns:

| Column | Meaning |
| --- | --- |
| `transaction_id` | Receipt number, e.g. `R20260926134255115885` |
| `timestamp` | When the sale was recorded (`YYYY-MM-DD HH:MM:SS`) |
| `business_date` | The trading day the sale belongs to |
| `sale_amount` | Sale amount (S$) |
| `amount_rendered` | Amount the customer gave (equals the sale for electronic payments) |
| `change_amount` | Change returned (0.00 for electronic payments) |
| `payment_type` | `Cash`, `PayNow`, `PayLah!` or `payWave` |

Notes:
- The file ships with sample sales from August–September 2026. Delete it to start fresh; a new file is created when the first sale is recorded.
- Do not rename the columns — the app checks the header when loading.
- Stop the app before opening or copying the CSV file.

## Tech stack

- Python 3 (standard library `csv`, `datetime`, `os`)
- Streamlit for the web interface
- Vega-Lite (via `st.vega_lite_chart`) and inline SVG / CSS for charts
