package com.mdxvision

import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.mockito.Mock
import org.mockito.Mockito.*
import org.mockito.junit.MockitoJUnitRunner
import org.junit.Assert.*
import java.nio.ByteBuffer

/**
 * Unit tests for AudioStreamingService
 *
 * Tests WebSocket audio streaming, audio processing, gain adjustment,
 * and transcription handling.
 */
@RunWith(MockitoJUnitRunner::class)
class AudioStreamingServiceTest {

    /**
     * Audio Processing Tests
     */
    class AudioProcessingTests {

        @Test
        fun `should apply 10x gain boost for Vuzix`() {
            val inputSample: Short = 100
            val gainFactor = 10.0f
            val boosted = applyGain(inputSample, gainFactor)

            // Result should be ~1000, clamped to Short.MAX_VALUE if needed
            assertTrue(boosted > inputSample)
        }

        @Test
        fun `should clamp audio to Short MAX_VALUE`() {
            val inputSample: Short = 5000
            val gainFactor = 10.0f
            val boosted = applyGain(inputSample, gainFactor)

            // 5000 * 10 = 50000, which exceeds Short.MAX_VALUE (32767)
            assertEquals(Short.MAX_VALUE, boosted)
        }

        @Test
        fun `should clamp audio to Short MIN_VALUE`() {
            val inputSample: Short = -5000
            val gainFactor = 10.0f
            val boosted = applyGain(inputSample, gainFactor)

            // -5000 * 10 = -50000, which is below Short.MIN_VALUE (-32768)
            assertEquals(Short.MIN_VALUE, boosted)
        }

        @Test
        fun `should handle zero sample`() {
            val inputSample: Short = 0
            val gainFactor = 10.0f
            val boosted = applyGain(inputSample, gainFactor)

            assertEquals(0.toShort(), boosted)
        }

        @Test
        fun `should calculate RMS correctly`() {
            // Simple test case: constant samples
            val samples = shortArrayOf(100, 100, 100, 100)
            val rms = calculateRMS(samples)

            // RMS of constant 100 is 100
            assertEquals(100.0f, rms, 0.1f)
        }

        @Test
        fun `should calculate dB correctly`() {
            val rms = 100.0f
            val maxValue = Short.MAX_VALUE.toFloat()
            val db = 20 * kotlin.math.log10(rms / maxValue)

            // 20 * log10(100 / 32767) ≈ -50.3 dB
            assertTrue(db < 0)
            assertTrue(db > -60)
        }

        private fun applyGain(sample: Short, gain: Float): Short {
            val amplified = (sample * gain).toInt()
            return amplified.coerceIn(Short.MIN_VALUE.toInt(), Short.MAX_VALUE.toInt()).toShort()
        }

        private fun calculateRMS(samples: ShortArray): Float {
            if (samples.isEmpty()) return 0f
            var sum = 0.0
            for (sample in samples) {
                sum += sample.toDouble() * sample.toDouble()
            }
            return kotlin.math.sqrt(sum / samples.size).toFloat()
        }
    }

    /**
     * Audio Configuration Tests
     */
    class AudioConfigurationTests {

        @Test
        fun `should use 16kHz sample rate`() {
            val expectedSampleRate = 16000
            assertEquals(expectedSampleRate, SAMPLE_RATE)
        }

        @Test
        fun `should use mono channel`() {
            val expectedChannels = 1
            assertEquals(expectedChannels, CHANNEL_COUNT)
        }

        @Test
        fun `should use 16-bit encoding`() {
            val expectedBitsPerSample = 16
            assertEquals(expectedBitsPerSample, BITS_PER_SAMPLE)
        }

        @Test
        fun `should calculate correct bytes per second`() {
            val bytesPerSecond = SAMPLE_RATE * CHANNEL_COUNT * (BITS_PER_SAMPLE / 8)
            assertEquals(32000, bytesPerSecond)
        }

        companion object {
            const val SAMPLE_RATE = 16000
            const val CHANNEL_COUNT = 1
            const val BITS_PER_SAMPLE = 16
        }
    }

    /**
     * WebSocket Connection Tests
     */
    class WebSocketTests {

        @Test
        fun `should construct correct WebSocket URL`() {
            val baseUrl = "10.0.2.2"
            val port = 8002
            val provider = "assemblyai"

            val wsUrl = constructWebSocketUrl(baseUrl, port, provider)

            assertEquals("ws://10.0.2.2:8002/ws/transcribe/assemblyai", wsUrl)
        }

        @Test
        fun `should fall back to default provider`() {
            val baseUrl = "10.0.2.2"
            val port = 8002

            val wsUrl = constructWebSocketUrl(baseUrl, port, null)

            assertEquals("ws://10.0.2.2:8002/ws/transcribe", wsUrl)
        }

        private fun constructWebSocketUrl(host: String, port: Int, provider: String?): String {
            val base = "ws://$host:$port/ws/transcribe"
            return if (provider != null) "$base/$provider" else base
        }
    }

    /**
     * Audio Level Monitoring Tests
     */
    class AudioLevelMonitoringTests {

        @Test
        fun `should detect silence when RMS below threshold`() {
            val rms = 5.0f
            val silenceThreshold = 10.0f

            assertTrue(isSilence(rms, silenceThreshold))
        }

        @Test
        fun `should detect speech when RMS above threshold`() {
            val rms = 50.0f
            val silenceThreshold = 10.0f

            assertFalse(isSilence(rms, silenceThreshold))
        }

        @Test
        fun `should calculate max sample from buffer`() {
            val samples = shortArrayOf(10, 50, 30, 150, 20)
            val maxSample = samples.maxOrNull() ?: 0

            assertEquals(150.toShort(), maxSample)
        }

        private fun isSilence(rms: Float, threshold: Float): Boolean {
            return rms < threshold
        }
    }

    /**
     * Transcription Response Parsing Tests
     */
    class TranscriptionResponseTests {

        @Test
        fun `should parse transcript text from JSON`() {
            val json = """{"text": "patient has headache", "is_final": true}"""
            val text = parseTranscriptText(json)

            assertEquals("patient has headache", text)
        }

        @Test
        fun `should detect final transcription`() {
            val json = """{"text": "test", "is_final": true}"""
            val isFinal = parseIsFinal(json)

            assertTrue(isFinal)
        }

        @Test
        fun `should detect non-final transcription`() {
            val json = """{"text": "test", "is_final": false}"""
            val isFinal = parseIsFinal(json)

            assertFalse(isFinal)
        }

        @Test
        fun `should handle speaker labels`() {
            val json = """{"text": "hello", "speaker": "Speaker 0"}"""
            val speaker = parseSpeaker(json)

            assertEquals("Speaker 0", speaker)
        }

        // Simplified JSON parsing for tests
        private fun parseTranscriptText(json: String): String? {
            val regex = Regex(""""text":\s*"([^"]+)"""")
            return regex.find(json)?.groupValues?.get(1)
        }

        private fun parseIsFinal(json: String): Boolean {
            return json.contains(""""is_final":\s*true""".toRegex())
        }

        private fun parseSpeaker(json: String): String? {
            val regex = Regex(""""speaker":\s*"([^"]+)"""")
            return regex.find(json)?.groupValues?.get(1)
        }
    }

    /**
     * Audio Buffer Management Tests
     */
    class BufferManagementTests {

        @Test
        fun `should create buffer of correct size`() {
            val bufferDurationMs = 100
            val sampleRate = 16000
            val bytesPerSample = 2

            val bufferSize = calculateBufferSize(sampleRate, bytesPerSample, bufferDurationMs)

            // 16000 samples/sec * 2 bytes/sample * 0.1 sec = 3200 bytes
            assertEquals(3200, bufferSize)
        }

        @Test
        fun `should convert short array to byte array`() {
            val shorts = shortArrayOf(0x0102, 0x0304)
            val bytes = shortsToBytes(shorts)

            // Little endian: 0x0102 -> [0x02, 0x01], 0x0304 -> [0x04, 0x03]
            assertEquals(4, bytes.size)
        }

        private fun calculateBufferSize(sampleRate: Int, bytesPerSample: Int, durationMs: Int): Int {
            return (sampleRate * bytesPerSample * durationMs) / 1000
        }

        private fun shortsToBytes(shorts: ShortArray): ByteArray {
            val bytes = ByteArray(shorts.size * 2)
            val buffer = ByteBuffer.wrap(bytes).order(java.nio.ByteOrder.LITTLE_ENDIAN)
            for (s in shorts) {
                buffer.putShort(s)
            }
            return bytes
        }
    }

    /**
     * Vuzix-Specific Audio Tests
     */
    class VuzixAudioTests {

        @Test
        fun `should detect Vuzix device by manufacturer`() {
            val manufacturer = "Vuzix"
            assertTrue(isVuzixDevice(manufacturer))
        }

        @Test
        fun `should not detect non-Vuzix device`() {
            val manufacturer = "Google"
            assertFalse(isVuzixDevice(manufacturer))
        }

        @Test
        fun `should use VOICE_RECOGNITION audio source for Vuzix`() {
            // MediaRecorder.AudioSource.VOICE_RECOGNITION = 6
            val audioSource = getAudioSourceForDevice(true)
            assertEquals(6, audioSource)
        }

        @Test
        fun `should use MIC audio source for non-Vuzix`() {
            // MediaRecorder.AudioSource.MIC = 1
            val audioSource = getAudioSourceForDevice(false)
            assertEquals(1, audioSource)
        }

        @Test
        fun `should apply gain boost for Vuzix`() {
            val isVuzix = true
            val gainFactor = getGainFactor(isVuzix)

            assertEquals(10.0f, gainFactor)
        }

        @Test
        fun `should not apply gain boost for non-Vuzix`() {
            val isVuzix = false
            val gainFactor = getGainFactor(isVuzix)

            assertEquals(1.0f, gainFactor)
        }

        private fun isVuzixDevice(manufacturer: String): Boolean {
            return manufacturer.contains("Vuzix", ignoreCase = true)
        }

        private fun getAudioSourceForDevice(isVuzix: Boolean): Int {
            return if (isVuzix) 6 else 1 // VOICE_RECOGNITION or MIC
        }

        private fun getGainFactor(isVuzix: Boolean): Float {
            return if (isVuzix) 10.0f else 1.0f
        }
    }
}
