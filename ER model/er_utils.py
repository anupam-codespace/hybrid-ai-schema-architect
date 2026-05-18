from graphviz import Digraph

def generate_fol(entities, relation, cardinality, participation):
    if len(entities) < 2:
        return {"error": "Not enough entities"}

    e1 = entities[0].capitalize()
    e2 = entities[1].capitalize()
    rel = relation.capitalize()

    fol = {
        "entities": [e1, e2],
        "relation": rel,
        "facts": [f"{rel}({e1}, {e2})"],
        "rules": [],
        "constraints": []
    }

    # Cardinality rules
    if cardinality == "1:1":
        fol["rules"].append(f"∀x {e1}(x) → ∃!y {e2}(y)")
    elif cardinality == "1:N":
        fol["rules"].append(f"∀x {e1}(x) → ∃y {e2}(y)")
    elif cardinality == "M:N":
        fol["rules"].append("Many-to-many relation")

    # Participation
    if participation == "total-total":
        fol["constraints"].append("Total participation")
    else:
        fol["constraints"].append("Partial participation")

    return fol


def generate_er_diagram(fol_data, filename="er_diagram"):
    dot = Digraph()

    # 🔥 THIS LINE MAKES IT HORIZONTAL
    dot.attr(rankdir="LR")   # Left → Right

    e1, e2 = fol_data["entities"]
    rel = fol_data["relation"]

    # Nodes
    dot.node(e1, shape="box")
    dot.node(e2, shape="box")
    dot.node(rel, shape="diamond")

    # Edges
    dot.edge(e1, rel)
    dot.edge(rel, e2)

    dot.render(filename, format="png", cleanup=True)

    return filename + ".png"