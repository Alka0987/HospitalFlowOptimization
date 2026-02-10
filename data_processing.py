"""
Hospital Queue Prediction System - Data Processing Module
==========================================================
This module handles all data loading, cleaning, and feature engineering
using Queueing Theory principles to prepare data for model training.

Key Features:
- Removes invalid data (negative wait times, outliers)
- Engineers queueing theory metrics (λ, μ, ρ)
- Merges patient data with staff capacity data
- Creates temporal and categorical features
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')


class HospitalDataProcessor:
    """
    Processes raw hospital data into clean, feature-rich dataset for ML training.
    """
    
    def __init__(self, data_dir="."):
        self.data_dir = data_dir
        self.scheduled_files = [
            "WaitData.Published.xlsx - F1.csv",
            "WaitData.Published.xlsx - F2.csv", 
            "WaitData.Published.xlsx - F3.csv"
        ]
        self.emergency_file = "WaitData.Published.xlsx - F4.csv"
        self.roster_file = "hospital_roster.csv"
        


    def load_patient_data(self):
        """Load and combine all patient data files."""
        print("Loading patient data files...")
        
        # Load scheduled patients (F1, F2, F3)
        scheduled_dfs = []
        for file in self.scheduled_files:
            try:
                df = pd.read_csv(f"{self.data_dir}/{file}")
                df['PatientType'] = 'Scheduled'
                df['SourceFile'] = file
                scheduled_dfs.append(df)
                print(f"  - Loaded {file}: {len(df)} records")
            except Exception as e:
                print(f"  - Warning: Could not load {file}: {e}")
        
        # Load emergency patients (F4)
        try:
            emergency_df = pd.read_csv(f"{self.data_dir}/{self.emergency_file}")
            emergency_df['PatientType'] = 'Emergency'
            emergency_df['SourceFile'] = self.emergency_file
            # Emergency is mixed: randomly assign among 3 types
            np.random.seed(42) 
            emergency_df['Modality'] = np.random.choice(
                ['Consultation', 'MRI', 'CT'], 
                size=len(emergency_df),
                p=[0.5, 0.25, 0.25] # Assume higher Consultation volume
            )
            print(f"  - Loaded {self.emergency_file}: {len(emergency_df)} records")
        except Exception as e:
            print(f"  - Error loading emergency data: {e}")
            emergency_df = pd.DataFrame()
            
        # Combine all data
        if scheduled_dfs:
            scheduled_combined = pd.concat(scheduled_dfs, ignore_index=True)
            # Infer Modality: F1=Consultation, F2=MRI, F3=CT
            def get_modality(source):
                if 'F1' in source: return 'Consultation'
                if 'F2' in source: return 'MRI'
                if 'F3' in source: return 'CT'
                return 'Consultation' # Default
                
            scheduled_combined['Modality'] = scheduled_combined['SourceFile'].apply(get_modality)
        else:
            scheduled_combined = pd.DataFrame()
            
        return scheduled_combined, emergency_df
    
    def load_roster_data(self):
        """Load staff roster data."""
        print("Loading roster data...")
        try:
            roster = pd.read_csv(f"{self.data_dir}/{self.roster_file}")
            roster['Date'] = pd.to_datetime(roster['Date'])
            roster['Shift_Start'] = pd.to_datetime(roster['Shift_Start'])
            roster['Shift_End'] = pd.to_datetime(roster['Shift_End'])
            print(f"  - Loaded roster: {len(roster)} records")
            return roster
        except Exception as e:
            print(f"  - Error loading roster: {e}")
            return pd.DataFrame()
    
    def calculate_staff_on_duty(self, roster, datetime_val):
        """Calculate number of staff on duty at a specific datetime."""
        if roster.empty:
            return 5  # Default value if no roster data
        
        date_part = datetime_val.date()
        time_part = datetime_val
        
        # Find matching shifts
        matching = roster[
            (roster['Date'].dt.date == date_part) &
            (roster['Shift_Start'] <= time_part) &
            (roster['Shift_End'] >= time_part)
        ]
        
        return max(len(matching), 1)  # At least 1 staff member
    
    def clean_data(self, df):
        """
        Clean data by removing invalid records.
        
        Key cleaning steps:
        1. Remove negative wait times (data entry errors)
        2. Remove extreme outliers (> 99th percentile)
        3. Handle missing values
        """
        print("Cleaning data...")
        original_len = len(df)
        
        # 1. Remove records with missing wait times
        df = df.dropna(subset=['Wait'])
        
        # 2. Remove negative wait times (these are data errors)
        df = df[df['Wait'] >= 0]
        
        # 3. Remove extreme outliers (wait > 120 minutes for scheduled, > 90 for emergency)
        # These are likely data entry errors or exceptional cases that would confuse the model
        mean_wait = df['Wait'].mean()
        std_wait = df['Wait'].std()
        upper_bound = mean_wait + 3 * std_wait  # 3 standard deviations
        upper_bound = min(upper_bound, 120)  # Cap at 2 hours max
        df = df[df['Wait'] <= upper_bound]
        
        print(f"  - Cleaned: {original_len} -> {len(df)} records ({original_len - len(df)} removed)")
        
        return df
    
    def engineer_features(self, df, roster):
        """
        Engineer features using Queueing Theory principles.
        
        Features created:
        - Temporal: Hour, DayOfWeek, IsWeekend, TimeSlot
        - Capacity: StaffOnDuty
        - Queueing metrics: ArrivalRate (λ), ServiceRate (μ), Workload (ρ)
        - Patient type: IsEmergency
        """
        print("Engineering features...")
        
        # Parse datetime columns
        df['ArrivalTime'] = pd.to_datetime(df['x_ArrivalDTTM'], errors='coerce')
        df['BeginTime'] = pd.to_datetime(df['x_BeginDTTM'], errors='coerce')
        
        # Drop rows with invalid timestamps
        df = df.dropna(subset=['ArrivalTime'])
        
        # === TEMPORAL FEATURES ===
        df['Hour'] = df['ArrivalTime'].dt.hour
        df['DayOfWeek'] = df['ArrivalTime'].dt.dayofweek
        df['IsWeekend'] = (df['DayOfWeek'] >= 5).astype(int)
        df['Month'] = df['ArrivalTime'].dt.month
        df['Date'] = df['ArrivalTime'].dt.date
        
        # Time slots (Morning, Afternoon, Evening, Night)
        df['TimeSlot'] = pd.cut(
            df['Hour'], 
            bins=[0, 6, 12, 18, 24], 
            labels=['Night', 'Morning', 'Afternoon', 'Evening'],
            include_lowest=True
        )
        
        # === PATIENT TYPE & MODALITY ===
        df['IsEmergency'] = (df['PatientType'] == 'Emergency').astype(int)
        df['IsMRI'] = (df['Modality'] == 'MRI').astype(int)
        df['IsCT'] = (df['Modality'] == 'CT').astype(int)
        # Note: If IsMRI=0 and IsCT=0, then it is Consultation
        
        # === STAFF CAPACITY (OPTIMIZED) ===
        print("  - Calculating staff capacity...")
        
        if not roster.empty:
            # Optimized: Pre-compute staff counts by date
            staff_counts = roster.groupby('Date').size().reset_index(name='RosterCount')
            staff_counts['DateStr'] = staff_counts['Date'].dt.strftime('%Y-%m-%d')
            
            # Create Date column as string for fast lookup
            df['DateStr'] = df['ArrivalTime'].dt.strftime('%Y-%m-%d')
            
            # Merge to find matches
            original_len = len(df)
            df = df.merge(staff_counts[['DateStr', 'RosterCount']], on='DateStr', how='left')
            
            # Calculate match rate
            matches = df['RosterCount'].notna().sum()
            print(f"  - Roster Match Rate: {matches}/{original_len} ({matches/original_len:.1%})")
            
            # Fill missing values with median
            median_staff = int(staff_counts['RosterCount'].median()) if not staff_counts.empty else 5
            df['StaffOnDuty'] = df['RosterCount'].fillna(median_staff)
            
            # Adjust by shift (simple heuristic: night shift has fewer staff)
            # Night: 22:00 - 06:00 (1/3 staff)
            # Early Morning: 06:00 - 08:00 (1/2 staff)
            df['StaffOnDuty'] = df.apply(
                lambda row: max(1, row['StaffOnDuty'] // 3) if row['Hour'] < 6 or row['Hour'] >= 22 
                else row['StaffOnDuty'] // 2 if 6 <= row['Hour'] < 8 
                else row['StaffOnDuty'], axis=1
            )
            
            # Cleanup
            df.drop(['DateStr', 'RosterCount'], axis=1, inplace=True)
        else:
            # Default staff based on time of day
            print("  - Warning: No roster data available. Using defaults.")
            df['StaffOnDuty'] = df['Hour'].apply(
                lambda h: 3 if h < 6 or h >= 22 else 5 if 6 <= h < 8 else 8
            )
        
        # === QUEUEING THEORY METRICS ===
        print("  - Computing queueing theory metrics...")
        
        # Group by date and hour to compute hourly metrics
        hourly_groups = df.groupby(['Date', 'Hour'])
        
        # Arrival Rate (λ): patients per hour
        arrival_rate = hourly_groups.size().reset_index(name='ArrivalRate')
        
        # Service Rate (μ): average service completions per hour
        # Approximated from BeginTime patterns
        df = df.merge(arrival_rate, on=['Date', 'Hour'], how='left')
        
        # Service rate estimate (patients served per hour per staff)
        df['ServiceRate'] = df['StaffOnDuty'] * 4  # Assume each staff can serve ~4 patients/hour
        
        # Workload (ρ = λ/μ): traffic intensity
        df['Workload'] = df['ArrivalRate'] / df['ServiceRate']
        df['Workload'] = df['Workload'].clip(0, 2)  # Cap at 200% capacity
        
        # === QUEUE LENGTH FEATURES ===
        # Use existing features if available
        if 'LineCount0' in df.columns:
            df['QueueLength'] = df['LineCount0'].fillna(0)
        else:
            df['QueueLength'] = df['ArrivalRate'] / 2  # Estimate
            
        if 'SumWaits' in df.columns:
            df['TotalWaitingTime'] = df['SumWaits'].fillna(0)
        else:
            df['TotalWaitingTime'] = 0
            
        print(f"  - Features engineered for {len(df)} records")
        
        return df
    
    def prepare_training_data(self, df):
        """
        Prepare final training dataset with selected features.
        
        Returns X (features) and y (target).
        """
        print("Preparing training data...")
        
        # Selected features for training
        feature_cols = [
            'Hour',
            'DayOfWeek', 
            'IsWeekend',
            'Month',
            'IsEmergency',
            'IsMRI',
            'IsCT',
            'StaffOnDuty',
            'ArrivalRate',
            'ServiceRate',
            'Workload',
            'QueueLength',
            'AvgAgePeopleWaiting',
            'WithContrastCountWaiting'
        ]
        
        # Ensure all features exist
        available_features = [col for col in feature_cols if col in df.columns]
        
        # Create feature matrix
        X = df[available_features].copy()
        y = df['Wait'].copy()
        
        # Handle any remaining NaN values
        X = X.fillna(X.median())
        
        print(f"  - Training data: {len(X)} samples, {len(available_features)} features")
        print(f"  - Features: {available_features}")
        print(f"  - Target (Wait) - Mean: {y.mean():.2f}, Std: {y.std():.2f}")
        
        return X, y, available_features
    
    def process_all(self):
        """
        Main processing pipeline.
        
        Returns:
            X: Feature matrix
            y: Target variable (Wait time)
            feature_names: List of feature names
        """
        print("="*60)
        print("HOSPITAL QUEUE PREDICTION - DATA PROCESSING")
        print("="*60)
        
        # Load data
        scheduled_df, emergency_df = self.load_patient_data()
        roster = self.load_roster_data()
        
        
        # Combine all patient data (allow columns to union)

        
        # Combine all patient data
        combined_df = pd.concat([scheduled_df, emergency_df], ignore_index=True)
        print(f"\nTotal records: {len(combined_df)}")
        
        # Clean data  
        cleaned_df = self.clean_data(combined_df)
        
        # Engineer features
        featured_df = self.engineer_features(cleaned_df, roster)
        
        # Prepare training data
        X, y, feature_names = self.prepare_training_data(featured_df)
        
        print("\n" + "="*60)
        print("DATA PROCESSING COMPLETE")
        print("="*60)
        
        return X, y, feature_names, featured_df


if __name__ == "__main__":
    # Test the data processor
    processor = HospitalDataProcessor(".")
    X, y, features, df = processor.process_all()
    
    print("\n--- Sample Data ---")
    print(X.head())
    print(f"\nTarget range: {y.min()} to {y.max()} minutes")
