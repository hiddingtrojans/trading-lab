"""
GPT Moat Analyzer

The missing piece: Actually understanding if a business is GOOD.

Numbers tell you growth. GPT tells you if it's real.
"""

import os
import json
from typing import Optional, Dict, Tuple
from dataclasses import dataclass
from openai import OpenAI


@dataclass
class MoatAnalysis:
    """GPT's assessment of a company's competitive moat."""
    ticker: str
    moat_score: int  # 1-10
    business_type: str  # "SaaS", "Bank", "Commodity", etc.
    one_liner: str  # What they actually do
    verdict: str  # "GOOD", "MEH", "GARBAGE"
    
    # Red flags
    is_bank: bool
    is_commodity: bool
    is_china: bool
    is_tobacco_gambling: bool
    is_cyclical: bool
    
    # Moat indicators
    has_recurring_revenue: bool
    has_switching_costs: bool
    has_network_effects: bool
    has_pricing_power: bool
    
    # Summary
    bull_case: str
    bear_case: str
    recommendation: str


# Companies to auto-reject based on SECTOR (not description)
REJECT_SECTORS = [
    'banks—regional', 'banks—diversified',
    'asset management', 'mortgage finance',
    'oil & gas', 'coal', 'metals & mining',
    'tobacco', 'gambling', 'cannabis',
    'credit services',
]

# Only reject if these appear in INDUSTRY (more precise)
REJECT_INDUSTRIES = [
    'regional banks', 'diversified banks', 'mortgage',
    'oil & gas exploration', 'oil & gas drilling',
    'coal', 'gold', 'silver', 'copper', 'steel',
    'tobacco', 'casinos', 'resorts & casinos',
]

# High-risk keywords in company name only (not description)
REJECT_NAME_KEYWORDS = [
    'bancorp', 'bancshares', 'bank corp', 'bank of',
    'petroleum', 'mining corp', 'gold corp',
    'tobacco', 'cannabis', 'marijuana',
    'casino', 'betting',
]

# China ADR detection (in name or description)
CHINA_KEYWORDS = [
    'china', 'chinese', 'cayman islands', 'hong kong',
    'prc', 'beijing', 'shanghai', 'shenzhen',
]


class MoatAnalyzer:
    """
    Uses GPT to analyze competitive moats.
    
    The scanner finds numbers. This finds quality.
    """
    
    def __init__(self):
        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            # Try to load from config
            config_path = os.path.join(os.path.dirname(__file__), '../../config/keys.json')
            if os.path.exists(config_path):
                with open(config_path) as f:
                    config = json.load(f)
                    api_key = config.get('openai_api_key')
        
        if not api_key:
            raise ValueError("No OpenAI API key found. Set OPENAI_API_KEY or add to config/keys.json")
        
        self.client = OpenAI(api_key=api_key)
    
    def quick_reject(self, name: str, sector: str, industry: str, description: str = "") -> Tuple[bool, str]:
        """
        Quick rejection based on sector/industry. No API call needed.
        
        More precise than keyword matching - only rejects clear cases.
        
        Returns: (should_reject, reason)
        """
        name_lower = name.lower()
        sector_lower = sector.lower()
        industry_lower = industry.lower()
        
        # Check sector (exact match)
        for reject_sector in REJECT_SECTORS:
            if reject_sector in sector_lower or reject_sector in industry_lower:
                return True, f"Sector: {sector}"
        
        # Check industry (exact match)
        for reject_industry in REJECT_INDUSTRIES:
            if reject_industry in industry_lower:
                return True, f"Industry: {industry}"
        
        # Check company name keywords (banks, etc)
        for keyword in REJECT_NAME_KEYWORDS:
            if keyword in name_lower:
                return True, f"Name contains: {keyword}"
        
        # China ADR detection (check name and first 200 chars of description)
        desc_start = description[:200].lower() if description else ""
        for keyword in CHINA_KEYWORDS:
            if keyword in name_lower or keyword in desc_start:
                return True, f"China ADR: {keyword}"
        
        return False, ""
    
    def analyze(
        self, 
        ticker: str,
        name: str,
        sector: str,
        industry: str,
        description: str,
        revenue_b: float,
        revenue_growth: float,
        gross_margin: float,
        operating_margin: float,
    ) -> Optional[MoatAnalysis]:
        """
        Full GPT analysis of competitive moat.
        
        Cost: ~$0.01-0.03 per call
        """
        # Quick reject first (free)
        should_reject, reason = self.quick_reject(name, sector, industry, description)
        if should_reject:
            return MoatAnalysis(
                ticker=ticker,
                moat_score=1,
                business_type="Rejected",
                one_liner=f"Auto-rejected: {reason}",
                verdict="GARBAGE",
                is_bank='bank' in reason.lower(),
                is_commodity='commodity' in sector.lower() or 'oil' in reason.lower(),
                is_china='china' in reason.lower(),
                is_tobacco_gambling='tobacco' in reason.lower() or 'gambling' in reason.lower(),
                is_cyclical=False,
                has_recurring_revenue=False,
                has_switching_costs=False,
                has_network_effects=False,
                has_pricing_power=False,
                bull_case="None",
                bear_case=reason,
                recommendation="Skip - auto-rejected",
            )
        
        # GPT analysis
        prompt = f"""Analyze this company as a GROWTH INVESTMENT. Be brutally honest.

COMPANY: {ticker} - {name}
SECTOR: {sector}
INDUSTRY: {industry}
DESCRIPTION: {description[:500] if description else 'Not available'}

FINANCIALS:
- Revenue: ${revenue_b:.2f}B
- Revenue Growth: {revenue_growth:.1f}% YoY
- Gross Margin: {gross_margin:.1f}%
- Operating Margin: {operating_margin:.1f}%

Answer in this EXACT JSON format:
{{
    "moat_score": <1-10, where 10 is strongest moat>,
    "business_type": "<SaaS|Hardware|Marketplace|Fintech|Healthcare|Consumer|Industrial|Commodity|Financial Services|Other>",
    "one_liner": "<What they do in 10 words or less>",
    "verdict": "<GOOD|MEH|GARBAGE>",
    "is_bank": <true if bank/financial services/BDC/REIT>,
    "is_commodity": <true if oil/gas/mining/agriculture>,
    "is_china": <true if Chinese company or ADR>,
    "is_tobacco_gambling": <true if tobacco/gambling/cannabis>,
    "is_cyclical": <true if highly cyclical business>,
    "has_recurring_revenue": <true if subscription/recurring revenue model>,
    "has_switching_costs": <true if hard for customers to leave>,
    "has_network_effects": <true if product gets better with more users>,
    "has_pricing_power": <true if can raise prices without losing customers>,
    "bull_case": "<Best case in 15 words>",
    "bear_case": "<Worst case in 15 words>",
    "recommendation": "<1 sentence: Should a growth investor look at this?>"
}}

BE HARSH. Most companies are MEH or GARBAGE. Only rate GOOD if it's genuinely a strong growth business with real competitive advantages.

A regional bank with 15% revenue growth is NOT a growth company.
A commodity producer with good margins is NOT a growth company.
A Chinese ADR is HIGH RISK regardless of numbers.

JSON only, no other text:"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # Cheap and fast
                messages=[
                    {"role": "system", "content": "You are a skeptical growth investor. You reject 80% of companies. You only like businesses with real competitive moats."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500,
            )
            
            content = response.choices[0].message.content.strip()
            
            # Parse JSON (handle markdown code blocks)
            if content.startswith('```'):
                content = content.split('```')[1]
                if content.startswith('json'):
                    content = content[4:]
            
            data = json.loads(content)
            
            return MoatAnalysis(
                ticker=ticker,
                moat_score=data.get('moat_score', 1),
                business_type=data.get('business_type', 'Unknown'),
                one_liner=data.get('one_liner', ''),
                verdict=data.get('verdict', 'MEH'),
                is_bank=data.get('is_bank', False),
                is_commodity=data.get('is_commodity', False),
                is_china=data.get('is_china', False),
                is_tobacco_gambling=data.get('is_tobacco_gambling', False),
                is_cyclical=data.get('is_cyclical', False),
                has_recurring_revenue=data.get('has_recurring_revenue', False),
                has_switching_costs=data.get('has_switching_costs', False),
                has_network_effects=data.get('has_network_effects', False),
                has_pricing_power=data.get('has_pricing_power', False),
                bull_case=data.get('bull_case', ''),
                bear_case=data.get('bear_case', ''),
                recommendation=data.get('recommendation', ''),
            )
            
        except Exception as e:
            print(f"   GPT error for {ticker}: {e}")
            return None
    
    def format_analysis(self, analysis: MoatAnalysis) -> str:
        """Format analysis for display."""
        if analysis.verdict == "GARBAGE":
            emoji = "🗑️"
        elif analysis.verdict == "MEH":
            emoji = "😐"
        else:
            emoji = "✅"
        
        # Moat indicators
        moat_icons = []
        if analysis.has_recurring_revenue:
            moat_icons.append("🔄 Recurring")
        if analysis.has_switching_costs:
            moat_icons.append("🔒 Sticky")
        if analysis.has_network_effects:
            moat_icons.append("🕸️ Network")
        if analysis.has_pricing_power:
            moat_icons.append("💰 Pricing")
        
        # Red flags
        flags = []
        if analysis.is_bank:
            flags.append("🏦 Bank")
        if analysis.is_commodity:
            flags.append("⛏️ Commodity")
        if analysis.is_china:
            flags.append("🇨🇳 China")
        if analysis.is_tobacco_gambling:
            flags.append("🚬 Vice")
        if analysis.is_cyclical:
            flags.append("📉 Cyclical")
        
        lines = [
            f"{emoji} {analysis.ticker} - {analysis.verdict} (Moat: {analysis.moat_score}/10)",
            f"   {analysis.one_liner}",
            f"   Type: {analysis.business_type}",
        ]
        
        if moat_icons:
            lines.append(f"   Moat: {' | '.join(moat_icons)}")
        
        if flags:
            lines.append(f"   ⚠️ Flags: {' | '.join(flags)}")
        
        lines.extend([
            f"   📈 Bull: {analysis.bull_case}",
            f"   📉 Bear: {analysis.bear_case}",
            f"   💡 {analysis.recommendation}",
        ])
        
        return "\n".join(lines)


def analyze_moat(ticker: str) -> Optional[MoatAnalysis]:
    """Quick function to analyze a single ticker."""
    import yfinance as yf
    
    stock = yf.Ticker(ticker)
    info = stock.info
    
    analyzer = MoatAnalyzer()
    return analyzer.analyze(
        ticker=ticker,
        name=info.get('shortName', ticker),
        sector=info.get('sector', 'Unknown'),
        industry=info.get('industry', 'Unknown'),
        description=info.get('longBusinessSummary', ''),
        revenue_b=info.get('totalRevenue', 0) / 1e9,
        revenue_growth=(info.get('revenueGrowth', 0) or 0) * 100,
        gross_margin=(info.get('grossMargins', 0) or 0) * 100,
        operating_margin=(info.get('operatingMargins', 0) or 0) * 100,
    )


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        ticker = sys.argv[1].upper()
        print(f"\nAnalyzing {ticker}...")
        
        analysis = analyze_moat(ticker)
        if analysis:
            analyzer = MoatAnalyzer()
            print("\n" + analyzer.format_analysis(analysis))
        else:
            print("Analysis failed")
    else:
        # Test with the garbage stocks from earlier
        test_tickers = ['RLX', 'ORRF', 'SEB', 'DOCN', 'PLTR']
        
        print("\n" + "=" * 60)
        print("MOAT ANALYSIS TEST")
        print("=" * 60)
        
        for ticker in test_tickers:
            print(f"\nAnalyzing {ticker}...")
            analysis = analyze_moat(ticker)
            if analysis:
                analyzer = MoatAnalyzer()
                print(analyzer.format_analysis(analysis))

