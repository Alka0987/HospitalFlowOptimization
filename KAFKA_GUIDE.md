# Kafka Integration Guide (Event-Driven Architecture)

This guide details how we would refactor the current system to use **Apache Kafka**. This decouples the *Simulation* (Data Source) from the *Processing* (ML/DB), allowing the system to handle massive scale (e.g., thousands of patients per second).

## 1. The Architecture Shift

### Current (Monolithic / Direct)
`Simulation` ➔ **[Predicts & Writes]** ➔ `MySQL` ➔ `Dashboard`
*(Limitation: If the database is slow, the reception simulation slows down. If the ML model is heavy, potential lag.)*

### Proposed (Event-Driven w/ Kafka)
`Simulation` ➔ **[Events]** ➔ `Kafka` ➔ **[Consumer]** ➔ `MySQL` ➔ `Dashboard`

1.  **Producer (`simulation_producer.py`)**: Just dumps raw data ("Patient Arrived") to Kafka. Extremely fast. Doesn't care about DB or ML.
2.  **Broker (Kafka)**: Buffers the messages. Can handle bursts.
3.  **Consumer (`backend_processor.py`)**: Reads messages, runs the heavy ML prediction, and writes to MySQL.
4.  **Dashboard**: Unchanged (reads from MySQL).

## 2. Implementation Steps

### Step 1: Install Dependencies
```bash
pip install kafka-python
# You also need a running Kafka Broker (usually via Docker)
# docker run -p 9092:9092 apache/kafka
```

### Step 2: Create the Producer (`kafka_producer.py`)
Replaces `simulation.py`.

```python
from kafka import KafkaProducer
import json
import time

# Initialize Producer
producer = KafkaProducer(
    bootstrap_servers=['localhost:9092'],
    value_serializer=lambda x: json.dumps(x).encode('utf-8')
)

def run_simulation():
    while True:
        # Generate random patient data (Raw, no predictions yet)
        patient_data = generate_random_patient() 
        
        # Send event to Topic
        producer.send('hospital_arrivals', value=patient_data)
        print(f"Sent: {patient_data['patient_name']}")
        
        time.sleep(random.randint(1, 4))
```

### Step 3: Create the Consumer (`kafka_consumer.py`)
This is the new "Brain" of the system.

```python
from kafka import KafkaConsumer
from db_manager import DatabaseManager
from predict import predict_wait_time
import json

consumer = KafkaConsumer(
    'hospital_arrivals',
    bootstrap_servers=['localhost:9092'],
    value_deserializer=lambda x: json.loads(x.decode('utf-8'))
)

db = DatabaseManager()

print("Listening for patients...")

for message in consumer:
    patient_data = message.value
    
    # PERFORMS THE HEAVY LIFTING HERE
    prediction = predict_wait_time(
        modality=patient_data['modality'],
        is_emergency=patient_data['is_emergency'],
        current_queue=db.get_queue_count() # Need to add this helper
    )
    
    # ENRICH DATA
    patient_data['predicted_wait_minutes'] = prediction
    
    # SAVE TO DB
    db.add_patient(patient_data)
    print(f"Processed: {patient_data['patient_name']} -> {prediction}m wait")
```

## 3. Benefits of this Approach
1.  **Buffering**: If the DB goes down for 5 minutes, the Simulation can keep running. Kafka holds the messages until the Consumer comes back online.
2.  **Scale**: You can run 10 Consumers in parallel to handle 100x more patients.
3.  **Real-Time Analytics**: Other systems (e.g., a Notification Service) can listen to the same `hospital_arrivals` topic to send SMS alerts without touching the main database.
