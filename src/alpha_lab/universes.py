"""
Centralized Universe Definitions
================================

Single source of truth for all ticker lists.
Import from here instead of hardcoding in each scanner.

Usage:
    from alpha_lab.universes import SMALL_CAP, MID_CAP, LIQUID_TECH, get_universe
"""

# High growth small caps - higher risk, higher reward
SMALL_CAP = [
    # Technology - High Growth
    'SMCI', 'CRDO', 'AEHR', 'IONQ', 'RGTI', 'QUBT', 'KULR', 'SOUN', 'BBAI', 'BIGC',
    'APP', 'DUOL', 'GLBE', 'TOST', 'BILL', 'PCOR', 'BRZE', 'DOCN', 'GTLB', 'MDB',
    'NET', 'CFLT', 'ESTC', 'DDOG', 'ZS', 'CRWD', 'PANW', 'FTNT', 'OKTA', 'CYBR',
    
    # Biotech/Healthcare
    'MRNA', 'BNTX', 'NVAX', 'SRRK', 'ARCT', 'VKTX', 'AKRO', 'MDGL', 'CRNX', 'BMRN',
    'EXAS', 'NTRA', 'ILMN', 'TWST', 'CDNA', 'GH', 'PACB', 'RXRX', 'DNA', 'BEAM',
    
    # Consumer/Retail
    'BIRD', 'BROS', 'CAVA', 'SHAK', 'WING', 'CMG', 'TXRH', 'DRI', 'EAT', 'PLAY',
    'LULU', 'DECK', 'ONON', 'SKX', 'CROX', 'ANF', 'GPS', 'AEO', 'URBN', 'GOOS',
    
    # Fintech
    'SOFI', 'UPST', 'AFRM', 'LC', 'HOOD', 'COIN', 'MARA', 'RIOT', 'CLSK', 'HUT',
    
    # Energy/Clean Tech
    'FSLR', 'ENPH', 'SEDG', 'RUN', 'NOVA', 'ARRY', 'PLUG', 'BLDP', 'BE', 'FCEL',
    
    # Recent IPOs / Underfollowed
    'ARM', 'BIRK', 'CART', 'KVYO', 'VRT', 'RDDT', 'GRAB', 'SE',
    'NU', 'STNE', 'PAGS', 'XP', 'MELI', 'GLOB', 'DLO', 'FOUR', 'PGY', 'ZETA',
]

# Mid caps - more stable, still growth potential
MID_CAP = [
    'ABNB', 'DASH', 'UBER', 'LYFT', 'RDFN', 'Z', 'CVNA', 'CARG',
    'TTD', 'ROKU', 'SPOT', 'SNAP', 'PINS', 'MTCH', 'ETSY', 'CHWY', 'W',
    'SQ', 'PYPL', 'SHOP', 'MKTX', 'VIRT',
    'WDAY', 'NOW', 'CRM', 'VEEV', 'HUBS', 'ZM', 'DOCU', 'BOX', 'DBX',
]

# Liquid tech - high volume, tight spreads, best for day trading
LIQUID_TECH = [
    'NVDA', 'AMD', 'TSLA', 'AAPL', 'MSFT', 'GOOGL', 'META', 'AMZN',
    'NFLX', 'CRM', 'ORCL', 'ADBE', 'INTC', 'QCOM', 'AVGO', 'MU',
]

# Meme/High volatility - use with caution
MEME_ADJACENT = [
    'GME', 'AMC', 'PLTR', 'SNOW', 'U', 'RBLX', 'DKNG', 'PENN',
]

# Sector ETFs for rotation analysis
SECTOR_ETFS = {
    'XLK': 'Technology',
    'XLF': 'Financials',
    'XLE': 'Energy',
    'XLV': 'Healthcare',
    'XLI': 'Industrials',
    'XLY': 'Consumer Discretionary',
    'XLP': 'Consumer Staples',
    'XLB': 'Materials',
    'XLU': 'Utilities',
    'XLRE': 'Real Estate',
    'XLC': 'Communication Services',
}


def get_universe(name: str = 'all') -> list:
    """
    Get ticker universe by name.
    
    Args:
        name: 'small_cap', 'mid_cap', 'liquid', 'meme', 'all'
    
    Returns:
        List of ticker symbols
    """
    universes = {
        'small_cap': SMALL_CAP,
        'mid_cap': MID_CAP,
        'liquid': LIQUID_TECH,
        'meme': MEME_ADJACENT,
        'all': list(set(SMALL_CAP + MID_CAP + LIQUID_TECH)),
        'tradeable': list(set(SMALL_CAP + MID_CAP)),  # Excludes meme
    }
    return universes.get(name, universes['tradeable'])


def get_sector_etf(sector: str) -> str:
    """Get ETF ticker for a sector name."""
    reverse = {v: k for k, v in SECTOR_ETFS.items()}
    return reverse.get(sector, 'SPY')

