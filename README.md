# Bank CSV Conversion API & Finance Flow Backend

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-green.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A unified cloud backend orchestrating the **Finance Flow** suite. It provides a lightweight, robust FastAPI wrapper that automatically detects your bank statement's origin (currently supporting **Amex**, **Bank of Scotland**, **Revolut**, **Monzo**, **Starling**, and a **Standard** pass-through) and dynamically converts it into a unified, consolidated schema.

Additionally, this service serves as the core proxy managing active connections to the **Google Sheets API** for statement sync logic and the **Frankfurter API** for live exchange rate calculations for the Finance Flow frontend dashboard.

## Unified Features & API Routes

- **POST `/convert`**: Normalizes local bank CSV definitions.
- **GET `/api/health`**: Diagnostic endpoint fetching current service account credentials.
- **GET `/api/rates`**: Secure proxy handling Frankfurter Exchange Rate conversions cleanly with explicit browser caching prevention and timeout safety.
- **GET, POST, PUT, DELETE `/api/sheets`**: Complete CRUD orchestration to actively sync transactions natively into configured Google Spreadsheets.

---

## Standardized CSV Output Schema
No matter what columns the local bank provides, this tool standardizes records to:
- `Date` (ISO Format: `YYYY-MM-DD`)
- `Type` (`expense` or `income`)
- `Category`
- `Amount` (Strictly positive float)
- `Bank` (e.g., "Amex", "Revolut")
- `Merchant` (e.g., Target, Starbucks)
- `Note`

---

## 🛠️ Tech Stack

| Technology | Purpose |
|---|---|
| [Python 3.9+](https://www.python.org/) | Runtime |
| [FastAPI](https://fastapi.tiangolo.com/) | Web framework & API |
| [Pandas](https://pandas.pydata.org/) | CSV parsing & data manipulation |
| [Google API Client](https://github.com/googleapis/google-api-python-client) | Google Sheets integration |
| [httpx](https://www.python-httpx.org/) | Async HTTP client (Frankfurter API proxy) |
| [Uvicorn](https://www.uvicorn.org/) | ASGI server |

---

## Installation & Local Development

1. **Prerequisites**: Python 3.9+

2. **Clone the repository:**
   ```bash
   git clone https://github.com/amannsyed/convert_transaction.git
   cd convert_transaction
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**
   Create a `.env` file in the root directory:
   ```env
   GOOGLE_SERVICE_ACCOUNT_JSON=<your-service-account-json>
   ```

5. **Running the API locally**:
   ```bash
   uvicorn main:app --reload
   ```
   The server will start at `http://127.0.0.1:8000`.

---

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Google Cloud service account credentials (JSON string) for Sheets integration | For Sheets features |

---

## Transforming a Statement
Upload your bank statement (either `.csv` or `.txt`):
```bash
curl -F "file=@/path/to/statement.csv" http://localhost:8000/convert
```

**Optional Parameters**: 
- `bank`: Explicitly specify the bank format (e.g. `amex`, `bank of scotland`, `revolut`, `starling`, `monzo`, `standard`).
- `output_format`: Use `csv` to get a downloadable CSV file instead of JSON.

Example:
```bash
curl -F "file=@/path/to/statement.csv" -F "bank=starling" -F "output_format=csv" http://localhost:8000/convert > converted.csv
```

## Running the Tests
To verify all parsers against local datasets:
```bash
python tests/test_all.py
```
To test the API endpoints:
```bash
python tests/test_api.py
```

---

## 📁 Project Structure

```text
convert_transaction/
├── parsers/
│   ├── __init__.py             # Parser registry
│   ├── base.py                 # Abstract base parser (Strategy Pattern)
│   ├── amex.py                 # American Express CSV parser
│   ├── bank_of_scotland.py     # Bank of Scotland CSV parser
│   ├── revolut.py              # Revolut CSV parser
│   ├── starling.py             # Starling Bank CSV parser
│   ├── monzo.py                # Monzo CSV parser
│   ├── standard.py             # Standard pass-through parser
│   └── mock_parser.py          # Mock parser for testing
├── tests/
│   ├── data/                   # Test CSV fixtures
│   ├── test_all.py             # Parser validation tests
│   └── test_api.py             # API endpoint tests
├── main.py                     # FastAPI application & routes
├── api.py                      # Finance Flow API routes (Sheets, rates)
├── requirements.txt            # Python dependencies
└── render.yaml                 # Render deployment configuration
```

---

## Deploy to Render

This repository is ready to be deployed on [Render](https://render.com).

1. Create a new **Web Service** on Render.
2. Connect your GitHub/GitLab repository.
3. Render will automatically detect the Python environment.
4. **Build Command**: `pip install -r requirements.txt`
5. **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

---

## How It Works / Adding a New Bank

We use a **Strategy Pattern**. The logic in `main.py` dynamically selects from available subclasses in the `parsers/` directory.

**To add a new bank:**
1. Create a new file in `parsers/` (e.g., `parsers/chase.py`).
2. Implement your logic adhering to `BaseParser`.
3. Add the parser class to `parsers/__init__.py`.
4. Add the parser to `PARSERS_MAP` in `main.py`.

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request or open an Issue.

## 📝 License

MIT
