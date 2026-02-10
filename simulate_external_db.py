
import mysql.connector
import datetime
import time
import random

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Alka@52092025',
    'database': 'hospital_flow'
}

def setup_db():
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    # Create a dummy table to simulate an external hospital DB
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS local_patients (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100),
            entered_at DATETIME
        )
    """)
    conn.commit()
    print("Created 'local_patients' table.")
    
    try:
        while True:
            # Insert a random patient every few seconds
            name = f"Patient_{random.randint(1000, 9999)}"
            entered_at = datetime.datetime.now()
            
            cursor.execute("INSERT INTO local_patients (name, entered_at) VALUES (%s, %s)", (name, entered_at))
            conn.commit()
            print(f"Inserted {name} at {entered_at}")
            
            time.sleep(random.randint(2, 6))
    except KeyboardInterrupt:
        print("Stopping simulation...")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    setup_db()
