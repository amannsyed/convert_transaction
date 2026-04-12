import io
import logging
import sys
from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from typing import Optional
import pandas as pd

from parsers import AmexParser, BankOfScotlandParser, RevolutParser, StarlingParser, MockParser, MonzoParser, StandardParser
from api import router as finance_router

# Robust logging for production (Render)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("bank-converter")

app = FastAPI(title="Bank CSV Converter API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://amannsyed.github.io"],
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

app.include_router(finance_router)

PARSERS_MAP = {
    "amex": AmexParser,
    "bank of scotland": BankOfScotlandParser,
    "revolut": RevolutParser,
    "starling": StarlingParser,
    "mock": MockParser,
    "monzo": MonzoParser,
    "standard": StandardParser
}

@app.post("/convert")
async def convert_csv(
    file: UploadFile = File(...), 
    bank: Optional[str] = Form(None), 
    output_format: Optional[str] = Form(None),
    q_bank: Optional[str] = Query(None, alias="bank"),
    q_output_format: Optional[str] = Query(None, alias="output_format")
):
    final_format = (output_format or q_output_format or "json").strip().lower().strip('"')
    final_bank = (bank or q_bank)
    if final_bank: final_bank = final_bank.strip().lower().strip('"')
    filename = file.filename or "statement.csv"

    if final_format not in {"json", "csv"}:
        raise HTTPException(status_code=400, detail="Unsupported output_format. Use 'json' or 'csv'.")

    logger.info(f"Received request to convert statement: {filename} (Format: {final_format})")
    
    if not filename.lower().endswith('.csv') and not filename.lower().endswith('.txt'):
        logger.warning(f"Rejected file {filename}: not a CSV or TXT format.")
        raise HTTPException(status_code=400, detail="Uploaded file must be a CSV or TXT")

    try:
        content = await file.read()
        
        # Detect encoding and handle BOM
        import charset_normalizer
        results = charset_normalizer.from_bytes(content).best()
        encoding = results.encoding if results else 'utf-8'
        
        # Fast separator sniffing
        sample = content[:4096]
        delimiter = ','
        if sample.count(b'\t') > sample.count(b','):
            delimiter = '\t'
        elif sample.count(b';') > sample.count(b','):
            delimiter = ';'
            
        logger.debug(f"Loading CSV with encoding: {encoding}, delimiter: {delimiter}")
        
        df = pd.read_csv(io.BytesIO(content), sep=delimiter, encoding=encoding)
        
        # Strip whitespace and hidden characters from column names
        df.columns = [str(c).strip().replace('\ufeff', '') for c in df.columns]
        detected_cols = [c.lower() for c in df.columns]
        
        logger.debug(f"Cleaned columns detected: {detected_cols}")
        
        selected_parser = None
        
        if final_bank:
            logger.info(f"User explicitly specified bank format: {final_bank}")
            target_parser_class = PARSERS_MAP.get(final_bank)
            
            if not target_parser_class:
                logger.warning(f"Explicit format '{final_bank}' requested but not supported.")
                raise HTTPException(status_code=400, detail=f"Unsupported format: '{final_bank}'.")
                
            if not target_parser_class.can_handle(df.columns.tolist()):
                logger.warning(f"Explicit format '{final_bank}' rejected: signature mismatch for columns {df.columns.tolist()}")
                raise HTTPException(status_code=400, detail=f"The provided CSV does not match the expected format for '{final_bank}'.")
            else:
                 selected_parser = target_parser_class
        else:
            logger.debug("No bank format specified. Attempting auto-detection.")
            for parser_name, parser in PARSERS_MAP.items():
                if parser.can_handle(df.columns.tolist()):
                    logger.info(f"Auto-detection matched format: {parser_name}")
                    selected_parser = parser
                    break
                    
            if not selected_parser:
                 logger.error(f"Auto-detection failed for columns: {df.columns.tolist()}")
                 raise HTTPException(status_code=400, detail="This bank formatting is not available.")
                 
        logger.info(f"Executing parser {selected_parser.__name__} on {len(df)} rows.")
        records = selected_parser.parse(df)
        
        logger.info(f"Successfully parsed {len(records)} internal standard records.")
        
        if final_format == "csv":
            out_df = pd.DataFrame(records)
            csv_str = out_df.to_csv(index=False)
            return Response(
                content=csv_str,
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=converted_{filename}"}
            )
            
        return {"data": records}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Fatal error processing CSV: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing CSV: {str(e)}")

@app.get("/")
@app.head("/")
def read_root():
    return {"message": "Bank CSV Converter API is running. POST to /convert with a CSV file."}
