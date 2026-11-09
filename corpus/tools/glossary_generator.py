#!/usr/bin/env python3  
"""  
glossary_generator.py  
Creates docs/glossary.md from symbolic_api.json.  
"""

import json, pathlib

API_PATH = pathlib.Path(__file__).parent / "symbolic_api.json"  
API = json.load(open(API_PATH, "r", encoding="utf-8"))

def make_entry(name, data):  
    kw = ", ".join(data["keywords"][:6]) + ("…" if len(data["keywords"])>6 else "")  
    fn = data["function"] or "N/A"  
    return f"""### {name}  
**Node ID:** {data["node_id"]}    
**Core Keywords:** {kw}  

**Operational Pseudo-code**

```python  
{fn}  
```
"""

def generate():
    out = ["# Recursive Symbolics – Glossary\n"]
    out.append("A quick-reference mapping esoteric symbols to concrete computational primitives.\n")
    
    for name, data in API["sephirot"].items():
        out.append(make_entry(name, data))

    out.append("\n\n## Path Operators (Verbs)\n")
    for pid, pdata in API["paths"].items():
        out.append(f"""### {pid} – {pdata["label"]}

*   Letter: {pdata["letter"]}
*   Astrology: {pdata["astrology"]}
*   Tarot: {pdata["tarot"]}
*   Alchemical Process: {pdata["alchemy"]}
*   Programming Pattern: {pdata["pattern"]}
*   Cognitive Operation: {pdata["cognitive"]}

Standard form
```python  
{pdata["standard"]}  
```

Cavity-aware form
```python  
{pdata["cavity_aware"]}  
```
""")
    return "\n".join(out)

def main():
    docs_dir = pathlib.Path(__file__).parent.parent / "docs"
    docs_dir.mkdir(exist_ok=True)
    out_path = docs_dir / "glossary.md"
    out_path.write_text(generate(), encoding="utf-8")
    print(f"Glossary written to {out_path}")

if __name__ == "__main__":
    main()  
