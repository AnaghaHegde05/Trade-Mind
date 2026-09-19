import shutil
import logging
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from pathlib import Path
from backend.config.settings import settings
from backend.utils.auth import verify_api_key

logger = logging.getLogger("trade_intel.routes.datasets")

router = APIRouter(tags=["Datasets"])

TARGET_DIR_MAP = {
    "market": settings.MARKET_DATASET_DIR,
    "demand": settings.DEMAND_DATASET_DIR,
    "pricing": settings.PRICING_DATASET_DIR,
    "logistics": settings.LOGISTICS_DATASET_DIR,
    "tariffs": settings.TARIFFS_DATASET_DIR,
    "risk": settings.RISK_DATASET_DIR,
    "suppliers": settings.SUPPLIERS_DATASET_DIR
}

@router.post("/datasets/upload", response_model=dict)
async def upload_dataset(
    file: UploadFile = File(...),
    dataset_type: str = Form(..., description="Target folder: market, demand, pricing, logistics, tariffs, risk, suppliers"),
    _auth: None = Depends(verify_api_key)
):
    """
    Accepts CSV, XLSX, or JSON files and saves them to the appropriate datasets subfolder.
    """
    dtype = dataset_type.lower().strip()
    if dtype not in TARGET_DIR_MAP:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid dataset_type '{dataset_type}'. Supported: {', '.join(TARGET_DIR_MAP.keys())}"
        )
        
    target_dir = TARGET_DIR_MAP[dtype]
    
    # Check extension
    suffix = Path(file.filename).suffix.lower()
    if suffix not in [".csv", ".xlsx", ".xls", ".json"]:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{suffix}'. Supported: .csv, .xlsx, .xls, .json"
        )
        
    target_path = target_dir / file.filename
    logger.info(f"Saving uploaded file {file.filename} of type {dtype} to {target_path}...")
    
    try:
        with open(target_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        return {
            "filename": file.filename,
            "dataset_type": dtype,
            "status": "UPLOAD_SUCCESS",
            "saved_path": str(target_path)
        }
    except Exception as e:
        logger.error(f"Failed to save file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
