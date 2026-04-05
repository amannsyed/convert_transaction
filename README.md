# Bank CSV Conversion API & Finance Flow Backend

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

## Installation & Local Development

1. **Prerequisites**: Python 3.9+
2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Running the API locally**:
   ```bash
   uvicorn main:app --reload
   ```
   The server will start at `http://127.0.0.1:8000`.

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
