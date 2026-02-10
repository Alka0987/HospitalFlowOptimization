import mysql.connector
from db_config import DB_CONFIG
from datetime import datetime

class DatabaseManager:
    def __init__(self):
        self.config = DB_CONFIG
        self.conn = None
        self.cursor = None

    def connect(self):
        """Establish connection to MySQL."""
        try:
            # Connect to valid database if it exists, else connect to server to create it
            self.conn = mysql.connector.connect(
                host=self.config['host'],
                user=self.config['user'],
                password=self.config['password']
            )
            self.cursor = self.conn.cursor(dictionary=True)
            return True
        except mysql.connector.Error as err:
            print(f"Error connecting to MySQL: {err}")
            return False

    def init_db(self):
        """Initialize database and tables."""
        if not self.connect():
            return False

        try:
            # Create Database
            self.cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.config['database']}")
            self.cursor.execute(f"USE {self.config['database']}")

            # Reset Table to apply schema changes (for dev/demo purposes)
            self.cursor.execute("DROP TABLE IF EXISTS patients")

            # Create Patients Table
            # Status: WAITING, COMPLETED, LEFT
            create_table_query = """
            CREATE TABLE IF NOT EXISTS patients (
                id INT AUTO_INCREMENT PRIMARY KEY,
                patient_id VARCHAR(50),
                patient_name VARCHAR(100),
                arrival_time DATETIME,
                patient_type VARCHAR(20),
                modality VARCHAR(20),
                predicted_wait_minutes FLOAT,
                elapsed_wait_minutes FLOAT DEFAULT 0.0,
                status VARCHAR(20) DEFAULT 'WAITING',
                is_alerted TINYINT(1) DEFAULT 0
            )
            """
            self.cursor.execute(create_table_query)
            self.conn.commit()
            print("Database and tables initialized successfully.")
            return True
        except mysql.connector.Error as err:
            print(f"Error initializing database: {err}")
            return False
        finally:
            self.close()

    def add_patient(self, patient_data):
        """
        Add a new patient to the queue.
        patient_data: dict with keys (patient_id, patient_name, arrival_time, patient_type, modality, predicted_wait_minutes)
        """
        self.connect()
        self.cursor.execute(f"USE {self.config['database']}")
        
        query = """
        INSERT INTO patients (patient_id, patient_name, arrival_time, patient_type, modality, predicted_wait_minutes, status)
        VALUES (%s, %s, %s, %s, %s, %s, 'WAITING')
        """
        values = (
            patient_data['patient_id'],
            patient_data['patient_name'],
            patient_data['arrival_time'],
            patient_data['patient_type'],
            patient_data['modality'],
            patient_data['predicted_wait_minutes']
        )
        
        try:
            self.cursor.execute(query, values)
            self.conn.commit()
            return self.cursor.lastrowid
        except mysql.connector.Error as err:
            print(f"Error adding patient: {err}")
            return None
        finally:
            self.close()

    def get_active_patients(self):
        """Retrieve all currently active patients (WAITING or WITH_DOCTOR)."""
        if not self.connect():
             return []
        
        try:
            self.cursor.execute(f"USE {self.config['database']}")
            
            # Select active patients
            query = "SELECT * FROM patients WHERE status IN ('WAITING', 'WITH_DOCTOR') ORDER BY arrival_time ASC"
            self.cursor.execute(query)
            result = self.cursor.fetchall()
            return result
        except mysql.connector.Error as err:
            print(f"Error fetching active patients: {err}")
            return []
        finally:
             self.close()

    def update_patient_status(self, patient_id, status):
        """Update status (e.g., to COMPLETED)."""
        if not self.connect():
            return

        try:
            self.cursor.execute(f"USE {self.config['database']}")
            query = "UPDATE patients SET status = %s WHERE patient_id = %s"
            self.cursor.execute(query, (status, patient_id))
            self.conn.commit()
        except mysql.connector.Error as err:
            print(f"Error updating status: {err}")
        finally:
            self.close()
            
    def update_elapsed_time(self, patient_id, elapsed_minutes):
        """Update how long the patient has been waiting."""
        if not self.connect():
            return

        try:
            self.cursor.execute(f"USE {self.config['database']}")
            query = "UPDATE patients SET elapsed_wait_minutes = %s WHERE patient_id = %s"
            self.cursor.execute(query, (elapsed_minutes, patient_id))
            self.conn.commit()
        except mysql.connector.Error as err:
            print(f"Error updating elapsed time: {err}")
        finally:
            self.close()

    def close(self):
        if self.cursor:
            try:
                self.cursor.close()
            except: pass
        if self.conn:
            try:
                self.conn.close()
            except: pass

    def get_queue_stats(self):
        """Get aggregated stats for analytics."""
        if not self.connect():
            return []

        try:
            self.cursor.execute(f"USE {self.config['database']}")
            
            # Breakdown by modality
            query = """
            SELECT 
                modality, 
                COUNT(*) as count, 
                AVG(predicted_wait_minutes) as avg_wait 
            FROM patients 
            WHERE status = 'WAITING' 
            GROUP BY modality
            """
            self.cursor.execute(query)
            stats = self.cursor.fetchall()
            return stats
        except mysql.connector.Error as err:
            print(f"Error getting queue stats: {err}")
            return []
        finally:
            self.close()

if __name__ == "__main__":
    # Test initialization
    db = DatabaseManager()
    db.init_db()
