import re
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import os, json, asyncio, datetime
import httpx
from cachetools import TTLCache
import google.generativeai as genai
from dotenv import load_dotenv
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import pandas as pd

load_dotenv()

app = FastAPI()

# Allow CORS for frontend (adjust origins as needed)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"]
)

# Configure API keys from environment
STOCK_API_KEY = os.getenv("STOCK_API_KEY")         # e.g. Alpha Vantage
NEWS_API_KEY = os.getenv("NEWS_API_KEY")           # e.g. NewsAPI
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")       # Gemini API
genai.configure(api_key=GOOGLE_API_KEY)

# In-memory cache for ticker queries (10-minute TTL)
cache = TTLCache(maxsize=100, ttl=600)  # 600 seconds = 10 minutes

@app.get("/api/v1/market-pulse")
async def get_market_pulse(ticker: str = Query(..., min_length=1, max_length=10)):
    ticker = ticker.upper()
    # Check cache first
    if ticker in cache:
        return cache[ticker]

    # 1. Fetch price data
    try:
        stock_url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={ticker}&apikey={STOCK_API_KEY}&outputsize=compact"
        async with httpx.AsyncClient() as client:
            stock_resp = await client.get(stock_url)
        stock_resp.raise_for_status() # Raise an exception for bad status codes
        data = stock_resp.json()
        if "Time Series (Daily)" not in data:
            raise HTTPException(status_code=404, detail="Ticker not found or invalid API key for stock data.")
    except httpx.RequestError as e:
        raise HTTPException(status_code=504, detail=f"Error fetching stock data: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred with stock data: {e}")

    ts = data["Time Series (Daily)"]
    df = pd.DataFrame.from_dict(ts, orient='index')
    df.index = pd.to_datetime(df.index)
    df = df.astype(float)
    df = df.sort_index(ascending=False)

    # Calculate returns and momentum scores
    df['returns'] = df['4. close'].pct_change() * 100
    df = df.dropna()
    returns = df['returns'].head(5).round(2).tolist()
    
    # Simple momentum score
    simple_momentum_score = round(sum(returns), 2) if returns else 0.0

    # Advanced momentum: compare last close to a moving average
    advanced_momentum_score = None
    last_close = df['4. close'].iloc[0]
    if len(df) >= 20:
        sma_20 = df['4. close'].rolling(window=20).mean().iloc[0]
    else:
    # Fallback: use mean of available closes if < 20 days
        sma_20 = df['4. close'].mean()

# Ensure SMA is valid
    if pd.notna(sma_20) and sma_20 > 0:
        advanced_momentum_score = round(((last_close / sma_20) - 1) * 100, 2)
    else:
        advanced_momentum_score = 0.0  # Default fallback

    
    # 2. Fetch latest 5 news headlines+descriptions and analyze sentiment
    headlines = []
    try:
        news_url = f"https://newsapi.org/v2/everything?q={ticker}&pageSize=20&sortBy=publishedAt&apiKey={NEWS_API_KEY}"
        async with httpx.AsyncClient() as client:
            news_resp = await client.get(news_url)
        news_resp.raise_for_status()
        news_data = news_resp.json()
        articles = news_data.get("articles", [])
        
        # Analyze sentiment for each headline
        analyzer = SentimentIntensityAnalyzer()
        for art in articles:
            title = art.get("title", "")
            description = art.get("description", "")
            sentiment = analyzer.polarity_scores(f"{title} {description}")
            headlines.append({
                "title": title, 
                "description": description, 
                "url": art.get("url", ""),
                "sentiment": sentiment['compound'] # Compound score: -1 (neg) to 1 (pos)
            })
        
        # Sort by relevance and sentiment, then take top 5
        headlines.sort(key=lambda x: abs(x['sentiment']), reverse=True)
        headlines = headlines[:5]

    except httpx.RequestError as e:
        # Non-critical, so we can continue without news
        print(f"Could not fetch news: {e}")
    except Exception as e:
        print(f"An unexpected error occurred with news data: {e}")


    # 3. Call LLM (e.g. Gemini) to determine pulse and explanation
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    system_prompt = (
        "You are an expert financial analyst. Your task is to determine the market pulse "
        "(bullish, bearish, or neutral) for a stock based on its recent price momentum and news headlines. "
        "Provide a concise, data-driven explanation for your decision. "
        "Respond in valid JSON format with two keys: 'pulse' and 'explanation'."
    )

    user_prompt = (
        f"Analyze the following data for the stock ticker {ticker}:\n"
        f"- **Price Momentum**:\n"
        f"  - The last 5 daily returns are {returns} (in %).\n"
        f"  - The simple momentum score (sum of returns) is {simple_momentum_score}.\n"
    )
    if advanced_momentum_score is not None:
        user_prompt += f"  - The advanced momentum score (% difference from 20-day SMA) is {advanced_momentum_score}%.\n"
    
    user_prompt += f"- **Recent News with Sentiment Scores**:\n"

    if headlines:
        for i, art in enumerate(headlines, 1):
            user_prompt += f"  {i}. Title: {art['title']} (Sentiment: {art['sentiment']:.2f})\n     Description: {art['description']}\n"
    else:
        user_prompt += "  No news headlines available.\n"
    
    user_prompt += "\nBased on this data, what is the market pulse and why?"

    pulse = "neutral"
    explanation = "Could not determine pulse."
    try:
        full_prompt = [system_prompt, user_prompt]
        llm_resp = await model.generate_content_async(full_prompt)
        # Clean the response to extract JSON
        llm_text = llm_resp.text.strip()
        # Regex to find JSON block, robust to markdown formatting
        json_match = re.search(r'\{.*\}', llm_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            llm_json = json.loads(json_str)
            pulse = llm_json.get("pulse", "neutral").lower()
            explanation = llm_json.get("explanation", "No explanation provided.")
        else:
            explanation = "Could not parse LLM response as JSON."

    except Exception as e:
        explanation = f"Could not get explanation from LLM: {e}"

    result = {
        "ticker": ticker,
        "as_of": datetime.date.today().isoformat(),
        "momentum": {
            "returns": returns, 
            "simple_score": simple_momentum_score,
            "advanced_score": advanced_momentum_score
        },
        "news": headlines,
        "pulse": pulse,
        "llm_explanation": explanation,
    }

    # Store in cache and return
    cache[ticker] = result
    return result
