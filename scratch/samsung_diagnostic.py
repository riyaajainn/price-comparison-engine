
import sys
import os
import re
import json

# Add src to path
sys.path.append(os.getcwd())

from src.extraction.extractor import parse_attributes_from_title
from src.normalization.normalizer import get_normalized_product
from src.matching.matcher import calculate_score, is_rejected

def run_samsung_diagnostic():
    # Simulate a real Samsung S25 Ultra search
    source_title = "Samsung Galaxy S25 Ultra 5G Mobile with Galaxy AI"
    source_raw = parse_attributes_from_title(source_title)
    source_norm = get_normalized_product(source_raw)
    
    print(f"=== Samsung Source Extraction Diagnostic ===")
    print(f"Source Title: {source_title}")
    print(f"Extracted Raw: {source_raw}")
    print(f"Normalized: {source_norm}")
    
    candidates = [
        ("Flipkart Match", "Samsung Galaxy S25 Ultra 5G (512 GB Storage, 12 GB RAM) Online at Best Price On Flipkart.com"),
        ("Reliance Match", "Samsung Galaxy S25 Ultra 5G 512 GB, 12 GB RAM, Titanium Black, Mobile Phone"),
        ("Wrong Model", "Samsung Galaxy S25 5G (256 GB Storage, 8 GB RAM)"),
        ("Wrong Variant", "Samsung Galaxy S25 Plus 5G (256 GB Storage, 12 GB RAM)")
    ]
    
    print(f"\n=== Matching Diagnostic ===")
    for label, title in candidates:
        print(f"\n--- Testing {label} ---")
        print(f"Candidate Title: {title}")
        
        cand_raw = parse_attributes_from_title(title)
        cand_norm = get_normalized_product(cand_raw)
        
        # Detailed rejection check
        print("Rejection Checks:")
        # 1. Accessories
        accessory_kws = ["case", "cover", "screen protector", "tempered glass"]
        acc_rej = any(kw in title.lower() for kw in accessory_kws)
        print(f"  - Accessory Match: {acc_rej}")
        
        # 2. Variant
        variants = ["pro", "plus", "ultra", "max", "fe", "mini", "lite", "se", "alpha", "neo", "edge"]
        source_ref = source_title.lower()
        s_v = [v for v in variants if re.search(rf'\b{v}\b', source_ref)]
        c_v = [v for v in variants if re.search(rf'\b{v}\b', title.lower())]
        var_rej = (s_v != c_v)
        print(f"  - Variant Match: Source {s_v}, Candidate {c_v} | Reject: {var_rej}")
        
        # 3. Storage Rejection (Rule 4 in matcher.py)
        # In matcher.py, if target_storage is empty, it doesn't reject.
        target_storage = source_norm.get("storage")
        print(f"  - Target Storage in Norm: '{target_storage}'")
        
        rej = is_rejected(title, source_norm, cand_norm, input_raw_title=source_title)
        print(f"  - Final is_rejected(): {rej}")
        
        if not rej:
            score = calculate_score(source_norm, cand_norm, title)
            print(f"  - Match Score: {score}")

if __name__ == "__main__":
    run_samsung_diagnostic()
