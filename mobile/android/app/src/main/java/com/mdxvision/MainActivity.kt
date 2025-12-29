package com.mdxvision

import android.Manifest
import android.content.Context
import android.content.Intent
import android.content.SharedPreferences
import android.content.pm.PackageManager
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import android.os.Bundle
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.util.Log
import android.widget.TextView
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.io.IOException

/**
 * MDx Vision - Main Activity
 * AR Smart Glasses Healthcare Documentation
 *
 * Patent Implementation:
 * - Claim 1-2: Voice commands via microphone
 * - Claim 5-7: Camera patient identification
 * - Claim 8: AR display overlay
 * - Claim 9: Wireless EHR connection
 */
class MainActivity : AppCompatActivity() {

    companion object {
        private const val TAG = "MDxVision"
        private const val PERMISSION_REQUEST_CODE = 1001
        private const val EHR_PROXY_URL = "http://10.0.2.2:8002" // EHR Proxy on host machine
        // Test patient from Cerner sandbox
        private const val TEST_PATIENT_ID = "12724066"
        // Offline cache
        private const val PREFS_NAME = "MDxVisionCache"
        private const val CACHE_PREFIX = "patient_"
        private const val CACHE_TIMESTAMP_SUFFIX = "_timestamp"
        private const val CACHE_MAX_AGE_MS = 24 * 60 * 60 * 1000L // 24 hours
    }

    // Offline cache
    private lateinit var cachePrefs: SharedPreferences

    private lateinit var speechRecognizer: SpeechRecognizer
    private lateinit var statusText: TextView
    private lateinit var transcriptText: TextView
    private lateinit var patientDataText: TextView
    private val httpClient = OkHttpClient.Builder()
        .connectTimeout(30, java.util.concurrent.TimeUnit.SECONDS)
        .readTimeout(60, java.util.concurrent.TimeUnit.SECONDS)
        .writeTimeout(30, java.util.concurrent.TimeUnit.SECONDS)
        .build()

    // Documentation mode
    private var isDocumentationMode = false
    private val documentationTranscripts = mutableListOf<String>()

    // Wake word and continuous listening (Patent Claims 1-4)
    private var isContinuousListening = false
    private val WAKE_WORD = "hey mdx"
    private var awaitingCommand = false

    // Live transcription via WebSocket (AssemblyAI/Deepgram)
    private var audioStreamingService: AudioStreamingService? = null
    private var isLiveTranscribing = false
    private var liveTranscriptText: TextView? = null
    private val liveTranscriptBuffer = StringBuilder()

    // Last generated note for saving
    private var lastGeneratedNote: JSONObject? = null
    private var lastNoteTranscript: String? = null

    // Barcode scanner launcher
    private val barcodeLauncher = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) { result ->
        if (result.resultCode == RESULT_OK) {
            val mrn = result.data?.getStringExtra(BarcodeScannerActivity.EXTRA_MRN)
            if (mrn != null) {
                Log.d(TAG, "Scanned MRN: $mrn")
                transcriptText.text = "Scanned MRN: $mrn"
                fetchPatientByMrn(mrn)
            }
        }
    }

    private val requiredPermissions = arrayOf(
        Manifest.permission.RECORD_AUDIO,
        Manifest.permission.CAMERA
    )

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Initialize offline cache
        cachePrefs = getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)

        // Simple layout for AR glasses
        setupUI()

        Log.d(TAG, "MDx Vision starting on ${android.os.Build.MANUFACTURER} ${android.os.Build.MODEL}")

        // Check if running on Vuzix
        if (isVuzixDevice()) {
            Log.d(TAG, "Vuzix device detected")
            statusText.text = "MDx Vision - Vuzix Mode"
        } else {
            statusText.text = "MDx Vision - Standard Mode"
        }

        checkPermissions()
    }

    // Data overlay for showing patient info
    private var dataOverlay: android.widget.FrameLayout? = null

    private fun setupUI() {
        // Main container
        val rootLayout = android.widget.FrameLayout(this).apply {
            setBackgroundColor(0xFF0A1628.toInt())
        }

        // Voice command grid layout
        val mainLayout = android.widget.LinearLayout(this).apply {
            orientation = android.widget.LinearLayout.VERTICAL
            setPadding(24, 24, 24, 24)
        }

        // Status bar at top
        val statusBar = android.widget.LinearLayout(this).apply {
            orientation = android.widget.LinearLayout.HORIZONTAL
            setPadding(0, 0, 0, 16)
        }

        statusText = TextView(this).apply {
            text = "MDx Vision"
            textSize = 20f
            setTextColor(0xFF10B981.toInt())
            layoutParams = android.widget.LinearLayout.LayoutParams(0, android.widget.LinearLayout.LayoutParams.WRAP_CONTENT, 1f)
        }
        statusBar.addView(statusText)

        transcriptText = TextView(this).apply {
            text = "Tap or speak a command"
            textSize = 14f
            setTextColor(0xFF94A3B8.toInt())
            gravity = android.view.Gravity.END
        }
        statusBar.addView(transcriptText)
        mainLayout.addView(statusBar)

        // Voice commands grid - 2 columns, 6 rows (12 buttons)
        val gridLayout = android.widget.GridLayout(this).apply {
            columnCount = 2
            rowCount = 6
            layoutParams = android.widget.LinearLayout.LayoutParams(
                android.widget.LinearLayout.LayoutParams.MATCH_PARENT,
                0, 1f
            )
        }

        // Define all voice commands
        val commands = listOf(
            CommandButton("HEY MDX MODE", 0xFF3B82F6.toInt()) { toggleContinuousListening() },
            CommandButton("LOAD PATIENT", 0xFF6366F1.toInt()) { fetchPatientData(TEST_PATIENT_ID) },
            CommandButton("FIND PATIENT", 0xFF8B5CF6.toInt()) { promptFindPatient() },
            CommandButton("SCAN WRISTBAND", 0xFFEC4899.toInt()) { startBarcodeScanner() },
            CommandButton("SHOW VITALS", 0xFF10B981.toInt()) { fetchPatientSection("vitals") },
            CommandButton("SHOW ALLERGIES", 0xFFEF4444.toInt()) { fetchPatientSection("allergies") },
            CommandButton("SHOW MEDS", 0xFFF59E0B.toInt()) { fetchPatientSection("medications") },
            CommandButton("SHOW LABS", 0xFF06B6D4.toInt()) { fetchPatientSection("labs") },
            CommandButton("SHOW PROCEDURES", 0xFF84CC16.toInt()) { fetchPatientSection("procedures") },
            CommandButton("START NOTE", 0xFFFFB800.toInt()) { toggleDocumentationMode() },
            CommandButton("LIVE TRANSCRIBE", 0xFFE11D48.toInt()) { toggleLiveTranscription() },
            CommandButton("SAVE NOTE", 0xFF22C55E.toInt()) { saveCurrentNote() }
        )

        commands.forEachIndexed { index, cmd ->
            val button = android.widget.Button(this).apply {
                text = cmd.label
                setBackgroundColor(cmd.color)
                setTextColor(0xFFFFFFFF.toInt())
                textSize = 16f
                isAllCaps = true
                setPadding(16, 32, 16, 32)

                val params = android.widget.GridLayout.LayoutParams().apply {
                    width = 0
                    height = 0
                    columnSpec = android.widget.GridLayout.spec(index % 2, 1f)
                    rowSpec = android.widget.GridLayout.spec(index / 2, 1f)
                    setMargins(8, 8, 8, 8)
                }
                layoutParams = params

                setOnClickListener { cmd.action() }
            }
            gridLayout.addView(button)
        }

        mainLayout.addView(gridLayout)
        rootLayout.addView(mainLayout)

        // Hidden patient data overlay (shown when data is loaded)
        patientDataText = TextView(this) // Hidden placeholder

        setContentView(rootLayout)
    }

    private data class CommandButton(val label: String, val color: Int, val action: () -> Unit)

    private fun promptFindPatient() {
        // Start voice recognition for patient name search
        statusText.text = "Say patient name..."
        transcriptText.text = "Listening for name"
        startVoiceRecognition()
    }

    private fun toggleContinuousListening() {
        isContinuousListening = !isContinuousListening

        if (isContinuousListening) {
            statusText.text = "Hey MDx - Listening"
            transcriptText.text = "Say 'Hey MDx' then your command"
            awaitingCommand = false
            startVoiceRecognition()
        } else {
            statusText.text = "MDx Vision"
            transcriptText.text = "Tap or speak a command"
            awaitingCommand = false
            try {
                speechRecognizer.stopListening()
            } catch (e: Exception) {
                Log.e(TAG, "Error stopping speech: ${e.message}")
            }
        }
    }

    private fun showDataOverlay(title: String, content: String) {
        // Remove existing overlay if any
        dataOverlay?.let { (it.parent as? android.view.ViewGroup)?.removeView(it) }

        val rootView = window.decorView.findViewById<android.view.ViewGroup>(android.R.id.content)

        dataOverlay = android.widget.FrameLayout(this).apply {
            setBackgroundColor(0xEE0A1628.toInt())
            isClickable = true

            val innerLayout = android.widget.LinearLayout(context).apply {
                orientation = android.widget.LinearLayout.VERTICAL
                setPadding(32, 32, 32, 32)
                layoutParams = android.widget.FrameLayout.LayoutParams(
                    android.widget.FrameLayout.LayoutParams.MATCH_PARENT,
                    android.widget.FrameLayout.LayoutParams.MATCH_PARENT
                )
            }

            // Title
            val titleText = TextView(context).apply {
                text = title
                textSize = 22f
                setTextColor(0xFF10B981.toInt())
                setPadding(0, 0, 0, 16)
            }
            innerLayout.addView(titleText)

            // Scrollable content
            val scrollView = android.widget.ScrollView(context).apply {
                layoutParams = android.widget.LinearLayout.LayoutParams(
                    android.widget.LinearLayout.LayoutParams.MATCH_PARENT, 0, 1f
                )
            }

            val contentText = TextView(context).apply {
                text = content
                textSize = 16f
                setTextColor(0xFFF8FAFC.toInt())
                setLineSpacing(4f, 1.2f)
            }
            scrollView.addView(contentText)
            innerLayout.addView(scrollView)

            // Close button
            val closeButton = android.widget.Button(context).apply {
                text = "CLOSE (or say 'close')"
                setBackgroundColor(0xFF475569.toInt())
                setTextColor(0xFFFFFFFF.toInt())
                setPadding(32, 24, 32, 24)
                setOnClickListener { hideDataOverlay() }
            }
            innerLayout.addView(closeButton)

            addView(innerLayout)
        }

        rootView.addView(dataOverlay)
        statusText.text = title
        transcriptText.text = "Say 'close' to dismiss"
    }

    private fun hideDataOverlay() {
        dataOverlay?.let { overlay ->
            (overlay.parent as? android.view.ViewGroup)?.removeView(overlay)
            dataOverlay = null
        }
        statusText.text = "MDx Vision"
        transcriptText.text = "Tap or speak a command"
    }

    private fun startBarcodeScanner() {
        val intent = Intent(this, BarcodeScannerActivity::class.java)
        barcodeLauncher.launch(intent)
    }

    private fun toggleDocumentationMode() {
        isDocumentationMode = !isDocumentationMode

        if (isDocumentationMode) {
            // Start documentation mode
            documentationTranscripts.clear()
            statusText.text = "DOCUMENTING"
            transcriptText.text = "Speak... say 'stop note' to finish"
            startVoiceRecognition()
        } else {
            // End documentation mode - generate note
            if (documentationTranscripts.isNotEmpty()) {
                generateClinicalNote(documentationTranscripts.joinToString(" "))
            } else {
                statusText.text = "MDx Vision"
                transcriptText.text = "No transcript captured"
            }
        }
    }

    /**
     * Toggle real-time transcription via AssemblyAI/Deepgram WebSocket
     * Shows live transcript overlay with streaming text
     */
    private fun toggleLiveTranscription() {
        if (isLiveTranscribing) {
            stopLiveTranscription()
        } else {
            startLiveTranscription()
        }
    }

    private fun startLiveTranscription() {
        // Check permission
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO)
            != PackageManager.PERMISSION_GRANTED
        ) {
            Toast.makeText(this, "Microphone permission required", Toast.LENGTH_SHORT).show()
            return
        }

        liveTranscriptBuffer.clear()

        // Create audio streaming service
        audioStreamingService = AudioStreamingService(this) { result ->
            runOnUiThread {
                // Check for voice command to stop transcription
                val lower = result.text.lowercase()
                if (result.isFinal && (lower.contains("stop transcri") ||
                    lower.contains("close") || lower.contains("stop recording"))) {
                    stopLiveTranscription()
                    hideLiveTranscriptionOverlay()
                    // Show the transcript without the stop command
                    val cleanTranscript = liveTranscriptBuffer.toString()
                        .replace(Regex("(?i)stop transcri\\w*"), "")
                        .replace(Regex("(?i)close"), "")
                        .replace(Regex("(?i)stop recording"), "")
                        .trim()
                    if (cleanTranscript.isNotEmpty()) {
                        showTranscriptionCompleteOverlay(cleanTranscript)
                    }
                    return@runOnUiThread
                }

                if (result.isFinal) {
                    // Final transcript - add to buffer
                    if (liveTranscriptBuffer.isNotEmpty()) {
                        liveTranscriptBuffer.append(" ")
                    }
                    liveTranscriptBuffer.append(result.text)
                    liveTranscriptText?.text = liveTranscriptBuffer.toString()
                } else {
                    // Interim result - show at end
                    val display = if (liveTranscriptBuffer.isEmpty()) {
                        result.text
                    } else {
                        "${liveTranscriptBuffer} ${result.text}"
                    }
                    liveTranscriptText?.text = display
                }
            }
        }

        audioStreamingService?.onConnected = { sessionId, provider ->
            runOnUiThread {
                statusText.text = "TRANSCRIBING ($provider)"
                Log.d(TAG, "Live transcription started: $sessionId via $provider")
            }
        }

        audioStreamingService?.onDisconnected = { fullTranscript ->
            runOnUiThread {
                Log.d(TAG, "Transcription ended, ${fullTranscript.length} chars")
                // Offer to generate note from transcript
                if (fullTranscript.isNotEmpty()) {
                    showTranscriptionCompleteOverlay(fullTranscript)
                }
            }
        }

        audioStreamingService?.onError = { message ->
            runOnUiThread {
                Toast.makeText(this, "Transcription error: $message", Toast.LENGTH_SHORT).show()
                statusText.text = "MDx Vision"
            }
        }

        // Show live transcription overlay
        showLiveTranscriptionOverlay()

        // Start streaming
        if (audioStreamingService?.startStreaming() == true) {
            isLiveTranscribing = true
        } else {
            hideLiveTranscriptionOverlay()
            Toast.makeText(this, "Failed to start transcription", Toast.LENGTH_SHORT).show()
        }
    }

    private fun stopLiveTranscription() {
        isLiveTranscribing = false
        audioStreamingService?.stopStreaming()
        statusText.text = "MDx Vision"
    }

    private fun showLiveTranscriptionOverlay() {
        dataOverlay?.let { (it.parent as? android.view.ViewGroup)?.removeView(it) }

        val rootView = window.decorView.findViewById<android.view.ViewGroup>(android.R.id.content)

        dataOverlay = android.widget.FrameLayout(this).apply {
            setBackgroundColor(0xEE0A1628.toInt())
            isClickable = true

            val innerLayout = android.widget.LinearLayout(context).apply {
                orientation = android.widget.LinearLayout.VERTICAL
                setPadding(32, 32, 32, 32)
                layoutParams = android.widget.FrameLayout.LayoutParams(
                    android.widget.FrameLayout.LayoutParams.MATCH_PARENT,
                    android.widget.FrameLayout.LayoutParams.MATCH_PARENT
                )
            }

            // Recording indicator
            val recordingIndicator = android.widget.LinearLayout(context).apply {
                orientation = android.widget.LinearLayout.HORIZONTAL
                setPadding(0, 0, 0, 16)

                val dot = TextView(context).apply {
                    text = "🔴"
                    textSize = 20f
                    setPadding(0, 0, 16, 0)
                }
                addView(dot)

                val title = TextView(context).apply {
                    text = "LIVE TRANSCRIPTION"
                    textSize = 20f
                    setTextColor(0xFFE11D48.toInt())
                }
                addView(title)
            }
            innerLayout.addView(recordingIndicator)

            // Scrollable transcript area
            val scrollView = android.widget.ScrollView(context).apply {
                layoutParams = android.widget.LinearLayout.LayoutParams(
                    android.widget.LinearLayout.LayoutParams.MATCH_PARENT, 0, 1f
                )
                setBackgroundColor(0xFF1E293B.toInt())
                setPadding(16, 16, 16, 16)
            }

            liveTranscriptText = TextView(context).apply {
                text = "Listening..."
                textSize = 18f
                setTextColor(0xFFF8FAFC.toInt())
                setLineSpacing(6f, 1.3f)
            }
            scrollView.addView(liveTranscriptText)
            innerLayout.addView(scrollView)

            // Stop button
            val stopButton = android.widget.Button(context).apply {
                text = "⏹ STOP TRANSCRIPTION"
                setBackgroundColor(0xFFE11D48.toInt())
                setTextColor(0xFFFFFFFF.toInt())
                textSize = 16f
                setPadding(32, 24, 32, 24)
                setOnClickListener {
                    stopLiveTranscription()
                    hideLiveTranscriptionOverlay()
                }
            }
            innerLayout.addView(stopButton)

            addView(innerLayout)
        }

        rootView.addView(dataOverlay)
        statusText.text = "Connecting..."
    }

    private fun hideLiveTranscriptionOverlay() {
        dataOverlay?.let { overlay ->
            (overlay.parent as? android.view.ViewGroup)?.removeView(overlay)
        }
        dataOverlay = null
        liveTranscriptText = null
    }

    private fun showTranscriptionCompleteOverlay(transcript: String) {
        hideLiveTranscriptionOverlay()

        val rootView = window.decorView.findViewById<android.view.ViewGroup>(android.R.id.content)

        dataOverlay = android.widget.FrameLayout(this).apply {
            setBackgroundColor(0xEE0A1628.toInt())
            isClickable = true

            val innerLayout = android.widget.LinearLayout(context).apply {
                orientation = android.widget.LinearLayout.VERTICAL
                setPadding(32, 32, 32, 32)
                layoutParams = android.widget.FrameLayout.LayoutParams(
                    android.widget.FrameLayout.LayoutParams.MATCH_PARENT,
                    android.widget.FrameLayout.LayoutParams.MATCH_PARENT
                )
            }

            val title = TextView(context).apply {
                text = "✓ TRANSCRIPTION COMPLETE"
                textSize = 20f
                setTextColor(0xFF10B981.toInt())
                setPadding(0, 0, 0, 16)
            }
            innerLayout.addView(title)

            val scrollView = android.widget.ScrollView(context).apply {
                layoutParams = android.widget.LinearLayout.LayoutParams(
                    android.widget.LinearLayout.LayoutParams.MATCH_PARENT, 0, 1f
                )
            }

            val contentText = TextView(context).apply {
                text = transcript
                textSize = 16f
                setTextColor(0xFFF8FAFC.toInt())
                setLineSpacing(4f, 1.2f)
            }
            scrollView.addView(contentText)
            innerLayout.addView(scrollView)

            // Button row
            val buttonRow = android.widget.LinearLayout(context).apply {
                orientation = android.widget.LinearLayout.HORIZONTAL
                setPadding(0, 16, 0, 0)
            }

            val generateNoteBtn = android.widget.Button(context).apply {
                text = "GENERATE NOTE"
                setBackgroundColor(0xFF10B981.toInt())
                setTextColor(0xFFFFFFFF.toInt())
                layoutParams = android.widget.LinearLayout.LayoutParams(0, android.widget.LinearLayout.LayoutParams.WRAP_CONTENT, 1f).apply {
                    marginEnd = 8
                }
                setOnClickListener {
                    hideDataOverlay()
                    generateClinicalNote(transcript)
                }
            }
            buttonRow.addView(generateNoteBtn)

            val closeBtn = android.widget.Button(context).apply {
                text = "CLOSE"
                setBackgroundColor(0xFF475569.toInt())
                setTextColor(0xFFFFFFFF.toInt())
                layoutParams = android.widget.LinearLayout.LayoutParams(0, android.widget.LinearLayout.LayoutParams.WRAP_CONTENT, 1f).apply {
                    marginStart = 8
                }
                setOnClickListener { hideDataOverlay() }
            }
            buttonRow.addView(closeBtn)

            innerLayout.addView(buttonRow)
            addView(innerLayout)
        }

        rootView.addView(dataOverlay)
        statusText.text = "MDx Vision"
    }

    private fun generateClinicalNote(transcript: String) {
        statusText.text = "Generating SOAP Note..."
        transcriptText.text = "Processing transcript"

        Thread {
            try {
                val json = JSONObject().apply {
                    put("transcript", transcript)
                    put("chief_complaint", "See transcript")
                }

                val request = Request.Builder()
                    .url("$EHR_PROXY_URL/api/v1/notes/quick")
                    .post(json.toString().toRequestBody("application/json".toMediaType()))
                    .build()

                httpClient.newCall(request).enqueue(object : Callback {
                    override fun onFailure(call: Call, e: IOException) {
                        Log.e(TAG, "Note generation error: ${e.message}")
                        runOnUiThread {
                            showDataOverlay("Note Generation Failed", "Error: ${e.message}")
                        }
                    }

                    override fun onResponse(call: Call, response: Response) {
                        val body = response.body?.string()
                        Log.d(TAG, "Generated note: $body")

                        runOnUiThread {
                            try {
                                val result = JSONObject(body ?: "{}")
                                // Store for later saving
                                lastGeneratedNote = result
                                lastNoteTranscript = transcript
                                val displayText = result.optString("display_text", "No note generated")
                                showNoteWithSaveOption("SOAP Note", displayText)
                            } catch (e: Exception) {
                                showDataOverlay("SOAP Note", body ?: "No response")
                            }
                        }
                    }
                })
            } catch (e: Exception) {
                Log.e(TAG, "Failed to generate note: ${e.message}")
                runOnUiThread {
                    showDataOverlay("Error", "Failed: ${e.message}")
                }
            }
        }.start()
    }

    private fun showNoteWithSaveOption(title: String, content: String) {
        // Remove existing overlay if any
        dataOverlay?.let { (it.parent as? android.view.ViewGroup)?.removeView(it) }

        val rootView = window.decorView.findViewById<android.view.ViewGroup>(android.R.id.content)

        dataOverlay = android.widget.FrameLayout(this).apply {
            setBackgroundColor(0xEE0A1628.toInt())
            isClickable = true

            val innerLayout = android.widget.LinearLayout(context).apply {
                orientation = android.widget.LinearLayout.VERTICAL
                setPadding(32, 32, 32, 32)
                layoutParams = android.widget.FrameLayout.LayoutParams(
                    android.widget.FrameLayout.LayoutParams.MATCH_PARENT,
                    android.widget.FrameLayout.LayoutParams.MATCH_PARENT
                )
            }

            // Title
            val titleText = TextView(context).apply {
                text = title
                textSize = 22f
                setTextColor(0xFF10B981.toInt())
                setPadding(0, 0, 0, 16)
            }
            innerLayout.addView(titleText)

            // Scrollable content
            val scrollView = android.widget.ScrollView(context).apply {
                layoutParams = android.widget.LinearLayout.LayoutParams(
                    android.widget.LinearLayout.LayoutParams.MATCH_PARENT, 0, 1f
                )
            }

            val contentText = TextView(context).apply {
                text = content
                textSize = 16f
                setTextColor(0xFFF8FAFC.toInt())
                setLineSpacing(4f, 1.2f)
            }
            scrollView.addView(contentText)
            innerLayout.addView(scrollView)

            // Button row with Save and Close
            val buttonRow = android.widget.LinearLayout(context).apply {
                orientation = android.widget.LinearLayout.HORIZONTAL
                setPadding(0, 16, 0, 0)
            }

            val saveButton = android.widget.Button(context).apply {
                text = "💾 SAVE NOTE"
                setBackgroundColor(0xFF22C55E.toInt())
                setTextColor(0xFFFFFFFF.toInt())
                layoutParams = android.widget.LinearLayout.LayoutParams(0, android.widget.LinearLayout.LayoutParams.WRAP_CONTENT, 1f).apply {
                    marginEnd = 8
                }
                setOnClickListener { saveCurrentNote() }
            }
            buttonRow.addView(saveButton)

            val closeButton = android.widget.Button(context).apply {
                text = "CLOSE"
                setBackgroundColor(0xFF475569.toInt())
                setTextColor(0xFFFFFFFF.toInt())
                layoutParams = android.widget.LinearLayout.LayoutParams(0, android.widget.LinearLayout.LayoutParams.WRAP_CONTENT, 1f).apply {
                    marginStart = 8
                }
                setOnClickListener { hideDataOverlay() }
            }
            buttonRow.addView(closeButton)

            innerLayout.addView(buttonRow)
            addView(innerLayout)
        }

        rootView.addView(dataOverlay)
        statusText.text = title
        transcriptText.text = "Say 'save note' or 'close'"
    }

    private fun saveCurrentNote() {
        val note = lastGeneratedNote
        val transcript = lastNoteTranscript
        val patientId = currentPatientData?.optString("patient_id")

        if (note == null) {
            Toast.makeText(this, "No note to save. Generate a note first.", Toast.LENGTH_SHORT).show()
            return
        }

        statusText.text = "Saving note..."
        transcriptText.text = "Uploading to EHR"

        Thread {
            try {
                val json = JSONObject().apply {
                    put("patient_id", patientId ?: TEST_PATIENT_ID)
                    put("note_type", "SOAP")
                    put("display_text", note.optString("display_text", ""))
                    put("summary", note.optString("summary", ""))
                    put("transcript", transcript ?: "")
                    put("timestamp", note.optString("timestamp", ""))
                }

                val request = Request.Builder()
                    .url("$EHR_PROXY_URL/api/v1/notes/save")
                    .post(json.toString().toRequestBody("application/json".toMediaType()))
                    .build()

                httpClient.newCall(request).enqueue(object : Callback {
                    override fun onFailure(call: Call, e: IOException) {
                        Log.e(TAG, "Save note error: ${e.message}")
                        runOnUiThread {
                            Toast.makeText(this@MainActivity, "Save failed: ${e.message}", Toast.LENGTH_SHORT).show()
                            statusText.text = "Save failed"
                        }
                    }

                    override fun onResponse(call: Call, response: Response) {
                        val body = response.body?.string()
                        Log.d(TAG, "Save response: $body")

                        runOnUiThread {
                            try {
                                val result = JSONObject(body ?: "{}")
                                val success = result.optBoolean("success", false)
                                val noteId = result.optString("note_id", "")

                                if (success) {
                                    Toast.makeText(this@MainActivity, "Note saved! ID: $noteId", Toast.LENGTH_LONG).show()
                                    statusText.text = "Note saved"
                                    transcriptText.text = "ID: $noteId"
                                    // Clear the saved note
                                    lastGeneratedNote = null
                                    lastNoteTranscript = null
                                    hideDataOverlay()
                                } else {
                                    val message = result.optString("message", "Save failed")
                                    Toast.makeText(this@MainActivity, message, Toast.LENGTH_SHORT).show()
                                    statusText.text = "MDx Vision"
                                }
                            } catch (e: Exception) {
                                Toast.makeText(this@MainActivity, "Save response error", Toast.LENGTH_SHORT).show()
                            }
                        }
                    }
                })
            } catch (e: Exception) {
                Log.e(TAG, "Failed to save note: ${e.message}")
                runOnUiThread {
                    Toast.makeText(this@MainActivity, "Save failed: ${e.message}", Toast.LENGTH_SHORT).show()
                }
            }
        }.start()
    }

    private fun fetchPatientByMrn(mrn: String) {
        statusText.text = "Looking up MRN..."
        transcriptText.text = "Scanning: $mrn"

        Thread {
            try {
                val encodedMrn = java.net.URLEncoder.encode(mrn, "UTF-8")
                val request = Request.Builder()
                    .url("$EHR_PROXY_URL/api/v1/patient/mrn/$encodedMrn")
                    .get()
                    .build()

                httpClient.newCall(request).enqueue(object : Callback {
                    override fun onFailure(call: Call, e: IOException) {
                        Log.e(TAG, "MRN lookup error: ${e.message}")
                        runOnUiThread {
                            showDataOverlay("Lookup Failed", "Error: ${e.message}")
                        }
                    }

                    override fun onResponse(call: Call, response: Response) {
                        val body = response.body?.string()
                        Log.d(TAG, "MRN lookup response: $body")

                        runOnUiThread {
                            if (response.code == 200) {
                                try {
                                    val patient = JSONObject(body ?: "{}")
                                    currentPatientData = patient

                                    // Cache by patient ID for offline access
                                    val patientId = patient.optString("patient_id", "")
                                    if (patientId.isNotEmpty()) {
                                        cachePatientData(patientId, body ?: "{}")
                                    }

                                    val name = patient.optString("name", "Unknown")
                                    val displayText = patient.optString("display_text", "No data")
                                    showDataOverlay("Patient: $name", displayText)
                                } catch (e: Exception) {
                                    showDataOverlay("Patient Found", body ?: "No response")
                                }
                            } else {
                                showDataOverlay("Not Found", "No patient with MRN: $mrn")
                            }
                        }
                    }
                })
            } catch (e: Exception) {
                Log.e(TAG, "MRN lookup failed: ${e.message}")
                runOnUiThread {
                    showDataOverlay("Error", "MRN lookup failed: ${e.message}")
                }
            }
        }.start()
    }

    // Store current patient data for section views
    private var currentPatientData: JSONObject? = null

    private fun fetchPatientData(patientId: String, forceOnline: Boolean = false) {
        // Check if offline - use cache
        if (!forceOnline && !isNetworkAvailable()) {
            val cached = getCachedPatient(patientId)
            if (cached != null) {
                currentPatientData = cached
                val name = cached.optString("name", "Unknown")
                val displayText = cached.optString("display_text", "No data")
                showDataOverlay("📴 OFFLINE: $name", displayText + "\n\n⚠️ Showing cached data")
                statusText.text = "Offline Mode"
                transcriptText.text = "Using cached data"
                return
            } else {
                statusText.text = "Offline - No cache"
                transcriptText.text = "Connect to network"
                Toast.makeText(this, "No cached data for this patient", Toast.LENGTH_SHORT).show()
                return
            }
        }

        statusText.text = "Loading patient..."
        transcriptText.text = "Connecting to EHR"

        Thread {
            try {
                val request = Request.Builder()
                    .url("$EHR_PROXY_URL/api/v1/patient/$patientId")
                    .get()
                    .build()

                httpClient.newCall(request).enqueue(object : Callback {
                    override fun onFailure(call: Call, e: IOException) {
                        Log.e(TAG, "EHR proxy error: ${e.message}")
                        runOnUiThread {
                            // Try to use cache on failure
                            val cached = getCachedPatient(patientId)
                            if (cached != null) {
                                currentPatientData = cached
                                val name = cached.optString("name", "Unknown")
                                val displayText = cached.optString("display_text", "No data")
                                showDataOverlay("📴 CACHED: $name", displayText + "\n\n⚠️ Network error - showing cached data")
                                statusText.text = "Using cache"
                                transcriptText.text = "Network unavailable"
                            } else {
                                statusText.text = "Connection failed"
                                transcriptText.text = "Error: ${e.message}"
                            }
                        }
                    }

                    override fun onResponse(call: Call, response: Response) {
                        val body = response.body?.string()
                        Log.d(TAG, "Patient data: $body")

                        runOnUiThread {
                            try {
                                val patient = JSONObject(body ?: "{}")
                                currentPatientData = patient

                                // Cache the patient data for offline use
                                cachePatientData(patientId, body ?: "{}")

                                val name = patient.optString("name", "Unknown")
                                val displayText = patient.optString("display_text", "No data")
                                showDataOverlay("Patient: $name", displayText)
                            } catch (e: Exception) {
                                showDataOverlay("Error", body ?: "No response")
                            }
                        }
                    }
                })
            } catch (e: Exception) {
                Log.e(TAG, "Failed to fetch patient: ${e.message}")
                runOnUiThread {
                    statusText.text = "Error"
                    transcriptText.text = e.message ?: "Unknown error"
                }
            }
        }.start()
    }

    private fun isVuzixDevice(): Boolean {
        val manufacturer = android.os.Build.MANUFACTURER.lowercase()
        val model = android.os.Build.MODEL.lowercase()
        return manufacturer.contains("vuzix") || model.contains("blade")
    }

    // ============ Offline Cache Methods ============

    private fun isNetworkAvailable(): Boolean {
        val connectivityManager = getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
        val network = connectivityManager.activeNetwork ?: return false
        val capabilities = connectivityManager.getNetworkCapabilities(network) ?: return false
        return capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
    }

    private fun cachePatientData(patientId: String, patientJson: String) {
        cachePrefs.edit().apply {
            putString("$CACHE_PREFIX$patientId", patientJson)
            putLong("$CACHE_PREFIX$patientId$CACHE_TIMESTAMP_SUFFIX", System.currentTimeMillis())
            apply()
        }
        Log.d(TAG, "Cached patient data: $patientId")
    }

    private fun getCachedPatient(patientId: String): JSONObject? {
        val cached = cachePrefs.getString("$CACHE_PREFIX$patientId", null) ?: return null
        val timestamp = cachePrefs.getLong("$CACHE_PREFIX$patientId$CACHE_TIMESTAMP_SUFFIX", 0)

        // Check if cache is expired
        if (System.currentTimeMillis() - timestamp > CACHE_MAX_AGE_MS) {
            Log.d(TAG, "Cache expired for patient: $patientId")
            return null
        }

        return try {
            JSONObject(cached)
        } catch (e: Exception) {
            Log.e(TAG, "Failed to parse cached patient: ${e.message}")
            null
        }
    }

    private fun getCachedPatientIds(): List<String> {
        return cachePrefs.all.keys
            .filter { it.startsWith(CACHE_PREFIX) && !it.endsWith(CACHE_TIMESTAMP_SUFFIX) }
            .map { it.removePrefix(CACHE_PREFIX) }
    }

    private fun clearCache() {
        cachePrefs.edit().clear().apply()
        Toast.makeText(this, "Patient cache cleared", Toast.LENGTH_SHORT).show()
        Log.d(TAG, "Cache cleared")
    }

    private fun checkPermissions() {
        val missingPermissions = requiredPermissions.filter {
            ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED
        }

        if (missingPermissions.isNotEmpty()) {
            ActivityCompat.requestPermissions(
                this,
                missingPermissions.toTypedArray(),
                PERMISSION_REQUEST_CODE
            )
        } else {
            initializeSpeechRecognizer()
        }
    }

    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)

        if (requestCode == PERMISSION_REQUEST_CODE) {
            if (grantResults.all { it == PackageManager.PERMISSION_GRANTED }) {
                initializeSpeechRecognizer()
            } else {
                Toast.makeText(this, "Permissions required for MDx Vision", Toast.LENGTH_LONG).show()
            }
        }
    }

    private fun initializeSpeechRecognizer() {
        if (SpeechRecognizer.isRecognitionAvailable(this)) {
            speechRecognizer = SpeechRecognizer.createSpeechRecognizer(this)
            speechRecognizer.setRecognitionListener(recognitionListener)
            Log.d(TAG, "Speech recognizer initialized")
            transcriptText.text = "Ready - Tap button or say command"
        } else {
            Log.e(TAG, "Speech recognition not available")
            transcriptText.text = "Speech recognition not available"
        }
    }

    private fun startVoiceRecognition() {
        val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
            putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1)
        }

        try {
            speechRecognizer.startListening(intent)
            statusText.text = "Listening..."
            Log.d(TAG, "Voice recognition started")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to start voice recognition: ${e.message}")
        }
    }

    private val recognitionListener = object : RecognitionListener {
        override fun onReadyForSpeech(params: Bundle?) {
            Log.d(TAG, "Ready for speech")
        }

        override fun onBeginningOfSpeech() {
            Log.d(TAG, "Beginning of speech")
        }

        override fun onRmsChanged(rmsdB: Float) {}

        override fun onBufferReceived(buffer: ByteArray?) {}

        override fun onEndOfSpeech() {
            Log.d(TAG, "End of speech")
            statusText.text = "Processing..."
        }

        override fun onError(error: Int) {
            val errorMessage = when (error) {
                SpeechRecognizer.ERROR_AUDIO -> "Audio error"
                SpeechRecognizer.ERROR_CLIENT -> "Client error"
                SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS -> "Insufficient permissions"
                SpeechRecognizer.ERROR_NETWORK -> "Network error"
                SpeechRecognizer.ERROR_NETWORK_TIMEOUT -> "Network timeout"
                SpeechRecognizer.ERROR_NO_MATCH -> "No speech detected"
                SpeechRecognizer.ERROR_RECOGNIZER_BUSY -> "Recognizer busy"
                SpeechRecognizer.ERROR_SERVER -> "Server error"
                SpeechRecognizer.ERROR_SPEECH_TIMEOUT -> "No speech detected"
                else -> "Unknown error"
            }
            Log.e(TAG, "Speech error: $errorMessage")

            // Continue listening in documentation or continuous mode
            if (isDocumentationMode) {
                statusText.text = "DOCUMENTING"
                transcriptText.text = "Listening..."
                transcriptText.postDelayed({ startVoiceRecognition() }, 1000)
            } else if (isContinuousListening) {
                statusText.text = "Hey MDx - Listening"
                transcriptText.text = "Say 'Hey MDx'..."
                transcriptText.postDelayed({ startVoiceRecognition() }, 1000)
            } else {
                statusText.text = "MDx Vision"
                // Reset to default message after 2 seconds
                transcriptText.text = errorMessage
                transcriptText.postDelayed({
                    transcriptText.text = "Tap or speak a command"
                }, 2000)
            }
        }

        override fun onResults(results: Bundle?) {
            val matches = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
            val transcript = matches?.firstOrNull() ?: ""

            Log.d(TAG, "Transcript: $transcript")
            val lower = transcript.lowercase()

            if (isContinuousListening) {
                // Check for wake word "Hey MDx"
                if (lower.contains(WAKE_WORD) || lower.contains("hey m d x") || lower.contains("a]mdx")) {
                    // Extract command after wake word
                    val wakeIndex = maxOf(
                        lower.indexOf(WAKE_WORD).let { if (it >= 0) it + WAKE_WORD.length else -1 },
                        lower.indexOf("hey m d x").let { if (it >= 0) it + 9 else -1 },
                        lower.indexOf("a]mdx").let { if (it >= 0) it + 5 else -1 }
                    )

                    if (wakeIndex > 0 && wakeIndex < transcript.length) {
                        // Command follows wake word
                        val command = transcript.substring(wakeIndex).trim()
                        statusText.text = "Command: $command"
                        transcriptText.text = "Processing..."
                        processTranscript(command)
                    } else {
                        // Just wake word, waiting for command
                        statusText.text = "Yes? Say command..."
                        awaitingCommand = true
                    }
                } else if (awaitingCommand) {
                    // Process as command (wake word was in previous phrase)
                    statusText.text = "MDx Vision"
                    transcriptText.text = "\"$transcript\""
                    processTranscript(transcript)
                    awaitingCommand = false
                } else {
                    // No wake word detected, keep listening
                    transcriptText.text = "Say 'Hey MDx'..."
                }

                // Continue listening in continuous mode
                transcriptText.postDelayed({
                    if (isContinuousListening) {
                        statusText.text = "Hey MDx - Listening"
                        startVoiceRecognition()
                    }
                }, 500)
            } else {
                // Normal mode - process transcript directly
                transcriptText.text = "\"$transcript\""
                statusText.text = "MDx Vision"
                processTranscript(transcript)
            }
        }

        override fun onPartialResults(partialResults: Bundle?) {
            val matches = partialResults?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
            val partial = matches?.firstOrNull() ?: ""
            transcriptText.text = "\"$partial\"..."
        }

        override fun onEvent(eventType: Int, params: Bundle?) {}
    }

    private fun processTranscript(transcript: String) {
        // If in documentation mode, collect transcripts
        if (isDocumentationMode) {
            documentationTranscripts.add(transcript)
            val count = documentationTranscripts.size
            transcriptText.text = "Recording... ($count segments)\nLatest: \"$transcript\""
            patientDataText.text = "Tap 'Start Note' to generate SOAP note"

            // Continue listening
            startVoiceRecognition()
            return
        }

        // Parse voice commands for patient lookup
        val lower = transcript.lowercase()

        when {
            lower.contains("patient") && lower.contains("load") -> {
                // Extract patient ID if mentioned
                val words = transcript.split(" ")
                val idIndex = words.indexOfFirst { it.all { c -> c.isDigit() } }
                val patientId = if (idIndex >= 0) words[idIndex] else TEST_PATIENT_ID
                fetchPatientData(patientId)
            }
            lower.contains("find") || lower.contains("search") -> {
                // Patient search by name
                val name = transcript.replace(Regex("(?i)(find|search|patient)"), "").trim()
                if (name.isNotEmpty()) {
                    searchPatients(name)
                }
            }
            lower.contains("start note") || lower.contains("start documentation") -> {
                // Voice command to start documentation
                if (!isDocumentationMode) toggleDocumentationMode()
            }
            lower.contains("stop note") || lower.contains("end note") || lower.contains("finish note") -> {
                // Voice command to stop documentation and generate note
                if (isDocumentationMode) toggleDocumentationMode()
            }
            lower.contains("save note") || lower.contains("save the note") || lower.contains("submit note") -> {
                // Voice command to save the current note
                saveCurrentNote()
            }
            lower.contains("live transcri") || lower.contains("start transcri") || lower.contains("transcribe") -> {
                // Voice command to start/stop live transcription
                toggleLiveTranscription()
            }
            lower.contains("stop transcri") -> {
                // Voice command to stop live transcription
                if (isLiveTranscribing) stopLiveTranscription()
            }
            lower.contains("scan") || lower.contains("wristband") -> {
                // Voice command to scan wristband
                startBarcodeScanner()
            }
            lower.contains("show vitals") || lower.contains("vitals") -> {
                // Show vitals only
                fetchPatientSection("vitals")
            }
            lower.contains("allergies") || lower.contains("allergy") -> {
                // Show allergies
                fetchPatientSection("allergies")
            }
            lower.contains("medication") || lower.contains("meds") || lower.contains("drugs") -> {
                // Show medications
                fetchPatientSection("medications")
            }
            lower.contains("labs") || lower.contains("laboratory") || lower.contains("results") -> {
                // Show lab results
                fetchPatientSection("labs")
            }
            lower.contains("procedure") || lower.contains("surgery") || lower.contains("operation") -> {
                // Show procedures
                fetchPatientSection("procedures")
            }
            lower.contains("immunization") || lower.contains("vaccine") || lower.contains("vaccination") || lower.contains("shot") -> {
                // Show immunizations
                fetchPatientSection("immunizations")
            }
            lower.contains("close") || lower.contains("dismiss") || lower.contains("back") -> {
                // Close any open overlay
                if (isLiveTranscribing) {
                    stopLiveTranscription()
                    hideLiveTranscriptionOverlay()
                }
                hideDataOverlay()
            }
            lower.contains("clear cache") || lower.contains("clear offline") -> {
                // Clear the offline cache
                clearCache()
                currentPatientData = null
                hideDataOverlay()
            }
            lower.contains("clear") || lower.contains("reset") -> {
                // Clear current patient data (not cache)
                currentPatientData = null
                hideDataOverlay()
                transcriptText.text = "Patient data cleared"
            }
            else -> {
                // Display transcribed text
                transcriptText.text = "\"$transcript\""
                Log.d(TAG, "Voice command: $transcript")
            }
        }
    }

    private fun fetchPatientSection(section: String) {
        // Use cached patient data if available
        currentPatientData?.let { patient ->
            val title = section.uppercase().replace("_", " ")
            val content = when (section) {
                "vitals" -> formatVitals(patient)
                "allergies" -> formatAllergies(patient)
                "medications" -> formatMedications(patient)
                "labs" -> formatLabs(patient)
                "procedures" -> formatProcedures(patient)
                "immunizations" -> formatImmunizations(patient)
                else -> patient.optString("display_text", "No data")
            }
            showDataOverlay(title, content)
            return
        }

        // If no cached data, fetch fresh
        statusText.text = "Loading ${section}..."
        transcriptText.text = "Fetching from EHR"

        Thread {
            try {
                val request = Request.Builder()
                    .url("$EHR_PROXY_URL/api/v1/patient/$TEST_PATIENT_ID")
                    .get()
                    .build()

                httpClient.newCall(request).enqueue(object : Callback {
                    override fun onFailure(call: Call, e: IOException) {
                        Log.e(TAG, "Fetch error: ${e.message}")
                        runOnUiThread {
                            statusText.text = "Failed to load"
                            transcriptText.text = "Error: ${e.message}"
                        }
                    }

                    override fun onResponse(call: Call, response: Response) {
                        val body = response.body?.string()
                        Log.d(TAG, "Patient data for $section: $body")

                        runOnUiThread {
                            try {
                                val patient = JSONObject(body ?: "{}")
                                currentPatientData = patient
                                val title = section.uppercase().replace("_", " ")
                                val content = when (section) {
                                    "vitals" -> formatVitals(patient)
                                    "allergies" -> formatAllergies(patient)
                                    "medications" -> formatMedications(patient)
                                    "labs" -> formatLabs(patient)
                                    "procedures" -> formatProcedures(patient)
                                    "immunizations" -> formatImmunizations(patient)
                                    else -> patient.optString("display_text", "No data")
                                }
                                showDataOverlay(title, content)
                            } catch (e: Exception) {
                                showDataOverlay("Error", "Parse error: ${e.message}")
                            }
                        }
                    }
                })
            } catch (e: Exception) {
                Log.e(TAG, "Failed to fetch $section: ${e.message}")
            }
        }.start()
    }

    private fun formatVitals(patient: JSONObject): String {
        val vitals = patient.optJSONArray("vitals") ?: return "No vitals recorded"
        val sb = StringBuilder("VITALS\n${"─".repeat(30)}\n")
        for (i in 0 until minOf(vitals.length(), 6)) {
            val v = vitals.getJSONObject(i)
            sb.append("• ${v.getString("name")}: ${v.getString("value")}${v.getString("unit")}\n")
        }
        return sb.toString()
    }

    private fun formatAllergies(patient: JSONObject): String {
        val allergies = patient.optJSONArray("allergies") ?: return "No allergies recorded"
        val sb = StringBuilder("⚠ ALLERGIES\n${"─".repeat(30)}\n")
        for (i in 0 until minOf(allergies.length(), 8)) {
            sb.append("• ${allergies.getString(i)}\n")
        }
        return sb.toString()
    }

    private fun formatMedications(patient: JSONObject): String {
        val meds = patient.optJSONArray("medications") ?: return "No medications recorded"
        val sb = StringBuilder("💊 MEDICATIONS\n${"─".repeat(30)}\n")
        for (i in 0 until minOf(meds.length(), 8)) {
            sb.append("• ${meds.getString(i)}\n")
        }
        return sb.toString()
    }

    private fun formatLabs(patient: JSONObject): String {
        val labs = patient.optJSONArray("labs") ?: return "No lab results"
        if (labs.length() == 0) return "No lab results available"
        val sb = StringBuilder("🔬 LAB RESULTS\n${"─".repeat(30)}\n")
        for (i in 0 until minOf(labs.length(), 8)) {
            val l = labs.getJSONObject(i)
            sb.append("• ${l.getString("name")}: ${l.getString("value")}${l.optString("unit", "")}\n")
        }
        return sb.toString()
    }

    private fun formatProcedures(patient: JSONObject): String {
        val procs = patient.optJSONArray("procedures") ?: return "No procedures recorded"
        if (procs.length() == 0) return "No procedures recorded"
        val sb = StringBuilder("🏥 PROCEDURES\n${"─".repeat(30)}\n")
        for (i in 0 until minOf(procs.length(), 8)) {
            val p = procs.getJSONObject(i)
            sb.append("• ${p.getString("name")}")
            val date = p.optString("date", "")
            if (date.isNotEmpty()) sb.append(" ($date)")
            sb.append("\n")
        }
        return sb.toString()
    }

    private fun formatImmunizations(patient: JSONObject): String {
        val imms = patient.optJSONArray("immunizations") ?: return "No immunizations recorded"
        if (imms.length() == 0) return "No immunizations recorded"
        val sb = StringBuilder("💉 IMMUNIZATIONS\n${"─".repeat(30)}\n")
        for (i in 0 until minOf(imms.length(), 10)) {
            val imm = imms.getJSONObject(i)
            sb.append("• ${imm.getString("name")}")
            val date = imm.optString("date", "")
            if (date.isNotEmpty()) sb.append(" ($date)")
            sb.append("\n")
        }
        return sb.toString()
    }

    private fun searchPatients(name: String) {
        statusText.text = "Searching..."
        patientDataText.text = ""

        Thread {
            try {
                val encodedName = java.net.URLEncoder.encode(name, "UTF-8")
                val request = Request.Builder()
                    .url("$EHR_PROXY_URL/api/v1/patient/search?name=$encodedName")
                    .get()
                    .build()

                httpClient.newCall(request).enqueue(object : Callback {
                    override fun onFailure(call: Call, e: IOException) {
                        Log.e(TAG, "Search error: ${e.message}")
                        runOnUiThread {
                            statusText.text = "Search failed"
                            patientDataText.text = "Error: ${e.message}"
                        }
                    }

                    override fun onResponse(call: Call, response: Response) {
                        val body = response.body?.string()
                        Log.d(TAG, "Search results: $body")

                        runOnUiThread {
                            statusText.text = "Search Results"
                            try {
                                val results = org.json.JSONArray(body ?: "[]")
                                val sb = StringBuilder()
                                for (i in 0 until minOf(results.length(), 5)) {
                                    val p = results.getJSONObject(i)
                                    sb.append("${p.getString("name")} (${p.getString("patient_id")})\n")
                                }
                                patientDataText.text = if (sb.isEmpty()) "No results" else sb.toString()
                            } catch (e: Exception) {
                                patientDataText.text = body ?: "No results"
                            }
                        }
                    }
                })
            } catch (e: Exception) {
                Log.e(TAG, "Search failed: ${e.message}")
            }
        }.start()
    }

    override fun onDestroy() {
        super.onDestroy()
        if (::speechRecognizer.isInitialized) {
            speechRecognizer.destroy()
        }
        // Clean up audio streaming service
        audioStreamingService?.destroy()
    }
}
