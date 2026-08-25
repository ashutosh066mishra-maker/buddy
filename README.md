# Budget Buddy AI 🚀

A modern, multimodal financial assistant powered by FastAPI, Google Gemini, and real-time data APIs. Budget Buddy helps users analyze expenses, track market trends, and gain deep economic insights using a sleek, interactive web interface.

## 🌟 Features

- **Real-Time Data Integration**: Fetches live stock prices, currency exchange rates, and current news using `yfinance` and DuckDuckGo search.
- **Multimodal AI Analysis**: Powered by Google's `gemini-flash-latest` model to analyze text, CSVs, PDFs, and images (like receipts or invoices).
- **Web Scraping & Crawling**: Automatically extracts and summarizes content from web pages and economic reports for comprehensive insights.
- **Interactive UI**: A beautiful, responsive frontend with data visualization (charts) and streaming responses for a seamless user experience.
- **High-Performance Backend**: Built on FastAPI for fast, asynchronous request handling.

## 🛠️ Tech Stack

- **Backend**: Python, FastAPI, Uvicorn
- **AI Model**: Google Generative AI (Gemini Flash)
- **Data APIs**: yfinance, DuckDuckGo Search (DDGS), Wikipedia, Frankfurter (Exchange rates)
- **Data Processing**: Pandas, PyPDF2, Pillow, BeautifulSoup, Trafilatura
- **Frontend**: HTML5, CSS3, Vanilla JavaScript (Chart.js for visualizations)

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- [Google Gemini API Key](https://aistudio.google.com/)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/lakshaytanwar2007/budget-buddy.git
   cd budget-buddy
   ```

2. Create a virtual environment and activate it:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```

3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up your API key:
   Update the `GEMINI_API_KEY` in `main.py` or set it as an environment variable (recommended for production).

5. Run the application:
   ```bash
   python main.py
   ```
   The app will automatically open in your default web browser at `http://127.0.0.1:8000/static/index.html`.

## 📂 Project Structure

- `main.py` - The core FastAPI backend application.
- `/static` - Contains the frontend assets (`index.html`, `style.css`, `app.js`).

## 💡 Usage

1. Open the application in your browser.
2. Type a financial query, stock ticker, or upload a document (CSV, PDF, Image).
3. Budget Buddy AI will instantly analyze the data and stream back comprehensive insights.
