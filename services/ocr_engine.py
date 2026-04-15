import re
import os
import csv
from thefuzz import process, fuzz
from paddleocr import PaddleOCR

# Initialize PaddleOCR (Downloads models on first run)
print("[SYSTEM] Initializing PaddleOCR Engine...")
ocr_model = PaddleOCR(use_angle_cls=True, lang='en', use_gpu=False, show_log=False)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TXT_FILE_PATH = os.path.join(BASE_DIR, 'data', 'product.txt')

# Standardized Lists
NOISE_WORDS = {"tablet", "capsule", "generic", "pharmacy", "refill", "take", "prescription", "qty", "unit", "units", "iu", "usp", "discard", "expires", "date"}
PII_PREFIXES = {"dr", "md", "rx", "phd", "patient", "name", "dr.", "md.", "rx.", "prescriber"}
PHARMACIES = {"cvs", "walgreens", "publix", "walmart", "riteaid", "kroger", "target", "costco"}
MANUFACTURERS = {"teva", "aurobindo", "amneal", "pfizer", "mylan", "lannett", "zydus", "sandoz"}
COMBINED_NOISE = NOISE_WORDS | PII_PREFIXES | PHARMACIES | MANUFACTURERS

FREQUENCIES = ["three times a day", "twice a day", "every 12 hours", "every 10 hours", "every 8 hours", "every 6 hours", "every 2 hours", "every 4 hours", "each week","everyday", "daily", "as needed"]
TIMES = ["bedtime", "morning", "evening", "with meals", "before meals"]

FREQUENCY_MAP = {
    "daily": "Once daily", "everyday": "Once daily", "every day": "Once daily", "once a day": "Once daily",
    "twice a day": "Twice daily", "bid": "Twice daily", "two times": "Twice daily",
    "three times": "Three times daily", "tid": "Three times daily",
    "four times": "Four times daily", "qid": "Four times daily",
    "every 12 hours": "Twice daily", "every 8 hours": "Three times daily", 
    "every 6 hours": "Four times daily", "every 4 hours": "Four times daily",
    "every other day": "Every other day",
    "weekly": "Weekly", "once a week": "Weekly",
    "as needed": "As needed", "prn": "As needed"
}

ROUTE_MAP = {
    "oral": "Oral", "mouth": "Oral",
    "sublingual": "Sublingual", "under the tongue": "Sublingual", "under tongue": "Sublingual",
    "enteral": "Enteral", "feeding tube": "Enteral",
    "topical": "Topical", "transdermal": "Transdermal", "patch": "Transdermal",
    "ophthalmic": "Ophthalmic", "eye": "Ophthalmic",
    "otic": "Otic", "ear": "Otic",
    "nasal": "Nasal", "nares": "Nasal", "nose": "Nasal", "nostril": "Nasal",
    "rectal": "Rectal", "rectum": "Rectal",
    "vaginal": "Vaginal", "vagina": "Vaginal",
    "inhalation": "Inhalation", "nebulizer": "Inhalation", "puff": "Inhalation", "puffs": "Inhalation",
    "injection": "Injection", "intravenous": "Intravenous", "iv": "Intravenous",
    "subcutaneous": "Subcutaneous", "sq": "Subcutaneous", "subq": "Subcutaneous", "subcut": "Subcutaneous",
    "intramuscular": "Intramuscular", "im": "Intramuscular"
}

def load_fda_data():
    """Loads FDA data from product.txt for name and route matching."""
    drug_names = set()
    routes = set()
    barcode_db = {}
    
    if not os.path.exists(TXT_FILE_PATH):
        print(f"[ERROR] FDA database missing at {TXT_FILE_PATH}")
        return [], [], {}

    with open(TXT_FILE_PATH, 'r', encoding='utf-8', errors='replace') as file:
        reader = csv.DictReader(file, delimiter='\t')
        for row in reader:
            brand = row.get('PROPRIETARYNAME', '').title()
            if brand:
                drug_names.add(brand)
                if row.get('PRODUCTNDC'):
                    barcode_db[row['PRODUCTNDC'].replace('-', '')] = brand
            
            if row.get('ROUTENAME'):
                for r in row['ROUTENAME'].split(';'):
                    routes.add(r.strip().title())
                    
    return list(drug_names), list(routes), barcode_db

ALL_DRUG_NAMES, VALID_ROUTES, BARCODE_DB = load_fda_data()
ALL_DRUG_NAMES_SET = set(ALL_DRUG_NAMES) # Moved to global scope for fast O(1) lookups

def extract_text_from_frame(frame):
    """Uses PaddleOCR to extract text fragments from image."""
    result = ocr_model.ocr(frame, cls=True)
    valid_lines = []
    
    if result and result[0]:
        for line in result[0]:
            box = line[0]           # [X, Y] coordinates
            text = line[1][0]       # line[1][0] is the recognized text string
            confidence = line[1][1] # AI certainty score
            
            # Confidence Thresholding: ignore smudges and low-light artifacts
            if confidence > 0.75: 
                # Spatial Geometry: Calculate vertical center
                y_center = sum([p[1] for p in box]) / 4
                valid_lines.append((y_center, text))
                
    # Sort text physically top-to-bottom
    valid_lines.sort(key=lambda x: x[0])
    raw_text = " ".join([line[1] for line in valid_lines])
    return raw_text.strip()

def parse_medication_label(raw_text, patient_name_words=None):
    """Parses text using safe regex and fuzzy matching against FDA data."""
    if patient_name_words is None:
        patient_name_words = []

    # Normalization: keep decimals, slashes, and COMMAS
    clean_text = re.sub(r'[^\w\s\.\-\/,]', ' ', raw_text)
    search_text = clean_text.lower()
    results = {}

    # Free text special instructions extraction
    direction_pattern = r'(?i)\b(take|apply|use|give|inhale|insert|instill|inject|place|chew|dissolve)\b.*?(?:(?=\b(?:qty|rx|dr\.|dr|md|patient|discard|refill|expires|date)\b)|$)'
    direction_match = re.search(direction_pattern, raw_text)
    if direction_match:
        results['special_instructions'] = direction_match.group(0).strip()

    # Dosage extraction with multiple patterns (e.g., 500mg, 1.25mg, 50,000 UNIT)
    dosage_patterns = [
        r'(?i)(\d+[\.,]\d+\s*(?:M[G6]|MC[G6]|ML|G))',        # Decimals: 1.25mg
        r'(?i)(\d+[\d,]*\s*(?:UNIT|UNITS|IU))',         # Units: 50,000 UNIT
        r'(?i)\b(\d+\s*(?:M[G6]|MC[G6]|ML|G))\b'                  # Standard: 500mg
    ]

    found_dosages = []
    seen_normalized = set()
    for pattern in dosage_patterns:
        matches = re.findall(pattern, clean_text)
        for match in matches:
            # Apply OCR typo fixes
            fixed_dosage = match.upper().replace('O', '0').replace('A', '4').replace('S', '5').replace('I', '1').replace('L', '1')
            
            # Remove all spaces to check for true duplicates (makes "300 MG" == "300MG")
            normalized = fixed_dosage.replace(" ", "")
            
            if normalized not in seen_normalized:
                seen_normalized.add(normalized)
                found_dosages.append(fixed_dosage.lower().strip())

    if found_dosages:
        results['dosage'] = " / ".join(found_dosages)

    # Extract Route, Frequency, Timing with direct and safe dictionary matching
    for key, canonical_freq in FREQUENCY_MAP.items():
        if re.search(r'\b' + re.escape(key) + r'\b', search_text):
            results['frequency'] = canonical_freq
            break

    for key, canonical_route in ROUTE_MAP.items():
        if re.search(r'\b' + re.escape(key) + r'\b', search_text):
            results['route'] = canonical_route
            break

    for time in TIMES:
        if time in search_text:
            results['scheduled_time'] = time.capitalize()
            break

    safe_text = search_text.replace("directed", "")

    # Fuzzy matching (Route, Frequency, Time)
    if 'route' not in results and VALID_ROUTES:
        route, score = process.extractOne(safe_text, VALID_ROUTES, scorer=fuzz.partial_ratio)
        if score > 80: results['route'] = route.capitalize()

    # Throttled to >= 90 score to prevent hallucinating instructions unless certain
    if 'frequency' not in results:
        freq, f_score = process.extractOne(safe_text, FREQUENCIES, scorer=fuzz.partial_ratio)
        if f_score >= 90: results['frequency'] = freq.capitalize()

    if 'scheduled_time' not in results:
        time, t_score = process.extractOne(safe_text, TIMES, scorer=fuzz.partial_ratio)
        if t_score >= 90: results['scheduled_time'] = time.capitalize()

    # Fuzzy matching (Medication Name)
    # Added a filter to ignore "MG" or "UNIT" as a drug name candidate
    dosage_keywords = {"MG", "MCG", "ML", "UNIT", "UNITS", "IU"}
    words = re.findall(r'\b[A-Za-z0-9]{2,}\b', clean_text.upper()) # Lowered to 4 to catch short names
    best_name = None
    high_score = 0

    for word in words:
        word_lower = word.lower()
        # Avoid matching keywords as drug names (Includes PII/PHI dynamic blacklists)
        if (word_lower in COMBINED_NOISE or 
            word_lower in FREQUENCY_MAP or 
            word.upper() in dosage_keywords or 
            word_lower in patient_name_words): 
            continue

        # First check for exact match in the set (fast)
        if word.upper() in ALL_DRUG_NAMES_SET:
            best_name = word.title()
            high_score = 100
            break
            
        name, score = process.extractOne(word, ALL_DRUG_NAMES, scorer=fuzz.ratio)
        if score > 85:
            # PENALTY: Prevent hallucinating Extended Release versions
            if " ER" in name and "ER" not in word.upper():
                score -= 20
            if " XR" in name and "XR" not in word.upper():
                score -= 20

            if score > high_score:
                high_score = score
                best_name = name
    
    if best_name:
        results['medication_name'] = best_name.title()

    return results