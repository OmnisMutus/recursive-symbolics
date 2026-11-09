#!/usr/bin/env python3
"""
feedback_ingester.py
Anonymizes ritual and debugger outputs to a shared dataset, 
enabling the system to learn and refine its rules from collective practice.

Usage (CLI):
    python feedback_ingester.py path/to/ritual_output.md [--dry]

Usage (Module):
    from feedback_ingester import ingest_feedback
    ingest_feedback(raw_text_content, source_type="ritual", dominant_sephirah=None, patch=None)
"""

import sys
import json
import re
import pathlib
import datetime
import hashlib
import argparse

DATASET_PATH = pathlib.Path(__file__).parent / "community_dataset.jsonl"

def scrub_pii(text):
    """
    Heuristic PII scrubber. 
    Removes emails, phones, IPs, and any line starting with `#User:` or similar tags.
    """
    # Remove emails
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b', '[EMAIL_REDACTED]', text)
    # Remove simple phone number patterns
    text = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE_REDACTED]', text)
    # Remove IP addresses
    text = re.sub(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '[IP_REDACTED]', text)
    
    # Remove custom user tagging lines e.g. #User: John Doe
    text = re.sub(r'#User:.*', '#User: [REDACTED]', text, flags=re.IGNORECASE)
    
    return text

def generate_user_hash():
    """Generates a stable anonymous hash for the local machine to track progression without identity."""
    # In a real app, this might hash a local config file or hardware ID. 
    # For now, we'll hash the filepath of the script as a generic placeholder for the local user.
    local_id = str(pathlib.Path(__file__).resolve())
    return hashlib.sha256(local_id.encode('utf-8')).hexdigest()[:16]

def parse_metrics_from_text(text):
    """Attempt to extract dominant sephirah and patch if the text comes from the debugger."""
    dominant = None
    patch = None
    
    dom_match = re.search(r'Dominant:\s*([A-Za-z]+)', text, re.IGNORECASE)
    if dom_match:
        dominant = dom_match.group(1)
        
    patch_match = re.search(r'invoke\s*([A-Za-z]+)', text, re.IGNORECASE)
    if patch_match:
        patch = patch_match.group(1)
        
    return dominant, patch

def ingest_feedback(content, source_type="unknown", dry_run=False, directive_strength=None, confidence_entropy=None, agency_attribution_index=None):
    """
    Scrubs content and appends it to the JSONL dataset.
    Includes Δ-γ directive strength and sovereignty metrics.
    """
    scrubbed_content = scrub_pii(content)
    
    # Auto-extract metrics if present in the raw text
    extracted_dominant, extracted_patch = parse_metrics_from_text(content)
    
    payload = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "user_id_hash": generate_user_hash(),
        "dominant_sephira": extracted_dominant,
        "patch": extracted_patch,
        "directive_strength_gamma": directive_strength,
        "confidence_entropy_hc": confidence_entropy,
        "agency_attribution_index": agency_attribution_index,
        "max_gamma_cap": 0.85,
        "notes": "",
        "source": source_type,
        "data": scrubbed_content
    }
    
    if dry_run:
        print("--- DRY RUN OUTPUT ---")
        print(json.dumps(payload, indent=2))
        print("----------------------")
        return payload

    try:
        with open(DATASET_PATH, 'a', encoding='utf-8') as f:
            f.write(json.dumps(payload) + "\n")
            f.flush()
    except Exception as e:
        print(f"Failed to write to dataset: {e}", file=sys.stderr)
        sys.exit(1)
        
    return payload

def main():
    parser = argparse.ArgumentParser(description="Ingest and anonymize framework feedback.")
    parser.add_argument("file", type=str, help="Path to the output file (.md or .txt)")
    parser.add_argument("--dry", action="store_true", help="Print the scrubbed payload without saving it")
    args = parser.parse_args()
        
    file_path = pathlib.Path(args.file)
    if not file_path.exists():
        print(f"Error: File {file_path} not found.", file=sys.stderr)
        sys.exit(1)
        
    try:
        raw_content = file_path.read_text(encoding='utf-8')
    except Exception as e:
        print(f"Error reading file: {e}", file=sys.stderr)
        sys.exit(1)
        
    source = "ritual_compiler" if "ritual" in file_path.name.lower() else "debugger"
    
    ingest_feedback(raw_content, source_type=source, dry_run=args.dry)
    
    if not args.dry:
        print(f"[SUCCESS] Payload stored. Successfully scrubbed and ingested {file_path.name}")
    sys.exit(0)

if __name__ == "__main__":
    main()
