import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from fastapi.testclient import TestClient
from main import app
import json

client = TestClient(app)

def test_auto_detect():
    print("Testing Auto-Detect...")
    with open("tests/data/user_test_format_2.csv", "rb") as f:
        # Bank of scotland format snippet
        response = client.post("/convert", files={"file": ("stmt.csv", f, "text/csv")})
        print("Status:", response.status_code)
        print(json.dumps(response.json(), indent=2))

def test_specify_bank():
    print("Testing Explicit Bank Specification (bank of scotland)...")
    with open("tests/data/user_test_format_2.csv", "rb") as f:
        response = client.post("/convert", files={"file": ("stmt.csv", f, "text/csv")}, data={"bank": "bank of scotland"})
        print("Status:", response.status_code)
        print(json.dumps(response.json(), indent=2))
        
def test_wrong_bank():
    print("Testing Explicit Bank Specification with wrong CSV (amex)...")
    with open("tests/data/user_test_format_2.csv", "rb") as f:
        response = client.post("/convert", files={"file": ("stmt.csv", f, "text/csv")}, data={"bank": "amex"})
        print("Status:", response.status_code)
        print(json.dumps(response.json(), indent=2))

def test_default_mock():
    print("Testing Default Parser (user_test_format_0.csv)...")
    with open("tests/data/user_test_format_0.csv", "rb") as f:
        response = client.post("/convert", files={"file": ("stmt.csv", f, "text/csv")})
        print("Status:", response.status_code)
        print(json.dumps(response.json(), indent=2))

def test_monzo():
    print("Testing Monzo Parser...")
    with open("tests/data/user_test_format_3.csv", "rb") as f:
        response = client.post("/convert", files={"file": ("stmt.csv", f, "text/csv")})
        print("Status:", response.status_code)
        import json
        print(json.dumps(response.json(), indent=2))

def test_csv_output():
    print("Testing CSV Output (user_test_format_3.csv)...")
    with open("tests/data/user_test_format_3.csv", "rb") as f:
        response = client.post("/convert", files={"file": ("stmt.csv", f, "text/csv")}, data={"output_format": "csv"})
        print("Status:", response.status_code)
        print("Headers:", response.headers.get("content-type"))
        print(response.text)

def test_standard_output():
    print("Testing Standard Passthrough Parser...")
    with open("tests/data/user_test_format_1.csv", "rb") as f:
        response = client.post("/convert", files={"file": ("stmt.csv", f, "text/csv")})
        print("Status:", response.status_code)
        import json
        print(json.dumps(response.json(), indent=2))

def test_csv_output_query():
    print("Testing CSV Output via Query Param...")
    with open("tests/data/user_test_format_3.csv", "rb") as f:
        response = client.post("/convert?output_format=csv", files={"file": ("stmt.csv", f, "text/csv")})
        print("Status:", response.status_code)
        print("Headers:", response.headers.get("content-type"))
        print("Content snippit:", response.text[:60])

if __name__ == "__main__":
    test_auto_detect()
    test_specify_bank()
    test_wrong_bank()
    test_default_mock()
    test_monzo()
    test_csv_output()
    test_standard_output()
    test_csv_output_query()
