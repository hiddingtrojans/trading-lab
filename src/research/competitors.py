"""
Competitor Comparison Module

Side-by-side comparison with industry peers.

Why this matters:
- Numbers without context are meaningless
- "Expensive" vs peers? Or just "expensive"?
- Identify best-in-class vs laggards
"""

import os
import sys
from typing import Optional, List, Dict
from dataclasses import dataclass
import yfinance as yf

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))


# Manually curated peer groups for common stocks
PEER_GROUPS = {
    # Tech Giants
    'AAPL': ['MSFT', 'GOOGL', 'AMZN', 'META'],
    'MSFT': ['AAPL', 'GOOGL', 'AMZN', 'META'],
    'GOOGL': ['AAPL', 'MSFT', 'META', 'AMZN'],
    'GOOG': ['AAPL', 'MSFT', 'META', 'AMZN'],
    'META': ['GOOGL', 'SNAP', 'PINS', 'TWTR'],
    'AMZN': ['WMT', 'TGT', 'COST', 'EBAY'],
    
    # Semiconductors
    'NVDA': ['AMD', 'INTC', 'AVGO', 'QCOM'],
    'AMD': ['NVDA', 'INTC', 'QCOM', 'MU'],
    'INTC': ['AMD', 'NVDA', 'QCOM', 'TXN'],
    
    # EV/Auto
    'TSLA': ['GM', 'F', 'RIVN', 'LCID'],
    'RIVN': ['TSLA', 'LCID', 'GM', 'F'],
    
    # Streaming
    'NFLX': ['DIS', 'WBD', 'PARA', 'CMCSA'],
    'DIS': ['NFLX', 'WBD', 'CMCSA', 'PARA'],
    
    # Fintech/Payments
    'V': ['MA', 'PYPL', 'SQ', 'AXP'],
    'MA': ['V', 'PYPL', 'SQ', 'AXP'],
    'PYPL': ['V', 'MA', 'SQ', 'AFRM'],
    'SQ': ['PYPL', 'V', 'MA', 'AFRM'],
    
    # Cloud/SaaS
    'CRM': ['NOW', 'WDAY', 'ORCL', 'SAP'],
    'NOW': ['CRM', 'WDAY', 'SNOW', 'DDOG'],
    
    # Banks
    'JPM': ['BAC', 'C', 'WFC', 'GS'],
    'BAC': ['JPM', 'C', 'WFC', 'MS'],
    
    # Retail
    'WMT': ['TGT', 'COST', 'AMZN', 'HD'],
    'TGT': ['WMT', 'COST', 'KR', 'DG'],
    
    # Airlines
    'DAL': ['UAL', 'AAL', 'LUV', 'JBLU'],
    
    # Healthcare
    'UNH': ['CVS', 'CI', 'ELV', 'HUM'],
    'JNJ': ['PFE', 'MRK', 'ABBV', 'LLY'],
}


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
    Compare a stock to its peers.
    """
    
    # Industry to ticker mapping for auto peer discovery
    INDUSTRY_PEERS = {
        'Software - Application': ['CRM', 'NOW', 'WDAY', 'ADBE', 'INTU', 'TEAM', 'ZM', 'DDOG'],
        'Software - Infrastructure': ['MSFT', 'ORCL', 'CRM', 'NOW', 'SNOW', 'MDB', 'NET'],
        'Semiconductors': ['NVDA', 'AMD', 'INTC', 'QCOM', 'AVGO', 'TXN', 'MU', 'AMAT'],
        'Internet Content & Information': ['GOOGL', 'META', 'SNAP', 'PINS', 'TWTR'],
        'Internet Retail': ['AMZN', 'EBAY', 'ETSY', 'SHOP', 'MELI', 'SE'],
        'Consumer Electronics': ['AAPL', 'SONY', 'HPQ', 'DELL'],
        'Auto Manufacturers': ['TSLA', 'GM', 'F', 'RIVN', 'LCID', 'TM', 'HMC'],
        'Banks - Diversified': ['JPM', 'BAC', 'C', 'WFC', 'GS', 'MS'],
        'Banks - Regional': ['USB', 'PNC', 'TFC', 'FITB', 'KEY'],
        'Credit Services': ['V', 'MA', 'AXP', 'DFS', 'COF', 'SYF'],
        'Financial Data & Stock Exchanges': ['SPGI', 'MSCI', 'ICE', 'CME', 'NDAQ'],
        'Asset Management': ['BLK', 'BX', 'KKR', 'APO', 'ARES'],
        'Insurance - Diversified': ['BRK-B', 'AIG', 'MET', 'PRU', 'AFL'],
        'Drug Manufacturers': ['JNJ', 'PFE', 'MRK', 'ABBV', 'LLY', 'BMY'],
        'Biotechnology': ['AMGN', 'GILD', 'BIIB', 'REGN', 'VRTX', 'MRNA'],
        'Medical Devices': ['MDT', 'ABT', 'SYK', 'BSX', 'ISRG', 'EW'],
        'Healthcare Plans': ['UNH', 'CVS', 'CI', 'ELV', 'HUM', 'CNC'],
        'Retail - Defensive': ['WMT', 'COST', 'TGT', 'DG', 'DLTR', 'KR'],
        'Restaurants': ['MCD', 'SBUX', 'CMG', 'YUM', 'DRI', 'QSR'],
        'Entertainment': ['DIS', 'NFLX', 'WBD', 'PARA', 'CMCSA', 'LYV'],
        'Aerospace & Defense': ['BA', 'LMT', 'RTX', 'NOC', 'GD', 'GE'],
        'Oil & Gas Integrated': ['XOM', 'CVX', 'COP', 'EOG', 'SLB', 'OXY'],
        'Utilities - Regulated Electric': ['NEE', 'DUK', 'SO', 'D', 'AEP', 'XEL'],
        'REIT - Diversified': ['AMT', 'PLD', 'EQIX', 'PSA', 'SPG', 'O'],
        'Telecom Services': ['T', 'VZ', 'TMUS', 'CMCSA', 'CHTR'],
        'Information Technology Services': ['ACN', 'IBM', 'CTSH', 'INFY', 'WIT'],
        'Specialty Retail': ['HD', 'LOW', 'TJX', 'ROST', 'BBY', 'ULTA'],
        'Packaged Foods': ['PEP', 'KO', 'MDLZ', 'GIS', 'K', 'KHC'],
        'Household Products': ['PG', 'CL', 'KMB', 'CHD', 'CLX'],
        # Fintech / Payment processing
        'Software - Financial': ['SQ', 'PYPL', 'AFRM', 'SOFI', 'UPST'],
        # Latin America focused
        'Financial - Payment Processing': ['DLO', 'STNE', 'PAGS', 'NU', 'MELI'],
    }
    
    def __init__(self, ticker: str):
        self.ticker = ticker.upper()
    
    def _find_peers_by_industry(self) -> List[str]:
        """Auto-find peers by industry."""
        try:
            stock = yf.Ticker(self.ticker)
            info = stock.info
            industry = info.get('industry', '')
            
            if not industry:
                return []
            
            # Check if we have peers for this industry
            if industry in self.INDUSTRY_PEERS:
                peers = [p for p in self.INDUSTRY_PEERS[industry] if p != self.ticker]
                return peers[:4]  # Max 4 peers
            
            # Try partial match
            for ind_name, peers in self.INDUSTRY_PEERS.items():
                if ind_name.lower() in industry.lower() or industry.lower() in ind_name.lower():
                    peers = [p for p in peers if p != self.ticker]
                    return peers[:4]
            
            # Still no match - try to find similar stocks by sector
            sector = info.get('sector', '')
            similar = []
            
            # Generic fallback by sector
            sector_fallback = {
                'Technology': ['AAPL', 'MSFT', 'GOOGL', 'META'],
                'Financial Services': ['JPM', 'V', 'MA', 'GS'],
                'Healthcare': ['JNJ', 'UNH', 'PFE', 'ABBV'],
                'Consumer Cyclical': ['AMZN', 'TSLA', 'HD', 'NKE'],
                'Consumer Defensive': ['PG', 'KO', 'PEP', 'WMT'],
                'Energy': ['XOM', 'CVX', 'COP', 'SLB'],
                'Industrials': ['CAT', 'HON', 'UPS', 'BA'],
                'Communication Services': ['GOOGL', 'META', 'DIS', 'NFLX'],
                'Utilities': ['NEE', 'DUK', 'SO', 'D'],
                'Real Estate': ['AMT', 'PLD', 'EQIX', 'PSA'],
                'Basic Materials': ['LIN', 'APD', 'SHW', 'ECL'],
            }
            
            if sector in sector_fallback:
                similar = [p for p in sector_fallback[sector] if p != self.ticker]
            
            return similar[:4]
            
        except Exception as e:
            return []
    
    def analyze(self) -> ComparisonResult:
        """Run peer comparison analysis."""
        
        # Get peers
        peers_list = PEER_GROUPS.get(self.ticker, [])
        
        if not peers_list:
            # Auto-find peers by industry
            peers_list = self._find_peers_by_industry()
        
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

