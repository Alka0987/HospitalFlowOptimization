# Hospital Queue Prediction Model Training

## Tasks
- [x] Analyze data files (F1-F4, roster)
- [x] Identify data quality issues (negative wait times causing hallucination)
- [x] Create data processing pipeline (`data_processing.py`)
- [x] Create model training script (`train_model.py`)
- [x] Train and evaluate model
- [x] Save trained model (`queue_model.joblib`)
- [x] Create prediction script (`predict.py`)
- [x] Fix roster data mapping in `data_processing.py`
- [x] Generate improved synthetic roster data (`generate_roster.py`)
- [x] Re-run training with new data
- [x] Test `predict.py` functionality

## Results
- **Training Data**: 99,392 samples (after cleaning 31,039 invalid records)
- **Test MAE**: 7.82 minutes (model predicts within ~8 minutes accuracy)
- **CV MAE**: 7.83 minutes (consistent cross-validation)
- **Predictions are bounded**: 0-68 minutes (no hallucination possible)
