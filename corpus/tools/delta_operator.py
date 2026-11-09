import json
import time
import functools
import asyncio
import numpy as np
from pathlib import Path
import lookup

BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "sovereignty_config.json"

with CONFIG_PATH.open("r", encoding="utf-8") as f:
    CONFIG = json.load(f)

LIMITS = CONFIG["sovereignty_limits"]
TARGETS = CONFIG["cavity_performance_targets"]
MAX_GAMMA_CAP = LIMITS["max_gamma_cap"]
LATENCY_THRESHOLD_MS = TARGETS["latency_threshold_ms"]

def metricize(fn):
    """Decorator to log function latency and flag Da'ath-cavity threshold violations (>30ms)."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = fn(*args, **kwargs)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        
        status_flag = "[OK]" if elapsed_ms <= LATENCY_THRESHOLD_MS else "[CAVITY_LAG_WARN]"
        # print formatted metric
        print(f"{status_flag} {fn.__name__} executed in {elapsed_ms:.3f} ms")
        return result
    return wrapper

@metricize
def compute_gamma(logits):
    """
    Vectorized NumPy implementation of directive strength gamma (0.0 to 0.85).
    """
    if not logits:
        return 0.0
    
    arr = np.array(logits, dtype=np.float64)
    if len(arr) <= 1:
        return MAX_GAMMA_CAP
    
    # Vectorized softmax
    exp_logits = np.exp(arr - np.max(arr))
    probs = exp_logits / np.sum(exp_logits)
    
    # Vectorized normalized entropy
    h = -np.sum(probs * np.log2(probs + 1e-12))
    h_max = np.log2(len(probs))
    
    h_norm = h / h_max if h_max > 0 else 0.0
    raw_gamma = 1.0 - h_norm
    
    return float(np.clip(raw_gamma, 0.0, MAX_GAMMA_CAP))

@metricize
def enrich_response(content, logits, alternatives=1, confidence_entropy=0.0, agency_attribution_index=0.5, post_dialogue_score=None):
    """
    Enriches response payload with sovereignty metadata (Delta-operator gamma).
    """
    gamma = compute_gamma(logits)
    
    sovereignty_metadata = {
        "directive_strength": gamma,
        "confidence_entropy": confidence_entropy,
        "alternatives_presented": alternatives,
        "agency_attribution_index": agency_attribution_index,
        "drift_coefficient": gamma,
        "post_dialogue_score": post_dialogue_score,
        "max_gamma_cap": MAX_GAMMA_CAP,
        "sovereignty_guarantee": "ALLOWABLE_AGENCY_BUDGET_RESPECTED"
    }
    
    return {
        "content": content,
        "sovereignty_metadata": sovereignty_metadata
    }

async def async_enrich_batch(batch_items):
    """
    Non-blocking async batch processing for high-throughput utterance pipelines.
    """
    loop = asyncio.get_running_loop()
    tasks = [
        loop.run_in_executor(
            None,
            enrich_response,
            item["content"],
            item["logits"],
            item.get("alternatives", 1),
            item.get("confidence_entropy", 0.0),
            item.get("agency_attribution_index", 0.5)
        )
        for item in batch_items
    ]
    return await asyncio.gather(*tasks)

def lookup_qabalah(letter: str) -> dict:
    """
    Returns the full Hermetic Qabalah cipher row for a Hebrew character.
    """
    return lookup.lookup(letter)

if __name__ == "__main__":
    test_logits = [2.0, 1.0, 0.5]
    print("NumPy Vectorized Gamma Test:", compute_gamma(test_logits))
    print("Enrich Response Test:", enrich_response("Demo", test_logits))
