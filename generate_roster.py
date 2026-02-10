import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def generate_roster():
    print("Generating synthetic roster...")
    
    # Load staff
    try:
        staff_df = pd.read_csv("hospital_staff.csv")
        staff_ids = staff_df['Staff_ID'].tolist()
        print(f"  - Loaded {len(staff_ids)} staff members")
    except Exception as e:
        print(f"  - Error loading staff: {e}")
        return

    # Configuration
    start_date = datetime(2022, 10, 30)
    end_date = datetime(2025, 9, 1)  # Cover slightly past data end
    
    shifts = {
        'Morning': {'start': 8, 'duration': 8},
        'Evening': {'start': 16, 'duration': 8},
        'Night': {'start': 0, 'duration': 8}
    }
    
    # Base staffing levels (Role-based distribution would be better, but simple count is improved)
    # Mean staff per shift
    weekday_staffing = {'Morning': 15, 'Evening': 10, 'Night': 5}
    weekend_staffing = {'Morning': 10, 'Evening': 8, 'Night': 4}
    
    roster_records = []
    
    current_date = start_date
    while current_date <= end_date:
        is_weekend = current_date.weekday() >= 5
        staffing_config = weekend_staffing if is_weekend else weekday_staffing
        
        # Shuffle staff for this day's pool to ensure random assignment
        daily_pool = np.random.permutation(staff_ids)
        pool_idx = 0
        
        for shift_name, config in shifts.items():
            # Determine staff count for this shift (Poisson distribution for variance)
            base_count = staffing_config[shift_name]
            # +/- 2 staff variance
            actual_count = max(1, int(np.random.normal(base_count, 1.5)))
            
            # Select staff
            if pool_idx + actual_count > len(daily_pool):
                # Reshuffle if we run out (rare with this pool size)
                daily_pool = np.random.permutation(staff_ids)
                pool_idx = 0
                
            selected_staff = daily_pool[pool_idx : pool_idx + actual_count]
            pool_idx += actual_count
            
            # Create records
            shift_start_dt = current_date + timedelta(hours=config['start'])
            shift_end_dt = shift_start_dt + timedelta(hours=config['duration'])
            
            for staff_id in selected_staff:
                roster_records.append({
                    'Date': current_date.strftime('%Y-%m-%d'),
                    'Shift_Name': shift_name,
                    'Staff_ID': staff_id,
                    'Shift_Start': shift_start_dt.strftime('%Y-%m-%d %H:%M'),
                    'Shift_End': shift_end_dt.strftime('%Y-%m-%d %H:%M')
                })
        
        current_date += timedelta(days=1)

    # Save
    roster_df = pd.DataFrame(roster_records)
    output_file = "hospital_roster.csv"
    roster_df.to_csv(output_file, index=False)
    
    print(f"  - Generated {len(roster_df)} roster records")
    print(f"  - Saved to {output_file}")
    
    # Quick Check
    print("\nSample Data:")
    print(roster_df.head())

if __name__ == "__main__":
    generate_roster()
