import streamlit as st
from models import entity_extraction, relation_extraction, predict_cardinality
from er_utils import generate_fol, generate_er_diagram
import os
os.environ["PATH"] += os.pathsep + r"C:/Program Files/Graphviz\bin"
st.set_page_config(page_title="AI ER Generator", layout="centered")

st.title("🧠 AI ER Diagram Generator")
st.write("Convert Natural Language → FOL → ER Diagram")

# Input
text = st.text_input("Enter your sentence")

if st.button("Generate"):
    if text.strip() == "":
        st.warning("Please enter a sentence")
    else:
        # 🔹 Model outputs
        entities = entity_extraction(text)
        relation = relation_extraction(text)
        card = predict_cardinality(text)

        # 🔹 Split safely
        parts = card.split("_")
        if len(parts) == 2:
            cardinality, participation = parts
        else:
            cardinality = parts[0]
            participation = "partial-partial"

        # 🔹 Generate FOL
        fol_data = generate_fol(entities, relation, cardinality, participation)

        # 🔹 Generate ER Diagram
        image_path = generate_er_diagram(fol_data)

        # 🔹 Display
        st.subheader("📌 Entities")
        st.write(entities)

        st.subheader("🔗 Relation")
        st.write(relation)

        st.subheader("📊 Cardinality")
        st.write(cardinality)

        st.subheader("📐 Participation")
        st.write(participation)

        st.subheader("🧠 FOL Representation")
        st.json(fol_data)

        st.subheader("📊 ER Diagram")
        st.image(image_path)