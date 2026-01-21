import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import (
    classification_report, confusion_matrix, roc_auc_score,
    precision_recall_curve, average_precision_score
)
import joblib
from pathlib import Path

from feature_extraction import FeatureExtractor, extract_all_features
from data_loader import SyntheticDataGenerator


class EarthquakeClassifier:

    def __init__(
        self,
        model_type: str = 'random_forest',
        sampling_rate: int = 100
    ):
        self.model_type = model_type
        self.sampling_rate = sampling_rate
        self.feature_extractor = FeatureExtractor(sampling_rate)
        self.scaler = StandardScaler()
        self.model = self._create_model()
        self.is_fitted = False

    def _create_model(self):
        if self.model_type == 'random_forest':
            return RandomForestClassifier(
                n_estimators=200,
                max_depth=20,
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=42,
                n_jobs=-1
            )
        elif self.model_type == 'gradient_boosting':
            return GradientBoostingClassifier(
                n_estimators=100,
                max_depth=5,
                learning_rate=0.1,
                random_state=42
            )
        else:
            raise ValueError(f"Unknown model type: {self.model_type}")

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        validation_split: float = 0.2
    ) -> Dict[str, float]:
        print("Extracting features...")
        X_features = self.feature_extractor.fit_transform(X)

        print("Scaling features...")
        X_scaled = self.scaler.fit_transform(X_features)

        X_train, X_val, y_train, y_val = train_test_split(
            X_scaled, y, test_size=validation_split, random_state=42, stratify=y
        )

        print(f"Training {self.model_type} model...")
        self.model.fit(X_train, y_train)
        self.is_fitted = True

        train_score = self.model.score(X_train, y_train)
        val_score = self.model.score(X_val, y_val)

        y_val_pred = self.model.predict(X_val)
        y_val_proba = self.model.predict_proba(X_val)[:, 1]

        metrics = {
            'train_accuracy': train_score,
            'val_accuracy': val_score,
            'val_roc_auc': roc_auc_score(y_val, y_val_proba),
            'val_avg_precision': average_precision_score(y_val, y_val_proba)
        }

        print("\nClassification Report:")
        print(classification_report(y_val, y_val_pred, target_names=['Non-EQ', 'EQ']))

        print("\nConfusion Matrix:")
        print(confusion_matrix(y_val, y_val_pred))

        return metrics

    def predict(self, X: np.ndarray) -> np.ndarray:
        if not self.is_fitted:
            raise RuntimeError("Model not fitted. Call fit() first.")

        X_features = self.feature_extractor.transform(X)
        X_scaled = self.scaler.transform(X_features)
        return self.model.predict(X_scaled)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        if not self.is_fitted:
            raise RuntimeError("Model not fitted. Call fit() first.")

        X_features = self.feature_extractor.transform(X)
        X_scaled = self.scaler.transform(X_features)
        return self.model.predict_proba(X_scaled)

    def get_feature_importance(self) -> pd.DataFrame:
        if not self.is_fitted:
            raise RuntimeError("Model not fitted. Call fit() first.")

        feature_names = self.feature_extractor.get_feature_names()

        if hasattr(self.model, 'feature_importances_'):
            importances = self.model.feature_importances_
        else:
            importances = np.zeros(len(feature_names))

        df = pd.DataFrame({
            'feature': feature_names,
            'importance': importances
        }).sort_values('importance', ascending=False)

        return df

    def save(self, path: str) -> None:
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)

        joblib.dump(self.model, path / 'model.joblib')
        joblib.dump(self.scaler, path / 'scaler.joblib')
        joblib.dump(self.feature_extractor, path / 'feature_extractor.joblib')

        metadata = {
            'model_type': self.model_type,
            'sampling_rate': self.sampling_rate,
            'feature_names': self.feature_extractor.get_feature_names()
        }
        joblib.dump(metadata, path / 'metadata.joblib')

        print(f"Model saved to {path}")

    @classmethod
    def load(cls, path: str) -> 'EarthquakeClassifier':
        path = Path(path)

        metadata = joblib.load(path / 'metadata.joblib')

        classifier = cls(
            model_type=metadata['model_type'],
            sampling_rate=metadata['sampling_rate']
        )

        classifier.model = joblib.load(path / 'model.joblib')
        classifier.scaler = joblib.load(path / 'scaler.joblib')
        classifier.feature_extractor = joblib.load(path / 'feature_extractor.joblib')
        classifier.is_fitted = True

        print(f"Model loaded from {path}")
        return classifier


class STALTACalibrator:

    def __init__(self, sampling_rate: int = 100):
        self.sampling_rate = sampling_rate
        self.optimal_params: Optional[Dict] = None

    def calculate_sta_lta(
        self,
        signal: np.ndarray,
        sta_window: float,
        lta_window: float
    ) -> np.ndarray:
        sta_samples = int(sta_window * self.sampling_rate)
        lta_samples = int(lta_window * self.sampling_rate)

        squared = signal**2

        sta = np.convolve(squared, np.ones(sta_samples)/sta_samples, mode='same')
        lta = np.convolve(squared, np.ones(lta_samples)/lta_samples, mode='same')

        return sta / (lta + 1e-10)

    def calibrate(
        self,
        earthquake_signals: List[np.ndarray],
        noise_signals: List[np.ndarray],
        sta_range: Tuple[float, float] = (0.5, 2.0),
        lta_range: Tuple[float, float] = (10.0, 60.0),
        threshold_range: Tuple[float, float] = (2.0, 10.0)
    ) -> Dict:
        best_score = 0
        best_params = None

        sta_values = np.linspace(sta_range[0], sta_range[1], 5)
        lta_values = np.linspace(lta_range[0], lta_range[1], 5)
        threshold_values = np.linspace(threshold_range[0], threshold_range[1], 10)

        for sta_window in sta_values:
            for lta_window in lta_values:
                if lta_window <= sta_window * 5:
                    continue

                eq_max_ratios = []
                for signal in earthquake_signals:
                    ratio = self.calculate_sta_lta(signal, sta_window, lta_window)
                    eq_max_ratios.append(np.max(ratio))

                noise_max_ratios = []
                for signal in noise_signals:
                    ratio = self.calculate_sta_lta(signal, sta_window, lta_window)
                    noise_max_ratios.append(np.max(ratio))

                for threshold in threshold_values:
                    tp = sum(1 for r in eq_max_ratios if r > threshold)
                    fn = len(eq_max_ratios) - tp
                    fp = sum(1 for r in noise_max_ratios if r > threshold)
                    tn = len(noise_max_ratios) - fp

                    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
                    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
                    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

                    if f1 > best_score:
                        best_score = f1
                        best_params = {
                            'sta_window': sta_window,
                            'lta_window': lta_window,
                            'trigger_threshold': threshold,
                            'detrigger_threshold': threshold * 0.4,
                            'precision': precision,
                            'recall': recall,
                            'f1_score': f1
                        }

        self.optimal_params = best_params
        return best_params

    def get_optimal_params(self) -> Dict:
        if self.optimal_params is None:
            return {
                'sta_window': 1.0,
                'lta_window': 30.0,
                'trigger_threshold': 5.0,
                'detrigger_threshold': 2.0
            }
        return self.optimal_params


def convert_to_tflite(
    model_path: str,
    output_path: str,
    representative_data: Optional[np.ndarray] = None
) -> None:
    try:
        import tensorflow as tf

        classifier = EarthquakeClassifier.load(model_path)

        feature_names = classifier.feature_extractor.get_feature_names()
        num_features = len(feature_names)

        tf_model = tf.keras.Sequential([
            tf.keras.layers.Dense(64, activation='relu', input_shape=(num_features,)),
            tf.keras.layers.Dropout(0.2),
            tf.keras.layers.Dense(32, activation='relu'),
            tf.keras.layers.Dropout(0.2),
            tf.keras.layers.Dense(1, activation='sigmoid')
        ])

        converter = tf.lite.TFLiteConverter.from_keras_model(tf_model)
        converter.optimizations = [tf.lite.Optimize.DEFAULT]
        converter.target_spec.supported_types = [tf.int8]

        if representative_data is not None:
            def representative_data_gen():
                for sample in representative_data[:100]:
                    yield [sample.astype(np.float32).reshape(1, -1)]
            converter.representative_dataset = representative_data_gen

        tflite_model = converter.convert()

        with open(output_path, 'wb') as f:
            f.write(tflite_model)

        print(f"TFLite model saved to {output_path}")
        print(f"Model size: {len(tflite_model) / 1024:.2f} KB")

    except ImportError:
        print("TensorFlow not available. Skipping TFLite conversion.")


if __name__ == "__main__":
    print("Generating synthetic training data...")
    generator = SyntheticDataGenerator(sampling_rate=100, duration=60.0)
    X, y, metadata = generator.generate_dataset(num_earthquakes=200, num_non_earthquakes=200)

    print(f"\nDataset shape: X={X.shape}, y={y.shape}")
    print(f"Class distribution: EQ={np.sum(y==1)}, Non-EQ={np.sum(y==0)}")

    print("\n" + "="*60)
    print("Training Random Forest Classifier")
    print("="*60)

    classifier = EarthquakeClassifier(model_type='random_forest', sampling_rate=100)
    metrics = classifier.fit(X, y, validation_split=0.2)

    print("\nTraining Metrics:")
    for name, value in metrics.items():
        print(f"  {name}: {value:.4f}")

    print("\nTop 10 Important Features:")
    importance_df = classifier.get_feature_importance()
    print(importance_df.head(10).to_string(index=False))

    classifier.save('models/earthquake_classifier')

    print("\n" + "="*60)
    print("Calibrating STA/LTA Parameters")
    print("="*60)

    eq_signals = [X[i] for i in range(len(y)) if y[i] == 1][:50]
    noise_signals = [X[i] for i in range(len(y)) if y[i] == 0][:50]

    calibrator = STALTACalibrator(sampling_rate=100)
    optimal_params = calibrator.calibrate(eq_signals, noise_signals)

    print("\nOptimal STA/LTA Parameters:")
    for name, value in optimal_params.items():
        if isinstance(value, float):
            print(f"  {name}: {value:.4f}")
        else:
            print(f"  {name}: {value}")
