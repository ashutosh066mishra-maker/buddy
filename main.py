import os
import json
import io
import threading
import webbrowser
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, File, UploadFile, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse, RedirectResponse
from pydantic import BaseModel, Field
from typing import List, Optional
from dotenv import load_dotenv
from langchain_core.output_parsers import JsonOutputParser
from google import genai
from google.genai import types

load_dotenv()

import langchain
from langchain_community.cache import SQLiteCache
langchain.llm_cache = SQLiteCache(database_path=".langchain.db")

import tempfile
import urllib.request
import xml.etree.ElementTree as ET
import pandas as pd
import yfinance as yf
import requests
from ddgs import DDGS
import wikipedia
import datetime
from googlesearch import search as google_search
from bs4 import BeautifulSoup
import trafilatura
from urllib.parse import urljoin
try:
    from PIL import Image
except ImportError:
    Image = None

try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

# Set the Gemini API key
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("Gemini API key not provided. Please set the GEMINI_API_KEY environment variable.")

genai_client = genai.Client(api_key=GEMINI_API_KEY)
uploaded_10k_file = None

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Add CORS middleware to avoid "Failed to fetch" errors if accessed via localhost vs 127.0.0.1
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files to serve the frontend
if not os.path.exists("static"):
    os.makedirs("static")
app.mount("/static", StaticFiles(directory="static", html=True), name="static")

@app.get("/")
def read_root():
    return RedirectResponse(url="/static/index.html")

def extract_chart_data(df):
    chart_data = {}
    
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    cat_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
    date_cols = [c for c in df.columns if 'date' in c.lower() or 'time' in c.lower()]
    
    if numeric_cols:
        primary_num = numeric_cols[0]
        
        chart_data['histogram'] = {
            'labels': [f"Item {i+1}" for i in range(len(df))],
            'values': df[primary_num].tolist(),
            'label': f'Distribution of {primary_num}'
        }
        
        if cat_cols:
            primary_cat = cat_cols[0]
            grouped = df.groupby(primary_cat)[primary_num].sum().reset_index()
            grouped = grouped.sort_values(by=primary_num, ascending=False).head(10)
            
            chart_data['bar'] = {
                'labels': grouped[primary_cat].astype(str).tolist(),
                'values': grouped[primary_num].tolist(),
                'label': f'Total {primary_num} by {primary_cat}'
            }
            chart_data['pie'] = chart_data['bar'] 
        
        if date_cols:
            primary_date = date_cols[0]
            grouped_date = df.groupby(primary_date)[primary_num].sum().reset_index()
            grouped_date = grouped_date.sort_values(by=primary_date)
            
            chart_data['line'] = {
                'labels': grouped_date[primary_date].astype(str).tolist(),
                'values': grouped_date[primary_num].tolist(),
                'label': f'{primary_num} Over Time'
            }
            
    return chart_data

def extract_text_from_pdf(file_contents):
    if PyPDF2 is None:
        return "PyPDF2 is not installed."
    pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_contents))
    text = ""
    for page in pdf_reader.pages:
        extracted = page.extract_text()
        if extracted:
            text += extracted + "\n"
    return text

# --- LangChain JSON Schema ---
class ChartData(BaseModel):
    labels: List[str] = Field(description="List of strings for the categories, items, or dates.")
    values: List[float] = Field(description="List of numbers (floats or integers) for the data values corresponding to each label.")
    label: str = Field(description="A descriptive title for the chart dataset (e.g., 'Monthly Expenses').")

class ChartPayload(BaseModel):
    bar: Optional[ChartData] = Field(None, description="Bar chart data, used for categorical comparisons.")
    pie: Optional[ChartData] = Field(None, description="Pie chart data, used for proportional breakdowns.")
    line: Optional[ChartData] = Field(None, description="Line chart data, used for trends over time.")
    histogram: Optional[ChartData] = Field(None, description="Histogram data, used for distributions.")

chart_parser = JsonOutputParser(pydantic_object=ChartPayload)

# --- Tool Functions for Gemini ---

def get_stock_price(ticker: str) -> str:
    """Gets the current stock or crypto price. Example tickers: AAPL, BTC-USD, TSLA."""
    try:
        stock = yf.Ticker(ticker)
        data = stock.history(period="1d")
        if data.empty:
            return f"Could not find data for ticker {ticker}."
        current_price = data['Close'].iloc[-1]
        currency = stock.info.get('currency', 'USD')
        return f"The current price of {ticker} is {current_price:.2f} {currency}."
    except Exception as e:
        return f"Error fetching stock data: {str(e)}"

def get_company_info(ticker: str) -> str:
    """Gets detailed company information, financial summary, and key statistics for a given stock ticker."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        summary = f"Company: {info.get('longName', ticker)}\n"
        summary += f"Sector: {info.get('sector', 'N/A')} | Industry: {info.get('industry', 'N/A')}\n"
        summary += f"Market Cap: {info.get('marketCap', 'N/A')}\n"
        summary += f"Forward PE: {info.get('forwardPE', 'N/A')}\n"
        summary += f"Dividend Yield: {info.get('dividendYield', 'N/A')}\n"
        summary += f"52 Week High: {info.get('fiftyTwoWeekHigh', 'N/A')} | Low: {info.get('fiftyTwoWeekLow', 'N/A')}\n"
        summary += f"Business Summary: {info.get('longBusinessSummary', 'N/A')[:500]}..."
        return summary
    except Exception as e:
        return f"Error fetching company info: {str(e)}"

def get_exchange_rate(base: str, target: str) -> str:
    """Gets the live currency exchange rate. Example: base='USD', target='EUR'"""
    try:
        url = f"https://api.frankfurter.app/latest?from={base.upper()}&to={target.upper()}"
        response = requests.get(url)
        if response.status_code != 200:
            return f"Error fetching exchange rate. Make sure currency codes are valid (e.g., USD, EUR)."
        data = response.json()
        rate = data['rates'].get(target.upper())
        if not rate:
            return f"Target currency {target} not found."
        return f"The current exchange rate from {base.upper()} to {target.upper()} is {rate}."
    except Exception as e:
        return f"Error fetching exchange rate: {str(e)}"

def get_historical_exchange_rate(base: str, target: str, start_date: str, end_date: str) -> str:
    """Gets historical currency exchange rates over a specific time period. Dates must be in YYYY-MM-DD format."""
    try:
        url = f"https://api.frankfurter.app/{start_date}..{end_date}?from={base.upper()}&to={target.upper()}"
        response = requests.get(url)
        if response.status_code != 200:
            return f"Error fetching historical rates. Make sure dates (YYYY-MM-DD) and currencies are valid."
        data = response.json()
        rates = data.get('rates', {})
        if not rates:
            return f"No historical data found for {base.upper()} to {target.upper()} in that date range."
        
        # To prevent overloading the model with huge responses, we will downsample if the range is large.
        dates = sorted(rates.keys())
        num_days = len(dates)
        
        downsampled_rates = {}
        if num_days > 365 * 2: # More than 2 years of data
            # Return yearly averages or the first available date of each year
            for date in dates:
                year = date[:4]
                if year not in downsampled_rates:
                    downsampled_rates[year] = rates[date][target.upper()]
        elif num_days > 60:
            # Return monthly averages or the first available date of each month
            for date in dates:
                month = date[:7] # YYYY-MM
                if month not in downsampled_rates:
                    downsampled_rates[month] = rates[date][target.upper()]
        else:
            # Return daily
            for date in dates:
                downsampled_rates[date] = rates[date][target.upper()]
                
        # Format output
        output_lines = [f"Historical exchange rates from {base.upper()} to {target.upper()} ({start_date} to {end_date}):"]
        for key, val in downsampled_rates.items():
            output_lines.append(f"{key}: {val}")
            
        return "\n".join(output_lines)
    except Exception as e:
        return f"Error fetching historical exchange rate: {str(e)}"

def search_web(query: str) -> str:
    """Searches the internet for up-to-date information, news, and real-time economic data."""
    try:
        results = DDGS().text(query, max_results=5)
        if not results:
            return "No results found."
        formatted_results = []
        for r in results:
            formatted_results.append(f"Title: {r.get('title')}\nLink: {r.get('href')}\nSummary: {r.get('body')}")
        return "\n\n".join(formatted_results)
    except Exception as e:
        return f"Error performing web search: {str(e)}"

def search_wikipedia(query: str) -> str:
    """Searches Wikipedia for current facts, history, and knowledge about a topic."""
    try:
        # Get the page summary
        return wikipedia.summary(query, sentences=3)
    except wikipedia.exceptions.DisambiguationError as e:
        return f"Topic is too ambiguous. Did you mean: {', '.join(e.options[:5])}?"
    except wikipedia.exceptions.PageError:
        return f"Could not find a Wikipedia page for '{query}'."
    except Exception as e:
        return f"Error fetching Wikipedia data: {str(e)}"

def get_current_news(query: str) -> str:
    """Gets the latest news articles and updates for a topic. Use this to find current events and news."""
    try:
        results = DDGS().news(query, max_results=5)
        if not results:
            return "No news found."
        formatted_results = []
        for r in results:
            formatted_results.append(f"Date: {r.get('date')}\nTitle: {r.get('title')}\nSource: {r.get('source')}\nSummary: {r.get('body')}")
        return "\n\n".join(formatted_results)
    except Exception as e:
        return f"Error fetching news: {str(e)}"

def google_search_realtime(query: str) -> str:
    """Performs a real-time Google search for current facts, data, or info."""
    try:
        res = google_search(query, advanced=True, num_results=5)
        formatted_results = []
        for r in res:
            formatted_results.append(f"Title: {r.title}\nDescription: {r.description}\nURL: {r.url}")
        if not formatted_results:
            return "No results found on Google."
        return "\n\n".join(formatted_results)
    except Exception as e:
        return f"Error performing Google search: {str(e)}"

def scrape_website(url: str) -> str:
    """Scrapes the main text content of any website URL. Use this to read full articles, economic reports, or data pages."""
    try:
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            text = trafilatura.extract(downloaded)
            if text:
                return text[:15000]
        
        # Fallback to BeautifulSoup if trafilatura fails
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        for script in soup(["script", "style"]):
            script.extract()
        return soup.get_text(separator=' ', strip=True)[:15000]
    except Exception as e:
        return f"Failed to scrape website: {str(e)}"

def crawl_website_links(url: str) -> str:
    """Crawls a website URL and returns a list of hyperlinks found on the page. Use this to discover reports or subpages."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            text = a.get_text(strip=True)
            if href.startswith('/'):
                href = urljoin(url, href)
            if text and href.startswith('http'):
                links.append(f"[{text}]({href})")
        
        if not links:
            return "No links found."
        
        # Return unique links up to 50
        unique_links = list(dict.fromkeys(links))
        return "\n".join(unique_links[:50])
    except Exception as e:
        return f"Failed to crawl links: {str(e)}"

def search_arxiv(query: str) -> str:
    """Searches arXiv for academic papers and research on economics, finance, computer science, and quantitative methods."""
    try:
        url = f"http://export.arxiv.org/api/query?search_query=all:{urllib.parse.quote(query)}&start=0&max_results=5"
        response = urllib.request.urlopen(url)
        data = response.read()
        root = ET.fromstring(data)
        
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        results = []
        for entry in root.findall('atom:entry', ns):
            title = entry.find('atom:title', ns).text.replace('\n', ' ')
            summary = entry.find('atom:summary', ns).text.replace('\n', ' ')
            link = entry.find('atom:id', ns).text
            results.append(f"Title: {title}\nLink: {link}\nAbstract: {summary[:500]}...")
            
        if not results:
            return "No academic papers found on arXiv for this query."
        return "\n\n".join(results)
    except Exception as e:
        return f"Error fetching from arXiv: {str(e)}"

def get_macroeconomic_data(country_code: str, indicator: str) -> str:
    """Gets macroeconomic data (GDP, inflation, unemployment) for a country using World Bank API.
    country_code: 3-letter ISO country code (e.g. USA, CHN, GBR)
    indicator: One of 'GDP' (NY.GDP.MKTP.CD), 'INFLATION' (FP.CPI.TOTL.ZG), or 'UNEMPLOYMENT' (SL.UEM.TOTL.ZS).
    """
    indicators = {
        'GDP': 'NY.GDP.MKTP.CD',
        'INFLATION': 'FP.CPI.TOTL.ZG',
        'UNEMPLOYMENT': 'SL.UEM.TOTL.ZS'
    }
    ind = indicators.get(indicator.upper())
    if not ind:
        return f"Unknown indicator. Use GDP, INFLATION, or UNEMPLOYMENT."
    try:
        url = f"https://api.worldbank.org/v2/country/{country_code}/indicator/{ind}?format=json&date=2020:2025"
        response = requests.get(url)
        data = response.json()
        if len(data) > 1 and data[1]:
            results = []
            for item in data[1][:5]:
                if item['value'] is not None:
                    results.append(f"Year {item['date']}: {item['value']}")
            return f"Macro data for {country_code} ({indicator}):\n" + "\n".join(results)
        return f"No data found for {country_code} {indicator}."
    except Exception as e:
        return f"Error fetching macro data: {str(e)}"

def get_treasury_yields() -> str:
    """Gets current US Treasury yields (10-year, 5-year, 2-year)."""
    try:
        tickers = {'10-Year': '^TNX', '5-Year': '^FVX', '2-Year': '^IRX'}
        results = []
        for name, ticker in tickers.items():
            stock = yf.Ticker(ticker)
            data = stock.history(period="1d")
            if not data.empty:
                yield_val = data['Close'].iloc[-1]
                results.append(f"{name} Yield: {yield_val:.3f}%")
        return "US Treasury Yields:\n" + "\n".join(results)
    except Exception as e:
        return f"Error fetching treasury yields: {str(e)}"

def fact_check_claim(claim: str) -> str:
    """Cross-references a specific claim against trusted news sources to verify its truthfulness."""
    try:
        query = f"{claim} fact check Reuters OR AP News OR Bloomberg"
        results = DDGS().text(query, max_results=3)
        if not results:
            return "No fact-checking results found."
        formatted_results = []
        for r in results:
            formatted_results.append(f"Title: {r.get('title')}\nSource Snippet: {r.get('body')}")
        return "Fact Check Results:\n\n" + "\n\n".join(formatted_results)
    except Exception as e:
        return f"Error performing fact check: {str(e)}"

def stream_gemini_response(chat, final_prompt, chart_data=None):
    def event_generator():
        if chart_data:
            yield json.dumps({"type": "charts", "data": chart_data}) + "\n"
        
        try:
            response = chat.send_message_stream(final_prompt)
        except Exception as e:
            yield json.dumps({"type": "text", "chunk": f"\n\n**Error:** {str(e)}"}) + "\n"
            return

        def process_response(resp):
            for chunk in resp:
                try:
                    part = chunk.parts[0] if getattr(chunk, 'parts', None) and len(chunk.parts) > 0 else None
                    fc = getattr(part, 'function_call', None) if part else None
                    
                    if fc and fc.name:
                        func_name = fc.name
                        args = {k: v for k, v in fc.args.items()}
                        
                        status_msgs = {
                            "get_stock_price": "Fetching real-time stock data...",
                            "get_company_info": "Fetching company info...",
                            "get_exchange_rate": "Checking live exchange rates...",
                            "get_historical_exchange_rate": "Fetching historical exchange rates...",
                            "search_web": "Searching the web...",
                            "search_wikipedia": "Searching Wikipedia...",
                            "get_current_news": "Fetching latest news...",
                            "google_search_realtime": "Searching Google...",
                            "scrape_website": "Reading website contents...",
                            "crawl_website_links": "Analyzing website links...",
                            "search_arxiv": "Searching academic papers...",
                            "get_macroeconomic_data": "Fetching macro data from World Bank...",
                            "get_treasury_yields": "Fetching Treasury yields...",
                            "fact_check_claim": "Cross-referencing claims..."
                        }
                        status_msg = status_msgs.get(func_name, f"Executing {func_name}...")
                        yield json.dumps({"type": "status", "message": status_msg}) + "\n"
                        
                        if func_name == "get_stock_price":
                            result = get_stock_price(**args)
                        elif func_name == "get_company_info":
                            result = get_company_info(**args)
                        elif func_name == "get_exchange_rate":
                            result = get_exchange_rate(**args)
                        elif func_name == "get_historical_exchange_rate":
                            result = get_historical_exchange_rate(**args)
                        elif func_name == "search_web":
                            result = search_web(**args)
                        elif func_name == "search_wikipedia":
                            result = search_wikipedia(**args)
                        elif func_name == "get_current_news":
                            result = get_current_news(**args)
                        elif func_name == "google_search_realtime":
                            result = google_search_realtime(**args)
                        elif func_name == "scrape_website":
                            result = scrape_website(**args)
                        elif func_name == "crawl_website_links":
                            result = crawl_website_links(**args)
                        elif func_name == "search_arxiv":
                            result = search_arxiv(**args)
                        elif func_name == "get_macroeconomic_data":
                            result = get_macroeconomic_data(**args)
                        elif func_name == "get_treasury_yields":
                            result = get_treasury_yields(**args)
                        elif func_name == "fact_check_claim":
                            result = fact_check_claim(**args)
                        else:
                            result = "Unknown function"
                        
                        new_resp = chat.send_message_stream(
                            types.Part.from_function_response(
                                name=func_name,
                                response={"result": result}
                            )
                        )
                        yield from process_response(new_resp)
                    else:
                        if chunk.text:
                            yield json.dumps({"type": "text", "chunk": chunk.text}) + "\n"
                except Exception as e:
                    print(f"Stream processing error: {e}")
                    yield json.dumps({"type": "text", "chunk": f"\n\n**Error:** {str(e)}"}) + "\n"

        yield from process_response(response)
                
    return StreamingResponse(event_generator(), media_type="application/x-ndjson")

@app.post("/analyze-expenses/")
def analyze_expenses(file: UploadFile = File(None), user_prompt: str = Form(None), chat_history: str = Form(None)):
    summary = ""
    chart_data = None
    image_content = None
    
    if file is not None and file.filename != "":
        contents = file.file.read()
        if contents:
            file_ext = os.path.splitext(file.filename)[1].lower()
            
            if file_ext == '.csv':
                try:
                    df = pd.read_csv(io.BytesIO(contents))
                    summary = f"Summary Statistics:\n{df.describe().to_string()}\n\nSample Data:\n{df.head(50).to_string()}"
                    chart_data = extract_chart_data(df)
                except Exception:
                    raise HTTPException(status_code=400, detail="Invalid CSV format.")
            elif file_ext == '.txt':
                try:
                    summary = contents.decode('utf-8')
                    summary = summary[:10000]
                except Exception:
                    raise HTTPException(status_code=400, detail="Invalid text file.")
            elif file_ext == '.pdf':
                try:
                    summary = extract_text_from_pdf(contents)
                    summary = summary[:10000]
                except Exception:
                    raise HTTPException(status_code=400, detail="Invalid or unreadable PDF file.")
            elif file_ext in ['.png', '.jpg', '.jpeg']:
                if Image is None:
                    raise HTTPException(status_code=500, detail="Pillow is not installed.")
                try:
                    image_content = Image.open(io.BytesIO(contents))
                except Exception:
                    raise HTTPException(status_code=400, detail="Invalid image file.")
            else:
                raise HTTPException(status_code=400, detail="Unsupported file format.")
    
    # Multimodal Support, Streaming, and Function Calling
    current_time = datetime.datetime.now().strftime("%A, %B %d, %Y %I:%M %p")
    system_context = (
        "You are B-Bv.2 model, the Ultimate Economics and Financial Chatbot powered by Gemini 2.5 Flash. The current date and time is {current_time}. "
        "You have access to extensive research tools including arXiv, World Bank macro data, Treasury yields, and Fact-Checking tools.\n"
        "IMPORTANT: Provide the best possible answer immediately using your tools in one go. "
        "CRITICAL: Give detailed, accurate, but SHORT and CONCISE answers only. Do not provide extended explanations unless the user explicitly asks for them. "
        "CRITICAL: DO NOT ask the user any follow-up or clarifying questions. Instead, give them suggestions for what they can ask further. "
        "Always provide a natural language response summarizing your findings. Do not just output tool calls. "
        "When asked to verify or fact-check claims, explicitly use the `fact_check_claim` tool. "
        "For macroeconomic data like GDP or inflation, use `get_macroeconomic_data`. For bonds, use `get_treasury_yields`. "
        "If a base currency is missing, default to USD.\n\n"
        "DATA VISUALIZATION:\n"
        "If the response contains quantifiable financial data, comparisons, trends, or metrics, you MUST automatically output a clean JSON schema alongside your text response to visualize this data as a chart, EVEN IF the user does not explicitly ask for a chart.\n"
        f"Output formatting instructions:\n{chart_parser.get_format_instructions()}\n"
        "You must output the JSON payload strictly in a markdown block e.g. ```json <json_payload> ```. Always describe the chart in your text."
    )

    config = types.GenerateContentConfig(
        tools=[
            get_stock_price, get_company_info, get_exchange_rate,
            get_historical_exchange_rate, search_web, search_wikipedia,
            get_current_news, google_search_realtime, scrape_website,
            crawl_website_links, search_arxiv, get_macroeconomic_data,
            get_treasury_yields, fact_check_claim
        ],
        system_instruction=system_context
    )
    
    history = []
    if chat_history:
        try:
            history_list = json.loads(chat_history)
            for msg in history_list:
                role = "user" if msg['role'] == "user" else "model"
                content = msg['content']
                # Make sure content is not empty
                if content:
                    history.append(types.Content(role=role, parts=[types.Part.from_text(text=content)]))
        except Exception as e:
            print(f"Failed to parse chat history: {e}")

    if summary:
        if user_prompt and user_prompt.strip():
            final_prompt = f"Here is the document/data provided by the user:\n\n{summary}\n\nThe user's query: '{user_prompt}'\nPlease answer precisely based on the data. Use markdown formatting."
        else:
            final_prompt = f"Here is the document/data provided by the user:\n\n{summary}\n\nPlease analyze this data thoroughly. If it is expense data, suggest savings. If it is general text, provide a helpful summary. Use markdown formatting."
    elif image_content:
        if user_prompt and user_prompt.strip():
            final_prompt = [f"Please analyze this image to answer the user's query: '{user_prompt}'", image_content]
        else:
            final_prompt = ["Please thoroughly analyze this image. If it's a receipt or invoice, summarize the totals and items. Provide your answer beautifully formatted in markdown.", image_content]
    else:
        if user_prompt and user_prompt.strip():
            final_prompt = f"You are B-Bv.2 model, a helpful AI assistant. Please answer: {user_prompt}"
        else:
            raise HTTPException(status_code=400, detail="Please provide a query or attach a supported file.")
            
    try:
        chat = genai_client.chats.create(model='gemini-2.5-flash', config=config, history=history)
        return stream_gemini_response(chat, final_prompt, chart_data)
        
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload_10k/")
def upload_10k(file: UploadFile = File(...)):
    global uploaded_10k_file
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported for 10-K upload.")
    
    contents = file.file.read()
    try:
        # Save to temp file and upload directly to Gemini using File API
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            temp_file.write(contents)
            temp_path = temp_file.name
            
        uploaded_10k_file = genai_client.files.upload(file=temp_path)
        os.remove(temp_path)
        
        return {"message": f"Successfully uploaded {file.filename} natively to Gemini."}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query_10k/")
def query_10k(user_prompt: str = Form(...), chat_history: str = Form(None)):
    global uploaded_10k_file
    try:
        if not uploaded_10k_file:
            def event_generator():
                yield json.dumps({"type": "text", "chunk": "Error: No documents have been ingested yet. Please upload a 10-K document first."}) + "\n"
            return StreamingResponse(event_generator(), media_type="application/x-ndjson")
            
        current_time = datetime.datetime.now().strftime("%A, %B %d, %Y %I:%M %p")
        system_context = (
            "You are Market Analyst Pro, a professional Financial Market Analyst powered by Gemini 2.5 Flash. The current date and time is {current_time}. "
            "You have access to extensive research tools including arXiv, World Bank macro data, Treasury yields, and Fact-Checking tools.\n"
            "IMPORTANT: Provide the best possible answer immediately using your tools in one go. "
            "CRITICAL: Give detailed, accurate, but SHORT and CONCISE answers only. Do not provide extended explanations unless the user explicitly asks for them. "
            "Answer the user's question based strictly and ONLY on the provided SEC 10-K document. "
            "Do not use outside knowledge unless using your tools to fetch current market data. "
            "When you provide an answer based on the document, explicitly cite the document name and page numbers where the information was found.\n\n"
            "BEHAVIORAL INSTRUCTIONS (ONE-SHOT EXECUTION):\n"
            "1. You are explicitly forbidden from asking the user follow-up or clarifying questions. Be conclusive.\n"
            "2. If the answer is in the document, state it immediately. If it is not, you MUST declare 'Information not available in the document' without speculating.\n\n"
            "SMART SUGGESTION ENGINE:\n"
            "You must ALWAYS append a tailored 'Suggested Next Questions' section at the very bottom of your response.\n"
            "Look at the specific document context you just retrieved and dynamically generate 3 high-value, highly relevant follow-up questions that the user might want to ask next based on this specific information.\n"
            "Format this section cleanly using Markdown line breaks and bullet points.\n\n"
            "DATA VISUALIZATION:\n"
            "If the response contains quantifiable financial data, comparisons, trends, or metrics, you MUST automatically output a clean JSON schema alongside your text response to visualize this data as a chart, EVEN IF the user does not explicitly ask for a chart.\n"
            f"Output formatting instructions:\n{chart_parser.get_format_instructions()}\n"
            "You must output the JSON payload strictly in a markdown block e.g. ```json <json_payload> ```. Always describe the chart in your text."
        )

        config = types.GenerateContentConfig(
            tools=[
                get_stock_price, get_company_info, get_exchange_rate,
                get_historical_exchange_rate, search_web, search_wikipedia,
                get_current_news, google_search_realtime, scrape_website,
                crawl_website_links, search_arxiv, get_macroeconomic_data,
                get_treasury_yields, fact_check_claim
            ],
            system_instruction=system_context
        )
        
        history = []
        if chat_history:
            try:
                history_list = json.loads(chat_history)
                for msg in history_list:
                    role = "user" if msg['role'] == "user" else "model"
                    content = msg['content']
                    if content:
                        history.append(types.Content(role=role, parts=[types.Part.from_text(text=content)]))
            except Exception as e:
                print(f"Failed to parse chat history: {e}")

        final_prompt = ["Here is the user's SEC 10-K document. Please answer based strictly on the document context and use your tools if needed.", uploaded_10k_file, user_prompt]

        chat = genai_client.chats.create(model='gemini-2.5-flash', config=config, history=history)
        return stream_gemini_response(chat, final_prompt)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)