"""Confidence calibrator for LLM routing decisions.

This module implements adaptive confidence calibration using machine learning
to replace hard-coded thresholds with learned decision boundaries.
"""

import asyncio
import csv
import logging
import pickle
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import numpy as np
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import accuracy_score, precision_recall_fscore_support
    from sklearn.model_selection import train_test_split
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    LogisticRegression = None
    np = None


logger = logging.getLogger(__name__)


class ConfidenceCalibrator:
    """Adaptive confidence calibrator for routing decisions."""

    def __init__(self, data_dir: Path | None = None):
        """Initialize calibrator with data directory."""
        self.data_dir = data_dir or Path("storage/calibrator")
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.csv_path = self.data_dir / "routing_decisions.csv"
        self.model_path = self.data_dir / "calibrator.pkl"

        self.model: LogisticRegression | None = None
        self.is_trained = False
        self.fallback_threshold = 0.45  # Increased threshold to favor external routing

        # Training parameters
        self.min_samples_for_training = 50  # Reduced to allow faster adaptation
        self.retrain_interval = 25  # Retrain more frequently
        self.sample_count = 0

        # Initialize CSV file
        self._initialize_csv()

        # Load existing model if available
        self._load_model()

    def _initialize_csv(self) -> None:
        """Initialize CSV file with headers if it doesn't exist."""
        if not self.csv_path.exists():
            with open(self.csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "timestamp", "query", "entropy", "local_confidence",
                    "route_used", "is_correct", "user_feedback", "execution_time"
                ])
            logger.info(f"📊 Initialized calibrator CSV at {self.csv_path}")

    def _load_model(self) -> None:
        """Load existing trained model if available."""
        if not SKLEARN_AVAILABLE:
            logger.warning("⚠️ sklearn not available, using fallback threshold")
            return

        if self.model_path.exists():
            try:
                with open(self.model_path, "rb") as f:
                    calibrator_data = pickle.load(f)
                    self.model = calibrator_data["model"]
                    self.is_trained = calibrator_data.get("is_trained", False)
                    self.sample_count = calibrator_data.get("sample_count", 0)

                logger.info(f"✅ Loaded trained calibrator model ({self.sample_count} samples)")
            except Exception as e:
                logger.error(f"❌ Failed to load calibrator model: {e}")
                self.model = None
                self.is_trained = False

    def _save_model(self) -> None:
        """Save trained model to disk."""
        if not self.model or not SKLEARN_AVAILABLE:
            return

        try:
            calibrator_data = {
                "model": self.model,
                "is_trained": self.is_trained,
                "sample_count": self.sample_count,
                "trained_at": datetime.now().isoformat()
            }

            with open(self.model_path, "wb") as f:
                pickle.dump(calibrator_data, f)

            logger.info(f"💾 Saved calibrator model with {self.sample_count} samples")
        except Exception as e:
            logger.error(f"❌ Failed to save calibrator model: {e}")

    async def log_decision(
        self,
        query: str,
        entropy: float,
        local_confidence: str,
        route_used: str,
        is_correct: bool,
        user_feedback: str | None = None,
        execution_time: float = 0.0
    ) -> None:
        """Log a routing decision for training data."""
        timestamp = datetime.now().isoformat()

        # Log to CSV in thread pool to avoid blocking
        def write_csv():
            with open(self.csv_path, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    timestamp, query[:100], entropy, local_confidence,
                    route_used, is_correct, user_feedback or "", execution_time
                ])

        await asyncio.get_event_loop().run_in_executor(None, write_csv)

        self.sample_count += 1

        # Trigger retraining if we have enough new samples
        if (self.sample_count % self.retrain_interval == 0 and
            self.sample_count >= self.min_samples_for_training):
            await self.retrain_model()

    async def retrain_model(self) -> bool:
        """Retrain the calibrator model with accumulated data."""
        if not SKLEARN_AVAILABLE:
            logger.warning("⚠️ sklearn not available, cannot retrain calibrator")
            return False

        logger.info("🔄 Retraining confidence calibrator...")

        # Load training data in thread pool
        def load_training_data():
            return self._load_training_data()

        training_data = await asyncio.get_event_loop().run_in_executor(None, load_training_data)

        if len(training_data) < self.min_samples_for_training:
            logger.warning(f"⚠️ Not enough training data: {len(training_data)} < {self.min_samples_for_training}")
            return False

        # Train model in thread pool
        def train_model():
            return self._train_model(training_data)

        success = await asyncio.get_event_loop().run_in_executor(None, train_model)

        if success:
            self.is_trained = True
            self._save_model()
            logger.info("✅ Calibrator model retrained successfully")
        else:
            logger.error("❌ Failed to retrain calibrator model")

        return success

    def _load_training_data(self) -> list[tuple[list[float], bool]]:
        """Load training data from CSV file."""
        training_data = []

        try:
            with open(self.csv_path, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        # Features: [entropy, query_length, local_confidence_numeric]
                        entropy = float(row["entropy"])
                        query_length = len(row["query"])

                        # Convert confidence to numeric
                        confidence_map = {"high": 1.0, "medium": 0.5, "low": 0.0}
                        local_conf = confidence_map.get(row["local_confidence"], 0.5)

                        features = [entropy, query_length, local_conf]

                        # Target: True if local routing was correct
                        is_correct = row["is_correct"].lower() == "true"
                        route_used = row["route_used"]

                        # For local routes, use is_correct directly
                        # For external routes, assume they were necessary (inverse)
                        if route_used == "local":
                            target = is_correct
                        else:
                            target = not is_correct  # External was needed because local would fail

                        training_data.append((features, target))

                    except (ValueError, KeyError) as e:
                        logger.debug(f"Skipping invalid training row: {e}")
                        continue

        except FileNotFoundError:
            logger.warning("No training data file found")

        return training_data

    def _train_model(self, training_data: list[tuple[list[float], bool]]) -> bool:
        """Train the logistic regression model."""
        try:
            # Prepare data
            X = np.array([features for features, _ in training_data])
            y = np.array([target for _, target in training_data])

            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y
            )

            # Train model
            self.model = LogisticRegression(random_state=42, max_iter=1000)
            self.model.fit(X_train, y_train)

            # Evaluate
            y_pred = self.model.predict(X_test)
            accuracy = accuracy_score(y_test, y_pred)
            precision, recall, f1, _ = precision_recall_fscore_support(y_test, y_pred, average="binary")

            logger.info("📊 Calibrator training results:")
            logger.info(f"   Accuracy: {accuracy:.3f}")
            logger.info(f"   Precision: {precision:.3f}")
            logger.info(f"   Recall: {recall:.3f}")
            logger.info(f"   F1: {f1:.3f}")

            return accuracy > 0.6  # Require minimum accuracy

        except Exception as e:
            logger.error(f"❌ Model training failed: {e}")
            return False

    def predict_should_use_local(
        self,
        entropy: float,
        query: str,
        local_confidence: str
    ) -> tuple[bool, float]:
        """Predict whether to use local LLM based on learned calibration."""
        if not self.is_trained or not self.model or not SKLEARN_AVAILABLE:
            # Fallback to threshold logic with FastLLM bias
            should_use_local = entropy < self.fallback_threshold  # Inverted comparison
            confidence = 1.0 - entropy if entropy < self.fallback_threshold else entropy
            return should_use_local, confidence

        try:
            # Prepare features
            query_length = len(query)
            confidence_map = {"high": 1.0, "medium": 0.5, "low": 0.0}
            local_conf = confidence_map.get(local_confidence, 0.5)

            features = np.array([[entropy, query_length, local_conf]])

            # Get prediction and probability
            prediction = self.model.predict(features)[0]
            probability = self.model.predict_proba(features)[0]

            # Add bias towards FastLLM's recommendation
            if entropy > 0.6:  # If FastLLM suggests high complexity
                prediction = False  # Route to external
                probability = np.array([0.3, 0.7])  # Bias probabilities

            # prediction=True means local should be used
            should_use_local = bool(prediction)
            confidence_score = max(probability)

            return should_use_local, confidence_score

        except Exception as e:
            logger.error(f"❌ Prediction failed: {e}")
            # Fallback to threshold with FastLLM bias
            should_use_local = entropy < self.fallback_threshold
            confidence = 1.0 - entropy if entropy < self.fallback_threshold else entropy
            return should_use_local, confidence

    def get_stats(self) -> dict[str, Any]:
        """Get calibrator statistics."""
        stats = {
            "is_trained": self.is_trained,
            "sample_count": self.sample_count,
            "sklearn_available": SKLEARN_AVAILABLE,
            "fallback_threshold": self.fallback_threshold,
            "min_samples_for_training": self.min_samples_for_training
        }

        if self.csv_path.exists():
            stats["csv_size"] = self.csv_path.stat().st_size

        if self.model_path.exists():
            stats["model_size"] = self.model_path.stat().st_size

        return stats


# Global calibrator instance
calibrator = ConfidenceCalibrator()
