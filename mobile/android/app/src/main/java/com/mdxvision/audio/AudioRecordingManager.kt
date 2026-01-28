package com.mdxvision.audio

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.util.Log
import androidx.core.content.ContextCompat
import com.mdxvision.AudioStreamingService
import kotlinx.coroutines.*

/**
 * AudioRecordingManager - Extracted from MainActivity (Issue #35)
 *
 * Manages audio recording for:
 * - Live transcription (real-time speech-to-text)
 * - Ambient Clinical Intelligence (background recording)
 * - Voiceprint enrollment and verification
 * - Voice command listening
 *
 * Wraps AudioStreamingService and provides a clean interface for audio operations.
 *
 * Patent Reference: US 15/237,980 - Claims 1-2 (Voice commands via microphone)
 */
class AudioRecordingManager(
    private val context: Context,
    private val config: Config = Config()
) {
    companion object {
        private const val TAG = "AudioRecordingManager"
    }

    /**
     * Configuration for audio recording
     */
    data class Config(
        val wsUrl: String = "ws://10.0.2.2:8002/ws/transcribe",
        val enableNoiseReduction: Boolean = true,
        val autoRestartOnError: Boolean = true,
        val maxRetries: Int = 3
    )

    /**
     * Recording mode
     */
    enum class RecordingMode {
        LIVE_TRANSCRIPTION,     // Real-time transcription with UI
        AMBIENT,                // Background Ambient Clinical Intelligence
        VOICE_COMMAND,          // Listening for voice commands
        VOICEPRINT_ENROLLMENT,  // Recording for voiceprint enrollment
        VOICEPRINT_VERIFY       // Recording for voiceprint verification
    }

    /**
     * Recording state
     */
    enum class RecordingState {
        IDLE,
        CONNECTING,
        RECORDING,
        PAUSED,
        ERROR
    }

    /**
     * Transcription result from audio
     */
    data class TranscriptionResult(
        val text: String,
        val isFinal: Boolean,
        val confidence: Float = 0f,
        val speaker: String? = null,
        val timestamp: Long = System.currentTimeMillis()
    )

    /**
     * Speaker context for diarization
     */
    data class SpeakerContext(
        val clinicianName: String? = null,
        val patientName: String? = null,
        val additionalSpeakers: List<String> = emptyList()
    )

    /**
     * Recording session info
     */
    data class SessionInfo(
        val sessionId: String,
        val provider: String,
        val startTime: Long,
        val mode: RecordingMode
    )

    // Current state
    private var currentState = RecordingState.IDLE
    private var currentMode: RecordingMode? = null
    private var currentSession: SessionInfo? = null

    // Audio streaming service
    private var audioStreamingService: AudioStreamingService? = null

    // Transcript buffer for accumulating results
    private val transcriptBuffer = StringBuilder()

    // Coroutine scope for async operations
    private val scope = CoroutineScope(Dispatchers.Main + SupervisorJob())

    // Callbacks
    var onStateChanged: ((RecordingState, RecordingMode?) -> Unit)? = null
    var onTranscription: ((TranscriptionResult) -> Unit)? = null
    var onSessionStarted: ((SessionInfo) -> Unit)? = null
    var onSessionEnded: ((String, Long) -> Unit)? = null  // (fullTranscript, durationMs)
    var onError: ((String) -> Unit)? = null
    var onPermissionRequired: (() -> Unit)? = null

    /**
     * Check if microphone permission is granted
     */
    fun hasPermission(): Boolean {
        return ContextCompat.checkSelfPermission(context, Manifest.permission.RECORD_AUDIO) ==
                PackageManager.PERMISSION_GRANTED
    }

    /**
     * Get current recording state
     */
    fun getState(): RecordingState = currentState

    /**
     * Get current recording mode
     */
    fun getMode(): RecordingMode? = currentMode

    /**
     * Check if currently recording
     */
    fun isRecording(): Boolean = currentState == RecordingState.RECORDING

    /**
     * Get accumulated transcript
     */
    fun getTranscript(): String = transcriptBuffer.toString()

    /**
     * Clear accumulated transcript
     */
    fun clearTranscript() {
        transcriptBuffer.clear()
    }

    /**
     * Start live transcription
     *
     * @param speakerContext Optional speaker context for diarization
     * @param provider Optional transcription provider ("assemblyai" or "deepgram")
     */
    fun startLiveTranscription(
        speakerContext: SpeakerContext? = null,
        provider: String? = null
    ): Boolean {
        return startRecording(RecordingMode.LIVE_TRANSCRIPTION, speakerContext, provider)
    }

    /**
     * Start ambient mode (Ambient Clinical Intelligence)
     *
     * @param speakerContext Optional speaker context for diarization
     */
    fun startAmbientMode(speakerContext: SpeakerContext? = null): Boolean {
        return startRecording(RecordingMode.AMBIENT, speakerContext)
    }

    /**
     * Start voice command listening
     */
    fun startVoiceCommandListening(): Boolean {
        return startRecording(RecordingMode.VOICE_COMMAND)
    }

    /**
     * Start voiceprint enrollment recording
     */
    fun startVoiceprintEnrollment(): Boolean {
        return startRecording(RecordingMode.VOICEPRINT_ENROLLMENT)
    }

    /**
     * Start voiceprint verification recording
     */
    fun startVoiceprintVerification(): Boolean {
        return startRecording(RecordingMode.VOICEPRINT_VERIFY)
    }

    /**
     * Internal method to start recording with specified mode
     */
    private fun startRecording(
        mode: RecordingMode,
        speakerContext: SpeakerContext? = null,
        provider: String? = null
    ): Boolean {
        // Check permission
        if (!hasPermission()) {
            Log.w(TAG, "Microphone permission not granted")
            onPermissionRequired?.invoke()
            return false
        }

        // Check if already recording
        if (currentState == RecordingState.RECORDING) {
            Log.w(TAG, "Already recording in mode: $currentMode")
            return false
        }

        Log.d(TAG, "Starting recording in mode: $mode")
        updateState(RecordingState.CONNECTING, mode)
        transcriptBuffer.clear()

        // Create audio streaming service
        audioStreamingService = AudioStreamingService(context) { result ->
            handleTranscriptionResult(result)
        }

        // Set up callbacks
        audioStreamingService?.onConnected = { sessionId, providerName ->
            val session = SessionInfo(
                sessionId = sessionId,
                provider = providerName,
                startTime = System.currentTimeMillis(),
                mode = mode
            )
            currentSession = session
            updateState(RecordingState.RECORDING, mode)
            onSessionStarted?.invoke(session)
            Log.d(TAG, "Recording session started: $sessionId via $providerName")
        }

        audioStreamingService?.onDisconnected = { fullTranscript ->
            val duration = currentSession?.let {
                System.currentTimeMillis() - it.startTime
            } ?: 0L
            onSessionEnded?.invoke(fullTranscript, duration)
            cleanup()
            Log.d(TAG, "Recording session ended: ${fullTranscript.length} chars, ${duration}ms")
        }

        audioStreamingService?.onError = { message ->
            Log.e(TAG, "Recording error: $message")
            onError?.invoke(message)
            updateState(RecordingState.ERROR, mode)

            // Auto-restart if configured
            if (config.autoRestartOnError) {
                scope.launch {
                    delay(1000)
                    if (currentState == RecordingState.ERROR) {
                        Log.d(TAG, "Auto-restarting after error")
                        startRecording(mode, speakerContext, provider)
                    }
                }
            }
        }

        // Build speaker context for AudioStreamingService
        val audioSpeakerContext = speakerContext?.let {
            AudioStreamingService.SpeakerContext(
                clinician = it.clinicianName,
                patient = it.patientName,
                others = it.additionalSpeakers
            )
        }

        // Start streaming
        return if (audioStreamingService?.startStreaming(
                provider = provider,
                speakerContext = audioSpeakerContext
            ) == true
        ) {
            currentMode = mode
            true
        } else {
            Log.e(TAG, "Failed to start streaming")
            updateState(RecordingState.ERROR, mode)
            onError?.invoke("Failed to start audio streaming")
            false
        }
    }

    /**
     * Stop recording
     *
     * @param generateOutput Whether to trigger output generation (e.g., SOAP note)
     */
    fun stopRecording(generateOutput: Boolean = true): String {
        if (currentState != RecordingState.RECORDING) {
            Log.w(TAG, "Not currently recording")
            return transcriptBuffer.toString()
        }

        Log.d(TAG, "Stopping recording, generateOutput=$generateOutput")
        audioStreamingService?.stopStreaming()

        val transcript = transcriptBuffer.toString()
        cleanup()

        return transcript
    }

    /**
     * Pause recording (if supported)
     */
    fun pauseRecording() {
        if (currentState == RecordingState.RECORDING) {
            // AudioStreamingService doesn't support pause, so we stop and remember state
            Log.d(TAG, "Pausing recording")
            audioStreamingService?.stopStreaming()
            updateState(RecordingState.PAUSED, currentMode)
        }
    }

    /**
     * Resume recording (if paused)
     */
    fun resumeRecording(): Boolean {
        if (currentState == RecordingState.PAUSED && currentMode != null) {
            Log.d(TAG, "Resuming recording in mode: $currentMode")
            return startRecording(currentMode!!)
        }
        return false
    }

    /**
     * Handle transcription result from AudioStreamingService
     */
    private fun handleTranscriptionResult(result: AudioStreamingService.TranscriptionResult) {
        val transcriptionResult = TranscriptionResult(
            text = result.text,
            isFinal = result.isFinal,
            confidence = result.confidence,
            speaker = result.speaker
        )

        // Accumulate final results
        if (result.isFinal && result.text.isNotBlank()) {
            if (transcriptBuffer.isNotEmpty()) {
                transcriptBuffer.append(" ")
            }
            transcriptBuffer.append(result.text)
        }

        // Notify listener
        onTranscription?.invoke(transcriptionResult)
    }

    /**
     * Update state and notify listener
     */
    private fun updateState(newState: RecordingState, mode: RecordingMode?) {
        currentState = newState
        currentMode = mode
        onStateChanged?.invoke(newState, mode)
    }

    /**
     * Clean up resources
     */
    private fun cleanup() {
        updateState(RecordingState.IDLE, null)
        currentSession = null
    }

    /**
     * Destroy manager and release all resources
     */
    fun destroy() {
        Log.d(TAG, "Destroying AudioRecordingManager")
        scope.cancel()
        audioStreamingService?.destroy()
        audioStreamingService = null
        cleanup()
    }

    /**
     * Configure WebSocket URL for physical devices
     */
    fun setWebSocketUrl(url: String) {
        AudioStreamingService.setDeviceUrl(url)
        Log.d(TAG, "WebSocket URL set to: $url")
    }

    /**
     * Get current WebSocket URL
     */
    fun getWebSocketUrl(): String = AudioStreamingService.getDeviceUrl()

    /**
     * Check if the device is an emulator
     */
    fun isEmulator(): Boolean {
        return android.os.Build.FINGERPRINT.contains("generic") ||
                android.os.Build.MODEL.contains("Emulator") ||
                android.os.Build.MANUFACTURER.contains("Genymotion")
    }

    /**
     * Check if the device is Vuzix glasses
     */
    fun isVuzixDevice(): Boolean {
        return android.os.Build.MANUFACTURER.contains("Vuzix", ignoreCase = true)
    }
}
