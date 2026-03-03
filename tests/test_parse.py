from pathlib import Path

from bdc_sched.parse.detect import find_candidate_tables
from bdc_sched.parse.schedule import parse_filing_file, parse_money, parse_schedule_rows


FIXTURE = Path(__file__).parent / "fixtures" / "sample_filing.html"


def test_heading_detection_finds_table():
    html = FIXTURE.read_text(encoding="utf-8")
    tables = find_candidate_tables(html)
    assert len(tables) >= 1


def test_parse_money_variants():
    assert parse_money("$1,234") == 1234.0
    assert parse_money("($98.5)") == -98.5
    assert parse_money("—") is None


def test_smoke_parse_fixture_rows():
    rows = parse_filing_file(
        FIXTURE,
        {
            "ticker": "ARCC",
            "cik": "0001287750",
            "accessionNo": "0001287750-24-000001",
            "filingDate": "2024-08-01",
            "form": "10-Q",
        },
    )
    assert len(rows) >= 2
    assert any("ABC Corp" in r["raw_row_text"] for r in rows)


def test_regression_keeps_valid_schedule_like_table():
    html = """
    <html><body>
      <h2>Consolidated Schedule of Investments</h2>
      <table>
        <tr><th>Portfolio Company</th><th>Principal</th><th>Amortized Cost</th><th>Fair Value</th></tr>
        <tr><td>Acme Holdings</td><td>$1,000</td><td>$980</td><td>$1,010</td></tr>
      </table>
    </body></html>
    """

    rows = parse_schedule_rows(html, {"ticker": "TST"})

    assert rows
    assert any("Acme Holdings" in r["raw_row_text"] for r in rows)
    assert all(not r.get("filter_fallback") for r in rows)


def test_regression_rejects_non_schedule_exhibit_table_without_heading():
    html = """
    <html><body>
      <table>
        <tr><th>Exhibit Index</th><th>Description</th><th>Amount</th></tr>
        <tr><td>10.1</td><td>Form of Indenture Agreement with Trustee</td><td>$1,000</td></tr>
      </table>
    </body></html>
    """

    rows = parse_schedule_rows(html, {"ticker": "TST"})

    assert rows == []


def test_regression_heading_with_all_tables_rejected_uses_fallback():
    html = """
    <html><body>
      <h2>Consolidated Schedule of Investments</h2>
      <table>
        <tr><th>Exhibit</th><th>Form of Agreement</th><th>Trustee</th></tr>
        <tr><td>10.2</td><td>Indenture Notes Due 2031</td><td>Example Trust Co.</td></tr>
      </table>
    </body></html>
    """

    rows = parse_schedule_rows(html, {"ticker": "TST"})

    assert rows
    assert all(r.get("filter_fallback") is True for r in rows)
    assert all(r.get("heading") == "Consolidated Schedule of Investments" for r in rows)
