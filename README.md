# Entity Relationship Architect

**Entity Relationship Architect** is an autonomous pipeline and web application designed to instantly transform unstructured inputs—such as natural language and flat database exports—into structured Entity-Relationship (ER) diagrams and production-ready SQL schemas. 

This repository serves as a core module within the broader **Enhanced Hybrid AI-Driven Database Engine** project, bridging the gap between raw data requirements and standardized database architecture.

## Overview

Designing a database schema traditionally requires manual interpretation of business logic and meticulous diagramming. This application automates the process using a natural language processing (NLP) pipeline. Users can supply plain English requirements or upload existing database files (CSV, Excel, PDF), and the system will automatically extract entities, infer foreign key relationships, and render a comprehensive architectural diagram.

### Key Capabilities

* **Multi-Format Ingestion:** Supports direct uploads of organizational requirements (PDF) or raw tabular data (CSV, XLSX). 
* **Intelligent Schema Inference:** Automatically analyzes column headers and foreign key naming conventions across multiple uploaded datasets to autonomously map relationships without requiring explicit instructions.
* **Natural Language Processing:** Leverages `spaCy` to parse contextual prompts, identifying complex cardinalities (One-to-One, One-to-Many, Many-to-Many).
* **Automated Visualization:** Generates standardized Chen notation ER diagrams dynamically using `Graphviz`.
* **SQL Generation:** Translates the inferred conceptual models directly into standardized, production-ready DDL (Data Definition Language) statements.

## Technical Architecture

The module is built on a modular, multi-stage processing pipeline:

1. **Input Processor:** Normalizes text encodings, standardizes abbreviations, and segments semantic phrases.
2. **NLP Extractor:** Utilizes part-of-speech tagging and dependency parsing to classify nouns as entities and associate properties as attributes.
3. **Relationship Engine:** Applies deterministic heuristic patterns to extract cardinalities and automatically constructs junction tables for complex many-to-many associations.
4. **Model Builder:** Synthesizes the extracted components into a canonical JSON graph structure.
5. **Generators:** Renders the JSON graph into graphical diagrams (`Graphviz`) and textual SQL schemas.

## Tech Stack

* **Frontend:** Streamlit
* **Backend Pipeline:** Python 3.9+, FastAPI (API Layer)
* **Natural Language Processing:** spaCy (`en_core_web_sm`)
* **Document Extraction:** pdfplumber, Pandas, OpenPyXL
* **Diagram Rendering:** Graphviz

## Local Development Setup

To run this application locally, ensure you have Python 3.9+ and the system-level Graphviz binary installed.

```bash
# 1. Clone the repository
git clone https://github.com/anupam-codespace/hybrid-ai-schema-architect.git
cd hybrid-ai-schema-architect

# 2. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install Python dependencies
pip install -r requirements.txt
python -m spacy download en_core_web_sm

# 4. Run the application
streamlit run app.py
```

## Production Deployment

This application is configured for seamless deployment on Linux-based cloud platforms (e.g., Streamlit Community Cloud). The repository includes a `packages.txt` file, ensuring that the required system-level dependencies (`graphviz`) are installed natively in the container runtime prior to execution.
