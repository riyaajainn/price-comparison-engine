
from src.extraction.extractor import parse_attributes_from_title
from src.normalization.normalizer import get_normalized_product
from src.search.searcher import build_search_query

input_title = "Samsung Galaxy S25 Ultra 5G AI Smartphone (Titanium Black, 12GB RAM, 512GB Storage), 200MP Camera, S Pen Included, Long Battery Life"

# 1. Extract
raw_data = parse_attributes_from_title(input_title)

# 2. Normalize
norm_data = get_normalized_product(raw_data)

# 3. Format as requested
print(f"Brand: {norm_data['brand'].title()}")
print(f"Model: {norm_data['model'].title()}")
print(f"Variant: {norm_data['variant'].title()}")
print(f"RAM: {norm_data['ram'].upper()}")
print(f"Storage: {norm_data['storage'].upper()}")
print(f"Color: {norm_data['color'].title()}")
print(f"\nOptimized Search Query: {build_search_query(norm_data)}")
