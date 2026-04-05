import os
import json
import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Header, HTTPException, Query, Body
import httpx
from google.oauth2 import service_account
from googleapiclient.discovery import build
import csv
import io
import datetime

logger = logging.getLogger("finance-api")
router = APIRouter(prefix="/api")

HEADERS = ["Date", "Type", "Category", "Amount", "Bank", "Merchant", "Note", "ID"]

def parse_service_account_json(raw_key):
    try:
        if not raw_key: return None
        curr = raw_key.strip()
        # Remove surrounding single quotes if present
        if curr.startswith("'") and curr.endswith("'"):
            curr = curr[1:-1]
        
        # If it's a stringified JSON with escapes, try processing it
        try:
            return json.loads(curr)
        except json.JSONDecodeError:
            # In case it came wrapped in double quotes and escaped
            if curr.startswith('"') and curr.endswith('"'):
                curr = curr[1:-1].encode('utf-8').decode('unicode_escape')
                return json.loads(curr)
            raise
    except Exception as e:
        logger.error(f"Failed to parse GOOGLE_SERVICE_ACCOUNT_JSON: {e}")
        return None

def get_sheets_client(x_sheet_id: Optional[str] = Header(None, alias="x-sheet-id")):
    if not x_sheet_id:
        raise HTTPException(status_code=400, detail="Missing Spreadsheet ID — provide via x-sheet-id header")
    
    raw_key = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not raw_key:
        raise HTTPException(status_code=500, detail="Missing GOOGLE_SERVICE_ACCOUNT_JSON in .env")
        
    service_account_info = parse_service_account_json(raw_key)
    if not service_account_info:
        raise HTTPException(status_code=500, detail="Invalid GOOGLE_SERVICE_ACCOUNT_JSON format in .env. Ensure it is a valid JSON.")
        
    credentials = service_account.Credentials.from_service_account_info(
        service_account_info,
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
    )
    
    sheets = build('sheets', 'v4', credentials=credentials)
    drive = build('drive', 'v3', credentials=credentials)
    return sheets, drive, x_sheet_id

def get_file_metadata(drive, file_id):
    try:
        file_meta = drive.files().get(
            fileId=file_id, 
            fields="id, name, mimeType",
            supportsAllDrives=True
        ).execute()
        return file_meta
    except Exception as e:
        logger.error(f"Error getting file metadata: {e}")
        return None

@router.get("/health")
def health_check():
    email = os.environ.get("GOOGLE_SERVICE_ACCOUNT_EMAIL")
    raw_key = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    
    if raw_key:
        info = parse_service_account_json(raw_key)
        if info:
            email = info.get("client_email", email)
            
    return {
        "status": "ok",
        "env": {
            "email": email,
            "hasKey": bool(raw_key or os.environ.get("GOOGLE_PRIVATE_KEY")),
            "hasSheetId": bool(os.environ.get("GOOGLE_SHEET_ID"))
        }
    }

@router.get("/rates")
async def get_rates(from_currency: str = Query(..., alias="from"), to_currency: str = Query(..., alias="to")):
    from fastapi.responses import JSONResponse
    logger.info(f"Rate conversion requested: {from_currency} -> {to_currency}")
    if not from_currency or not to_currency:
        return JSONResponse(status_code=400, content={"error": "Missing from or to query params"})
        
    # Point directly to the redirect target — skips the 301 hop entirely
    req_url = f"https://api.frankfurter.dev/v1/latest?amount=1&base={from_currency}&symbols={to_currency}"
    logger.info(f"Rate conversion requested: {from_currency} -> {to_currency}")

    try:
        
        async with httpx.AsyncClient(follow_redirects=False, timeout=8.0) as client:
            response = await client.get(
                req_url,
                headers={"User-Agent": "Mozilla/5.0 FinanceFlow/1.0"}
            )
            logger.info(f"Frankfurter Status Code: {response.status_code}")
            logger.debug(f"Redirect history: {response.history}")
            logger.info(f"Frankfurter Response Headers: {response.headers}")
            logger.info(f"Frankfurter Response Body: {response.text}")
            
            if not response.is_success:
                logger.error(f"Frankfurter error {response.status_code}: {response.text}")
                return JSONResponse(
                    status_code=502 if response.status_code in (301, 302, 308) else response.status_code,
                    content={"error": f"Exchange API error {response.status_code}: {response.text}"}
                )
            return response.json()
    except httpx.TimeoutException:
        logger.error("Frankfurter API timed out after 8 seconds")
        return JSONResponse(status_code=504, content={"error": "Exchange API timed out"})
    except Exception as e:
        logger.error(f"Rates Proxy Error: {e}")
        return JSONResponse(status_code=500, content={"error": f"Failed to connect to Exchange API: {str(e)}"})

@router.get("/sheets")
async def get_sheets(x_sheet_id: Optional[str] = Header(None, alias="x-sheet-id")):
    try:
        sheets, drive, spreadsheet_id = get_sheets_client(x_sheet_id)
        metadata = get_file_metadata(drive, spreadsheet_id)

        if metadata and metadata.get('mimeType') == 'text/csv':
            response = drive.files().get_media(
                fileId=spreadsheet_id,
                supportsAllDrives=True
            ).execute()
            csv_data = response.decode('utf-8')
            reader = csv.DictReader(io.StringIO(csv_data))
            return [row for row in reader]

        response = sheets.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range="A:Z"
        ).execute()

        rows = response.get('values', [])
        if not rows:
            return []

        headers = [str(h).strip() for h in rows[0]]
        data = []
        for row in rows[1:]:
            obj = {}
            for index, header in enumerate(headers):
                normalized = header.upper()
                val = row[index] if index < len(row) else ""
                obj[normalized] = val
                if normalized != header:
                    obj[header] = val
            data.append(obj)
            
        return data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"GET Sheets Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sheets")
async def post_sheets(transaction: dict = Body(...), x_sheet_id: Optional[str] = Header(None, alias="x-sheet-id")):
    try:
        sheets, drive, spreadsheet_id = get_sheets_client(x_sheet_id)
        metadata = get_file_metadata(drive, spreadsheet_id)
        
        date_str = transaction.get("date", datetime.datetime.now().isoformat()).split('T')[0]
        new_row = [
            date_str,
            transaction.get("type", ""),
            transaction.get("category", ""),
            transaction.get("amount", ""),
            transaction.get("bank", ""),
            transaction.get("merchant", ""),
            transaction.get("note", ""),
            transaction.get("id", "")
        ]

        if metadata and metadata.get('mimeType') == 'text/csv':
            response = drive.files().get_media(
                fileId=spreadsheet_id,
                supportsAllDrives=True
            ).execute()
            csv_data = response.decode('utf-8')
            
            # Simple append via csv writer
            out = io.StringIO()
            writer = csv.writer(out)
            # if completely empty, write headers
            if not csv_data.strip():
                writer.writerow(HEADERS)
            writer.writerow(new_row)
            
            updated_csv = csv_data + out.getvalue()
            
            media = build('http', 'media').MediaIoBaseUpload(
                io.BytesIO(updated_csv.encode('utf-8')),
                mimetype='text/csv',
                resumable=True
            )
            drive.files().update(
                fileId=spreadsheet_id,
                media_body=media,
                supportsAllDrives=True
            ).execute()
            return {"success": True}

        # Sheets update
        meta = sheets.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range="A1:Z1"
        ).execute()
        
        values = meta.get('values', [])
        if not values:
            sheets.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range="A1",
                valueInputOption="USER_ENTERED",
                body={"values": [HEADERS]}
            ).execute()
        else:
            current_headers = [str(h).upper() for h in values[0] if h]
            if "ID" not in current_headers:
                sheets.spreadsheets().values().update(
                    spreadsheetId=spreadsheet_id,
                    range="A1",
                    valueInputOption="USER_ENTERED",
                    body={"values": [HEADERS]}
                ).execute()

        sheets.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range="A:H",
            valueInputOption="RAW",
            body={"values": [new_row]}
        ).execute()

        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"POST Sheets Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/sheets/{item_id}")
async def delete_sheets(item_id: str, x_sheet_id: Optional[str] = Header(None, alias="x-sheet-id")):
    try:
        sheets, drive, spreadsheet_id = get_sheets_client(x_sheet_id)
        metadata = get_file_metadata(drive, spreadsheet_id)

        if metadata and metadata.get('mimeType') == 'text/csv':
            response = drive.files().get_media(
                fileId=spreadsheet_id,
                supportsAllDrives=True
            ).execute()
            csv_data = response.decode('utf-8')
            
            reader = list(csv.reader(io.StringIO(csv_data)))
            if not reader:
                raise HTTPException(status_code=404, detail="No data found")
                
            id_index = HEADERS.index("ID")
            row_index = -1
            for i, row in enumerate(reader):
                if i > 0 and len(row) > id_index and row[id_index] == item_id:
                    row_index = i
                    break
                    
            if row_index == -1:
                raise HTTPException(status_code=404, detail="Transaction not found")
                
            del reader[row_index]
            
            out = io.StringIO()
            writer = csv.writer(out)
            writer.writerows(reader)
            updated_csv = out.getvalue()
            
            # actually we should import MediaIoBaseUpload from googleapiclient.http
            from googleapiclient.http import MediaIoBaseUpload
            media = MediaIoBaseUpload(
                io.BytesIO(updated_csv.encode('utf-8')),
                mimetype='text/csv',
                resumable=True
            )
            drive.files().update(
                fileId=spreadsheet_id,
                media_body=media,
                supportsAllDrives=True
            ).execute()
            return {"success": True}

        # Google Sheets deletion
        response = sheets.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range="A:Z"
        ).execute()

        rows = response.get('values', [])
        if not rows:
            raise HTTPException(status_code=404, detail="No data found")

        headers = rows[0]
        id_index = -1
        for i, h in enumerate(headers):
            if str(h).upper() == "ID":
                id_index = i
                break
                
        row_index = -1
        if id_index != -1:
            for idx, row in enumerate(rows):
                if idx > 0 and len(row) > id_index and str(row[id_index]) == str(item_id):
                    row_index = idx
                    break

        if row_index == -1:
            for idx, row in enumerate(rows):
                if idx > 0 and item_id in row:
                    row_index = idx
                    break

        if row_index == -1:
            raise HTTPException(status_code=404, detail="Transaction not found in sheet. Try 'Sync All' to refresh.")

        sheets.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={
                "requests": [{
                    "deleteDimension": {
                        "range": {
                            "sheetId": 0,
                            "dimension": "ROWS",
                            "startIndex": row_index,
                            "endIndex": row_index + 1
                        }
                    }
                }]
            }
        ).execute()

        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"DELETE Sheets Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/sheets/batch")
async def put_sheets_batch(transactions: list = Body(...), x_sheet_id: Optional[str] = Header(None, alias="x-sheet-id")):
    try:
        sheets, drive, spreadsheet_id = get_sheets_client(x_sheet_id)
        metadata = get_file_metadata(drive, spreadsheet_id)

        rows = []
        for t in transactions:
            date_str = t.get("date", datetime.datetime.now().isoformat()).split('T')[0]
            rows.append([
                date_str,
                t.get("type", ""),
                t.get("category", ""),
                t.get("amount", ""),
                t.get("bank", ""),
                t.get("merchant", ""),
                t.get("note", ""),
                t.get("id", "")
            ])

        from googleapiclient.http import MediaIoBaseUpload

        if metadata and metadata.get('mimeType') == 'text/csv':
            out = io.StringIO()
            writer = csv.writer(out)
            writer.writerow(HEADERS)
            writer.writerows(rows)
            csv_data = out.getvalue()
            
            media = MediaIoBaseUpload(
                io.BytesIO(csv_data.encode('utf-8')),
                mimetype='text/csv',
                resumable=True
            )
            drive.files().update(
                fileId=spreadsheet_id,
                media_body=media,
                supportsAllDrives=True
            ).execute()
        else:
            sheets.spreadsheets().values().clear(
                spreadsheetId=spreadsheet_id,
                range="A:Z"
            ).execute()
            
            sheets.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range="A1",
                valueInputOption="USER_ENTERED",
                body={"values": [HEADERS] + rows}
            ).execute()

        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch Update Sheets Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/sheets/{item_id}")
async def put_sheets(item_id: str, transaction: dict = Body(...), x_sheet_id: Optional[str] = Header(None, alias="x-sheet-id")):
    try:
        sheets, drive, spreadsheet_id = get_sheets_client(x_sheet_id)
        metadata = get_file_metadata(drive, spreadsheet_id)
        
        date_str = transaction.get("date", datetime.datetime.now().isoformat()).split('T')[0]
        updated_row = [
            date_str,
            transaction.get("type", ""),
            transaction.get("category", ""),
            transaction.get("amount", ""),
            transaction.get("bank", ""),
            transaction.get("merchant", ""),
            transaction.get("note", ""),
            item_id
        ]
        
        from googleapiclient.http import MediaIoBaseUpload

        if metadata and metadata.get('mimeType') == 'text/csv':
            response = drive.files().get_media(
                fileId=spreadsheet_id,
                supportsAllDrives=True
            ).execute()
            csv_data = response.decode('utf-8')
            
            reader = list(csv.reader(io.StringIO(csv_data)))
            id_index = HEADERS.index("ID")
            row_index = -1
            for i, row in enumerate(reader):
                if i > 0 and len(row) > id_index and row[id_index] == item_id:
                    row_index = i
                    break
                    
            if row_index == -1:
                raise HTTPException(status_code=404, detail="Transaction not found")
                
            reader[row_index] = updated_row
            
            out = io.StringIO()
            writer = csv.writer(out)
            writer.writerows(reader)
            updated_csv = out.getvalue()
            
            media = MediaIoBaseUpload(
                io.BytesIO(updated_csv.encode('utf-8')),
                mimetype='text/csv',
                resumable=True
            )
            drive.files().update(
                fileId=spreadsheet_id,
                media_body=media,
                supportsAllDrives=True
            ).execute()
            return {"success": True}

        response = sheets.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range="A:Z"
        ).execute()

        rows = response.get('values', [])
        if not rows:
            raise HTTPException(status_code=404, detail="No data found")

        headers = rows[0]
        id_index = -1
        for i, h in enumerate(headers):
            if str(h).upper() == "ID":
                id_index = i
                break
                
        row_index = -1
        if id_index != -1:
            for idx, row in enumerate(rows):
                if idx > 0 and len(row) > id_index and str(row[id_index]) == str(item_id):
                    row_index = idx
                    break

        if row_index == -1:
            for idx, row in enumerate(rows):
                if idx > 0 and item_id in row:
                    row_index = idx
                    break

        if row_index == -1:
            raise HTTPException(status_code=404, detail="Transaction not found in sheet. Try 'Sync All' to refresh.")

        sheets.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"A{row_index + 1}:H{row_index + 1}",
            valueInputOption="USER_ENTERED",
            body={"values": [updated_row]}
        ).execute()

        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"PUT Sheets Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
