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
class NewsSentiment:
    """Sentiment analysis of recent news."""
    overall_sentiment: str  # "Bullish", "Bearish", "Neutral", "Mixed"
    sentiment_score: int  # -100 to +100
    summary: str  # One-line summary
    key_themes: List[str]  # Main topics in news
    bullish_signals: List[str]
    bearish_signals: List[str]


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
    news_sentiment: Optional[NewsSentiment] = None


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
        
        # Sentiment analysis (uses OpenAI if available)
        sentiment = self._analyze_news_sentiment(news, name)
        
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
            news_sentiment=sentiment,
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
        """
        Get recent news headlines.
        
        Sources (in order of preference):
        1. Google News RSS (free, reliable)
        2. yfinance (fallback)
        """
        # Try Google News first
        google_news = self._get_google_news()
        if google_news:
            return google_news
        
        # Fallback to yfinance
        try:
            news = self.stock.news
            if not news:
                return []
            
            result = []
            for n in news[:5]:
                title = n.get('title', '')
                if not title or title == '...':
                    continue
                
                timestamp = n.get('providerPublishTime', 0)
                if timestamp and timestamp > 946684800:
                    date_str = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')
                else:
                    date_str = 'Recent'
                
                result.append({
                    'title': title,
                    'publisher': n.get('publisher', 'Unknown'),
                    'date': date_str,
                    'link': n.get('link', ''),
                })
            
            return result
        except:
            return []
    
    def _get_google_news(self) -> List[Dict]:
        """Fetch news from Google News RSS (free, no API key)."""
        try:
            import xml.etree.ElementTree as ET
            from urllib.parse import quote
            
            # Get company name for search
            company_name = self.info.get('shortName', self.ticker)
            
            # Google News RSS URL
            query = quote(f"{company_name} stock")
            url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
            
            response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            
            if response.status_code != 200:
                return []
            
            # Parse RSS XML
            root = ET.fromstring(response.content)
            
            result = []
            for item in root.findall('.//item')[:5]:
                title_elem = item.find('title')
                pub_date_elem = item.find('pubDate')
                source_elem = item.find('source')
                link_elem = item.find('link')
                
                title = title_elem.text if title_elem is not None else ''
                
                # Parse date (format: "Mon, 25 Nov 2024 12:00:00 GMT")
                if pub_date_elem is not None and pub_date_elem.text:
                    try:
                        from email.utils import parsedate_to_datetime
                        dt = parsedate_to_datetime(pub_date_elem.text)
                        date_str = dt.strftime('%Y-%m-%d')
                    except:
                        date_str = 'Recent'
                else:
                    date_str = 'Recent'
                
                source = source_elem.text if source_elem is not None else 'Google News'
                link = link_elem.text if link_elem is not None else ''
                
                if title:
                    result.append({
                        'title': title,
                        'publisher': source,
                        'date': date_str,
                        'link': link,
                    })
            
            return result
            
        except Exception as e:
            return []
    
    def _analyze_news_sentiment(self, news: List[Dict], company_name: str) -> Optional[NewsSentiment]:
        """
        Analyze sentiment of recent news using OpenAI.
        
        Cost: ~$0.01 per analysis
        """
        if not news:
            return None
        
        try:
            from openai import OpenAI
            
            # Get API key
            api_key = os.environ.get('OPENAI_API_KEY')
            if not api_key:
                config_path = os.path.join(os.path.dirname(__file__), '../../config/keys.json')
                if os.path.exists(config_path):
                    with open(config_path) as f:
                        config = json.load(f)
                        api_key = config.get('openai_api_key')
            
            if not api_key:
                return self._simple_sentiment_analysis(news)
            
            client = OpenAI(api_key=api_key)
            
            # Format news for analysis
            news_text = "\n".join([
                f"- {n['title']} ({n['publisher']}, {n['date']})"
                for n in news[:5]
            ])
            
            prompt = f"""Analyze the sentiment of these recent news headlines about {company_name}:

{news_text}

Respond in this exact JSON format:
{{
    "overall_sentiment": "<Bullish|Bearish|Neutral|Mixed>",
    "sentiment_score": <-100 to +100, where -100 is extremely bearish, +100 is extremely bullish>,
    "summary": "<One sentence summary of the news sentiment>",
    "key_themes": ["<theme1>", "<theme2>", "<theme3>"],
    "bullish_signals": ["<signal1>", "<signal2>"],
    "bearish_signals": ["<signal1>", "<signal2>"]
}}

Be objective. If news is mostly neutral/factual, say Neutral. Only say Bullish/Bearish if there's clear positive/negative sentiment.
JSON only:"""

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a financial news sentiment analyzer. Be objective and accurate."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=300,
            )
            
            content = response.choices[0].message.content.strip()
            
            # Parse JSON
            if content.startswith('```'):
                content = content.split('```')[1]
                if content.startswith('json'):
                    content = content[4:]
            
            data = json.loads(content)
            
            return NewsSentiment(
                overall_sentiment=data.get('overall_sentiment', 'Neutral'),
                sentiment_score=data.get('sentiment_score', 0),
                summary=data.get('summary', ''),
                key_themes=data.get('key_themes', []),
                bullish_signals=data.get('bullish_signals', []),
                bearish_signals=data.get('bearish_signals', []),
            )
            
        except Exception as e:
            # Fallback to simple analysis
            return self._simple_sentiment_analysis(news)
    
    def _simple_sentiment_analysis(self, news: List[Dict]) -> Optional[NewsSentiment]:
        """Simple keyword-based sentiment (fallback when no OpenAI)."""
        if not news:
            return None
        
        bullish_words = ['surge', 'soar', 'jump', 'gain', 'rise', 'up', 'high', 'growth', 
                         'beat', 'strong', 'bullish', 'buy', 'upgrade', 'outperform', 'positive']
        bearish_words = ['fall', 'drop', 'plunge', 'decline', 'down', 'low', 'weak', 'miss',
                         'bearish', 'sell', 'downgrade', 'underperform', 'negative', 'concern', 'risk']
        
        bullish_count = 0
        bearish_count = 0
        
        for n in news:
            title_lower = n.get('title', '').lower()
            for word in bullish_words:
                if word in title_lower:
                    bullish_count += 1
            for word in bearish_words:
                if word in title_lower:
                    bearish_count += 1
        
        if bullish_count > bearish_count + 2:
            sentiment = "Bullish"
            score = min(50 + (bullish_count - bearish_count) * 10, 80)
        elif bearish_count > bullish_count + 2:
            sentiment = "Bearish"
            score = max(-50 - (bearish_count - bullish_count) * 10, -80)
        elif bullish_count > 0 and bearish_count > 0:
            sentiment = "Mixed"
            score = (bullish_count - bearish_count) * 10
        else:
            sentiment = "Neutral"
            score = 0
        
        return NewsSentiment(
            overall_sentiment=sentiment,
            sentiment_score=score,
            summary="Based on keyword analysis of headlines",
            key_themes=[],
            bullish_signals=[],
            bearish_signals=[],
        )
    
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
                title = news.get('title', '')
                if title and len(title) > 3:  # Skip empty or very short titles
                    display_title = title[:60] + "..." if len(title) > 60 else title
                    lines.append(f"  📰 {display_title}")
                    lines.append(f"     {news.get('publisher', '')} | {news.get('date', 'Recent')}")
        
        # Sentiment Analysis
        if p.news_sentiment:
            s = p.news_sentiment
            
            # Emoji based on sentiment
            if s.overall_sentiment == "Bullish":
                emoji = "🟢"
            elif s.overall_sentiment == "Bearish":
                emoji = "🔴"
            elif s.overall_sentiment == "Mixed":
                emoji = "🟡"
            else:
                emoji = "⚪"
            
            lines.extend([
                "",
                "─" * 60,
                "NEWS SENTIMENT ANALYSIS",
                "─" * 60,
                f"  {emoji} Overall: {s.overall_sentiment} ({s.sentiment_score:+d}/100)",
            ])
            
            if s.summary:
                lines.append(f"  📝 {s.summary}")
            
            if s.key_themes:
                lines.append(f"  🏷️  Themes: {', '.join(s.key_themes[:3])}")
            
            if s.bullish_signals:
                lines.append(f"  📈 Bullish: {', '.join(s.bullish_signals[:2])}")
            
            if s.bearish_signals:
                lines.append(f"  📉 Bearish: {', '.join(s.bearish_signals[:2])}")
        
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

