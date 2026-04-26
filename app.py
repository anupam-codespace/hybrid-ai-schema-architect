"""
Streamlit Web UI for ER Diagram Generation Module
Premium, minimalistic interface for the Enhanced Hybrid AI DB Engine.
"""

import streamlit as st
import os
import io
import pandas as pd
import pdfplumber
from er_module.pipeline import ERPipeline

# ── Page config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ER Diagram Generator",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── Premium Custom CSS ─────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');

  body, .stApp { 
      font-family: 'Inter', sans-serif;
      background-color: #FAFAFA;
      color: #111827;
  }
  
  /* Typography */
  h1 { 
      font-weight: 600 !important; 
      color: #111827 !important;
      letter-spacing: -0.025em;
  }
  h2, h3, h4 { 
      font-weight: 500 !important; 
      color: #374151 !important; 
  }
  
  /* Text Area & Upload Styling */
  .stTextArea textarea { 
      font-size: 15px; 
      border-radius: 8px;
      border: 1px solid #E5E7EB;
      box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
      padding: 1rem;
      transition: all 0.2s ease;
  }
  .stTextArea textarea:focus {
      border-color: #3B82F6;
      box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2);
  }
  
  /* Button Styling */
  .stButton > button {
      border-radius: 6px;
      font-weight: 500;
      transition: all 0.2s ease;
  }
  .stButton > button[kind="primary"] {
      background-color: #111827;
      color: white;
      border: none;
  }
  .stButton > button[kind="primary"]:hover {
      background-color: #374151;
  }
  
  /* Clean up default Streamlit elements */
  #MainMenu {visibility: hidden;}
  footer {visibility: hidden;}
  header {visibility: hidden;}
  
  /* Custom upload area */
  .css-1n76uvr {
      border-radius: 8px;
  }
  
  /* Suggestion buttons */
  .suggestion-btn > button {
      background-color: #F3F4F6 !important;
      color: #374151 !important;
      border: 1px solid #E5E7EB !important;
      font-size: 0.85rem !important;
      text-align: left !important;
      justify-content: flex-start !important;
      padding: 0.5rem 1rem !important;
  }
  .suggestion-btn > button:hover {
      background-color: #E5E7EB !important;
      border-color: #D1D5DB !important;
  }
</style>
""", unsafe_allow_html=True)

# ── Helper Functions ───────────────────────────────────────────────────────

def infer_relationships_from_schema(schema_dict):
    """Infer natural language relationships from column names."""
    sentences = []
    # Create a mapping of lowercase entity names to their correct casing
    entity_map = {e.lower(): e for e in schema_dict.keys()}
    
    for entity, cols in schema_dict.items():
        for col in cols:
            col_lower = col.lower()
            for other_ent_lower, other_ent in entity_map.items():
                if entity.lower() == other_ent_lower:
                    continue
                # Common FK patterns: department_id, departmentid, id_department
                fk_names = [f"{other_ent_lower}_id", f"{other_ent_lower}id", f"id_{other_ent_lower}"]
                if any(fk in col_lower for fk in fk_names):
                    sentences.append(f"Each {entity} belongs to exactly one {other_ent}.")
    
    # Simple de-duplication of sentences
    return " ".join(list(set(sentences)))

def process_uploaded_files(uploaded_files):
    if not uploaded_files:
        return "", []
        
    extracted_text = ""
    detected_entities = []
    schema_dict = {}
    
    for file in uploaded_files:
        ext = os.path.splitext(file.name)[1].lower()
        try:
            if ext == '.pdf':
                with pdfplumber.open(file) as pdf:
                    for page in pdf.pages:
                        extracted = page.extract_text()
                        if extracted:
                            extracted_text += extracted + "\n"
            elif ext == '.csv':
                df = pd.read_csv(file)
                entity_name = os.path.splitext(file.name)[0].capitalize()
                schema_dict[entity_name] = df.columns.tolist()
            elif ext in ['.xlsx', '.xls']:
                xls = pd.ExcelFile(file)
                for sheet_name in xls.sheet_names:
                    df = pd.read_excel(xls, sheet_name=sheet_name)
                    entity_name = sheet_name.capitalize()
                    schema_dict[entity_name] = df.columns.tolist()
        except Exception as e:
            st.error(f"Error reading file {file.name}: {e}")
            
    # Convert structured schemas to natural language
    for ent, cols in schema_dict.items():
        extracted_text += f"{ent} has {', '.join(cols)}.\n"
        detected_entities.append(ent)
        
    # Infer relationships cross-file
    if schema_dict:
        rel_text = infer_relationships_from_schema(schema_dict)
        if rel_text:
            extracted_text += "\n" + rel_text + "\n"
            
    return extracted_text, detected_entities

# ── Header ─────────────────────────────────────────────────────────────────
st.title("Entity Relationship Architect")
st.markdown("<p style='color: #6B7280; font-size: 1.1rem; margin-bottom: 2rem;'>Automatically generate an Entity Relationship diagram from documents and natural language.</p>", unsafe_allow_html=True)

try:
    # ── Main Layout ────────────────────────────────────────────────────────────

    col_input, col_output = st.columns([1, 1.2], gap="large")

    with col_input:
        st.markdown("### 1. Data Source")
        st.markdown("<span style='color: #6B7280; font-size: 0.9rem;'>Upload an organizational document (PDF) or schema definitions (Excel, CSV).</span>", unsafe_allow_html=True)
        uploaded_files = st.file_uploader("Upload Document", type=["pdf", "csv", "xlsx", "xls"], label_visibility="hidden", accept_multiple_files=True)
        
        extracted_text, detected_entities = process_uploaded_files(uploaded_files)
        
        st.markdown("### 2. Context Prompt")
        st.markdown("<span style='color: #6B7280; font-size: 0.9rem;'>Add specific instructions, relationships, or just describe the entire database schema here.</span>", unsafe_allow_html=True)
        
        # Initialize session state for the prompt text
        if "prompt_input" not in st.session_state:
            st.session_state.prompt_input = ""
            
        def populate_prompt(text):
            st.session_state.prompt_input = text

        user_prompt = st.text_area(
            "Schema Description",
            key="prompt_input",
            height=140,
            placeholder="e.g. Employee has ID, Name. Department has DeptID, Name. Employee belongs to Department.",
            label_visibility="hidden"
        )

        # Dynamic suggestions based on file upload
        if uploaded_files:
            st.markdown("<div style='margin-top: 0.5rem; margin-bottom: 0.5rem; color: #6B7280; font-size: 0.85rem; font-weight: 500;'>Suggestions based on your upload:</div>", unsafe_allow_html=True)
            
            has_pdf = any(os.path.splitext(f.name)[1].lower() == '.pdf' for f in uploaded_files)
            suggestions = []
            
            # De-duplicate entities
            detected_entities = list(dict.fromkeys(detected_entities))
            
            if has_pdf:
                suggestions = [
                    "Extract entities and show one-to-many relationships.",
                    "Identify primary keys and many-to-many relationships."
                ]
            elif len(detected_entities) == 1:
                ent = detected_entities[0]
                suggestions = [
                    f"Each {ent} belongs to exactly one Department.",
                    f"One {ent} can have many Records.",
                    f"Many {ent}s can enroll in many Courses."
                ]
            elif len(detected_entities) >= 2:
                ent1, ent2 = detected_entities[0], detected_entities[1]
                suggestions = [
                    f"One {ent1} has many {ent2}s.",
                    f"Each {ent2} belongs to exactly one {ent1}.",
                    f"Many {ent1}s are associated with many {ent2}s."
                ]
                
            for idx, sug in enumerate(suggestions):
                st.markdown('<div class="suggestion-btn">', unsafe_allow_html=True)
                st.button(f"{sug}", key=f"sug_btn_{idx}", on_click=populate_prompt, args=(sug,), use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
                
        st.markdown("<br>", unsafe_allow_html=True)

        col_btn, col_clear = st.columns([2, 1])
        with col_btn:
            run_btn = st.button("Generate Architecture", type="primary", use_container_width=True)
        with col_clear:
            if st.button("Clear Input", use_container_width=True):
                st.session_state.prompt_input = ""
                st.rerun()

    with col_output:
        st.markdown("### Visual Architecture")
        
        if run_btn:
            combined_text = extracted_text + "\n" + user_prompt
            
            if not combined_text.strip():
                st.warning("Please upload a document or provide a schema description.")
            else:
                with st.spinner("Analyzing semantics and generating architecture..."):
                    try:
                        pipeline = ERPipeline(output_dir="./er_outputs")
                        # We only care about the diagram here. SQL and JSON are generated but not displayed.
                        result = pipeline.run(
                            user_text=combined_text,
                            diagram_format="png",
                            notation="chen",
                            generate_sql=False
                        )
                    except Exception as e:
                        st.error(f"Analysis failed: {str(e)}")
                        st.stop()

                # Minimal warnings presentation
                if result.get("warnings"):
                    for w in result["warnings"]:
                        st.info(w)

                if result.get("diagram_path") and os.path.exists(result["diagram_path"]):
                    # Container for diagram
                    st.markdown("<div style='border: 1px solid #E5E7EB; border-radius: 8px; padding: 2rem; background: white; min-height: 400px; display: flex; justify-content: center; align-items: center;'>", unsafe_allow_html=True)
                    st.image(result["diagram_path"], use_container_width=True)
                    st.markdown("</div><br>", unsafe_allow_html=True)
                    
                    with open(result["diagram_path"], "rb") as f:
                        st.download_button(
                            "Download Diagram (PNG)",
                            f,
                            file_name="architecture.png",
                            mime="image/png",
                            type="primary"
                        )
                else:
                    st.info("Visualization unavailable. No valid entities or relationships could be parsed from the input.")
        else:
            # Placeholder before generation
            st.markdown("<div style='border: 1px dashed #E5E7EB; border-radius: 8px; padding: 2rem; background: #FAFAFA; min-height: 400px; display: flex; justify-content: center; align-items: center; color: #9CA3AF; text-align: center;'>Your generated diagram will appear here.</div>", unsafe_allow_html=True)

except Exception as e:
    st.error("An unexpected error occurred during execution.")
    st.exception(e)
