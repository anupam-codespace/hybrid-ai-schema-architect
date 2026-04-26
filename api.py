"""
FastAPI Backend for ER Diagram Generation Module
Exposes a REST API that integrates with the Hybrid AI Database Engine.

Endpoints:
  POST /generate-er    → Full pipeline (JSON + SQL + diagram path)
  POST /generate-json  → JSON only (faster, no diagram)
  GET  /diagram/{name} → Download generated diagram image
  GET  /health         → Health check
"""

import os
import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from er_module.pipeline import ERPipeline

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

OUTPUT_DIR = "./er_outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

app = FastAPI(
    title="ER Diagram Generation API",
    description="Natural language → ER diagram, JSON model, and SQL schema",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Singleton pipeline (loaded once at startup)
pipeline: ERPipeline | None = None


@app.on_event("startup")
async def load_pipeline():
    global pipeline
    pipeline = ERPipeline(output_dir=OUTPUT_DIR)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class ERRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=10,
        example="Student has ID, Name, Email. Course has CID and Title. "
                "One Student can enroll in many Courses."
    )
    output_name: str    = Field("er_diagram", description="Base filename for diagram")
    diagram_format: str = Field("png", pattern="^(png|pdf|svg)$")
    notation: str       = Field("chen", pattern="^(chen|crow)$")
    generate_sql: bool  = True


class ERResponse(BaseModel):
    er_model: dict
    er_json: str
    sql: str | None
    diagram_path: str | None
    warnings: list[str]
    status: str = "success"


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok", "pipeline_ready": pipeline is not None}


@app.post("/generate-er", response_model=ERResponse)
def generate_er(req: ERRequest):
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Pipeline not initialised.")
    try:
        result = pipeline.run(
            user_text=req.text,
            output_name=req.output_name,
            diagram_format=req.diagram_format,
            notation=req.notation,
            generate_sql=req.generate_sql,
            view_diagram=False,
        )
        return ERResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.exception("Unhandled error in /generate-er")
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")


@app.post("/generate-json")
def generate_json_only(req: ERRequest):
    """Faster endpoint — skips diagram rendering, returns ER model + SQL only."""
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Pipeline not initialised.")
    try:
        result = pipeline.run(
            user_text=req.text,
            output_name=req.output_name,
            diagram_format=req.diagram_format,
            generate_sql=req.generate_sql,
            view_diagram=False,
        )
        return {"er_model": result["er_model"], "sql": result["sql"], "warnings": result["warnings"]}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/diagram/{filename}")
def get_diagram(filename: str):
    """Download a previously generated diagram file."""
    safe_name = Path(filename).name  # prevent directory traversal
    file_path = Path(OUTPUT_DIR) / safe_name
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Diagram not found.")
    return FileResponse(str(file_path))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
