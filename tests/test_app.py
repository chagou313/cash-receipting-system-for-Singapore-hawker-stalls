"""Unit tests for the business logic in app.py (no Streamlit server needed)."""

import os
import sys
from datetime import date, datetime

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app  # noqa: E402


SAMPLE_CSV = os.path.join(os.path.dirname(app.DATA_FILE), "transactions.csv")


def make(sale, rendered, payment, day, hour=12, receipt=None):
    return app.build_transaction(
        sale, rendered, payment, day,
        now=datetime(day.year, day.month, day.day, hour, 0, 0),
        transaction_id=receipt,
    )


# ---------------------------- money and change ----------------------------

def test_money_rounds_to_two_places():
    assert app.money("3.456") == 3.46
    assert app.money(5) == 5.0


@pytest.mark.parametrize("bad", ["abc", None, ""])
def test_money_rejects_invalid_values(bad):
    with pytest.raises(ValueError):
        app.money(bad)


def test_money_rejects_negative_values():
    with pytest.raises(ValueError):
        app.money(-1)


def test_currency_format():
    assert app.currency(1234.5) == "S$1,234.50"


def test_cash_change_is_calculated():
    assert app.calculate_change("Cash", 7.50, 20) == 12.50


def test_cash_change_avoids_float_errors():
    assert app.calculate_change("Cash", 8.80, 10.00) == 1.20


def test_cash_short_payment_is_rejected():
    with pytest.raises(ValueError):
        app.calculate_change("Cash", 9.50, 5.00)


@pytest.mark.parametrize("payment", ["PayNow", "PayLah!", "payWave"])
def test_electronic_payments_have_no_change(payment):
    assert app.calculate_change(payment, 6.30) == 0.0


def test_zero_sale_is_rejected():
    with pytest.raises(ValueError):
        app.calculate_change("PayNow", 0)


def test_unknown_payment_type_is_rejected():
    with pytest.raises(ValueError):
        app.calculate_change("Bitcoin", 5)


def test_build_transaction_for_electronic_payment():
    row = make(5.80, None, "PayLah!", date(2026, 9, 1), receipt="T1")
    assert row == {
        "transaction_id": "T1",
        "timestamp": "2026-09-01 12:00:00",
        "business_date": "2026-09-01",
        "sale_amount": "5.80",
        "amount_rendered": "5.80",
        "change_amount": "0.00",
        "payment_type": "PayLah!",
    }


def test_build_transaction_generates_receipt_number():
    row = app.build_transaction(4.20, 10, "Cash", date(2026, 9, 1),
                                now=datetime(2026, 9, 1, 8, 30, 15, 123456))
    assert row["transaction_id"] == "R20260901083015123456"
    assert row["change_amount"] == "5.80"


# ---------------------------- CSV storage ----------------------------

def test_save_and_load_round_trip(tmp_path):
    csv_path = str(tmp_path / "data" / "transactions.csv")
    first = make(7.50, 20, "Cash", date(2026, 9, 2), receipt="A")
    second = make(3.50, None, "PayNow", date(2026, 9, 2), hour=13, receipt="B")
    app.save_transaction(csv_path, first)
    app.save_transaction(csv_path, second)
    loaded = app.load_transactions(csv_path)
    assert [row["transaction_id"] for row in loaded] == ["A", "B"]
    assert loaded[0]["change_amount"] == "12.50"


def test_missing_file_loads_as_empty(tmp_path):
    assert app.load_transactions(str(tmp_path / "none.csv")) == []


def test_invalid_header_is_rejected(tmp_path):
    csv_path = tmp_path / "bad.csv"
    csv_path.write_text("id,amount\n1,2\n", encoding="utf-8")
    with pytest.raises(ValueError, match="header"):
        app.load_transactions(str(csv_path))


def test_invalid_row_reports_line_number(tmp_path):
    csv_path = tmp_path / "bad.csv"
    header = ",".join(app.FIELDNAMES)
    csv_path.write_text(
        header + "\nX,2026-09-01 10:00:00,2026-09-01,5.00,5.00,0.00,Cheque\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="line 2"):
        app.load_transactions(str(csv_path))


def test_update_transaction_recalculates_change(tmp_path):
    csv_path = str(tmp_path / "t.csv")
    app.save_transaction(csv_path, make(5.00, None, "PayNow", date(2026, 9, 3), receipt="U"))
    assert app.update_transaction(csv_path, "U", 6.30, 10, "Cash", date(2026, 9, 4))
    row = app.load_transactions(csv_path)[0]
    assert row["payment_type"] == "Cash"
    assert row["change_amount"] == "3.70"
    assert row["business_date"] == "2026-09-04"
    assert row["timestamp"] == "2026-09-03 12:00:00"  # original time is kept


def test_delete_transaction(tmp_path):
    csv_path = str(tmp_path / "t.csv")
    app.save_transaction(csv_path, make(5.00, None, "PayNow", date(2026, 9, 3), receipt="D1"))
    app.save_transaction(csv_path, make(6.00, None, "PayNow", date(2026, 9, 3), receipt="D2"))
    assert app.delete_transaction(csv_path, "D1") is True
    assert app.delete_transaction(csv_path, "missing") is False
    assert [row["transaction_id"] for row in app.load_transactions(csv_path)] == ["D2"]


def test_sample_data_file_is_valid():
    rows = app.load_transactions(SAMPLE_CSV)
    assert len(rows) > 0


# ---------------------------- reports ----------------------------

@pytest.fixture
def sales():
    return [
        make(7.50, 20, "Cash", date(2026, 8, 1), hour=9, receipt="1"),
        make(3.50, None, "PayNow", date(2026, 8, 1), hour=11, receipt="2"),
        make(5.00, None, "payWave", date(2026, 8, 2), receipt="3"),
        make(9.50, 10, "Cash", date(2026, 9, 5), receipt="4"),
    ]


def test_daily_totals(sales):
    rows = app.daily_transactions(sales, date(2026, 8, 1))
    assert app.daily_totals(rows) == {
        "transaction_count": 2,
        "total_sales": 11.0,
        "total_rendered": 23.5,
        "total_change": 12.5,
    }


def test_payment_filter(sales):
    rows = app.filter_transactions_by_payment(sales, ["Cash"])
    assert [row["transaction_id"] for row in rows] == ["1", "4"]


def test_date_range_filter(sales):
    rows = app.filter_transactions_by_date_range(sales, date(2026, 8, 2), date(2026, 9, 30))
    assert [row["transaction_id"] for row in rows] == ["3", "4"]


def test_month_summary_splits_by_payment_type(sales):
    summary = app.period_month_summary(sales)
    august, september = summary
    assert august["month_label"] == "August 2026"
    assert august["cash_sales"] == 7.5
    assert august["paynow_sales"] == 3.5
    assert august["paywave_sales"] == 5.0
    assert august["total_sales"] == 16.0
    assert september["transaction_count"] == 1


def test_payment_percentages_add_up(sales):
    rows = app.payment_display_rows(app.payment_summary(sales))
    assert round(sum(row["percentage"] for row in rows)) == 100


def test_daily_trend_stats(sales):
    stats = app.daily_trend_stats(app.period_daily_summary(sales))
    assert stats["best_date"] == "2026-08-01"
    assert stats["best_sales"] == 11.0
    assert stats["average_sales"] == round((11.0 + 5.0 + 9.5) / 3, 2)


def test_rows_to_csv_quotes_special_characters():
    text = app.rows_to_csv([{"name": "PayLah!, app", "amount": "5.00"}])
    assert text == 'name,amount\n"PayLah!, app",5.00'
