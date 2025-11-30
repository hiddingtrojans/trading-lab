"""
13F Hedge Fund Tracker - Track what the big funds are buying/selling.

Uses SEC EDGAR (free, no API key required).

13F filings are required for institutions with >$100M AUM.
Filed quarterly, within 45 days of quarter end.
"""

import requests
import json
import time
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.alpha_lab.telegram_alerts import send_message as send_telegram_message


@dataclass
class HoldingChange:
    """Represents a change in a fund's holdings."""
    ticker: str
    company_name: str
    action: str  # NEW, INCREASED, DECREASED, SOLD
    shares_current: int
    shares_previous: int
    value_current: float
    percent_change: float


class HedgeFundTracker:
    """Track 13F filings from major hedge funds."""
    
    BASE_URL = "https://data.sec.gov"
    
    HEADERS = {
        "User-Agent": "TradingScanner/1.0 (contact@example.com)",
        "Accept-Encoding": "gzip, deflate",
    }
    
    # Famous funds to track (CIK numbers)
    TRACKED_FUNDS = {
        "Berkshire Hathaway": "0001067983",
        "Bridgewater Associates": "0001350694", 
        "Renaissance Technologies": "0001037389",
        "Citadel Advisors": "0001423053",
        "Two Sigma Investments": "0001179392",
        "DE Shaw": "0001009207",
        "Pershing Square": "0001336528",
        "Third Point": "0001040273",
        "Greenlight Capital": "0001079114",
        "Appaloosa Management": "0001656456",
        "Tiger Global": "0001167483",
        "Coatue Management": "0001535392",
        "Druckenmiller (Duquesne)": "0001536411",
        "Bill Ackman (Pershing)": "0001336528",
        "David Tepper (Appaloosa)": "0001656456",
    }
    
    # CUSIP to Ticker mapping (partial - we'll fetch more dynamically)
    CUSIP_TO_TICKER = {
        "037833100": "AAPL",
        "594918104": "MSFT", 
        "02079K305": "GOOGL",
        "023135106": "AMZN",
        "67066G104": "NVDA",
        "30303M102": "META",
        "88160R101": "TSLA",
        "46625H100": "JPM",
        "38141G104": "GS",
    }
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
        self.last_request_time = 0
        self._ticker_cache = {}
        
    def _rate_limit(self):
        """Ensure we don't exceed 10 requests/second."""
        elapsed = time.time() - self.last_request_time
        if elapsed < 0.1:
            time.sleep(0.1 - elapsed)
        self.last_request_time = time.time()
        
    def get_latest_13f(self, fund_cik: str) -> Optional[Dict]:
        """Get the most recent 13F filing for a fund."""
        try:
            self._rate_limit()
            
            url = f"{self.BASE_URL}/submissions/CIK{fund_cik}.json"
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
            
            data = resp.json()
            fund_name = data.get("name", "Unknown")
            
            filings = data.get("filings", {}).get("recent", {})
            forms = filings.get("form", [])
            dates = filings.get("filingDate", [])
            accessions = filings.get("accessionNumber", [])
            
            # Find most recent 13F-HR (the main quarterly filing)
            for i, form in enumerate(forms):
                if form == "13F-HR":
                    return {
                        "fund_name": fund_name,
                        "fund_cik": fund_cik,
                        "filing_date": dates[i],
                        "accession": accessions[i],
                    }
                    
            return None
            
        except Exception as e:
            print(f"Error fetching 13F for {fund_cik}: {e}")
            return None
            
    def get_13f_holdings(self, fund_cik: str, accession: str) -> List[Dict]:
        """
        Parse 13F holdings from the XML filing.
        
        Returns list of holdings with ticker, shares, value.
        """
        holdings = []
        
        try:
            # Format accession for URL - SEC uses dashes removed for directory
            accession_clean = accession.replace("-", "")
            cik_clean = fund_cik.lstrip("0")
            
            self._rate_limit()
            
            # Use www.sec.gov for archives (data.sec.gov doesn't have index.json)
            archive_base = "https://www.sec.gov"
            
            # Get filing index to find the XML file
            index_url = f"{archive_base}/Archives/edgar/data/{cik_clean}/{accession_clean}/index.json"
            resp = self.session.get(index_url, timeout=10)
            resp.raise_for_status()
            
            index_data = resp.json()
            
            # Find the infotable XML file (contains actual holdings)
            # It's usually a numbered file like "46994.xml", not "primary_doc.xml"
            xml_file = None
            for item in index_data.get("directory", {}).get("item", []):
                name = item.get("name", "").lower()
                if "infotable" in name and name.endswith(".xml"):
                    xml_file = item.get("name")
                    break
                    
            if not xml_file:
                # Try alternate naming - look for numbered XML files (not primary_doc)
                for item in index_data.get("directory", {}).get("item", []):
                    name = item.get("name", "")
                    if name.endswith(".xml") and "primary" not in name.lower():
                        xml_file = name
                        break
                        
            if not xml_file:
                return []
                
            # Fetch the holdings XML
            self._rate_limit()
            xml_url = f"{archive_base}/Archives/edgar/data/{cik_clean}/{accession_clean}/{xml_file}"
            resp = self.session.get(xml_url, timeout=15)
            resp.raise_for_status()
            
            # Parse XML content
            content = resp.text
            
            # Extract each infoTable entry
            entries = re.findall(r'<infoTable>(.*?)</infoTable>', content, re.DOTALL | re.IGNORECASE)
            
            if not entries:
                # Try alternate format
                entries = re.findall(r'<ns1:infoTable>(.*?)</ns1:infoTable>', content, re.DOTALL | re.IGNORECASE)
                
            for entry in entries:
                holding = self._parse_holding_entry(entry)
                if holding:
                    holdings.append(holding)
                    
        except Exception as e:
            print(f"Error parsing 13F holdings: {e}")
            
        return holdings
        
    def _parse_holding_entry(self, xml_entry: str) -> Optional[Dict]:
        """Parse a single holding entry from 13F XML."""
        def extract(tag):
            # Try both namespaced and non-namespaced
            patterns = [
                f"<{tag}>([^<]+)</{tag}>",
                f"<ns1:{tag}>([^<]+)</ns1:{tag}>",
            ]
            for pattern in patterns:
                match = re.search(pattern, xml_entry, re.IGNORECASE)
                if match:
                    return match.group(1).strip()
            return None
            
        company_name = extract("nameOfIssuer")
        cusip = extract("cusip")
        value = extract("value")  # In thousands
        shares = extract("sshPrnamt") or extract("shrsOrPrnAmt")
        
        if not all([company_name, value]):
            return None
            
        # Try to get ticker from CUSIP
        ticker = self.CUSIP_TO_TICKER.get(cusip, "")
        if not ticker:
            # Try to derive from company name
            ticker = self._guess_ticker(company_name)
            
        try:
            # SEC 13F reports value in dollars (not thousands as documentation suggests)
            value_float = float(value.replace(",", ""))
            shares_int = int(shares.replace(",", "")) if shares else 0
        except:
            value_float = 0
            shares_int = 0
            
        return {
            "company_name": company_name,
            "ticker": ticker,
            "cusip": cusip,
            "value": value_float,
            "shares": shares_int,
        }
        
    def _guess_ticker(self, company_name: str) -> str:
        """Try to guess ticker from company name."""
        name_lower = company_name.lower()
        
        guesses = {
            "apple": "AAPL",
            "microsoft": "MSFT",
            "alphabet": "GOOGL",
            "amazon": "AMZN",
            "nvidia": "NVDA",
            "meta platforms": "META",
            "tesla": "TSLA",
            "jpmorgan": "JPM",
            "goldman": "GS",
            "berkshire": "BRK.B",
            "visa": "V",
            "mastercard": "MA",
            "johnson & johnson": "JNJ",
            "unitedhealth": "UNH",
            "eli lilly": "LLY",
            "broadcom": "AVGO",
            "salesforce": "CRM",
            "netflix": "NFLX",
            "costco": "COST",
            "home depot": "HD",
            "walt disney": "DIS",
            "coca-cola": "KO",
            "pepsico": "PEP",
            "chevron": "CVX",
            "exxon": "XOM",
        }
        
        for key, ticker in guesses.items():
            if key in name_lower:
                return ticker
                
        return ""
        
    def get_top_holdings(self, fund_name: str, limit: int = 20) -> List[Dict]:
        """Get top holdings for a fund by name."""
        cik = self.TRACKED_FUNDS.get(fund_name)
        if not cik:
            print(f"Unknown fund: {fund_name}")
            return []
            
        filing = self.get_latest_13f(cik)
        if not filing:
            return []
            
        holdings = self.get_13f_holdings(cik, filing["accession"])
        
        # Sort by value and return top N
        holdings.sort(key=lambda x: x["value"], reverse=True)
        
        return holdings[:limit]
        
    def compare_filings(self, fund_cik: str) -> List[HoldingChange]:
        """
        Compare two most recent 13F filings to find changes.
        
        This is the money feature - shows what funds bought/sold.
        """
        changes = []
        
        try:
            self._rate_limit()
            
            url = f"{self.BASE_URL}/submissions/CIK{fund_cik}.json"
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
            
            data = resp.json()
            filings = data.get("filings", {}).get("recent", {})
            forms = filings.get("form", [])
            accessions = filings.get("accessionNumber", [])
            
            # Find two most recent 13F-HR filings
            recent_13fs = []
            for i, form in enumerate(forms):
                if form == "13F-HR":
                    recent_13fs.append(accessions[i])
                    if len(recent_13fs) >= 2:
                        break
                        
            if len(recent_13fs) < 2:
                return []
                
            # Get holdings from both filings
            current_holdings = self.get_13f_holdings(fund_cik, recent_13fs[0])
            previous_holdings = self.get_13f_holdings(fund_cik, recent_13fs[1])
            
            # Create lookup by CUSIP
            current_by_cusip = {h["cusip"]: h for h in current_holdings}
            previous_by_cusip = {h["cusip"]: h for h in previous_holdings}
            
            # Find changes
            all_cusips = set(current_by_cusip.keys()) | set(previous_by_cusip.keys())
            
            for cusip in all_cusips:
                current = current_by_cusip.get(cusip)
                previous = previous_by_cusip.get(cusip)
                
                if current and not previous:
                    # NEW position
                    changes.append(HoldingChange(
                        ticker=current["ticker"] or cusip[:8],
                        company_name=current["company_name"],
                        action="NEW",
                        shares_current=current["shares"],
                        shares_previous=0,
                        value_current=current["value"],
                        percent_change=100.0,
                    ))
                elif previous and not current:
                    # SOLD entire position
                    changes.append(HoldingChange(
                        ticker=previous["ticker"] or cusip[:8],
                        company_name=previous["company_name"],
                        action="SOLD",
                        shares_current=0,
                        shares_previous=previous["shares"],
                        value_current=0,
                        percent_change=-100.0,
                    ))
                elif current and previous:
                    # Check for increase/decrease
                    if current["shares"] > previous["shares"] * 1.1:  # >10% increase
                        pct = ((current["shares"] - previous["shares"]) / previous["shares"]) * 100
                        changes.append(HoldingChange(
                            ticker=current["ticker"] or cusip[:8],
                            company_name=current["company_name"],
                            action="INCREASED",
                            shares_current=current["shares"],
                            shares_previous=previous["shares"],
                            value_current=current["value"],
                            percent_change=pct,
                        ))
                    elif current["shares"] < previous["shares"] * 0.9:  # >10% decrease
                        pct = ((current["shares"] - previous["shares"]) / previous["shares"]) * 100
                        changes.append(HoldingChange(
                            ticker=current["ticker"] or cusip[:8],
                            company_name=current["company_name"],
                            action="DECREASED",
                            shares_current=current["shares"],
                            shares_previous=previous["shares"],
                            value_current=current["value"],
                            percent_change=pct,
                        ))
                        
            # Sort by absolute value of change
            changes.sort(key=lambda x: abs(x.percent_change), reverse=True)
            
        except Exception as e:
            print(f"Error comparing filings: {e}")
            
        return changes


def format_value(value: float) -> str:
    """Format dollar value nicely."""
    if value >= 1_000_000_000:
        return f"${value/1_000_000_000:.1f}B"
    elif value >= 1_000_000:
        return f"${value/1_000_000:.1f}M"
    elif value >= 1_000:
        return f"${value/1_000:.0f}K"
    else:
        return f"${value:.0f}"


def run_13f_scan(fund_names: Optional[List[str]] = None, send_telegram: bool = True):
    """
    Scan 13F filings for significant changes.
    
    Args:
        fund_names: List of fund names to scan (default: all tracked funds)
        send_telegram: Whether to send Telegram alerts
    """
    tracker = HedgeFundTracker()
    
    funds_to_scan = fund_names or list(tracker.TRACKED_FUNDS.keys())
    
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Scanning 13F filings...")
    
    all_changes = []
    
    for fund_name in funds_to_scan:
        cik = tracker.TRACKED_FUNDS.get(fund_name)
        if not cik:
            continue
            
        print(f"\n  Checking {fund_name}...")
        
        # Get latest filing info
        filing = tracker.get_latest_13f(cik)
        if not filing:
            continue
            
        print(f"    Latest filing: {filing['filing_date']}")
        
        # Get changes
        changes = tracker.compare_filings(cik)
        
        if changes:
            # Filter to significant changes
            significant = [c for c in changes if c.action in ["NEW", "SOLD"] or abs(c.percent_change) > 25]
            
            if significant:
                print(f"    Found {len(significant)} significant changes")
                
                for change in significant[:5]:  # Top 5
                    action_emoji = {
                        "NEW": "+",
                        "SOLD": "-",
                        "INCREASED": "+",
                        "DECREASED": "-",
                    }.get(change.action, "")
                    
                    print(f"      {action_emoji} {change.action}: {change.ticker or change.company_name[:20]}")
                    
                    all_changes.append({
                        "fund": fund_name,
                        "change": change,
                    })
                    
    # Send consolidated Telegram alert
    if send_telegram and all_changes:
        _send_13f_alert(all_changes)
        
    return all_changes


def _send_13f_alert(changes: List[Dict]):
    """Send Telegram alert for 13F changes."""
    
    # Group by action type
    new_positions = [c for c in changes if c["change"].action == "NEW"]
    sold_positions = [c for c in changes if c["change"].action == "SOLD"]
    increased = [c for c in changes if c["change"].action == "INCREASED"]
    decreased = [c for c in changes if c["change"].action == "DECREASED"]
    
    lines = ["13F FUND ACTIVITY\n"]
    
    if new_positions:
        lines.append("NEW POSITIONS:")
        for c in new_positions[:5]:
            ticker = c["change"].ticker or c["change"].company_name[:15]
            lines.append(f"  {c['fund'][:15]}: {ticker} ({format_value(c['change'].value_current)})")
            
    if sold_positions:
        lines.append("\nSOLD ENTIRELY:")
        for c in sold_positions[:5]:
            ticker = c["change"].ticker or c["change"].company_name[:15]
            lines.append(f"  {c['fund'][:15]}: {ticker}")
            
    if increased:
        lines.append("\nINCREASED >25%:")
        for c in increased[:3]:
            ticker = c["change"].ticker or c["change"].company_name[:15]
            lines.append(f"  {c['fund'][:15]}: {ticker} (+{c['change'].percent_change:.0f}%)")
            
    if decreased:
        lines.append("\nDECREASED >25%:")
        for c in decreased[:3]:
            ticker = c["change"].ticker or c["change"].company_name[:15]
            lines.append(f"  {c['fund'][:15]}: {ticker} ({c['change'].percent_change:.0f}%)")
            
    message = "\n".join(lines)
    send_telegram_message(message)


def get_berkshire_holdings(limit: int = 20) -> List[Dict]:
    """Quick function to get Buffett's current holdings."""
    tracker = HedgeFundTracker()
    return tracker.get_top_holdings("Berkshire Hathaway", limit)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="13F Hedge Fund Tracker")
    parser.add_argument("--fund", type=str, help="Specific fund to check")
    parser.add_argument("--holdings", action="store_true", help="Show current holdings")
    parser.add_argument("--changes", action="store_true", help="Show recent changes")
    parser.add_argument("--no-telegram", action="store_true", help="Don't send alerts")
    
    args = parser.parse_args()
    
    tracker = HedgeFundTracker()
    
    if args.holdings:
        fund = args.fund or "Berkshire Hathaway"
        print(f"\nTop holdings for {fund}:")
        holdings = tracker.get_top_holdings(fund)
        for i, h in enumerate(holdings, 1):
            ticker = h["ticker"] or h["company_name"][:20]
            print(f"  {i:2}. {ticker:8} - {format_value(h['value'])}")
    else:
        # Default: scan for changes
        funds = [args.fund] if args.fund else None
        run_13f_scan(funds, send_telegram=not args.no_telegram)

