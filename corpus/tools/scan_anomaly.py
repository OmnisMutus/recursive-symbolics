#!/usr/bin/env python3
"""
scan_anomaly.py
Crawls the published Web ARG to verify glitch assets, hidden steganography, 
and logs any unexpected anomalies.
"""

import argparse
import urllib.request
import urllib.error
import json
import re
from datetime import datetime, timezone

def construct_pages_url(repo_url):
    """Convert a GitHub repo URL to a GitHub Pages URL."""
    # Example: https://github.com/OmnisMutus/OMARG-PHIRERA-Open-Source-Anomalous-Phenomena-Methods.git
    match = re.search(r'github\.com/([^/]+)/([^/.]+)(?:\.git)?', repo_url)
    if not match:
        raise ValueError("Invalid GitHub repository URL format.")
    username, repo = match.groups()
    return f"https://{username}.github.io/{repo}/games/web_arg/index.html"

def crawl_site(url):
    print(f"[*] Crawling target: {url}")
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "target_url": url,
        "status": "UNKNOWN",
        "assets_verified": {
            "hidden_pre_block": False,
            "glitch_css_linked": False,
            "anomaly_image_linked": False
        },
        "anomalies": []
    }
    
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'OMARG-Scan-Bot/1.0'})
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8')
            report["status"] = f"HTTP {response.status} OK"
            
            # Verify hidden <pre> block
            if 'class="hidden-clue"' in html and 'UEFUSF9JRDogUDEx' in html:
                report["assets_verified"]["hidden_pre_block"] = True
            else:
                report["anomalies"].append("Steganographic Base64 clue is missing or malformed.")
                
            # Verify CSS
            if 'style.css' in html:
                report["assets_verified"]["glitch_css_linked"] = True
            else:
                report["anomalies"].append("Glitch CSS stylesheet is not linked.")
                
            # Verify Image
            if 'anomaly_scan.jpg' in html:
                report["assets_verified"]["anomaly_image_linked"] = True
            else:
                report["anomalies"].append("Anomaly scan image is missing from DOM.")
                
    except urllib.error.HTTPError as e:
        report["status"] = f"HTTP {e.code} Error"
        report["anomalies"].append(str(e))
    except Exception as e:
        report["status"] = "CONNECTION ERROR"
        report["anomalies"].append(str(e))
        
    return report

def main():
    parser = argparse.ArgumentParser(description="Scan published ARG for anomalies.")
    parser.add_argument("--repo", required=True, help="GitHub repository URL")
    parser.add_argument("--output", required=True, help="Path to save the JSON report")
    args = parser.parse_args()
    
    try:
        pages_url = construct_pages_url(args.repo)
    except ValueError as e:
        print(f"[!] {e}")
        return
        
    report = crawl_site(pages_url)
    
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=4)
        
    print(f"[SUCCESS] Scan complete. Report saved to {args.output}")
    if report["anomalies"]:
        print("[!] WARNING: Anomalies detected during scan.")
        for anomaly in report["anomalies"]:
            print(f"  - {anomaly}")
    else:
        print("[SUCCESS] All assets verified. System is stable.")

if __name__ == "__main__":
    main()
