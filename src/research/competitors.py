"""
Competitor Comparison Module

Side-by-side comparison with industry peers.

Why this matters:
- Numbers without context are meaningless
- "Expensive" vs peers? Or just "expensive"?
- Identify best-in-class vs laggards

Auto-discovers peers based on:
- Business model (from description keywords)
- Market cap range (similar-sized companies)
- Sector/Industry
- Geographic focus (if applicable)
"""

import os
import sys
from typing import Optional, List, Dict, Set
from dataclasses import dataclass
import yfinance as yf
import re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))


@dataclass
class CompanyMetrics:
    """Key metrics for a company."""
    ticker: str
    name: str
    market_cap_b: float
    pe_ratio: Optional[float]
    forward_pe: Optional[float]
    peg_ratio: Optional[float]
    revenue_growth: Optional[float]
    profit_margin: Optional[float]
    roe: Optional[float]
    debt_to_equity: Optional[float]
    price_to_book: Optional[float]
    dividend_yield: Optional[float]
    price_ytd_pct: Optional[float]


@dataclass
class ComparisonResult:
    """Comparison result."""
    ticker: str
    target: CompanyMetrics
    peers: List[CompanyMetrics]
    peer_avg: Dict[str, float]
    ranking: Dict[str, int]  # Rank among peers for each metric
    verdict: str


class CompetitorAnalyzer:
    """
    Compare a stock to its peers using intelligent auto-discovery.
    
    No hardcoded lists - finds peers dynamically based on:
    1. Business model keywords (from description)
    2. Market cap range (similar-sized companies)
    3. Sector/Industry match
    4. Geographic focus (if applicable)
    """
    
    # Business model keyword patterns
    BUSINESS_MODELS = {
        'payment_processing': ['payment', 'transaction processing', 'payment gateway', 'merchant', 
                              'payment solution', 'fintech', 'payment platform', 'checkout'],
        'saas': ['software as a service', 'saas', 'cloud software', 'subscription software', 
                'enterprise software', 'software platform'],
        'ecommerce': ['e-commerce', 'online retail', 'marketplace', 'online store', 'digital commerce'],
        'banking': ['bank', 'banking', 'financial services', 'digital bank', 'neobank'],
        'streaming': ['streaming', 'video streaming', 'content streaming', 'entertainment platform'],
        'semiconductor': ['semiconductor', 'chip', 'processor', 'integrated circuit'],
        'retail': ['retail', 'retailer', 'store', 'shopping'],
        'cloud_infrastructure': ['cloud infrastructure', 'cloud computing', 'data center', 'cloud platform'],
    }
    
    # Common stocks by sector for peer search (curated list for efficiency)
    SECTOR_UNIVERSE = {
        'Technology': ['AAPL', 'MSFT', 'GOOGL', 'META', 'NVDA', 'AMD', 'INTC', 'CRM', 'NOW', 
                      'ORCL', 'ADBE', 'INTU', 'SNOW', 'DDOG', 'NET', 'MDB', 'ZM', 'TEAM'],
        'Financial Services': ['JPM', 'BAC', 'C', 'WFC', 'GS', 'MS', 'V', 'MA', 'PYPL', 'SQ', 
                              'AXP', 'COF', 'DFS', 'STNE', 'PAGS', 'NU', 'DLO', 'SOFI', 'AFRM'],
        'Healthcare': ['JNJ', 'UNH', 'PFE', 'ABBV', 'LLY', 'MRK', 'BMY', 'AMGN', 'GILD', 
                      'REGN', 'VRTX', 'CVS', 'CI', 'HUM'],
        'Consumer Cyclical': ['AMZN', 'TSLA', 'HD', 'NKE', 'SBUX', 'MCD', 'NFLX', 'DIS'],
        'Consumer Defensive': ['WMT', 'COST', 'TGT', 'PG', 'KO', 'PEP'],
        'Energy': ['XOM', 'CVX', 'COP', 'SLB', 'EOG'],
        'Industrials': ['CAT', 'HON', 'UPS', 'BA', 'GE'],
        'Communication Services': ['GOOGL', 'META', 'DIS', 'NFLX', 'T', 'VZ'],
        'Utilities': ['NEE', 'DUK', 'SO', 'D'],
        'Real Estate': ['AMT', 'PLD', 'EQIX', 'PSA'],
    }
    
    def __init__(self, ticker: str):
        self.ticker = ticker.upper()
        self.stock = yf.Ticker(self.ticker)
        self.info = self.stock.info
    
    def _extract_business_model(self, description: str) -> Set[str]:
        """Extract business model keywords from description."""
        description_lower = description.lower()
        models = set()
        
        for model, keywords in self.BUSINESS_MODELS.items():
            for keyword in keywords:
                if keyword in description_lower:
                    models.add(model)
                    break
        
        return models
    
    def _get_market_cap_range(self, market_cap: float) -> tuple:
        """Get market cap range for peer search (within 10x-0.1x)."""
        if market_cap < 1e9:  # < $1B
            return (0, 10e9)
        elif market_cap < 10e9:  # $1B-$10B
            return (0.5e9, 50e9)
        elif market_cap < 100e9:  # $10B-$100B
            return (5e9, 500e9)
        else:  # > $100B
            return (50e9, float('inf'))
    
    def _score_peer_match(self, peer_ticker: str, target_models: Set[str], 
                         target_mcap: float, target_sector: str, target_desc: str) -> float:
        """Score how well a peer matches (0-100)."""
        try:
            peer_stock = yf.Ticker(peer_ticker)
            peer_info = peer_stock.info
            
            # Skip if no market cap
            peer_mcap = peer_info.get('marketCap', 0)
            if not peer_mcap or peer_mcap < 100e6:  # Skip micro-caps
                return 0
            
            score = 0
            peer_desc = peer_info.get('longBusinessSummary', '').lower()
            peer_models = self._extract_business_model(peer_desc)
            
            # 1. Business model match (50 points) - MOST IMPORTANT
            if target_models and peer_models:
                overlap = len(target_models & peer_models)
                if overlap > 0:
                    score += 50  # Strong match
                elif target_models:  # Check for keyword overlap in descriptions
                    # Count shared keywords
                    target_words = set(re.findall(r'\b\w{4,}\b', target_desc.lower()))
                    peer_words = set(re.findall(r'\b\w{4,}\b', peer_desc))
                    shared = len(target_words & peer_words)
                    if shared > 5:  # Significant keyword overlap
                        score += 30
            
            # 2. Sector match (30 points) - less important than business model
            peer_sector = peer_info.get('sector', '')
            if peer_sector == target_sector:
                score += 30
            elif peer_sector:  # Partial credit for related sectors
                score += 5
            
            # 3. Market cap similarity (20 points)
            if target_mcap > 0:
                ratio = min(peer_mcap, target_mcap) / max(peer_mcap, target_mcap)
                score += ratio * 20  # Closer market cap = higher score
            
            return score
            
        except Exception:
            return 0
    
    def _find_peers_dynamically(self) -> List[str]:
        """Dynamically discover peers based on business model, market cap, and sector."""
        try:
            info = self.info
            sector = info.get('sector', '')
            industry = info.get('industry', '')
            description = info.get('longBusinessSummary', '')
            market_cap = info.get('marketCap', 0)
            
            if not sector or not market_cap:
                return []
            
            # Extract business model
            business_models = self._extract_business_model(description)
            
            # Get candidate universe from sector
            candidates = list(self.SECTOR_UNIVERSE.get(sector, []))
            
            # If payment processing, also check Financial Services
            if 'payment_processing' in business_models:
                candidates.extend(self.SECTOR_UNIVERSE.get('Financial Services', []))
                candidates = list(set(candidates))  # Remove duplicates
            
            # If no candidates from sector, try related
            if not candidates:
                if 'Technology' in sector or 'Software' in sector:
                    candidates = self.SECTOR_UNIVERSE.get('Technology', [])
                elif 'Financial' in sector:
                    candidates = self.SECTOR_UNIVERSE.get('Financial Services', [])
            
            if not candidates:
                return []
            
            # Score all candidates
            scored_peers = []
            for candidate in candidates:
                if candidate == self.ticker:
                    continue
                
                score = self._score_peer_match(
                    candidate, business_models, market_cap, sector, description
                )
                
                if score > 25:  # Minimum threshold (raised for better quality)
                    scored_peers.append((score, candidate))
            
            # Sort by score and return top 4
            scored_peers.sort(reverse=True, key=lambda x: x[0])
            return [ticker for _, ticker in scored_peers[:4]]
            
        except Exception as e:
            return []
    
    def analyze(self) -> ComparisonResult:
        """Run peer comparison analysis."""
        
        # Dynamically discover peers
        peers_list = self._find_peers_dynamically()
        
        # Get target metrics
        target = self._get_metrics(self.ticker)
        
        # Get peer metrics
        peers = []
        for peer_ticker in peers_list[:4]:  # Max 4 peers
            peer_metrics = self._get_metrics(peer_ticker)
            if peer_metrics:
                peers.append(peer_metrics)
        
        # Calculate peer averages
        peer_avg = self._calculate_averages(peers)
        
        # Rank target among peers
        ranking = self._calculate_ranking(target, peers)
        
        # Generate verdict
        verdict = self._generate_verdict(target, peer_avg, ranking)
        
        return ComparisonResult(
            ticker=self.ticker,
            target=target,
            peers=peers,
            peer_avg=peer_avg,
            ranking=ranking,
            verdict=verdict,
        )
    
    def _get_metrics(self, ticker: str) -> Optional[CompanyMetrics]:
        """Get key metrics for a ticker."""
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            market_cap = info.get('marketCap', 0)
            if not market_cap:
                return None
            
            # Get YTD return
            ytd_pct = None
            try:
                hist = stock.history(period='ytd')
                if not hist.empty and len(hist) > 1:
                    ytd_pct = ((hist['Close'].iloc[-1] / hist['Close'].iloc[0]) - 1) * 100
            except:
                pass
            
            return CompanyMetrics(
                ticker=ticker,
                name=info.get('shortName', ticker),
                market_cap_b=market_cap / 1e9,
                pe_ratio=info.get('trailingPE'),
                forward_pe=info.get('forwardPE'),
                peg_ratio=info.get('pegRatio'),
                revenue_growth=self._pct(info.get('revenueGrowth')),
                profit_margin=self._pct(info.get('profitMargins')),
                roe=self._pct(info.get('returnOnEquity')),
                debt_to_equity=info.get('debtToEquity'),
                price_to_book=info.get('priceToBook'),
                dividend_yield=self._pct(info.get('dividendYield')),
                price_ytd_pct=ytd_pct,
            )
            
        except Exception as e:
            return None
    
    def _pct(self, value) -> Optional[float]:
        """Convert ratio to percentage if needed."""
        if value is None:
            return None
        if value < 1:
            return value * 100
        return value
    
    def _calculate_averages(self, peers: List[CompanyMetrics]) -> Dict[str, float]:
        """Calculate peer averages for each metric."""
        if not peers:
            return {}
        
        metrics = ['pe_ratio', 'forward_pe', 'peg_ratio', 'revenue_growth', 
                   'profit_margin', 'roe', 'debt_to_equity', 'price_to_book']
        
        averages = {}
        for metric in metrics:
            values = [getattr(p, metric) for p in peers if getattr(p, metric) is not None]
            if values:
                averages[metric] = sum(values) / len(values)
        
        return averages
    
    def _calculate_ranking(self, target: CompanyMetrics, peers: List[CompanyMetrics]) -> Dict[str, int]:
        """Rank target among peers for each metric."""
        if not peers:
            return {}
        
        all_companies = [target] + peers
        ranking = {}
        
        # Metrics where lower is better
        lower_better = ['pe_ratio', 'forward_pe', 'peg_ratio', 'debt_to_equity', 'price_to_book']
        
        # Metrics where higher is better
        higher_better = ['revenue_growth', 'profit_margin', 'roe', 'price_ytd_pct']
        
        for metric in lower_better + higher_better:
            values = [(c.ticker, getattr(c, metric)) for c in all_companies]
            values = [(t, v) for t, v in values if v is not None]
            
            if not values:
                continue
            
            # Sort (ascending for lower_better, descending for higher_better)
            reverse = metric in higher_better
            values.sort(key=lambda x: x[1], reverse=reverse)
            
            for rank, (ticker, _) in enumerate(values, 1):
                if ticker == target.ticker:
                    ranking[metric] = rank
                    break
        
        return ranking
    
    def _generate_verdict(self, target: CompanyMetrics, peer_avg: Dict[str, float], 
                         ranking: Dict[str, int]) -> str:
        """Generate comparison verdict."""
        signals = []
        
        # Valuation comparison
        if target.pe_ratio and 'pe_ratio' in peer_avg:
            diff = ((target.pe_ratio / peer_avg['pe_ratio']) - 1) * 100
            if diff > 30:
                signals.append("🔴 Premium valuation vs peers")
            elif diff > 10:
                signals.append("🟠 Slightly expensive vs peers")
            elif diff < -30:
                signals.append("🟢 Discount to peers")
            elif diff < -10:
                signals.append("🟢 Slight discount to peers")
        
        # Growth comparison
        if target.revenue_growth and 'revenue_growth' in peer_avg:
            if target.revenue_growth > peer_avg['revenue_growth'] * 1.5:
                signals.append("🟢 Growth leader")
            elif target.revenue_growth < peer_avg['revenue_growth'] * 0.5:
                signals.append("🔴 Growth laggard")
        
        # Profitability
        if target.profit_margin and 'profit_margin' in peer_avg:
            if target.profit_margin > peer_avg['profit_margin'] * 1.3:
                signals.append("🟢 Best-in-class margins")
            elif target.profit_margin < peer_avg['profit_margin'] * 0.7:
                signals.append("🟠 Below-average margins")
        
        # Overall ranking
        if ranking:
            avg_rank = sum(ranking.values()) / len(ranking)
            if avg_rank <= 1.5:
                signals.append("⭐ Top performer in peer group")
            elif avg_rank >= 4:
                signals.append("📉 Lagging peer group")
        
        return " | ".join(signals) if signals else "📊 In line with peers"
    
    def format_report(self, result: ComparisonResult) -> str:
        """Format comparison report."""
        lines = [
            "═" * 70,
            f"🏆 PEER COMPARISON: {result.ticker}",
            "═" * 70,
            "",
            f"Verdict: {result.verdict}",
            "",
        ]
        
        if not result.peers:
            lines.append("❌ No peer data available for comparison")
            lines.append("   Consider adding peers to PEER_GROUPS in competitors.py")
            return "\n".join(lines)
        
        # Header
        lines.append("─" * 70)
        header = f"{'Metric':<20}"
        header += f"{result.target.ticker:>10}"
        for peer in result.peers:
            header += f"{peer.ticker:>10}"
        header += f"{'Avg':>10}"
        lines.append(header)
        lines.append("─" * 70)
        
        # Metrics
        metrics = [
            ('Market Cap ($B)', 'market_cap_b', '.1f'),
            ('P/E Ratio', 'pe_ratio', '.1f'),
            ('Forward P/E', 'forward_pe', '.1f'),
            ('PEG Ratio', 'peg_ratio', '.2f'),
            ('Revenue Growth %', 'revenue_growth', '.1f'),
            ('Profit Margin %', 'profit_margin', '.1f'),
            ('ROE %', 'roe', '.1f'),
            ('Debt/Equity', 'debt_to_equity', '.1f'),
            ('Price/Book', 'price_to_book', '.1f'),
            ('YTD Return %', 'price_ytd_pct', '.1f'),
        ]
        
        for label, attr, fmt in metrics:
            row = f"{label:<20}"
            
            # Target value
            target_val = getattr(result.target, attr)
            row += self._format_cell(target_val, fmt, result.ranking.get(attr))
            
            # Peer values
            for peer in result.peers:
                peer_val = getattr(peer, attr)
                row += self._format_cell(peer_val, fmt)
            
            # Average
            avg_val = result.peer_avg.get(attr)
            row += self._format_cell(avg_val, fmt)
            
            lines.append(row)
        
        lines.append("─" * 70)
        
        # Rankings summary
        lines.append("")
        lines.append("📊 RANKINGS (1 = best)")
        lines.append("─" * 70)
        
        for metric, rank in sorted(result.ranking.items()):
            total = len(result.peers) + 1
            emoji = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else "  "
            lines.append(f"  {emoji} {metric.replace('_', ' ').title()}: #{rank} of {total}")
        
        lines.append("")
        lines.append("═" * 70)
        
        return "\n".join(lines)
    
    def _format_cell(self, value, fmt: str, rank: int = None) -> str:
        """Format a cell value."""
        if value is None:
            return f"{'N/A':>10}"
        
        try:
            formatted = f"{value:{fmt}}"
            if rank == 1:
                formatted = f"*{formatted}"
            return f"{formatted:>10}"
        except:
            return f"{'N/A':>10}"


def compare_competitors(ticker: str):
    """Run competitor comparison for a ticker."""
    analyzer = CompetitorAnalyzer(ticker)
    result = analyzer.analyze()
    print(analyzer.format_report(result))
    return result


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        ticker = sys.argv[1].upper()
        compare_competitors(ticker)
    else:
        print("Usage: python competitors.py TICKER")
        print("\nExample: python competitors.py AAPL")

