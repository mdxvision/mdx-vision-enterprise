"""
MDx Vision - Facial Recognition Service

Identifies patients and staff from drone camera or any video feed.
Uses face_recognition library (dlib-based) for accurate face matching.

Usage:
    service = FacialRecognitionService()
    service.register_face("Dr. Smith", image_path="smith.jpg")
    service.register_face("Patient John Doe", image_path="john_doe.jpg")

    # From video frame
    matches = service.identify_faces(frame)
    # Returns: [{"name": "Dr. Smith", "confidence": 0.95, "bbox": (x,y,w,h)}]
"""

import os
import json
import logging
import base64
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import numpy as np

logger = logging.getLogger(__name__)

# Try to import face_recognition - may need installation
try:
    import face_recognition
    FACE_RECOGNITION_AVAILABLE = True
except ImportError:
    FACE_RECOGNITION_AVAILABLE = False
    logger.warning("face_recognition not installed. Run: pip install face-recognition")

# Try to import OpenCV for image processing
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    logger.warning("OpenCV not installed. Run: pip install opencv-python")


@dataclass
class RegisteredFace:
    """A registered face in the database."""
    id: str
    name: str
    role: str  # "patient", "clinician", "staff", "visitor"
    encoding: List[float]  # 128-dimensional face encoding
    metadata: Dict[str, Any]  # Additional info (room, department, etc.)
    image_path: Optional[str] = None


@dataclass
class FaceMatch:
    """A detected and identified face."""
    name: str
    role: str
    confidence: float  # 0.0 - 1.0
    bbox: Tuple[int, int, int, int]  # (top, right, bottom, left)
    metadata: Dict[str, Any]


class FacialRecognitionService:
    """
    Facial recognition service for identifying patients and staff.

    Features:
    - Register faces from images
    - Identify faces in video frames
    - Configurable confidence threshold
    - Face database persistence
    """

    # Default paths
    DEFAULT_DB_PATH = "data/faces/face_db.json"
    DEFAULT_IMAGES_PATH = "data/faces/images"

    # Recognition settings
    DEFAULT_TOLERANCE = 0.6  # Lower = stricter matching
    DEFAULT_MODEL = "hog"  # "hog" (faster) or "cnn" (more accurate)

    def __init__(
        self,
        db_path: str = None,
        images_path: str = None,
        tolerance: float = None,
        model: str = None
    ):
        self.db_path = Path(db_path or self.DEFAULT_DB_PATH)
        self.images_path = Path(images_path or self.DEFAULT_IMAGES_PATH)
        self.tolerance = tolerance or self.DEFAULT_TOLERANCE
        self.model = model or self.DEFAULT_MODEL

        # Face database: id -> RegisteredFace
        self._faces: Dict[str, RegisteredFace] = {}

        # Cached encodings for fast lookup
        self._known_encodings: List[np.ndarray] = []
        self._known_ids: List[str] = []

        # Ensure directories exist
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.images_path.mkdir(parents=True, exist_ok=True)

        # Load existing database
        self._load_database()

    def _load_database(self):
        """Load face database from disk."""
        if self.db_path.exists():
            try:
                with open(self.db_path, 'r') as f:
                    data = json.load(f)

                for face_data in data.get('faces', []):
                    face = RegisteredFace(
                        id=face_data['id'],
                        name=face_data['name'],
                        role=face_data['role'],
                        encoding=face_data['encoding'],
                        metadata=face_data.get('metadata', {}),
                        image_path=face_data.get('image_path')
                    )
                    self._faces[face.id] = face

                self._rebuild_cache()
                logger.info(f"Loaded {len(self._faces)} faces from database")

            except Exception as e:
                logger.error(f"Failed to load face database: {e}")

    def _save_database(self):
        """Save face database to disk."""
        try:
            data = {
                'faces': [asdict(face) for face in self._faces.values()]
            }
            with open(self.db_path, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved {len(self._faces)} faces to database")

        except Exception as e:
            logger.error(f"Failed to save face database: {e}")

    def _rebuild_cache(self):
        """Rebuild encoding cache for fast lookup."""
        self._known_encodings = []
        self._known_ids = []

        for face_id, face in self._faces.items():
            self._known_encodings.append(np.array(face.encoding))
            self._known_ids.append(face_id)

    def register_face(
        self,
        name: str,
        role: str = "unknown",
        image_path: str = None,
        image_data: bytes = None,
        image_base64: str = None,
        metadata: Dict[str, Any] = None
    ) -> Optional[str]:
        """
        Register a new face in the database.

        Args:
            name: Person's name
            role: "patient", "clinician", "staff", "visitor"
            image_path: Path to image file
            image_data: Raw image bytes
            image_base64: Base64-encoded image
            metadata: Additional info (room number, department, etc.)

        Returns:
            Face ID if successful, None otherwise
        """
        if not FACE_RECOGNITION_AVAILABLE:
            logger.error("face_recognition library not available")
            return None

        # Load image
        image = None
        saved_path = None

        if image_path:
            image = face_recognition.load_image_file(image_path)
            saved_path = image_path

        elif image_data:
            # Convert bytes to numpy array
            nparr = np.frombuffer(image_data, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        elif image_base64:
            image_bytes = base64.b64decode(image_base64)
            nparr = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        if image is None:
            logger.error("No valid image provided")
            return None

        # Detect faces
        face_locations = face_recognition.face_locations(image, model=self.model)
        if not face_locations:
            logger.warning(f"No face detected in image for {name}")
            return None

        if len(face_locations) > 1:
            logger.warning(f"Multiple faces detected, using first one for {name}")

        # Get face encoding
        face_encodings = face_recognition.face_encodings(image, face_locations)
        if not face_encodings:
            logger.error(f"Could not encode face for {name}")
            return None

        encoding = face_encodings[0]

        # Generate ID
        import uuid
        face_id = str(uuid.uuid4())[:8]

        # Save image if not already saved
        if not saved_path and CV2_AVAILABLE:
            saved_path = str(self.images_path / f"{face_id}.jpg")
            cv2.imwrite(saved_path, cv2.cvtColor(image, cv2.COLOR_RGB2BGR))

        # Create face record
        face = RegisteredFace(
            id=face_id,
            name=name,
            role=role,
            encoding=encoding.tolist(),
            metadata=metadata or {},
            image_path=saved_path
        )

        self._faces[face_id] = face
        self._rebuild_cache()
        self._save_database()

        logger.info(f"Registered face: {name} (ID: {face_id}, role: {role})")
        return face_id

    def identify_faces(
        self,
        frame: np.ndarray,
        tolerance: float = None
    ) -> List[FaceMatch]:
        """
        Identify faces in a video frame.

        Args:
            frame: RGB image as numpy array (H, W, 3)
            tolerance: Override default tolerance

        Returns:
            List of FaceMatch objects for identified faces
        """
        if not FACE_RECOGNITION_AVAILABLE:
            return []

        if not self._known_encodings:
            return []

        tolerance = tolerance or self.tolerance

        # Detect faces
        face_locations = face_recognition.face_locations(frame, model=self.model)
        if not face_locations:
            return []

        # Get encodings
        face_encodings = face_recognition.face_encodings(frame, face_locations)

        matches = []
        for encoding, location in zip(face_encodings, face_locations):
            # Compare to known faces
            distances = face_recognition.face_distance(self._known_encodings, encoding)

            if len(distances) > 0:
                best_idx = np.argmin(distances)
                best_distance = distances[best_idx]

                if best_distance <= tolerance:
                    face_id = self._known_ids[best_idx]
                    face = self._faces[face_id]

                    # Convert distance to confidence (0 = perfect match)
                    confidence = 1.0 - best_distance

                    match = FaceMatch(
                        name=face.name,
                        role=face.role,
                        confidence=confidence,
                        bbox=location,  # (top, right, bottom, left)
                        metadata=face.metadata
                    )
                    matches.append(match)
                else:
                    # Unknown face
                    matches.append(FaceMatch(
                        name="Unknown",
                        role="unknown",
                        confidence=0.0,
                        bbox=location,
                        metadata={}
                    ))

        return matches

    def identify_from_base64(self, image_base64: str) -> List[FaceMatch]:
        """Identify faces from base64-encoded image."""
        if not CV2_AVAILABLE:
            return []

        try:
            image_bytes = base64.b64decode(image_base64)
            nparr = np.frombuffer(image_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            return self.identify_faces(frame)
        except Exception as e:
            logger.error(f"Failed to decode image: {e}")
            return []

    def get_registered_faces(self) -> List[Dict[str, Any]]:
        """Get list of all registered faces (without encodings)."""
        return [
            {
                "id": face.id,
                "name": face.name,
                "role": face.role,
                "metadata": face.metadata
            }
            for face in self._faces.values()
        ]

    def delete_face(self, face_id: str) -> bool:
        """Remove a face from the database."""
        if face_id in self._faces:
            del self._faces[face_id]
            self._rebuild_cache()
            self._save_database()
            logger.info(f"Deleted face: {face_id}")
            return True
        return False

    def clear_database(self):
        """Remove all faces from database."""
        self._faces.clear()
        self._rebuild_cache()
        self._save_database()
        logger.info("Cleared face database")


# ═══════════════════════════════════════════════════════════════════════════
# DRONE VIDEO FACE DETECTION
# ═══════════════════════════════════════════════════════════════════════════

class DroneVideoProcessor:
    """
    Process video stream from drone camera for face detection.

    Connects to Tello video stream and runs facial recognition.
    """

    def __init__(
        self,
        face_service: FacialRecognitionService,
        video_url: str = "udp://0.0.0.0:11111"
    ):
        self.face_service = face_service
        self.video_url = video_url
        self._running = False
        self._cap: Optional[cv2.VideoCapture] = None
        self._last_matches: List[FaceMatch] = []
        self._callbacks: List[callable] = []

    def add_callback(self, callback: callable):
        """Add callback for face detection events."""
        self._callbacks.append(callback)

    def start(self):
        """Start processing video stream."""
        if not CV2_AVAILABLE:
            logger.error("OpenCV not available")
            return False

        try:
            self._cap = cv2.VideoCapture(self.video_url)
            if not self._cap.isOpened():
                logger.error(f"Could not open video stream: {self.video_url}")
                return False

            self._running = True
            logger.info(f"Started video processing from {self.video_url}")

            import threading
            self._thread = threading.Thread(target=self._process_loop, daemon=True)
            self._thread.start()
            return True

        except Exception as e:
            logger.error(f"Failed to start video processing: {e}")
            return False

    def stop(self):
        """Stop processing video stream."""
        self._running = False
        if self._cap:
            self._cap.release()
            self._cap = None

    def _process_loop(self):
        """Main processing loop."""
        frame_count = 0

        while self._running and self._cap:
            ret, frame = self._cap.read()
            if not ret:
                continue

            frame_count += 1

            # Process every 10th frame for performance
            if frame_count % 10 != 0:
                continue

            # Convert BGR to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Detect faces
            matches = self.face_service.identify_faces(rgb_frame)

            # Check for new detections
            if matches != self._last_matches:
                self._last_matches = matches

                # Notify callbacks
                for callback in self._callbacks:
                    try:
                        callback(matches)
                    except Exception as e:
                        logger.error(f"Callback error: {e}")

    def get_last_matches(self) -> List[FaceMatch]:
        """Get most recent face matches."""
        return self._last_matches

    def get_current_frame(self) -> Optional[np.ndarray]:
        """Get current video frame."""
        if self._cap and self._cap.isOpened():
            ret, frame = self._cap.read()
            if ret:
                return frame
        return None


# ═══════════════════════════════════════════════════════════════════════════
# SINGLETON INSTANCE
# ═══════════════════════════════════════════════════════════════════════════

_face_service: Optional[FacialRecognitionService] = None


def get_face_service() -> FacialRecognitionService:
    """Get singleton face recognition service."""
    global _face_service
    if _face_service is None:
        _face_service = FacialRecognitionService()
    return _face_service


def reset_face_service():
    """Reset face service (for testing)."""
    global _face_service
    _face_service = None
