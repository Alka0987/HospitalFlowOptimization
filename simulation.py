import time
import os
import random
import uuid
from datetime import datetime
from db_manager import DatabaseManager
from predict import predict_wait_time
from train_model import HospitalQueuePredictor

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
        'arrival_time': datetime.now(),
        'patient_type': 'Emergency' if is_emergency else 'Scheduled',
        'modality': modality,
        'is_emergency': is_emergency,
        'age': int(random.gauss(45, 15)),  # Normal dist around 45
        'with_contrast': with_contrast
    }

def process_departures(db):
    """Mark patients as COMPLETED if they have waited long enough."""
    active_patients = db.get_active_patients()
    if not active_patients:
        return 0
        
    completed_count = 0
    now = datetime.now()
    
    for p in active_patients:
        # Time they have been waiting
        arrival = p['arrival_time']
        waited_minutes = (now - arrival).total_seconds() / 60
        
        # Predicted wait + random service variance (0-10% extra)
        # We assume they leave after (Predicted + Service Time)
        # Simplifying: They leave when Waited > Predicted + 5 mins
        # User Request: remove patients every 2 minutes (Force fast departure for demo)
        depart_threshold = 2.0 
        doctor_threshold = 1.0 # Simulate entering doctor's room after 1 minute

        if waited_minutes > depart_threshold:
            db.update_patient_status(p['patient_id'], 'COMPLETED')
            print(f"[- {now.strftime('%H:%M:%S')}] {p['patient_name']} COMPLETED (Waited {waited_minutes:.1f}m)")
            completed_count += 1
        elif waited_minutes > doctor_threshold and p['status'] == 'WAITING':
             db.update_patient_status(p['patient_id'], 'WITH_DOCTOR')
             print(f"[> {now.strftime('%H:%M:%S')}] {p['patient_name']} is WITH_DOCTOR")
            
    return completed_count

def run_simulation():
    print("Starting Hospital Queue Simulation...")
    print("Press Ctrl+C to stop.")
    
    db = DatabaseManager()
    if not db.init_db():
        print("Failed to initialize DB. Exiting.")
        return

    # Load model once
    print("Loading AI Model...")
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        model_path = os.path.join(base_dir, "queue_model.joblib")
        print(f"Loading model from {model_path}...")
        model = HospitalQueuePredictor.load(model_path)
    except Exception as e:
        print(f"Could not load model: {e}")
        return

    try:
        while True:
            # 1. Generate Patient
            p = generate_random_patient()
            
            # 2. Get Current State (Queue Length) from DB
            active_patients = db.get_active_patients()
            queue_length = len(active_patients)
            
            # Count contrast scans in queue
            contrast_count = sum(1 for row in active_patients if row['modality'] in ['MRI', 'CT']) # Simplified proxy
            
            # 3. Predict Wait Time
            predicted_wait = predict_wait_time(
                hour=p['arrival_time'].hour,
                is_emergency=p['is_emergency'],
                modality=p['modality'],
                staff_on_duty=6, # Assume constant for sim
                current_queue=queue_length,
                avg_age=p['age'], # Using patient's own age as proxy for queue avg for simplicity
                contrast_queue=contrast_count,
                model=model
            )
            
            # 4. Add to DB
            patient_record = {
                'patient_id': p['patient_id'],
                'patient_name': p['patient_name'],
                'arrival_time': p['arrival_time'],
                'patient_type': p['patient_type'],
                'modality': p['modality'],
                'predicted_wait_minutes': predicted_wait
            }
            db.add_patient(patient_record)
            
            print(f"[+ {p['arrival_time'].strftime('%H:%M:%S')}] {p['patient_name']} ({p['modality']}) - Pred: {predicted_wait:.0f}m - Q: {queue_length}")
            
            # 5. Process Departures
            process_departures(db)
            
            # 6. Simulate Time Passing for others (Update elapsed time)
            # In a real system, elapsed time is calculated on read. 
            # Here we just sleep.
            
            sleep_time = random.randint(2, 5) # New patient every 2-5 seconds
            time.sleep(sleep_time)
            
    except KeyboardInterrupt:
        print("\nSimulation stopped.")

if __name__ == "__main__":
    run_simulation()
