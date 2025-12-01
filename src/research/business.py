"""
Business Understanding Module

Goes beyond numbers to understand:
- What does the company actually do?
- Who are their customers?
- What's their competitive advantage (moat)?
- Who are the competitors?
- What are the key risks?

Uses SEC filings + AI to extract business insights.
"""

import os
import requests
import yfinance as yf
from datetime import datetime
from typing import Dict, Optional, List
from dataclasses import dataclass
import json
import re


@dataclass
class BusinessProfile:
    """Complete business understanding."""
    ticker: str
    name: str
    
    # Business description
    description: str
    business_summary: str
    
    # Market position
    sector: str
    industry: str
    employees: int
    headquarters: str
    founded: Optional[str]
    
    # Products/Services
    products: List[str]
    revenue_segments: List[Dict]
    
    # Competitive landscape
    competitors: List[str]
    competitive_advantages: List[str]
    
    # Risks
    key_risks: List[str]
    
    # Management
    ceo: str
    key_executives: List[Dict]
    
    # Recent developments
    recent_news: List[Dict]


class BusinessAnalyzer:
    """
    Understand the business, not just the stock.
    
    This is the work that creates real edge.
    """
    
    SEC_HEADERS = {
        'User-Agent': 'Research Platform research@example.com',
        'Accept-Encoding': 'gzip, deflate',
    }
    
    def __init__(self, ticker: str):
        self.ticker = ticker.upper()
        self.stock = yf.Ticker(self.ticker)
        self.info = self.stock.info
        self.profile: Optional[BusinessProfile] = None
    
    def analyze(self) -> BusinessProfile:
        """Run complete business analysis."""
        info = self.info
        
        # Basic info
        name = info.get('longName') or info.get('shortName', self.ticker)
        description = info.get('longBusinessSummary', '')
        
        # Create concise business summary
        business_summary = self._summarize_business(description)
        
        # Company info
        sector = info.get('sector', 'Unknown')
        industry = info.get('industry', 'Unknown')
        employees = info.get('fullTimeEmployees', 0)
        
        city = info.get('city', '')
        country = info.get('country', '')
        headquarters = f"{city}, {country}" if city else country
        
        # Products and segments (from description)
        products = self._extract_products(description)
        revenue_segments = self._get_revenue_segments()
        
        # Competitors
        competitors = self._identify_competitors()
        
        # Competitive advantages
        advantages = self._identify_moat(description)
        
        # Risks
        risks = self._identify_risks(description)
        
        # Management
        ceo = self._get_ceo()
        executives = self._get_executives()
        
        # News
        news = self._get_recent_news()
        
        self.profile = BusinessProfile(
            ticker=self.ticker,
            name=name,
            description=description,
            business_summary=business_summary,
            sector=sector,
            industry=industry,
            employees=employees,
            headquarters=headquarters,
            founded=None,  # Would need to scrape
            products=products,
            revenue_segments=revenue_segments,
            competitors=competitors,
            competitive_advantages=advantages,
            key_risks=risks,
            ceo=ceo,
            key_executives=executives,
            recent_news=news,
        )
        
        return self.profile
    
    def _summarize_business(self, description: str) -> str:
        """Create a concise business summary."""
        if not description:
            return "Business description not available."
        
        # Take first 2-3 sentences
        sentences = description.split('. ')
        summary = '. '.join(sentences[:3])
        if not summary.endswith('.'):
            summary += '.'
        
        return summary[:500]
    
    def _extract_products(self, description: str) -> List[str]:
        """Extract main products/services from description."""
        products = []
        
        # Common product keywords
        keywords = [
            'platform', 'software', 'service', 'solution', 'product',
            'application', 'system', 'technology', 'tool',
        ]
        
        # Simple extraction - would be better with NLP
        sentences = description.lower().split('.')
        for sentence in sentences:
            for keyword in keywords:
                if keyword in sentence:
                    # Extract phrase around keyword
                    products.append(sentence.strip()[:100])
                    break
        
        return products[:5]  # Top 5
    
    def _get_revenue_segments(self) -> List[Dict]:
        """Get revenue breakdown by segment if available."""
        # yfinance doesn't have this easily
        # Would need to parse 10-K
        return []
    
    def _identify_competitors(self) -> List[str]:
        """Identify key competitors."""
        # Based on industry
        industry = self.info.get('industry', '')
        sector = self.info.get('sector', '')
        
        # Industry competitor mapping
        competitor_map = {
            'Software—Infrastructure': ['MSFT', 'AMZN', 'GOOGL', 'CRM', 'ORCL'],
            'Software—Application': ['CRM', 'ADBE', 'NOW', 'WDAY', 'INTU'],
            'Internet Content & Information': ['GOOGL', 'META', 'SNAP', 'PINS', 'TWTR'],
            'Semiconductors': ['NVDA', 'AMD', 'INTC', 'QCOM', 'AVGO'],
            'Internet Retail': ['AMZN', 'BABA', 'JD', 'MELI', 'SE'],
            'Biotechnology': ['AMGN', 'GILD', 'BIIB', 'VRTX', 'REGN'],
            'Specialty Retail': ['HD', 'LOW', 'TJX', 'ROST', 'BBY'],
        }
        
        competitors = competitor_map.get(industry, [])
        
        # Remove self from competitors
        competitors = [c for c in competitors if c != self.ticker]
        
        return competitors[:5]
    
    def _identify_moat(self, description: str) -> List[str]:
        """Identify potential competitive advantages."""
        moats = []
        desc_lower = description.lower()
        
        # Check for moat indicators
        moat_indicators = {
            'network effect': ['network', 'platform', 'marketplace', 'ecosystem'],
            'switching costs': ['integrated', 'embedded', 'mission-critical', 'enterprise'],
            'brand strength': ['leading', 'trusted', 'brand', 'recognized'],
            'cost advantage': ['scale', 'efficient', 'low-cost', 'automation'],
            'intellectual property': ['patent', 'proprietary', 'unique technology'],
            'regulatory barrier': ['licensed', 'regulated', 'compliance', 'approved'],
        }
        
        for moat_type, keywords in moat_indicators.items():
            for keyword in keywords:
                if keyword in desc_lower:
                    moats.append(moat_type.title())
                    break
        
        if not moats:
            moats.append("No clear moat identified - requires deeper analysis")
        
        return list(set(moats))
    
    def _identify_risks(self, description: str) -> List[str]:
        """Identify key business risks."""
        risks = []
        
        info = self.info
        
        # Financial risks
        debt_to_equity = info.get('debtToEquity', 0) or 0
        if debt_to_equity > 100:
            risks.append(f"High debt levels ({debt_to_equity/100:.1f}x D/E)")
        
        # Profitability
        net_margin = info.get('profitMargins', 0) or 0
        if net_margin < 0:
            risks.append("Currently unprofitable")
        
        # Cash burn
        fcf = info.get('freeCashflow', 0)
        if fcf < 0:
            risks.append("Negative free cash flow")
        
        # Customer concentration (from description)
        if 'concentration' in description.lower() or 'single customer' in description.lower():
            risks.append("Customer concentration risk")
        
        # Competitive risk
        risks.append("Competitive pressure in industry")
        
        # Regulatory
        if any(word in description.lower() for word in ['regulation', 'compliance', 'government']):
            risks.append("Regulatory/compliance risk")
        
        return risks[:5]
    
    def _get_ceo(self) -> str:
        """Get CEO name."""
        try:
            officers = self.stock.info.get('companyOfficers', [])
            for officer in officers:
                title = officer.get('title', '').lower()
                if 'ceo' in title or 'chief executive' in title:
                    return officer.get('name', 'Unknown')
            return 'Unknown'
        except:
            return 'Unknown'
    
    def _get_executives(self) -> List[Dict]:
        """Get key executives."""
        try:
            officers = self.stock.info.get('companyOfficers', [])
            return [
                {'name': o.get('name', ''), 'title': o.get('title', '')}
                for o in officers[:5]
            ]
        except:
            return []
    
    def _get_recent_news(self) -> List[Dict]:
        """Get recent news headlines."""
        try:
            news = self.stock.news
            return [
                {
                    'title': n.get('title', ''),
                    'publisher': n.get('publisher', ''),
                    'date': datetime.fromtimestamp(n.get('providerPublishTime', 0)).strftime('%Y-%m-%d'),
                    'link': n.get('link', ''),
                }
                for n in news[:5]
            ]
        except:
            return []
    
    def format_report(self) -> str:
        """Format business analysis as report."""
        if not self.profile:
            self.analyze()
        
        p = self.profile
        
        lines = [
            "═" * 60,
            f"🏢 BUSINESS ANALYSIS: {p.ticker}",
            f"   {p.name}",
            "═" * 60,
            "",
            "─" * 60,
            "WHAT DO THEY DO?",
            "─" * 60,
            p.business_summary,
            "",
            "─" * 60,
            "COMPANY INFO",
            "─" * 60,
            f"Sector: {p.sector}",
            f"Industry: {p.industry}",
            f"Headquarters: {p.headquarters}",
            f"Employees: {p.employees:,}" if p.employees else "Employees: Unknown",
            f"CEO: {p.ceo}",
            "",
        ]
        
        if p.key_executives:
            lines.append("Key Executives:")
            for exec in p.key_executives[:3]:
                lines.append(f"  • {exec['name']} - {exec['title']}")
            lines.append("")
        
        lines.extend([
            "─" * 60,
            "COMPETITIVE LANDSCAPE",
            "─" * 60,
        ])
        
        if p.competitors:
            lines.append("Main Competitors:")
            for comp in p.competitors:
                lines.append(f"  • {comp}")
            lines.append("")
        
        lines.append("Competitive Advantages:")
        for adv in p.competitive_advantages:
            lines.append(f"  ✓ {adv}")
        
        lines.extend([
            "",
            "─" * 60,
            "KEY RISKS",
            "─" * 60,
        ])
        
        for risk in p.key_risks:
            lines.append(f"  ⚠️ {risk}")
        
        if p.recent_news:
            lines.extend([
                "",
                "─" * 60,
                "RECENT NEWS",
                "─" * 60,
            ])
            for news in p.recent_news[:3]:
                lines.append(f"  📰 {news['title'][:60]}...")
                lines.append(f"     {news['publisher']} | {news['date']}")
        
        lines.extend([
            "",
            "═" * 60,
        ])
        
        return "\n".join(lines)


def analyze_business(ticker: str) -> BusinessProfile:
    """Run business analysis on a ticker."""
    analyzer = BusinessAnalyzer(ticker)
    profile = analyzer.analyze()
    print(analyzer.format_report())
    return profile


if __name__ == "__main__":
    import sys
    ticker = sys.argv[1] if len(sys.argv) > 1 else "DOCN"
    analyze_business(ticker)

