import os
import json
import requests
from datetime import datetime, timedelta
import time

# Define the cache file path
CACHE_FILE = os.path.join(os.path.dirname(__file__), 'news_cache.json')
CACHE_TTL = 3600  # 1 hour

def load_cache():
    """Load the cache from a JSON file."""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading cache: {e}")
    return {}

def save_cache(cache):
    """Save the cache to a JSON file."""
    try:
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache, f)
    except Exception as e:
        print(f"Error saving cache: {e}")

def get_stock_news(stock_codes, api_key, days_back=7, max_results=5, language="en"):
    """
    Fetch news related to specific stocks from the Finlight API.
    
    This version uses a file-based JSON cache to improve performance.
    
    Args:
        stock_codes (list): List of stock codes to fetch news for.
        api_key (str): Finlight API key.
        days_back (int): How many days back to search for news.
        max_results (int): Maximum number of news articles to return.
        language (str): Language of the articles.
        
    Returns:
        list: List of news items (with duplicate titles omitted).
    """
    cache_key = f"{','.join(sorted(stock_codes))}_{days_back}_{max_results}_{language}"
    now = time.time()
    
    # Load existing cache from file.
    cache = load_cache()
    
    if cache_key in cache:
        entry = cache[cache_key]
        if now - entry.get('timestamp', 0) < CACHE_TTL:
            return entry.get('data', [])
    
    # Updated mapping: include Singapore stocks (with .SI), US stocks, ETFs, and Cryptocurrencies.
    stock_mapping = {
        # Singapore Stocks (with .SI)
        'Z74.SI': 'Singtel Singapore',
        'CC3.SI': 'StarHub Singapore',
        'C6L.SI': 'Singapore Airlines',
        '9CI.SI': 'CapitaLand Group',
        'D05.SI': 'DBS Bank Singapore',
        'O39.SI': 'OCBC Singapore',
        'U11.SI': 'UOB Singapore',
        'C52.SI': 'ComfortDelGro Singapore',
        'S63.SI': 'Singapore Technologies Engineering',
        'U96.SI': 'Sembcorp Industries Singapore',
        
        # US Stocks
        'AAPL': 'Apple',
        'MSFT': 'Microsoft',
        'GOOGL': 'Alphabet',
        'AMZN': 'Amazon',
        'TSLA': 'Tesla',
        'NVDA': 'Nvidia',
        'META': 'Meta',
        'NFLX': 'Netflix',
        'BABA': 'Alibaba',
        'JPM': 'JPMorgan Chase',
        'V': 'Visa',
        'DIS': 'Disney',
        'PEP': 'PepsiCo',
        'NKE': 'Nike',
        'UNH': 'UnitedHealth',
        'BAC': 'Bank of America',
        'KO': 'Coca-Cola',
        'CSCO': 'Cisco',
        'ADBE': 'Adobe',
        'INTC': 'Intel',
        'CRM': 'Salesforce',
        'T': 'AT&T',
        'XOM': 'ExxonMobil',
        'PFE': 'Pfizer',
        'ORCL': 'Oracle',
        'WMT': 'Walmart',
        'MCD': "McDonald's",
        'PYPL': 'PayPal',
        'COST': 'Costco',
        'HON': 'Honeywell',
        
        # ETFs
        'SPY': 'SPDR S&P 500 ETF Trust',
        'IVV': 'iShares Core S&P 500 ETF',
        'VTI': 'Vanguard Total Stock Market ETF',
        'VOO': 'Vanguard S&P 500 ETF',
        'QQQ': 'Invesco QQQ Trust',
        'ARKK': 'ARK Innovation ETF',
        'EFA': 'iShares MSCI EAFE ETF',
        'EEM': 'iShares MSCI Emerging Markets ETF',
        'BND': 'Vanguard Total Bond Market ETF',
        'AGG': 'iShares Core U.S. Aggregate Bond ETF',
        
        # Cryptocurrencies
        'bitcoin': 'Bitcoin',
        'ethereum': 'Ethereum',
        'solana': 'Solana',
        'ripple': 'Ripple',
        'cardano': 'Cardano',
        'polkadot': 'Polkadot',
        'litecoin': 'Litecoin',
        'avalanche-2': 'Avalanche',
        'dogecoin': 'Dogecoin',
        'chainlink': 'Chainlink'
    }
    
    search_terms = []
    stock_names = []
    for code in stock_codes:
        if code in stock_mapping:
            search_terms.append(stock_mapping[code])
            stock_names.append(stock_mapping[code])
        else:
            search_terms.append(code)
            stock_names.append(code)
    
    if not search_terms:
        cache[cache_key] = {'timestamp': now, 'data': []}
        save_cache(cache)
        return []
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')
    
    base_url = "https://api.finlight.me/v1/articles/extended"
    headers = {
        "accept": "application/json",
        "X-API-KEY": api_key
    }
    
    all_news = []
    
    for i, search_term in enumerate(search_terms):
        params = {
            "query": search_term,
            "from": start_date_str,
            "to": end_date_str,
            "language": language,
            "pageSize": max_results
        }
        try:
            response = requests.get(base_url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            if 'articles' in data:
                for article in data['articles']:
                    article['stock_name'] = stock_names[i]
                    all_news.append(article)
        except Exception as e:
            print(f"Error fetching news for {search_term}: {e}")
            continue

    all_news.sort(key=lambda x: x.get('publishDate', ''), reverse=True)
    
    seen_titles = set()
    unique_news = []
    for article in all_news:
        title = article.get('title')
        if title and title not in seen_titles:
            unique_news.append(article)
            seen_titles.add(title)
    
    final_news = unique_news[:max_results]
    
    cache[cache_key] = {'timestamp': now, 'data': final_news}
    save_cache(cache)
    
    return final_news
