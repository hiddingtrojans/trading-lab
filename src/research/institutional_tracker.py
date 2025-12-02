"""
13F Institutional Tracker

Track what hedge funds and institutions are buying/selling.
13F filings are required quarterly for institutions with >$100M in assets.

Data source: SEC EDGAR 13F filings (free, quarterly)

Why this matters:
- Big money moves markets
- See what ARK, Vanguard, BlackRock are buying BEFORE the crowd
- Track position changes over quarters
"""

import os
import sys
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import json
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))


# Well-known institutions to track
NOTABLE_INSTITUTIONS = {
    # Activist/Growth
    '1649339': 'ARK Investment Management',
    '1067983': 'Berkshire Hathaway',
    '1350694': 'Tiger Global Management',
    '1336528': 'Citadel Advisors',
    '1037389': 'Renaissance Technologies',
    '1061768': 'Bridgewater Associates',
    '1364742': 'Viking Global Investors',
    '1103804': 'D.E. Shaw',
    '1595082': 'Coatue Management',
    '921669': 'Soros Fund Management',
    
    # Big Index Funds
    '102909': 'Vanguard Group',
    '93751': 'BlackRock',
    '1350941': 'State Street',
    '19617': 'Fidelity',
    
    # Notable Hedge Funds
    '1167483': 'Dragoneer Investment',
    '1579982': 'Lone Pine Capital',
    '1484148': 'Hillhouse Capital',
    '1466857': 'Altimeter Capital',
}


@dataclass
class InstitutionalHolding:
    """A single institutional holding from 13F."""
    institution_name: str
    institution_cik: str
    ticker: str
    company_name: str
    shares: int
    value: int  # in $1000s
    filing_date: str
    report_date: str  # Quarter end date


@dataclass
class InstitutionalChange:
    """Change in institutional holdings between quarters."""
    institution_name: str
    ticker: str
    prev_shares: int
    curr_shares: int
    change_shares: int
    change_pct: float
    action: str  # "NEW", "ADDED", "REDUCED", "SOLD"
    value: int  # Current value in $1000s


@dataclass
class InstitutionalSummary:
    """Summary of institutional activity for a stock."""
    ticker: str
    company_name: str
    total_institutions: int
    new_positions: int
    increased_positions: int
    decreased_positions: int
    sold_positions: int
    notable_changes: List[InstitutionalChange]
    signal: str


class InstitutionalTracker:
    """
    Track institutional holdings from SEC 13F filings.
    
    The edge: See what big money is doing before retail.
    """
    
    SEC_HEADERS = {
        'User-Agent': 'Research Platform contact@example.com',
        'Accept-Encoding': 'gzip, deflate',
    }
    
    def __init__(self):
        self._cik_map = None
        self._ticker_to_cusip = {}
    
    def _get_cik_map(self) -> Dict[str, str]:
        """Load ticker to CIK mapping."""
        if self._cik_map is None:
            try:
                url = "https://www.sec.gov/files/company_tickers.json"
                response = requests.get(url, headers=self.SEC_HEADERS, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    self._cik_map = {}
                    for entry in data.values():
                        t = entry.get('ticker', '').upper()
                        cik = str(entry.get('cik_str', ''))
                        if t and cik:
                            self._cik_map[t] = cik
                else:
                    self._cik_map = {}
            except Exception:
                self._cik_map = {}
        
        return self._cik_map
    
    def get_recent_13f_filings(self, institution_cik: str, count: int = 2) -> List[Dict]:
        """Get recent 13F filings for an institution."""
        try:
            url = f"https://data.sec.gov/submissions/CIK{institution_cik.zfill(10)}.json"
            response = requests.get(url, headers=self.SEC_HEADERS, timeout=10)
            
            if response.status_code != 200:
                return []
            
            data = response.json()
            filings = []
            
            recent = data.get('filings', {}).get('recent', {})
            forms = recent.get('form', [])
            dates = recent.get('filingDate', [])
            accessions = recent.get('accessionNumber', [])
            
            for i, form in enumerate(forms):
                if form in ['13F-HR', '13F-HR/A']:
                    if len(filings) < count:
                        filings.append({
                            'form': form,
                            'date': dates[i] if i < len(dates) else '',
                            'accession': accessions[i] if i < len(accessions) else '',
                            'cik': institution_cik,
                        })
            
            return filings
            
        except Exception as e:
            return []
    
    def parse_13f_holdings(self, filing: Dict) -> Dict[str, InstitutionalHolding]:
        """Parse a 13F filing to extract holdings."""
        holdings = {}
        
        try:
            cik = filing['cik']
            accession = filing['accession'].replace('-', '')
            
            # Get directory listing
            index_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/index.json"
            index_response = requests.get(index_url, headers=self.SEC_HEADERS, timeout=10)
            
            if index_response.status_code != 200:
                return holdings
            
            # Find the infotable XML file (contains holdings)
            xml_filename = None
            files = index_response.json().get('directory', {}).get('item', [])
            for f in files:
                name = f.get('name', '').lower()
                if 'infotable' in name and name.endswith('.xml'):
                    xml_filename = f.get('name')
                    break
            
            if not xml_filename:
                return holdings
            
            # Get the holdings XML
            url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{xml_filename}"
            response = requests.get(url, headers=self.SEC_HEADERS, timeout=10)
            
            if response.status_code != 200:
                return holdings
            
            # Parse XML
            # Remove namespace for easier parsing
            content = response.text
            content = content.replace('xmlns="http://www.sec.gov/edgar/document/thirteenf/informationtable"', '')
            
            root = ET.fromstring(content)
            
            institution_name = NOTABLE_INSTITUTIONS.get(cik, f"CIK {cik}")
            
            for info_table in root.findall('.//infoTable'):
                try:
                    name_elem = info_table.find('nameOfIssuer')
                    cusip_elem = info_table.find('cusip')
                    shares_elem = info_table.find('.//sshPrnamt')
                    value_elem = info_table.find('value')
                    
                    if name_elem is None or shares_elem is None:
                        continue
                    
                    company_name = name_elem.text or ''
                    cusip = cusip_elem.text if cusip_elem is not None else ''
                    shares = int(shares_elem.text) if shares_elem.text else 0
                    value = int(value_elem.text) if value_elem is not None and value_elem.text else 0
                    
                    # Try to get ticker from CUSIP
                    ticker = self._cusip_to_ticker(cusip, company_name)
                    
                    if ticker:
                        holdings[ticker] = InstitutionalHolding(
                            institution_name=institution_name,
                            institution_cik=cik,
                            ticker=ticker,
                            company_name=company_name,
                            shares=shares,
                            value=value,
                            filing_date=filing['date'],
                            report_date=filing['date'],
                        )
                
                except Exception:
                    continue
            
            return holdings
            
        except Exception as e:
            return holdings
    
    def _cusip_to_ticker(self, cusip: str, company_name: str) -> Optional[str]:
        """Convert CUSIP to ticker symbol."""
        # Check cache
        if cusip in self._ticker_to_cusip:
            return self._ticker_to_cusip[cusip]
        
        # Common CUSIP to ticker mappings for major stocks
        KNOWN_CUSIPS = {
            '037833100': 'AAPL',  # Apple
            '594918104': 'MSFT',  # Microsoft
            '02079K305': 'GOOG',  # Alphabet Class C
            '02079K107': 'GOOGL', # Alphabet Class A
            '023135106': 'AMZN',  # Amazon
            '88160R101': 'TSLA',  # Tesla
            '30303M102': 'META',  # Meta
            '67066G104': 'NVDA',  # NVIDIA
            '11135F101': 'BRK.B', # Berkshire
            '478160104': 'JNJ',   # Johnson & Johnson
            '91324P102': 'UNH',   # UnitedHealth
            '92826C839': 'V',     # Visa
            '254687106': 'DIS',   # Disney
            '742718109': 'PG',    # Procter & Gamble
            '46625H100': 'JPM',   # JPMorgan
            '17275R102': 'CSCO',  # Cisco
            '00206R102': 'T',     # AT&T
            '931142103': 'WMT',   # Walmart
            '60871R209': 'MRK',   # Merck
            '713448108': 'PEP',   # PepsiCo
        }
        
        if cusip in KNOWN_CUSIPS:
            ticker = KNOWN_CUSIPS[cusip]
            self._ticker_to_cusip[cusip] = ticker
            return ticker
        
        # Try to match by company name
        company_upper = company_name.upper()
        
        NAME_TO_TICKER = {
            'APPLE': 'AAPL',
            'MICROSOFT': 'MSFT',
            'ALPHABET': 'GOOGL',
            'AMAZON': 'AMZN',
            'TESLA': 'TSLA',
            'META PLATFORMS': 'META',
            'NVIDIA': 'NVDA',
            'BERKSHIRE': 'BRK.B',
            'JOHNSON': 'JNJ',
            'UNITEDHEALTH': 'UNH',
            'VISA': 'V',
            'DISNEY': 'DIS',
            'PROCTER': 'PG',
            'JPMORGAN': 'JPM',
            'CISCO': 'CSCO',
            'WALMART': 'WMT',
            'PEPSICO': 'PEP',
        }
        
        for name_part, ticker in NAME_TO_TICKER.items():
            if name_part in company_upper:
                self._ticker_to_cusip[cusip] = ticker
                return ticker
        
        return None
    
    def _find_ticker_in_13f(self, filing: Dict, target_ticker: str) -> Optional[Tuple[int, int, str]]:
        """
        Search a 13F filing for a specific ticker by company name.
        Returns (shares, value, company_name) if found.
        """
        try:
            import yfinance as yf
            
            # Get company name for the target ticker
            stock = yf.Ticker(target_ticker)
            info = stock.info
            company_name = info.get('shortName', info.get('longName', target_ticker))
            
            # Get the words to search for
            SKIP_WORDS = {'INC', 'INC.', 'CORP', 'CORP.', 'LTD', 'LTD.', 'CO', 'CO.', 
                          'LLC', 'LP', 'PLC', 'THE', 'A', 'AN', 'OF', 'AND', '&'}
            
            search_terms = [target_ticker.upper()]
            if company_name:
                # Add company name words (first meaningful word)
                name_words = company_name.upper().split()
                for word in name_words:
                    # Clean punctuation
                    word_clean = word.rstrip('.,')
                    if word_clean not in SKIP_WORDS and len(word_clean) >= 3:
                        search_terms.append(word_clean)
                        break  # Just take the first meaningful word
            
            # Parse the 13F
            cik = filing['cik']
            accession = filing['accession'].replace('-', '')
            
            index_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/index.json"
            index_response = requests.get(index_url, headers=self.SEC_HEADERS, timeout=10)
            
            if index_response.status_code != 200:
                return None
            
            xml_filename = None
            files = index_response.json().get('directory', {}).get('item', [])
            for f in files:
                name = f.get('name', '').lower()
                if 'infotable' in name and name.endswith('.xml'):
                    xml_filename = f.get('name')
                    break
            
            if not xml_filename:
                return None
            
            url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{xml_filename}"
            response = requests.get(url, headers=self.SEC_HEADERS, timeout=10)
            
            if response.status_code != 200:
                return None
            
            content = response.text
            content = content.replace('xmlns="http://www.sec.gov/edgar/document/thirteenf/informationtable"', '')
            
            root = ET.fromstring(content)
            
            for info_table in root.findall('.//infoTable'):
                name_elem = info_table.find('nameOfIssuer')
                if name_elem is None:
                    continue
                
                issuer_name = (name_elem.text or '').upper()
                
                # Check if this is the company we're looking for
                # Match ticker exactly OR company name starts exactly with our search
                matched = False
                
                # Clean issuer name for comparison
                issuer_clean = issuer_name.replace('.', '').replace(',', '')
                
                # Check if ticker matches (e.g., "AAPL" in "AAPL INC")
                if target_ticker in issuer_clean:
                    matched = True
                else:
                    # Check if the issuer name starts with company name
                    # e.g., "APPLE INC" should match "APPLE INC" but not "APPLE HOSPITALITY"
                    for term in search_terms:
                        if term == target_ticker:
                            continue  # Skip ticker, check names
                        # Issuer should start with the term followed by common suffixes
                        for suffix in [' INC', ' CORP', ' CO', ' LTD', ' LLC', ' PLC', ' CLASS']:
                            if issuer_clean.startswith(term + suffix):
                                matched = True
                                break
                        if matched:
                            break
                
                if matched:
                    shares_elem = info_table.find('.//sshPrnamt')
                    value_elem = info_table.find('value')
                    
                    shares = int(shares_elem.text) if shares_elem is not None and shares_elem.text else 0
                    value = int(value_elem.text) if value_elem is not None and value_elem.text else 0
                    
                    if shares > 0:
                        return (shares, value, name_elem.text)
            
            return None
            
        except Exception as e:
            return None
    
    def get_institutional_activity(self, ticker: str) -> Optional[InstitutionalSummary]:
        """
        Get institutional activity for a stock by checking notable institutions.
        
        Note: This is a simplified approach. For comprehensive data,
        you'd need a service like WhaleWisdom or Bloomberg.
        """
        ticker = ticker.upper()
        changes = []
        company_name = ticker
        
        print(f"   Checking {len(NOTABLE_INSTITUTIONS)} major institutions...")
        
        checked = 0
        for inst_cik, inst_name in list(NOTABLE_INSTITUTIONS.items())[:15]:  # Check top 15
            try:
                checked += 1
                if checked % 5 == 0:
                    print(f"   Progress: {checked}/{min(15, len(NOTABLE_INSTITUTIONS))}...")
                
                # Get last 2 filings
                filings = self.get_recent_13f_filings(inst_cik, count=2)
                
                if len(filings) < 1:
                    continue
                
                # Search for the ticker in the filing
                current_result = self._find_ticker_in_13f(filings[0], ticker)
                
                if current_result:
                    curr_shares, curr_value, found_name = current_result
                    company_name = found_name or ticker
                    
                    # Check previous quarter
                    prev_shares = 0
                    if len(filings) >= 2:
                        prev_result = self._find_ticker_in_13f(filings[1], ticker)
                        if prev_result:
                            prev_shares = prev_result[0]
                    
                    change_shares = curr_shares - prev_shares
                    
                    if prev_shares > 0:
                        change_pct = (change_shares / prev_shares) * 100
                    else:
                        change_pct = 100  # New position
                    
                    # Determine action
                    if prev_shares == 0:
                        action = "NEW"
                    elif change_shares > 0:
                        action = "ADDED"
                    elif change_shares < 0:
                        action = "REDUCED"
                    else:
                        action = "HELD"
                    
                    if action != "HELD":
                        changes.append(InstitutionalChange(
                            institution_name=inst_name,
                            ticker=ticker,
                            prev_shares=prev_shares,
                            curr_shares=curr_shares,
                            change_shares=change_shares,
                            change_pct=change_pct,
                            action=action,
                            value=curr_value,
                        ))
                        print(f"   ✅ Found in {inst_name}: {curr_shares:,} shares")
                
                time.sleep(0.3)  # Rate limiting
                
            except Exception:
                continue
        
        if not changes:
            return None
        
        # Calculate summary
        new_positions = len([c for c in changes if c.action == "NEW"])
        increased = len([c for c in changes if c.action == "ADDED"])
        decreased = len([c for c in changes if c.action == "REDUCED"])
        sold = len([c for c in changes if c.action == "SOLD"])
        
        # Determine signal
        if new_positions >= 2 or (new_positions + increased) >= 3:
            signal = "🟢 Institutions Accumulating"
        elif (decreased + sold) >= 3:
            signal = "🔴 Institutions Exiting"
        elif new_positions > 0 or increased > 0:
            signal = "🟡 Some Institutional Interest"
        else:
            signal = "⚪ Mixed/Neutral"
        
        # Sort by significance (new positions first, then by value)
        changes.sort(key=lambda x: (x.action != "NEW", -x.value))
        
        return InstitutionalSummary(
            ticker=ticker,
            company_name=changes[0].ticker if changes else ticker,
            total_institutions=len(changes),
            new_positions=new_positions,
            increased_positions=increased,
            decreased_positions=decreased,
            sold_positions=sold,
            notable_changes=changes[:10],
            signal=signal,
        )
    
    def format_summary(self, summary: InstitutionalSummary) -> str:
        """Format institutional summary for display."""
        lines = [
            "═" * 50,
            f"🏦 INSTITUTIONAL ACTIVITY: {summary.ticker}",
            "═" * 50,
            "",
            f"Signal: {summary.signal}",
            "",
            f"Notable Institutions ({summary.total_institutions} found):",
            f"  🆕 New positions: {summary.new_positions}",
            f"  📈 Increased: {summary.increased_positions}",
            f"  📉 Decreased: {summary.decreased_positions}",
            f"  ❌ Sold: {summary.sold_positions}",
            "",
        ]
        
        if summary.notable_changes:
            lines.append("Recent Changes:")
            lines.append("─" * 50)
            
            for change in summary.notable_changes[:7]:
                if change.action == "NEW":
                    emoji = "🆕"
                    desc = f"NEW position"
                elif change.action == "ADDED":
                    emoji = "📈"
                    desc = f"+{change.change_pct:.1f}%"
                elif change.action == "REDUCED":
                    emoji = "📉"
                    desc = f"{change.change_pct:.1f}%"
                else:
                    emoji = "❌"
                    desc = "SOLD"
                
                # Value appears to be in actual dollars
                value_m = change.value / 1_000_000
                if value_m >= 1000:
                    value_str = f"${value_m/1000:.1f}B"
                elif value_m >= 1:
                    value_str = f"${value_m:.1f}M"
                else:
                    value_str = f"${change.value/1000:.0f}K"
                
                lines.append(f"  {emoji} {change.institution_name}")
                lines.append(f"     {desc} ({change.curr_shares:,} shares, {value_str})")
                lines.append("")
        
        lines.append("═" * 50)
        lines.append("📅 Data from latest 13F filings (quarterly)")
        lines.append("═" * 50)
        
        return "\n".join(lines)
    
    def quick_check(self, ticker: str) -> None:
        """Quick check of institutional activity for a ticker."""
        print(f"\n🏦 Checking institutional activity for {ticker}...")
        print("   (This checks 10 major funds - takes ~30 seconds)\n")
        
        summary = self.get_institutional_activity(ticker)
        
        if summary:
            print(self.format_summary(summary))
        else:
            print(f"   No institutional activity found for {ticker}")
            print("   This could mean:")
            print("   - Stock not held by major institutions")
            print("   - Small cap not in 13F filings")
            print("   - CUSIP matching issue")


def check_institutions(ticker: str):
    """Quick check of institutional activity for a ticker."""
    tracker = InstitutionalTracker()
    tracker.quick_check(ticker)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        ticker = sys.argv[1].upper()
        check_institutions(ticker)
    else:
        print("Usage: python institutional_tracker.py TICKER")
        print("\nExample: python institutional_tracker.py AAPL")
        print("\nNote: This checks 13F filings from major institutions.")
        print("It takes ~30 seconds to scan notable funds.")

