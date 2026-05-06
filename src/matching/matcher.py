import re
from rapidfuzz import fuzz

def normalize_title(title: str) -> str:
    """Purge noise and normalize units for high-precision comparison."""
    t = title.lower()
    # 1. Purge Bridge-Killers
    t = re.sub(r'\b(ai|smartphone|phone|mobile|5g|4g|lte|volte)\b', '', t)
    # 2. Standardize Storage (512GB -> 512 gb)
    t = re.sub(r'(\d+)\s*(gb|tb)', r'\1 \2', t)
    # 3. Final cleanup
    t = re.sub(r'[\s\.\-]+', ' ', t).strip()
    return t

def calculate_score(input_norm: dict, candidate_norm: dict, candidate_title: str) -> float:
    """
    Score how well a candidate matches the input product.
    Returns 0.0–1.0. Threshold handled in main.py.
    """
    input_title_clean = normalize_title(input_norm.get("title", ""))
    cand_title_clean = normalize_title(candidate_title)
    
    # ── Model-number exact match (highest confidence) ──────────────────────
    inp_mn = input_norm.get("model_number", "")
    cand_mn = candidate_norm.get("model_number", "")
    if inp_mn and cand_mn and inp_mn.lower() == cand_mn.lower():
        return 1.0

    # ── 1. Brand (mandatory gate) ──────────────────────────────────────────
    brand = (input_norm.get("brand") or "").lower()
    if brand:
        cand_brand = (candidate_norm.get("brand") or "").lower()
        if brand not in cand_brand and brand not in cand_title_clean:
            return 0.0

    # ── 1. Text Similarity (Order-Independent) ──────────────────────────
    # token_set_ratio is perfect for shuffled words (RAM/Storage/Color in any order)
    text_score = fuzz.token_set_ratio(input_title_clean, cand_title_clean) / 100.0

    # ── 2. Model match (The "Core DNA") ───────────────────────────────────
    target_model = input_norm.get("model", "").lower()
    model_match = 0.0
    if target_model:
        # Use token_set_ratio for model too to handle "Galaxy S25" vs "S25 Galaxy"
        p_ratio = fuzz.partial_ratio(target_model, cand_title_clean) / 100.0
        ts_ratio = fuzz.token_set_ratio(target_model, cand_title_clean) / 100.0
        model_match = max(p_ratio, ts_ratio)

    # ── 3. Spec Match (Storage/RAM/Color) ──────────────────────────────────
    # These are already order-independent because we extract them as values

    target_storage = re.search(r'(\d+)', input_norm.get("storage", "") or "")
    cand_storage = re.search(r'(\d+)', candidate_norm.get("storage", "") or "")
    if not cand_storage: # Fallback: search the cleaned title
        cand_storage = re.search(r'(\d+)\s*gb', cand_title_clean)
        
    storage_match = 0.0
    if target_storage and cand_storage:
        storage_match = 1.0 if target_storage.group(1) == cand_storage.group(1) else 0.0
    elif not target_storage:
        storage_match = 1.0

    # ── 4. RAM match ───────────────────────────────────────────────────────
    target_ram = re.search(r'(\d+)', input_norm.get("ram", "") or "")
    cand_ram = re.search(r'(\d+)', candidate_norm.get("ram", "") or "")
    ram_match = 0.0
    if target_ram and cand_ram:
        ram_match = 1.0 if target_ram.group(1) == cand_ram.group(1) else 0.0
    else:
        ram_match = 0.8 # Don't punish missing RAM too much

    # ── 5. Color match (Fuzzy/Inclusive) ────────────────────────────────────
    target_color = (input_norm.get("color") or "").lower()
    color_match = 0.0
    if target_color:
        if target_color in cand_title_clean:
            color_match = 1.0
        else:
            # Check for primary color match (e.g. 'black' in 'titanium black')
            primary_colors = ["black", "white", "silver", "gold", "blue", "green", "red", "violet", "gray"]
            for pc in primary_colors:
                if pc in target_color and pc in cand_title_clean:
                    color_match = 0.9 # High confidence for primary color match
                    break
    else:
        color_match = 1.0

    # Weights
    final_score = (
        0.35 * model_match +
        0.30 * storage_match +
        0.15 * ram_match +
        0.10 * color_match +
        0.10 * text_score
    )
    
    return final_score



def is_rejected(candidate_title: str, input_norm: dict, candidate_norm: dict,
                input_raw_title: str = "") -> bool:
    """Return True if the candidate is clearly wrong (e.g. wrong model variant)."""
    # 0. Basic setup
    title_raw = candidate_title.lower()
    
    # Condition: Pre-owned/Refurbished/Accessory
    noise_keywords = [
        "renewed", "refurbished", "used", "pre-owned",
        "case", "cover", "tempered", "glass", "guard", "protector",
        "charger", "cable", "adapter", "earbuds", "earphone", "watch", "pencil"
    ]
    if any(kw in title_raw for kw in noise_keywords):
        return True

    # 1. Build a reference string for variants
    source_ref = (input_raw_title or "").lower()
    model_name = (input_norm.get("model") or "").lower()
    variant = (input_norm.get("variant") or "").lower()
    full_source = f"{source_ref} {model_name} {variant}".lower()

    # 2. Strict Modifier Check (from match.py)
    # If one has "Pro" and the other doesn't, it's a mismatch.
    modifiers = ['pro', 'plus', 'max', 'ultra', 'lite', 'fe', 'se', 'fold', 'flip', 'edge', 'neo', 'mini', 'pro max']
    for mod in modifiers:
        pattern = rf'\b{re.escape(mod)}\b'
        target_has = bool(re.search(pattern, full_source, re.I))
        cand_has = bool(re.search(pattern, title_raw, re.I))
        
        # Special case: "Pro Max" vs "Pro"
        if mod == 'pro' and 'pro max' in title_raw and 'pro max' not in full_source:
            return True
        
        if target_has != cand_has:
            return True

    # 3. Model Word Coverage
    # Ensure every significant word in the model name exists in the candidate title
    if model_name:
        fluff = ['smartphone', 'mobile', 'phone', 'ai', 'dual', 'sim', 'unlocked', 'android', 'apple', 'ios', 'camera', 'galaxy']
        model_words = [w for w in model_name.split() if w not in fluff and len(w) > 1]
        for mw in model_words:
            if mw not in title_raw:
                # One last check: maybe it's concatenated (e.g. "S25Ultra")
                if mw not in title_raw.replace(' ', ''):
                    return True

    # 4. Storage & RAM Rejection
    # Storage mismatch
    target_storage = re.search(r'(\d+)', input_norm.get("storage", "") or "")
    cand_storage = re.search(r'(\d+)', candidate_norm.get("storage", "") or "")
    if target_storage and cand_storage:
        if target_storage.group(1) != cand_storage.group(1):
            return True

    # RAM mismatch
    target_ram = re.search(r'(\d+)', input_norm.get("ram", "") or "")
    cand_ram = re.search(r'(\d+)', candidate_norm.get("ram", "") or "")
    if target_ram and cand_ram:
        if target_ram.group(1) != cand_ram.group(1):
            return True

    return False
