#!/usr/bin/env python3  
"""  
ritual_compiler.py  
Transforms a high-level intention into a concrete step-by-step  
checklist using the Sephirotic routing table.

Usage:  
    python ritual_compiler.py "Launch New Project"  
"""

import json, sys, pathlib, heapq

API_PATH = pathlib.Path(__file__).parent / "symbolic_api.json"  
API = json.load(open(API_PATH, "r", encoding="utf-8"))

# ----------------------------------------------------------------------  
# Build a simple adjacency list from the Paths  
adj = {}  
for pid, pdata in API["paths"].items():  
    src, dst = pdata["label"].split(" → ")  
    adj.setdefault(src.strip(), []).append((dst.strip(), pid))

def heuristic(a, b):  
    # trivial heuristic: each hop costs 1 → uniform  
    return 0

def a_star(start, goal):  
    """Return list of (node, path_id) from start to goal."""  
    frontier = [(0, start, [])]  # (priority, node, path_sofar)  
    explored = set()  
    while frontier:  
        _, cur, path = heapq.heappop(frontier)  
        if cur == goal:  
            return path  
        if cur in explored:  
            continue  
        explored.add(cur)  
        for nxt, pid in adj.get(cur, []):  
            new_path = path + [(nxt, pid)]  
            priority = len(new_path) + heuristic(nxt, goal)  
            heapq.heappush(frontier, (priority, nxt, new_path))  
    return None

def compile_ritual(intent, origin="Kether", destination="Malkuth"):  
    route = a_star(origin, destination)  
    if not route:  
        raise RuntimeError(f"No route from {origin} to {destination}")

    steps = []  
    current_state = {"seed": intent}  
    for node, pid in route:  
        path_info = API["paths"][pid]  
        step = {  
            "to_node": node,  
            "path_id": pid,  
            "description": f"{path_info['label']} – {path_info['alchemy']} – {path_info['pattern']}",  
            "code_snippet": f"{path_info['standard']}  // apply to current state"  
        }  
        steps.append(step)  
        # In a real engine we would update current_state; omitted for brevity  
    return steps

def format_markdown(steps, intent):  
    md = f"# Ritual Compilation – \"{intent}\"\n\n"  
    md += "| Step | Destination | Path | Symbolic Meaning | Pseudo-code |\n"  
    md += "|------|-------------|------|------------------|-------------|\n"  
    for i, s in enumerate(steps, 1):  
        md += f"| {i} | {s['to_node']} | {s['path_id']} | {s['description']} | `{s['code_snippet']}` |\n"  
    return md

def main():  
    if len(sys.argv) < 2:  
        print("Usage: python ritual_compiler.py \"<high-level intention>\"")  
        sys.exit(1)

    intent = " ".join(sys.argv[1:])  
    steps = compile_ritual(intent)  
    markdown = format_markdown(steps, intent)  
    out_file = pathlib.Path(__file__).parent / f"ritual_{intent.replace(' ', '_').lower()}.md"  
    out_file.write_text(markdown, encoding="utf-8")  
    print(f"Ritual compiled to {out_file}")

if __name__ == "__main__":  
    main()  
