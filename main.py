import io
import logging
from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Query
from fastapi.responses import Response
from typing import Optional
import pandas as pd
import numpy as np

from parsers import AmexParser, BankOfScotlandParser, RevolutParser, StarlingParser, MockParser, MonzoParser, StandardParser

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="Bank CSV Converter API")

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

    logger.info(f"Received request to convert statement: {file.filename} (Format: {final_format})")
    
    if not file.filename.endswith('.csv') and not file.filename.endswith('.txt'):
        logger.warning(f"Rejected file {file.filename}: not a CSV or TXT format.")
        raise HTTPException(status_code=400, detail="Uploaded file must be a CSV or TXT")

    try:
        content = await file.read()
        
        # Fast separator sniffing to avoid engine='python' hanging on large files
        sample = content[:2048]
        delimiter = ','
        if sample.count(b'\t') > sample.count(b','):
            delimiter = '\t'
            
        df = pd.read_csv(io.BytesIO(content), sep=delimiter)
        
        logger.debug(f"Successfully loaded CSV into Pandas using separator '{delimiter}'. Columns detected: {df.columns.tolist()}")
        
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
            filename = file.filename if file.filename else "statement.csv"
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
def read_root():
    return {"message": "Bank CSV Converter API is running. POST to /convert with a CSV file."}
