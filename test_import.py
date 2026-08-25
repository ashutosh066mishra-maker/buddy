import sys

modules_to_test = [
    "os", "json", "io", "threading", "webbrowser", "contextlib",
    "fastapi", "pydantic", "typing", "google.generativeai", "dotenv",
    "langchain_core.output_parsers", "urllib.request", "xml.etree.ElementTree",
    "pandas", "yfinance", "requests", "duckduckgo_search", "wikipedia", "datetime",
    "googlesearch", "bs4", "trafilatura", "urllib.parse", "rag_engine"
]

for mod in modules_to_test:
    print(f"Importing {mod}...")
    try:
        if mod == "duckduckgo_search":
            import duckduckgo_search
        else:
            __import__(mod)
        print(f"Successfully imported {mod}")
    except Exception as e:
        print(f"Failed to import {mod}: {e}")
