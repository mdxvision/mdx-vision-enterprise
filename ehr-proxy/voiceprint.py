"""
MDx Vision - Voiceprint Speaker Recognition
Uses SpeechBrain ECAPA-TDNN for speaker verification

Enrollment: Record 3+ audio samples → Extract embeddings → Store average
Verification: Record audio → Extract embedding → Compare similarity → Accept/Reject
"""

import os
import io
import json
import base64
import hashlib
import numpy as np
from typing import Optional, List, Tuple
from datetime import datetime, timezone

# Lazy load SpeechBrain (heavy import)
_speaker_model = None
_USE_SPEECHBRAIN = True  # Set to False to use placeholder mode

def _get_speaker_model():
    """Lazy load the SpeechBrain speaker verification model."""
    global _speaker_model

    if _speaker_model is None and _USE_SPEECHBRAIN:
        try:
            from speechbrain.inference.speaker import SpeakerRecognition

            # Use pre-trained ECAPA-TDNN model for speaker verification
            # Downloads ~80MB model on first run, cached after
            _speaker_model = SpeakerRecognition.from_hparams(
                source="speechbrain/spkrec-ecapa-voxceleb",
                savedir="data/speechbrain_models/spkrec-ecapa"
            )
            print("✅ SpeechBrain speaker model loaded")
        except ImportError:
            print("⚠️ SpeechBrain not installed - using placeholder mode")
        except Exception as e:
            print(f"⚠️ Failed to load SpeechBrain: {e} - using placeholder mode")

    return _speaker_model


# ═══════════════════════════════════════════════════════════════════════════
# STORAGE
# ═══════════════════════════════════════════════════════════════════════════

VOICEPRINT_DIR = os.path.join(os.path.dirname(__file__), "data", "voiceprints")
os.makedirs(VOICEPRINT_DIR, exist_ok=True)


def _get_voiceprint_path(clinician_id: str) -> str:
    """Get path to clinician's voiceprint file."""
    safe_id = hashlib.md5(clinician_id.encode()).hexdigest()
    return os.path.join(VOICEPRINT_DIR, f"{safe_id}.json")


def _load_voiceprint(clinician_id: str) -> Optional[dict]:
    """Load stored voiceprint for a clinician."""
    path = _get_voiceprint_path(clinician_id)
    if os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
    return None


def _save_voiceprint(clinician_id: str, data: dict):
    """Save voiceprint data for a clinician."""
    path = _get_voiceprint_path(clinician_id)
    with open(path, 'w') as f:
        json.dump(data, f)


# ═══════════════════════════════════════════════════════════════════════════
# AUDIO PROCESSING
# ═══════════════════════════════════════════════════════════════════════════

def _decode_audio(audio_base64: str) -> Optional[bytes]:
    """Decode base64 audio to bytes."""
    try:
        return base64.b64decode(audio_base64)
    except Exception as e:
        print(f"Failed to decode audio: {e}")
        return None


def _audio_to_tensor(audio_bytes: bytes):
    """Convert audio bytes to tensor for SpeechBrain."""
    try:
        import torchaudio
        import torch

        # Load audio from bytes
        audio_buffer = io.BytesIO(audio_bytes)
        waveform, sample_rate = torchaudio.load(audio_buffer)

        # Resample to 16kHz if needed (SpeechBrain expects 16kHz)
        if sample_rate != 16000:
            resampler = torchaudio.transforms.Resample(sample_rate, 16000)
            waveform = resampler(waveform)

        # Convert to mono if stereo
        if waveform.shape[0] > 1:
            waveform = torch.mean(waveform, dim=0, keepdim=True)

        return waveform
    except Exception as e:
        print(f"Failed to process audio: {e}")
        return None


def _extract_embedding(audio_bytes: bytes) -> Optional[np.ndarray]:
    """Extract speaker embedding from audio using SpeechBrain."""
    model = _get_speaker_model()

    if model is None:
        # Placeholder mode - return random embedding
        print("⚠️ Using placeholder embedding (SpeechBrain not available)")
        return np.random.randn(192).astype(np.float32)

    try:
        waveform = _audio_to_tensor(audio_bytes)
        if waveform is None:
            return None

        # Extract embedding
        embedding = model.encode_batch(waveform)
        return embedding.squeeze().numpy()
    except Exception as e:
        print(f"Failed to extract embedding: {e}")
        return None


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two embeddings."""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


# ═══════════════════════════════════════════════════════════════════════════
# ENROLLMENT
# ═══════════════════════════════════════════════════════════════════════════

# Phrases for enrollment (user reads these aloud)
ENROLLMENT_PHRASES = [
    "My voice is my password, verify me.",
    "MDx Vision, unlock my session now.",
    "I authorize this clinical action.",
]


def get_enrollment_phrases() -> List[str]:
    """Get the phrases user should read for enrollment."""
    return ENROLLMENT_PHRASES.copy()


def enroll_voiceprint(
    clinician_id: str,
    audio_samples: List[str],  # Base64 encoded audio files
    clinician_name: str = ""
) -> dict:
    """
    Enroll a clinician's voiceprint from audio samples.

    Args:
        clinician_id: Unique clinician identifier
        audio_samples: List of base64-encoded audio recordings (min 3)
        clinician_name: Optional name for display

    Returns:
        Success/failure dict with enrollment status
    """
    if len(audio_samples) < 3:
        return {
            "success": False,
            "error": f"Need at least 3 audio samples, got {len(audio_samples)}"
        }

    embeddings = []

    for i, audio_b64 in enumerate(audio_samples):
        audio_bytes = _decode_audio(audio_b64)
        if audio_bytes is None:
            return {
                "success": False,
                "error": f"Failed to decode audio sample {i+1}"
            }

        embedding = _extract_embedding(audio_bytes)
        if embedding is None:
            return {
                "success": False,
                "error": f"Failed to extract voiceprint from sample {i+1}"
            }

        embeddings.append(embedding)

    # Average the embeddings to create a robust voiceprint
    avg_embedding = np.mean(embeddings, axis=0)

    # Compute variance to check consistency
    variances = [np.linalg.norm(e - avg_embedding) for e in embeddings]
    avg_variance = np.mean(variances)

    if avg_variance > 0.5:  # Threshold for consistency
        print(f"⚠️ High variance in enrollment samples: {avg_variance}")

    # Store voiceprint
    voiceprint_data = {
        "clinician_id": clinician_id,
        "clinician_name": clinician_name,
        "embedding": avg_embedding.tolist(),
        "num_samples": len(audio_samples),
        "variance": float(avg_variance),
        "enrolled_at": datetime.now(timezone.utc).isoformat(),
        "version": "1.0"
    }

    _save_voiceprint(clinician_id, voiceprint_data)

    print(f"✅ Voiceprint enrolled for {clinician_name or clinician_id}")

    return {
        "success": True,
        "message": "Voiceprint enrolled successfully",
        "samples_used": len(audio_samples),
        "consistency_score": float(1.0 - min(avg_variance, 1.0))
    }


# ═══════════════════════════════════════════════════════════════════════════
# VERIFICATION
# ═══════════════════════════════════════════════════════════════════════════

# Similarity thresholds
THRESHOLD_ACCEPT = 0.70  # Above this = accept
THRESHOLD_REJECT = 0.50  # Below this = reject
# Between = uncertain, may prompt for retry


def verify_voiceprint(
    clinician_id: str,
    audio_sample: str,  # Base64 encoded audio
) -> dict:
    """
    Verify a voice sample against stored voiceprint.

    Args:
        clinician_id: Clinician to verify against
        audio_sample: Base64-encoded audio recording

    Returns:
        Verification result with confidence score
    """
    # Load stored voiceprint
    voiceprint = _load_voiceprint(clinician_id)
    if voiceprint is None:
        return {
            "success": False,
            "verified": False,
            "error": "No voiceprint enrolled for this clinician",
            "confidence": 0.0
        }

    # Decode and process audio
    audio_bytes = _decode_audio(audio_sample)
    if audio_bytes is None:
        return {
            "success": False,
            "verified": False,
            "error": "Failed to decode audio sample",
            "confidence": 0.0
        }

    # Extract embedding from new sample
    new_embedding = _extract_embedding(audio_bytes)
    if new_embedding is None:
        return {
            "success": False,
            "verified": False,
            "error": "Failed to extract voiceprint from audio",
            "confidence": 0.0
        }

    # Compare with stored embedding
    stored_embedding = np.array(voiceprint["embedding"])
    similarity = _cosine_similarity(new_embedding, stored_embedding)

    # Determine result
    if similarity >= THRESHOLD_ACCEPT:
        verified = True
        status = "accepted"
    elif similarity < THRESHOLD_REJECT:
        verified = False
        status = "rejected"
    else:
        verified = False
        status = "uncertain"

    print(f"🔊 Voiceprint verification: {status} (similarity: {similarity:.3f})")

    return {
        "success": True,
        "verified": verified,
        "confidence": float(similarity),
        "threshold": THRESHOLD_ACCEPT,
        "status": status,
        "clinician_name": voiceprint.get("clinician_name", "")
    }


def is_enrolled(clinician_id: str) -> bool:
    """Check if a clinician has an enrolled voiceprint."""
    return _load_voiceprint(clinician_id) is not None


def delete_voiceprint(clinician_id: str) -> dict:
    """Delete a clinician's voiceprint enrollment."""
    path = _get_voiceprint_path(clinician_id)
    if os.path.exists(path):
        os.remove(path)
        return {"success": True, "message": "Voiceprint deleted"}
    return {"success": False, "error": "No voiceprint found"}


# ═══════════════════════════════════════════════════════════════════════════
# TESTING
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("Voiceprint module loaded")
    print(f"Phrases for enrollment: {ENROLLMENT_PHRASES}")

    # Test model loading
    model = _get_speaker_model()
    if model:
        print("✅ SpeechBrain model ready")
    else:
        print("⚠️ Running in placeholder mode")
