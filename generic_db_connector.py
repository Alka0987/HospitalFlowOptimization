
import mysql.connector
from kafka import KafkaProducer
import json
import time
import datetime

class GenericDBConnector:
    def __init__(self, config_file):
        with open(config_file, 'r') as f:
            self.config = json.load(f)
            
        self.last_check = datetime.datetime.now() - datetime.timedelta(days=1) # Start from 1 day ago or persistent state
        
        # Connect to Source DB
        print(f"Connecting to Source DB ({self.config['db_type']})...")
        self.conn = mysql.connector.connect(**self.config['db_connection'])
        self.cursor = self.conn.cursor(dictionary=True)
        
        # Connect to Kafka
        print("Connecting to Kafka...")
        self.producer = KafkaProducer(
            bootstrap_servers=self.config['kafka_bootstrap'],
            value_serializer=lambda x: json.dumps(x, default=str).encode('utf-8')
        )

    def poll(self):
        """Poll the database for new records."""
        query = self.config['query']
        params = (self.last_check,)
        
        print(f"Polling since {self.last_check}...")
        self.cursor.execute(query, params)
        rows = self.cursor.fetchall()
        
        if not rows:
            print("No new records.")
            return

        print(f"Found {len(rows)} new records.")
        
        for row in rows:
            # 1. Normalize/Map
            msg = self.map_row(row)
            
            # 2. Add Source Metadata
            msg['source_hospital'] = self.config['hospital_id']
            msg['ingested_at'] = datetime.datetime.now().isoformat()
            
            # 3. Send to Kafka
            self.producer.send(self.config['kafka_topic'], value=msg)
            
            # Update Checkpoint (using the column specified in config)
            # Assuming strictly increasing timestamp for simplicity
            row_timestamp = row[self.config['timestamp_column']]
            if row_timestamp > self.last_check:
                self.last_check = row_timestamp
        
        self.producer.flush()
        print(f"Sent {len(rows)} events to {self.config['kafka_topic']}")

    def map_row(self, row):
        """Transform row based on mapping config."""
        mapped = {}
        for target_col, source_col in self.config['mapping'].items():
            if source_col in row:
                mapped[target_col] = row[source_col]
            else:
                mapped[target_col] = None # Or default value
        return mapped

    def run(self):
        print(f"Starting Connector for {self.config['hospital_id']}...")
        try:
            while True:
                self.poll()
                time.sleep(self.config['poll_interval_sec'])
        except KeyboardInterrupt:
            print("Stopping...")
        finally:
            self.cursor.close()
            self.conn.close()
            self.producer.close()

if __name__ == "__main__":
    # Example Usage
    connector = GenericDBConnector("hospital_a_config.json")
    connector.run()
