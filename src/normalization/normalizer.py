import re


def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = text.lower()
    # Preserve + sign for variants like S24+
    text = re.sub(r'[^a-z0-9\s\.\+]', ' ', text)
    text = " ".join(text.split())
    
    # Strict Exclusion Filter: Connectivity and Marketing Fluff
    noise_words = [
        # Connectivity
        '5g', '4g', 'volte', 'wi fi', 'wifi', 'lte',
        # Marketing Fluff
        'smartphone', 'mobile phone', 'phone', 'ai', '200mp', 'camera', 
        's pen', 'spen', 'battery', 'charging', 'model', 'new', 'best deal',
        'display', 'snapdragon', 'provisual', 'included', 'fast', 'long',
        'for sale', 'buy online', 'price', 'in india'
    ]
    for word in noise_words:
        # Use regex for word boundary to avoid partial matches (e.g. 'ai' in 'xiaomi')
        text = re.sub(rf'\b{word}\b', '', text)
    
    return " ".join(text.split())


def normalize_units(text: str) -> str:
    if not text:
        return ""
    text = text.lower().strip()
    # Standardize to "[Value] GB/TB" with a space
    text = re.sub(r'(\d+)\s*gb', r'\1 GB', text)
    text = re.sub(r'(\d+)\s*tb', r'\1 TB', text)
    text = re.sub(r'(\d+)\s*mb', r'\1 MB', text)
    # Extract only the first storage token if the value is verbose
    # e.g. "256 GB Internal Storage" → "256gb"
    m = re.search(r'(\d+\s*(?:gb|tb|mb))', text)
    return m.group(1).upper() if m else text


def normalize_color(color: str) -> str:
    if not color:
        return ""
    color = normalize_text(color)

    # Comprehensive vendor-color → base-color mapping
    color_map = {
        # Black family
        "midnight black": "black", "phantom black": "black",
        "awesome graphite": "black", "space black": "black",
        "matte black": "black", "onyx black": "black",
        "graphite black": "black", "carbon black": "black",
        "jet black": "black", "classic black": "black",

        # White family
        "phantom white": "white", "starlight": "white",
        "awesome white": "white", "cloud white": "white",
        "pearl white": "white", "cream white": "white",

        # Grey family
        "space grey": "grey", "space gray": "grey",
        "graphite": "grey", "titanium gray": "grey",
        "flint gray": "grey", "cool grey": "grey",
        "gun metal": "grey", "gunmetal": "grey",

        # Blue family
        "cobalt blue": "blue", "awesome blue": "blue",
        "pacific blue": "blue", "sierra blue": "blue",
        "alpine blue": "blue", "ice blue": "blue",
        "midnight blue": "blue", "navy blue": "blue",
        "steel blue": "blue", "titanium blue": "blue",
        "ocean blue": "blue", "sky blue": "blue",
        "royal blue": "blue", "aegean blue": "blue",

        # Green family
        "awesome lime": "green", "mint green": "green",
        "sage green": "green", "forest green": "green",
        "cypress green": "green",

        # Violet / Purple family
        "cobalt violet": "violet", "awesome violet": "violet",
        "lavender": "purple", "light purple": "purple",
        "orchid": "purple",

        # Red / Coral family
        "cosmic red": "red", "awesome red": "red",
        "cardinal red": "red", "fiery red": "red",
        "sunrise coral": "coral",

        # Gold / Champagne
        "champagne gold": "gold", "rose gold": "gold",
        "golden": "gold",

        # Silver
        "prism silver": "silver", "awesome silver": "silver",
        "alpine silver": "silver",

        # Titanium (treat as its own base)
        "natural titanium": "titanium", "white titanium": "titanium",
        "black titanium": "titanium", "desert titanium": "titanium",
        "blue titanium": "titanium",
    }

    for key, val in color_map.items():
        if key in color:
            return val

    # If no map hit, strip common adjectives and keep only the color word
    base_colors = [
        "black", "white", "grey", "gray", "silver", "gold", "blue", "green",
        "red", "violet", "pink", "purple", "orange", "brown", "coral",
        "yellow", "cyan", "teal", "titanium", "graphite", "champagne",
        "lavender", "peach", "cream", "midnight", "starlight"
    ]
    for bc in base_colors:
        if bc in color:
            return bc

    return color


def normalize_brand(brand: str) -> str:
    if not brand:
        return ""
    brand = normalize_text(brand)
    brand_map = {
        "apple": "apple", "samsung": "samsung", "google": "google",
        "oneplus": "oneplus", "xiaomi": "xiaomi", "realme": "realme",
        "oppo": "oppo", "vivo": "vivo", "motorola": "motorola",
        "nothing": "nothing", "iqoo": "iqoo", "poco": "poco",
        "infinix": "infinix", "tecno": "tecno", "lava": "lava",
        "nokia": "nokia", "asus": "asus", "lg": "lg", "htc": "htc",
    }
    for key, val in brand_map.items():
        if key in brand:
            return val
    return brand


def get_normalized_product(data: dict) -> dict:
    return {
        "brand": normalize_brand(data.get("brand", "")),
        "model": normalize_text(data.get("model", "")),
        "variant": normalize_text(data.get("variant", "")),
        "model_number": normalize_text(data.get("model_number", "")),
        "ram": normalize_units(data.get("ram", "")),
        "storage": normalize_units(data.get("storage", "")),
        "color": normalize_color(data.get("color", "")),
    }
