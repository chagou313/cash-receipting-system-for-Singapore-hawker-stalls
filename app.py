"""
# AN6100 Programming Essential 
# Assignment & Presentation Part 3 ——Simple Streamlit cash receipting system for Ah Beng's food stall.
# 2026

# Class Number             :Section B
# Name                     :Xu Jie                     
# Presentation Video link  :https://www.dropbox.com/scl/fi/nu4v98gjgoao42kcceb4t/SB_Xu_Jie.mp4?rlkey=dqbxyini89w78gf83qezs5jct&st=9p7yv226&dl=0
"""

import csv
from datetime import date, datetime
import os

import streamlit as st


APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(APP_DIR, "data", "transactions.csv")
PAYMENT_TYPES = ("Cash", "PayNow", "PayLah!", "payWave")
PAYMENT_VISUALS = {
    "Cash": {"icon": "💵", "color": "#2E7D32"},
    "PayNow": {"icon": "📱", "color": "#E5484D"},
    "PayLah!": {"icon": "💜", "color": "#7C3AED"},
    "payWave": {"icon": "💳", "color": "#0284C7"},
}
MENU_ICONS = {
    "New Transaction": "🧾",
    "Daily Report": "📅",
    "Monthly Report": "📊",
    "Manage Transactions": "✏️",
}
FIELDNAMES = (
    "transaction_id", "timestamp", "business_date", "sale_amount",
    "amount_rendered", "change_amount", "payment_type",
)
COLUMN_LABELS = {
    "transaction_id": "Receipt No.",
    "timestamp": "Recorded At",
    "business_date": "Business Date",
    "sale_amount": "Sale Amount (S$)",
    "amount_rendered": "Amount Rendered (S$)",
    "change_amount": "Change Returned (S$)",
    "payment_type": "Payment Type",
}

APP_CSS = """
<style>
.block-container { padding-top: 2rem; max-width: 1180px; font-size: 18px; }
h1 { font-size: 42px !important; }
h2 { font-size: 32px !important; }
h3 { font-size: 25px !important; }
p, label, [data-testid="stCaptionContainer"] { font-size: 18px !important; }
[data-testid="stSidebar"] * { font-size: 18px !important; }
[data-testid="stSidebar"] [role="radiogroup"] { gap: 8px; }
[data-testid="stSidebar"] [role="radiogroup"] > label {
    border: 1px solid transparent; border-radius: 13px; cursor: pointer;
    min-height: 54px; padding: 10px 13px; width: 100%;
}
[data-testid="stSidebar"] [role="radiogroup"] > label:hover {
    background: #eaf4e8; border-color: #c9ddc6;
}
[data-testid="stSidebar"] [role="radiogroup"] > label:has(input:checked) {
    background: #e5f3e2; border-color: #77ad72;
}
[data-testid="stSidebar"] [role="radiogroup"] > label:has(input:checked) p {
    color: #1f6d35; font-weight: 750;
}
[data-testid="stWidgetLabel"] p { font-size: 18px !important; font-weight: 600; }
input, [data-baseweb="select"] * { font-size: 18px !important; }
.stButton button, .stDownloadButton button { font-size: 18px !important; min-height: 3rem; }
[data-testid="stMetric"] {
    background: #f7faf7; border: 1px solid #dce8dc;
    padding: 1rem; border-radius: 0.7rem;
}
[data-testid="stMetricLabel"] p { font-size: 18px !important; }
[data-testid="stMetricValue"] { font-size: 34px !important; }
</style>
"""


# ---------------------------- Basic helpers ----------------------------

def money(value):
    """Convert a value to a non-negative amount rounded to two places."""
    try:
        amount = round(float(value), 2)
    except (TypeError, ValueError):
        raise ValueError("Enter a valid amount.")
    if amount < 0:
        raise ValueError("Amount cannot be negative.")
    return amount


def currency(value):
    return f"S${money(value):,.2f}"


def transaction_timestamp(row):
    return row["timestamp"]


def summary_total_sales(row):
    return money(row["total_sales"])


def format_payment_option(name):
    return f"{PAYMENT_VISUALS[name]['icon']}  {name}"


def format_menu_option(name):
    return f"{MENU_ICONS[name]}  {name}"


def rows_to_csv(rows):
    """Convert dictionaries to a CSV string for Streamlit downloads."""
    if not rows:
        return ""
    headings = list(rows[0].keys())
    csv_lines = [",".join(headings)]
    for row in rows:
        values = []
        for heading in headings:
            value = str(row.get(heading, ""))
            value = value.replace('"', '""')
            if "," in value or '"' in value or "\n" in value:
                value = '"' + value + '"'
            values.append(value)
        csv_lines.append(",".join(values))
    return "\n".join(csv_lines)


def payment_slug(payment_filters):
    if set(payment_filters) == set(PAYMENT_TYPES):
        return "all_payments"
    names = []
    for name in payment_filters:
        names.append(name.lower().replace(" ", "_").replace("!", ""))
    return "-".join(names)


# ---------------------------- Transaction rules ----------------------------

def calculate_change(payment_type, sale_amount, amount_rendered=None):
    if payment_type not in PAYMENT_TYPES:
        raise ValueError("Select a valid payment type.")
    sale = money(sale_amount)
    if sale <= 0:
        raise ValueError("Sale amount must be greater than zero.")
    if payment_type != "Cash":
        return 0.0
    rendered = money(amount_rendered)
    if rendered < sale:
        raise ValueError("Amount rendered must be at least the sale amount.")
    return round(rendered - sale, 2)


def build_transaction(sale_amount, amount_rendered, payment_type,
                      business_date=None, now=None, transaction_id=None):
    sale = money(sale_amount)
    if sale <= 0:
        raise ValueError("Sale amount must be greater than zero.")
    change = calculate_change(payment_type, sale, amount_rendered)
    if payment_type == "Cash":
        rendered = money(amount_rendered)
    else:
        rendered = sale
    transaction_time = now or datetime.now()
    sale_date = business_date or date.today()
    receipt_number = transaction_id
    if not receipt_number:
        receipt_number = "R" + transaction_time.strftime("%Y%m%d%H%M%S%f")
    return {
        "transaction_id": receipt_number,
        "timestamp": transaction_time.strftime("%Y-%m-%d %H:%M:%S"),
        "business_date": sale_date.isoformat(),
        "sale_amount": f"{sale:.2f}",
        "amount_rendered": f"{rendered:.2f}",
        "change_amount": f"{change:.2f}",
        "payment_type": payment_type,
    }


# ---------------------------- CSV text storage ----------------------------

def csv_row(transaction):
    return {
        "transaction_id": transaction["transaction_id"],
        "timestamp": transaction["timestamp"],
        "business_date": transaction["business_date"],
        "sale_amount": f"{money(transaction['sale_amount']):.2f}",
        "amount_rendered": f"{money(transaction['amount_rendered']):.2f}",
        "change_amount": f"{money(transaction['change_amount']):.2f}",
        "payment_type": transaction["payment_type"],
    }


def save_transaction(csv_path, transaction):
    folder = os.path.dirname(csv_path)
    if folder and not os.path.exists(folder):
        os.makedirs(folder)
    write_header = not os.path.exists(csv_path) or os.path.getsize(csv_path) == 0
    with open(csv_path, "a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDNAMES)
        if write_header:
            writer.writeheader()
        writer.writerow(csv_row(transaction))


def load_transactions(csv_path):
    if not os.path.exists(csv_path) or os.path.getsize(csv_path) == 0:
        return []
    transactions = []
    with open(csv_path, newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        if tuple(reader.fieldnames or ()) != FIELDNAMES:
            raise ValueError("The transactions file has an invalid or missing header.")
        line_number = 1
        for row in reader:
            line_number += 1
            try:
                if row["payment_type"] not in PAYMENT_TYPES:
                    raise ValueError("Invalid payment type")
                datetime.strptime(row["timestamp"], "%Y-%m-%d %H:%M:%S")
                date.fromisoformat(row["business_date"])
                row["sale_amount"] = f"{money(row['sale_amount']):.2f}"
                row["amount_rendered"] = f"{money(row['amount_rendered']):.2f}"
                row["change_amount"] = f"{money(row['change_amount']):.2f}"
            except (KeyError, TypeError, ValueError):
                raise ValueError(f"Invalid transaction data on CSV line {line_number}.")
            transactions.append(row)
    return transactions


def replace_transactions(csv_path, transactions):
    folder = os.path.dirname(csv_path)
    if folder and not os.path.exists(folder):
        os.makedirs(folder)
    with open(csv_path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDNAMES)
        writer.writeheader()
        for row in transactions:
            writer.writerow(csv_row(row))


def delete_transaction(csv_path, transaction_id):
    transactions = load_transactions(csv_path)
    remaining = []
    removed = False
    for row in transactions:
        if row["transaction_id"] == transaction_id:
            removed = True
        else:
            remaining.append(row)
    if removed:
        replace_transactions(csv_path, remaining)
    return removed


def update_transaction(csv_path, transaction_id, sale_amount, amount_rendered,
                       payment_type, business_date):
    transactions = load_transactions(csv_path)
    for index in range(len(transactions)):
        original = transactions[index]
        if original["transaction_id"] == transaction_id:
            transactions[index] = build_transaction(
                sale_amount, amount_rendered, payment_type, business_date,
                datetime.strptime(original["timestamp"], "%Y-%m-%d %H:%M:%S"),
                original["transaction_id"],
            )
            replace_transactions(csv_path, transactions)
            return True
    return False


# ---------------------------- Report calculations ----------------------------

def daily_transactions(transactions, selected_date):
    target = selected_date.isoformat()
    rows = []
    for row in transactions:
        if row["business_date"] == target:
            rows.append(row)
    return sorted(rows, key=transaction_timestamp)


def filter_transactions_by_payment(transactions, payment_filter):
    if payment_filter == "All payment types":
        return list(transactions)
    if isinstance(payment_filter, (list, tuple, set)):
        selected_payments = set(payment_filter)
    else:
        selected_payments = {payment_filter}
    rows = []
    for row in transactions:
        if row["payment_type"] in selected_payments:
            rows.append(row)
    return rows


def available_payment_types(transactions):
    """List payment types that occur in the supplied transactions."""
    types_found = []
    for payment_type in PAYMENT_TYPES:
        for row in transactions:
            if row["payment_type"] == payment_type:
                types_found.append(payment_type)
                break
    return types_found


def sync_payment_filter_state(state, widget_key, options_key, available_types):
    """Reset a payment selection only when its available options change."""
    current_options = state.get(options_key)
    if current_options != available_types:
        state[widget_key] = list(available_types)
        state[options_key] = list(available_types)
    elif widget_key not in state:
        state[widget_key] = list(available_types)


def filter_transactions_by_date_range(transactions, start_date, end_date,
                                      payment_filter="All payment types"):
    if isinstance(start_date, date):
        start_key = start_date.isoformat()
    else:
        start_key = str(start_date)
    if isinstance(end_date, date):
        end_key = end_date.isoformat()
    else:
        end_key = str(end_date)
    rows = []
    for row in transactions:
        if start_key <= row["business_date"] <= end_key:
            rows.append(row)
    return filter_transactions_by_payment(rows, payment_filter)


def daily_totals(transactions):
    total_sales = 0.0
    total_rendered = 0.0
    total_change = 0.0
    for row in transactions:
        total_sales += money(row["sale_amount"])
        total_rendered += money(row["amount_rendered"])
        total_change += money(row["change_amount"])
    return {
        "transaction_count": len(transactions),
        "total_sales": round(total_sales, 2),
        "total_rendered": round(total_rendered, 2),
        "total_change": round(total_change, 2),
    }


def homepage_summary(transactions, selected_date=None):
    target_date = selected_date or date.today()
    today_rows = daily_transactions(transactions, target_date)
    today_total = 0.0
    for row in today_rows:
        today_total += money(row["sale_amount"])
    last_row = None
    if transactions:
        last_row = max(transactions, key=transaction_timestamp)
    return {
        "today_sales": round(today_total, 2),
        "today_transactions": len(today_rows),
        "last_sale": money(last_row["sale_amount"]) if last_row else None,
        "last_payment_type": last_row["payment_type"] if last_row else None,
        "last_transaction_id": last_row["transaction_id"] if last_row else None,
    }


def monthly_transactions(transactions, year, month):
    prefix = f"{int(year):04d}-{int(month):02d}-"
    rows = []
    for row in transactions:
        if row["business_date"].startswith(prefix):
            rows.append(row)
    return rows


def yearly_transactions(transactions, year):
    prefix = f"{int(year):04d}-"
    rows = []
    for row in transactions:
        if row["business_date"].startswith(prefix):
            rows.append(row)
    return rows


def filter_monthly_transactions(transactions, year, month_filter="All months",
                                payment_filter="All payment types"):
    rows = yearly_transactions(transactions, year)
    if month_filter != "All months":
        if isinstance(month_filter, (list, tuple, set)):
            selected_months = set(month_filter)
        else:
            selected_months = {month_filter}
        month_rows = []
        for row in rows:
            if int(row["business_date"][5:7]) in selected_months:
                month_rows.append(row)
        rows = month_rows
    return filter_transactions_by_payment(rows, payment_filter)


def period_daily_summary(transactions):
    grouped = {}
    for row in transactions:
        business_date = row["business_date"]
        if business_date not in grouped:
            grouped[business_date] = {"transaction_count": 0, "total_sales": 0.0}
        grouped[business_date]["transaction_count"] += 1
        grouped[business_date]["total_sales"] += money(row["sale_amount"])
    summary = []
    for business_date in sorted(grouped):
        summary.append({
            "business_date": business_date,
            "transaction_count": grouped[business_date]["transaction_count"],
            "total_sales": round(grouped[business_date]["total_sales"], 2),
        })
    return summary


def filtered_daily_history(transactions, payment_filter):
    """Summarise every recorded business day for the selected payments."""
    filtered_rows = filter_transactions_by_payment(transactions, payment_filter)
    return period_daily_summary(filtered_rows)


def monthly_daily_summary(transactions, year, month):
    return period_daily_summary(monthly_transactions(transactions, year, month))


def period_month_summary(transactions):
    payment_keys = {
        "Cash": "cash_sales", "PayNow": "paynow_sales",
        "PayLah!": "paylah_sales", "payWave": "paywave_sales",
    }
    grouped = {}
    for row in transactions:
        month_key = row["business_date"][:7]
        if month_key not in grouped:
            first_day = date(int(month_key[:4]), int(month_key[5:7]), 1)
            grouped[month_key] = {
                "month_key": month_key,
                "month_label": first_day.strftime("%B %Y"),
                "transaction_count": 0,
                "cash_sales": 0.0, "paynow_sales": 0.0,
                "paylah_sales": 0.0, "paywave_sales": 0.0,
                "total_sales": 0.0,
            }
        group = grouped[month_key]
        sale = money(row["sale_amount"])
        group["transaction_count"] += 1
        group[payment_keys[row["payment_type"]]] += sale
        group["total_sales"] += sale
    summary = []
    for month_key in sorted(grouped):
        row = grouped[month_key]
        for key in payment_keys.values():
            row[key] = round(row[key], 2)
        row["total_sales"] = round(row["total_sales"], 2)
        summary.append(row)
    return summary


def yearly_month_summary(transactions, year):
    summary = period_month_summary(yearly_transactions(transactions, year))
    for row in summary:
        first_day = date(int(row["month_key"][:4]), int(row["month_key"][5:7]), 1)
        row["month_label"] = first_day.strftime("%B")
    return summary


def payment_summary(transactions):
    grouped = {}
    for row in transactions:
        payment_type = row["payment_type"]
        if payment_type not in grouped:
            grouped[payment_type] = {"transaction_count": 0, "total_sales": 0.0}
        grouped[payment_type]["transaction_count"] += 1
        grouped[payment_type]["total_sales"] += money(row["sale_amount"])
    summary = []
    for payment_type in PAYMENT_TYPES:
        if payment_type in grouped:
            summary.append({
                "payment_type": payment_type,
                "transaction_count": grouped[payment_type]["transaction_count"],
                "total_sales": round(grouped[payment_type]["total_sales"], 2),
            })
    return summary


def daily_payment_summary(transactions, selected_date):
    return payment_summary(daily_transactions(transactions, selected_date))


def monthly_payment_summary(transactions, year, month):
    return payment_summary(monthly_transactions(transactions, year, month))


def payment_display_rows(summary, payment_filter="All payment types"):
    by_type = {}
    total = 0.0
    for row in summary:
        by_type[row["payment_type"]] = row
        total += money(row["total_sales"])
    display = []
    for payment_type in PAYMENT_TYPES:
        transaction_count = 0
        sales = 0.0
        if payment_type in by_type:
            transaction_count = by_type[payment_type]["transaction_count"]
            sales = money(by_type[payment_type]["total_sales"])
        percentage = 0.0
        if total > 0:
            percentage = round(sales / total * 100, 1)
        display.append({
            "payment_type": payment_type,
            "transaction_count": transaction_count,
            "total_sales": sales,
            "percentage": percentage,
            "icon": PAYMENT_VISUALS[payment_type]["icon"],
            "color": PAYMENT_VISUALS[payment_type]["color"],
        })
    if payment_filter == "All payment types":
        return display
    if isinstance(payment_filter, (list, tuple, set)):
        selected_payments = set(payment_filter)
    else:
        selected_payments = {payment_filter}
    filtered = []
    for row in display:
        if row["payment_type"] in selected_payments:
            filtered.append(row)
    return filtered


def payment_summary_frame(summary, payment_filter="All payment types"):
    rows = payment_display_rows(summary, payment_filter)
    table = []
    for row in rows:
        table.append({
            "Payment Type": row["payment_type"],
            "Transactions": row["transaction_count"],
            "Total Sales (S$)": f"{row['total_sales']:.2f}",
        })
    return table


def active_payment_rows(rows):
    """Return only payment types that have sales in the current selection."""
    active_rows = []
    for row in rows:
        if money(row["total_sales"]) > 0:
            active_rows.append(row)
    return active_rows


def payment_donut_gradient(rows):
    """Build the colour stops used by the payment breakdown ring."""
    total = 0.0
    for row in rows:
        total += money(row["total_sales"])
    if total <= 0:
        return "#E5E7EB 0% 100%"
    stops = []
    start = 0.0
    for row in rows:
        share = money(row["total_sales"]) / total * 100
        end = start + share
        stops.append(f"{row['color']} {start:.1f}% {end:.1f}%")
        start = end
    return ", ".join(stops)


def daily_summary_frame(day_summary):
    table = []
    for row in day_summary:
        table.append({
            "Business Date": row["business_date"],
            "Transactions": row["transaction_count"],
            "Total Sales (S$)": f"{row['total_sales']:.2f}",
        })
    return table


def daily_trend_chart_rows(day_summary):
    """Prepare a continuous date axis so chart labels remain horizontal."""
    chart_rows = []
    for row in day_summary:
        chart_rows.append({
            "Business Date": date.fromisoformat(row["business_date"]),
            "Sales": money(row["total_sales"]),
        })
    return chart_rows


def daily_trend_window(day_summary, start_index, window_size=10):
    """Return one fixed-size section of the daily trend."""
    if not day_summary:
        return []
    maximum_start = max(0, len(day_summary) - window_size)
    start = int(start_index)
    if start < 0:
        start = 0
    if start > maximum_start:
        start = maximum_start
    return day_summary[start:start + window_size]


def daily_trend_chart_html(day_summary):
    """Create a fixed-size sales chart with visible values at every point."""
    if not day_summary:
        return ""
    chart_width = 900
    chart_height = 390
    left_margin = 70
    right_margin = 30
    top_margin = 25
    bottom_margin = 70
    plot_width = chart_width - left_margin - right_margin
    plot_height = chart_height - top_margin - bottom_margin

    highest_sale = 0.0
    for row in day_summary:
        sale = money(row["total_sales"])
        if sale > highest_sale:
            highest_sale = sale
    axis_max = int(highest_sale)
    if axis_max < highest_sale:
        axis_max += 1
    if axis_max < 5:
        axis_max = 5
    remainder = axis_max % 5
    if remainder:
        axis_max += 5 - remainder

    grid_parts = []
    for level in range(6):
        value = axis_max * level / 5
        y_position = top_margin + plot_height - (plot_height * level / 5)
        grid_parts.append(
            f"<line x1='{left_margin}' y1='{y_position:.1f}' "
            f"x2='{chart_width - right_margin}' y2='{y_position:.1f}' "
            f"stroke='#dfe8df' stroke-width='1' />"
            f"<text x='{left_margin - 12}' y='{y_position + 5:.1f}' "
            f"text-anchor='end' font-size='14' fill='#718075'>{value:g}</text>"
        )

    point_parts = []
    label_parts = []
    coordinates = []
    if len(day_summary) == 1:
        x_step = 0
    else:
        x_step = plot_width / (len(day_summary) - 1)
    for index in range(len(day_summary)):
        row = day_summary[index]
        sale = money(row["total_sales"])
        if len(day_summary) == 1:
            x_position = left_margin + plot_width / 2
        else:
            x_position = left_margin + index * x_step
        y_position = top_margin + plot_height - (sale / axis_max * plot_height)
        coordinates.append(f"{x_position:.1f},{y_position:.1f}")
        date_label = date.fromisoformat(row["business_date"]).strftime("%d %b")
        point_parts.append(
            f"<circle cx='{x_position:.1f}' cy='{y_position:.1f}' r='5' "
            f"fill='#2E7D32' stroke='white' stroke-width='2'>"
            f"<title>{date_label} · {currency(sale)}</title></circle>"
            f"<text x='{x_position:.1f}' y='{y_position - 12:.1f}' "
            f"text-anchor='middle' font-size='13' font-weight='700' "
            f"fill='#2E7D32'>{currency(sale)}</text>"
        )
        label_parts.append(
            f"<text x='{x_position:.1f}' y='{chart_height - 31}' "
            f"text-anchor='middle' font-size='14' fill='#667269'>{date_label}</text>"
        )

    return (
        "<div style='width:100%; padding:4px 0 8px; border-bottom:1px solid #dce8dc;'>"
        f"<svg style='width:100%; height:auto; display:block;' "
        f"viewBox='0 0 {chart_width} {chart_height}' xmlns='http://www.w3.org/2000/svg'>"
        + "".join(grid_parts)
        + f"<polyline points='{' '.join(coordinates)}' fill='none' stroke='#2E7D32' "
        + "stroke-width='4' stroke-linecap='round' stroke-linejoin='round' />"
        + "".join(point_parts)
        + "".join(label_parts)
        + f"<text x='{chart_width / 2:.1f}' y='{chart_height - 4}' text-anchor='middle' "
        + "font-size='16' font-weight='600' fill='#465249'>Business Date</text>"
        + f"<text x='18' y='{chart_height / 2:.1f}' text-anchor='middle' "
        + "font-size='16' font-weight='600' fill='#465249' "
        + f"transform='rotate(-90 18 {chart_height / 2:.1f})'>Sales (S$)</text>"
        + "</svg></div>"
    )


def month_summary_frame(month_summary):
    chart_rows = []
    for row in month_summary:
        month_date = date.fromisoformat(row["month_key"] + "-01")
        month_label = month_date.strftime("%b %y")
        chart_rows.append({"Month": month_label, "Sales": money(row["total_sales"])})
    return chart_rows


def month_chart_spec(month_summary):
    return {
        "data": {"values": month_summary_frame(month_summary)},
        "mark": {
            "type": "bar",
            "color": "#2E7D32",
            "cornerRadiusTopLeft": 7,
            "cornerRadiusTopRight": 7,
        },
        "encoding": {
            "x": {
                "field": "Month",
                "type": "nominal",
                "sort": None,
                "axis": {
                    "title": "Month",
                    "labelAngle": 0,
                    "labelPadding": 12,
                },
            },
            "y": {
                "field": "Sales",
                "type": "quantitative",
                "axis": {"title": "Sales (S$)"},
            },
            "tooltip": [
                {"field": "Month", "type": "nominal"},
                {"field": "Sales", "type": "quantitative", "format": ".2f"},
            ],
        },
        "height": 420,
    }


def monthly_summary_table(month_summary):
    table = []
    for row in month_summary:
        table.append({
            "Month": row["month_label"],
            "Transactions": row["transaction_count"],
            "Cash (S$)": f"{row['cash_sales']:.2f}",
            "PayNow (S$)": f"{row['paynow_sales']:.2f}",
            "PayLah! (S$)": f"{row['paylah_sales']:.2f}",
            "payWave (S$)": f"{row['paywave_sales']:.2f}",
            "Total Sales (S$)": f"{row['total_sales']:.2f}",
        })
    return table


def daily_trend_stats(day_summary):
    if not day_summary:
        return {"best_date": None, "best_sales": 0.0, "average_sales": 0.0}
    best_row = max(day_summary, key=summary_total_sales)
    total = 0.0
    for row in day_summary:
        total += money(row["total_sales"])
    return {
        "best_date": best_row["business_date"],
        "best_sales": money(best_row["total_sales"]),
        "average_sales": round(total / len(day_summary), 2),
    }


def display_rows(rows):
    display = []
    for row in rows:
        display.append({
            COLUMN_LABELS["transaction_id"]: row["transaction_id"],
            COLUMN_LABELS["timestamp"]: row["timestamp"],
            COLUMN_LABELS["business_date"]: row["business_date"],
            COLUMN_LABELS["sale_amount"]: f"{money(row['sale_amount']):.2f}",
            COLUMN_LABELS["amount_rendered"]: f"{money(row['amount_rendered']):.2f}",
            COLUMN_LABELS["change_amount"]: f"{money(row['change_amount']):.2f}",
            COLUMN_LABELS["payment_type"]: row["payment_type"],
        })
    return display


# ---------------------------- Streamlit interface ----------------------------

def load_data():
    try:
        return load_transactions(DATA_FILE)
    except (OSError, ValueError) as error:
        st.error(f"Unable to read the transaction file: {error}")
        st.stop()


def render_payment_dashboard(summary, heading, payment_filter="All payment types"):
    st.subheader(heading)
    rows = payment_display_rows(summary, payment_filter)
    active_rows = active_payment_rows(rows)
    total_sales = 0.0
    for row in active_rows:
        total_sales += money(row["total_sales"])
    chart_column, card_column = st.columns([0.9, 1.1], gap="large")
    with chart_column:
        if active_rows:
            gradient = payment_donut_gradient(active_rows)
            st.markdown(
                f"""
                <div style="display:flex; justify-content:center; padding:14px 0 8px;">
                    <div style="width:280px; height:280px; border-radius:50%;
                                background:conic-gradient({gradient}); padding:30px;
                                box-shadow:0 14px 35px rgba(31,77,48,0.13);">
                        <div style="height:100%; border-radius:50%; background:white;
                                    display:flex; flex-direction:column; align-items:center;
                                    justify-content:center; box-shadow:inset 0 0 0 1px #e3ece3;">
                            <div style="font-size:34px; line-height:1; font-weight:800;
                                        color:#153f22;">{currency(total_sales)}</div>
                            <div style="font-size:17px; color:#718075; margin-top:10px;">
                                Total sales
                            </div>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            legend_parts = []
            for row in active_rows:
                share = row["total_sales"] / total_sales * 100
                legend_parts.append(
                    f"<span style='display:inline-flex; align-items:center; gap:7px; "
                    f"margin:6px 12px; color:#465249; font-size:16px;'>"
                    f"<span style='width:11px; height:11px; border-radius:50%; "
                    f"background:{row['color']};'></span>{row['payment_type']} "
                    f"<strong>{share:.1f}%</strong></span>"
                )
            st.markdown(
                "<div style='text-align:center; margin-bottom:10px;'>" +
                "".join(legend_parts) + "</div>",
                unsafe_allow_html=True,
            )
        else:
            st.info("No sales are available for this selection.")
    with card_column:
        for row in active_rows:
            if row["transaction_count"] == 1:
                transaction_word = "transaction"
            else:
                transaction_word = "transactions"
            share = row["total_sales"] / total_sales * 100
            st.markdown(
                f"""
                <div style="border:1px solid #dce8dc; border-left:7px solid {row['color']};
                            border-radius:17px; padding:18px 20px; margin:8px 0 14px;
                            background:linear-gradient(110deg, #ffffff 60%, {row['color']}12);
                            box-shadow:0 7px 20px rgba(31,77,48,0.07);">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <div>
                            <div style="font-size:21px; font-weight:750; color:#173e23;">
                                {row['payment_type']}
                            </div>
                            <div style="font-size:31px; font-weight:800; color:{row['color']};
                                        margin-top:5px;">{currency(row['total_sales'])}</div>
                        </div>
                        <div style="font-size:28px; width:55px; height:55px; border-radius:15px;
                                    background:{row['color']}16; display:flex; align-items:center;
                                    justify-content:center;">{row['icon']}</div>
                    </div>
                    <div style="font-size:16px; color:#718075; margin-top:8px;">
                        {row['transaction_count']} {transaction_word} · {share:.1f}% of sales
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    return payment_summary_frame(summary, payment_filter)


def render_daily_sales_dashboard(day_summary):
    st.subheader("Sales by business day")
    st.caption("All recorded dates · filtered by the selected payment types")
    visible_days = 10
    maximum_start = max(0, len(day_summary) - visible_days)
    start_index = maximum_start
    if maximum_start > 0:
        slider_key = "daily_trend_position"
        signature_parts = []
        for row in day_summary:
            signature_parts.append(
                f"{row['business_date']}:{money(row['total_sales']):.2f}"
            )
        trend_signature = "|".join(signature_parts)
        if st.session_state.get("daily_trend_signature") != trend_signature:
            st.session_state[slider_key] = maximum_start
            st.session_state["daily_trend_signature"] = trend_signature
        saved_position = st.session_state.get(slider_key, maximum_start)
        if (not isinstance(saved_position, int) or saved_position < 0
                or saved_position > maximum_start):
            st.session_state[slider_key] = maximum_start
        start_index = st.slider(
            "Move through business days",
            min_value=0,
            max_value=maximum_start,
            key=slider_key,
            help="The latest days are shown first. Drag left to review earlier days.",
        )
    chart_days = daily_trend_window(day_summary, start_index, visible_days)
    st.markdown(daily_trend_chart_html(chart_days), unsafe_allow_html=True)
    first_visible = date.fromisoformat(chart_days[0]["business_date"]).strftime("%d %b %Y")
    last_visible = date.fromisoformat(chart_days[-1]["business_date"]).strftime("%d %b %Y")
    st.caption(f"Showing {first_visible} – {last_visible}")
    stats = daily_trend_stats(day_summary)
    best_date = date.fromisoformat(stats["best_date"]).strftime("%d %B %Y")
    day_word = "business day" if len(day_summary) == 1 else "business days"
    best_column, average_column = st.columns(2)
    with best_column:
        st.metric(
            "🏆 Best business day",
            currency(stats["best_sales"]),
            delta=best_date,
            delta_color="off",
        )
    with average_column:
        st.metric(
            "📊 Average sales per day",
            currency(stats["average_sales"]),
            delta=f"Across {len(day_summary)} {day_word}",
            delta_color="off",
        )


def render_month_dashboard(month_summary):
    st.subheader("Sales by month")
    st.vega_lite_chart(spec=month_chart_spec(month_summary), width="stretch")
    best_row = max(month_summary, key=summary_total_sales)
    total = 0.0
    for row in month_summary:
        total += money(row["total_sales"])
    average = round(total / len(month_summary), 2)
    month_word = "month" if len(month_summary) == 1 else "months"
    best_column, average_column = st.columns(2)
    with best_column:
        st.metric(
            "🏆 Best sales month",
            currency(best_row["total_sales"]),
            delta=best_row["month_label"],
            delta_color="off",
        )
    with average_column:
        st.metric(
            "📊 Average per active month",
            currency(average),
            delta=f"Across {len(month_summary)} {month_word}",
            delta_color="off",
        )
    return monthly_summary_table(month_summary)


def new_transaction_page(transactions):
    st.header("New Transaction")
    st.caption("Record one sale and calculate the change due to the customer.")
    if "recorded_transaction" in st.session_state:
        recorded = st.session_state.pop("recorded_transaction")
        st.success(f"Receipt {recorded['transaction_id']} recorded successfully. Sale: {currency(recorded['sale_amount'])}. Change: {currency(recorded['change_amount'])}.")
    left, right = st.columns(2)
    with left:
        business_date = st.date_input("Business date", value=date.today())
        payment_type = st.selectbox("Payment type", PAYMENT_TYPES)
    with right:
        sale_amount = st.number_input("Sale amount (S$)", min_value=0.0, step=0.10, format="%.2f")
        if payment_type == "Cash":
            amount_rendered = st.number_input("Amount rendered (S$)", min_value=0.0, step=0.10, format="%.2f")
        else:
            amount_rendered = None
            st.text_input("Amount rendered", value="Same as the sale amount for electronic payments", disabled=True)
    if payment_type == "Cash":
        change_preview = round(amount_rendered - sale_amount, 2)
        st.metric("Change due (calculated automatically)", currency(max(change_preview, 0)))
        if sale_amount > 0 and change_preview < 0:
            st.error(f"Amount rendered is short by {currency(abs(change_preview))}. Enter at least the sale amount.")
    if st.button("Record transaction", type="primary", width="stretch"):
        try:
            transaction = build_transaction(sale_amount, amount_rendered, payment_type, business_date)
            save_transaction(DATA_FILE, transaction)
        except (OSError, ValueError) as error:
            st.error(str(error))
        else:
            st.session_state["recorded_transaction"] = transaction
            st.rerun()
    st.divider()
    st.subheader("Today at a glance")
    summary = homepage_summary(transactions)
    transaction_text = f"{summary['today_transactions']} transactions"
    if summary["today_transactions"] == 1:
        transaction_text = "1 transaction"
    today_column, last_column = st.columns(2)
    today_column.metric("Today's sales", currency(summary["today_sales"]), delta=transaction_text, delta_color="off")
    if summary["last_sale"] is None:
        last_sale = "—"
        last_payment = "No transactions yet"
    else:
        last_sale = currency(summary["last_sale"])
        last_payment = summary["last_payment_type"]
    last_column.metric("Last transaction", last_sale, delta=last_payment, delta_color="off")


def daily_report_page(transactions):
    st.header("Daily Sales Report")
    date_column, filter_column = st.columns(2)
    with date_column:
        selected_date = st.date_input("Select business date", value=date.today())
    all_rows = daily_transactions(transactions, selected_date)
    if not all_rows:
        st.info("No transactions were recorded for this date.")
        return
    available_types = available_payment_types(all_rows)
    sync_payment_filter_state(
        st.session_state,
        "daily_payment_choices",
        "daily_payment_options",
        available_types,
    )
    with filter_column:
        payment_filters = st.multiselect(
            "Filter by payment type",
            available_types,
            format_func=format_payment_option,
            key="daily_payment_choices",
        )
    if not payment_filters:
        st.info("Select at least one payment type to display the report.")
        return
    rows = filter_transactions_by_payment(all_rows, payment_filters)
    if not rows:
        st.info("No transactions match the selected payment types.")
        return
    totals = daily_totals(rows)
    column1, column2, column3, column4 = st.columns(4)
    column1.metric("Transactions", totals["transaction_count"])
    column2.metric("Total sales", currency(totals["total_sales"]))
    column3.metric("Amount rendered", currency(totals["total_rendered"]))
    column4.metric("Change returned", currency(totals["total_change"]))
    payment_table = render_payment_dashboard(payment_summary(rows), "Daily sales by payment type", payment_filters)
    slug = payment_slug(payment_filters)
    st.download_button("Download daily payment summary (CSV)", data=rows_to_csv(payment_table), file_name=f"daily_payment_summary_{selected_date.isoformat()}_{slug}.csv", mime="text/csv")
    daily_history = filtered_daily_history(transactions, payment_filters)
    if daily_history:
        render_daily_sales_dashboard(daily_history)
    st.subheader("Transaction listing")
    transaction_table = display_rows(rows)
    st.dataframe(transaction_table, hide_index=True, width="stretch")
    st.download_button("Download daily transaction report (CSV)", data=rows_to_csv(transaction_table), file_name=f"daily_transactions_{selected_date.isoformat()}_{slug}.csv", mime="text/csv")


def monthly_report_page(transactions):
    st.header("Monthly Sales Summary")
    if not transactions:
        st.info("No transactions were recorded.")
        return
    available_dates = []
    for row in transactions:
        available_dates.append(date.fromisoformat(row["business_date"]))
    available_dates = sorted(available_dates)
    period_column, payment_column = st.columns([1.1, 1])
    with period_column:
        selected_period = st.date_input("Select date range", value=(available_dates[0], available_dates[-1]), min_value=available_dates[0], max_value=available_dates[-1], key="monthly_date_range")
    if not isinstance(selected_period, (tuple, list)) or len(selected_period) != 2:
        st.info("Select both a start date and an end date.")
        return
    start_date = selected_period[0]
    end_date = selected_period[1]
    period_rows = filter_transactions_by_date_range(
        transactions,
        start_date,
        end_date,
    )
    if not period_rows:
        st.info("No transactions were recorded for the selected period.")
        return
    available_types = available_payment_types(period_rows)
    sync_payment_filter_state(
        st.session_state,
        "monthly_payment_choices",
        "monthly_payment_options",
        available_types,
    )
    with payment_column:
        payment_filters = st.multiselect(
            "Filter by payment type",
            available_types,
            format_func=format_payment_option,
            key="monthly_payment_choices",
        )
    if not payment_filters:
        st.info("Select at least one payment type to display the report.")
        return
    rows = filter_transactions_by_date_range(transactions, start_date, end_date, payment_filters)
    if not rows:
        st.info("No transactions match the selected period and payment types.")
        return
    month_summary = period_month_summary(rows)
    total_sales = 0.0
    for row in rows:
        total_sales += money(row["sale_amount"])
    period_label = f"{start_date.strftime('%d %b %Y')} – {end_date.strftime('%d %b %Y')}"
    column1, column2, column3 = st.columns(3)
    column1.metric("Selected period", period_label)
    column2.metric("Transactions", len(rows))
    column3.metric("Total sales", currency(total_sales))
    monthly_table = render_month_dashboard(month_summary)
    render_payment_dashboard(payment_summary(rows), "Sales by payment type", payment_filters)
    st.subheader("Monthly sales by payment type")
    st.dataframe(monthly_table, hide_index=True, width="stretch")
    st.caption("All charts, summary tables, and CSV exports reflect the selected date range and payment types.")
    slug = payment_slug(payment_filters)
    st.download_button("Download monthly payment summary (CSV)", data=rows_to_csv(monthly_table), file_name=f"monthly_sales_summary_{start_date:%Y%m%d}_{end_date:%Y%m%d}_{slug}.csv", mime="text/csv")
    daily_table = daily_summary_frame(period_daily_summary(rows))
    st.subheader("Daily sales summary")
    st.dataframe(daily_table, hide_index=True, width="stretch")
    st.download_button("Download daily sales summary (CSV)", data=rows_to_csv(daily_table), file_name=f"daily_sales_summary_{start_date:%Y%m%d}_{end_date:%Y%m%d}_{slug}.csv", mime="text/csv")


def manage_transactions_page(transactions):
    st.header("Manage Transactions")
    st.caption("Edit or permanently delete a recorded transaction.")
    if not transactions:
        st.info("There are no transactions to manage.")
        return
    if "manage_message" in st.session_state:
        st.success(st.session_state.pop("manage_message"))
    ordered = sorted(transactions, key=transaction_timestamp, reverse=True)
    labels = {}
    for row in ordered:
        labels[row["transaction_id"]] = f"{row['business_date']} | {row['transaction_id']} | {currency(row['sale_amount'])} | {row['payment_type']}"
    selected_label = st.selectbox("Select receipt", list(labels.values()))
    selected_id = ""
    for receipt_id in labels:
        if labels[receipt_id] == selected_label:
            selected_id = receipt_id
            break
    selected = ordered[0]
    for row in ordered:
        if row["transaction_id"] == selected_id:
            selected = row
            break
    st.dataframe(display_rows([selected]), hide_index=True, width="stretch")
    edit_tab, delete_tab = st.tabs(["✏️ Edit Transaction", "🗑️ Delete Transaction"])
    with edit_tab:
        edit_date = st.date_input("Business date", value=date.fromisoformat(selected["business_date"]), key=f"edit_date_{selected_id}")
        edit_payment = st.selectbox("Payment type", PAYMENT_TYPES, index=PAYMENT_TYPES.index(selected["payment_type"]), key=f"edit_payment_{selected_id}")
        edit_sale = st.number_input("Sale amount (S$)", min_value=0.0, value=float(selected["sale_amount"]), step=0.10, format="%.2f", key=f"edit_sale_{selected_id}")
        if edit_payment == "Cash":
            if selected["payment_type"] == "Cash":
                default_rendered = float(selected["amount_rendered"])
            else:
                default_rendered = float(selected["sale_amount"])
            edit_rendered = st.number_input("Amount rendered (S$)", min_value=0.0, value=default_rendered, step=0.10, format="%.2f", key=f"edit_rendered_{selected_id}")
            edit_change = round(edit_rendered - edit_sale, 2)
            st.metric("Recalculated change", currency(max(edit_change, 0)))
            if edit_sale > 0 and edit_change < 0:
                st.error(f"Amount rendered is short by {currency(abs(edit_change))}.")
        else:
            edit_rendered = None
            st.info("No change is calculated for electronic payments. The amount rendered will match the sale amount.")
        if st.button("Save transaction changes", type="primary", key=f"save_edit_{selected_id}"):
            try:
                updated = update_transaction(DATA_FILE, selected_id, edit_sale, edit_rendered, edit_payment, edit_date)
            except (OSError, ValueError) as error:
                st.error(f"Unable to update the transaction: {error}")
            else:
                if updated:
                    st.session_state["manage_message"] = f"Receipt {selected_id} was updated successfully."
                    st.rerun()
                else:
                    st.warning("The receipt could not be found.")
    with delete_tab:
        st.warning("Deleting a transaction cannot be undone.")
        confirmed = st.checkbox("I confirm that this incorrect transaction should be deleted.", key=f"confirm_delete_{selected_id}")
        if st.button("Delete selected transaction", disabled=not confirmed, key=f"delete_{selected_id}"):
            try:
                removed = delete_transaction(DATA_FILE, selected_id)
            except (OSError, ValueError) as error:
                st.error(f"Unable to delete the transaction: {error}")
            else:
                if removed:
                    st.session_state["manage_message"] = f"Receipt {selected_id} was deleted."
                    st.rerun()
                else:
                    st.warning("The receipt could not be found.")


def main():
    st.set_page_config(page_title="Ah Beng Cash Receipting", page_icon="🧾", layout="wide")
    st.markdown(APP_CSS, unsafe_allow_html=True)
    st.title("🧾 Ah Beng Vegetarian Food")
    st.caption("Simple cash receipting and sales reconciliation")
    page = st.sidebar.radio("Menu", ("New Transaction", "Daily Report", "Monthly Report", "Manage Transactions"), format_func=format_menu_option)
    st.sidebar.divider()
    st.sidebar.caption("Data file: transactions.csv")
    transactions = load_data()
    if page == "New Transaction":
        new_transaction_page(transactions)
    elif page == "Daily Report":
        daily_report_page(transactions)
    elif page == "Monthly Report":
        monthly_report_page(transactions)
    else:
        manage_transactions_page(transactions)


if __name__ == "__main__":
    main()
