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

from unittest.mock import patch, MagicMock, AsyncMock

def test_api_health():
    print("Testing /api/health...")
    with patch.dict("os.environ", {"GOOGLE_SERVICE_ACCOUNT_EMAIL": "test@test.com", "GOOGLE_SERVICE_ACCOUNT_JSON": '{"client_email": "mock@test.com"}'}):
        response = client.get("/api/health")
        print("Status:", response.status_code)
        print(json.dumps(response.json(), indent=2))

def test_api_rates():
    print("Testing /api/rates...")
    with patch("api.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"rates": {"USD": 1.1}}
        mock_response.raise_for_status.return_value = None
        mock_client.get.return_value = mock_response
        
        # AsyncMock __aenter__ return value config for async context manager
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        response = client.get("/api/rates?from=EUR&to=USD")
        print("Status:", response.status_code)
        print(json.dumps(response.json(), indent=2))

def test_api_sheets_get():
    print("Testing /api/sheets GET...")
    with patch("api.get_sheets_client") as mock_client_getter, patch("api.get_file_metadata") as mock_metadata:
        mock_sheets = MagicMock()
        mock_drive = MagicMock()
        mock_client_getter.return_value = (mock_sheets, mock_drive, "test-sheet-id")
        
        # Mocking basic spreadsheet response
        mock_metadata.return_value = {"mimeType": "application/vnd.google-apps.spreadsheet"}
        mock_sheets.spreadsheets().values().get().execute.return_value = {
            "values": [
                ["Date", "Type", "Category", "Amount", "Bank", "Merchant", "Note", "ID"],
                ["2024-01-01", "expense", "Groceries", "50", "TestBank", "Store", "", "123"]
            ]
        }
        
        response = client.get("/api/sheets", headers={"x-sheet-id": "test-sheet-id"})
        print("Status:", response.status_code)
        print(json.dumps(response.json(), indent=2))

if __name__ == "__main__":
    test_auto_detect()
    test_specify_bank()
    test_wrong_bank()
    test_default_mock()
    test_monzo()
    test_csv_output()
    test_standard_output()
    test_csv_output_query()
    test_api_health()
    test_api_rates()
    test_api_sheets_get()
