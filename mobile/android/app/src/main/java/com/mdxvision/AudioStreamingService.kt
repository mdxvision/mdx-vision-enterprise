package com.mdxvision

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import android.util.Log
import androidx.core.content.ContextCompat
import kotlinx.coroutines.*
import okhttp3.*
import okio.ByteString
import okio.ByteString.Companion.toByteString
import org.json.JSONObject
import java.nio.ByteBuffer
import java.nio.ByteOrder

/**
 * MDx Vision - Real-Time Audio Streaming Service
 *
 * Streams audio to the EHR proxy for transcription via AssemblyAI or Deepgram.
 *
 * Usage:
 *   val service = AudioStreamingService(context) { result ->
 *       // Handle transcription result
 *       Log.d("Transcript", result.text)
 *   }
 *   service.startStreaming()
 *   // ... later
 *   service.stopStreaming()
 */
class AudioStreamingService(
    private val context: Context,
    private val onTranscription: (TranscriptionResult) -> Unit
) {
    companion object {
        private const val TAG = "AudioStreaming"

        // Audio configuration (must match server expectations)
        const val SAMPLE_RATE = 16000
        const val CHANNEL_CONFIG = AudioFormat.CHANNEL_IN_MONO
        const val AUDIO_FORMAT = AudioFormat.ENCODING_PCM_16BIT
        const val BUFFER_SIZE_FACTOR = 2

        // WebSocket URL (10.0.2.2 = host machine from emulator)
        const val WS_URL_EMULATOR = "ws://10.0.2.2:8002/ws/transcribe"
        const val WS_URL_DEVICE = "ws://192.168.1.243:8002/ws/transcribe"  // Mac IP for Galaxy S24
    }

    data class TranscriptionResult(
        val text: String,
        val isFinal: Boolean,
        val confidence: Float = 0f,
        val speaker: String? = null
    )

    /**
     * Speaker context for name mapping
     */
    data class SpeakerContext(
        val clinician: String? = null,
        val patient: String? = null,
        val others: List<String> = emptyList()
    )

    private var webSocket: WebSocket? = null
    private var audioRecord: AudioRecord? = null
    private var isStreaming = false
    private var recordingJob: Job? = null
    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())

    private val client = OkHttpClient.Builder()
        .readTimeout(0, java.util.concurrent.TimeUnit.MILLISECONDS)
        .build()

    // Speaker context to send after connection
    private var pendingSpeakerContext: SpeakerContext? = null

    // Callbacks
    var onConnected: ((sessionId: String, provider: String) -> Unit)? = null
    var onDisconnected: ((fullTranscript: String) -> Unit)? = null
    var onError: ((message: String) -> Unit)? = null
    var onSpeakerContextSet: ((clinician: String?, patient: String?) -> Unit)? = null

    /**
     * Start streaming audio to the transcription service
     *
     * @param provider Optional provider override ("assemblyai" or "deepgram")
     * @param speakerContext Optional speaker context for name mapping
     */
    fun startStreaming(provider: String? = null, speakerContext: SpeakerContext? = null): Boolean {
        if (isStreaming) {
            Log.w(TAG, "Already streaming")
            return false
        }

        // Store speaker context to send after connection
        pendingSpeakerContext = speakerContext

        // Check permission
        if (ContextCompat.checkSelfPermission(context, Manifest.permission.RECORD_AUDIO)
            != PackageManager.PERMISSION_GRANTED
        ) {
            Log.e(TAG, "RECORD_AUDIO permission not granted")
            onError?.invoke("Microphone permission required")
            return false
        }

        // Determine WebSocket URL - use device URL for physical devices
        val isEmulator = android.os.Build.FINGERPRINT.contains("generic") ||
                         android.os.Build.MODEL.contains("Emulator") ||
                         android.os.Build.MANUFACTURER.contains("Genymotion")
        val baseUrl = if (isEmulator) WS_URL_EMULATOR else WS_URL_DEVICE
        val wsUrl = if (provider != null) {
            "${baseUrl.removeSuffix("/ws/transcribe")}/ws/transcribe/$provider"
        } else {
            baseUrl
        }

        Log.d(TAG, "Connecting to: $wsUrl")

        // Connect WebSocket
        val request = Request.Builder()
            .url(wsUrl)
            .build()

        webSocket = client.newWebSocket(request, object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) {
                Log.d(TAG, "WebSocket connected")
            }

            override fun onMessage(webSocket: WebSocket, text: String) {
                handleMessage(text)
            }

            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                Log.e(TAG, "WebSocket error: ${t.message}")
                isStreaming = false
                onError?.invoke(t.message ?: "Connection failed")
            }

            override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
                Log.d(TAG, "WebSocket closed: $reason")
                isStreaming = false
            }
        })

        return true
    }

    private fun handleMessage(text: String) {
        try {
            val json = JSONObject(text)
            val type = json.optString("type", "")

            when (type) {
                "connected" -> {
                    val sessionId = json.optString("session_id", "")
                    val provider = json.optString("provider", "")
                    Log.d(TAG, "Session started: $sessionId ($provider)")
                    isStreaming = true
                    onConnected?.invoke(sessionId, provider)

                    // Send speaker context if available
                    pendingSpeakerContext?.let { context ->
                        sendSpeakerContext(context)
                        Log.d(TAG, "Sent speaker context: clinician=${context.clinician}, patient=${context.patient}")
                    }

                    // Start recording audio
                    startRecording()
                }

                "transcript" -> {
                    val speakerValue = if (json.has("speaker") && !json.isNull("speaker")) {
                        json.optString("speaker")
                    } else null

                    val result = TranscriptionResult(
                        text = json.optString("text", ""),
                        isFinal = json.optBoolean("is_final", false),
                        confidence = json.optDouble("confidence", 0.0).toFloat(),
                        speaker = speakerValue
                    )
                    if (result.text.isNotEmpty()) {
                        onTranscription(result)
                    }
                }

                "ended" -> {
                    val fullTranscript = json.optString("full_transcript", "")
                    Log.d(TAG, "Session ended, transcript length: ${fullTranscript.length}")
                    onDisconnected?.invoke(fullTranscript)
                }

                "error" -> {
                    val message = json.optString("message", "Unknown error")
                    Log.e(TAG, "Server error: $message")
                    onError?.invoke(message)
                }

                "pong" -> {
                    // Keepalive response
                }

                "speaker_context_set" -> {
                    val clinician = if (json.has("clinician") && !json.isNull("clinician")) json.optString("clinician") else null
                    val patient = if (json.has("patient") && !json.isNull("patient")) json.optString("patient") else null
                    Log.d(TAG, "Speaker context confirmed: clinician=$clinician, patient=$patient")
                    onSpeakerContextSet?.invoke(clinician, patient)
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error parsing message: ${e.message}")
        }
    }

    /**
     * Send speaker context to map speaker IDs to actual names
     */
    private fun sendSpeakerContext(context: SpeakerContext) {
        try {
            val json = JSONObject().apply {
                put("type", "speaker_context")
                context.clinician?.let { put("clinician", it) }
                context.patient?.let { put("patient", it) }
                if (context.others.isNotEmpty()) {
                    put("others", org.json.JSONArray(context.others))
                }
            }
            webSocket?.send(json.toString())
        } catch (e: Exception) {
            Log.e(TAG, "Error sending speaker context: ${e.message}")
        }
    }

    /**
     * Update speaker context during an active session
     */
    fun updateSpeakerContext(clinician: String? = null, patient: String? = null, others: List<String> = emptyList()) {
        val context = SpeakerContext(clinician, patient, others)
        if (isStreaming) {
            sendSpeakerContext(context)
        } else {
            pendingSpeakerContext = context
        }
    }

    private fun startRecording() {
        val bufferSize = AudioRecord.getMinBufferSize(
            SAMPLE_RATE,
            CHANNEL_CONFIG,
            AUDIO_FORMAT
        ) * BUFFER_SIZE_FACTOR

        try {
            audioRecord = AudioRecord(
                MediaRecorder.AudioSource.MIC,
                SAMPLE_RATE,
                CHANNEL_CONFIG,
                AUDIO_FORMAT,
                bufferSize
            )

            if (audioRecord?.state != AudioRecord.STATE_INITIALIZED) {
                Log.e(TAG, "AudioRecord failed to initialize")
                onError?.invoke("Failed to initialize microphone")
                return
            }

            audioRecord?.startRecording()
            Log.d(TAG, "Recording started, buffer size: $bufferSize")

            // Start sending audio in background
            recordingJob = scope.launch {
                val buffer = ShortArray(bufferSize / 2)  // 16-bit samples

                while (isActive && isStreaming) {
                    val readCount = audioRecord?.read(buffer, 0, buffer.size) ?: 0

                    if (readCount > 0) {
                        // Convert shorts to bytes (little-endian PCM)
                        val byteBuffer = ByteBuffer.allocate(readCount * 2)
                        byteBuffer.order(ByteOrder.LITTLE_ENDIAN)
                        for (i in 0 until readCount) {
                            byteBuffer.putShort(buffer[i])
                        }

                        // Send to WebSocket
                        webSocket?.send(byteBuffer.array().toByteString())
                    }

                    // Small delay to prevent overwhelming the network
                    delay(20)
                }
            }

        } catch (e: SecurityException) {
            Log.e(TAG, "Security exception: ${e.message}")
            onError?.invoke("Microphone access denied")
        } catch (e: Exception) {
            Log.e(TAG, "Recording error: ${e.message}")
            onError?.invoke("Recording failed: ${e.message}")
        }
    }

    /**
     * Stop streaming and get final transcript
     */
    fun stopStreaming() {
        if (!isStreaming) {
            Log.w(TAG, "Not streaming")
            return
        }

        Log.d(TAG, "Stopping stream...")
        isStreaming = false

        // Stop recording
        recordingJob?.cancel()
        audioRecord?.stop()
        audioRecord?.release()
        audioRecord = null

        // Send stop message
        try {
            webSocket?.send("{\"type\":\"stop\"}")
        } catch (e: Exception) {
            Log.e(TAG, "Error sending stop: ${e.message}")
        }

        // Close WebSocket after brief delay (to receive final transcript)
        scope.launch {
            delay(500)
            webSocket?.close(1000, "Session ended")
            webSocket = null
        }
    }

    /**
     * Check if currently streaming
     */
    fun isActive(): Boolean = isStreaming

    /**
     * Send a ping to keep connection alive
     */
    fun sendPing() {
        webSocket?.send("{\"type\":\"ping\"}")
    }

    /**
     * Clean up resources
     */
    fun destroy() {
        stopStreaming()
        scope.cancel()
        client.dispatcher.executorService.shutdown()
    }
}
