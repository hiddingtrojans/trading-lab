"""
SEC EDGAR Scanner - Insider Trades & 13F Filings

Free data source - no API key required.
https://www.sec.gov/cgi-bin/browse-edgar

Rate limit: 10 requests/second
"""

import requests
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.alpha_lab.telegram_alerts import send_message as send_telegram_message


class SECScanner:
    """Scans SEC EDGAR for insider trades and institutional holdings."""
    
    BASE_URL = "https://data.sec.gov"
    EDGAR_URL = "https://www.sec.gov/cgi-bin/browse-edgar"
    
    # SEC requires a User-Agent header with contact info
    HEADERS = {
        "User-Agent": "TradingScanner/1.0 (contact@example.com)",
        "Accept-Encoding": "gzip, deflate",
    }
    
    # Common tickers to CIK mapping (SEC uses CIK not ticker)
    # This is a starter set - we'll fetch dynamically for others
    TICKER_TO_CIK = {
        "AAPL": "0000320193",
        "MSFT": "0000789019",
        "GOOGL": "0001652044",
        "AMZN": "0001018724",
        "NVDA": "0001045810",
        "META": "0001326801",
        "TSLA": "0001318605",
        "AMD": "0000002488",
        "CRM": "0001108524",
        "NFLX": "0001065280",
    }
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
        self.last_request_time = 0
        
    def _rate_limit(self):
        """Ensure we don't exceed 10 requests/second."""
        elapsed = time.time() - self.last_request_time
        if elapsed < 0.1:  # 10 req/sec = 0.1 sec between requests
            time.sleep(0.1 - elapsed)
        self.last_request_time = time.time()
        
    def get_cik_for_ticker(self, ticker: str) -> Optional[str]:
        """Get CIK number for a ticker symbol."""
        ticker = ticker.upper()
        
        # Check cache first
        if ticker in self.TICKER_TO_CIK:
            return self.TICKER_TO_CIK[ticker]
            
        # Fetch from SEC company tickers JSON
        try:
            self._rate_limit()
            url = "https://www.sec.gov/files/company_tickers.json"
            resp = self.session.get(url, timeout=10)
            resp.raise_for_status()
            
            data = resp.json()
            for entry in data.values():
                if entry.get("ticker", "").upper() == ticker:
                    cik = str(entry["cik_str"]).zfill(10)
                    self.TICKER_TO_CIK[ticker] = cik
                    return cik
                    
        except Exception as e:
            print(f"Error fetching CIK for {ticker}: {e}")
            
        return None
        
    def get_insider_trades(self, ticker: str, days_back: int = 7) -> List[Dict]:
        """
        Get recent insider trades (Form 4 filings) for a ticker.
        
        Form 4 = insider buys/sells within 2 business days of transaction.
        """
        cik = self.get_cik_for_ticker(ticker)
        if not cik:
            return []
            
        trades = []
        
        try:
            self._rate_limit()
            
            # Get company filings
            url = f"{self.BASE_URL}/submissions/CIK{cik}.json"
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
            
            data = resp.json()
            filings = data.get("filings", {}).get("recent", {})
            
            if not filings:
                return []
                
            # Find Form 4 filings
            forms = filings.get("form", [])
            dates = filings.get("filingDate", [])
            accessions = filings.get("accessionNumber", [])
            
            cutoff_date = datetime.now() - timedelta(days=days_back)
            
            for i, form in enumerate(forms):
                if form != "4":
                    continue
                    
                filing_date = datetime.strptime(dates[i], "%Y-%m-%d")
                if filing_date < cutoff_date:
                    break  # Filings are in reverse chronological order
                    
                # Get the actual filing details
                accession = accessions[i].replace("-", "")
                filing_url = f"{self.BASE_URL}/Archives/edgar/data/{cik.lstrip('0')}/{accession}"
                
                trade_info = self._parse_form4(filing_url, ticker, dates[i])
                if trade_info:
                    trades.append(trade_info)
                    
                # Limit to 5 most recent
                if len(trades) >= 5:
                    break
                    
        except Exception as e:
            print(f"Error fetching insider trades for {ticker}: {e}")
            
        return trades
        
    def _parse_form4(self, filing_url: str, ticker: str, filing_date: str) -> Optional[Dict]:
        """Parse Form 4 XML to extract trade details."""
        try:
            self._rate_limit()
            
            # Get filing index
            index_url = f"{filing_url}/index.json"
            resp = self.session.get(index_url, timeout=10)
            resp.raise_for_status()
            
            index_data = resp.json()
            
            # Find the XML file
            xml_file = None
            for item in index_data.get("directory", {}).get("item", []):
                name = item.get("name", "")
                if name.endswith(".xml") and "primary_doc" not in name.lower():
                    xml_file = name
                    break
                    
            if not xml_file:
                return None
                
            # Fetch and parse XML
            self._rate_limit()
            xml_url = f"{filing_url}/{xml_file}"
            resp = self.session.get(xml_url, timeout=10)
            resp.raise_for_status()
            
            # Simple XML parsing without external library
            content = resp.text
            
            # Extract key fields using string parsing (avoiding lxml dependency)
            insider_name = self._extract_xml_value(content, "rptOwnerName")
            insider_title = self._extract_xml_value(content, "officerTitle") or \
                           self._extract_xml_value(content, "isDirector")
            
            # Transaction details
            transaction_type = self._extract_xml_value(content, "transactionAcquiredDisposedCode")
            shares = self._extract_xml_value(content, "transactionShares")
            price = self._extract_xml_value(content, "transactionPricePerShare")
            
            if not all([insider_name, transaction_type, shares]):
                return None
                
            is_buy = transaction_type == "A"  # A = Acquired, D = Disposed
            
            try:
                shares_float = float(shares.replace(",", ""))
                price_float = float(price.replace(",", "")) if price else 0
                total_value = shares_float * price_float
            except:
                shares_float = 0
                price_float = 0
                total_value = 0
                
            return {
                "ticker": ticker,
                "insider_name": insider_name,
                "title": insider_title if insider_title != "1" else "Director",
                "transaction_type": "BUY" if is_buy else "SELL",
                "shares": shares_float,
                "price": price_float,
                "total_value": total_value,
                "filing_date": filing_date,
                "url": xml_url.replace(".xml", "-index.htm")
            }
            
        except Exception as e:
            # Silently fail on individual filings
            return None
            
    def _extract_xml_value(self, xml: str, tag: str) -> Optional[str]:
        """Extract value from XML tag."""
        import re
        pattern = f"<{tag}[^>]*>([^<]+)</{tag}>"
        match = re.search(pattern, xml, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return None
        
    def scan_insider_buys(self, tickers: List[str], min_value: float = 100000) -> List[Dict]:
        """
        Scan multiple tickers for significant insider BUYS.
        
        Args:
            tickers: List of ticker symbols
            min_value: Minimum transaction value to report
            
        Returns:
            List of significant insider buy transactions
        """
        significant_buys = []
        
        for ticker in tickers:
            print(f"  Scanning {ticker} for insider trades...")
            trades = self.get_insider_trades(ticker)
            
            for trade in trades:
                if trade["transaction_type"] == "BUY" and trade["total_value"] >= min_value:
                    significant_buys.append(trade)
                    
        # Sort by value descending
        significant_buys.sort(key=lambda x: x["total_value"], reverse=True)
        
        return significant_buys
        
    def get_13f_filings(self, fund_cik: str, ticker: Optional[str] = None) -> Dict:
        """
        Get 13F institutional holdings for a fund.
        
        13F filings show what hedge funds and institutions own.
        Filed quarterly, within 45 days of quarter end.
        """
        try:
            self._rate_limit()
            
            url = f"{self.BASE_URL}/submissions/CIK{fund_cik}.json"
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
            
            data = resp.json()
            fund_name = data.get("name", "Unknown Fund")
            
            filings = data.get("filings", {}).get("recent", {})
            forms = filings.get("form", [])
            dates = filings.get("filingDate", [])
            accessions = filings.get("accessionNumber", [])
            
            # Find most recent 13F-HR
            for i, form in enumerate(forms):
                if form == "13F-HR":
                    return {
                        "fund_name": fund_name,
                        "fund_cik": fund_cik,
                        "filing_date": dates[i],
                        "accession": accessions[i],
                        # Full parsing would require downloading the XML
                        # which is complex - keeping it simple for now
                    }
                    
        except Exception as e:
            print(f"Error fetching 13F for {fund_cik}: {e}")
            
        return {}


class InsiderTradeAlert:
    """Monitor and alert on significant insider trades."""
    
    # Tickers to monitor for insider activity
    DEFAULT_WATCHLIST = [
        # Mega caps
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA",
        # Growth
        "CRM", "NFLX", "AMD", "SNOW", "PLTR", "CRWD", "NET",
        # Financials
        "JPM", "GS", "MS", "BAC",
        # Healthcare
        "UNH", "JNJ", "LLY", "PFE",
    ]
    
    def __init__(self, watchlist: Optional[List[str]] = None):
        self.scanner = SECScanner()
        self.watchlist = watchlist or self.DEFAULT_WATCHLIST
        
    def check_and_alert(self, min_value: float = 100000, send_telegram: bool = True) -> List[Dict]:
        """
        Check for significant insider buys and send alerts.
        
        Args:
            min_value: Minimum transaction value to alert on
            send_telegram: Whether to send Telegram alerts
            
        Returns:
            List of significant insider buys found
        """
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Scanning for insider trades...")
        
        buys = self.scanner.scan_insider_buys(self.watchlist, min_value)
        
        if not buys:
            print("  No significant insider buys found")
            return []
            
        print(f"  Found {len(buys)} significant insider buy(s)")
        
        for buy in buys:
            self._print_trade(buy)
            
            if send_telegram:
                self._send_alert(buy)
                
        return buys
        
    def _print_trade(self, trade: Dict):
        """Print trade details to console."""
        print(f"\n  INSIDER BUY: ${trade['ticker']}")
        print(f"  {trade['insider_name']} ({trade['title']})")
        print(f"  {trade['shares']:,.0f} shares @ ${trade['price']:.2f}")
        print(f"  Total: ${trade['total_value']:,.0f}")
        print(f"  Filed: {trade['filing_date']}")
        
    def _send_alert(self, trade: Dict):
        """Send Telegram alert for insider trade."""
        # Format value nicely
        if trade['total_value'] >= 1_000_000:
            value_str = f"${trade['total_value']/1_000_000:.1f}M"
        else:
            value_str = f"${trade['total_value']/1_000:,.0f}K"
            
        message = f"""INSIDER BUY: ${trade['ticker']}

{trade['insider_name']}
{trade['title']}

{trade['shares']:,.0f} shares @ ${trade['price']:.2f}
Total: {value_str}

Filed: {trade['filing_date']}"""
        
        send_telegram_message(message)


# Well-known hedge fund CIKs for 13F tracking
FAMOUS_FUNDS = {
    "Berkshire Hathaway": "0001067983",
    "Bridgewater Associates": "0001350694",
    "Renaissance Technologies": "0001037389",
    "Citadel Advisors": "0001423053",
    "Two Sigma": "0001179392",
    "DE Shaw": "0001009207",
    "Appaloosa Management": "0001656456",
    "Pershing Square": "0001336528",
    "Third Point": "0001040273",
    "Greenlight Capital": "0001079114",
}


def run_insider_scan(watchlist: Optional[List[str]] = None, min_value: float = 100000):
    """Run insider trade scan and alert."""
    alerter = InsiderTradeAlert(watchlist)
    return alerter.check_and_alert(min_value=min_value, send_telegram=True)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="SEC Insider Trade Scanner")
    parser.add_argument("--tickers", type=str, help="Comma-separated tickers to scan")
    parser.add_argument("--min-value", type=float, default=100000, help="Minimum trade value")
    parser.add_argument("--no-telegram", action="store_true", help="Don't send Telegram alerts")
    
    args = parser.parse_args()
    
    watchlist = args.tickers.split(",") if args.tickers else None
    
    alerter = InsiderTradeAlert(watchlist)
    alerter.check_and_alert(min_value=args.min_value, send_telegram=not args.no_telegram)

