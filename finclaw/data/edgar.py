"""SEC EDGAR wrapper using edgartools for filing access."""

from __future__ import annotations

from typing import Any

from finclaw.data.cache import TTLCache

_cache = TTLCache(default_ttl=1800)  # 30-minute cache


def _get_company(ticker: str):
    """Lazy-import edgartools and return a Company object."""
    from edgar import Company
    return Company(ticker)


def search_filings(
    ticker: str,
    form_type: str = "10-K",
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Search for recent filings of a given type."""
    cache_key = f"edgar:search:{ticker}:{form_type}:{limit}"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    company = _get_company(ticker)
    filings = company.get_filings(form=form_type).latest(limit)

    result = []
    for f in filings:
        result.append({
            "accession_number": str(f.accession_no),
            "form_type": f.form,
            "filing_date": str(f.filing_date),
            "description": getattr(f, "description", ""),
        })

    _cache.set(cache_key, result)
    return result


def get_filing_text(
    ticker: str,
    form_type: str = "10-K",
    index: int = 0,
    max_chars: int = 8000,
) -> dict[str, Any]:
    """Get the text content of a specific filing.

    Args:
        ticker: Stock ticker symbol.
        form_type: SEC form type (10-K, 10-Q, 8-K, etc.).
        index: 0 = most recent, 1 = second most recent, etc.
        max_chars: Maximum characters to return.
    """
    cache_key = f"edgar:text:{ticker}:{form_type}:{index}"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    company = _get_company(ticker)
    filings = company.get_filings(form=form_type).latest(index + 1)
    filing_list = list(filings)
    if index >= len(filing_list):
        return {"error": f"Only {len(filing_list)} {form_type} filings found for {ticker}."}

    filing = filing_list[index]
    obj = filing.obj()

    # Try to get markdown or text representation
    try:
        text = obj.markdown() if hasattr(obj, "markdown") else obj.text()
    except Exception:
        text = str(obj)

    if len(text) > max_chars:
        text = text[:max_chars] + "\n\n... [truncated]"

    result = {
        "ticker": ticker.upper(),
        "form_type": form_type,
        "filing_date": str(filing.filing_date),
        "accession_number": str(filing.accession_no),
        "text": text,
    }
    _cache.set(cache_key, result)
    return result


def get_financial_statements(
    ticker: str,
    form_type: str = "10-K",
    index: int = 0,
) -> dict[str, Any]:
    """Extract financial statements from a filing as formatted tables.

    Returns income statement, balance sheet, and cash flow if available.
    """
    cache_key = f"edgar:financials:{ticker}:{form_type}:{index}"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    company = _get_company(ticker)
    filings = company.get_filings(form=form_type).latest(index + 1)
    filing_list = list(filings)
    if index >= len(filing_list):
        return {"error": f"Only {len(filing_list)} {form_type} filings found for {ticker}."}

    filing = filing_list[index]
    obj = filing.obj()

    result: dict[str, Any] = {
        "ticker": ticker.upper(),
        "form_type": form_type,
        "filing_date": str(filing.filing_date),
        "statements": {},
    }

    # Extract financial statements if available
    for attr_name, label in [
        ("income_statement", "Income Statement"),
        ("balance_sheet", "Balance Sheet"),
        ("cash_flow_statement", "Cash Flow Statement"),
    ]:
        try:
            stmt = getattr(obj, attr_name, None)
            if stmt is not None:
                df = stmt.to_dataframe() if hasattr(stmt, "to_dataframe") else None
                if df is not None and not df.empty:
                    result["statements"][label] = df.to_string()
                else:
                    result["statements"][label] = str(stmt)
        except Exception:
            continue

    _cache.set(cache_key, result)
    return result


def compare_filings(
    ticker: str,
    form_type: str = "10-Q",
    count: int = 2,
) -> dict[str, Any]:
    """Compare financial metrics across recent filings."""
    results = []
    for i in range(count):
        stmt = get_financial_statements(ticker, form_type, index=i)
        if "error" not in stmt:
            results.append(stmt)

    return {
        "ticker": ticker.upper(),
        "form_type": form_type,
        "filings_compared": len(results),
        "filings": results,
    }
