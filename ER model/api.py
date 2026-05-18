from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import uuid
import re
import os

from models import entity_extraction, relation_extraction, predict_cardinality

app = FastAPI(title="ER Diagram API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Request / Response Models ────────────────────────────────────────────────

class GenerateERRequest(BaseModel):
    prompt: str
    file_ids: List[str] = []

class ExportERRequest(BaseModel):
    entities: List[dict]
    relationships: List[dict]
    format: str

class ChatRequest(BaseModel):
    prompt: str
    file_ids: List[str] = []
    session_id: Optional[str] = None

# ─── Helpers ──────────────────────────────────────────────────────────────────

def deduplicate_preserve_order(items: List[str]) -> List[str]:
    seen = set()
    result = []
    for item in items:
        key = item.lower()
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result

def build_attributes(entity_name: str) -> List[dict]:
    attrs: List[dict] = []
    # Primary key
    attrs.append({"id": str(uuid.uuid4()), "name": f"{entity_name}_ID", "type": "INT", "isPrimary": True})
    return attrs

# ─── ER Diagram Generate ──────────────────────────────────────────────────────

@app.post("/er-diagram/generate")
def generate_er_diagram_endpoint(req: GenerateERRequest):
    text = req.prompt.strip()

    # 1. Run all three NLP models on this prompt
    raw_entities = entity_extraction(text)
    relation     = relation_extraction(text)
    cardinality  = predict_cardinality(text)

    # 2. Clean & deduplicate
    cleaned = [
        e for e in raw_entities
        if re.match(r"^[A-Za-z][A-Za-z0-9_\-]*$", e) and len(e) > 1
    ]
    entities_list = deduplicate_preserve_order(cleaned)
    
    # 2.5 Fallback Rule-Based Extraction if ML model fails to find 2 entities
    if len(entities_list) < 2:
        stop_words = {
            'a','an','the','is','are','was','were','be','been','being','have','has','had',
            'do','does','did','will','would','could','should','may','might','shall','can',
            'to','of','in','for','on','with','at','by','from','up','about','into',
            'that','this','these','those','it','its','and','or','but','if','then','than',
            'so','both','either','neither','not','also','just','very','quite','only',
            'need','must','each','every','any','all','most','more','some','such','no',
            'many','multiple','several','various','few','one',
            # Common verbs
            'enroll','enrolls','enrolled','work','works','belong','belongs','manage','manages',
            'use','uses','contain','contains','include','includes','teach','teaches','taught',
            'assign','assigns','assigned','place','places','order','orders','buy','buys',
            'bought','sell','sells','sold','own','owns','employ','employs','hire','hires',
            'treat','treats','write','writes','wrote','publish','publishes','attend','attends',
            'register','registers','submit','submits','supply','supplies','support','supports',
            'create','creates','produce','produces','rent','rents','borrow','borrows','lend','lends'
        }
        words = re.sub(r'[^\w\s]', '', text.lower()).split()
        candidates = []
        for w in words:
            if len(w) > 2 and w not in stop_words:
                candidates.append(w)
        
        candidates = deduplicate_preserve_order(candidates)
        # Merge the ML entities with the rule-based ones
        for c in candidates:
            if c not in [e.lower() for e in entities_list]:
                entities_list.append(c)

    # 3. Guard — fallback to generic entities if needed
    e1_name = entities_list[0].capitalize() if len(entities_list) > 0 else "Entity1"
    e2_name = entities_list[1].capitalize() if len(entities_list) > 1 else "Entity2"
    rel_name = relation.replace("_", " ").capitalize()

    e1_id  = str(uuid.uuid4())
    e2_id  = str(uuid.uuid4())
    rel_id = str(uuid.uuid4())

    entities = [
        {
            "id": e1_id,
            "name": e1_name,
            "attributes": build_attributes(e1_name),
            "position": {"x": 100, "y": 220},
        },
        {
            "id": e2_id,
            "name": e2_name,
            "attributes": build_attributes(e2_name),
            "position": {"x": 560, "y": 220},
        },
    ]

    relationships = [
        {
            "id": rel_id,
            "source": e1_id,
            "target": e2_id,
            "label": rel_name,
            "cardinality": cardinality,
        }
    ]

    content = (
        f"Here is the ER diagram generated from your prompt:\n\n"
        f"**Entities detected:** {e1_name}, {e2_name}\n"
        f"**Relationship:** {rel_name}\n"
        f"**Cardinality:** {cardinality}"
    )

    return {
        "message_id": str(uuid.uuid4()),
        "content": content,
        "er_diagram": {
            "type": "json",
            "data": "{}",
            "entities": entities,
            "relationships": relationships,
        },
    }

# ─── ER Diagram Export ────────────────────────────────────────────────────────

@app.post("/er-diagram/export")
def export_er_diagram_endpoint(req: ExportERRequest):
    if req.format == "json":
        return JSONResponse(content={"entities": req.entities, "relationships": req.relationships})

    try:
        from graphviz import Digraph
    except ImportError:
        return JSONResponse(status_code=500, content={"message": "Graphviz not installed on server."})

    dot = Digraph()
    dot.attr(rankdir="LR", bgcolor="white")

    id_to_name: dict = {}
    for ent in req.entities:
        name = ent.get("name", "Unknown")
        id_to_name[ent["id"]] = name
        dot.node(name, shape="box", style="filled", fillcolor="white", fontname="Helvetica")
        for attr in ent.get("attributes", []):
            attr_label = attr.get("name", "")
            attr_id    = attr.get("id", str(uuid.uuid4()))
            shape = "ellipse"
            if attr.get("isPrimary"):
                attr_label = f"<u>{attr_label}</u>"
                dot.node(attr_id, label=f"<{attr_label}>", shape=shape, fontname="Helvetica")
            else:
                dot.node(attr_id, label=attr_label, shape=shape, fontname="Helvetica")
            dot.edge(name, attr_id)

    for rel in req.relationships:
        src = id_to_name.get(rel.get("source", ""), "")
        tgt = id_to_name.get(rel.get("target", ""), "")
        label = rel.get("label", "relation")
        card  = rel.get("cardinality", "")
        rid = rel.get("id", str(uuid.uuid4()))
        dot.node(rid, label=label, shape="diamond", fontname="Helvetica")
        if src:
            dot.edge(src, rid)
        if tgt:
            dot.edge(rid, tgt, label=card)

    filename = f"/tmp/er_{uuid.uuid4().hex}"
    fmt = req.format if req.format in ("svg", "png", "pdf") else "png"
    try:
        out = dot.render(filename, format=fmt, cleanup=True)
        media = "image/svg+xml" if fmt == "svg" else f"image/{fmt}"
        return FileResponse(out, media_type=media, filename=f"er_diagram.{fmt}")
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": f"Graphviz render failed: {str(e)}"})

# ─── Save ─────────────────────────────────────────────────────────────────────

class SaveERRequest(BaseModel):
    entities: List[dict]
    relationships: List[dict]
    session_id: Optional[str] = None

@app.post("/er-diagram/save")
def save_er_diagram_endpoint(req: SaveERRequest):
    # In production this would persist to DB; for now acknowledge success
    return {"message": "Diagram saved successfully.", "diagram_id": str(uuid.uuid4())}

# ─── Chat fallback ────────────────────────────────────────────────────────────

@app.post("/chat")
def chat_endpoint(req: ChatRequest):
    return {
        "message_id": str(uuid.uuid4()),
        "content": (
            f"You said: \"{req.prompt}\"\n\n"
            "Switch to **ER Model** mode and describe your domain — "
            "e.g. *\"A student can enroll in many courses\"* — "
            "to generate an ER diagram automatically."
        ),
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
