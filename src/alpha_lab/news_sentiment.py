#!/usr/bin/env python3
"""
News Sentiment Analysis with FinBERT
=====================================

Fetches FREE news from Yahoo Finance and analyzes with FinBERT.
No API key required.
"""

import os
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import warnings
warnings.filterwarnings('ignore')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))


# Lazy load FinBERT to save memory
_finbert_pipe = None


def get_finbert():
    """Lazy load FinBERT pipeline."""
    global _finbert_pipe
    
    if _finbert_pipe is None:
        print("  📦 Loading FinBERT model (first time only)...")
        try:
            from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
            
            tok = AutoTokenizer.from_pretrained("yiyanghkust/finbert-tone")
            mdl = AutoModelForSequenceClassification.from_pretrained("yiyanghkust/finbert-tone")
            _finbert_pipe = pipeline(
                "text-classification",
                model=mdl,
                tokenizer=tok,
                return_all_scores=True,
                truncation=True
            )
            print("  ✅ FinBERT loaded")
        except Exception as e:
            print(f"  ❌ FinBERT failed to load: {e}")
            return None
    
    return _finbert_pipe


def fetch_news_yfinance(ticker: str, max_articles: int = 10) -> List[Dict]:
    """
    Fetch news from Yahoo Finance (FREE, no API key).
    
    Returns list of:
    {
        'title': str,
        'publisher': str,
        'link': str,
        'published': datetime,
    }
    """
    import yfinance as yf
    
    news = []
    
    try:
        stock = yf.Ticker(ticker)
        raw_news = stock.news
        
        if not raw_news:
            return news
            
        for item in raw_news[:max_articles]:
            # Handle nested structure (yfinance 0.2.x+)
            content = item.get('content', item)  # Fallback to item itself
            
            # Get title
            title = content.get('title', item.get('title', ''))
            
            # Get publisher
            provider = content.get('provider', {})
            publisher = provider.get('displayName', item.get('publisher', 'Unknown'))
            
            # Get link
            canonical = content.get('canonicalUrl', {})
            link = canonical.get('url', item.get('link', ''))
            
            # Parse timestamp
            pub_date_str = content.get('pubDate', '')
            if pub_date_str:
                try:
                    pub_time = datetime.fromisoformat(pub_date_str.replace('Z', '+00:00'))
                except:
                    pub_time = datetime.now()
            else:
                pub_time = datetime.fromtimestamp(item.get('providerPublishTime', 0))
            
            if title:  # Only add if we have a title
                news.append({
                    'title': title,
                    'publisher': publisher,
                    'link': link,
                    'published': pub_time,
                    'summary': content.get('summary', ''),
                })
            
    except Exception as e:
        print(f"  ⚠️ Error fetching news for {ticker}: {e}")
        
    return news


def analyze_sentiment(text: str) -> Dict:
    """
    Analyze sentiment of text using FinBERT.
    
    Returns:
    {
        'sentiment': 'positive' | 'negative' | 'neutral',
        'confidence': float (0-1),
        'scores': {'positive': float, 'negative': float, 'neutral': float}
    }
    """
    pipe = get_finbert()
    
    if pipe is None:
        return {
            'sentiment': 'neutral',
            'confidence': 0,
            'scores': {'positive': 0.33, 'negative': 0.33, 'neutral': 0.34}
        }
    
    try:
        # Truncate to 512 chars (FinBERT limit)
        text = text[:512]
        
        result = pipe(text)[0]
        
        # Parse scores
        scores = {item['label'].lower(): item['score'] for item in result}
        
        # Determine overall sentiment
        sentiment = max(scores, key=scores.get)
        confidence = scores[sentiment]
        
        return {
            'sentiment': sentiment,
            'confidence': confidence,
            'scores': scores
        }
        
    except Exception as e:
        print(f"  ⚠️ Sentiment analysis error: {e}")
        return {
            'sentiment': 'neutral',
            'confidence': 0,
            'scores': {'positive': 0.33, 'negative': 0.33, 'neutral': 0.34}
        }


def get_ticker_sentiment(ticker: str, max_articles: int = 10) -> Dict:
    """
    Get overall sentiment for a ticker based on recent news.
    
    Returns:
    {
        'ticker': str,
        'overall_sentiment': 'positive' | 'negative' | 'neutral',
        'sentiment_score': float (-1 to 1),
        'num_articles': int,
        'positive_count': int,
        'negative_count': int,
        'neutral_count': int,
        'articles': List[Dict]  # With sentiment for each
    }
    """
    print(f"  📰 Fetching news for {ticker}...")
    news = fetch_news_yfinance(ticker, max_articles)
    
    if not news:
        return {
            'ticker': ticker,
            'overall_sentiment': 'neutral',
            'sentiment_score': 0,
            'num_articles': 0,
            'positive_count': 0,
            'negative_count': 0,
            'neutral_count': 0,
            'articles': [],
            'error': 'No news found'
        }
    
    print(f"  🧠 Analyzing {len(news)} articles with FinBERT...")
    
    analyzed_articles = []
    positive_count = 0
    negative_count = 0
    neutral_count = 0
    total_score = 0
    
    for article in news:
        sentiment = analyze_sentiment(article['title'])
        
        article['sentiment'] = sentiment['sentiment']
        article['sentiment_confidence'] = sentiment['confidence']
        article['sentiment_scores'] = sentiment['scores']
        
        analyzed_articles.append(article)
        
        # Count sentiments
        if sentiment['sentiment'] == 'positive':
            positive_count += 1
            total_score += sentiment['confidence']
        elif sentiment['sentiment'] == 'negative':
            negative_count += 1
            total_score -= sentiment['confidence']
        else:
            neutral_count += 1
    
    # Calculate overall sentiment
    num_articles = len(analyzed_articles)
    sentiment_score = total_score / num_articles if num_articles > 0 else 0
    
    if sentiment_score > 0.2:
        overall = 'positive'
    elif sentiment_score < -0.2:
        overall = 'negative'
    else:
        overall = 'neutral'
    
    return {
        'ticker': ticker,
        'overall_sentiment': overall,
        'sentiment_score': round(sentiment_score, 3),
        'num_articles': num_articles,
        'positive_count': positive_count,
        'negative_count': negative_count,
        'neutral_count': neutral_count,
        'articles': analyzed_articles
    }


def print_sentiment_report(result: Dict):
    """Print a nice sentiment report."""
    print()
    print("=" * 60)
    print(f"  📰 NEWS SENTIMENT: {result['ticker']}")
    print("=" * 60)
    
    # Overall sentiment with emoji
    sentiment = result['overall_sentiment']
    score = result['sentiment_score']
    
    if sentiment == 'positive':
        emoji = '🟢'
    elif sentiment == 'negative':
        emoji = '🔴'
    else:
        emoji = '🟡'
    
    print(f"\n  {emoji} Overall: {sentiment.upper()} (score: {score:+.2f})")
    print(f"  📊 Articles: {result['num_articles']} analyzed")
    print(f"     • Positive: {result['positive_count']}")
    print(f"     • Negative: {result['negative_count']}")
    print(f"     • Neutral:  {result['neutral_count']}")
    
    # Show individual articles
    if result['articles']:
        print(f"\n  📰 Recent Headlines:")
        for article in result['articles'][:5]:
            sent = article['sentiment']
            if sent == 'positive':
                icon = '🟢'
            elif sent == 'negative':
                icon = '🔴'
            else:
                icon = '🟡'
            
            title = article['title'][:60] + '...' if len(article['title']) > 60 else article['title']
            print(f"     {icon} {title}")
    
    print()
    print("=" * 60)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="News Sentiment Analysis")
    parser.add_argument("ticker", help="Stock ticker to analyze")
    parser.add_argument("--articles", "-n", type=int, default=10, help="Number of articles")
    
    args = parser.parse_args()
    
    result = get_ticker_sentiment(args.ticker.upper(), args.articles)
    print_sentiment_report(result)

