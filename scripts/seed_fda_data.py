# scripts/seed_fda_data.py
import sqlite3
import csv
import os
import time

# Safely locate the database and the FDA product file
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'medrec.db')
TXT_PATH = os.path.join(BASE_DIR, 'data', 'product.txt')

def setup_database_table(cursor):
    """Creates the fda_medications table if it doesn't exist, with an index on NDC for fast lookups."""
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fda_medications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ndc TEXT,              -- NEW COLUMN
            brand_name TEXT,
            generic_name TEXT
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_ndc ON fda_medications(ndc)') # Index for speed!

def seed_data():
    """Reads the FDA product.txt file and seeds the fda_medications table in SQLite."""
    if not os.path.exists(TXT_PATH):
        print(f"Error: Could not find {TXT_PATH}")
        return

    print(f"Opening database: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    setup_database_table(cursor)

    print(f"Reading data from: {TXT_PATH}")
    start_time = time.time()
    
    data_to_insert = []
    # FDA files sometimes have weird characters, so errors='ignore' prevents crashes
    with open(TXT_PATH, 'r', encoding='utf-8', errors='ignore') as file:
        # Tell Python the file uses Tabs (\t), not commas
        reader = csv.DictReader(file, delimiter='\t') 
        
        for row in reader:
            ndc = row.get('PRODUCTNDC', '').strip().replace('-', '') # Store as 00020152
            brand = row.get('PROPRIETARYNAME', '').strip().upper()
            generic = row.get('NONPROPRIETARYNAME', '').strip().upper()
            
            if brand or generic: 
                data_to_insert.append((ndc, brand, generic))

    # Perform the high-speed batch insert
    print(f"Injecting {len(data_to_insert):,} records into SQLite. This might take a few seconds...")
    cursor.executemany('''
        INSERT INTO fda_medications (ndc, brand_name, generic_name)
        VALUES (?, ?, ?)
    ''', data_to_insert)

    conn.commit()
    conn.close()

    elapsed_time = time.time() - start_time
    print(f"Success: Database seeded with {len(data_to_insert):,} medications in {elapsed_time:.2f} seconds.")

def is_database_seeded():
    """Quickly checks if the FDA data is already in the database."""
    if not os.path.exists(DB_PATH):
        return False
        
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        # Just ask for the count of rows (super fast)
        cursor.execute("SELECT COUNT(*) FROM fda_medications")
        count = cursor.fetchone()[0]
        conn.close()
        # If we have more than 10,000 rows, it's safely seeded
        return count > 10000 
    except sqlite3.OperationalError:
        # The table doesn't even exist yet
        return False
    
if __name__ == "__main__":
    seed_data()