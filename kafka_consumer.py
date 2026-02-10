
from kafka import KafkaConsumer
from db_manager import DatabaseManager
from predict import predict_wait_time
from train_model import HospitalQueuePredictor
import json
import os
from mock_kafka import MockKafkaConsumer
import time
from datetime import datetime

def load_ai_model():
    """Load the trained ML model."""
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        model_path = os.path.join(base_dir, "queue_model.joblib")
        print(f"Loading model from {model_path}...")
        return HospitalQueuePredictor.load(model_path)
    except Exception as e:
        print(f"FATAL: Could not load model: {e}")
        return None

def process_patient(patient_data, db, model):
    """Run prediction and save to DB."""
    
    # 1. Get Current Queue Metrics from DB
    active_patients = db.get_active_patients()
    queue_length = len(active_patients) if active_patients else 0
    
    # Simplified proxy for contrast queue
    contrast_count = 0
    if active_patients:
        contrast_count = sum(1 for row in active_patients if row.get('modality') in ['MRI', 'CT'])
    
    # 2. Predict Wait Time
    # Convert ISO string back to datetime object for hour calculation
    arrival_dt = datetime.fromisoformat(patient_data['arrival_time'])
    
    predicted_wait = predict_wait_time(
        hour=arrival_dt.hour,
        is_emergency=patient_data['is_emergency'],
        modality=patient_data['modality'],
        staff_on_duty=6, # Assume constant for sim
        current_queue=queue_length,
        avg_age=patient_data.get('age', 45),
        contrast_queue=contrast_count,
        model=model
    )
    
    # 3. Add to Database
    patient_record = {
        'patient_id': patient_data['patient_id'],
        'patient_name': patient_data['patient_name'],
        'arrival_time': arrival_dt, # DB needs datetime object
        'patient_type': patient_data['patient_type'],
        'modality': patient_data['modality'],
        'predicted_wait_minutes': predicted_wait
    }
    
    db.add_patient(patient_record)
    
    print(f"[CONSUMER] Processed: {patient_data['patient_name']} -> {predicted_wait:.1f}m wait (Q: {queue_length})")

def run_consumer():
    print("Starting Kafka Consumer...")
    
    # Initialize DB
    db = DatabaseManager()
    if not db.init_db():
        print("Failed to connect to DB. Retrying in 5s...")
        time.sleep(5)
        # Simple retry logic could be added here
        
    # Load Model
    model = load_ai_model()
    if not model:
        return

    # Connect to Kafka
    print("Connecting to Kafka at localhost:9092...")
    try:
        consumer = KafkaConsumer(
            'hospital_arrivals',
            bootstrap_servers=['localhost:9092'],
            auto_offset_reset='latest',
            enable_auto_commit=True,
            group_id='hospital_group_1',
            value_deserializer=lambda x: json.loads(x.decode('utf-8'))
        )
        print("Connected to Kafka! Listening for patients...")
    except Exception as e:
        print(f"Failed to connect to REAL Kafka: {e}")
        print("Falling back to MOCK Kafka (reading from file)...")
        consumer = MockKafkaConsumer('hospital_arrivals')

    try:
        for message in consumer:
            patient_data = message.value
            process_patient(patient_data, db, model)
            
    except KeyboardInterrupt:
        print("\nConsumer stopped.")
    except Exception as e:
        print(f"Consumer Error: {e}")
    finally:
        consumer.close()
        db.close()

if __name__ == "__main__":
    run_consumer()
