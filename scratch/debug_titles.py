
import sys
import os
import re

# Add src to path
sys.path.append(os.getcwd())

from src.extraction.extractor import parse_attributes_from_title
from src.normalization.normalizer import get_normalized_product
from src.matching.matcher import calculate_score, is_rejected

def analyze_titles():
    # OnePlus Test Case
    input_title_op = "OnePlus 13s | Snapdragon® 8 Elite | Smarter with OnePlus AI | Lifetime Display Warranty | 12GB+256GB | Green Silk"
    platforms_op = {
        "Flipkart (OnePlus)": "OnePlus 13s 5G (Green Silk, 256 GB) (12 GB RAM)",
        "Reliance (OnePlus)": "OnePlus 13s 5G 256 GB, 12 GB RAM, Green Silk, Mobile Phone",
        "Croma (OnePlus)": "OnePlus 13s 5G (12GB RAM, 512GB, Green Silk)"
    }

    # Samsung Test Case
    input_title_sam = "Samsung Galaxy S25 Ultra 5G Mobile with Galaxy AI"
    platforms_sam = {
        "Flipkart (Samsung)": "Samsung Galaxy S25 Ultra 5G (512 GB Storage, 12 GB RAM) Online at Best Price On Flipkart.com",
        "Amazon (Samsung)": "Samsung Galaxy S25 Ultra 5G Mobile with Galaxy AI",
        "Reliance (Samsung)": "Samsung Galaxy S25 Ultra 5G 512 GB, 12 GB RAM, Titanium Black, Mobile Phone"
    }
    
    test_cases = [
        (input_title_op, platforms_op),
        (input_title_sam, platforms_sam)
    ]

    for input_title, platforms in test_cases:
        print(f"\n{'='*20} TESTING: {input_title[:40]}... {'='*20}")
        raw_data = parse_attributes_from_title(input_title)
        input_norm = get_normalized_product(raw_data)
        print(f"Input Normalized: {input_norm}")
    
        for platform, cand_title in platforms.items():
            print(f"\n--- {platform} Analysis ---")
            print(f"Candidate Title: {cand_title}")
            
            cand_raw_data = parse_attributes_from_title(cand_title)
            cand_norm = get_normalized_product(cand_raw_data)
            print(f"Candidate Normalized: {cand_norm}")
            
            rejected = is_rejected(cand_title, input_norm, cand_norm)
            print(f"Is Rejected: {rejected}")
            
            if not rejected:
                score = calculate_score(input_norm, cand_norm, cand_title)
                print(f"Match Score: {score}")
            else:
                # Re-check rejection rules manually to see which one triggered
                print("Identifying rejection cause...")
                
                # Rule 1: Accessories
                accessory_kws = ["case", "cover", "screen protector", "tempered glass", "guard", "strap", "cable", "adapter", "charger", "pouch", "skin", "earphones", "buds", "watch", "band", "connector", "compatible with"]
                for kw in accessory_kws:
                    if kw in cand_title.lower():
                        print(f"  [!] REJECTED: Accessory keyword found: {kw}")

                # Rule 5: Variants
                variants_list = ["pro max", "ultra", "pro", "plus", "max", "mini", "fe", "se", "e"]
                def get_v(text):
                    found = set()
                    for v in variants_list:
                        if re.search(rf"(?:\b|(?<=\d)){v}\b", text.lower()):
                            found.add(v)
                    return found
                
                target_context = f"{input_norm.get('model')} {input_norm.get('variant')} {input_norm.get('storage')} {input_norm.get('ram')}".lower()
                t_v = get_v(target_context)
                c_v = get_v(cand_title)
                if t_v != c_v:
                    print(f"  [!] REJECTED: Variant mismatch. Target: {t_v}, Cand: {c_v}")

                # Check Model Identifier (The suspected bug)
                target_model = input_norm.get("model", "")
                if target_model:
                    target_ids = re.findall(r'\b[a-z0-9]*\d+[a-z0-9]*\b', target_model)
                    for tid in target_ids:
                        if not re.search(rf'\b{tid}\b', cand_title.lower()):
                            print(f"  [!] REJECTED: Missing model ID '{tid}' (Case sensitive?)")

                # Check Storage
                cand_tokens = set(re.findall(r'\b(\d+)\s*(?:gb|tb)\b', cand_title.lower()))
                target_tokens = set(re.findall(r'\b(\d+)\s*(?:gb|tb)\b', target_context))
                if cand_tokens and target_tokens:
                    for ct in cand_tokens:
                        if ct not in target_tokens:
                            print(f"  [!] REJECTED: Storage/RAM mismatch. Cand has {ct}, not in target {target_tokens}")
                elif cand_tokens and not target_tokens:
                    print(f"  [!] REJECTED: Cand has specs {cand_tokens} but Target has NONE (Strict Rule Failure)")

if __name__ == "__main__":
    analyze_titles()
