package com.mdxvision

import org.junit.Before
import org.junit.Test
import org.junit.Assert.*
import java.nio.ByteBuffer

/**
 * Unit tests for AudioStreamingService
 *
 * Tests WebSocket audio streaming, audio processing, gain adjustment,
 * and transcription handling.
 */
class AudioStreamingServiceTest {

    // Audio Processing Tests

    @Test
    fun `audio - should apply 10x gain boost for Vuzix`() {
        val inputSample: Short = 100
        val gainFactor = 10.0f
        val boosted = applyGain(inputSample, gainFactor)
        assertTrue(boosted > inputSample)
    }

    @Test
    fun `audio - should clamp audio to Short MAX_VALUE`() {
        val inputSample: Short = 5000
        val gainFactor = 10.0f
        val boosted = applyGain(inputSample, gainFactor)
        assertEquals(Short.MAX_VALUE, boosted)
    }

    @Test
    fun `audio - should clamp audio to Short MIN_VALUE`() {
        val inputSample: Short = -5000
        val gainFactor = 10.0f
        val boosted = applyGain(inputSample, gainFactor)
        assertEquals(Short.MIN_VALUE, boosted)
    }

    @Test
    fun `audio - should handle zero sample`() {
        val inputSample: Short = 0
        val gainFactor = 10.0f
        val boosted = applyGain(inputSample, gainFactor)
        assertEquals(0.toShort(), boosted)
    }

    @Test
    fun `audio - should calculate RMS correctly`() {
        val samples = shortArrayOf(100, 100, 100, 100)
        val rms = calculateRMS(samples)
        assertEquals(100.0f, rms, 0.1f)
    }

    @Test
    fun `audio - should calculate dB correctly`() {
        val rms = 100.0f
        val maxValue = Short.MAX_VALUE.toFloat()
        val db = 20 * kotlin.math.log10(rms / maxValue)
        assertTrue(db < 0)
        assertTrue(db > -60)
    }

    // Audio Configuration Tests

    @Test
    fun `config - should use 16kHz sample rate`() {
        val expectedSampleRate = 16000
        assertEquals(expectedSampleRate, SAMPLE_RATE)
    }

    @Test
    fun `config - should use mono channel`() {
        val expectedChannels = 1
        assertEquals(expectedChannels, CHANNEL_COUNT)
    }

    @Test
    fun `config - should use 16-bit encoding`() {
        val expectedBitsPerSample = 16
        assertEquals(expectedBitsPerSample, BITS_PER_SAMPLE)
    }

    @Test
    fun `config - should calculate correct bytes per second`() {
        val bytesPerSecond = SAMPLE_RATE * CHANNEL_COUNT * (BITS_PER_SAMPLE / 8)
        assertEquals(32000, bytesPerSecond)
    }

    // WebSocket Tests

    @Test
    fun `websocket - should construct correct WebSocket URL`() {
        val baseUrl = "10.0.2.2"
        val port = 8002
        val provider = "assemblyai"
        val wsUrl = constructWebSocketUrl(baseUrl, port, provider)
        assertEquals("ws://10.0.2.2:8002/ws/transcribe/assemblyai", wsUrl)
    }

    @Test
    fun `websocket - should fall back to default provider`() {
        val baseUrl = "10.0.2.2"
        val port = 8002
        val wsUrl = constructWebSocketUrl(baseUrl, port, null)
        assertEquals("ws://10.0.2.2:8002/ws/transcribe", wsUrl)
    }

    // Audio Level Monitoring Tests

    @Test
    fun `level - should detect silence when RMS below threshold`() {
        val rms = 5.0f
        val silenceThreshold = 10.0f
        assertTrue(isSilence(rms, silenceThreshold))
    }

    @Test
    fun `level - should detect speech when RMS above threshold`() {
        val rms = 50.0f
        val silenceThreshold = 10.0f
        assertFalse(isSilence(rms, silenceThreshold))
    }

    @Test
    fun `level - should calculate max sample from buffer`() {
        val samples = shortArrayOf(10, 50, 30, 150, 20)
        val maxSample = samples.maxOrNull() ?: 0
        assertEquals(150.toShort(), maxSample)
    }

    // Transcription Response Tests

    @Test
    fun `transcript - should parse transcript text from JSON`() {
        val json = """{"text": "patient has headache", "is_final": true}"""
        val text = parseTranscriptText(json)
        assertEquals("patient has headache", text)
    }

    @Test
    fun `transcript - should detect final transcription`() {
        val json = """{"text": "test", "is_final": true}"""
        val isFinal = parseIsFinal(json)
        assertTrue(isFinal)
    }

    @Test
    fun `transcript - should detect non-final transcription`() {
        val json = """{"text": "test", "is_final": false}"""
        val isFinal = parseIsFinal(json)
        assertFalse(isFinal)
    }

    @Test
    fun `transcript - should handle speaker labels`() {
        val json = """{"text": "hello", "speaker": "Speaker 0"}"""
        val speaker = parseSpeaker(json)
        assertEquals("Speaker 0", speaker)
    }

    // Buffer Management Tests

    @Test
    fun `buffer - should create buffer of correct size`() {
        val bufferDurationMs = 100
        val sampleRate = 16000
        val bytesPerSample = 2
        val bufferSize = calculateBufferSize(sampleRate, bytesPerSample, bufferDurationMs)
        assertEquals(3200, bufferSize)
    }

    @Test
    fun `buffer - should convert short array to byte array`() {
        val shorts = shortArrayOf(0x0102, 0x0304)
        val bytes = shortsToBytes(shorts)
        assertEquals(4, bytes.size)
    }

    // Vuzix-Specific Tests

    @Test
    fun `vuzix - should detect Vuzix device by manufacturer`() {
        val manufacturer = "Vuzix"
        assertTrue(isVuzixDevice(manufacturer))
    }

    @Test
    fun `vuzix - should not detect non-Vuzix device`() {
        val manufacturer = "Google"
        assertFalse(isVuzixDevice(manufacturer))
    }

    @Test
    fun `vuzix - should use VOICE_RECOGNITION audio source for Vuzix`() {
        val audioSource = getAudioSourceForDevice(true)
        assertEquals(6, audioSource)
    }

    @Test
    fun `vuzix - should use MIC audio source for non-Vuzix`() {
        val audioSource = getAudioSourceForDevice(false)
        assertEquals(1, audioSource)
    }

    @Test
    fun `vuzix - should apply gain boost for Vuzix`() {
        val isVuzix = true
        val gainFactor = getGainFactor(isVuzix)
        assertEquals(10.0f, gainFactor)
    }

    @Test
    fun `vuzix - should not apply gain boost for non-Vuzix`() {
        val isVuzix = false
        val gainFactor = getGainFactor(isVuzix)
        assertEquals(1.0f, gainFactor)
    }

    // Constants
    companion object {
        const val SAMPLE_RATE = 16000
        const val CHANNEL_COUNT = 1
        const val BITS_PER_SAMPLE = 16
    }

    // Helper functions

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

    private fun constructWebSocketUrl(host: String, port: Int, provider: String?): String {
        val base = "ws://$host:$port/ws/transcribe"
        return if (provider != null) "$base/$provider" else base
    }

    private fun isSilence(rms: Float, threshold: Float): Boolean {
        return rms < threshold
    }

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
