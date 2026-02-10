"""
Hospital Queue Prediction System - Prediction Module
=====================================================
Simple interface for making wait time predictions using the trained model.
"""

from train_model import HospitalQueuePredictor
from datetime import datetime


def predict_wait_time(hour=None, day_of_week=None, is_emergency=False, modality='MRI',
                      staff_on_duty=5, current_queue=5, is_busy=False,
                      avg_age=45, contrast_queue=1, model=None):
    """
    Predict wait time for a patient.
    
    Args:
        hour: Hour of day (0-23). If None, uses current hour.
        day_of_week: Day (0=Monday, 6=Sunday). If None, uses today.
        is_emergency: Is this an emergency patient?
        modality: 'MRI', 'CT', or 'Consultation'
        staff_on_duty: Number of staff currently on duty
        current_queue: Current number of people in queue
        is_busy: Is it a typically busy time?
        avg_age: Average age of people in the queue (default 45)
        contrast_queue: Number of people waiting for contrast scans (default 1)
        
    Returns:
        Predicted wait time in minutes
    """
    # Use current time if not specified
    now = datetime.now()
    if hour is None:
        hour = now.hour
    if day_of_week is None:
        day_of_week = now.weekday()
    
    # Calculate derived features
    is_weekend = 1 if day_of_week >= 5 else 0
    
    # Modality encoding
    mod = str(modality).upper()
    is_mri = 1 if 'MRI' in mod else 0
    is_ct = 1 if 'CT' in mod else 0
    # Consultation is implied when both are 0
    
    # Estimate arrival rate based on time and busyness
    base_rate = 10
    if 9 <= hour <= 17:  # Business hours
        base_rate = 15
    if is_busy:
        base_rate *= 1.5
    
    arrival_rate = base_rate
    service_rate = staff_on_duty * 4
    workload = min(arrival_rate / service_rate, 2.0)
    
    # Build feature dictionary
    features = {
        'Hour': hour,
        'DayOfWeek': day_of_week,
        'IsWeekend': is_weekend,
        'Month': now.month,
        'IsEmergency': 1 if is_emergency else 0,
        'IsMRI': is_mri,
        'IsCT': is_ct,
        'StaffOnDuty': staff_on_duty,
        'ArrivalRate': arrival_rate,
        'ServiceRate': service_rate,
        'Workload': workload,
        'QueueLength': current_queue,
        'AvgAgePeopleWaiting': avg_age,
        'WithContrastCountWaiting': contrast_queue
    }
    
    # Load model if not provided
    if model is None:
        try:
            model = HospitalQueuePredictor.load("queue_model.joblib")
        except Exception as e:
            print(f"Error loading model: {e}")
            return 0

    wait_time = model.predict(features)
    
    return wait_time


def main():
    """Interactive prediction demo."""
    print("="*60)
    print("HOSPITAL QUEUE WAIT TIME PREDICTIOR")
    print("="*60)
    
    # Current context
    now = datetime.now()
    print(f"\nTime: {now.strftime('%A, %H:%M')}")
    print("-" * 60)
    print(f"{'PATIENT TYPE':<15} | {'MODALITY':<15} | {'WAIT TIME':<15}")
    print("-" * 60)
    
    scenarios = [
        ('Scheduled', 'Consultation', False, 'Consultation'),
        ('Scheduled', 'MRI',         False, 'MRI'),
        ('Scheduled', 'CT',          False, 'CT'),
        ('Emergency', 'Consultation', True,  'Consultation'),
        ('Emergency', 'MRI',         True,  'MRI'),
        ('Emergency', 'CT',          True,  'CT')
    ]
    
    for label_type, label_mod, is_emerg, mod in scenarios:
        wait = predict_wait_time(
            staff_on_duty=6, 
            current_queue=8, 
            is_emergency=is_emerg, 
            modality=mod
        )
        print(f"{label_type:<15} | {label_mod:<15} | {wait:.0f} minutes")
    
    print("-" * 60)
    print("\nusage:")
    print("  from predict import predict_wait_time")
    print("  wait = predict_wait_time(modality='MRI', contrast_queue=4, avg_age=65)")


if __name__ == "__main__":
    main()
