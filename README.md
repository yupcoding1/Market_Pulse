# Market-Pulse Microservice

This project is a "Market-Pulse" microservice that analyzes a given stock ticker to determine if its outlook is bullish, bearish, or neutral for the near future. It synthesizes price momentum data and recent news sentiment, feeding them into a Large Language Model (LLM) to generate a concise, data-driven analysis.

## Features

*   **Dual-Signal Analysis**: Combines financial (price momentum) and textual (news sentiment) data for a holistic view.
*   **LLM-Powered Insights**: Uses Google's Gemini 1.5 Flash model to interpret the data and provide a qualitative "pulse" and explanation.
*   **RESTful API**: Exposes a simple and clean `GET /api/v1/market-pulse` endpoint.
*   **Modern Frontend**: A responsive, chat-style React interface with a dark/light theme and data visualizations.
*   **Efficient & Robust Backend**: Built with FastAPI, featuring asynchronous requests, in-memory caching, and solid error handling.
*   **Containerized**: Includes a `Dockerfile` for easy deployment.

## Tech Stack

*   **Backend**: Python 3.10, FastAPI, Uvicorn
*   **Frontend**: React 18, Recharts for charts
*   **LLM**: Google Gemini 1.5 Flash
*   **Data Sources**: Alpha Vantage (Stocks), NewsAPI.org (News)
*   **Key Python Libraries**: `httpx`, `cachetools`, `pandas`, `vader-sentiment`
*   **DevOps**: Docker

## Setup and Running the Application

### Prerequisites

*   Python 3.8+
*   Node.js v16+ and npm
*   Docker (optional, for containerized deployment)

### 1. Environment Setup

API keys are required from the following services:
*   [Alpha Vantage](https://www.alphavantage.co/support/#api-key) (Stock Prices)
*   [NewsAPI.org](https://newsapi.org/register) (News Headlines)
*   [Google AI Studio](https://aistudio.google.com/app/apikey) (Gemini LLM)

**Option A: Local Environment File**

1.  Navigate to the `src` directory.
2.  Create a file named `.env`.
3.  Add your API keys to the `.env` file as follows:

    ```
    STOCK_API_KEY=YOUR_ALPHA_VANTAGE_KEY
    NEWS_API_KEY=YOUR_NEWSAPI_KEY
    GOOGLE_API_KEY=YOUR_GEMINI_KEY
    ```

**Option B: System Environment Variables**

Alternatively, you can set these as system-wide environment variables.

### 2. Backend Setup

1.  **Navigate to the project root.**
2.  **Install Python dependencies:**
    ```bash
    pip install -r src/requirements.txt
    ```
3.  **Run the FastAPI server:**
    ```bash
    uvicorn src.main:app --reload
    ```
    The backend will be available at `http://127.0.0.1:8000`.

### 3. Frontend Setup

1.  **Navigate to the `frontend` directory:**
    ```bash
    cd frontend
    ```
2.  **Install Node.js dependencies:**
    ```bash
    npm install
    ```
3.  **Run the React development server:**
    ```bash
    npm start
    ```
    The frontend will open automatically at `http://localhost:3000`.

### 4. Docker Setup (Optional)

1.  **Ensure Docker Desktop is running.**
2.  **Build the Docker image from the project root:**
    ```bash
    docker build -t market-pulse .
    ```
3.  **Run the container:**
    ```bash
    docker run -p 8000:8000 -e STOCK_API_KEY="YOUR_KEY" -e NEWS_API_KEY="YOUR_KEY" -e GOOGLE_API_KEY="YOUR_KEY" market-pulse
    ```
    Then, start the frontend separately as described in Step 3.

## API Documentation

### `GET /api/v1/market-pulse`

Fetches and analyzes market data for a given stock ticker.

*   **Query Parameter**:
    *   `ticker` (string, required): The stock ticker symbol (e.g., `MSFT`, `AAPL`).
*   **Success Response (200 OK)**:
    Returns a JSON object with the analysis.
*   **Error Responses**:
    *   `404 Not Found`: If the ticker is invalid or no data is found.
    *   `504 Gateway Timeout`: If an upstream API (stock/news) fails to respond.
    *   `500 Internal Server Error`: For other unexpected errors.

#### Sample Request

```bash
curl "http://127.0.0.1:8000/api/v1/market-pulse?ticker=NVDA"
```

#### Sample Response Body

```json
{
  "ticker": "NVDA",
  "as_of": "2025-08-07",
  "momentum": {
    "returns": [0.5, -0.2, 1.1, 0.8, -0.1],
    "simple_score": 2.1,
    "advanced_score": 3.45
  },
  "news": [
    {
      "title": "NVIDIA Announces New GPU Architecture",
      "description": "...",
      "url": "...",
      "sentiment": 0.85
    }
  ],
  "pulse": "bullish",
  "llm_explanation": "The stock shows strong positive momentum with a simple score of 2.1 and is trading 3.45% above its 20-day average. This is supported by highly positive news about its new GPU architecture, indicating a bullish outlook."
}
```

## Design Notes & Trade-offs

*   **Momentum Calculation**: The service calculates two momentum scores:
    1.  **Simple Score**: A straightforward sum of the last 5 daily percentage returns. It's easy to understand but can be noisy.
    2.  **Advanced Score**: The percentage difference between the last closing price and the 20-day Simple Moving Average (SMA). This provides a better sense of the recent trend relative to a medium-term baseline.
*   **News Sentiment**: I used `vaderSentiment` for its simplicity and effectiveness on financial text without needing pre-training. It provides a normalized `compound` score from -1 to 1, which is perfect for feeding into the LLM.
*   **Prompt Engineering**: The prompt sent to Gemini is highly structured. It explicitly provides the ticker, momentum scores, and top 5 news headlines with their sentiment scores. This "few-shot" approach with clear data points helps the LLM generate consistent, data-driven, and relevant explanations.
*   **Caching**: A simple in-memory `TTLCache` with a 10-minute TTL is used to prevent spamming the downstream APIs (Alpha Vantage, NewsAPI, Google) for the same ticker repeatedly. This is a pragmatic choice for a single-instance service. For a scaled-out solution, a distributed cache like Redis would be the next step.
*   **Async Backend**: FastAPI and `httpx` enable asynchronous fetching of stock and news data. This means the two network calls happen concurrently, significantly reducing the total response time compared to a sequential approach.

## Next Steps & Potential Improvements

*   **Unit Tests**: Implement `pytest` tests for the momentum calculation logic and to validate the structure of the prompt sent to the LLM.
*   **CI/CD**: Create a simple GitHub Actions workflow to run linting (e.g., with `ruff`) and execute the unit tests on every push.
*   **Distributed Caching**: For a multi-instance deployment, replace the `TTLCache` with a **Redis** cache to ensure a shared cache state across all replicas.
*   **More Sophisticated Momentum**: Incorporate more advanced indicators like RSI (Relative Strength Index) or MACD (Moving Average Convergence Divergence) for a more nuanced momentum signal.
*   **LLM Response Validation**: Implement stricter validation on the LLM's JSON output, potentially using a library like Pydantic to ensure the `pulse` is one of the three allowed values.
*   **Frontend Polish**: Add loading skeletons in the UI for a smoother perceived performance while the API call is in progress.
