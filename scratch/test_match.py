from src.matching.matcher import is_rejected, calculate_score
from src.extraction.extractor import parse_attributes_from_title

source_norm = {
    'title': 'Samsung S25 Ultra',
    'model': 'S25',
    'variant': 'Ultra',
    'ram': '12 GB',
    'storage': '256 GB',
    'brand': 'Samsung'
}

cand_title = 'Samsung Galaxy S25 Ultra 5G 256 GB, 12 GB RAM, Titanium Black, Mobile Phone'
cand_norm = parse_attributes_from_title(cand_title)
print(f"Cand norm: {cand_norm}")

rejected = is_rejected(cand_title, source_norm, cand_norm, "Samsung S25 Ultra")
print(f"Rejected: {rejected}")
score = calculate_score(source_norm, cand_norm, cand_title)
print(f"Score: {score}")

