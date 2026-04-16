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

TIMES = ["bedtime", "morning", "evening", "with meals", "before meals"]

FREQUENCY_MAP = {
    "every other day": "Every other day",
    "every 12 hours": "Twice daily", 
    "every 8 hours": "Three times daily", 
    "every 6 hours": "Four times daily", 
    "every 4 hours": "Four times daily",
    "three times a day": "Three times daily",
    "four times a day": "Four times daily",
    "twice a day": "Twice daily",
    "once a day": "Once daily",
    "three times daily": "Three times daily",
    "four times daily": "Four times daily",
    "twice daily": "Twice daily",
    "three times": "Three times daily",
    "four times": "Four times daily",
    "two times": "Twice daily",
    "3 times": "Three times daily",
    "4 times": "Four times daily",
    "2 times": "Twice daily",
    "1 time": "Once daily",
    "once a week": "Weekly",
    "every day": "Once daily",
    "everyday": "Once daily",
    "as needed": "As needed", 
    "daily": "Once daily", 
    "weekly": "Weekly", 
    "bid": "Twice daily", 
    "tid": "Three times daily",
    "qid": "Four times daily", 
    "prn": "As needed"
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
            box = line[0]           
            text = line[1][0]       
            confidence = line[1][1] 
            if confidence > 0.75: 
                y_center = sum([p[1] for p in box]) / 4
                valid_lines.append((y_center, text))
                
    valid_lines.sort(key=lambda x: x[0])
    raw_text = " ".join([line[1] for line in valid_lines])
    return raw_text.strip()

def parse_medication_label(raw_text, patient_name_words=None):
    """Parses text using safe regex and fuzzy matching against FDA data."""
    if patient_name_words is None:
        patient_name_words = []

    clean_text = re.sub(r'[^\w\s\.\-\/,]', ' ', raw_text)
    search_text = clean_text.lower()
    results = {}

    direction_pattern = r'(?i)\b(take|apply|use|give|inhale|insert|instill|inject|place|chew|dissolve)\b.*?(?:(?=\b(?:qty|rx|dr\.|dr|md|patient|discard|refill|expires|date)\b)|$)'
    direction_match = re.search(direction_pattern, raw_text)
    if direction_match:
        results['special_instructions'] = direction_match.group(0).strip()

    dosage_patterns = [
        r'(?i)(\d+[\.,]\d+\s*(?:M[G6]|MC[G6]|ML|G))',        
        r'(?i)(\d+[\d,]*\s*(?:UNIT|UNITS|IU))',         
        r'(?i)\b(\d+\s*(?:M[G6]|MC[G6]|ML|G))\b'                  
    ]

    found_dosages = []
    seen_normalized = set()
    for pattern in dosage_patterns:
        matches = re.findall(pattern, clean_text)
        for match in matches:
            fixed_dosage = match.upper().replace('O', '0').replace('A', '4').replace('S', '5').replace('I', '1').replace('L', '1')
            normalized = fixed_dosage.replace(" ", "")
            if normalized not in seen_normalized:
                seen_normalized.add(normalized)
                found_dosages.append(fixed_dosage.lower().strip())

    if found_dosages:
        results['dosage'] = " / ".join(found_dosages)

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

    if 'route' not in results and VALID_ROUTES:
        route, score = process.extractOne(safe_text, VALID_ROUTES, scorer=fuzz.partial_ratio)
        if score > 80: results['route'] = route.capitalize()

    if 'scheduled_time' not in results:
        time, t_score = process.extractOne(safe_text, TIMES, scorer=fuzz.partial_ratio)
        if t_score >= 90: results['scheduled_time'] = time.capitalize()

    # --- UPDATED N-GRAM MEDICATION NAME EXTRACTION ---
    dosage_keywords = {"MG", "MCG", "ML", "UNIT", "UNITS", "IU"}
    
    # \b[A-Za-z0-9]+\b grabs ALL alphanumeric words, including single letters like "D" in Vitamin D3
    raw_words = re.findall(r'\b[A-Za-z0-9]+\b', clean_text.upper()) 
    
    # Generate 1-word, 2-word, and 3-word combinations (N-Grams)
    candidates = []
    for i in range(len(raw_words)):
        candidates.append(raw_words[i])
        if i < len(raw_words) - 1:
            candidates.append(f"{raw_words[i]} {raw_words[i+1]}")
        if i < len(raw_words) - 2:
            candidates.append(f"{raw_words[i]} {raw_words[i+1]} {raw_words[i+2]}")

    # Sort candidates by length (longer phrases first) to prioritize multi-word drug names over single words
    candidates.sort(key=lambda x: len(x.split()), reverse=True)

    best_name = None
    high_score = 0

    for phrase in candidates:
        phrase_lower = phrase.lower()
        phrase_upper = phrase.upper()
        
        # Skip pure junk phrases (like a single floating "D" that isn't attached to anything)
        if len(phrase) < 3 and " " not in phrase and not any(char.isalpha() for char in phrase):
            continue
            
        # Avoid matching keywords by breaking the phrase down and checking intersections
        phrase_words_lower = set(phrase_lower.split())
        phrase_words_upper = set(phrase_upper.split())
        
        if (phrase_words_lower.intersection(COMBINED_NOISE) or 
            phrase_words_lower.intersection(FREQUENCY_MAP) or 
            phrase_words_upper.intersection(dosage_keywords) or 
            phrase_words_lower.intersection(set(patient_name_words))): 
            continue

        if phrase_upper in ALL_DRUG_NAMES_SET:
            best_name = phrase.title()
            high_score = 100
            break
            
        name, score = process.extractOne(phrase, ALL_DRUG_NAMES, scorer=fuzz.ratio)
        if score > 85:
            # ER/XR Hallucination Penalty
            if " ER" in name and "ER" not in phrase_upper:
                score -= 20
            if " XR" in name and "XR" not in phrase_upper:
                score -= 20

            if score > high_score:
                high_score = score
                best_name = name
    
    if best_name:
        results['medication_name'] = best_name.title()

    return results