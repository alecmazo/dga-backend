import os
import requests  # For direct API calls
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, RedirectResponse  # For HTML and redirect
import yfinance as yf  # For stock prices
from datetime import datetime
from functools import lru_cache  # Caches results for the day

app = FastAPI()

# Get your xAI API key from environment
api_key = os.getenv("XAI_API_KEY")
if not api_key:
    api_key = "fallback-dummy-key"  # For testing; replace in Vercel

# Your stock portfolio - edit this list!
portfolio = ["TSLA", "INTC", "FNMAS", "IBRX"]

@lru_cache(maxsize=1)  # Caches the analyses
def get_daily_analyses():
    try:
        # Fetch stock data
        stock_data = {}
        for ticker in portfolio:
            try:
                info = yf.Ticker(ticker).info
                stock_data[ticker] = {
                    "price": info.get("regularMarketPrice", "N/A"),
                    "change": info.get("regularMarketChangePercent", "N/A")
                }
            except Exception as e:
                stock_data[ticker] = {"price": "N/A", "change": "N/A"}

        summary = "\n".join([f"{ticker}: Price ${data['price']}, Change {data['change']}%" 
                             for ticker, data in stock_data.items()])

        analyses = {}
        agents = {
            "Warren Buffett": "You are Warren Buffett, a value investor focused on long-term holdings, economic moats, and buying wonderful companies at fair prices. Analyze the portfolio's overall value, risks, and buy/hold/sell advice based on fundamentals.",
            "Michael Burry": "You are Michael Burry, a contrarian value investor who spots bubbles and asymmetries. Provide a skeptical analysis of the portfolio, highlighting overvaluations, macroeconomic risks, and opportunistic buys.",
            "Andreessen Horowitz": "You are an analyst from Andreessen Horowitz, emphasizing tech growth, innovation, and scalability. Evaluate the portfolio for disruptive potential, network effects, and high-growth opportunities in public equities.",
            "Elon Musk": "You are Elon Musk, a visionary entrepreneur focused on groundbreaking tech, sustainability, and bold risks. Assess the portfolio for innovative edges, future-proofing, and moonshot potential."
        }

        for agent, prompt in agents.items():
            try:
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                body = {
                    "model": "grok-4",
                    "messages": [
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": f"Today's date: {datetime.now().date()}. Portfolio summary: {summary}. Provide a concise daily analysis (200-300 words) from your perspective."}
                    ]
                }
                response = requests.post("https://api.x.ai/v1/chat/completions", headers=headers, json=body, timeout=10)
                response.raise_for_status()  # Raise if not 200
                response_json = response.json()
                analyses[agent] = response_json['choices'][0]['message']['content']
            except Exception as e:
                analyses[agent] = f"Error generating {agent}'s analysis: {str(e)}"

        return analyses

    except Exception as e:
        return {"Error": f"Failed to generate analyses: {str(e)}"}

@app.get("/widget", response_class=HTMLResponse)
def widget():
    analyses = get_daily_analyses()
    today = datetime.now().date()

    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; padding: 15px; background: #f8f9fa; }}
            h2 {{ color: #2c3e50; }}
            h3 {{ color: #34495e; border-bottom: 1px solid #ddd; padding-bottom: 5px; }}
            p {{ line-height: 1.6; }}
            .agent {{ margin-bottom: 25px; background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
        </style>
    </head>
    <body>
        <h2>Daily Portfolio Analyses - {today}</h2>
    """

    if "Error" in analyses:
        html += f"<p style='color:red;'>{analyses['Error']}</p>"
    else:
        for agent, text in analyses.items():
            html += f"""
            <div class="agent">
                <h3>{agent}'s View</h3>
                <p>{text.replace('\n', '<br>')}</p>
            </div>
            """

    html += "</body></html>"
    return HTMLResponse(content=html, media_type="text/html")

@app.get("/", response_class=RedirectResponse)
def root():
    return "/widget"