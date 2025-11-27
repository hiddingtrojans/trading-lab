#!/usr/bin/env python3
"""
Sentiment Features with FinBERT
================================

News sentiment using FinBERT model.
"""

import pandas as pd
from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
import warnings
warnings.filterwarnings('ignore')


_finbert_pipe = None


def _get_finbert_pipe():
    """Lazy load FinBERT pipeline."""
    global _finbert_pipe
    
    if _finbert_pipe is None:
        print("📦 Loading FinBERT model...")
        tok = AutoTokenizer.from_pretrained("yiyanghkust/finbert-tone")
        mdl = AutoModelForSequenceClassification.from_pretrained("yiyanghkust/finbert-tone")
        _finbert_pipe = pipeline(
            "text-classification",
            model=mdl,
            tokenizer=tok,
            return_all_scores=True,
            truncation=True
        )
        print("✅ FinBERT loaded")
    
    return _finbert_pipe


def build_sentiment_features(cfg: dict, cutoff_utc: str = "21:00") -> pd.DataFrame:
    """
    Build sentiment features from news.
    
    Args:
        cfg: Config dict
        cutoff_utc: UTC time cutoff (only include news before this time)
        
    Returns:
        DataFrame with multi-index (date, ticker) and sentiment scores
    """
    # Expect headlines with timestamps and tickers in data/raw/news.csv
    # Format: ts_utc, ticker, headline
    
    news_path = "data/raw/news.csv"
    
    try:
        df = pd.read_csv(news_path, parse_dates=["ts_utc"])
    except FileNotFoundError:
        print(f"⚠️  No news file found at {news_path}")
        print("   Creating dummy sentiment features (all neutral)")
        
        # Return empty DataFrame with correct structure
        return pd.DataFrame(columns=['S_diff_mean', 'S_diff_std', 'S_n'])
    
    # Filter by cutoff time
    df = df[df["ts_utc"].dt.strftime("%H:%M") <= cutoff_utc]
    
    if df.empty:
        return pd.DataFrame(columns=['S_diff_mean', 'S_diff_std', 'S_n'])
    
    # Get FinBERT pipeline
    clf = _get_finbert_pipe()
    
    # Score headlines
    scores = []
    
    for _, r in df.iterrows():
        headline = r["headline"][:256]  # Truncate to 256 chars
        
        try:
            out = clf(headline)[0]
            d = {s['label'].lower(): s['score'] for s in out}
            
            # Sentiment diff: positive - negative
            s_diff = d.get("positive", 0) - d.get("negative", 0)
            
            scores.append((r["ts_utc"].date(), r["ticker"], s_diff))
        except Exception as e:
            print(f"⚠️  Error scoring headline: {e}")
            continue
    
    if not scores:
        return pd.DataFrame(columns=['S_diff_mean', 'S_diff_std', 'S_n'])
    
    # Aggregate by date and ticker
    s = (pd.DataFrame(scores, columns=["date", "ticker", "s_diff"])
         .groupby(["date", "ticker"])
         .agg({"s_diff": ["mean", "std", "count"]}))
    
    s.columns = ["S_diff_mean", "S_diff_std", "S_n"]
    
    return s
