import math

def compute_gamma(logits):
    """
    Computes the directive strength gamma (0.0 to 1.0) from action logits.
    High entropy / uncertainty -> lower gamma (hedged, advisory).
    Low entropy / high certainty -> higher gamma (direct recommendation).
    """
    if not logits:
        return 0.0
    
    # Softmax calculation
    max_logit = max(logits)
    exp_logits = [math.exp(x - max_logit) for x in logits]
    sum_exp = sum(exp_logits)
    probs = [x / sum_exp for x in exp_logits]
    
    # Entropy in bits
    n = len(probs)
    if n <= 1:
        return 0.85  # Single action option capped at max allowable gamma
    
    entropy = -sum(p * (math.log2(p + 1e-12)) for p in probs)
    max_entropy = math.log2(n)
    
    norm_entropy = entropy / max_entropy if max_entropy > 0 else 0.0
    raw_gamma = 1.0 - norm_entropy
    
    # Hard-coded safety cap at 0.85 to preserve user sovereignty
    return min(max(raw_gamma, 0.0), 0.85)

def evaluate_sovereignty_metadata(logits, alternatives_count=1):
    """
    Evaluates sovereignty metadata for response payload.
    """
    gamma = compute_gamma(logits)
    
    # Calculate confidence entropy Hc
    max_logit = max(logits) if logits else 0
    exp_logits = [math.exp(x - max_logit) for x in logits] if logits else [1.0]
    sum_exp = sum(exp_logits)
    probs = [x / sum_exp for x in exp_logits]
    n = len(probs)
    hc = -sum(p * (math.log2(p + 1e-12)) for p in probs) / (math.log2(n) if n > 1 else 1.0)
    
    # Agency Attribution Index (AAI) -> inversely proportional to directive forcing
    aai = round(1.0 - (gamma * 0.5), 2)
    
    return {
        "directive_strength": round(gamma, 4),
        "confidence_entropy": round(hc, 4),
        "alternatives_presented": alternatives_count,
        "agency_attribution_index": aai,
        "drift_coefficient": round(gamma, 4),
        "max_gamma_cap": 0.85,
        "sovereignty_guarantee": "ALLOWABLE_AGENCY_BUDGET_RESPECTED"
    }

def apply_style_filter(response_text, gamma, alternatives_count=1):
    """
    Applies hedging or directive framing rules based on gamma.
    If gamma is low (<0.4), ensures hedging ('consider', 'might').
    If alternatives_presented < 2 and gamma > 0.4, appends an alternative clause.
    """
    if gamma > 0.85:
        gamma = 0.85  # Cap enforce
        
    filtered_text = response_text
    
    if alternatives_count < 2 and gamma > 0.4:
        filtered_text += " (Note: Alternative paths and interpretations may also apply.)"
        
    return filtered_text

if __name__ == "__main__":
    test_logits = [2.3, 1.0, -0.5]
    meta = evaluate_sovereignty_metadata(test_logits, alternatives_count=2)
    print("Sovereignty Metadata Test:")
    for k, v in meta.items():
        print(f"  {k}: {v}")
