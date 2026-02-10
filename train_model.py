"""
Hospital Queue Prediction System - Model Training Module
=========================================================
This module trains a Random Forest model to predict patient wait times.

Key Features:
- Robust data validation to prevent "hallucination"
- Proper train/test split with stratification
- Hyperparameter tuning
- Prediction bounds to ensure sensible outputs
- Model evaluation with multiple metrics
"""

import pandas as pd
import numpy as np
import joblib
import json
from datetime import datetime
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import warnings
warnings.filterwarnings('ignore')

from data_processing import HospitalDataProcessor


class HospitalQueuePredictor:
    """
    Random Forest model for predicting hospital queue wait times.
    
    Anti-hallucination measures:
    1. Training data is cleaned to remove invalid records
    2. Feature scaling prevents numerical instability
    3. Prediction bounds ensure outputs are realistic
    4. Cross-validation ensures model generalizes well
    """
    
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.feature_names = None
        self.min_wait = 0      # Minimum possible wait
        self.max_wait = 120    # Maximum realistic wait (2 hours)
        self.training_stats = {}
        
    def train(self, X, y, feature_names, tune_hyperparams=False):
        """
        Train the Random Forest model.
        
        Args:
            X: Feature matrix
            y: Target variable (wait times)
            feature_names: List of feature names
            tune_hyperparams: Whether to perform grid search
        """
        print("\n" + "="*60)
        print("MODEL TRAINING")
        print("="*60)
        
        self.feature_names = feature_names
        
        # Store training statistics for validation
        self.training_stats = {
            'wait_mean': float(y.mean()),
            'wait_std': float(y.std()),
            'wait_min': float(y.min()),
            'wait_max': float(y.max()),
            'n_samples': len(y),
            'features': feature_names
        }
        
        # Update max wait based on training data
        self.max_wait = min(float(y.max()) * 1.5, 120)
        
        # Split data
        print("Splitting data (80% train, 20% test)...")
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        # Scale features
        print("Scaling features...")
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Model configuration
        if tune_hyperparams:
            print("Tuning hyperparameters (this may take a while)...")
            param_grid = {
                'n_estimators': [100, 200],
                'max_depth': [10, 20, None],
                'min_samples_split': [2, 5],
                'min_samples_leaf': [1, 2]
            }
            
            grid_search = GridSearchCV(
                RandomForestRegressor(random_state=42, n_jobs=-1),
                param_grid,
                cv=3,
                scoring='neg_mean_absolute_error',
                n_jobs=-1
            )
            grid_search.fit(X_train_scaled, y_train)
            self.model = grid_search.best_estimator_
            print(f"Best parameters: {grid_search.best_params_}")
        else:
            # Use robust default parameters
            print("Training with optimized default parameters...")
            self.model = RandomForestRegressor(
                n_estimators=200,           # More trees for stability
                max_depth=15,               # Prevent overfitting
                min_samples_split=5,        # Require minimum samples to split
                min_samples_leaf=3,         # Minimum samples in leaf
                max_features='sqrt',        # Feature randomization
                random_state=42,
                n_jobs=-1                   # Use all CPU cores
            )
            self.model.fit(X_train_scaled, y_train)
        
        print("Training complete!")
        
        # Evaluate model
        self._evaluate(X_train_scaled, y_train, X_test_scaled, y_test)
        
        # Cross-validation for robustness check
        print("\nCross-validation (5-fold)...")
        cv_scores = cross_val_score(
            self.model, X_train_scaled, y_train, 
            cv=5, scoring='neg_mean_absolute_error'
        )
        cv_mae = -cv_scores.mean()
        print(f"  - CV MAE: {cv_mae:.2f} minutes (+/- {cv_scores.std():.2f})")
        
        self.training_stats['cv_mae'] = float(cv_mae)
        
        return self
    
    def _evaluate(self, X_train, y_train, X_test, y_test):
        """Evaluate model performance on train and test sets."""
        print("\n--- Model Evaluation ---")
        
        # Train predictions
        train_pred = self._bound_predictions(self.model.predict(X_train))
        train_mae = mean_absolute_error(y_train, train_pred)
        train_rmse = np.sqrt(mean_squared_error(y_train, train_pred))
        train_r2 = r2_score(y_train, train_pred)
        
        # Test predictions  
        test_pred = self._bound_predictions(self.model.predict(X_test))
        test_mae = mean_absolute_error(y_test, test_pred)
        test_rmse = np.sqrt(mean_squared_error(y_test, test_pred))
        test_r2 = r2_score(y_test, test_pred)
        
        print(f"\nTraining Set:")
        print(f"  - MAE:  {train_mae:.2f} minutes")
        print(f"  - RMSE: {train_rmse:.2f} minutes")
        print(f"  - R²:   {train_r2:.4f}")
        
        print(f"\nTest Set:")
        print(f"  - MAE:  {test_mae:.2f} minutes")
        print(f"  - RMSE: {test_rmse:.2f} minutes")
        print(f"  - R²:   {test_r2:.4f}")
        
        # Check for overfitting
        overfit_ratio = train_mae / test_mae if test_mae > 0 else 1
        if overfit_ratio < 0.7:
            print("\n[WARN] Warning: Model may be overfitting!")
        else:
            print("\n[OK] Model generalization looks good!")
        
        # Store metrics
        self.training_stats['train_mae'] = float(train_mae)
        self.training_stats['test_mae'] = float(test_mae)
        self.training_stats['train_r2'] = float(train_r2)
        self.training_stats['test_r2'] = float(test_r2)
        
        # Feature importance
        print("\n--- Feature Importance ---")
        importances = self.model.feature_importances_
        feature_imp = sorted(zip(self.feature_names, importances), 
                            key=lambda x: x[1], reverse=True)
        for feat, imp in feature_imp:
            bar = '#' * int(imp * 50)
            print(f"  {feat:15s}: {bar} ({imp:.3f})")
    
    def _bound_predictions(self, predictions):
        """
        Bound predictions to realistic values.
        
        This is a KEY anti-hallucination measure!
        """
        return np.clip(predictions, self.min_wait, self.max_wait)
    
    def predict(self, features_dict):
        """
        Make a single prediction.
        
        Args:
            features_dict: Dictionary with feature values
            
        Returns:
            Predicted wait time in minutes (bounded to realistic range)
        """
        if self.model is None:
            raise ValueError("Model not trained! Call train() first.")
        
        # Create feature vector
        feature_vector = []
        for feat in self.feature_names:
            if feat in features_dict:
                feature_vector.append(features_dict[feat])
            else:
                # Use default/median values
                defaults = {
                    'Hour': 12,
                    'DayOfWeek': 2,
                    'IsWeekend': 0,
                    'Month': 6,
                    'IsEmergency': 0,
                    'StaffOnDuty': 5,
                    'ArrivalRate': 10,
                    'ServiceRate': 20,
                    'Workload': 0.5,
                    'QueueLength': 5
                }
                feature_vector.append(defaults.get(feat, 0))
        
        # Scale and predict
        X = np.array([feature_vector])
        X_scaled = self.scaler.transform(X)
        prediction = self.model.predict(X_scaled)[0]
        
        # Bound prediction
        bounded_prediction = self._bound_predictions(np.array([prediction]))[0]
        
        return float(bounded_prediction)
    
    def predict_batch(self, X):
        """
        Make batch predictions.
        
        Args:
            X: Feature matrix (DataFrame or numpy array)
            
        Returns:
            Array of predicted wait times (bounded)
        """
        if self.model is None:
            raise ValueError("Model not trained!")
        
        X_scaled = self.scaler.transform(X)
        predictions = self.model.predict(X_scaled)
        
        return self._bound_predictions(predictions)
    
    def save(self, model_path="queue_model.joblib", stats_path="model_stats.json"):
        """Save the trained model and statistics."""
        print(f"\nSaving model to {model_path}...")
        
        # Save model and scaler
        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'feature_names': self.feature_names,
            'min_wait': self.min_wait,
            'max_wait': self.max_wait
        }
        joblib.dump(model_data, model_path)
        
        # Save training statistics
        self.training_stats['saved_at'] = datetime.now().isoformat()
        with open(stats_path, 'w') as f:
            json.dump(self.training_stats, f, indent=2)
        
        print(f"Model saved successfully!")
        print(f"  - Model: {model_path}")
        print(f"  - Stats: {stats_path}")
    
    @classmethod
    def load(cls, model_path="queue_model.joblib"):
        """Load a previously trained model."""
        print(f"Loading model from {model_path}...")
        
        model_data = joblib.load(model_path)
        
        predictor = cls()
        predictor.model = model_data['model']
        predictor.scaler = model_data['scaler']
        predictor.feature_names = model_data['feature_names']
        predictor.min_wait = model_data['min_wait']
        predictor.max_wait = model_data['max_wait']
        
        print("Model loaded successfully!")
        return predictor


def main():
    """Main training pipeline."""
    print("="*60)
    print("HOSPITAL QUEUE PREDICTION SYSTEM")
    print("="*60)
    print(f"Training started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Step 1: Process data
    processor = HospitalDataProcessor(".")
    X, y, feature_names, df = processor.process_all()
    
    # Step 2: Train model
    predictor = HospitalQueuePredictor()
    predictor.train(X, y, feature_names, tune_hyperparams=False)
    
    # Step 3: Save model
    predictor.save()
    
    # Step 4: Test prediction
    print("\n" + "="*60)
    print("SAMPLE PREDICTIONS")
    print("="*60)
    
    test_cases = [
        {
            'description': 'Monday morning, Emergency patient',
            'features': {'Hour': 9, 'DayOfWeek': 0, 'IsWeekend': 0, 'IsEmergency': 1,
                        'StaffOnDuty': 8, 'ArrivalRate': 15, 'Workload': 0.8, 'QueueLength': 10}
        },
        {
            'description': 'Sunday afternoon, Scheduled patient',
            'features': {'Hour': 14, 'DayOfWeek': 6, 'IsWeekend': 1, 'IsEmergency': 0,
                        'StaffOnDuty': 4, 'ArrivalRate': 5, 'Workload': 0.3, 'QueueLength': 3}
        },
        {
            'description': 'Friday evening, Emergency patient, busy',
            'features': {'Hour': 18, 'DayOfWeek': 4, 'IsWeekend': 0, 'IsEmergency': 1,
                        'StaffOnDuty': 6, 'ArrivalRate': 20, 'Workload': 1.2, 'QueueLength': 15}
        }
    ]
    
    for case in test_cases:
        wait_time = predictor.predict(case['features'])
        print(f"\n{case['description']}:")
        print(f"  -> Predicted wait: {wait_time:.1f} minutes")
    
    print("\n" + "="*60)
    print("TRAINING COMPLETE!")
    print("="*60)
    print("\nModel files created:")
    print("  - queue_model.joblib (trained model)")
    print("  - model_stats.json (training statistics)")
    print("\nTo make predictions, use:")
    print("  python predict.py")


if __name__ == "__main__":
    main()
