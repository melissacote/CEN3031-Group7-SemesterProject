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
FREQUENCIES = ["everyday", "daily", "twice a day", "three times a day", "every 4 hours", "as needed"]
TIMES = ["bedtime", "morning", "evening", "with meals", "before meals"]

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

def extract_text_from_frame(frame):
    """Uses PaddleOCR to extract text fragments from image."""
    result = ocr_model.ocr(frame, cls=True)
    raw_text = ""
    if result and result[0]:
        for line in result[0]:
            # line[1][0] is the recognized text string
            raw_text += line[1][0] + " "
    return raw_text.strip()

def parse_medication_label(raw_text):
    """Parses text using safe regex and fuzzy matching against FDA data."""
    # Normalization: keep decimals, slashes, and COMMAS
    clean_text = re.sub(r'[^\w\s\.\-\/,]', ' ', raw_text)
    results = {}

    # Dosage Extraction with multiple patterns (e.g., 500mg, 1.25mg, 50,000 UNIT)
    dosage_patterns = [
        r'(?i)(\d+[\.,]\d+\s*(?:MG|MCG|ML|G))',        # Decimals: 1.25mg
        r'(?i)(\d+[\d,]*\s*(?:UNIT|UNITS|IU))',         # Units: 50,000 UNIT
        r'(?i)(\d+\s*(?:MG|MCG|ML|G))'                  # Standard: 500mg
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

    # Fuzzy matching (Route, Frequency, Time)
    if VALID_ROUTES:
        route, score = process.extractOne(clean_text, VALID_ROUTES, scorer=fuzz.partial_ratio)
        if score > 60: results['route'] = route

    freq, f_score = process.extractOne(clean_text, FREQUENCIES, scorer=fuzz.partial_ratio)
    if f_score > 60: results['frequency'] = freq

    time, t_score = process.extractOne(clean_text, TIMES, scorer=fuzz.partial_ratio)
    if t_score > 60: results['scheduled_time'] = time

    # Fuzzy matching (Medication Name)
    words = re.findall(r'\b[A-Za-z0-9]{4,}\b', clean_text.upper()) # Lowered to 4 to catch short names
    best_name = None
    high_score = 0
    for word in words:
        name, score = process.extractOne(word, ALL_DRUG_NAMES)
        if score > 85 and score > high_score:
            high_score = score
            best_name = name
    
    if best_name:
        results['medication_name'] = best_name.title()

    return results