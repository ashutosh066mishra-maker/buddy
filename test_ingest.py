import os
from dotenv import load_dotenv
import google.generativeai as genai
import traceback

load_dotenv()
genai.configure(api_key=os.environ.get('GEMINI_API_KEY'))

from rag_engine import rag_engine_instance

try:
    with open("test.pdf", "wb") as f:
        f.write(b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>\nendobj\n4 0 obj\n<< /Length 21 >>\nstream\nBT\n/F1 12 Tf\n100 700 Td\n(Hello World) Tj\nET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000213 00000 n \ntrailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n283\n%%EOF")

    with open("test.pdf", "rb") as f:
        contents = f.read()

    res = rag_engine_instance.ingest_pdf(contents, "test.pdf")
    print("SUCCESS:", res)
except Exception as e:
    print("ERROR:")
    traceback.print_exc()
