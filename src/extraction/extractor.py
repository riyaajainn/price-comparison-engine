from bs4 import BeautifulSoup
import re


def parse_attributes_from_title(title: str, existing_data: dict = None) -> dict:
    """Extract brand, model, variant, storage, ram, color from a product title string."""
    data = existing_data.copy() if existing_data else {}
    data["title"] = title
    if not title:
        return data

    t_lower = title.lower()

    # 1. Brand
    if not data.get("brand"):
        for b in ["samsung", "apple", "oneplus", "xiaomi", "realme",
                  "oppo", "vivo", "motorola", "google", "nothing",
                  "iqoo", "poco", "infinix", "tecno", "lava"]:
            if b in t_lower:
                data["brand"] = b
                break

    # 2. Storage + RAM (Heuristic: Smaller=RAM, Larger=Storage)
    if not data.get("ram") or not data.get("storage"):
        gb_matches = list(re.finditer(r'\b(\d+)\s*(GB|TB|MB)\b', title, re.IGNORECASE))
        gb_values = []
        for m in gb_matches:
            val = int(m.group(1))
            unit = m.group(2).upper()
            sort_val = val * 1024 if unit == 'TB' else (val / 1024 if unit == 'MB' else val)
            gb_values.append({'str': f"{val} {unit}", 'val': sort_val})
        
        gb_values.sort(key=lambda x: x['val'])
        if len(gb_values) >= 2:
            if gb_values[0]['val'] <= 64:
                data.setdefault("ram", gb_values[0]['str'])
                data.setdefault("storage", gb_values[-1]['str'])
            else:
                data.setdefault("storage", gb_values[0]['str'])
        elif len(gb_values) == 1:
            if 'ram' in t_lower: data.setdefault("ram", gb_values[0]['str'])
            else: data.setdefault("storage", gb_values[0]['str'])

    # 3. Model & Variant
    # Hardware Variant Taxonomy
    variants_premium = ["ultra", "pro max", "pro", "fold", "tri-fold", "air", "slim"]
    variants_mid = ["plus", r"\+", "fe", "ce", "neo", "r", "gt", "turbo"]
    variants_entry = ["lite", "play", "go"] # 'e', 's', 'c', 'a' handled specially to avoid common words
    
    all_variants = variants_premium + variants_mid + variants_entry
    
    extracted_variant = ""
    for v in all_variants:
        if v == r"\+":
            # Only match + if it's attached to a word (e.g. S24+) 
            # and not surrounded by spaces or between numbers
            pattern = r'(?<=[a-zA-Z0-9])\+'
        else:
            pattern = rf'\b{v}\b'
            
        if re.search(pattern, t_lower):
            extracted_variant = v.replace("\\", "")
            break
    
    # Special handling for single-letter variants (e, s, c, a) often appended to model
    if not extracted_variant:
        m_v = re.search(r'\b\d+([esca])\b', t_lower)
        if m_v:
            extracted_variant = m_v.group(1)

    data["variant"] = extracted_variant.title() if extracted_variant else ""

    if not data.get("model"):
        # ── Brand-specific model extraction ──────────────────────────────
        # Goal: capture the *searchable* model string, e.g. "Galaxy S25",
        # "iPhone 16", "Pixel 9", "13" (OnePlus), "Edge 50" (Motorola),
        # "Phone (2a)" (Nothing).  Variant words (Pro/Ultra/Plus/…) are
        # stripped here because they are stored separately in data["variant"].

        # Words to strip before picking the model token
        _VARIANT_NOISE = re.compile(
            r'\b(pro\s*max|pro|ultra|plus|max|fe|ce|neo|lite|play|fold|air|slim|gt|turbo)\b',
            re.I
        )
        _NOISE = re.compile(
            r'\b(5g|4g|lte|volte|ai|smartphone|phone|mobile|wi.?fi|ram|storage|'
            r'internal|inch|display|snapdragon|dimensity|mediatek|buy|online|'
            r'india|price|sale|new|latest|official|genuine|original)\b',
            re.I
        )

        def _strip_noise(s):
            s = _VARIANT_NOISE.sub('', s)
            s = _NOISE.sub('', s)
            # Remove storage/RAM tokens (digits followed by GB/TB/MB)
            s = re.sub(r'\d+\s*(?:gb|tb|mb)', '', s, flags=re.I)
            # Remove parenthetical color/storage hints like "(Black Eclipse, 256 GB)"
            s = re.sub(r'\([^)]*\)', '', s)
            s = re.sub(r'\s+', ' ', s).strip(' -,')
            return s

        brand = data.get("brand", "").lower()

        if "samsung" in t_lower:
            # Capture "Galaxy [series-letter][number]" e.g. Galaxy S25, Galaxy A56, Galaxy M35
            m = re.search(r'galaxy\s+([a-z]\d+)', t_lower)
            if m:
                data["model"] = f"Galaxy {m.group(1).upper()}"
            else:
                # Broader fallback: Galaxy + next token
                m2 = re.search(r'galaxy\s+(\S+)', t_lower)
                data["model"] = f"Galaxy {m2.group(1).upper()}" if m2 else ""

        elif "iphone" in t_lower:
            m = re.search(r'iphone\s+(\d+)', t_lower)
            data["model"] = f"iPhone {m.group(1)}" if m else "iPhone"

        elif "pixel" in t_lower:
            # Google Pixel 9, Pixel 9 Pro, Pixel 8a, Pixel Fold
            m = re.search(r'pixel\s+(\d+[a-z]?|fold|tablet)', t_lower)
            data["model"] = f"Pixel {m.group(1).title()}" if m else "Pixel"

        elif "oneplus" in t_lower:
            # OnePlus 13, OnePlus 12R, OnePlus Nord CE 4
            m = re.search(r'oneplus\s+(\d+[a-z0-9]*)', t_lower)
            if m:
                data["model"] = m.group(1).upper()
            else:
                # "Nord CE 4" style
                m2 = re.search(r'oneplus\s+(nord(?:\s+\w+)*)', t_lower)
                data["model"] = m2.group(1).title() if m2 else ""

        elif "motorola" in t_lower or "moto" in t_lower:
            # Motorola Edge 50, Moto G85, Motorola Razr 50
            m = re.search(r'(?:motorola|moto)\s+(\w+\s*\d+)', t_lower)
            if m:
                model_raw = _strip_noise(m.group(1))
                data["model"] = model_raw.title() if model_raw else m.group(1).title()
            else:
                m2 = re.search(r'(?:motorola|moto)\s+(\w+)', t_lower)
                data["model"] = m2.group(1).title() if m2 else ""

        elif "nothing" in t_lower:
            # Nothing Phone (2a), Nothing Phone (1) — keep the identifier only
            m = re.search(r'nothing\s+phone\s*\(([^)]+)\)', t_lower)
            if m:
                data["model"] = m.group(1).upper()   # "2A", "1", "2"
            else:
                m2 = re.search(r'nothing\s+phone\s+(\S+)', t_lower)
                data["model"] = f"Phone {m2.group(1).upper()}" if m2 else "Phone"

        elif "iqoo" in t_lower:
            m = re.search(r'iqoo\s+(\d+[a-z0-9]*)', t_lower)
            data["model"] = f"{m.group(1).upper()}" if m else ""

        elif "poco" in t_lower:
            # POCO X6 Pro, POCO M6 Plus
            m = re.search(r'poco\s+([a-z]\d+)', t_lower)
            data["model"] = f"{m.group(1).upper()}" if m else ""

        elif "xiaomi" in t_lower:
            m = re.search(r'xiaomi\s+(\d+[a-z0-9]*)', t_lower)
            data["model"] = m.group(1).upper() if m else ""

        elif "realme" in t_lower:
            # Realme 13 Pro+, Realme GT 6, Realme Narzo 70
            m = re.search(r'realme\s+(gt\s+\d+|\d+[a-z0-9]*|narzo\s+\d+)', t_lower)
            if m:
                data["model"] = m.group(1).title()
            else:
                m2 = re.search(r'realme\s+(\w+)', t_lower)
                data["model"] = m2.group(1).title() if m2 else ""

        elif "oppo" in t_lower:
            m = re.search(r'oppo\s+(find\s+\w+|reno\s*\d+[a-z0-9]*|\w+\s*\d+)', t_lower)
            data["model"] = m.group(1).title() if m else ""

        elif "vivo" in t_lower:
            m = re.search(r'vivo\s+(x\d+[a-z0-9]*|v\d+[a-z0-9]*|y\d+[a-z0-9]*|\w+\s*\d+)', t_lower)
            data["model"] = m.group(1).title() if m else ""

        else:
            # Generic fallback: strip brand name + noise, take first meaningful token(s)
            clean_t = re.sub(rf'\b{re.escape(brand)}\b', '', t_lower, flags=re.I)
            clean_t = _strip_noise(clean_t)
            # Take up to 2 tokens (e.g. "Nord CE" for a brand we don't know)
            tokens = clean_t.split()
            data["model"] = " ".join(tokens[:2]).title() if tokens else ""

    # 4. Color
    if not data.get("color"):
        known_colors = [
            "black", "white", "grey", "gray", "silver", "gold",
            "blue", "red", "violet", "pink", "green", "yellow",
            "purple", "orange", "brown", "lavender", "peach",
            "cyan", "teal", "titanium", "graphite", "midnight",
            "starlight", "cream", "coral", "champagne"
        ]
        for c in known_colors:
            if re.search(rf'\b{c}\b', t_lower):
                # Try to catch adjectives (e.g. "Phantom Black")
                m = re.search(rf'([a-z]+)\s+{c}', t_lower)
                data["color"] = m.group(0).title() if m else c.title()
                break

    return data


class ProductExtractor:
    def __init__(self, html_content: str, platform: str):
        self.soup = BeautifulSoup(html_content, 'html.parser')
        self.platform = platform

    def extract(self) -> dict:
        data = {}
        if self.platform == "amazon":
            data = self._extract_amazon()
        elif self.platform == "flipkart":
            data = self._extract_flipkart()
        elif self.platform == "croma":
            data = self._extract_croma()
        elif self.platform == "reliance_digital":
            data = self._extract_reliance()

        # ── Centralized Title Fallback Parser ─────────────────────────────
        return parse_attributes_from_title(data.get('title', ''), data)

    # ── Platform extractors ───────────────────────────────────────────────

    def _extract_amazon(self) -> dict:
        data = {}

        # Title
        title_el = (self.soup.select_one("#productTitle") or
                    self.soup.select_one(".product-title-word-break"))
        
        # Fallback for Amazon Search Result Pages (if user provided a search URL)
        if not title_el:
            first_result = self.soup.select_one('[data-component-type="s-search-result"] h2 a')
            if first_result:
                print("[*] Detected Amazon Search Page. Picking first result as source.")
                data['title'] = first_result.get_text().strip()
                # We don't have full specs from search page, but title fallback will work
                return data

        data['title'] = title_el.get_text().strip() if title_el else ""


        # Brand
        brand_el = (self.soup.select_one("#bylineInfo") or
                    self.soup.select_one(".po-brand .po-break-word"))
        if brand_el:
            data['brand'] = (brand_el.get_text()
                             .replace("Visit the ", "")
                             .replace(" Store", "")
                             .strip())

        def _parse_row(label: str, value: str):
            label = label.lower().strip()
            value = re.sub(r'[\u200e\u200f\u202a-\u202e]', '', value).strip()
            if not value:
                return
            if "ram" in label:
                # Validate RAM value from table
                m_val = re.search(r'(\d+)', value)
                if m_val:
                    num = int(m_val.group(1))
                    if 1 < num < 64:
                        data.setdefault("ram", value)
            if "memory storage" in label or "internal storage" in label or "storage capacity" in label:
                data.setdefault("storage", value)
            if "colour" in label or "color" in label:
                data.setdefault("color", value)
            if "item model number" in label or "model number" in label:
                data.setdefault("model_number", value)
            if "model name" in label:
                data.setdefault("model", value)
            if "brand" in label:
                data.setdefault("brand", value)

        # ALL spec table sections Amazon uses
        for sel in [
            "#productDetails_techSpec_section_1 tr",
            "#productDetails_techSpec_section_2 tr",
            "#productDetails_db_sections tr",
            ".prodDetTable tr",
            ".a-expander-content tr",
        ]:
            for row in self.soup.select(sel):
                th = row.select_one("th")
                td = row.select_one("td")
                if th and td:
                    _parse_row(th.get_text(), td.get_text())

        # detailBullets (bullet-list style specs)
        for li in self.soup.select("#detailBullets_feature_div li"):
            spans = li.select("span.a-text-bold")
            if spans:
                label = spans[0].get_text().replace(":", "").strip()
                value = li.get_text().replace(spans[0].get_text(), "").strip(" :\n")
                _parse_row(label, value)

        # "Product Overview" po-* grid
        for row in self.soup.select(".po-feature-bullets li"):
            label_el = row.select_one("span.a-text-bold")
            value_el = row.select_one(".po-break-word")
            if label_el and value_el:
                _parse_row(label_el.get_text(), value_el.get_text())

        return data

    def _extract_flipkart(self) -> dict:
        data = {}

        title_el = (self.soup.select_one("span.VU-Z7G") or
                    self.soup.select_one("span.B_NuCI") or
                    self.soup.select_one("h1.B_NuCI") or
                    self.soup.select_one(".B_NuCI") or
                    self.soup.select_one("h1._6EBuvT") or
                    self.soup.select_one("h1"))
        data['title'] = title_el.get_text().strip() if title_el else ""

        for row in self.soup.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) >= 2:
                label = cells[0].get_text().strip().lower()
                value = cells[1].get_text().strip()
                if not value:
                    continue
                if "model name" in label:
                    data.setdefault("model", value)
                if "model number" in label or "model id" in label:
                    data.setdefault("model_number", value)
                if "internal storage" in label or ("storage" in label and "external" not in label):
                    data.setdefault("storage", value)
                if "ram" in label:
                    data.setdefault("ram", value)
                if "color" in label or "colour" in label:
                    data.setdefault("color", value)
                if "brand" in label:
                    data.setdefault("brand", value)

        # Key-value div fallback (newer Flipkart layouts)
        for li in self.soup.select("._3Fm-vq, ._21lJbe, .RmoJze, .WJdYP6"):
            text = li.get_text(" ", strip=True)
            for kw, field in [("RAM", "ram"), ("Storage", "storage"),
                               ("Color", "color"), ("Brand", "brand")]:
                if kw.lower() in text.lower():
                    val = re.split(rf'{kw}\s*[:\-]?\s*', text, flags=re.IGNORECASE)
                    if len(val) > 1:
                        v_str = val[1].strip().split()[0]
                        m_v = re.search(r'(\d+)', v_str)
                        if m_v:
                            num = int(m_v.group(1))
                            if 1 < num < 64:
                                data.setdefault(field, v_str)

        return data

    def _extract_croma(self) -> dict:
        data = {}

        title_el = (self.soup.select_one("h1.pd-title") or
                    self.soup.select_one("h1.product-name") or
                    self.soup.select_one("h1"))
        data['title'] = title_el.get_text().strip() if title_el else ""

        for (item_sel, label_sel, value_sel) in [
            (".cp-specification-item", ".cp-specification-label", ".cp-specification-value"),
            (".specification-item", ".specification-label", ".specification-value"),
            ("tr", "th", "td"),
        ]:
            for item in self.soup.select(item_sel):
                label_el = item.select_one(label_sel)
                value_el = item.select_one(value_sel)
                if not (label_el and value_el):
                    continue
                label = label_el.get_text().strip().lower()
                value = value_el.get_text().strip()
                if not value:
                    continue
                if "brand" in label:
                    data.setdefault("brand", value)
                if "model number" in label or "model no" in label:
                    data.setdefault("model_number", value)
                if "model name" in label:
                    data.setdefault("model", value)
                if "internal storage" in label or ("storage" in label and "external" not in label):
                    data.setdefault("storage", value)
                if "ram" in label:
                    m_v = re.search(r'(\d+)', value)
                    if m_v:
                        num = int(m_v.group(1))
                        if 1 < num < 64:
                            data.setdefault("ram", value)
                if "color" in label or "colour" in label:
                    data.setdefault("color", value)

        return data

    def _extract_reliance(self) -> dict:
        data = {}

        title_el = (self.soup.select_one("h1.pdp__title") or
                    self.soup.select_one("h1.product-title") or
                    self.soup.select_one("h1"))
        data['title'] = title_el.get_text().strip() if title_el else ""

        for (item_sel, label_sel, value_sel) in [
            ("li.pdp__tab-info__list__item",
             ".pdp__tab-info__list__label",
             ".pdp__tab-info__list__value"),
            ("li.spec-item", ".spec-label", ".spec-value"),
            ("tr", "th", "td"),
        ]:
            for item in self.soup.select(item_sel):
                label_el = item.select_one(label_sel)
                value_el = item.select_one(value_sel)
                if not (label_el and value_el):
                    continue
                label = label_el.get_text().strip().lower()
                value = value_el.get_text().strip()
                if not value:
                    continue
                if "brand" in label:
                    data.setdefault("brand", value)
                if "model name" in label:
                    data.setdefault("model", value)
                if "model number" in label or "model no" in label:
                    data.setdefault("model_number", value)
                if "internal storage" in label or ("storage" in label and "external" not in label):
                    data.setdefault("storage", value)
                if "ram" in label:
                    data.setdefault("ram", value)
                if "colour" in label or "color" in label:
                    data.setdefault("color", value)

        return data
