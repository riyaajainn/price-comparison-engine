
import sys
import os
import re
import urllib.parse

# Add src to path
sys.path.append(os.getcwd())

from src.extraction.extractor import parse_attributes_from_title
from src.normalization.normalizer import get_normalized_product
from src.search.searcher import build_search_query

def expert_reconstruct(input_title):
    # Stage 1: Identity Lock
    raw_data = parse_attributes_from_title(input_title)
    # Ensure brand is set for the normalization
    if "samsung" in input_title.lower(): raw_data["brand"] = "Samsung"
    
    # Stage 2: Technical Standardization
    norm = get_normalized_product(raw_data)
    
    # Generate High-Intent DNA
    dna = build_search_query(norm, simple=False)
    
    # Generate Link
    link = f"https://www.amazon.in/s?k={urllib.parse.quote_plus(dna)}&ref=nb_sb_noss"
    
    print(f"Brand: {norm['brand'].title()}")
    print(f"Model: {norm['model'].title()}")
    print(f"Variant: {norm['variant'].title() if norm['variant'] else 'None'}")
    print(f"RAM: {norm['ram'] if norm['ram'] else 'None'}")
    print(f"Storage: {norm['storage'] if norm['storage'] else 'None'}")
    print(f"Color: {norm['color'].title() if norm['color'] else 'None'}")
    print(f"\nOptimized Amazon Search DNA: {dna}")
    print(f"Direct Product Link: {link}")

if __name__ == "__main__":
    title = "Samsung Galaxy S25 Ultra 5G AI Smartphone (Titanium Black, 12GB RAM, 512GB Storage), 200MP Camera, S Pen Included, Long Battery Life"
    expert_reconstruct(title)
