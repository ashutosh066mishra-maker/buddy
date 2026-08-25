import requests
try:
    res = requests.post("http://127.0.0.1:8000/analyze-expenses/", data={"user_prompt": "hello"})
    print("Status:", res.status_code)
    print("Text:", res.text[:200])
except Exception as e:
    print("Error:", e)
