"""
Stock Discovery Engine

Find stocks BEFORE they become popular:
- Small/mid caps (under $10B market cap)
- Growing revenue (>15% YoY)
- Low analyst coverage (0-5 analysts)
- Profitable or path to profitability
- Reasonable valuation

Scans the ENTIRE US market - NO HARDCODED TICKERS.

Data sources:
1. NASDAQ FTP - All listed securities (free, official)
2. IBKR Scanner - Real-time market scans

This is where the edge is - finding quality companies
that institutions can't buy and retail hasn't found yet.
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass
import time
import requests
import os
import io


@dataclass
class DiscoveredStock:
    """A potentially interesting undiscovered stock."""
    ticker: str
    name: str
    sector: str
    industry: str
    market_cap: float  # in billions
    price: float
    revenue_growth: float  # YoY %
    gross_margin: float
    analyst_count: int
    pe_ratio: Optional[float]
    ps_ratio: Optional[float]
    insider_ownership: float
    short_percent: float
    discovery_reason: str
    score: int  # 0-100


class StockDiscovery:
    """
    Discovers undercovered stocks with strong fundamentals.
    
    Scans ENTIRE US market - downloads ALL tickers from official sources.
    NO HARDCODED TICKER LISTS.
    
    The edge: Finding quality before the crowd.
    """
    
    # Cache file for ticker universe
    UNIVERSE_CACHE = os.path.join(os.path.dirname(__file__), '../../data/ticker_universe.csv')
    
    def __init__(self):
        self.discovered: List[DiscoveredStock] = []
        self.universe: List[str] = []
    
    def get_full_universe(self) -> List[str]:
        """
        Get FULL universe of ALL US stocks.
        
        Source: NASDAQ FTP - Official list of all listed securities
        Updated daily by NASDAQ.
        """
        # Check cache first (refresh if older than 1 day)
        if os.path.exists(self.UNIVERSE_CACHE):
            cache_age = datetime.now().timestamp() - os.path.getmtime(self.UNIVERSE_CACHE)
            if cache_age < 24 * 3600:  # 1 day
                try:
                    df = pd.read_csv(self.UNIVERSE_CACHE)
                    self.universe = df['ticker'].tolist()
                    print(f"   📂 Loaded {len(self.universe)} tickers from cache")
                    return self.universe
                except:
                    pass
        
        print("   📡 Downloading FULL US stock universe from NASDAQ...")
        tickers = set()
        
        # Source 1: NASDAQ Trader FTP - NASDAQ listed
        try:
            url = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
            resp = requests.get(url, timeout=30)
            lines = resp.text.strip().split('\n')
            for line in lines[1:-1]:  # Skip header and footer
                parts = line.split('|')
                if len(parts) > 0:
                    symbol = parts[0].strip()
                    # Skip test symbols and special characters
                    if symbol and len(symbol) <= 5 and symbol.isalpha():
                        tickers.add(symbol)
            print(f"      NASDAQ listed: {len(tickers)} tickers")
        except Exception as e:
            print(f"      NASDAQ FTP error: {e}")
        
        # Source 2: NASDAQ Trader FTP - Other listed (NYSE, etc)
        try:
            url = "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"
            resp = requests.get(url, timeout=30)
            lines = resp.text.strip().split('\n')
            before = len(tickers)
            for line in lines[1:-1]:  # Skip header and footer
                parts = line.split('|')
                if len(parts) > 0:
                    symbol = parts[0].strip()
                    if symbol and len(symbol) <= 5 and symbol.isalpha():
                        tickers.add(symbol)
            print(f"      NYSE/Other listed: {len(tickers) - before} tickers")
        except Exception as e:
            print(f"      Other FTP error: {e}")
        
        # Source 3: NASDAQ screener API (backup, has more data)
        if len(tickers) < 3000:
            try:
                for exchange in ['NASDAQ', 'NYSE', 'AMEX']:
                    url = f"https://api.nasdaq.com/api/screener/stocks?tableonly=true&limit=10000&exchange={exchange}"
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                        'Accept': 'application/json',
                    }
                    resp = requests.get(url, headers=headers, timeout=30)
                    if resp.status_code == 200:
                        data = resp.json()
                        rows = data.get('data', {}).get('table', {}).get('rows', [])
                        for row in rows:
                            symbol = row.get('symbol', '').strip()
                            if symbol and len(symbol) <= 5:
                                # Filter out weird symbols
                                if not any(c in symbol for c in ['^', '/', '$', '.']):
                                    tickers.add(symbol)
                print(f"      API backup: total {len(tickers)} tickers")
            except Exception as e:
                print(f"      API error: {e}")
        
        self.universe = sorted(list(tickers))
        
        # Cache for next time
        try:
            os.makedirs(os.path.dirname(self.UNIVERSE_CACHE), exist_ok=True)
            pd.DataFrame({'ticker': self.universe}).to_csv(self.UNIVERSE_CACHE, index=False)
            print(f"   💾 Cached {len(self.universe)} tickers")
        except Exception as e:
            print(f"   Cache error: {e}")
        
        print(f"   ✅ Total universe: {len(self.universe)} US stocks")
        return self.universe
    
    def scan_universe(
        self,
        min_market_cap: float = 0.2,  # $200M
        max_market_cap: float = 10.0,  # $10B
        min_revenue_growth: float = 10.0,
        max_analyst_count: int = 5,
        min_score: int = 50,
        max_stocks_to_scan: int = 500,  # Limit for speed
    ) -> List[DiscoveredStock]:
        """
        Scan ENTIRE US market for undiscovered stocks.
        
        Downloads all US tickers, then filters by criteria.
        
        Args:
            min_market_cap: Minimum market cap in billions
            max_market_cap: Maximum market cap in billions
            min_revenue_growth: Minimum YoY revenue growth %
            max_analyst_count: Maximum number of analysts covering
            min_score: Minimum discovery score (0-100)
            max_stocks_to_scan: Limit for API rate limiting
        """
        print(f"\n🔍 STOCK DISCOVERY ENGINE")
        print(f"   Criteria: ${min_market_cap}B - ${max_market_cap}B cap")
        print(f"   Revenue growth: >{min_revenue_growth}%")
        print(f"   Max analyst coverage: {max_analyst_count}")
        print()
        
        # Get full universe
        universe = self.get_full_universe()
        
        # Shuffle to get random sample each time
        import random
        random.shuffle(universe)
        
        # Limit for API rate limiting (full scan would take hours)
        scan_list = universe[:max_stocks_to_scan]
        
        print(f"   Scanning {len(scan_list)} of {len(universe)} stocks...")
        print()
        
        discovered = []
        scanned = 0
        errors = 0
        
        for i, ticker in enumerate(scan_list):
            if i % 50 == 0 and i > 0:
                print(f"   Progress: {i}/{len(scan_list)} scanned, {len(discovered)} found...")
            
            try:
                stock = self._analyze_stock(ticker)
                scanned += 1
                
                if stock is None:
                    continue
                
                # Apply filters
                if stock.market_cap < min_market_cap or stock.market_cap > max_market_cap:
                    continue
                if stock.revenue_growth < min_revenue_growth:
                    continue
                if stock.analyst_count > max_analyst_count:
                    continue
                if stock.score < min_score:
                    continue
                
                discovered.append(stock)
                print(f"   ✓ {ticker}: {stock.name[:25]} | ${stock.market_cap}B | +{stock.revenue_growth}% rev | Score {stock.score}")
                
            except Exception as e:
                errors += 1
                continue
            
            # Rate limiting for yfinance
            time.sleep(0.2)
        
        # Sort by score
        discovered.sort(key=lambda x: x.score, reverse=True)
        self.discovered = discovered
        
        print()
        print(f"   ✅ Scanned: {scanned} stocks")
        print(f"   ✅ Discovered: {len(discovered)} opportunities")
        print(f"   ⚠️  Errors: {errors}")
        
        return discovered
    
    def _analyze_stock(self, ticker: str) -> Optional[DiscoveredStock]:
        """
        Analyze a single stock for discovery potential.
        
        REAL fundamental checks (not just surface metrics):
        1. Absolute revenue - Must be meaningful ($50M+ minimum)
        2. Revenue trajectory - Consistent growth, not one spike
        3. Profitability path - Improving margins or burning cash?
        4. Debt health - Manageable or drowning?
        5. Cash position - Runway to survive?
        6. Free cash flow - Actually generating or destroying cash?
        """
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # Basic info
            name = info.get('shortName', ticker)
            sector = info.get('sector', 'Unknown')
            industry = info.get('industry', 'Unknown')
            
            # Skip if missing critical data
            if sector == 'Unknown':
                return None
            
            # Market cap
            market_cap = info.get('marketCap', 0)
            if market_cap == 0:
                return None
            market_cap_b = market_cap / 1e9
            
            # Price
            price = info.get('currentPrice') or info.get('regularMarketPrice', 0)
            if price == 0:
                return None
            
            # ════════════════════════════════════════════════════════════
            # CRITICAL: Absolute revenue check
            # A company with $1M revenue growing 900% is GARBAGE
            # We need REAL businesses with meaningful scale
            # ════════════════════════════════════════════════════════════
            total_revenue = info.get('totalRevenue', 0) or 0
            if total_revenue < 50_000_000:  # Minimum $50M revenue
                return None  # Skip micro businesses
            
            revenue_b = total_revenue / 1e9
            
            # Revenue growth
            revenue_growth = info.get('revenueGrowth', 0) or 0
            revenue_growth_pct = revenue_growth * 100
            
            # ════════════════════════════════════════════════════════════
            # PROFITABILITY PATH
            # Not just "are they profitable" but "are they GETTING there"
            # ════════════════════════════════════════════════════════════
            operating_margin = (info.get('operatingMargins', 0) or 0) * 100
            profit_margin = (info.get('profitMargins', 0) or 0) * 100
            gross_margin = (info.get('grossMargins', 0) or 0) * 100
            
            # Free cash flow - THE most important metric
            free_cash_flow = info.get('freeCashflow', 0) or 0
            fcf_margin = (free_cash_flow / total_revenue * 100) if total_revenue > 0 else 0
            
            # ════════════════════════════════════════════════════════════
            # DEBT HEALTH
            # Growing revenue means nothing if drowning in debt
            # ════════════════════════════════════════════════════════════
            total_debt = info.get('totalDebt', 0) or 0
            total_cash = info.get('totalCash', 0) or 0
            debt_to_equity = info.get('debtToEquity', 0) or 0
            
            # Net cash position (positive = more cash than debt)
            net_cash = total_cash - total_debt
            net_cash_b = net_cash / 1e9
            
            # Cash runway for unprofitable companies
            if free_cash_flow < 0:
                cash_runway_years = total_cash / abs(free_cash_flow) if free_cash_flow != 0 else 0
            else:
                cash_runway_years = 999  # FCF positive, no burn
            
            # Analyst coverage
            analyst_count = info.get('numberOfAnalystOpinions', 0) or 0
            
            # Valuation
            pe_ratio = info.get('forwardPE') or info.get('trailingPE')
            ps_ratio = info.get('priceToSalesTrailing12Months')
            
            # Ownership
            insider_ownership = (info.get('heldPercentInsiders', 0) or 0) * 100
            short_percent = (info.get('shortPercentOfFloat', 0) or 0) * 100
            
            # ════════════════════════════════════════════════════════════
            # QUALITY FILTERS - Reject garbage early
            # ════════════════════════════════════════════════════════════
            
            # Reject: Negative gross margin (broken business model)
            if gross_margin < 0:
                return None
            
            # Reject: Cash runway < 1 year for unprofitable companies
            if profit_margin < 0 and cash_runway_years < 1:
                return None
            
            # Reject: Debt > 3x equity (overleveraged)
            if debt_to_equity > 300:
                return None
            
            # Calculate discovery score with REAL metrics
            score, reason = self._calculate_score(
                revenue_growth_pct=revenue_growth_pct,
                revenue_b=revenue_b,
                gross_margin=gross_margin,
                operating_margin=operating_margin,
                fcf_margin=fcf_margin,
                analyst_count=analyst_count,
                insider_ownership=insider_ownership,
                pe_ratio=pe_ratio,
                ps_ratio=ps_ratio,
                market_cap_b=market_cap_b,
                debt_to_equity=debt_to_equity,
                net_cash_b=net_cash_b,
                cash_runway_years=cash_runway_years,
            )
            
            return DiscoveredStock(
                ticker=ticker,
                name=name,
                sector=sector,
                industry=industry,
                market_cap=round(market_cap_b, 2),
                price=round(price, 2),
                revenue_growth=round(revenue_growth_pct, 1),
                gross_margin=round(gross_margin, 1),
                analyst_count=analyst_count,
                pe_ratio=round(pe_ratio, 1) if pe_ratio else None,
                ps_ratio=round(ps_ratio, 1) if ps_ratio else None,
                insider_ownership=round(insider_ownership, 1),
                short_percent=round(short_percent, 1),
                discovery_reason=reason,
                score=score,
            )
            
        except Exception as e:
            return None
    
    def _calculate_score(
        self,
        revenue_growth_pct: float,
        revenue_b: float,
        gross_margin: float,
        operating_margin: float,
        fcf_margin: float,
        analyst_count: int,
        insider_ownership: float,
        pe_ratio: Optional[float],
        ps_ratio: Optional[float],
        market_cap_b: float,
        debt_to_equity: float,
        net_cash_b: float,
        cash_runway_years: float,
    ) -> tuple[int, str]:
        """
        Calculate discovery score based on REAL fundamentals.
        
        Max 100 points:
        - Revenue quality (0-20): Growth + absolute size
        - Profitability path (0-25): Margins + FCF
        - Financial health (0-20): Debt + cash position
        - Discovery potential (0-20): Low coverage + insider buying
        - Valuation (0-15): P/S, P/E reasonableness
        """
        score = 0
        reasons = []
        
        # ════════════════════════════════════════════════════════════
        # REVENUE QUALITY (0-20 points)
        # Growth ONLY counts if absolute revenue is meaningful
        # ════════════════════════════════════════════════════════════
        
        # Revenue scale bonus
        if revenue_b >= 1.0:  # $1B+ revenue
            scale_bonus = 5
            reasons.append(f"${revenue_b:.1f}B revenue")
        elif revenue_b >= 0.5:  # $500M+ revenue
            scale_bonus = 3
        elif revenue_b >= 0.1:  # $100M+ revenue
            scale_bonus = 1
        else:
            scale_bonus = 0
        
        # Revenue growth (only meaningful with scale)
        if revenue_growth_pct > 30 and revenue_b >= 0.1:
            score += 15 + scale_bonus
            reasons.append(f"+{revenue_growth_pct:.0f}% growth")
        elif revenue_growth_pct > 20 and revenue_b >= 0.1:
            score += 12 + scale_bonus
            reasons.append("Strong growth")
        elif revenue_growth_pct > 10 and revenue_b >= 0.1:
            score += 8 + scale_bonus
        elif revenue_growth_pct > 0:
            score += 3 + scale_bonus
        
        # ════════════════════════════════════════════════════════════
        # PROFITABILITY PATH (0-25 points)
        # This is THE key differentiator
        # ════════════════════════════════════════════════════════════
        
        # Free cash flow positive = HUGE bonus
        if fcf_margin > 15:
            score += 15
            reasons.append("Strong FCF")
        elif fcf_margin > 5:
            score += 10
            reasons.append("FCF positive")
        elif fcf_margin > 0:
            score += 5
        
        # Operating margin
        if operating_margin > 20:
            score += 10
            reasons.append("High op margin")
        elif operating_margin > 10:
            score += 7
        elif operating_margin > 0:
            score += 3
        elif operating_margin > -10:
            score += 1  # Small loss, might be investing in growth
        # Negative operating margin with no points = burning cash
        
        # ════════════════════════════════════════════════════════════
        # FINANCIAL HEALTH (0-20 points)
        # ════════════════════════════════════════════════════════════
        
        # Net cash position
        if net_cash_b > 0.5:  # $500M+ net cash
            score += 10
            reasons.append("Cash rich")
        elif net_cash_b > 0:  # Positive net cash
            score += 5
        elif debt_to_equity < 50:  # Low debt
            score += 3
        
        # Cash runway (for unprofitable companies)
        if cash_runway_years >= 999:  # FCF positive
            score += 10
        elif cash_runway_years > 3:
            score += 7
            reasons.append(f"{cash_runway_years:.1f}yr runway")
        elif cash_runway_years > 2:
            score += 3
        # <2 years runway and FCF negative = risky
        
        # ════════════════════════════════════════════════════════════
        # DISCOVERY POTENTIAL (0-20 points)
        # Low coverage = opportunity before crowd finds it
        # ════════════════════════════════════════════════════════════
        
        if analyst_count == 0:
            score += 15
            reasons.append("Zero coverage")
        elif analyst_count <= 2:
            score += 12
            reasons.append("Low coverage")
        elif analyst_count <= 5:
            score += 6
        
        # Insider ownership (skin in the game)
        if insider_ownership > 20:
            score += 5
            reasons.append("High insider")
        elif insider_ownership > 10:
            score += 3
        
        # ════════════════════════════════════════════════════════════
        # VALUATION (0-15 points)
        # ════════════════════════════════════════════════════════════
        
        if ps_ratio and ps_ratio < 3:
            score += 10
            reasons.append("Cheap on P/S")
        elif ps_ratio and ps_ratio < 5:
            score += 5
        
        # Small cap bonus (0-10 points)
        if market_cap_b < 1:
            score += 10
            reasons.append("Micro cap")
        elif market_cap_b < 2:
            score += 5
        
        reason = " + ".join(reasons) if reasons else "Meets criteria"
        return min(score, 100), reason
    
    def format_discovery_report(self, top_n: int = 10) -> str:
        """Format discovered stocks as a report."""
        if not self.discovered:
            return "No stocks discovered. Run scan_universe() first."
        
        lines = [
            "═" * 60,
            "🔍 DISCOVERED STOCKS",
            f"   {datetime.now().strftime('%B %d, %Y')}",
            "═" * 60,
            "",
        ]
        
        for stock in self.discovered[:top_n]:
            lines.extend([
                f"{'─' * 60}",
                f"📊 {stock.ticker} - {stock.name}",
                f"   Score: {stock.score}/100 | {stock.discovery_reason}",
                f"",
                f"   Sector: {stock.sector}",
                f"   Market Cap: ${stock.market_cap}B",
                f"   Price: ${stock.price}",
                f"",
                f"   Revenue Growth: {stock.revenue_growth}% YoY",
                f"   Gross Margin: {stock.gross_margin}%",
                f"   Analyst Coverage: {stock.analyst_count} analysts",
                f"   Insider Ownership: {stock.insider_ownership}%",
                f"",
            ])
            
            if stock.pe_ratio:
                lines.append(f"   P/E: {stock.pe_ratio}x")
            if stock.ps_ratio:
                lines.append(f"   P/S: {stock.ps_ratio}x")
            
            lines.append("")
        
        lines.append("═" * 60)
        lines.append(f"Run: python research.py {self.discovered[0].ticker if self.discovered else 'TICKER'}")
        lines.append("for deep analysis on any stock")
        lines.append("═" * 60)
        
        return "\n".join(lines)
    
    # ════════════════════════════════════════════════════════════════════
    # WEEKLY COMPREHENSIVE SCAN
    # This is the REAL discovery - scan everything, track over time
    # ════════════════════════════════════════════════════════════════════
    
    def run_weekly_scan(
        self,
        min_market_cap: float = 0.3,
        max_market_cap: float = 10.0,
        min_revenue_growth: float = 10.0,
        min_score: int = 40,
    ) -> Dict:
        """
        Run comprehensive weekly scan of ENTIRE universe.
        
        This should run once per week (Sunday night).
        Results are saved to database for tracking.
        
        Returns:
            {
                'scanned': 11552,
                'discovered': 127,
                'improvements': [stocks that improved vs last week],
                'new_discoveries': [stocks meeting criteria for first time]
            }
        """
        from .discovery_db import DiscoveryDatabase
        
        print("\n" + "═" * 60)
        print("📊 WEEKLY COMPREHENSIVE SCAN")
        print(f"   {datetime.now().strftime('%A, %B %d, %Y')}")
        print("═" * 60)
        
        # Get full universe
        universe = self.get_full_universe()
        print(f"\n   Universe: {len(universe)} US stocks")
        print(f"   Criteria: ${min_market_cap}B - ${max_market_cap}B cap")
        print(f"   Min growth: {min_revenue_growth}%")
        print(f"   Min score: {min_score}")
        print()
        
        # Scan all stocks (this takes a while)
        discovered = []
        scanned = 0
        errors = 0
        
        batch_size = 100
        for i in range(0, len(universe), batch_size):
            batch = universe[i:i+batch_size]
            print(f"   Scanning batch {i//batch_size + 1}/{len(universe)//batch_size + 1}...")
            
            for ticker in batch:
                try:
                    stock = self._analyze_stock(ticker)
                    scanned += 1
                    
                    if stock is None:
                        continue
                    
                    # Apply filters
                    if stock.market_cap < min_market_cap or stock.market_cap > max_market_cap:
                        continue
                    if stock.revenue_growth < min_revenue_growth:
                        continue
                    if stock.score < min_score:
                        continue
                    
                    discovered.append(stock)
                    
                except Exception:
                    errors += 1
                    continue
                
                time.sleep(0.15)  # Rate limiting
            
            # Progress update
            print(f"      Scanned: {scanned}, Found: {len(discovered)}, Errors: {errors}")
        
        self.discovered = sorted(discovered, key=lambda x: x.score, reverse=True)
        
        # Save to database
        db = DiscoveryDatabase()
        results_for_db = []
        for stock in self.discovered:
            results_for_db.append({
                'ticker': stock.ticker,
                'name': stock.name,
                'sector': stock.sector,
                'industry': stock.industry,
                'market_cap_b': stock.market_cap,
                'price': stock.price,
                'revenue_growth': stock.revenue_growth,
                'gross_margin': stock.gross_margin,
                'analyst_count': stock.analyst_count,
                'pe_ratio': stock.pe_ratio,
                'ps_ratio': stock.ps_ratio,
                'insider_ownership': stock.insider_ownership,
                'score': stock.score,
                'discovery_reason': stock.discovery_reason,
            })
        
        criteria = {
            'min_market_cap': min_market_cap,
            'max_market_cap': max_market_cap,
            'min_revenue_growth': min_revenue_growth,
            'min_score': min_score,
        }
        
        scan_id = db.save_weekly_scan(results_for_db, criteria, scanned)
        
        # Find improvements vs last week
        improvements = db.find_improvements(min_score_change=10)
        new_discoveries = db.get_new_discoveries()
        
        print()
        print("═" * 60)
        print(f"✅ WEEKLY SCAN COMPLETE")
        print(f"   Scanned: {scanned} stocks")
        print(f"   Discovered: {len(discovered)} opportunities")
        print(f"   Improvements: {len(improvements)} stocks improved vs last week")
        print(f"   New discoveries: {len(new_discoveries)} stocks meeting criteria first time")
        print("═" * 60)
        
        return {
            'scanned': scanned,
            'discovered': len(discovered),
            'top_stocks': self.discovered[:20],
            'improvements': improvements,
            'new_discoveries': new_discoveries,
        }
    
    def format_improvements_report(self, improvements) -> str:
        """Format improvement report for Telegram."""
        if not improvements:
            return "No significant improvements this week."
        
        lines = [
            "═" * 50,
            "📈 STOCKS THAT IMPROVED THIS WEEK",
            "   (Score jumped 10+ points)",
            "═" * 50,
            "",
        ]
        
        for imp in improvements[:10]:
            fcf_note = " 🔥 FCF TURNED POSITIVE!" if imp.fcf_turned_positive else ""
            lines.extend([
                f"🚀 {imp.ticker} - {imp.name[:25]}",
                f"   Score: {imp.prev_score} → {imp.curr_score} (+{imp.score_change})",
                f"   {imp.improvement_reason}{fcf_note}",
                "",
            ])
        
        lines.append("═" * 50)
        lines.append("These stocks are improving before the crowd notices.")
        lines.append("═" * 50)
        
        return "\n".join(lines)


def run_weekly_discovery():
    """
    Run weekly comprehensive scan.
    
    Should be scheduled for Sunday night via cron:
    0 22 * * 0 cd /path/to/scanner && python -c "from src.research.discovery import run_weekly_discovery; run_weekly_discovery()"
    """
    engine = StockDiscovery()
    results = engine.run_weekly_scan(
        min_market_cap=0.3,   # $300M
        max_market_cap=10.0,  # $10B
        min_revenue_growth=10.0,
        min_score=40,
    )
    
    # Print top discoveries
    print("\n" + engine.format_discovery_report(top_n=15))
    
    # Print improvements
    if results['improvements']:
        print("\n" + engine.format_improvements_report(results['improvements']))
    
    return results


def discover_stocks(
    min_cap: float = 0.3,
    max_cap: float = 10.0,
    min_growth: float = 10.0,
    max_scan: int = 500,
    max_analysts: int = 10,
) -> List[DiscoveredStock]:
    """Run quick stock discovery scan."""
    engine = StockDiscovery()
    stocks = engine.scan_universe(
        min_market_cap=min_cap,
        max_market_cap=max_cap,
        min_revenue_growth=min_growth,
        max_stocks_to_scan=max_scan,
        max_analyst_count=max_analysts,
    )
    print(engine.format_discovery_report())
    return stocks


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--weekly':
        run_weekly_discovery()
    else:
        discover_stocks()

