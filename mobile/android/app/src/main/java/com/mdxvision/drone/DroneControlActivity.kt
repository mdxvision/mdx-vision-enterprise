package com.mdxvision.drone

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Bundle
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.speech.tts.TextToSpeech
import android.util.Log
import android.view.MotionEvent
import android.view.View
import android.widget.Button
import android.widget.FrameLayout
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import com.mdxvision.R
import kotlinx.coroutines.launch
import java.util.Locale
import java.util.UUID

/**
 * Drone Voice Control Activity
 *
 * Push-to-talk interface for controlling drones via voice commands.
 * Communicates with ehr-proxy drone endpoints.
 *
 * Feature-gated: Must be enabled via DroneFeatureFlag.
 */
class DroneControlActivity : AppCompatActivity(), TextToSpeech.OnInitListener {

    companion object {
        private const val TAG = "DroneControl"
        private const val PERMISSION_REQUEST_CODE = 2001

        // Session ID is stable per install
        private var cachedSessionId: String? = null
    }

    // API Client
    private lateinit var droneApi: DroneApiClient

    // Session
    private val sessionId: String
        get() {
            if (cachedSessionId == null) {
                val prefs = getSharedPreferences("DroneControl", MODE_PRIVATE)
                cachedSessionId = prefs.getString("session_id", null)
                    ?: UUID.randomUUID().toString().also {
                        prefs.edit().putString("session_id", it).apply()
                    }
            }
            return cachedSessionId!!
        }

    // Speech
    private var speechRecognizer: SpeechRecognizer? = null
    private var tts: TextToSpeech? = null
    private var isTtsReady = false

    // UI State
    private var currentState: DroneUiState = DroneUiState.Idle
    private var lastParsedResponse: ParseResponse? = null

    // Views
    private lateinit var statusIndicator: TextView
    private lateinit var adapterInfo: TextView
    private lateinit var sessionInfo: TextView
    private lateinit var transcriptCard: LinearLayout
    private lateinit var transcriptText: TextView
    private lateinit var parsedCard: LinearLayout
    private lateinit var intentText: TextView
    private lateinit var normalizedText: TextView
    private lateinit var confidenceText: TextView
    private lateinit var resultCard: LinearLayout
    private lateinit var resultStatusText: TextView
    private lateinit var resultMessageText: TextView
    private lateinit var errorCard: LinearLayout
    private lateinit var errorText: TextView
    private lateinit var stopButton: Button
    private lateinit var pttButton: Button
    private lateinit var confirmButton: Button
    private lateinit var executeButton: Button
    private lateinit var listeningOverlay: FrameLayout
    private lateinit var listeningText: TextView
    private lateinit var disabledOverlay: FrameLayout
    private lateinit var disabledMessage: TextView
    private lateinit var retryButton: Button

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_drone_control)

        // Initialize API client with server URL from MainActivity
        val serverUrl = getSharedPreferences("MDxVision", MODE_PRIVATE)
            .getString("server_url", "http://192.168.1.243:8002") ?: "http://192.168.1.243:8002"
        droneApi = DroneApiClient.getInstance(serverUrl)

        initViews()
        initSpeech()
        setupListeners()

        // Check drone status on startup
        checkDroneStatus()
    }

    private fun initViews() {
        statusIndicator = findViewById(R.id.statusIndicator)
        adapterInfo = findViewById(R.id.adapterInfo)
        sessionInfo = findViewById(R.id.sessionInfo)
        transcriptCard = findViewById(R.id.transcriptCard)
        transcriptText = findViewById(R.id.transcriptText)
        parsedCard = findViewById(R.id.parsedCard)
        intentText = findViewById(R.id.intentText)
        normalizedText = findViewById(R.id.normalizedText)
        confidenceText = findViewById(R.id.confidenceText)
        resultCard = findViewById(R.id.resultCard)
        resultStatusText = findViewById(R.id.resultStatusText)
        resultMessageText = findViewById(R.id.resultMessageText)
        errorCard = findViewById(R.id.errorCard)
        errorText = findViewById(R.id.errorText)
        stopButton = findViewById(R.id.stopButton)
        pttButton = findViewById(R.id.pttButton)
        confirmButton = findViewById(R.id.confirmButton)
        executeButton = findViewById(R.id.executeButton)
        listeningOverlay = findViewById(R.id.listeningOverlay)
        listeningText = findViewById(R.id.listeningText)
        disabledOverlay = findViewById(R.id.disabledOverlay)
        disabledMessage = findViewById(R.id.disabledMessage)
        retryButton = findViewById(R.id.retryButton)

        // Show session ID (truncated)
        sessionInfo.text = "Session: ${sessionId.take(8)}..."
    }

    private fun initSpeech() {
        // Initialize TTS
        tts = TextToSpeech(this, this)

        // Check microphone permission
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO)
            != PackageManager.PERMISSION_GRANTED
        ) {
            ActivityCompat.requestPermissions(
                this,
                arrayOf(Manifest.permission.RECORD_AUDIO),
                PERMISSION_REQUEST_CODE
            )
        } else {
            initSpeechRecognizer()
        }
    }

    private fun initSpeechRecognizer() {
        if (!SpeechRecognizer.isRecognitionAvailable(this)) {
            Toast.makeText(this, "Speech recognition not available", Toast.LENGTH_LONG).show()
            return
        }

        speechRecognizer = SpeechRecognizer.createSpeechRecognizer(this).apply {
            setRecognitionListener(object : RecognitionListener {
                override fun onReadyForSpeech(params: Bundle?) {
                    Log.d(TAG, "Ready for speech")
                    listeningText.text = "Listening..."
                }

                override fun onBeginningOfSpeech() {
                    Log.d(TAG, "Speech started")
                    listeningText.text = "Listening..."
                }

                override fun onRmsChanged(rmsdB: Float) {
                    // Could show audio level indicator
                }

                override fun onBufferReceived(buffer: ByteArray?) {}

                override fun onEndOfSpeech() {
                    Log.d(TAG, "Speech ended")
                    listeningText.text = "Processing..."
                }

                override fun onError(error: Int) {
                    Log.e(TAG, "Speech error: $error")
                    hideListening()
                    val errorMsg = when (error) {
                        SpeechRecognizer.ERROR_AUDIO -> "Audio recording error"
                        SpeechRecognizer.ERROR_CLIENT -> "Client error"
                        SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS -> "Permission denied"
                        SpeechRecognizer.ERROR_NETWORK -> "Network error"
                        SpeechRecognizer.ERROR_NETWORK_TIMEOUT -> "Network timeout"
                        SpeechRecognizer.ERROR_NO_MATCH -> "No speech detected"
                        SpeechRecognizer.ERROR_RECOGNIZER_BUSY -> "Recognizer busy"
                        SpeechRecognizer.ERROR_SERVER -> "Server error"
                        SpeechRecognizer.ERROR_SPEECH_TIMEOUT -> "No speech detected"
                        else -> "Unknown error ($error)"
                    }
                    if (error != SpeechRecognizer.ERROR_NO_MATCH &&
                        error != SpeechRecognizer.ERROR_SPEECH_TIMEOUT
                    ) {
                        showError(errorMsg)
                    }
                }

                override fun onResults(results: Bundle?) {
                    hideListening()
                    val matches = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                    val transcript = matches?.firstOrNull()
                    if (transcript != null) {
                        Log.d(TAG, "Transcript: $transcript")
                        onTranscriptReceived(transcript)
                    } else {
                        showError("No speech detected")
                    }
                }

                override fun onPartialResults(partialResults: Bundle?) {
                    val matches = partialResults?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                    matches?.firstOrNull()?.let {
                        listeningText.text = "\"$it\""
                    }
                }

                override fun onEvent(eventType: Int, params: Bundle?) {}
            })
        }
    }

    private fun setupListeners() {
        // Push-to-talk button
        pttButton.setOnTouchListener { _, event ->
            when (event.action) {
                MotionEvent.ACTION_DOWN -> {
                    startListening()
                    true
                }
                MotionEvent.ACTION_UP, MotionEvent.ACTION_CANCEL -> {
                    stopListening()
                    true
                }
                else -> false
            }
        }

        // STOP button - emergency stop
        stopButton.setOnClickListener {
            emergencyStop()
        }

        // Confirm button
        confirmButton.setOnClickListener {
            lastParsedResponse?.let { confirmCommand(it) }
        }

        // Execute button
        executeButton.setOnClickListener {
            lastParsedResponse?.let { executeCommand(it, confirm = false) }
        }

        // Retry button (when disabled)
        retryButton.setOnClickListener {
            checkDroneStatus()
        }
    }

    private fun checkDroneStatus() {
        lifecycleScope.launch {
            statusIndicator.text = "Checking..."
            statusIndicator.setTextColor(getColor(android.R.color.holo_orange_light))

            droneApi.getStatus().fold(
                onSuccess = { status ->
                    if (status.enabled) {
                        statusIndicator.text = if (status.connected) "Connected" else "Disconnected"
                        statusIndicator.setTextColor(
                            getColor(if (status.connected) android.R.color.holo_green_light else android.R.color.holo_orange_light)
                        )
                        adapterInfo.text = "Adapter: ${status.adapterName ?: "Unknown"} (${status.adapterType ?: "?"})"
                        disabledOverlay.visibility = View.GONE
                        updateState(DroneUiState.Idle)
                    } else {
                        showDisabled(status.message ?: "Drone control disabled on server")
                    }
                },
                onFailure = { error ->
                    Log.e(TAG, "Status check failed", error)
                    showDisabled("Cannot connect to server: ${error.message}")
                }
            )
        }
    }

    private fun showDisabled(message: String) {
        statusIndicator.text = "Disabled"
        statusIndicator.setTextColor(getColor(android.R.color.holo_red_light))
        disabledMessage.text = message
        disabledOverlay.visibility = View.VISIBLE
        updateState(DroneUiState.Disabled)
    }

    private fun startListening() {
        if (currentState == DroneUiState.Disabled) return

        speechRecognizer?.let { recognizer ->
            val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
                putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
                putExtra(RecognizerIntent.EXTRA_LANGUAGE, Locale.US)
                putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
                putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1)
            }
            recognizer.startListening(intent)
            showListening()
            updateState(DroneUiState.Listening)
        }
    }

    private fun stopListening() {
        speechRecognizer?.stopListening()
    }

    private fun showListening() {
        listeningText.text = "Listening..."
        listeningOverlay.visibility = View.VISIBLE
        pttButton.text = "Listening..."
        pttButton.backgroundTintList = ContextCompat.getColorStateList(this, android.R.color.holo_green_dark)
    }

    private fun hideListening() {
        listeningOverlay.visibility = View.GONE
        pttButton.text = "Hold to Speak"
        pttButton.backgroundTintList = ContextCompat.getColorStateList(this, android.R.color.holo_blue_dark)
    }

    private fun onTranscriptReceived(transcript: String) {
        // Show transcript
        transcriptCard.visibility = View.VISIBLE
        transcriptText.text = transcript
        hideError()

        // Parse the command
        parseCommand(transcript)
    }

    private fun parseCommand(transcript: String) {
        updateState(DroneUiState.Processing)

        lifecycleScope.launch {
            droneApi.parse(transcript, sessionId).fold(
                onSuccess = { response ->
                    Log.d(TAG, "Parsed: ${response.intent} | ${response.normalizedCommand}")
                    lastParsedResponse = response
                    showParsedResult(response)

                    if (response.isUnknown) {
                        showError("Command not recognized")
                        speak("Command not recognized")
                        updateState(DroneUiState.Error("Command not recognized"))
                    } else if (response.requiresConfirmation) {
                        // Needs confirmation - show confirm button
                        speak("Confirm ${response.normalizedCommand}?")
                        updateState(DroneUiState.AwaitingConfirmation(response))
                    } else {
                        // Safe command - show execute button for manual execution
                        // (Prioritizing safety over auto-execute)
                        updateState(DroneUiState.Parsed(response))
                    }
                },
                onFailure = { error ->
                    Log.e(TAG, "Parse failed", error)
                    showError("Parse failed: ${error.message}")
                    updateState(DroneUiState.Error(error.message ?: "Parse failed"))
                }
            )
        }
    }

    private fun showParsedResult(response: ParseResponse) {
        parsedCard.visibility = View.VISIBLE
        intentText.text = response.intent
        normalizedText.text = response.normalizedCommand
        confidenceText.text = "Confidence: ${(response.confidence * 100).toInt()}%"

        // Update card color based on intent
        val cardColor = when {
            response.isUnknown -> getColor(android.R.color.darker_gray)
            response.requiresConfirmation -> getColor(android.R.color.holo_orange_dark)
            else -> getColor(android.R.color.holo_green_dark)
        }
        parsedCard.setBackgroundColor(cardColor)
    }

    private fun executeCommand(response: ParseResponse, confirm: Boolean) {
        updateState(DroneUiState.Processing)
        hideActionButtons()

        lifecycleScope.launch {
            droneApi.execute(
                intent = response.intent,
                slots = response.slots,
                confirm = if (confirm) true else null,
                sessionId = sessionId
            ).fold(
                onSuccess = { execResponse ->
                    Log.d(TAG, "Execute result: ${execResponse.status} - ${execResponse.message}")
                    showExecuteResult(execResponse)

                    when {
                        execResponse.status.isSuccess -> {
                            speak(execResponse.message)
                            updateState(DroneUiState.Executed(execResponse))
                        }
                        execResponse.status.needsConfirmation -> {
                            // Shouldn't happen if we confirmed, but handle it
                            speak("Please confirm")
                            updateState(DroneUiState.AwaitingConfirmation(response))
                        }
                        else -> {
                            speak(execResponse.message)
                            updateState(DroneUiState.Error(execResponse.message))
                        }
                    }
                },
                onFailure = { error ->
                    Log.e(TAG, "Execute failed", error)
                    showError("Execute failed: ${error.message}")
                    updateState(DroneUiState.Error(error.message ?: "Execute failed"))
                }
            )
        }
    }

    private fun confirmCommand(response: ParseResponse) {
        executeCommand(response, confirm = true)
    }

    private fun emergencyStop() {
        Log.w(TAG, "EMERGENCY STOP")
        speak("Emergency stop")

        lifecycleScope.launch {
            droneApi.emergencyStop(sessionId).fold(
                onSuccess = { response ->
                    Log.d(TAG, "STOP result: ${response.status} - ${response.message}")
                    showExecuteResult(response)
                    Toast.makeText(this@DroneControlActivity, "STOP executed", Toast.LENGTH_SHORT).show()
                },
                onFailure = { error ->
                    Log.e(TAG, "STOP failed", error)
                    showError("STOP failed: ${error.message}")
                    Toast.makeText(this@DroneControlActivity, "STOP failed!", Toast.LENGTH_LONG).show()
                }
            )
        }
    }

    private fun showExecuteResult(response: ExecuteResponse) {
        resultCard.visibility = View.VISIBLE
        resultStatusText.text = response.status.value.uppercase()
        resultMessageText.text = response.message

        // Update card color based on status
        val cardColor = when (response.status) {
            ExecutionStatus.OK -> getColor(android.R.color.holo_blue_dark)
            ExecutionStatus.NEEDS_CONFIRM -> getColor(android.R.color.holo_orange_dark)
            ExecutionStatus.BLOCKED, ExecutionStatus.RATE_LIMITED -> getColor(android.R.color.holo_red_dark)
            else -> getColor(android.R.color.darker_gray)
        }
        resultCard.setBackgroundColor(cardColor)
    }

    private fun showError(message: String) {
        errorCard.visibility = View.VISIBLE
        errorText.text = message
    }

    private fun hideError() {
        errorCard.visibility = View.GONE
    }

    private fun hideActionButtons() {
        confirmButton.visibility = View.GONE
        executeButton.visibility = View.GONE
    }

    private fun updateState(newState: DroneUiState) {
        currentState = newState

        when (newState) {
            DroneUiState.Idle -> {
                hideActionButtons()
                resultCard.visibility = View.GONE
            }
            DroneUiState.Listening -> {
                hideActionButtons()
            }
            DroneUiState.Processing -> {
                hideActionButtons()
            }
            is DroneUiState.Parsed -> {
                // Show execute button for safe commands
                executeButton.visibility = View.VISIBLE
                confirmButton.visibility = View.GONE
            }
            is DroneUiState.AwaitingConfirmation -> {
                // Show confirm button
                confirmButton.visibility = View.VISIBLE
                executeButton.visibility = View.GONE
            }
            is DroneUiState.Executed -> {
                hideActionButtons()
            }
            is DroneUiState.Error -> {
                hideActionButtons()
            }
            DroneUiState.Disabled -> {
                hideActionButtons()
            }
        }
    }

    private fun speak(text: String) {
        if (isTtsReady) {
            tts?.speak(text, TextToSpeech.QUEUE_ADD, null, "drone_feedback")
        }
    }

    override fun onInit(status: Int) {
        if (status == TextToSpeech.SUCCESS) {
            tts?.language = Locale.US
            isTtsReady = true
        }
    }

    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == PERMISSION_REQUEST_CODE) {
            if (grantResults.isNotEmpty() && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
                initSpeechRecognizer()
            } else {
                Toast.makeText(this, "Microphone permission required", Toast.LENGTH_LONG).show()
                finish()
            }
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        speechRecognizer?.destroy()
        tts?.shutdown()
    }
}
