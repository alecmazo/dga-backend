import os
from fastapi import FastAPI
from fastapi.responses import HTMLResponse  # This lets us return pure HTML
from fastapi.responses import RedirectResponse  # Add this import at the top if not already there
from xai_sdk import Client
from xai_sdk.chat import user, system
import yfinance as yf  # For stock prices
from datetime import datetime
from functools import lru_cache  # Caches results for the day

app = FastAPI()

# Get your xAI API key from environment (set via export in Terminal)
api_key = os.getenv("XAI_API_KEY")
if not api_key:
    api_key = "fallback-dummy-key"  # Or return an error HTML: return "<html><body>API key missing—check Vercel env vars.</body></html>"

client = Client(api_key=api_key, timeout=3600)

# Your stock portfolio - DEFINED HERE! Edit this list as needed. Make sure it's not indented under anything.
portfolio = ["INTC", "TSLA", "MOH", "T", "FNMAS", "CSCO", "HAL", "IBRX", "WFC", "C"]

@lru_cache(maxsize=1)  # Caches the analyses so they don't regenerate on every request
def get_daily_analyses():
    try:
        # Fetch current stock data
        stock_data = {}
        for ticker in portfolio:
            try:
                info = yf.Ticker(ticker).info
                stock_data[ticker] = {
                    "price": info.get("regularMarketPrice", "N/A"),
                    "change": info.get("regularMarketChangePercent", "N/A")
                }
            except Exception as e:
                stock_data[ticker] = {"price": "N/A", "change": "N/A"}  # Fallback on error

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
                chat = client.chat.create(model="grok-4")
                chat.append(system(prompt))
                chat.append(user(f"Today's date: {datetime.now().date()}. Portfolio summary: {summary}. Provide a concise daily analysis (200-300 words) from your perspective."))
                response = chat.sample()
                analyses[agent] = response.content
            except Exception as e:
                analyses[agent] = f"Error generating {agent}'s analysis: {str(e)}"

        return analyses

    except Exception as e:
        return {"Error": f"Failed to generate analyses: {str(e)}"}

@app.get("/widget", response_class=HTMLResponse)
def widget():
    analyses = get_daily_analyses()
    today = datetime.now().date()

    # Build simple HTML
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
    return html

@app.get("/", response_class=RedirectResponse)
def root():
    return "/widget"  # Redirects to /widget automatically

@app.get("/test")
def test():
    return "Hello, this is working!"


#"INTC", "TSLA", "MOH", "T", "FNMAS", "CSCO", "HAL", "IBRX", "WFC", "C"