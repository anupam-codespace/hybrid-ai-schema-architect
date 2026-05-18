# Hybrid AI Schema Architect

**Hybrid AI Schema Architect** is an intelligent, full-stack application that bridges the gap between natural language and database design. By leveraging advanced Machine Learning and NLP (Natural Language Processing), it automatically extracts entities, relationships, and attributes from conversational prompts to generate professional Entity-Relationship (ER) diagrams and SQL schemas.

---

## 🌟 Key Features

* **AI-Powered Schema Generation**: Type a natural language description of your database, and the AI engine will instantly extract the required entities, attributes, and relationships.
* **Interactive ER Diagram Canvas**: A sleek, professional drag-and-drop canvas built with React Flow. Visualize, edit, and export your diagrams in real-time.
* **Custom Attribute Configuration**: Fully edit diagram nodes via an intuitive multi-step wizard. Set precise SQL datatypes (`INT`, `VARCHAR`, `BOOLEAN`, etc.) and define structured vs. unstructured data parameters.
* **Real-time Export**: Export your high-fidelity ER diagrams directly to PNG, SVG, or JSON formats without losing quality.
* **Robust Fallback Engine**: The Python backend utilizes a resilient, rule-based NLP extraction system to ensure highly accurate schema generation even when edge cases are encountered.

---

## 🛠️ Technology Stack

**Frontend (`/Model Ui`)**:
* **Framework**: React (Vite) + TypeScript
* **Styling**: Tailwind CSS & Lucide Icons
* **State Management**: Zustand
* **Visualization**: React Flow

**Backend**:
* **Language**: Python 3.x
* **AI/NLP**: Transformers (Hugging Face), spaCy, and custom NER/Safetensors models
* **Framework**: FastAPI / Flask *(depending on runtime)*

---

## 🚀 Getting Started

### 1. Running the Frontend
The UI is contained within the `Model Ui` repository/folder.

```bash
cd "Model Ui"
npm install
npm run dev
```

### 2. Running the Backend
Ensure you have Python 3.10+ installed.

```bash
# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install requirements
pip install -r requirements.txt

# Run the API server
python app.py  # or the respective entry point
```

> **Note:** The backend requires several pre-trained NLP models. Ensure that your models (e.g., `model.safetensors`, `ner_model.zip`) are placed in the `ER model/` directory before running the server. These files are ignored via `.gitignore` due to their size.

---

## 🤝 Contributing
Contributions, issues, and feature requests are welcome! Feel free to check out the issues page.

## 📝 License
This project is open-source and available under the [MIT License](LICENSE).
