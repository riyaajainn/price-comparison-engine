
import sys
import os
import re

# Add src to path
sys.path.append(os.getcwd())

from src.extraction.extractor import parse_attributes_from_title
from src.normalization.normalizer import get_normalized_product
from src.matching.matcher import calculate_score, is_rejected

def test_amazon_noisy_title():
    # Flipkart Source (What the user is looking for)
    source_title = "Samsung Galaxy S25 Ultra 5G (Titanium Black, 512 GB) (12 GB RAM)"
    source_raw = parse_attributes_from_title(source_title)
    source_norm = get_normalized_product(source_raw)
    
    # Amazon Candidate (Noisy Title)
    amazon_title = "Samsung Galaxy S25 Ultra 5G AI Smartphone (Titanium Black, 12GB RAM, 512GB Storage), 200MP Camera, S Pen Included, Long Battery Life"
    amazon_raw = parse_attributes_from_title(amazon_title)
    amazon_norm = get_normalized_product(amazon_raw)
    
    print("=== Amazon Noisy Title Diagnostic ===")
    print(f"Source: {source_title}")
    print(f"Amazon: {amazon_title}")
    print(f"\nSource Norm: {source_norm}")
    print(f"Amazon Norm: {amazon_norm}")
    
    rej = is_rejected(amazon_title, source_norm, amazon_norm, input_raw_title=source_title)
    print(f"\nIs Rejected: {rej}")
    
    if not rej:
        score = calculate_score(source_norm, amazon_norm, amazon_title)
        print(f"Match Score: {score}")
    else:
        print("Re-evaluating rejection reasons...")
        # Rule 5: Variants
        variants = ["pro", "plus", "ultra", "max", "fe", "mini", "lite", "se", "alpha", "neo", "edge"]
        source_ref = source_title.lower()
        s_v = [v for v in variants if re.search(rf'\b{v}\b', source_ref)]
        c_v = [v for v in variants if re.search(rf'\b{v}\b', amazon_title.lower())]
        print(f"  Variants: Source {s_v}, Cand {c_v}")
        
        # Rule 6: Model ID
        target_model = source_norm.get("model", "")
        target_ids = re.findall(r'\b[a-z0-9]*\d+[a-z0-9]*\b', target_model.lower())
        print(f"  Model IDs: {target_ids}")
        for tid in target_ids:
            if not re.search(rf'\b{tid}\b', amazon_title.lower(), re.I):
                print(f"  [!] Missing Model ID: {tid}")

if __name__ == "__main__":
    test_amazon_noisy_title()
