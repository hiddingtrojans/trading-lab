"""
Insider Buying Tracker

Track when company insiders (CEOs, CFOs, directors) buy stock.
This is one of the strongest signals - they know their company best.

Data source: SEC EDGAR Form 4 filings (free, real-time)

Why this matters:
- Insiders sell for many reasons (taxes, diversification, buying a house)
- Insiders BUY for only ONE reason: they think the stock will go up
"""

import os
import sys
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass
import json
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))


@dataclass
class InsiderTransaction:
    """A single insider transaction."""
    ticker: str
    company_name: str
    insider_name: str
    insider_title: str  # CEO, CFO, Director, etc.
    transaction_type: str  # "Buy" or "Sell"
    shares: int
    price: float
    value: float  # shares * price
    date: str
    filing_url: str


@dataclass 
class InsiderSummary:
    """Summary of insider activity for a stock."""
    ticker: str
    company_name: str
    total_buys_30d: int
    total_sells_30d: int
    buy_value_30d: float
    sell_value_30d: float
    net_value_30d: float  # buys - sells
    recent_transactions: List[InsiderTransaction]
    signal: str  # "Strong Buy", "Buying", "Mixed", "Selling", "Strong Sell"


class InsiderTracker:
    """
    Track insider buying/selling from SEC Form 4 filings.
    
    The edge: Real-time data that GPT doesn't have.
    """
    
    SEC_HEADERS = {
        'User-Agent': 'Research Platform contact@example.com',
        'Accept-Encoding': 'gzip, deflate',
    }
    
    def __init__(self):
        self.cache = {}
    
    def get_recent_filings(self, ticker: str, days: int = 30) -> List[InsiderTransaction]:
        """
        Get recent Form 4 filings for a ticker.
        
        Form 4 = Insider transactions (must be filed within 2 business days)
        """
        transactions = []
        
        try:
            # Step 1: Get company CIK from SEC
            cik = self._get_cik(ticker)
            if not cik:
                return []
            
            # Step 2: Get recent Form 4 filings
            filings = self._get_form4_filings(cik, days)
            
            # Step 3: Parse each filing
            for filing in filings[:20]:  # Limit to recent 20
                txns = self._parse_form4(filing, ticker)
                transactions.extend(txns)
            
            # Sort by date (newest first)
            transactions.sort(key=lambda x: x.date, reverse=True)
            
            return transactions
            
        except Exception as e:
            print(f"   Error fetching insider data for {ticker}: {e}")
            return []
    
    def _get_cik(self, ticker: str) -> Optional[str]:
        """Get company CIK number from ticker using SEC company tickers file."""
        try:
            # Use SEC's official ticker-to-CIK mapping
            if not hasattr(self, '_cik_map'):
                url = "https://www.sec.gov/files/company_tickers.json"
                response = requests.get(url, headers=self.SEC_HEADERS, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    # Build ticker -> CIK map
                    self._cik_map = {}
                    for entry in data.values():
                        t = entry.get('ticker', '').upper()
                        cik = str(entry.get('cik_str', ''))
                        if t and cik:
                            self._cik_map[t] = cik
                else:
                    self._cik_map = {}
            
            return self._cik_map.get(ticker.upper())
            
        except Exception as e:
            print(f"   Error getting CIK: {e}")
            return None
    
    def _get_form4_filings(self, cik: str, days: int) -> List[Dict]:
        """Get list of Form 4 filings for a company."""
        try:
            # Use SEC EDGAR API
            url = f"https://data.sec.gov/submissions/CIK{cik.zfill(10)}.json"
            
            response = requests.get(url, headers=self.SEC_HEADERS, timeout=10)
            
            if response.status_code != 200:
                return []
            
            data = response.json()
            filings = []
            
            # Get recent filings
            recent = data.get('filings', {}).get('recent', {})
            forms = recent.get('form', [])
            dates = recent.get('filingDate', [])
            accessions = recent.get('accessionNumber', [])
            
            cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            
            for i, form in enumerate(forms):
                if form in ['4', '4/A']:  # Form 4 or amended Form 4
                    if i < len(dates) and dates[i] >= cutoff_date:
                        filings.append({
                            'form': form,
                            'date': dates[i],
                            'accession': accessions[i] if i < len(accessions) else None,
                            'cik': cik,
                        })
            
            return filings
            
        except Exception as e:
            return []
    
    def _parse_form4(self, filing: Dict, ticker: str) -> List[InsiderTransaction]:
        """Parse a Form 4 filing to extract transactions."""
        transactions = []
        
        try:
            cik = filing['cik']
            accession = filing['accession'].replace('-', '')
            
            # First, get the directory listing to find the XML file
            index_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/index.json"
            index_response = requests.get(index_url, headers=self.SEC_HEADERS, timeout=10)
            
            if index_response.status_code != 200:
                return []
            
            # Find the Form 4 XML file
            xml_filename = None
            files = index_response.json().get('directory', {}).get('item', [])
            for f in files:
                name = f.get('name', '')
                if name.endswith('.xml') and 'form4' in name.lower():
                    xml_filename = name
                    break
                # Also check for standard naming
                if name.endswith('.xml') and 'index' not in name.lower():
                    xml_filename = name
            
            if not xml_filename:
                return []
            
            # Get the XML file
            url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{xml_filename}"
            response = requests.get(url, headers=self.SEC_HEADERS, timeout=10)
            
            if response.status_code != 200:
                return []
            
            # Parse XML
            root = ET.fromstring(response.content)
            
            # Get insider info
            reporter = root.find('.//reportingOwner')
            if reporter is None:
                return []
            
            insider_name = ""
            insider_title = ""
            
            owner_id = reporter.find('.//reportingOwnerId')
            if owner_id is not None:
                name_elem = owner_id.find('rptOwnerName')
                insider_name = name_elem.text if name_elem is not None else "Unknown"
            
            relationship = reporter.find('.//reportingOwnerRelationship')
            if relationship is not None:
                if relationship.find('isOfficer') is not None:
                    title_elem = relationship.find('officerTitle')
                    insider_title = title_elem.text if title_elem is not None else "Officer"
                elif relationship.find('isDirector') is not None:
                    insider_title = "Director"
                elif relationship.find('isTenPercentOwner') is not None:
                    insider_title = "10% Owner"
                else:
                    insider_title = "Insider"
            
            # Get company name
            issuer = root.find('.//issuer')
            company_name = ""
            if issuer is not None:
                name_elem = issuer.find('issuerName')
                company_name = name_elem.text if name_elem is not None else ticker
            
            # Get non-derivative transactions (common stock)
            non_deriv = root.find('.//nonDerivativeTable')
            if non_deriv is not None:
                for txn in non_deriv.findall('.//nonDerivativeTransaction'):
                    tx = self._parse_transaction(txn, ticker, company_name, insider_name, insider_title, filing)
                    if tx:
                        transactions.append(tx)
            
            return transactions
            
        except Exception as e:
            return []
    
    def _parse_transaction(self, txn, ticker, company_name, insider_name, insider_title, filing) -> Optional[InsiderTransaction]:
        """Parse a single transaction from Form 4."""
        try:
            # Transaction type
            coding = txn.find('.//transactionCoding')
            if coding is None:
                return None
            
            code_elem = coding.find('transactionCode')
            code = code_elem.text if code_elem is not None else ""
            
            # P = Purchase, S = Sale, A = Award, M = Exercise
            if code == 'P':
                tx_type = "Buy"
            elif code == 'S':
                tx_type = "Sell"
            else:
                return None  # Skip grants, exercises, etc.
            
            # Shares
            amounts = txn.find('.//transactionAmounts')
            if amounts is None:
                return None
            
            shares_elem = amounts.find('.//transactionShares/value')
            shares = int(float(shares_elem.text)) if shares_elem is not None else 0
            
            price_elem = amounts.find('.//transactionPricePerShare/value')
            price = float(price_elem.text) if price_elem is not None and price_elem.text else 0
            
            # Date
            date_elem = txn.find('.//transactionDate/value')
            date = date_elem.text if date_elem is not None else filing['date']
            
            if shares == 0:
                return None
            
            return InsiderTransaction(
                ticker=ticker,
                company_name=company_name,
                insider_name=insider_name,
                insider_title=insider_title,
                transaction_type=tx_type,
                shares=shares,
                price=price,
                value=shares * price,
                date=date,
                filing_url=f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={ticker}&type=4",
            )
            
        except Exception as e:
            return None
    
    def get_insider_summary(self, ticker: str, days: int = 30) -> Optional[InsiderSummary]:
        """Get summary of insider activity for a stock."""
        transactions = self.get_recent_filings(ticker, days)
        
        if not transactions:
            return None
        
        # Calculate summary
        buys = [t for t in transactions if t.transaction_type == "Buy"]
        sells = [t for t in transactions if t.transaction_type == "Sell"]
        
        buy_value = sum(t.value for t in buys)
        sell_value = sum(t.value for t in sells)
        net_value = buy_value - sell_value
        
        # Determine signal
        if len(buys) >= 3 and buy_value > sell_value * 2:
            signal = "🟢 Strong Buy Signal"
        elif len(buys) >= 2 and buy_value > sell_value:
            signal = "🟢 Buying"
        elif len(sells) >= 3 and sell_value > buy_value * 2:
            signal = "🔴 Strong Sell Signal"
        elif len(sells) >= 2 and sell_value > buy_value:
            signal = "🔴 Selling"
        else:
            signal = "⚪ Mixed/Neutral"
        
        company_name = transactions[0].company_name if transactions else ticker
        
        return InsiderSummary(
            ticker=ticker,
            company_name=company_name,
            total_buys_30d=len(buys),
            total_sells_30d=len(sells),
            buy_value_30d=buy_value,
            sell_value_30d=sell_value,
            net_value_30d=net_value,
            recent_transactions=transactions[:10],
            signal=signal,
        )
    
    def format_summary(self, summary: InsiderSummary) -> str:
        """Format insider summary for display."""
        lines = [
            "═" * 50,
            f"🔍 INSIDER ACTIVITY: {summary.ticker}",
            f"   {summary.company_name}",
            "═" * 50,
            "",
            f"Signal: {summary.signal}",
            "",
            f"Last 30 Days:",
            f"  📈 Buys:  {summary.total_buys_30d} transactions (${summary.buy_value_30d:,.0f})",
            f"  📉 Sells: {summary.total_sells_30d} transactions (${summary.sell_value_30d:,.0f})",
            f"  💰 Net:   ${summary.net_value_30d:+,.0f}",
            "",
        ]
        
        if summary.recent_transactions:
            lines.append("Recent Transactions:")
            lines.append("─" * 50)
            
            for txn in summary.recent_transactions[:5]:
                emoji = "📈" if txn.transaction_type == "Buy" else "📉"
                lines.append(f"  {emoji} {txn.date}: {txn.insider_name}")
                lines.append(f"     {txn.insider_title} {txn.transaction_type.upper()} {txn.shares:,} shares @ ${txn.price:.2f}")
                lines.append(f"     Value: ${txn.value:,.0f}")
                lines.append("")
        
        lines.append("═" * 50)
        
        return "\n".join(lines)
    
    def scan_for_buying(self, tickers: List[str], min_buys: int = 2, min_value: float = 100000) -> List[InsiderSummary]:
        """
        Scan multiple tickers for insider buying activity.
        
        Args:
            tickers: List of tickers to scan
            min_buys: Minimum number of buy transactions
            min_value: Minimum total buy value
        
        Returns:
            List of stocks with significant insider buying
        """
        results = []
        
        print(f"\n🔍 Scanning {len(tickers)} stocks for insider buying...")
        
        for i, ticker in enumerate(tickers):
            if i % 10 == 0 and i > 0:
                print(f"   Progress: {i}/{len(tickers)}...")
            
            summary = self.get_insider_summary(ticker)
            
            if summary:
                if summary.total_buys_30d >= min_buys and summary.buy_value_30d >= min_value:
                    results.append(summary)
                    print(f"   ✅ {ticker}: {summary.total_buys_30d} buys (${summary.buy_value_30d:,.0f})")
            
            time.sleep(0.5)  # Rate limiting for SEC
        
        # Sort by buy value
        results.sort(key=lambda x: x.buy_value_30d, reverse=True)
        
        return results


def check_insider(ticker: str):
    """Quick check of insider activity for a ticker."""
    tracker = InsiderTracker()
    
    print(f"\n🔍 Checking insider activity for {ticker}...")
    
    summary = tracker.get_insider_summary(ticker)
    
    if summary:
        print(tracker.format_summary(summary))
    else:
        print(f"   No insider transactions found for {ticker} in last 30 days")


def scan_watchlist_for_insiders(tickers: List[str]):
    """Scan a watchlist for insider buying."""
    tracker = InsiderTracker()
    
    results = tracker.scan_for_buying(tickers)
    
    if results:
        print("\n" + "═" * 50)
        print("🔔 INSIDER BUYING DETECTED")
        print("═" * 50)
        
        for summary in results[:10]:
            print(f"\n{summary.signal}")
            print(f"   {summary.ticker}: {summary.total_buys_30d} buys (${summary.buy_value_30d:,.0f})")
            
            for txn in summary.recent_transactions[:2]:
                print(f"   • {txn.insider_title} bought ${txn.value:,.0f}")
    else:
        print("\n   No significant insider buying detected")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        ticker = sys.argv[1].upper()
        check_insider(ticker)
    else:
        # Demo with some tickers
        print("Usage: python insider_tracker.py TICKER")
        print("\nExample: python insider_tracker.py MBOT")

