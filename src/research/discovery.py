"""
Stock Discovery Engine

Find stocks BEFORE they become popular:
- Small/mid caps ($200M - $5B)
- Growing revenue (>15% YoY)
- Low analyst coverage (0-3 analysts)
- Not trending on social media
- Reasonable valuation

This is where the edge is - finding quality companies
that institutions can't buy and retail hasn't found yet.
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass
import time


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
    
    The edge: Finding quality before the crowd.
    """
    
    # Universe to scan - small/mid cap indices and sectors
    # In production, would use full Russell 2000/3000
    SCAN_UNIVERSE = [
        # Small cap tech
        'DOCN', 'NET', 'CFLT', 'MDB', 'GTLB', 'ESTC', 'SUMO', 'DT', 'NEWR', 'PLAN',
        'ZUO', 'APPF', 'TENB', 'ASAN', 'FROG', 'MNDY', 'BRZE', 'AYX', 'PATH', 'AI',
        
        # Small cap healthcare
        'DOCS', 'GDRX', 'CERT', 'TALK', 'HIMS', 'ACCD', 'ALHC', 'OSH', 'RXRX', 'SDGR',
        'VERA', 'PRCT', 'RXDX', 'IMVT', 'ARVN', 'FATE', 'BEAM', 'EDIT', 'NTLA', 'CRSP',
        
        # Small cap consumer
        'DTC', 'PRPL', 'LOVE', 'LESL', 'PLBY', 'RENT', 'BARK', 'CHWY', 'WISH', 'POSH',
        'REAL', 'OPEN', 'RDFN', 'CVNA', 'CARG', 'SFM', 'GO', 'EVGO', 'CHPT', 'BLNK',
        
        # Small cap industrial/other
        'STEM', 'RUN', 'NOVA', 'ARRY', 'MAXN', 'SEDG', 'ENPH', 'FSLR', 'SPWR', 'BE',
        'PLUG', 'BLDP', 'HYLN', 'XL', 'FSR', 'LCID', 'RIVN', 'GOEV', 'PSNY', 'FFIE',
        
        # Recent IPOs / less covered
        'TOST', 'BROS', 'YOU', 'DLO', 'TASK', 'COUR', 'DUOL', 'UPST', 'AFRM', 'SOFI',
        'HOOD', 'COIN', 'RBLX', 'U', 'PLTR', 'SNOW', 'ABNB', 'DASH', 'CPNG', 'GRAB',
        
        # Value small caps
        'PRDO', 'CATO', 'HIBB', 'DBI', 'SCVL', 'CAL', 'GCO', 'BKE', 'TLYS', 'ZUMZ',
        'BOOT', 'SHOO', 'SKX', 'CROX', 'DECK', 'ONON', 'BIRK', 'VFC', 'PVH', 'RL',
    ]
    
    def __init__(self):
        self.discovered: List[DiscoveredStock] = []
    
    def scan_universe(
        self,
        min_market_cap: float = 0.2,  # $200M
        max_market_cap: float = 5.0,   # $5B
        min_revenue_growth: float = 10.0,
        max_analyst_count: int = 5,
        min_score: int = 50,
    ) -> List[DiscoveredStock]:
        """
        Scan for undiscovered stocks meeting criteria.
        
        Args:
            min_market_cap: Minimum market cap in billions
            max_market_cap: Maximum market cap in billions
            min_revenue_growth: Minimum YoY revenue growth %
            max_analyst_count: Maximum number of analysts covering
            min_score: Minimum discovery score (0-100)
        """
        print(f"\n🔍 STOCK DISCOVERY ENGINE")
        print(f"   Scanning {len(self.SCAN_UNIVERSE)} stocks...")
        print(f"   Criteria: ${min_market_cap}B-${max_market_cap}B cap, {min_revenue_growth}%+ growth")
        print()
        
        discovered = []
        
        for i, ticker in enumerate(self.SCAN_UNIVERSE):
            if i % 20 == 0:
                print(f"   Progress: {i}/{len(self.SCAN_UNIVERSE)}...")
            
            try:
                stock = self._analyze_stock(ticker)
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
                print(f"   ✓ Found: {ticker} - {stock.name[:30]} (Score: {stock.score})")
                
            except Exception as e:
                continue
            
            # Rate limiting
            time.sleep(0.3)
        
        # Sort by score
        discovered.sort(key=lambda x: x.score, reverse=True)
        self.discovered = discovered
        
        print(f"\n   Found {len(discovered)} undiscovered opportunities")
        return discovered
    
    def _analyze_stock(self, ticker: str) -> Optional[DiscoveredStock]:
        """Analyze a single stock for discovery potential."""
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # Basic info
            name = info.get('shortName', ticker)
            sector = info.get('sector', 'Unknown')
            industry = info.get('industry', 'Unknown')
            
            # Market cap
            market_cap = info.get('marketCap', 0)
            if market_cap == 0:
                return None
            market_cap_b = market_cap / 1e9
            
            # Price
            price = info.get('currentPrice') or info.get('regularMarketPrice', 0)
            if price == 0:
                return None
            
            # Revenue growth
            revenue_growth = info.get('revenueGrowth', 0) or 0
            revenue_growth_pct = revenue_growth * 100
            
            # Margins
            gross_margin = (info.get('grossMargins', 0) or 0) * 100
            
            # Analyst coverage
            analyst_count = info.get('numberOfAnalystOpinions', 0) or 0
            
            # Valuation
            pe_ratio = info.get('forwardPE') or info.get('trailingPE')
            ps_ratio = info.get('priceToSalesTrailing12Months')
            
            # Ownership
            insider_ownership = (info.get('heldPercentInsiders', 0) or 0) * 100
            short_percent = (info.get('shortPercentOfFloat', 0) or 0) * 100
            
            # Calculate discovery score
            score, reason = self._calculate_score(
                revenue_growth_pct, gross_margin, analyst_count,
                insider_ownership, pe_ratio, ps_ratio, market_cap_b
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
        revenue_growth: float,
        gross_margin: float,
        analyst_count: int,
        insider_ownership: float,
        pe_ratio: Optional[float],
        ps_ratio: Optional[float],
        market_cap: float,
    ) -> tuple[int, str]:
        """Calculate discovery score and reason."""
        score = 0
        reasons = []
        
        # Revenue growth (0-25 points)
        if revenue_growth > 50:
            score += 25
            reasons.append("Hyper growth")
        elif revenue_growth > 30:
            score += 20
            reasons.append("Strong growth")
        elif revenue_growth > 15:
            score += 15
            reasons.append("Good growth")
        elif revenue_growth > 0:
            score += 5
        
        # Low coverage (0-25 points) - KEY for discovery
        if analyst_count == 0:
            score += 25
            reasons.append("Zero coverage")
        elif analyst_count <= 2:
            score += 20
            reasons.append("Minimal coverage")
        elif analyst_count <= 5:
            score += 10
        
        # Gross margin (0-15 points)
        if gross_margin > 70:
            score += 15
            reasons.append("High margins")
        elif gross_margin > 50:
            score += 10
        elif gross_margin > 30:
            score += 5
        
        # Insider ownership (0-15 points)
        if insider_ownership > 20:
            score += 15
            reasons.append("High insider ownership")
        elif insider_ownership > 10:
            score += 10
        elif insider_ownership > 5:
            score += 5
        
        # Valuation (0-10 points)
        if ps_ratio and ps_ratio < 3:
            score += 10
            reasons.append("Cheap on P/S")
        elif ps_ratio and ps_ratio < 5:
            score += 5
        
        # Small cap bonus (0-10 points)
        if market_cap < 1:
            score += 10
            reasons.append("Micro cap")
        elif market_cap < 2:
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


def discover_stocks(
    min_cap: float = 0.2,
    max_cap: float = 5.0,
    min_growth: float = 10.0,
) -> List[DiscoveredStock]:
    """Run stock discovery scan."""
    engine = StockDiscovery()
    stocks = engine.scan_universe(
        min_market_cap=min_cap,
        max_market_cap=max_cap,
        min_revenue_growth=min_growth,
    )
    print(engine.format_discovery_report())
    return stocks


if __name__ == "__main__":
    discover_stocks()

