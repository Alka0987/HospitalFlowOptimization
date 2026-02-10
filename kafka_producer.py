
from kafka import KafkaProducer
import json
import time
import random
import uuid
import datetime
import os
from mock_kafka import MockKafkaProducer

def generate_random_patient():
    """Generate random patient attributes."""
    is_emergency = random.random() < 0.2  # 20% emergency
    
    if is_emergency:
        modality = random.choice(['Consultation', 'MRI', 'CT'])
        # Emergencies often have contrast
        with_contrast = random.choice([True, False]) 
    else:
        # Scheduled usually specific
        modality = random.choices(['Consultation', 'MRI', 'CT'], weights=[0.5, 0.3, 0.2])[0]
        with_contrast = random.random() < 0.3

    first_names = ["James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael", "Linda", "David", "Elizabeth", "William", "Barbara", "Richard", "Susan", "Joseph", "Jessica", "Thomas", "Sarah", "Charles", "Karen"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin"]

    return {
        'patient_id': str(uuid.uuid4())[:8],
        'patient_name': f"{random.choice(first_names)} {random.choice(last_names)}",
        'arrival_time': datetime.datetime.now().isoformat(),
        'patient_type': 'Emergency' if is_emergency else 'Scheduled',
        'modality': modality,
        'is_emergency': is_emergency,
        'age': int(random.gauss(45, 15)),  
        'with_contrast': with_contrast
    }

def run_producer():
    print("Starting Kafka Producer...")
    print("Connecting to Kafka at localhost:9092...")
    
    try:
        producer = KafkaProducer(
            bootstrap_servers=['localhost:9092'],
            value_serializer=lambda x: json.dumps(x).encode('utf-8')
        )
        print("Connected to Kafka!")
    except Exception as e:
        print(f"Failed to connect to REAL Kafka: {e}")
        print("Falling back to MOCK Kafka (for testing without Docker)...")
        producer = MockKafkaProducer()

    try:
        while True:
            # Generate Event
            patient_data = generate_random_patient()
            
            # Send to Kafka
            producer.send('hospital_arrivals', value=patient_data)
            print(f"[PRODUCER] Sent: {patient_data['patient_name']} ({patient_data['modality']})")
            
            # Flush periodically
            if random.random() < 0.1:
                producer.flush()
                
            time.sleep(random.randint(1, 4))
            
    except KeyboardInterrupt:
        print("\nProducer stopped.")
    except Exception as e:
        print(f"Producer Error: {e}")
    finally:
        producer.close()

if __name__ == "__main__":
    run_producer()
