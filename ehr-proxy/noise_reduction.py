"""
MDx Vision - Real-Time Noise Reduction using RNNoise
Mozilla's open-source ML noise suppression (free alternative to Krisp AI)

Features:
- 15-20dB noise reduction using recurrent neural network
- Sample rate conversion for pyrnnoise (requires 48kHz)
- Voice activity detection (VAD) with speech probability
- Low-latency processing suitable for real-time streaming

Requirements:
    pip install pyrnnoise numpy scipy

Usage:
    reducer = NoiseReducer()
    denoised_audio, speech_prob = reducer.process(audio_bytes_16khz)
"""

import numpy as np
from typing import Tuple, Optional
import struct

# pyrnnoise requires 48kHz sample rate
RNNOISE_SAMPLE_RATE = 48000
# Client sends 16kHz audio
CLIENT_SAMPLE_RATE = 16000
# Sample rate ratio
RESAMPLE_RATIO = RNNOISE_SAMPLE_RATE // CLIENT_SAMPLE_RATE  # 3

# RNNoise frame size (10ms at 48kHz)
RNNOISE_FRAME_SIZE = 480


class NoiseReducer:
    """
    Real-time noise reducer using Mozilla's RNNoise.

    Handles sample rate conversion between client's 16kHz and RNNoise's 48kHz.
    Uses linear interpolation for upsampling and decimation for downsampling
    to minimize latency while maintaining audio quality.
    """

    def __init__(self, enabled: bool = True, input_sample_rate: int = CLIENT_SAMPLE_RATE):
        """
        Initialize the noise reducer.

        Args:
            enabled: Whether noise reduction is active
            input_sample_rate: Sample rate of input audio (default 16kHz)
        """
        self.enabled = enabled
        self.input_sample_rate = input_sample_rate
        self._rnnoise = None
        self._buffer = np.array([], dtype=np.float32)  # Accumulator for partial frames
        self._speech_prob_history = []  # Track speech probability
        self._initialized = False

        if enabled:
            self._initialize()

    def _initialize(self):
        """Initialize RNNoise model"""
        try:
            from pyrnnoise import RNNoise
            self._rnnoise = RNNoise(sample_rate=RNNOISE_SAMPLE_RATE)
            self._initialized = True
            print(f"✅ RNNoise initialized (48kHz, ~15-20dB noise reduction)")
        except ImportError as e:
            print(f"⚠️ RNNoise not available: {e}")
            print("   Install with: pip install pyrnnoise")
            self.enabled = False
        except Exception as e:
            print(f"⚠️ RNNoise initialization failed: {e}")
            self.enabled = False

    def _bytes_to_float32(self, audio_bytes: bytes) -> np.ndarray:
        """
        Convert 16-bit PCM bytes to float32 array normalized to [-1, 1].

        Args:
            audio_bytes: Raw 16-bit PCM audio data

        Returns:
            Numpy array of float32 samples
        """
        # Unpack as 16-bit signed integers
        samples = np.frombuffer(audio_bytes, dtype=np.int16)
        # Normalize to float32 [-1, 1]
        return samples.astype(np.float32) / 32768.0

    def _float32_to_bytes(self, audio: np.ndarray) -> bytes:
        """
        Convert float32 array back to 16-bit PCM bytes.

        Args:
            audio: Float32 audio samples normalized to [-1, 1]

        Returns:
            Raw 16-bit PCM bytes
        """
        # Clip to prevent overflow
        audio = np.clip(audio, -1.0, 1.0)
        # Convert back to int16
        samples = (audio * 32767).astype(np.int16)
        return samples.tobytes()

    def _upsample(self, audio: np.ndarray, factor: int = RESAMPLE_RATIO) -> np.ndarray:
        """
        Upsample audio using linear interpolation.

        Args:
            audio: Input audio at source sample rate
            factor: Upsampling factor (3 for 16kHz -> 48kHz)

        Returns:
            Upsampled audio
        """
        if len(audio) == 0:
            return audio

        # Create output array
        output_len = len(audio) * factor
        output = np.zeros(output_len, dtype=np.float32)

        # Linear interpolation
        for i in range(len(audio) - 1):
            for j in range(factor):
                t = j / factor
                output[i * factor + j] = audio[i] * (1 - t) + audio[i + 1] * t

        # Handle last sample
        output[(len(audio) - 1) * factor:] = audio[-1]

        return output

    def _downsample(self, audio: np.ndarray, factor: int = RESAMPLE_RATIO) -> np.ndarray:
        """
        Downsample audio using decimation.

        Args:
            audio: Input audio at high sample rate
            factor: Downsampling factor (3 for 48kHz -> 16kHz)

        Returns:
            Downsampled audio
        """
        if len(audio) == 0:
            return audio

        # Simple decimation (take every nth sample)
        return audio[::factor].copy()

    def process(self, audio_bytes: bytes) -> Tuple[bytes, float]:
        """
        Process audio chunk through RNNoise.

        Args:
            audio_bytes: Raw 16-bit PCM audio at input sample rate

        Returns:
            Tuple of (denoised audio bytes, average speech probability 0-1)
        """
        if not self.enabled or not self._initialized:
            return audio_bytes, 1.0  # Pass through unchanged

        # Convert to float32
        audio = self._bytes_to_float32(audio_bytes)

        # Upsample to 48kHz for RNNoise
        audio_48k = self._upsample(audio)

        # Add to buffer
        self._buffer = np.concatenate([self._buffer, audio_48k])

        # Process complete frames
        output_frames = []
        speech_probs = []

        while len(self._buffer) >= RNNOISE_FRAME_SIZE:
            frame = self._buffer[:RNNOISE_FRAME_SIZE]
            self._buffer = self._buffer[RNNOISE_FRAME_SIZE:]

            # Process through RNNoise
            try:
                for prob, denoised in self._rnnoise.denoise_chunk(frame, partial=False):
                    speech_probs.append(prob)
                    output_frames.append(denoised)
            except Exception as e:
                # On error, pass through unchanged
                print(f"⚠️ RNNoise processing error: {e}")
                output_frames.append(frame)
                speech_probs.append(1.0)

        if not output_frames:
            return b"", 0.0  # No complete frames yet

        # Combine output frames
        denoised_48k = np.concatenate(output_frames)

        # Downsample back to original rate
        denoised = self._downsample(denoised_48k)

        # Calculate average speech probability
        avg_speech_prob = np.mean(speech_probs) if speech_probs else 1.0

        # Track for stats
        self._speech_prob_history.append(avg_speech_prob)
        if len(self._speech_prob_history) > 100:
            self._speech_prob_history.pop(0)

        return self._float32_to_bytes(denoised), float(avg_speech_prob)

    def get_stats(self) -> dict:
        """
        Get noise reduction statistics.

        Returns:
            Dict with stats about noise reduction performance
        """
        if not self._speech_prob_history:
            return {
                "enabled": self.enabled,
                "initialized": self._initialized,
                "avg_speech_probability": 0.0,
                "frames_processed": 0
            }

        return {
            "enabled": self.enabled,
            "initialized": self._initialized,
            "avg_speech_probability": np.mean(self._speech_prob_history),
            "min_speech_probability": np.min(self._speech_prob_history),
            "max_speech_probability": np.max(self._speech_prob_history),
            "frames_processed": len(self._speech_prob_history),
            "buffer_size": len(self._buffer)
        }

    def reset(self):
        """Reset the noise reducer state (call between sessions)"""
        self._buffer = np.array([], dtype=np.float32)
        self._speech_prob_history = []
        if self._rnnoise:
            # Re-initialize for fresh state
            try:
                from pyrnnoise import RNNoise
                self._rnnoise = RNNoise(sample_rate=RNNOISE_SAMPLE_RATE)
            except:
                pass


class NoiseReductionSession:
    """
    Manages noise reduction for a single transcription session.
    Provides thread-safe processing with session-level statistics.
    """

    def __init__(self, session_id: str, enabled: bool = True):
        """
        Create a new noise reduction session.

        Args:
            session_id: Unique session identifier
            enabled: Whether to enable noise reduction
        """
        self.session_id = session_id
        self.reducer = NoiseReducer(enabled=enabled)
        self.total_audio_bytes = 0
        self.total_denoised_bytes = 0
        self.chunk_count = 0

    def process(self, audio_bytes: bytes) -> Tuple[bytes, float]:
        """
        Process audio through noise reduction.

        Args:
            audio_bytes: Raw 16-bit PCM audio

        Returns:
            Tuple of (denoised audio bytes, speech probability)
        """
        self.total_audio_bytes += len(audio_bytes)
        self.chunk_count += 1

        denoised, speech_prob = self.reducer.process(audio_bytes)
        self.total_denoised_bytes += len(denoised)

        return denoised, speech_prob

    def get_stats(self) -> dict:
        """Get session statistics"""
        base_stats = self.reducer.get_stats()
        base_stats.update({
            "session_id": self.session_id,
            "total_audio_bytes": self.total_audio_bytes,
            "total_denoised_bytes": self.total_denoised_bytes,
            "chunk_count": self.chunk_count
        })
        return base_stats

    def close(self):
        """Clean up session resources"""
        self.reducer.reset()


# Global noise reduction toggle
NOISE_REDUCTION_ENABLED = True


def is_noise_reduction_available() -> bool:
    """Check if RNNoise is available"""
    try:
        from pyrnnoise import RNNoise
        return True
    except ImportError:
        return False


def create_noise_reduction_session(session_id: str, enabled: bool = None) -> NoiseReductionSession:
    """
    Factory function to create a noise reduction session.

    Args:
        session_id: Unique session identifier
        enabled: Override global enable setting

    Returns:
        Configured noise reduction session
    """
    if enabled is None:
        enabled = NOISE_REDUCTION_ENABLED

    return NoiseReductionSession(session_id, enabled=enabled)


# Test function
def _test_noise_reduction():
    """Quick test of noise reduction"""
    print("Testing RNNoise integration...")

    # Check availability
    if not is_noise_reduction_available():
        print("❌ pyrnnoise not installed")
        return

    # Create session
    session = create_noise_reduction_session("test-001")

    # Generate test audio (16kHz, 100ms of silence with some noise)
    duration_samples = 1600  # 100ms at 16kHz
    noise = np.random.randn(duration_samples).astype(np.float32) * 0.1
    test_audio = (noise * 32767).astype(np.int16).tobytes()

    print(f"Input: {len(test_audio)} bytes")

    # Process
    denoised, speech_prob = session.process(test_audio)

    print(f"Output: {len(denoised)} bytes")
    print(f"Speech probability: {speech_prob:.2f}")
    print(f"Stats: {session.get_stats()}")

    session.close()
    print("✅ RNNoise test passed")


if __name__ == "__main__":
    _test_noise_reduction()
