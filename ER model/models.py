import torch
from transformers import (
    AutoTokenizer,
    AutoModelForTokenClassification,
    AutoModelForSequenceClassification
)

# ================= PATHS =================
NER_MODEL_PATH        = "final_ner_model"
RELATION_MODEL_PATH   = "model file/relation_model"
CARDINALITY_MODEL_PATH = "model file/cardinality_model_final/cardinality_model_final"

# ================= LOAD MODELS =================

# -------- NER (DistilBert Token Classification) --------
ner_tokenizer = AutoTokenizer.from_pretrained("distilbert-base-uncased")
ner_model = AutoModelForTokenClassification.from_pretrained(NER_MODEL_PATH)
ner_model.eval()

# -------- RELATION (DistilBert Sequence Classification) --------
relation_tokenizer = AutoTokenizer.from_pretrained(RELATION_MODEL_PATH)
relation_model = AutoModelForSequenceClassification.from_pretrained(RELATION_MODEL_PATH)
# Override labels to human-readable relation names
relation_model.config.id2label = {
    0: "enrolls",
    1: "has",
    2: "works_on",
    3: "belongs_to",
    4: "manages",
    5: "uses"
}
relation_model.config.label2id = {v: k for k, v in relation_model.config.id2label.items()}
relation_model.eval()

# -------- CARDINALITY (DistilBert Sequence Classification) --------
card_tokenizer = AutoTokenizer.from_pretrained(CARDINALITY_MODEL_PATH)
card_model = AutoModelForSequenceClassification.from_pretrained(CARDINALITY_MODEL_PATH)
# Map raw labels to ER cardinality strings
# LABEL_0 = 1:1, LABEL_1 = 1:N, LABEL_2 = M:N, LABEL_3 = N:1 (treated as 1:N from other side)
CARD_LABEL_MAP = {
    0: "1:1",
    1: "1:N",
    2: "M:N",
    3: "1:N",
}
card_model.eval()

# ================= FUNCTIONS =================

def entity_extraction(text: str) -> list[str]:
    """
    Run the NER model and return only B-ENTITY tagged tokens,
    properly merged from WordPiece subwords.
    """
    inputs = ner_tokenizer(text, return_tensors="pt", truncation=True, padding=True)

    with torch.no_grad():
        outputs = ner_model(**inputs)

    preds  = torch.argmax(outputs.logits, dim=2)[0]
    tokens = ner_tokenizer.convert_ids_to_tokens(inputs["input_ids"][0])
    id2label = ner_model.config.id2label

    entities = []
    current_entity = None

    for token, pred in zip(tokens, preds):
        label = id2label[pred.item()]

        # Skip special tokens
        if token in ("[CLS]", "[SEP]", "[PAD]"):
            if current_entity:
                entities.append(current_entity)
                current_entity = None
            continue

        if label == "B-ENTITY":
            if current_entity:
                entities.append(current_entity)
            if token.startswith("##"):
                current_entity = token[2:]
            else:
                current_entity = token
        elif label != "O" and "ENTITY" in label and current_entity:
            # Handle I-ENTITY continuation (if model uses BIO scheme)
            if token.startswith("##"):
                current_entity += token[2:]
            else:
                current_entity += token
        else:
            # Non-entity token – but may be subword continuation of entity
            if token.startswith("##") and current_entity:
                current_entity += token[2:]
            else:
                if current_entity:
                    entities.append(current_entity)
                    current_entity = None

    if current_entity:
        entities.append(current_entity)

    return entities


def relation_extraction(text: str) -> str:
    inputs = relation_tokenizer(text, return_tensors="pt", truncation=True, padding=True)

    with torch.no_grad():
        outputs = relation_model(**inputs)

    pred = torch.argmax(outputs.logits, dim=1).item()
    return relation_model.config.id2label[pred]


def predict_cardinality(text: str) -> str:
    """Returns a cardinality string like '1:N', '1:1', 'M:N'."""
    inputs = card_tokenizer(text, return_tensors="pt", truncation=True, padding=True)

    with torch.no_grad():
        outputs = card_model(**inputs)

    pred = torch.argmax(outputs.logits, dim=1).item()
    return CARD_LABEL_MAP.get(pred, "1:N")