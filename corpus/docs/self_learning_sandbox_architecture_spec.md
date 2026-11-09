# Technical Specification: Non-Pedagogical Self-Learning Engine & Sandbox

## Executive Overview

This document provides a formal technical specification detailing **how our non-pedagogical implementation framework is applied to the interactive AI OS Kernel / Sandbox** located in [`../standalone_rca_sandbox.py`](../standalone_rca_sandbox.py).

Rather than functioning as a static, single-use script, the **Symbolic OS V2.0 Sandbox** is an **Autonomous Continuous Self-Learning System** that continuously adapts its vector weights, records interaction telemetry to disk (`rca_memory.json`), and enforces **Geburah Directivity Capping ($\gamma \le 0.85$)** in real time.

---

##  1. Self-Learning Engine Architecture

```mermaid
graph TD
    Input["User Input / Slash Command (/eval, /learn, /qualia)"] --> Tokenizer["Pure Token Vectorizer (L2 Projection in R^d)"]
    Tokenizer --> Centroids["Sephirotic Centroid Distance Evaluator (d_C)"]
    Centroids --> Memory["RCALearningEngine (rca_memory.json)<br/>• Persistent Transition Weights<br/>• Historical Frequency Counters"]
    Memory --> Telemetry["4D Qualia Telemetry Vector (Q)<br/>[Phi_somatic, H_emotional, Delta_gamma, Tau_resonance]"]
    Telemetry --> Directivity["Geburah Directivity Guard (gamma <= 0.85)<br/>Non-Coercive Policy Output"]
    Directivity --> Feedback["Dynamic Self-Polishing Weight Update<br/>W_new = W_old + lr * (Reward - W_old)"]
    Feedback --> Memory
```

---

##  2. How the Non-Pedagogical Self-Learning Sandbox Operates

### A. Persistent State Memory (`rca_memory.json`)
The sandbox operates with continuous memory persistence. On every interaction, the `RCALearningEngine` updates and serializes:
```json
{
  "total_interactions": 42,
  "state_counts": {
    "Keter": 5,
    "Chokmah": 8,
    "Binah": 12,
    "Tifereth": 10,
    "Geburah": 4,
    "Malkuth": 3
  },
  "transition_weights": {
    "Keter": 1.05,
    "Chokmah": 1.12,
    "Binah": 1.08,
    "Tifereth": 1.15
  },
  "last_updated": "2026-07-30 01:11:14"
}
```

### B. Dynamic Weight Self-Polishing (Hebbian / Q-Update)
When a user evaluates a prompt, the engine calculates the normalized entropy $H_{\text{norm}}$ and updates state efficacy weights dynamically:
$$W_{n+1}(\text{Sephira}) = W_n(\text{Sephira}) + \alpha \cdot \left(R - W_n(\text{Sephira})\right)$$
where $\alpha = 0.05$ is the learning rate and $R \in [0.5, 1.0]$ is the entropy reward.

### C. 4D Qualia Telemetry Vector ($Q$)
Calculated in sub-millisecond real time without third-party frameworks:
- **$\Phi_{\text{somatic}}$**: Malkuth grounding index (physical / hardware alignment).
- **$H_{\text{emotional}}$**: Bigram uniqueness entropy measuring expression variance.
- **$\Delta\gamma$**: Damping delta $| \text{Score}_{\text{Geburah}} - \text{Score}_{\text{Chesed}} |$.
- **$\tau_{\text{resonance}}$**: Harmonization resonance $(\text{Score}_{\text{Tifereth}} + \text{Score}_{\text{Keter}}) / 2 + 0.30$.

### D. Interactive Slash Command Workbench
The sandbox provides an interactive command menu:
- `/eval <text>`: Run governance and directivity evaluation deck.
- `/learn`: Launch 4-Week Software Engineering Curriculum Tutor.
- `/qualia`: Inspect real-time 4D Qualia Telemetry vector.
- `/memory`: Inspect persistent vector weights in `rca_memory.json`.
- `/dht`: Test Kademlia P2P UDP network node.

---

##  3. How to Run & Practice with the Sandbox

Open PowerShell in `solo/`:

```powershell
cd "`this corpus`"

# Launch Interactive Self-Learning Sandbox:
python standalone_rca_sandbox.py

# Execute Single-Prompt Evaluation:
python standalone_rca_sandbox.py "/eval Building high-performance AI engines"
```

---

##  Key File Links

-  **Sandbox Kernel**: [`../standalone_rca_sandbox.py`](../standalone_rca_sandbox.py)
-  **Persistent Memory**: [`../rca_memory.json`](../rca_memory.json)
-  **Specification**: [`self_learning_sandbox_architecture_spec.md`](self_learning_sandbox_architecture_spec.md)
-  **Brain Mirror**: `self_learning_sandbox_architecture_spec.md` (local brain artifact, not in this repository)
-  **License**: [`LICENSE`](../../LICENSE) (**OmnisMutus**)
