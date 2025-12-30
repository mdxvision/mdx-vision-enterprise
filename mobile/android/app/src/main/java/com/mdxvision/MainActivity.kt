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
import android.speech.tts.TextToSpeech
import java.util.Locale
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
        // Font size settings
        private const val PREF_FONT_SIZE = "font_size_level"
        private const val FONT_SIZE_SMALL = 0
        private const val FONT_SIZE_MEDIUM = 1
        private const val FONT_SIZE_LARGE = 2
        private const val FONT_SIZE_EXTRA_LARGE = 3
        // Clinician name setting
        private const val PREF_CLINICIAN_NAME = "clinician_name"
        private const val DEFAULT_CLINICIAN_NAME = "Clinician"
        // Speech feedback setting
        private const val PREF_SPEECH_FEEDBACK = "speech_feedback_enabled"
        // Offline note drafts
        private const val DRAFT_PREFIX = "note_draft_"
        private const val DRAFT_IDS_KEY = "pending_draft_ids"
        private const val MAX_SYNC_ATTEMPTS = 5
        // Patient history
        private const val HISTORY_KEY = "patient_history"
        private const val MAX_HISTORY_SIZE = 10
        // Session timeout (HIPAA compliance)
        private const val PREF_SESSION_TIMEOUT = "session_timeout_minutes"
        private const val DEFAULT_SESSION_TIMEOUT_MINUTES = 5
        private const val SESSION_CHECK_INTERVAL_MS = 30_000L // Check every 30 seconds
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

    // Pending transcript for preview (before note generation)
    private var pendingTranscript: String? = null

    // Editable note content (for edit before save)
    private var editableNoteContent: String? = null
    private var noteEditText: android.widget.EditText? = null
    private var isNoteEditing: Boolean = false

    // Font size for accessibility
    private var currentFontSizeLevel: Int = FONT_SIZE_MEDIUM

    // Auto-scroll for live transcription
    private var isAutoScrollEnabled: Boolean = true
    private var liveTranscriptScrollView: android.widget.ScrollView? = null

    // Offline note drafts
    private var networkCallback: ConnectivityManager.NetworkCallback? = null
    private var isSyncing = false

    // Note type for clinical documentation (SOAP, PROGRESS, HP, CONSULT, AUTO)
    private var currentNoteType: String = "AUTO"  // Default to auto-detect

    // Clinician name for speaker context (can be configured in settings)
    private var clinicianName: String = "Clinician"  // Default name, update from settings/login

    // Text-to-Speech for spoken patient summaries (hands-free while walking)
    private var textToSpeech: TextToSpeech? = null
    private var isTtsReady: Boolean = false
    private var isSpeechFeedbackEnabled: Boolean = true  // Audible confirmations for actions

    // Session timeout for HIPAA compliance
    private var lastActivityTime: Long = System.currentTimeMillis()
    private var isSessionLocked: Boolean = false
    private var sessionTimeoutMinutes: Int = DEFAULT_SESSION_TIMEOUT_MINUTES
    private var sessionCheckHandler: android.os.Handler? = null
    private var sessionCheckRunnable: Runnable? = null
    private var lockScreenOverlay: android.widget.FrameLayout? = null

    // Voice note editing - edit history for undo functionality
    private val editHistory = mutableListOf<String>()
    private val MAX_EDIT_HISTORY = 10

    // Section aliases for voice commands (maps spoken words to canonical section names)
    private val sectionAliases = mapOf(
        "subjective" to listOf("subjective", "chief complaint", "chief", "cc", "hpi", "history"),
        "objective" to listOf("objective", "exam", "physical", "vitals", "physical exam"),
        "assessment" to listOf("assessment", "diagnosis", "impression", "dx", "diagnoses"),
        "plan" to listOf("plan", "treatment", "recommendations", "rx", "orders")
    )

    // Macro templates for quick insertion
    private val macroTemplates = mapOf(
        "normal_exam" to """General: Alert, oriented, no acute distress
HEENT: Normocephalic, PERRL, oropharynx clear
Neck: Supple, no lymphadenopathy
Lungs: Clear to auscultation bilaterally
Heart: Regular rate and rhythm, no murmurs
Abdomen: Soft, non-tender, non-distended
Extremities: No edema, pulses intact
Neuro: Grossly intact""",
        "normal_vitals" to "Vital signs within normal limits",
        "negative_ros" to "Review of systems negative except as noted in HPI",
        "follow_up" to "Follow up in 2 weeks, or sooner if symptoms worsen. Return to ED for fever >101, difficulty breathing, or worsening symptoms.",
        "diabetes_followup" to "Continue current diabetes regimen. Check A1C in 3 months. Continue dietary modifications. Return for routine follow-up.",
        "hypertension_followup" to "Continue current antihypertensive medications. Monitor blood pressure at home. Low sodium diet. Return in 1 month for BP check."
    )

    // Voice navigation - track current active scroll view for scroll commands
    private var currentScrollView: android.widget.ScrollView? = null
    private var currentContentText: TextView? = null  // For read-back

    // Voice dictation mode - direct speech-to-text into note sections
    private var isDictationMode: Boolean = false
    private var dictationTargetSection: String? = null  // Which section to dictate into
    private var dictationBuffer: StringBuilder = StringBuilder()  // Accumulates dictated text

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

        // Initialize offline cache and settings
        cachePrefs = getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        loadFontSizeSetting()
        loadClinicianName()
        loadSpeechFeedbackSetting()
        loadSessionTimeoutSetting()

        // Start session timeout checker for HIPAA compliance
        startSessionTimeoutChecker()

        // Register network callback for auto-sync of offline drafts
        registerNetworkCallback()

        // Check for pending drafts on startup
        val draftCount = getPendingDraftCount()
        if (draftCount > 0) {
            Log.d(TAG, "Found $draftCount pending draft(s) on startup")
        }

        // Initialize Text-to-Speech for hands-free patient summaries
        initTextToSpeech()

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
                textSize = getTitleFontSize()
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
                textSize = getContentFontSize()
                setTextColor(0xFFF8FAFC.toInt())
                setLineSpacing(4f, 1.2f)
            }
            scrollView.addView(contentText)
            innerLayout.addView(scrollView)

            // Track for voice navigation
            currentScrollView = scrollView
            currentContentText = contentText

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
        transcriptText.text = "Say 'close' or navigate with 'scroll up/down'"
    }

    /**
     * Show patient data overlay with photo
     * Displays patient photo (or initials) at the top, followed by patient data
     */
    private fun showPatientDataOverlay(patient: JSONObject) {
        val name = patient.optString("name", "Unknown")
        val displayText = patient.optString("display_text", "No data")
        val photoUrl = patient.optString("photo_url", "")

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

            // Header with photo and name
            val headerLayout = android.widget.LinearLayout(context).apply {
                orientation = android.widget.LinearLayout.HORIZONTAL
                setPadding(0, 0, 0, 16)
                gravity = android.view.Gravity.CENTER_VERTICAL
            }

            // Patient photo or initials placeholder
            val photoSize = 64
            val photoView = android.widget.ImageView(context).apply {
                layoutParams = android.widget.LinearLayout.LayoutParams(photoSize, photoSize).apply {
                    marginEnd = 16
                }
                scaleType = android.widget.ImageView.ScaleType.CENTER_CROP

                // Make it circular with a background
                background = android.graphics.drawable.GradientDrawable().apply {
                    shape = android.graphics.drawable.GradientDrawable.OVAL
                    setColor(0xFF374151.toInt())
                }
                clipToOutline = true
                outlineProvider = object : android.view.ViewOutlineProvider() {
                    override fun getOutline(view: android.view.View, outline: android.graphics.Outline) {
                        outline.setOval(0, 0, view.width, view.height)
                    }
                }
            }

            // Load photo or show initials
            if (photoUrl.isNotEmpty()) {
                loadPatientPhoto(photoView, photoUrl)
            } else {
                // Show initials placeholder
                showInitialsPlaceholder(photoView, name, photoSize)
            }
            headerLayout.addView(photoView)

            // Patient name
            val nameText = TextView(context).apply {
                text = "Patient: $name"
                textSize = getTitleFontSize()
                setTextColor(0xFF10B981.toInt())
            }
            headerLayout.addView(nameText)

            innerLayout.addView(headerLayout)

            // Scrollable content
            val scrollView = android.widget.ScrollView(context).apply {
                layoutParams = android.widget.LinearLayout.LayoutParams(
                    android.widget.LinearLayout.LayoutParams.MATCH_PARENT, 0, 1f
                )
            }

            val contentText = TextView(context).apply {
                text = displayText
                textSize = getContentFontSize()
                setTextColor(0xFFF8FAFC.toInt())
                setLineSpacing(4f, 1.2f)
            }
            scrollView.addView(contentText)
            innerLayout.addView(scrollView)

            // Track for voice navigation
            currentScrollView = scrollView
            currentContentText = contentText

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
        statusText.text = "Patient: $name"
        transcriptText.text = "Say 'close' or navigate with 'scroll up/down'"
    }

    /**
     * Load patient photo from URL or base64 data URI
     */
    private fun loadPatientPhoto(imageView: android.widget.ImageView, photoUrl: String) {
        try {
            if (photoUrl.startsWith("data:")) {
                // Base64 data URI
                val base64Data = photoUrl.substringAfter("base64,")
                val imageBytes = android.util.Base64.decode(base64Data, android.util.Base64.DEFAULT)
                val bitmap = android.graphics.BitmapFactory.decodeByteArray(imageBytes, 0, imageBytes.size)
                imageView.setImageBitmap(bitmap)
            } else {
                // URL - load asynchronously
                Thread {
                    try {
                        val url = java.net.URL(photoUrl)
                        val connection = url.openConnection() as java.net.HttpURLConnection
                        connection.doInput = true
                        connection.connect()
                        val input = connection.inputStream
                        val bitmap = android.graphics.BitmapFactory.decodeStream(input)
                        runOnUiThread {
                            imageView.setImageBitmap(bitmap)
                        }
                    } catch (e: Exception) {
                        Log.e(TAG, "Failed to load patient photo: ${e.message}")
                    }
                }.start()
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error processing patient photo: ${e.message}")
        }
    }

    /**
     * Show initials placeholder when no photo is available
     */
    private fun showInitialsPlaceholder(imageView: android.widget.ImageView, name: String, size: Int) {
        // Extract initials (first letter of first and last name)
        val parts = name.split(" ", ",").filter { it.isNotBlank() }
        val initials = when {
            parts.size >= 2 -> "${parts[0].first()}${parts[1].first()}"
            parts.isNotEmpty() -> parts[0].take(2)
            else -> "?"
        }.uppercase()

        // Create a bitmap with initials
        val bitmap = android.graphics.Bitmap.createBitmap(size, size, android.graphics.Bitmap.Config.ARGB_8888)
        val canvas = android.graphics.Canvas(bitmap)

        // Draw circle background
        val bgPaint = android.graphics.Paint().apply {
            color = 0xFF6366F1.toInt()  // Indigo color
            isAntiAlias = true
        }
        canvas.drawCircle(size / 2f, size / 2f, size / 2f, bgPaint)

        // Draw initials
        val textPaint = android.graphics.Paint().apply {
            color = 0xFFFFFFFF.toInt()
            textSize = size * 0.4f
            textAlign = android.graphics.Paint.Align.CENTER
            isAntiAlias = true
            typeface = android.graphics.Typeface.DEFAULT_BOLD
        }
        val textY = size / 2f - (textPaint.descent() + textPaint.ascent()) / 2
        canvas.drawText(initials, size / 2f, textY, textPaint)

        imageView.setImageBitmap(bitmap)
    }

    private fun hideDataOverlay() {
        dataOverlay?.let { overlay ->
            (overlay.parent as? android.view.ViewGroup)?.removeView(overlay)
            dataOverlay = null
        }
        // Clear voice navigation tracking
        currentScrollView = null
        currentContentText = null
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
                    // Final transcript - add to buffer with speaker label if available
                    if (liveTranscriptBuffer.isNotEmpty()) {
                        liveTranscriptBuffer.append("\n")
                    }
                    // Add speaker label if present and different from last
                    val speakerPrefix = if (result.speaker != null) {
                        "[${result.speaker}]: "
                    } else ""
                    liveTranscriptBuffer.append(speakerPrefix).append(result.text)
                    liveTranscriptText?.text = liveTranscriptBuffer.toString()
                } else {
                    // Interim result - show at end with speaker
                    val speakerPrefix = if (result.speaker != null) "[${result.speaker}]: " else ""
                    val display = if (liveTranscriptBuffer.isEmpty()) {
                        speakerPrefix + result.text
                    } else {
                        "${liveTranscriptBuffer}\n$speakerPrefix${result.text}"
                    }
                    liveTranscriptText?.text = display
                }

                // Auto-scroll to bottom if enabled
                if (isAutoScrollEnabled) {
                    liveTranscriptScrollView?.post {
                        liveTranscriptScrollView?.fullScroll(android.view.View.FOCUS_DOWN)
                    }
                }
            }
        }

        audioStreamingService?.onConnected = { sessionId, provider ->
            runOnUiThread {
                statusText.text = "TRANSCRIBING ($provider)"
                Log.d(TAG, "Live transcription started: $sessionId via $provider")
                speakFeedback("Recording started")
            }
        }

        audioStreamingService?.onDisconnected = { fullTranscript ->
            runOnUiThread {
                Log.d(TAG, "Transcription ended, ${fullTranscript.length} chars")
                speakFeedback("Recording stopped")
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
                speakFeedback("Transcription error")
            }
        }

        // Show live transcription overlay
        showLiveTranscriptionOverlay()

        // Build speaker context from loaded patient and clinician
        val patientName = currentPatientData?.optString("name")?.takeIf { it.isNotEmpty() }
        val speakerContext = AudioStreamingService.SpeakerContext(
            clinician = clinicianName,
            patient = patientName
        )

        // Start streaming with speaker context
        if (audioStreamingService?.startStreaming(speakerContext = speakerContext) == true) {
            isLiveTranscribing = true
            if (patientName != null) {
                Log.d(TAG, "Speaker context: clinician=$clinicianName, patient=$patientName")
            }
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
            liveTranscriptScrollView = android.widget.ScrollView(context).apply {
                layoutParams = android.widget.LinearLayout.LayoutParams(
                    android.widget.LinearLayout.LayoutParams.MATCH_PARENT, 0, 1f
                )
                setBackgroundColor(0xFF1E293B.toInt())
                setPadding(16, 16, 16, 16)
            }

            liveTranscriptText = TextView(context).apply {
                text = "Listening..."
                textSize = getContentFontSize() + 2f  // Slightly larger for transcription
                setTextColor(0xFFF8FAFC.toInt())
                setLineSpacing(6f, 1.3f)
            }
            liveTranscriptScrollView?.addView(liveTranscriptText)
            innerLayout.addView(liveTranscriptScrollView)

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
        liveTranscriptScrollView = null
    }

    private fun showTranscriptionCompleteOverlay(transcript: String) {
        hideLiveTranscriptionOverlay()

        // Store for voice command access
        pendingTranscript = transcript

        // Analyze the transcript for preview
        val analysis = analyzeTranscript(transcript)

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
            val title = TextView(context).apply {
                text = "📋 TRANSCRIPT PREVIEW"
                textSize = getTitleFontSize()
                setTextColor(0xFF10B981.toInt())
                setPadding(0, 0, 0, 8)
            }
            innerLayout.addView(title)

            // Stats row
            val statsText = TextView(context).apply {
                text = "📊 ${analysis.wordCount} words • ~${analysis.estimatedMinutes} min • ${getNoteTypeDisplayName()}"
                textSize = getContentFontSize() - 2f
                setTextColor(0xFF94A3B8.toInt())
                setPadding(0, 0, 0, 12)
            }
            innerLayout.addView(statsText)

            // Detected topics (if any)
            if (analysis.detectedTopics.isNotEmpty()) {
                val topicsLayout = android.widget.LinearLayout(context).apply {
                    orientation = android.widget.LinearLayout.VERTICAL
                    setBackgroundColor(0xFF1E293B.toInt())
                    setPadding(16, 12, 16, 12)
                    val params = android.widget.LinearLayout.LayoutParams(
                        android.widget.LinearLayout.LayoutParams.MATCH_PARENT,
                        android.widget.LinearLayout.LayoutParams.WRAP_CONTENT
                    )
                    params.bottomMargin = 12
                    layoutParams = params
                }

                val topicsTitle = TextView(context).apply {
                    text = "🔍 Key Topics Detected:"
                    textSize = getContentFontSize() - 1f
                    setTextColor(0xFF60A5FA.toInt())
                    setPadding(0, 0, 0, 4)
                }
                topicsLayout.addView(topicsTitle)

                val topicsList = TextView(context).apply {
                    text = analysis.detectedTopics.joinToString(" • ")
                    textSize = getContentFontSize() - 2f
                    setTextColor(0xFFE2E8F0.toInt())
                }
                topicsLayout.addView(topicsList)

                innerLayout.addView(topicsLayout)
            }

            // Transcript preview label
            val previewLabel = TextView(context).apply {
                text = "📝 Transcript:"
                textSize = getContentFontSize() - 1f
                setTextColor(0xFF94A3B8.toInt())
                setPadding(0, 0, 0, 4)
            }
            innerLayout.addView(previewLabel)

            // Scrollable transcript
            val scrollView = android.widget.ScrollView(context).apply {
                layoutParams = android.widget.LinearLayout.LayoutParams(
                    android.widget.LinearLayout.LayoutParams.MATCH_PARENT, 0, 1f
                )
                setBackgroundColor(0xFF1E293B.toInt())
                setPadding(12, 12, 12, 12)
            }

            val contentText = TextView(context).apply {
                text = transcript
                textSize = getContentFontSize()
                setTextColor(0xFFF8FAFC.toInt())
                setLineSpacing(4f, 1.2f)
            }
            scrollView.addView(contentText)
            innerLayout.addView(scrollView)

            // Hint text
            val hintText = TextView(context).apply {
                text = "💡 Say \"generate note\", \"re-record\", or \"close\""
                textSize = getContentFontSize() - 3f
                setTextColor(0xFF64748B.toInt())
                setPadding(0, 8, 0, 8)
                gravity = android.view.Gravity.CENTER
            }
            innerLayout.addView(hintText)

            // Button row
            val buttonRow = android.widget.LinearLayout(context).apply {
                orientation = android.widget.LinearLayout.HORIZONTAL
                setPadding(0, 8, 0, 0)
            }

            val generateNoteBtn = android.widget.Button(context).apply {
                text = "✓ GENERATE"
                setBackgroundColor(0xFF10B981.toInt())
                setTextColor(0xFFFFFFFF.toInt())
                textSize = 14f
                layoutParams = android.widget.LinearLayout.LayoutParams(0, android.widget.LinearLayout.LayoutParams.WRAP_CONTENT, 1f).apply {
                    marginEnd = 4
                }
                setOnClickListener {
                    hideDataOverlay()
                    generateClinicalNote(transcript)
                }
            }
            buttonRow.addView(generateNoteBtn)

            val reRecordBtn = android.widget.Button(context).apply {
                text = "🔄 RE-RECORD"
                setBackgroundColor(0xFFF59E0B.toInt())
                setTextColor(0xFFFFFFFF.toInt())
                textSize = 14f
                layoutParams = android.widget.LinearLayout.LayoutParams(0, android.widget.LinearLayout.LayoutParams.WRAP_CONTENT, 1f).apply {
                    marginStart = 4
                    marginEnd = 4
                }
                setOnClickListener {
                    hideDataOverlay()
                    toggleLiveTranscription() // Start new transcription
                }
            }
            buttonRow.addView(reRecordBtn)

            val closeBtn = android.widget.Button(context).apply {
                text = "✕ CLOSE"
                setBackgroundColor(0xFF475569.toInt())
                setTextColor(0xFFFFFFFF.toInt())
                textSize = 14f
                layoutParams = android.widget.LinearLayout.LayoutParams(0, android.widget.LinearLayout.LayoutParams.WRAP_CONTENT, 1f).apply {
                    marginStart = 4
                }
                setOnClickListener { hideDataOverlay() }
            }
            buttonRow.addView(closeBtn)

            innerLayout.addView(buttonRow)
            addView(innerLayout)
        }

        rootView.addView(dataOverlay)
        statusText.text = "Review Transcript"
        transcriptText.text = "${analysis.wordCount} words captured"
    }

    /**
     * Analyze transcript to extract useful preview information
     */
    private data class TranscriptAnalysis(
        val wordCount: Int,
        val estimatedMinutes: Int,
        val detectedTopics: List<String>
    )

    private fun analyzeTranscript(transcript: String): TranscriptAnalysis {
        val words = transcript.split(Regex("\\s+")).filter { it.isNotBlank() }
        val wordCount = words.size
        // Average speaking rate is ~150 words per minute
        val estimatedMinutes = maxOf(1, (wordCount / 150.0).toInt())

        // Detect medical topics from transcript
        val topics = mutableListOf<String>()
        val lower = transcript.lowercase()

        // Symptoms & complaints
        if (lower.contains("pain") || lower.contains("hurt") || lower.contains("ache")) topics.add("Pain")
        if (lower.contains("headache") || lower.contains("migraine")) topics.add("Headache")
        if (lower.contains("fever") || lower.contains("temperature")) topics.add("Fever")
        if (lower.contains("cough") || lower.contains("cold") || lower.contains("congestion")) topics.add("Respiratory")
        if (lower.contains("nausea") || lower.contains("vomit") || lower.contains("diarrhea")) topics.add("GI symptoms")
        if (lower.contains("dizzy") || lower.contains("vertigo") || lower.contains("lightheaded")) topics.add("Dizziness")
        if (lower.contains("fatigue") || lower.contains("tired") || lower.contains("weak")) topics.add("Fatigue")
        if (lower.contains("rash") || lower.contains("itch") || lower.contains("skin")) topics.add("Skin")
        if (lower.contains("chest pain") || lower.contains("palpitation") || lower.contains("shortness of breath")) topics.add("Cardiac")
        if (lower.contains("anxiety") || lower.contains("depress") || lower.contains("stress")) topics.add("Mental health")

        // Conditions
        if (lower.contains("diabetes") || lower.contains("blood sugar") || lower.contains("glucose")) topics.add("Diabetes")
        if (lower.contains("hypertension") || lower.contains("blood pressure") || lower.contains("bp")) topics.add("Hypertension")
        if (lower.contains("asthma") || lower.contains("inhaler") || lower.contains("wheez")) topics.add("Asthma")

        // Procedures/actions
        if (lower.contains("exam") || lower.contains("physical")) topics.add("Physical exam")
        if (lower.contains("lab") || lower.contains("blood test") || lower.contains("bloodwork")) topics.add("Lab work")
        if (lower.contains("x-ray") || lower.contains("ct scan") || lower.contains("mri") || lower.contains("imaging")) topics.add("Imaging")
        if (lower.contains("prescri") || lower.contains("medication") || lower.contains("refill")) topics.add("Prescription")
        if (lower.contains("follow up") || lower.contains("follow-up") || lower.contains("return visit")) topics.add("Follow-up")

        return TranscriptAnalysis(
            wordCount = wordCount,
            estimatedMinutes = estimatedMinutes,
            detectedTopics = topics.take(5) // Limit to top 5 topics
        )
    }

    private fun generateClinicalNote(transcript: String) {
        val noteTypeDisplay = getNoteTypeDisplayName()
        statusText.text = "Generating $noteTypeDisplay..."
        transcriptText.text = "Processing transcript"

        Thread {
            try {
                val json = JSONObject().apply {
                    put("transcript", transcript)
                    put("chief_complaint", "See transcript")
                    put("note_type", currentNoteType)
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

                                var displayText = result.optString("display_text", "No note generated")

                                // Check if note type was auto-detected
                                if (result.optBoolean("auto_detected", false)) {
                                    val detectedType = result.optString("note_type", "SOAP")
                                    val confidence = result.optInt("detection_confidence", 0)
                                    val reason = result.optString("detection_reason", "")
                                    val detectedName = getDisplayNameForType(detectedType)

                                    // Prepend auto-detection info
                                    displayText = "🤖 Auto-detected: $detectedName ($confidence% confidence)\n" +
                                            "Reason: $reason\n" +
                                            "─".repeat(25) + "\n\n" +
                                            displayText

                                    showNoteWithSaveOption("$detectedName (Auto)", displayText)
                                    speakFeedback("$detectedName generated")
                                } else {
                                    showNoteWithSaveOption(noteTypeDisplay, displayText)
                                    speakFeedback("$noteTypeDisplay generated")
                                }
                            } catch (e: Exception) {
                                showDataOverlay(noteTypeDisplay, body ?: "No response")
                                speakFeedback("Error generating note")
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

    private fun getNoteTypeDisplayName(): String {
        return when (currentNoteType.uppercase()) {
            "SOAP" -> "SOAP Note"
            "PROGRESS" -> "Progress Note"
            "HP" -> "H&P Note"
            "CONSULT" -> "Consult Note"
            "AUTO" -> "Auto-Detect Note"
            else -> "Clinical Note"
        }
    }

    private fun getDisplayNameForType(noteType: String): String {
        return when (noteType.uppercase()) {
            "SOAP" -> "SOAP Note"
            "PROGRESS" -> "Progress Note"
            "HP" -> "H&P Note"
            "CONSULT" -> "Consult Note"
            else -> "Clinical Note"
        }
    }

    private fun setNoteType(noteType: String) {
        currentNoteType = noteType.uppercase()
        val displayName = getNoteTypeDisplayName()
        Toast.makeText(this, "Note type: $displayName", Toast.LENGTH_SHORT).show()
        transcriptText.text = "Note type: $displayName"
        Log.d(TAG, "Note type set to $currentNoteType")
    }

    private fun showNoteWithSaveOption(title: String, content: String) {
        // Remove existing overlay if any
        dataOverlay?.let { (it.parent as? android.view.ViewGroup)?.removeView(it) }

        // Store original content for editing
        editableNoteContent = content
        isNoteEditing = false

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

            // Title row with edit indicator
            val titleRow = android.widget.LinearLayout(context).apply {
                orientation = android.widget.LinearLayout.HORIZONTAL
                setPadding(0, 0, 0, 16)
            }

            val titleText = TextView(context).apply {
                text = title
                textSize = getTitleFontSize()
                setTextColor(0xFF10B981.toInt())
                layoutParams = android.widget.LinearLayout.LayoutParams(0, android.widget.LinearLayout.LayoutParams.WRAP_CONTENT, 1f)
            }
            titleRow.addView(titleText)

            // Edit mode indicator
            val editIndicator = TextView(context).apply {
                text = "📝 EDITABLE"
                textSize = 14f
                setTextColor(0xFF3B82F6.toInt())
            }
            titleRow.addView(editIndicator)
            innerLayout.addView(titleRow)

            // Hint text for editing
            val hintText = TextView(context).apply {
                text = "Tap note to edit before saving"
                textSize = 12f
                setTextColor(0xFF94A3B8.toInt())
                setPadding(0, 0, 0, 8)
            }
            innerLayout.addView(hintText)

            // Scrollable editable content
            val scrollView = android.widget.ScrollView(context).apply {
                layoutParams = android.widget.LinearLayout.LayoutParams(
                    android.widget.LinearLayout.LayoutParams.MATCH_PARENT, 0, 1f
                )
                setBackgroundColor(0xFF1E293B.toInt())
            }

            // EditText for editable note content
            noteEditText = android.widget.EditText(context).apply {
                setText(content)
                textSize = getContentFontSize()
                setTextColor(0xFFF8FAFC.toInt())
                setHintTextColor(0xFF64748B.toInt())
                setLineSpacing(4f, 1.2f)
                setBackgroundColor(0x00000000) // Transparent background
                setPadding(16, 16, 16, 16)
                gravity = android.view.Gravity.TOP or android.view.Gravity.START
                inputType = android.text.InputType.TYPE_CLASS_TEXT or
                        android.text.InputType.TYPE_TEXT_FLAG_MULTI_LINE or
                        android.text.InputType.TYPE_TEXT_FLAG_NO_SUGGESTIONS
                isSingleLine = false
                minLines = 10

                // Track when user edits
                addTextChangedListener(object : android.text.TextWatcher {
                    override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
                    override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {
                        isNoteEditing = true
                        editableNoteContent = s?.toString()
                    }
                    override fun afterTextChanged(s: android.text.Editable?) {}
                })
            }
            scrollView.addView(noteEditText)
            innerLayout.addView(scrollView)

            // Track for voice navigation
            currentScrollView = scrollView

            // Button row with Edit actions, Save, and Close
            val buttonRow = android.widget.LinearLayout(context).apply {
                orientation = android.widget.LinearLayout.HORIZONTAL
                setPadding(0, 16, 0, 0)
            }

            // Reset button (restore original)
            val resetButton = android.widget.Button(context).apply {
                text = "↩ RESET"
                setBackgroundColor(0xFF6366F1.toInt())
                setTextColor(0xFFFFFFFF.toInt())
                textSize = 14f
                layoutParams = android.widget.LinearLayout.LayoutParams(0, android.widget.LinearLayout.LayoutParams.WRAP_CONTENT, 0.8f).apply {
                    marginEnd = 4
                }
                setOnClickListener {
                    noteEditText?.setText(content)
                    editableNoteContent = content
                    isNoteEditing = false
                    Toast.makeText(context, "Note reset to original", Toast.LENGTH_SHORT).show()
                }
            }
            buttonRow.addView(resetButton)

            val saveButton = android.widget.Button(context).apply {
                text = "💾 SAVE"
                setBackgroundColor(0xFF22C55E.toInt())
                setTextColor(0xFFFFFFFF.toInt())
                textSize = 14f
                layoutParams = android.widget.LinearLayout.LayoutParams(0, android.widget.LinearLayout.LayoutParams.WRAP_CONTENT, 1f).apply {
                    marginStart = 4
                    marginEnd = 4
                }
                setOnClickListener { saveCurrentNote() }
            }
            buttonRow.addView(saveButton)

            val closeButton = android.widget.Button(context).apply {
                text = "CLOSE"
                setBackgroundColor(0xFF475569.toInt())
                setTextColor(0xFFFFFFFF.toInt())
                textSize = 14f
                layoutParams = android.widget.LinearLayout.LayoutParams(0, android.widget.LinearLayout.LayoutParams.WRAP_CONTENT, 0.8f).apply {
                    marginStart = 4
                }
                setOnClickListener {
                    // Warn if there are unsaved edits
                    if (isNoteEditing) {
                        confirmDiscardEdits()
                    } else {
                        hideDataOverlay()
                    }
                }
            }
            buttonRow.addView(closeButton)

            innerLayout.addView(buttonRow)
            addView(innerLayout)
        }

        rootView.addView(dataOverlay)
        statusText.text = title
        transcriptText.text = "Edit note, then 'save note' or 'close'"
    }

    private fun confirmDiscardEdits() {
        android.app.AlertDialog.Builder(this)
            .setTitle("Unsaved Changes")
            .setMessage("You have unsaved edits. Discard changes?")
            .setPositiveButton("Discard") { _, _ ->
                isNoteEditing = false
                editableNoteContent = null
                noteEditText = null
                hideDataOverlay()
            }
            .setNegativeButton("Keep Editing", null)
            .show()
    }

    private fun resetNoteEdits() {
        val note = lastGeneratedNote
        if (note == null || noteEditText == null) {
            Toast.makeText(this, "No note to reset", Toast.LENGTH_SHORT).show()
            return
        }

        val originalContent = note.optString("display_text", "")
        noteEditText?.setText(originalContent)
        editableNoteContent = originalContent
        isNoteEditing = false
        Toast.makeText(this, "Note reset to original", Toast.LENGTH_SHORT).show()
        transcriptText.text = "Note restored"
        Log.d(TAG, "Note edits reset to original")
    }

    private fun focusNoteEdit() {
        if (noteEditText == null) {
            Toast.makeText(this, "No note open for editing", Toast.LENGTH_SHORT).show()
            return
        }

        // Focus on EditText and show keyboard
        noteEditText?.requestFocus()
        val imm = getSystemService(Context.INPUT_METHOD_SERVICE) as android.view.inputmethod.InputMethodManager
        imm.showSoftInput(noteEditText, android.view.inputmethod.InputMethodManager.SHOW_IMPLICIT)
        Toast.makeText(this, "Editing note...", Toast.LENGTH_SHORT).show()
        transcriptText.text = "Tap to edit note text"
        Log.d(TAG, "Note edit focused")
    }

    // ============ Voice Note Editing Functions ============

    /**
     * Push current state to edit history for undo functionality.
     */
    private fun pushEditHistory() {
        editableNoteContent?.let {
            editHistory.add(it)
            if (editHistory.size > MAX_EDIT_HISTORY) {
                editHistory.removeAt(0)
            }
            Log.d(TAG, "Pushed to edit history (${editHistory.size} states)")
        }
    }

    /**
     * Undo the last edit by restoring previous state.
     */
    private fun undoLastEdit(): Boolean {
        if (editHistory.isEmpty()) {
            Toast.makeText(this, "Nothing to undo", Toast.LENGTH_SHORT).show()
            speakFeedback("Nothing to undo")
            return false
        }

        val previous = editHistory.removeLast()
        noteEditText?.setText(previous)
        editableNoteContent = previous
        isNoteEditing = editHistory.isNotEmpty()
        Toast.makeText(this, "Change undone", Toast.LENGTH_SHORT).show()
        speakFeedback("Change undone")
        Log.d(TAG, "Undid last edit (${editHistory.size} states remaining)")
        return true
    }

    /**
     * Resolve spoken section name to canonical section name.
     */
    private fun resolveSection(spoken: String): String? {
        val lower = spoken.lowercase()
        for ((canonical, aliases) in sectionAliases) {
            if (aliases.any { lower.contains(it) }) {
                return canonical
            }
        }
        return null
    }

    /**
     * Get the regex pattern for a SOAP section.
     */
    private fun getSectionPattern(section: String): Regex {
        return when (section) {
            "subjective" -> Regex("(▸ S(?:UBJECTIVE)?:?)([\\s\\S]*?)(?=\\n▸ [OAP]|\\n▸ ICD|$)", RegexOption.IGNORE_CASE)
            "objective" -> Regex("(▸ O(?:BJECTIVE)?:?)([\\s\\S]*?)(?=\\n▸ [AP]|\\n▸ ICD|$)", RegexOption.IGNORE_CASE)
            "assessment" -> Regex("(▸ A(?:SSESSMENT)?:?)([\\s\\S]*?)(?=\\n▸ P|\\n▸ ICD|$)", RegexOption.IGNORE_CASE)
            "plan" -> Regex("(▸ P(?:LAN)?:?)([\\s\\S]*?)(?=\\n▸ ICD|\\n▸ CPT|\\n═|$)", RegexOption.IGNORE_CASE)
            else -> Regex("($section:?)([\\s\\S]*?)(?=\\n▸|\\n═|$)", RegexOption.IGNORE_CASE)
        }
    }

    /**
     * Update a note section with new content (replace).
     */
    private fun updateNoteSection(section: String, newContent: String) {
        if (noteEditText == null || editableNoteContent == null) {
            Toast.makeText(this, "No note open. Generate a note first.", Toast.LENGTH_SHORT).show()
            speakFeedback("No note open")
            return
        }

        val canonicalSection = resolveSection(section)
        if (canonicalSection == null) {
            Toast.makeText(this, "Unknown section: $section", Toast.LENGTH_SHORT).show()
            speakFeedback("Unknown section")
            return
        }

        // Push to history before making changes
        pushEditHistory()

        val current = editableNoteContent ?: ""
        val pattern = getSectionPattern(canonicalSection)
        val sectionLabel = when (canonicalSection) {
            "subjective" -> "▸ S:"
            "objective" -> "▸ O:"
            "assessment" -> "▸ A:"
            "plan" -> "▸ P:"
            else -> "▸ ${canonicalSection.uppercase()}:"
        }

        val updated = if (pattern.containsMatchIn(current)) {
            current.replace(pattern) { matchResult ->
                "${matchResult.groupValues[1]}\n$newContent\n"
            }
        } else {
            // Section not found, append at end
            "$current\n$sectionLabel\n$newContent\n"
        }

        noteEditText?.setText(updated)
        editableNoteContent = updated
        isNoteEditing = true

        val sectionName = canonicalSection.replaceFirstChar { it.uppercase() }
        Toast.makeText(this, "$sectionName updated", Toast.LENGTH_SHORT).show()
        speakFeedback("$sectionName updated")
        transcriptText.text = "Changed $sectionName"
        Log.d(TAG, "Updated section $canonicalSection")
    }

    /**
     * Append content to a note section.
     */
    private fun appendToNoteSection(section: String, content: String) {
        if (noteEditText == null || editableNoteContent == null) {
            Toast.makeText(this, "No note open. Generate a note first.", Toast.LENGTH_SHORT).show()
            speakFeedback("No note open")
            return
        }

        val canonicalSection = resolveSection(section)
        if (canonicalSection == null) {
            Toast.makeText(this, "Unknown section: $section", Toast.LENGTH_SHORT).show()
            speakFeedback("Unknown section")
            return
        }

        // Push to history before making changes
        pushEditHistory()

        val current = editableNoteContent ?: ""
        val pattern = getSectionPattern(canonicalSection)

        val updated = if (pattern.containsMatchIn(current)) {
            current.replace(pattern) { matchResult ->
                val existingContent = matchResult.groupValues[2].trimEnd()
                "${matchResult.groupValues[1]}$existingContent\n$content\n"
            }
        } else {
            // Section not found, create it
            val sectionLabel = when (canonicalSection) {
                "subjective" -> "▸ S:"
                "objective" -> "▸ O:"
                "assessment" -> "▸ A:"
                "plan" -> "▸ P:"
                else -> "▸ ${canonicalSection.uppercase()}:"
            }
            "$current\n$sectionLabel\n$content\n"
        }

        noteEditText?.setText(updated)
        editableNoteContent = updated
        isNoteEditing = true

        val sectionName = canonicalSection.replaceFirstChar { it.uppercase() }
        Toast.makeText(this, "Added to $sectionName", Toast.LENGTH_SHORT).show()
        speakFeedback("Added to $sectionName")
        transcriptText.text = "Added to $sectionName"
        Log.d(TAG, "Appended to section $canonicalSection: $content")
    }

    /**
     * Delete the last sentence from the note.
     */
    private fun deleteLastSentence() {
        if (noteEditText == null || editableNoteContent == null) {
            Toast.makeText(this, "No note open", Toast.LENGTH_SHORT).show()
            return
        }

        // Push to history before making changes
        pushEditHistory()

        val current = editableNoteContent ?: ""
        // Find last sentence (ends with . ! or ?)
        val sentencePattern = Regex("[^.!?]*[.!?]\\s*$")
        val updated = current.replace(sentencePattern, "").trimEnd()

        if (updated == current) {
            // Try removing last line instead
            val lines = current.lines().dropLast(1)
            val updatedLines = lines.joinToString("\n")
            noteEditText?.setText(updatedLines)
            editableNoteContent = updatedLines
        } else {
            noteEditText?.setText(updated)
            editableNoteContent = updated
        }

        isNoteEditing = true
        Toast.makeText(this, "Last sentence deleted", Toast.LENGTH_SHORT).show()
        speakFeedback("Deleted")
        transcriptText.text = "Deleted last sentence"
        Log.d(TAG, "Deleted last sentence")
    }

    /**
     * Delete the last line from the note.
     */
    private fun deleteLastLine() {
        if (noteEditText == null || editableNoteContent == null) {
            Toast.makeText(this, "No note open", Toast.LENGTH_SHORT).show()
            return
        }

        // Push to history before making changes
        pushEditHistory()

        val current = editableNoteContent ?: ""
        val lines = current.lines().dropLast(1)
        val updated = lines.joinToString("\n")

        noteEditText?.setText(updated)
        editableNoteContent = updated
        isNoteEditing = true

        Toast.makeText(this, "Last line deleted", Toast.LENGTH_SHORT).show()
        speakFeedback("Line deleted")
        transcriptText.text = "Deleted last line"
        Log.d(TAG, "Deleted last line")
    }

    /**
     * Delete a specific item from a section (e.g., "delete plan item 2").
     */
    private fun deleteSectionItem(section: String, itemNumber: Int) {
        if (noteEditText == null || editableNoteContent == null) {
            Toast.makeText(this, "No note open", Toast.LENGTH_SHORT).show()
            return
        }

        val canonicalSection = resolveSection(section)
        if (canonicalSection == null) {
            Toast.makeText(this, "Unknown section: $section", Toast.LENGTH_SHORT).show()
            return
        }

        // Push to history before making changes
        pushEditHistory()

        val current = editableNoteContent ?: ""
        val pattern = getSectionPattern(canonicalSection)
        val match = pattern.find(current)

        if (match != null) {
            val sectionContent = match.groupValues[2]
            val lines = sectionContent.lines().filter { it.isNotBlank() }

            if (itemNumber in 1..lines.size) {
                val newLines = lines.toMutableList()
                newLines.removeAt(itemNumber - 1)
                val newContent = "\n" + newLines.joinToString("\n") + "\n"

                val updated = current.replace(pattern) { m ->
                    "${m.groupValues[1]}$newContent"
                }

                noteEditText?.setText(updated)
                editableNoteContent = updated
                isNoteEditing = true

                Toast.makeText(this, "Item $itemNumber deleted", Toast.LENGTH_SHORT).show()
                speakFeedback("Item $itemNumber deleted")
                transcriptText.text = "Deleted ${canonicalSection} item $itemNumber"
                Log.d(TAG, "Deleted item $itemNumber from $canonicalSection")
            } else {
                Toast.makeText(this, "Item $itemNumber not found", Toast.LENGTH_SHORT).show()
                speakFeedback("Item not found")
            }
        }
    }

    /**
     * Clear an entire section.
     */
    private fun clearSection(section: String) {
        if (noteEditText == null || editableNoteContent == null) {
            Toast.makeText(this, "No note open", Toast.LENGTH_SHORT).show()
            return
        }

        val canonicalSection = resolveSection(section)
        if (canonicalSection == null) {
            Toast.makeText(this, "Unknown section: $section", Toast.LENGTH_SHORT).show()
            return
        }

        // Push to history before making changes
        pushEditHistory()

        val current = editableNoteContent ?: ""
        val pattern = getSectionPattern(canonicalSection)

        val updated = current.replace(pattern) { matchResult ->
            "${matchResult.groupValues[1]}\n[Section cleared]\n"
        }

        noteEditText?.setText(updated)
        editableNoteContent = updated
        isNoteEditing = true

        val sectionName = canonicalSection.replaceFirstChar { it.uppercase() }
        Toast.makeText(this, "$sectionName cleared", Toast.LENGTH_SHORT).show()
        speakFeedback("$sectionName cleared")
        transcriptText.text = "Cleared $sectionName"
        Log.d(TAG, "Cleared section $canonicalSection")
    }

    /**
     * Insert a macro template into the note.
     */
    private fun insertMacro(macroName: String) {
        if (noteEditText == null || editableNoteContent == null) {
            Toast.makeText(this, "No note open", Toast.LENGTH_SHORT).show()
            return
        }

        val template = macroTemplates[macroName]
        if (template == null) {
            Toast.makeText(this, "Unknown macro: $macroName", Toast.LENGTH_SHORT).show()
            return
        }

        // Push to history before making changes
        pushEditHistory()

        // Determine which section to insert into based on macro type
        val targetSection = when (macroName) {
            "normal_exam", "normal_vitals" -> "objective"
            "negative_ros" -> "subjective"
            "follow_up", "diabetes_followup", "hypertension_followup" -> "plan"
            else -> "plan"
        }

        appendToNoteSection(targetSection, template)

        val macroLabel = macroName.replace("_", " ").replaceFirstChar { it.uppercase() }
        transcriptText.text = "Inserted $macroLabel"
        Log.d(TAG, "Inserted macro $macroName into $targetSection")
    }

    /**
     * Extract content after a keyword (e.g., "change assessment TO headache" -> "headache").
     */
    private fun extractContentAfter(text: String, keyword: String): String {
        val lower = text.lowercase()
        val keywordLower = keyword.lowercase()
        val index = lower.lastIndexOf(keywordLower)
        return if (index >= 0 && index + keyword.length < text.length) {
            text.substring(index + keyword.length).trim()
        } else {
            ""
        }
    }

    /**
     * Extract section name from voice command.
     */
    private fun extractSectionFromCommand(text: String): String? {
        val lower = text.lowercase()
        // Check for section keywords
        for ((canonical, aliases) in sectionAliases) {
            for (alias in aliases) {
                if (lower.contains(alias)) {
                    return canonical
                }
            }
        }
        return null
    }

    // ============ Voice Navigation Functions ============

    /**
     * Scroll the current view down by a page.
     */
    private fun scrollDown() {
        val scrollView = currentScrollView ?: liveTranscriptScrollView
        if (scrollView == null) {
            Toast.makeText(this, "Nothing to scroll", Toast.LENGTH_SHORT).show()
            return
        }

        scrollView.post {
            val scrollAmount = scrollView.height * 3 / 4  // Scroll 75% of visible height
            scrollView.smoothScrollBy(0, scrollAmount)
        }
        speakFeedback("Scrolling down")
        Log.d(TAG, "Voice navigation: scroll down")
    }

    /**
     * Scroll the current view up by a page.
     */
    private fun scrollUp() {
        val scrollView = currentScrollView ?: liveTranscriptScrollView
        if (scrollView == null) {
            Toast.makeText(this, "Nothing to scroll", Toast.LENGTH_SHORT).show()
            return
        }

        scrollView.post {
            val scrollAmount = scrollView.height * 3 / 4  // Scroll 75% of visible height
            scrollView.smoothScrollBy(0, -scrollAmount)
        }
        speakFeedback("Scrolling up")
        Log.d(TAG, "Voice navigation: scroll up")
    }

    /**
     * Scroll to the top of the current view.
     */
    private fun scrollToTop() {
        val scrollView = currentScrollView ?: liveTranscriptScrollView
        if (scrollView == null) {
            Toast.makeText(this, "Nothing to scroll", Toast.LENGTH_SHORT).show()
            return
        }

        scrollView.post {
            scrollView.smoothScrollTo(0, 0)
        }
        speakFeedback("Top of page")
        transcriptText.text = "Scrolled to top"
        Log.d(TAG, "Voice navigation: scroll to top")
    }

    /**
     * Scroll to the bottom of the current view.
     */
    private fun scrollToBottom() {
        val scrollView = currentScrollView ?: liveTranscriptScrollView
        if (scrollView == null) {
            Toast.makeText(this, "Nothing to scroll", Toast.LENGTH_SHORT).show()
            return
        }

        scrollView.post {
            scrollView.fullScroll(android.view.View.FOCUS_DOWN)
        }
        speakFeedback("Bottom of page")
        transcriptText.text = "Scrolled to bottom"
        Log.d(TAG, "Voice navigation: scroll to bottom")
    }

    /**
     * Navigate to a specific section in the note (scroll to section header).
     */
    private fun goToSection(section: String) {
        val content = editableNoteContent ?: currentContentText?.text?.toString()
        if (content == null) {
            Toast.makeText(this, "No content to navigate", Toast.LENGTH_SHORT).show()
            return
        }

        val scrollView = currentScrollView ?: liveTranscriptScrollView
        val textView = noteEditText ?: currentContentText
        if (scrollView == null || textView == null) {
            Toast.makeText(this, "Cannot navigate", Toast.LENGTH_SHORT).show()
            return
        }

        // Find section header in content
        val sectionPattern = when (section) {
            "subjective" -> Regex("(?:▸ S:|S:|SUBJECTIVE:)", RegexOption.IGNORE_CASE)
            "objective" -> Regex("(?:▸ O:|O:|OBJECTIVE:)", RegexOption.IGNORE_CASE)
            "assessment" -> Regex("(?:▸ A:|A:|ASSESSMENT:)", RegexOption.IGNORE_CASE)
            "plan" -> Regex("(?:▸ P:|P:|PLAN:)", RegexOption.IGNORE_CASE)
            else -> {
                Toast.makeText(this, "Unknown section: $section", Toast.LENGTH_SHORT).show()
                return
            }
        }

        val match = sectionPattern.find(content)
        if (match == null) {
            Toast.makeText(this, "Section not found: $section", Toast.LENGTH_SHORT).show()
            speakFeedback("Section not found")
            return
        }

        // Calculate scroll position based on character offset
        val charOffset = match.range.first
        val layout = textView.layout

        if (layout != null) {
            val line = layout.getLineForOffset(charOffset)
            val yPosition = layout.getLineTop(line)

            scrollView.post {
                scrollView.smoothScrollTo(0, yPosition)
            }

            val sectionName = section.replaceFirstChar { it.uppercase() }
            speakFeedback("$sectionName section")
            transcriptText.text = "Navigated to $sectionName"
            Log.d(TAG, "Voice navigation: go to $section at line $line")
        } else {
            // Fallback: just scroll to approximate position
            val approximatePosition = (charOffset.toFloat() / content.length * scrollView.getChildAt(0).height).toInt()
            scrollView.post {
                scrollView.smoothScrollTo(0, approximatePosition)
            }
            speakFeedback("$section section")
            Log.d(TAG, "Voice navigation: go to $section (approximate)")
        }
    }

    /**
     * Read back a specific section of the note using TTS.
     */
    private fun readSection(section: String) {
        val content = editableNoteContent ?: currentContentText?.text?.toString()
        if (content == null) {
            Toast.makeText(this, "No content to read", Toast.LENGTH_SHORT).show()
            return
        }

        // Extract section content
        val sectionContent = extractSectionContent(content, section)
        if (sectionContent.isNullOrEmpty()) {
            Toast.makeText(this, "Section not found: $section", Toast.LENGTH_SHORT).show()
            speakFeedback("Section not found")
            return
        }

        val sectionName = section.replaceFirstChar { it.uppercase() }
        transcriptText.text = "Reading $sectionName..."

        // Speak the section content
        textToSpeech?.speak("$sectionName. $sectionContent", TextToSpeech.QUEUE_FLUSH, null, "read_section")
        Log.d(TAG, "Voice navigation: reading $section section")
    }

    /**
     * Extract the content of a specific section from the note.
     */
    private fun extractSectionContent(content: String, section: String): String? {
        // Define patterns for section boundaries
        val sectionPatterns = mapOf(
            "subjective" to Regex("(?:▸ S:|S:|SUBJECTIVE:?)\\s*(.+?)(?=(?:\\n▸ [OAP]:|\\n[OAP]:|\\nOBJECTIVE:|\\nASSESSMENT:|\\nPLAN:|$))", setOf(RegexOption.DOT_MATCHES_ALL, RegexOption.IGNORE_CASE)),
            "objective" to Regex("(?:▸ O:|O:|OBJECTIVE:?)\\s*(.+?)(?=(?:\\n▸ [AP]:|\\n[AP]:|\\nASSESSMENT:|\\nPLAN:|$))", setOf(RegexOption.DOT_MATCHES_ALL, RegexOption.IGNORE_CASE)),
            "assessment" to Regex("(?:▸ A:|A:|ASSESSMENT:?)\\s*(.+?)(?=(?:\\n▸ P:|\\nP:|\\nPLAN:|$))", setOf(RegexOption.DOT_MATCHES_ALL, RegexOption.IGNORE_CASE)),
            "plan" to Regex("(?:▸ P:|P:|PLAN:?)\\s*(.+?)(?=(?:\\n▸|\\n═|$))", setOf(RegexOption.DOT_MATCHES_ALL, RegexOption.IGNORE_CASE))
        )

        val pattern = sectionPatterns[section] ?: return null
        val match = pattern.find(content)
        return match?.groupValues?.getOrNull(1)?.trim()
    }

    /**
     * Read the entire note using TTS.
     */
    private fun readEntireNote() {
        val content = editableNoteContent ?: currentContentText?.text?.toString()
        if (content == null) {
            Toast.makeText(this, "No content to read", Toast.LENGTH_SHORT).show()
            return
        }

        transcriptText.text = "Reading note..."

        // Clean up the content for speech (remove decorative characters)
        val cleanContent = content
            .replace("▸", "")
            .replace("═", "")
            .replace(Regex("─+"), "")
            .replace(Regex("\\s+"), " ")
            .trim()

        textToSpeech?.speak(cleanContent, TextToSpeech.QUEUE_FLUSH, null, "read_note")
        Log.d(TAG, "Voice navigation: reading entire note")
    }

    /**
     * Show only a specific section of the note (hide others).
     */
    private fun showSectionOnly(section: String) {
        val content = editableNoteContent ?: return

        val sectionContent = extractSectionContent(content, section)
        if (sectionContent.isNullOrEmpty()) {
            Toast.makeText(this, "Section not found: $section", Toast.LENGTH_SHORT).show()
            return
        }

        val sectionName = section.replaceFirstChar { it.uppercase() }
        val displayContent = "▸ ${sectionName.first()}:\n$sectionContent"

        showDataOverlay("$sectionName Section", displayContent)
        speakFeedback("$sectionName only")
        Log.d(TAG, "Voice navigation: showing $section only")
    }

    // ============ Voice Dictation Mode Functions ============

    /**
     * Start dictation mode for a specific note section.
     * All subsequent speech will be accumulated and inserted into the target section.
     */
    private fun startDictation(section: String) {
        if (noteEditText == null || editableNoteContent == null) {
            Toast.makeText(this, "Open a note first to dictate", Toast.LENGTH_SHORT).show()
            speakFeedback("Open a note first")
            return
        }

        // Validate section exists
        val resolvedSection = resolveSection(section)
        if (resolvedSection == null) {
            Toast.makeText(this, "Unknown section: $section", Toast.LENGTH_SHORT).show()
            speakFeedback("Unknown section")
            return
        }

        isDictationMode = true
        dictationTargetSection = resolvedSection
        dictationBuffer.clear()

        val sectionName = resolvedSection.replaceFirstChar { it.uppercase() }
        transcriptText.text = "🎙️ Dictating to $sectionName... Say 'stop dictating' when done"
        statusText.text = "DICTATION MODE: $sectionName"

        speakFeedback("Dictating to $sectionName. Speak now.")
        Toast.makeText(this, "Dictation started for $sectionName", Toast.LENGTH_SHORT).show()
        Log.d(TAG, "Dictation mode started for section: $resolvedSection")

        // Show visual indicator
        showDictationIndicator(sectionName)
    }

    /**
     * Stop dictation mode and insert accumulated text into the target section.
     */
    private fun stopDictation() {
        if (!isDictationMode) {
            Toast.makeText(this, "Not in dictation mode", Toast.LENGTH_SHORT).show()
            return
        }

        val section = dictationTargetSection
        val dictatedText = dictationBuffer.toString().trim()

        isDictationMode = false
        dictationTargetSection = null

        // Hide dictation indicator
        hideDictationIndicator()

        if (dictatedText.isEmpty()) {
            transcriptText.text = "Dictation ended (no text captured)"
            speakFeedback("No text captured")
            Log.d(TAG, "Dictation stopped with no text")
            return
        }

        if (section != null) {
            // Push to history before making changes
            pushEditHistory()

            // Append dictated text to the section
            appendToNoteSection(section, dictatedText)

            val sectionName = section.replaceFirstChar { it.uppercase() }
            val wordCount = dictatedText.split("\\s+".toRegex()).size
            transcriptText.text = "Added $wordCount words to $sectionName"
            speakFeedback("Added $wordCount words to $sectionName")
            Log.d(TAG, "Dictation complete: $wordCount words added to $section")
        }

        dictationBuffer.clear()
        statusText.text = "MDx Vision"
    }

    /**
     * Cancel dictation mode without inserting text.
     */
    private fun cancelDictation() {
        if (!isDictationMode) {
            Toast.makeText(this, "Not in dictation mode", Toast.LENGTH_SHORT).show()
            return
        }

        isDictationMode = false
        dictationTargetSection = null
        dictationBuffer.clear()

        hideDictationIndicator()

        transcriptText.text = "Dictation cancelled"
        statusText.text = "MDx Vision"
        speakFeedback("Dictation cancelled")
        Log.d(TAG, "Dictation cancelled")
    }

    /**
     * Add text to the dictation buffer (called during speech recognition in dictation mode).
     */
    private fun addToDictationBuffer(text: String) {
        if (!isDictationMode) return

        if (dictationBuffer.isNotEmpty()) {
            dictationBuffer.append(" ")
        }
        dictationBuffer.append(text)

        // Update display to show what's been captured
        val section = dictationTargetSection?.replaceFirstChar { it.uppercase() } ?: "Note"
        val wordCount = dictationBuffer.toString().split("\\s+".toRegex()).filter { it.isNotEmpty() }.size
        transcriptText.text = "🎙️ $section: $wordCount words captured\n\"${getLastWords(dictationBuffer.toString(), 10)}...\""

        Log.d(TAG, "Dictation buffer: ${dictationBuffer.length} chars, $wordCount words")
    }

    /**
     * Get the last N words from a string for preview.
     */
    private fun getLastWords(text: String, n: Int): String {
        val words = text.split("\\s+".toRegex()).filter { it.isNotEmpty() }
        return if (words.size <= n) {
            text
        } else {
            words.takeLast(n).joinToString(" ")
        }
    }

    /**
     * Show visual indicator for dictation mode.
     */
    private var dictationIndicator: android.widget.FrameLayout? = null

    private fun showDictationIndicator(sectionName: String) {
        // Remove existing indicator if any
        hideDictationIndicator()

        val rootView = window.decorView.findViewById<android.view.ViewGroup>(android.R.id.content)

        dictationIndicator = android.widget.FrameLayout(this).apply {
            setBackgroundColor(0xCC000000.toInt())

            val indicatorLayout = android.widget.LinearLayout(context).apply {
                orientation = android.widget.LinearLayout.VERTICAL
                gravity = android.view.Gravity.CENTER
                setPadding(32, 24, 32, 24)
                layoutParams = android.widget.FrameLayout.LayoutParams(
                    android.widget.FrameLayout.LayoutParams.MATCH_PARENT,
                    android.widget.FrameLayout.LayoutParams.WRAP_CONTENT
                ).apply {
                    gravity = android.view.Gravity.TOP
                }
            }

            // Recording indicator
            val recordingText = TextView(context).apply {
                text = "🎙️ DICTATING TO $sectionName"
                textSize = 18f
                setTextColor(0xFFEF4444.toInt())  // Red for recording
                gravity = android.view.Gravity.CENTER
                setPadding(0, 0, 0, 8)
            }
            indicatorLayout.addView(recordingText)

            // Instructions
            val instructionsText = TextView(context).apply {
                text = "Speak now • Say \"stop dictating\" when done"
                textSize = 14f
                setTextColor(0xFF94A3B8.toInt())
                gravity = android.view.Gravity.CENTER
            }
            indicatorLayout.addView(instructionsText)

            addView(indicatorLayout)

            // Tap to stop
            setOnClickListener {
                stopDictation()
            }
        }

        rootView.addView(dictationIndicator)
    }

    private fun hideDictationIndicator() {
        dictationIndicator?.let { indicator ->
            (indicator.parent as? android.view.ViewGroup)?.removeView(indicator)
            dictationIndicator = null
        }
    }

    /**
     * Check if currently in dictation mode.
     */
    private fun isInDictationMode(): Boolean = isDictationMode

    private fun showVoiceCommandHelp() {
        val helpText = """
            |🎤 VOICE COMMANDS
            |${"─".repeat(30)}
            |
            |📋 PATIENT DATA
            |• "Load patient" - Load test patient
            |• "Find [name]" - Search patients
            |• "Scan wristband" - Scan barcode
            |
            |🏥 CLINICAL INFO
            |• "Show vitals" - Display vitals
            |• "Show allergies" - Display allergies
            |• "Show meds" - Display medications
            |• "Show labs" - Display lab results
            |• "Show procedures" - Display procedures
            |• "Show immunizations" - Display vaccines
            |• "Show conditions" - Display diagnoses
            |• "Show care plans" - Display care plans
            |• "Show notes" - Display clinical notes
            |
            |🔊 PATIENT SUMMARY (Hands-Free)
            |• "Patient summary" - Show quick overview
            |• "Brief me" - Speak summary aloud
            |• "Tell me about patient" - Spoken briefing
            |• "Stop talking" - Stop speech
            |
            |📝 DOCUMENTATION
            |• "Start note" - Begin documentation
            |• "Live transcribe" - Real-time transcription
            |• "Stop transcription" - End transcription
            |• "SOAP note" - Set note type to SOAP
            |• "Progress note" - Set to Progress Note
            |• "H&P note" - Set to H&P
            |• "Consult note" - Set to Consult
            |• "Auto note" - Auto-detect note type
            |
            |📋 TRANSCRIPT PREVIEW
            |• "Generate note" - Create note from transcript
            |• "Looks good" - Confirm and generate
            |• "Re-record" - Start over
            |• "Try again" - Discard and re-record
            |
            |💾 NOTE MANAGEMENT
            |• "Edit note" - Focus note for editing
            |• "Reset note" - Restore original note
            |• "Save note" - Sign off and save
            |
            |✏️ VOICE NOTE EDITING
            |• "Change [section] to [text]" - Replace section
            |• "Add to [section]: [text]" - Append to section
            |• "Delete last sentence" - Remove last sentence
            |• "Delete [section] item [N]" - Remove item
            |• "Clear [section]" - Clear entire section
            |• "Insert normal exam" - Add normal exam
            |• "Insert follow up" - Add follow-up text
            |• "Undo" - Undo last change
            |
            |🧭 VOICE NAVIGATION
            |• "Scroll down" / "Page down" - Scroll down
            |• "Scroll up" / "Page up" - Scroll up
            |• "Go to top" - Scroll to top
            |• "Go to bottom" - Scroll to bottom
            |• "Go to [section]" - Jump to section
            |• "Show [section] only" - Show one section
            |• "Read [section]" - Read section aloud
            |• "Read note" - Read entire note aloud
            |
            |🎙️ VOICE DICTATION
            |• "Dictate to [section]" - Start dictating
            |• "Stop dictating" - End and insert text
            |• "Cancel dictation" - Discard dictated text
            |
            |📤 OFFLINE DRAFTS
            |• "Show drafts" - View pending drafts
            |• "Sync notes" - Upload pending drafts
            |• "Delete draft [N]" - Remove draft
            |• "View draft [N]" - See draft details
            |
            |⚙️ SETTINGS
            |• "My name is Dr. [Name]" - Set clinician
            |• "Increase font" - Larger text
            |• "Decrease font" - Smaller text
            |• "Auto scroll on/off" - Toggle scroll
            |• "Speech feedback" - Toggle voice confirmations
            |
            |📋 HISTORY
            |• "Show history" - Recent patients
            |• "Load [N]" - Load patient from history
            |• "Clear history" - Clear patient history
            |
            |🔐 SECURITY
            |• "Lock session" - Lock for HIPAA
            |• "Unlock" - Unlock session
            |• "Timeout [N] min" - Set timeout
            |
            |🔧 OTHER
            |• "Hey MDx [command]" - Wake word
            |• "Close" - Dismiss overlay
            |• "Clear cache" - Clear offline data
            |• "Help" - Show this help
        """.trimMargin()

        showDataOverlay("Voice Commands", helpText)
        statusText.text = "Voice Command Help"
        transcriptText.text = "Say any command or 'close'"
        Log.d(TAG, "Showing voice command help")
    }

    private fun showQuickPatientSummary() {
        val patient = currentPatientData
        if (patient == null) {
            Toast.makeText(this, "No patient loaded. Say 'load patient' first.", Toast.LENGTH_SHORT).show()
            return
        }

        val name = patient.optString("name", "Unknown")
        val dob = patient.optString("date_of_birth", "")
        val gender = patient.optString("gender", "").uppercase()

        val sb = StringBuilder()
        sb.append("👤 PATIENT SUMMARY\n")
        sb.append("${"═".repeat(30)}\n\n")

        // Demographics
        sb.append("$name\n")
        if (dob.isNotEmpty()) sb.append("DOB: $dob")
        if (gender.isNotEmpty()) sb.append(" | $gender")
        sb.append("\n\n")

        // Critical: Allergies (always show first)
        val allergies = patient.optJSONArray("allergies")
        sb.append("⚠️ ALLERGIES\n")
        if (allergies != null && allergies.length() > 0) {
            for (i in 0 until minOf(allergies.length(), 5)) {
                sb.append("  • ${allergies.getString(i)}\n")
            }
            if (allergies.length() > 5) sb.append("  (+${allergies.length() - 5} more)\n")
        } else {
            sb.append("  No known allergies\n")
        }
        sb.append("\n")

        // Active Conditions
        val conditions = patient.optJSONArray("conditions")
        sb.append("📋 ACTIVE CONDITIONS\n")
        if (conditions != null && conditions.length() > 0) {
            var activeCount = 0
            for (i in 0 until minOf(conditions.length(), 5)) {
                val cond = conditions.getJSONObject(i)
                val condName = cond.optString("name", "")
                val status = cond.optString("status", "")
                if (condName.isNotEmpty()) {
                    sb.append("  • $condName")
                    if (status.isNotEmpty()) sb.append(" [$status]")
                    sb.append("\n")
                    activeCount++
                }
            }
            if (conditions.length() > 5) sb.append("  (+${conditions.length() - 5} more)\n")
            if (activeCount == 0) sb.append("  None recorded\n")
        } else {
            sb.append("  None recorded\n")
        }
        sb.append("\n")

        // Current Medications
        val meds = patient.optJSONArray("medications")
        sb.append("💊 CURRENT MEDICATIONS\n")
        if (meds != null && meds.length() > 0) {
            for (i in 0 until minOf(meds.length(), 5)) {
                sb.append("  • ${meds.getString(i)}\n")
            }
            if (meds.length() > 5) sb.append("  (+${meds.length() - 5} more)\n")
        } else {
            sb.append("  None recorded\n")
        }
        sb.append("\n")

        // Recent Vitals (just the key ones)
        val vitals = patient.optJSONArray("vitals")
        sb.append("📊 RECENT VITALS\n")
        if (vitals != null && vitals.length() > 0) {
            for (i in 0 until minOf(vitals.length(), 4)) {
                val v = vitals.getJSONObject(i)
                sb.append("  • ${v.optString("name")}: ${v.optString("value")}${v.optString("unit")}\n")
            }
        } else {
            sb.append("  None recorded\n")
        }

        showDataOverlay("Patient Summary", sb.toString())
        statusText.text = "Patient Summary"
        transcriptText.text = "Key info for $name"
        Log.d(TAG, "Showing quick patient summary for $name")
    }

    /**
     * Initialize Text-to-Speech for hands-free patient information
     * Allows clinicians to hear patient summary while walking to the room
     */
    private fun initTextToSpeech() {
        textToSpeech = TextToSpeech(this) { status ->
            if (status == TextToSpeech.SUCCESS) {
                val result = textToSpeech?.setLanguage(Locale.US)
                if (result == TextToSpeech.LANG_MISSING_DATA || result == TextToSpeech.LANG_NOT_SUPPORTED) {
                    Log.e(TAG, "TTS: Language not supported")
                    isTtsReady = false
                } else {
                    isTtsReady = true
                    // Set slightly slower speech rate for medical info clarity
                    textToSpeech?.setSpeechRate(0.9f)
                    Log.d(TAG, "TTS: Initialized successfully")
                }
            } else {
                Log.e(TAG, "TTS: Initialization failed")
                isTtsReady = false
            }
        }
    }

    /**
     * Speak text aloud using Text-to-Speech
     */
    private fun speak(text: String, queueMode: Int = TextToSpeech.QUEUE_FLUSH) {
        if (isTtsReady && textToSpeech != null) {
            textToSpeech?.speak(text, queueMode, null, "mdx_tts_${System.currentTimeMillis()}")
        } else {
            Toast.makeText(this, "Speech not available", Toast.LENGTH_SHORT).show()
        }
    }

    /**
     * Stop any ongoing speech
     */
    private fun stopSpeaking() {
        textToSpeech?.stop()
    }

    /**
     * Speak patient summary aloud - hands-free briefing while walking to patient
     * Creates a natural, conversational summary of key patient information
     */
    private fun speakPatientSummary() {
        val patient = currentPatientData
        if (patient == null) {
            speak("No patient loaded. Say load patient first.")
            return
        }

        val name = patient.optString("name", "Unknown patient")
        val dob = patient.optString("date_of_birth", "")
        val gender = patient.optString("gender", "")

        val speechBuilder = StringBuilder()

        // Start with patient identification
        speechBuilder.append("Patient summary for $name. ")
        if (gender.isNotEmpty()) {
            speechBuilder.append("${gender}. ")
        }
        if (dob.isNotEmpty()) {
            speechBuilder.append("Date of birth: ${formatDateForSpeech(dob)}. ")
        }

        // Critical: Allergies first (safety)
        val allergies = patient.optJSONArray("allergies")
        if (allergies != null && allergies.length() > 0) {
            speechBuilder.append("Alert: Patient has ${allergies.length()} known ${if (allergies.length() == 1) "allergy" else "allergies"}. ")
            for (i in 0 until minOf(allergies.length(), 3)) {
                speechBuilder.append("${allergies.getString(i)}. ")
            }
            if (allergies.length() > 3) {
                speechBuilder.append("And ${allergies.length() - 3} more. ")
            }
        } else {
            speechBuilder.append("No known allergies. ")
        }

        // Active Conditions
        val conditions = patient.optJSONArray("conditions")
        if (conditions != null && conditions.length() > 0) {
            speechBuilder.append("Active conditions: ")
            for (i in 0 until minOf(conditions.length(), 3)) {
                val cond = conditions.getJSONObject(i)
                val condName = cond.optString("name", "")
                if (condName.isNotEmpty()) {
                    speechBuilder.append("$condName. ")
                }
            }
            if (conditions.length() > 3) {
                speechBuilder.append("Plus ${conditions.length() - 3} more. ")
            }
        }

        // Current Medications (brief)
        val meds = patient.optJSONArray("medications")
        if (meds != null && meds.length() > 0) {
            speechBuilder.append("On ${meds.length()} ${if (meds.length() == 1) "medication" else "medications"}. ")
            // Only read top 2 for brevity
            for (i in 0 until minOf(meds.length(), 2)) {
                speechBuilder.append("${meds.getString(i)}. ")
            }
        }

        // Recent Vitals (key ones)
        val vitals = patient.optJSONArray("vitals")
        if (vitals != null && vitals.length() > 0) {
            speechBuilder.append("Recent vitals: ")
            for (i in 0 until minOf(vitals.length(), 3)) {
                val v = vitals.getJSONObject(i)
                val vitalName = v.optString("name", "")
                val vitalValue = v.optString("value", "")
                val vitalUnit = v.optString("unit", "")
                if (vitalName.isNotEmpty() && vitalValue.isNotEmpty()) {
                    speechBuilder.append("${formatVitalNameForSpeech(vitalName)}: $vitalValue $vitalUnit. ")
                }
            }
        }

        speechBuilder.append("End of summary.")

        // Also show on screen while speaking
        showQuickPatientSummary()

        // Speak the summary
        speak(speechBuilder.toString())
        Log.d(TAG, "Speaking patient summary for $name")
    }

    /**
     * Format date string for natural speech (e.g., "1990-09-15" -> "September 15th, 1990")
     */
    private fun formatDateForSpeech(dateStr: String): String {
        return try {
            val parts = dateStr.split("-")
            if (parts.size == 3) {
                val months = listOf("January", "February", "March", "April", "May", "June",
                    "July", "August", "September", "October", "November", "December")
                val month = months.getOrElse(parts[1].toInt() - 1) { parts[1] }
                val day = parts[2].toInt()
                val daySuffix = when {
                    day in 11..13 -> "th"
                    day % 10 == 1 -> "st"
                    day % 10 == 2 -> "nd"
                    day % 10 == 3 -> "rd"
                    else -> "th"
                }
                "$month $day$daySuffix, ${parts[0]}"
            } else {
                dateStr
            }
        } catch (e: Exception) {
            dateStr
        }
    }

    /**
     * Format vital names for natural speech
     */
    private fun formatVitalNameForSpeech(name: String): String {
        return when {
            name.contains("BP", ignoreCase = true) || name.contains("Blood Pressure", ignoreCase = true) -> "Blood pressure"
            name.contains("HR", ignoreCase = true) || name.contains("Heart Rate", ignoreCase = true) -> "Heart rate"
            name.contains("Temp", ignoreCase = true) -> "Temperature"
            name.contains("SpO2", ignoreCase = true) || name.contains("O2 Sat", ignoreCase = true) -> "Oxygen saturation"
            name.contains("RR", ignoreCase = true) || name.contains("Resp", ignoreCase = true) -> "Respiratory rate"
            name.contains("BMI", ignoreCase = true) -> "B M I"
            else -> name
        }
    }

    private fun saveCurrentNote() {
        // Show sign-off confirmation dialog before saving
        showSignOffConfirmation()
    }

    private fun showSignOffConfirmation() {
        val note = lastGeneratedNote
        if (note == null) {
            Toast.makeText(this, "No note to save. Generate a note first.", Toast.LENGTH_SHORT).show()
            return
        }

        val patientName = currentPatientData?.optString("name") ?: "Unknown Patient"
        val noteType = note.optString("note_type", currentNoteType)
        val wasEdited = isNoteEditing
        val editedLabel = if (wasEdited) " (edited)" else ""

        // Build confirmation dialog
        val dialogView = android.widget.LinearLayout(this).apply {
            orientation = android.widget.LinearLayout.VERTICAL
            setPadding(48, 32, 48, 16)
        }

        // Header
        val headerText = TextView(this).apply {
            text = "📋 Sign Off & Save Note"
            textSize = 20f
            setTextColor(0xFF10B981.toInt())
            setPadding(0, 0, 0, 24)
        }
        dialogView.addView(headerText)

        // Patient info
        val patientText = TextView(this).apply {
            text = "Patient: $patientName"
            textSize = 16f
            setTextColor(0xFF1F2937.toInt())
            setPadding(0, 0, 0, 8)
        }
        dialogView.addView(patientText)

        // Note type
        val noteTypeText = TextView(this).apply {
            text = "Note Type: $noteType$editedLabel"
            textSize = 16f
            setTextColor(0xFF1F2937.toInt())
            setPadding(0, 0, 0, 8)
        }
        dialogView.addView(noteTypeText)

        // Clinician
        val clinicianText = TextView(this).apply {
            text = "Signed by: $clinicianName"
            textSize = 16f
            setTextColor(0xFF1F2937.toInt())
            setPadding(0, 0, 0, 16)
        }
        dialogView.addView(clinicianText)

        // Confirmation checkbox
        val confirmCheckbox = android.widget.CheckBox(this).apply {
            text = "I confirm this clinical note is accurate and complete"
            textSize = 14f
            setTextColor(0xFF374151.toInt())
            setPadding(0, 8, 0, 8)
        }
        dialogView.addView(confirmCheckbox)

        // Disclaimer
        val disclaimerText = TextView(this).apply {
            text = "This note will be saved to the patient's medical record."
            textSize = 12f
            setTextColor(0xFF6B7280.toInt())
            setPadding(0, 16, 0, 0)
        }
        dialogView.addView(disclaimerText)

        val dialog = android.app.AlertDialog.Builder(this)
            .setView(dialogView)
            .setPositiveButton("Sign & Save", null)  // Set to null initially to prevent auto-dismiss
            .setNegativeButton("Cancel") { d, _ -> d.dismiss() }
            .create()

        dialog.setOnShowListener {
            val signButton = dialog.getButton(android.app.AlertDialog.BUTTON_POSITIVE)
            signButton.isEnabled = false  // Disable until checkbox is checked

            confirmCheckbox.setOnCheckedChangeListener { _, isChecked ->
                signButton.isEnabled = isChecked
            }

            signButton.setOnClickListener {
                if (confirmCheckbox.isChecked) {
                    dialog.dismiss()
                    performNoteSave()
                } else {
                    Toast.makeText(this, "Please confirm the note is accurate", Toast.LENGTH_SHORT).show()
                }
            }
        }

        dialog.show()
    }

    private fun performNoteSave() {
        val note = lastGeneratedNote
        val transcript = lastNoteTranscript
        val patientId = currentPatientData?.optString("patient_id") ?: TEST_PATIENT_ID
        val patientName = currentPatientData?.optString("name") ?: "Unknown Patient"

        if (note == null) {
            Toast.makeText(this, "No note to save. Generate a note first.", Toast.LENGTH_SHORT).show()
            return
        }

        // Use edited content if available, otherwise use original
        val noteContent = editableNoteContent ?: note.optString("display_text", "")
        val wasEdited = isNoteEditing
        val signedAt = java.text.SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss", java.util.Locale.US).format(java.util.Date())
        val summary = note.optString("summary", "")

        // Check if offline - save as draft immediately
        if (!isNetworkAvailable()) {
            val draftId = saveDraftNote(
                patientId = patientId,
                patientName = patientName,
                noteType = currentNoteType,
                displayText = noteContent,
                summary = summary,
                transcript = transcript ?: "",
                wasEdited = wasEdited,
                signedBy = clinicianName,
                signedAt = signedAt
            )

            Toast.makeText(this, "Offline - Note saved as draft: $draftId", Toast.LENGTH_LONG).show()
            statusText.text = "Draft saved (offline)"
            transcriptText.text = "Will sync when online"
            speakFeedback("Note saved as offline draft")
            clearAfterSave()
            return
        }

        statusText.text = "Saving note..."
        transcriptText.text = if (wasEdited) "Saving edited note..." else "Uploading to EHR"

        Thread {
            try {
                val json = JSONObject().apply {
                    put("patient_id", patientId)
                    put("note_type", currentNoteType)
                    put("display_text", noteContent)
                    put("summary", summary)
                    put("transcript", transcript ?: "")
                    put("timestamp", note.optString("timestamp", ""))
                    put("was_edited", wasEdited)
                    put("signed_by", clinicianName)
                    put("signed_at", signedAt)
                }

                val request = Request.Builder()
                    .url("$EHR_PROXY_URL/api/v1/notes/save")
                    .post(json.toString().toRequestBody("application/json".toMediaType()))
                    .build()

                httpClient.newCall(request).enqueue(object : Callback {
                    override fun onFailure(call: Call, e: IOException) {
                        Log.e(TAG, "Save note error: ${e.message}")
                        runOnUiThread {
                            // Save as draft on network failure
                            val draftId = saveDraftNote(
                                patientId = patientId,
                                patientName = patientName,
                                noteType = currentNoteType,
                                displayText = noteContent,
                                summary = summary,
                                transcript = transcript ?: "",
                                wasEdited = wasEdited,
                                signedBy = clinicianName,
                                signedAt = signedAt
                            )
                            Toast.makeText(this@MainActivity, "Save failed - saved as draft: $draftId", Toast.LENGTH_LONG).show()
                            statusText.text = "Saved as draft"
                            transcriptText.text = "Will retry when online"
                            speakFeedback("Save failed. Note saved as draft.")
                            clearAfterSave()
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
                                    val editMsg = if (wasEdited) " (edited)" else ""
                                    Toast.makeText(this@MainActivity, "Note saved$editMsg! ID: $noteId", Toast.LENGTH_LONG).show()
                                    statusText.text = "Note saved"
                                    transcriptText.text = "ID: $noteId"
                                    lastSavedNoteId = noteId  // Store for push-to-EHR
                                    clearAfterSave()
                                    speakFeedback("Note saved successfully. Say push note to send to EHR.")
                                } else {
                                    val message = result.optString("message", "Save failed")
                                    Toast.makeText(this@MainActivity, message, Toast.LENGTH_SHORT).show()
                                    statusText.text = "MDx Vision"
                                    speakFeedback("Failed to save note")
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
                    // Save as draft on exception
                    val draftId = saveDraftNote(
                        patientId = patientId,
                        patientName = patientName,
                        noteType = currentNoteType,
                        displayText = noteContent,
                        summary = summary,
                        transcript = transcript ?: "",
                        wasEdited = wasEdited,
                        signedBy = clinicianName,
                        signedAt = signedAt
                    )
                    Toast.makeText(this@MainActivity, "Error - saved as draft: $draftId", Toast.LENGTH_LONG).show()
                    statusText.text = "Saved as draft"
                    speakFeedback("Error occurred. Note saved as draft.")
                    clearAfterSave()
                }
            }
        }.start()
    }

    private fun clearAfterSave() {
        lastGeneratedNote = null
        lastNoteTranscript = null
        editableNoteContent = null
        noteEditText = null
        isNoteEditing = false
        hideDataOverlay()
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
                                    val patientName = patient.optString("name", "Unknown")
                                    if (patientId.isNotEmpty()) {
                                        cachePatientData(patientId, body ?: "{}")
                                        // Add to patient history for quick access
                                        addToPatientHistory(patientId, patientName)
                                    }

                                    showPatientDataOverlay(patient)
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

    // Store last saved note ID for push-to-EHR feature
    private var lastSavedNoteId: String? = null

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
                // Speech feedback and safety warnings even when offline
                speakFeedback("Patient $name loaded from cache")
                speakCriticalVitalAlerts(cached)  // Vitals first (most urgent)
                speakAllergyWarnings(cached)
                speakCriticalLabAlerts(cached)
                speakMedicationInteractions(cached)
                speakLabTrends(cached)
                speakVitalTrends(cached)  // Trends last
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
                                // Speech feedback and safety warnings from cache
                                speakFeedback("Patient $name loaded from cache")
                                speakCriticalVitalAlerts(cached)  // Vitals first (most urgent)
                                speakAllergyWarnings(cached)
                                speakCriticalLabAlerts(cached)
                                speakMedicationInteractions(cached)
                                speakLabTrends(cached)
                                speakVitalTrends(cached)  // Trends last
                            } else {
                                statusText.text = "Connection failed"
                                transcriptText.text = "Error: ${e.message}"
                                speakFeedback("Failed to load patient")
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

                                // Add to patient history for quick access
                                addToPatientHistory(patientId, name)

                                showPatientDataOverlay(patient)

                                // Speech feedback
                                speakFeedback("Patient $name loaded")

                                // Safety-critical alerts (always spoken) - vitals first as most urgent
                                speakCriticalVitalAlerts(patient)
                                speakAllergyWarnings(patient)
                                speakCriticalLabAlerts(patient)
                                speakMedicationInteractions(patient)
                                speakLabTrends(patient)
                                speakVitalTrends(patient)  // Trends last
                            } catch (e: Exception) {
                                showDataOverlay("Error", body ?: "No response")
                                speakFeedback("Error loading patient")
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

    // ============ Session Timeout Methods (HIPAA Compliance) ============

    /**
     * Update last activity timestamp. Call this on any user interaction.
     */
    private fun updateLastActivity() {
        lastActivityTime = System.currentTimeMillis()
    }

    /**
     * Start the session timeout checker.
     * Runs periodically to check if session should be locked.
     */
    private fun startSessionTimeoutChecker() {
        sessionCheckHandler = android.os.Handler(android.os.Looper.getMainLooper())
        sessionCheckRunnable = object : Runnable {
            override fun run() {
                checkSessionTimeout()
                sessionCheckHandler?.postDelayed(this, SESSION_CHECK_INTERVAL_MS)
            }
        }
        sessionCheckHandler?.postDelayed(sessionCheckRunnable!!, SESSION_CHECK_INTERVAL_MS)
        Log.d(TAG, "Session timeout checker started (${sessionTimeoutMinutes} min timeout)")
    }

    /**
     * Stop the session timeout checker.
     */
    private fun stopSessionTimeoutChecker() {
        sessionCheckRunnable?.let { sessionCheckHandler?.removeCallbacks(it) }
        sessionCheckHandler = null
        sessionCheckRunnable = null
        Log.d(TAG, "Session timeout checker stopped")
    }

    /**
     * Check if session has timed out and lock if needed.
     */
    private fun checkSessionTimeout() {
        if (isSessionLocked) return

        val elapsed = System.currentTimeMillis() - lastActivityTime
        val timeoutMs = sessionTimeoutMinutes * 60 * 1000L

        if (elapsed >= timeoutMs) {
            Log.d(TAG, "Session timeout - locking after ${elapsed / 1000}s inactivity")
            lockSession()
        }
    }

    /**
     * Lock the session - hide PHI and show lock screen.
     */
    private fun lockSession() {
        if (isSessionLocked) return

        isSessionLocked = true
        Log.d(TAG, "Session locked for HIPAA compliance")

        // Stop any active transcription
        if (isLiveTranscribing) {
            stopLiveTranscription()
        }

        // Stop TTS
        textToSpeech?.stop()

        // Hide any data overlays
        hideDataOverlay()
        hideLiveTranscriptionOverlay()

        // Show lock screen
        showLockScreenOverlay()

        // Update status
        statusText.text = "Session Locked"
        transcriptText.text = "Tap or say 'unlock' to continue"
        patientDataText.text = ""

        // Speak lock notification
        speakFeedback("Session locked due to inactivity")
    }

    /**
     * Unlock the session.
     */
    private fun unlockSession() {
        if (!isSessionLocked) return

        isSessionLocked = false
        updateLastActivity()

        // Hide lock screen
        hideLockScreenOverlay()

        // Restore status
        statusText.text = "Session Unlocked"
        transcriptText.text = "Ready for commands"

        // Speak unlock confirmation
        speakFeedback("Session unlocked")

        Log.d(TAG, "Session unlocked")
    }

    /**
     * Show the lock screen overlay.
     */
    private fun showLockScreenOverlay() {
        if (lockScreenOverlay != null) return

        val rootView = findViewById<android.view.ViewGroup>(android.R.id.content)

        lockScreenOverlay = android.widget.FrameLayout(this).apply {
            setBackgroundColor(0xF0121212.toInt())
            isClickable = true
            isFocusable = true

            setOnClickListener {
                unlockSession()
            }
        }

        val lockContent = android.widget.LinearLayout(this).apply {
            orientation = android.widget.LinearLayout.VERTICAL
            gravity = android.view.Gravity.CENTER
            setPadding(48, 48, 48, 48)
        }

        // Lock icon
        val lockIcon = TextView(this).apply {
            text = "🔒"
            textSize = 72f
            gravity = android.view.Gravity.CENTER
        }

        // Lock message
        val lockMessage = TextView(this).apply {
            text = "Session Locked"
            textSize = 28f
            setTextColor(0xFFFFFFFF.toInt())
            gravity = android.view.Gravity.CENTER
            setPadding(0, 24, 0, 16)
        }

        // HIPAA message
        val hipaaMessage = TextView(this).apply {
            text = "For HIPAA compliance, this session\nwas locked due to inactivity."
            textSize = 16f
            setTextColor(0xFFAAAAAA.toInt())
            gravity = android.view.Gravity.CENTER
            setPadding(0, 0, 0, 32)
        }

        // Unlock instruction
        val unlockInstruction = TextView(this).apply {
            text = "Tap anywhere or say \"unlock\" to continue"
            textSize = 14f
            setTextColor(0xFF4CAF50.toInt())
            gravity = android.view.Gravity.CENTER
        }

        // Timeout info
        val timeoutInfo = TextView(this).apply {
            text = "Timeout: ${sessionTimeoutMinutes} minutes"
            textSize = 12f
            setTextColor(0xFF666666.toInt())
            gravity = android.view.Gravity.CENTER
            setPadding(0, 48, 0, 0)
        }

        lockContent.addView(lockIcon)
        lockContent.addView(lockMessage)
        lockContent.addView(hipaaMessage)
        lockContent.addView(unlockInstruction)
        lockContent.addView(timeoutInfo)

        val contentParams = android.widget.FrameLayout.LayoutParams(
            android.widget.FrameLayout.LayoutParams.WRAP_CONTENT,
            android.widget.FrameLayout.LayoutParams.WRAP_CONTENT
        ).apply {
            gravity = android.view.Gravity.CENTER
        }

        lockScreenOverlay?.addView(lockContent, contentParams)

        val overlayParams = android.widget.FrameLayout.LayoutParams(
            android.widget.FrameLayout.LayoutParams.MATCH_PARENT,
            android.widget.FrameLayout.LayoutParams.MATCH_PARENT
        )

        rootView.addView(lockScreenOverlay, overlayParams)
        Log.d(TAG, "Lock screen overlay shown")
    }

    /**
     * Hide the lock screen overlay.
     */
    private fun hideLockScreenOverlay() {
        lockScreenOverlay?.let {
            val rootView = findViewById<android.view.ViewGroup>(android.R.id.content)
            rootView.removeView(it)
            lockScreenOverlay = null
            Log.d(TAG, "Lock screen overlay hidden")
        }
    }

    /**
     * Set session timeout duration in minutes.
     */
    private fun setSessionTimeout(minutes: Int) {
        sessionTimeoutMinutes = minutes.coerceIn(1, 60)
        cachePrefs.edit().putInt(PREF_SESSION_TIMEOUT, sessionTimeoutMinutes).apply()
        Toast.makeText(this, "Session timeout set to $sessionTimeoutMinutes minutes", Toast.LENGTH_SHORT).show()
        speakFeedback("Session timeout set to $sessionTimeoutMinutes minutes")
        Log.d(TAG, "Session timeout set to $sessionTimeoutMinutes minutes")
    }

    /**
     * Load session timeout setting from preferences.
     */
    private fun loadSessionTimeoutSetting() {
        sessionTimeoutMinutes = cachePrefs.getInt(PREF_SESSION_TIMEOUT, DEFAULT_SESSION_TIMEOUT_MINUTES)
        Log.d(TAG, "Loaded session timeout: $sessionTimeoutMinutes minutes")
    }

    // ============ Patient History Methods ============

    /**
     * Add a patient to the recently viewed history.
     * Stores patient ID, name, and timestamp for quick access.
     * Maintains a maximum of MAX_HISTORY_SIZE entries.
     */
    private fun addToPatientHistory(patientId: String, patientName: String) {
        val history = getPatientHistory().toMutableList()

        // Remove existing entry for this patient (to move to top)
        history.removeAll { it.optString("patient_id") == patientId }

        // Create new entry
        val entry = JSONObject().apply {
            put("patient_id", patientId)
            put("name", patientName)
            put("timestamp", System.currentTimeMillis())
        }

        // Add to beginning (most recent first)
        history.add(0, entry)

        // Trim to max size
        val trimmed = history.take(MAX_HISTORY_SIZE)

        // Save as JSON array
        val historyArray = org.json.JSONArray()
        trimmed.forEach { historyArray.put(it) }

        cachePrefs.edit()
            .putString(HISTORY_KEY, historyArray.toString())
            .apply()

        Log.d(TAG, "Added to history: $patientName ($patientId)")
    }

    /**
     * Get list of recently viewed patients.
     * Returns list of JSONObjects with patient_id, name, timestamp.
     */
    private fun getPatientHistory(): List<JSONObject> {
        val historyJson = cachePrefs.getString(HISTORY_KEY, null) ?: return emptyList()

        return try {
            val array = org.json.JSONArray(historyJson)
            (0 until array.length()).map { array.getJSONObject(it) }
        } catch (e: Exception) {
            Log.e(TAG, "Failed to parse patient history: ${e.message}")
            emptyList()
        }
    }

    /**
     * Clear patient history.
     */
    private fun clearPatientHistory() {
        cachePrefs.edit().remove(HISTORY_KEY).apply()
        Toast.makeText(this, "Patient history cleared", Toast.LENGTH_SHORT).show()
        Log.d(TAG, "Patient history cleared")
    }

    /**
     * Show overlay with recently viewed patients.
     * Allows quick load by saying "load [number]".
     */
    private fun showHistoryOverlay() {
        val history = getPatientHistory()

        if (history.isEmpty()) {
            showDataOverlay("📋 Recent Patients", "No patients in history.\n\nLoad a patient to add them to history.")
            speakFeedback("No patients in history")
            return
        }

        val sb = StringBuilder()
        sb.appendLine("Say \"load [number]\" to quickly load a patient")
        sb.appendLine()

        history.forEachIndexed { index, entry ->
            val name = entry.optString("name", "Unknown")
            val patientId = entry.optString("patient_id", "")
            val timestamp = entry.optLong("timestamp", 0)
            val timeAgo = formatTimeAgo(timestamp)

            sb.appendLine("${index + 1}. $name")
            sb.appendLine("   ID: $patientId • $timeAgo")
            sb.appendLine()
        }

        sb.appendLine("─────────────────────")
        sb.appendLine("Commands: \"clear history\"")

        showDataOverlay("📋 Recent Patients (${history.size})", sb.toString())
        speakFeedback("${history.size} recent patients")
    }

    /**
     * Load patient from history by index (1-based).
     */
    private fun loadPatientFromHistory(index: Int) {
        val history = getPatientHistory()

        if (index < 1 || index > history.size) {
            Toast.makeText(this, "Invalid selection: $index", Toast.LENGTH_SHORT).show()
            speakFeedback("Invalid selection")
            return
        }

        val entry = history[index - 1]
        val patientId = entry.optString("patient_id", "")
        val patientName = entry.optString("name", "Unknown")

        if (patientId.isEmpty()) {
            Toast.makeText(this, "Invalid patient entry", Toast.LENGTH_SHORT).show()
            return
        }

        Log.d(TAG, "Loading patient from history: $patientName ($patientId)")
        fetchPatientData(patientId)
    }

    // ============ Offline Note Drafts Methods ============

    private fun saveDraftNote(
        patientId: String,
        patientName: String,
        noteType: String,
        displayText: String,
        summary: String,
        transcript: String,
        wasEdited: Boolean,
        signedBy: String,
        signedAt: String
    ): String {
        val draftId = "DRAFT-${java.util.UUID.randomUUID().toString().take(8).uppercase()}"

        val draft = JSONObject().apply {
            put("draft_id", draftId)
            put("patient_id", patientId)
            put("patient_name", patientName)
            put("note_type", noteType)
            put("display_text", displayText)
            put("summary", summary)
            put("transcript", transcript)
            put("was_edited", wasEdited)
            put("signed_by", signedBy)
            put("signed_at", signedAt)
            put("created_at", System.currentTimeMillis())
            put("sync_attempts", 0)
            put("last_sync_attempt", 0L)
            put("last_error", JSONObject.NULL)
        }

        cachePrefs.edit().apply {
            putString("$DRAFT_PREFIX$draftId", draft.toString())
            val existingIds = cachePrefs.getString(DRAFT_IDS_KEY, "") ?: ""
            val newIds = if (existingIds.isEmpty()) draftId else "$existingIds,$draftId"
            putString(DRAFT_IDS_KEY, newIds)
            apply()
        }

        Log.d(TAG, "Saved draft note: $draftId for patient $patientId")
        updatePendingDraftsIndicator()
        return draftId
    }

    private fun getPendingDrafts(): List<JSONObject> {
        val idsString = cachePrefs.getString(DRAFT_IDS_KEY, "") ?: ""
        if (idsString.isEmpty()) return emptyList()

        return idsString.split(",")
            .filter { it.isNotEmpty() }
            .mapNotNull { draftId ->
                cachePrefs.getString("$DRAFT_PREFIX$draftId", null)?.let { json ->
                    try { JSONObject(json) } catch (e: Exception) { null }
                }
            }
            .sortedByDescending { it.optLong("created_at", 0) }
    }

    private fun getPendingDraftCount(): Int {
        val idsString = cachePrefs.getString(DRAFT_IDS_KEY, "") ?: ""
        return if (idsString.isEmpty()) 0 else idsString.split(",").filter { it.isNotEmpty() }.size
    }

    private fun deleteDraft(draftId: String) {
        cachePrefs.edit().apply {
            remove("$DRAFT_PREFIX$draftId")

            val existingIds = cachePrefs.getString(DRAFT_IDS_KEY, "") ?: ""
            val newIds = existingIds.split(",")
                .filter { it.isNotEmpty() && it != draftId }
                .joinToString(",")
            putString(DRAFT_IDS_KEY, newIds)
            apply()
        }

        Log.d(TAG, "Deleted draft: $draftId")
        updatePendingDraftsIndicator()
    }

    private fun updateDraftSyncStatus(draftId: String, error: String?) {
        val draftJson = cachePrefs.getString("$DRAFT_PREFIX$draftId", null) ?: return

        try {
            val draft = JSONObject(draftJson)
            draft.put("sync_attempts", draft.optInt("sync_attempts", 0) + 1)
            draft.put("last_sync_attempt", System.currentTimeMillis())
            draft.put("last_error", error ?: JSONObject.NULL)

            cachePrefs.edit().putString("$DRAFT_PREFIX$draftId", draft.toString()).apply()
        } catch (e: Exception) {
            Log.e(TAG, "Failed to update draft sync status: ${e.message}")
        }
    }

    private fun updatePendingDraftsIndicator() {
        val count = getPendingDraftCount()
        runOnUiThread {
            if (count > 0) {
                transcriptText.text = "📋 $count draft(s) pending sync"
            }
        }
    }

    private fun formatTimeAgo(timestamp: Long): String {
        val diff = System.currentTimeMillis() - timestamp
        val minutes = diff / 60000
        val hours = minutes / 60
        val days = hours / 24

        return when {
            days > 0 -> "$days day(s) ago"
            hours > 0 -> "$hours hour(s) ago"
            minutes > 0 -> "$minutes min ago"
            else -> "Just now"
        }
    }

    private fun showPendingDraftsOverlay() {
        val drafts = getPendingDrafts()

        if (drafts.isEmpty()) {
            Toast.makeText(this, "No pending drafts", Toast.LENGTH_SHORT).show()
            return
        }

        val sb = StringBuilder()
        sb.append("📋 PENDING DRAFTS\n")
        sb.append("${"═".repeat(30)}\n\n")

        drafts.forEachIndexed { index, draft ->
            val patientName = draft.optString("patient_name", "Unknown")
            val noteType = draft.optString("note_type", "SOAP")
            val createdAt = draft.optLong("created_at", 0)
            val attempts = draft.optInt("sync_attempts", 0)
            val lastError = draft.optString("last_error", "")
            val timeAgo = formatTimeAgo(createdAt)
            val draftIdShort = draft.optString("draft_id", "")

            sb.append("${index + 1}. $patientName\n")
            sb.append("   Type: $noteType | $timeAgo\n")
            sb.append("   ID: $draftIdShort\n")
            if (attempts > 0) {
                sb.append("   ⚠️ Sync attempts: $attempts\n")
                if (lastError.isNotEmpty() && lastError != "null") {
                    sb.append("   Error: $lastError\n")
                }
            }
            sb.append("\n")
        }

        sb.append("─".repeat(30) + "\n")
        sb.append("Say 'sync notes' to sync now\n")
        sb.append("Say 'delete draft [number]' to remove\n")
        sb.append("Say 'view draft [number]' to see details")

        showDataOverlay("Pending Drafts (${drafts.size})", sb.toString())
    }

    private fun showDraftDetails(draft: JSONObject) {
        val patientName = draft.optString("patient_name", "Unknown")
        val noteType = draft.optString("note_type", "SOAP")
        val displayText = draft.optString("display_text", "")
        val draftId = draft.optString("draft_id", "")

        val title = "$noteType Draft - $patientName"
        val content = "$displayText\n\n─────────────────\nDraft ID: $draftId\nSay 'delete draft' to remove"

        showDataOverlay(title, content)
    }

    // ============ Network Monitoring & Auto-Sync ============

    private fun registerNetworkCallback() {
        val connectivityManager = getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager

        networkCallback = object : ConnectivityManager.NetworkCallback() {
            override fun onAvailable(network: android.net.Network) {
                Log.d(TAG, "Network available - checking for pending drafts")
                runOnUiThread {
                    val draftCount = getPendingDraftCount()
                    if (draftCount > 0 && !isSyncing) {
                        Toast.makeText(this@MainActivity, "Network restored - $draftCount draft(s) pending", Toast.LENGTH_SHORT).show()
                        syncPendingDrafts()
                    }
                }
            }

            override fun onLost(network: android.net.Network) {
                Log.d(TAG, "Network lost")
                runOnUiThread {
                    val draftCount = getPendingDraftCount()
                    if (draftCount > 0) {
                        transcriptText.text = "Offline - $draftCount draft(s) pending"
                    }
                }
            }
        }

        val networkRequest = android.net.NetworkRequest.Builder()
            .addCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
            .build()

        connectivityManager.registerNetworkCallback(networkRequest, networkCallback!!)
        Log.d(TAG, "Network callback registered")
    }

    private fun unregisterNetworkCallback() {
        networkCallback?.let { callback ->
            val connectivityManager = getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
            try {
                connectivityManager.unregisterNetworkCallback(callback)
                Log.d(TAG, "Network callback unregistered")
            } catch (e: Exception) {
                Log.e(TAG, "Error unregistering network callback: ${e.message}")
            }
        }
        networkCallback = null
    }

    private fun syncPendingDrafts() {
        if (isSyncing) {
            Log.d(TAG, "Sync already in progress")
            return
        }

        val drafts = getPendingDrafts()
        if (drafts.isEmpty()) {
            Log.d(TAG, "No drafts to sync")
            return
        }

        if (!isNetworkAvailable()) {
            Log.d(TAG, "Network not available for sync")
            Toast.makeText(this, "No network connection", Toast.LENGTH_SHORT).show()
            return
        }

        isSyncing = true
        statusText.text = "Syncing ${drafts.size} draft(s)..."
        speakFeedback("Syncing ${drafts.size} pending notes")

        Thread {
            var successCount = 0
            var failCount = 0

            for (draft in drafts) {
                val draftId = draft.optString("draft_id", "")
                val attempts = draft.optInt("sync_attempts", 0)

                // Skip if too many attempts
                if (attempts >= MAX_SYNC_ATTEMPTS) {
                    Log.w(TAG, "Skipping draft $draftId - max attempts reached")
                    failCount++
                    continue
                }

                try {
                    val json = JSONObject().apply {
                        put("patient_id", draft.optString("patient_id"))
                        put("note_type", draft.optString("note_type"))
                        put("display_text", draft.optString("display_text"))
                        put("summary", draft.optString("summary"))
                        put("transcript", draft.optString("transcript"))
                        put("timestamp", draft.optString("signed_at"))
                        put("was_edited", draft.optBoolean("was_edited"))
                        put("signed_by", draft.optString("signed_by"))
                        put("signed_at", draft.optString("signed_at"))
                    }

                    val request = Request.Builder()
                        .url("$EHR_PROXY_URL/api/v1/notes/save")
                        .post(json.toString().toRequestBody("application/json".toMediaType()))
                        .build()

                    val response = httpClient.newCall(request).execute()
                    val body = response.body?.string()
                    val result = JSONObject(body ?: "{}")

                    if (result.optBoolean("success", false)) {
                        deleteDraft(draftId)
                        successCount++
                        Log.d(TAG, "Synced draft $draftId successfully")
                    } else {
                        updateDraftSyncStatus(draftId, result.optString("message", "Unknown error"))
                        failCount++
                    }
                } catch (e: Exception) {
                    Log.e(TAG, "Sync error for draft $draftId: ${e.message}")
                    updateDraftSyncStatus(draftId, e.message)
                    failCount++
                }
            }

            isSyncing = false

            runOnUiThread {
                updatePendingDraftsIndicator()

                when {
                    successCount > 0 && failCount == 0 -> {
                        Toast.makeText(this@MainActivity, "Synced $successCount note(s)", Toast.LENGTH_SHORT).show()
                        statusText.text = "All notes synced"
                        transcriptText.text = "Ready"
                        speakFeedback("All notes synced successfully")
                    }
                    successCount > 0 && failCount > 0 -> {
                        Toast.makeText(this@MainActivity, "Synced $successCount, $failCount failed", Toast.LENGTH_LONG).show()
                        statusText.text = "$failCount draft(s) pending"
                        speakFeedback("Synced $successCount notes. $failCount still pending.")
                    }
                    else -> {
                        Toast.makeText(this@MainActivity, "Sync failed - will retry later", Toast.LENGTH_SHORT).show()
                        statusText.text = "${drafts.size} draft(s) pending"
                    }
                }
            }
        }.start()
    }

    // ============ Font Size Methods ============

    private fun getContentFontSize(): Float {
        return when (currentFontSizeLevel) {
            FONT_SIZE_SMALL -> 14f
            FONT_SIZE_MEDIUM -> 16f
            FONT_SIZE_LARGE -> 20f
            FONT_SIZE_EXTRA_LARGE -> 24f
            else -> 16f
        }
    }

    private fun getTitleFontSize(): Float {
        return when (currentFontSizeLevel) {
            FONT_SIZE_SMALL -> 18f
            FONT_SIZE_MEDIUM -> 22f
            FONT_SIZE_LARGE -> 26f
            FONT_SIZE_EXTRA_LARGE -> 30f
            else -> 22f
        }
    }

    private fun getFontSizeName(): String {
        return when (currentFontSizeLevel) {
            FONT_SIZE_SMALL -> "Small"
            FONT_SIZE_MEDIUM -> "Medium"
            FONT_SIZE_LARGE -> "Large"
            FONT_SIZE_EXTRA_LARGE -> "Extra Large"
            else -> "Medium"
        }
    }

    private fun loadFontSizeSetting() {
        currentFontSizeLevel = cachePrefs.getInt(PREF_FONT_SIZE, FONT_SIZE_MEDIUM)
    }

    private fun saveFontSizeSetting() {
        cachePrefs.edit().putInt(PREF_FONT_SIZE, currentFontSizeLevel).apply()
    }

    private fun loadClinicianName() {
        clinicianName = cachePrefs.getString(PREF_CLINICIAN_NAME, DEFAULT_CLINICIAN_NAME) ?: DEFAULT_CLINICIAN_NAME
    }

    private fun setClinicianName(name: String) {
        clinicianName = name
        cachePrefs.edit().putString(PREF_CLINICIAN_NAME, name).apply()
        Toast.makeText(this, "Clinician: $name", Toast.LENGTH_SHORT).show()
        transcriptText.text = "Clinician set to: $name"
        Log.d(TAG, "Clinician name set to: $name")
    }

    private fun loadSpeechFeedbackSetting() {
        isSpeechFeedbackEnabled = cachePrefs.getBoolean(PREF_SPEECH_FEEDBACK, true)
    }

    private fun toggleSpeechFeedback() {
        isSpeechFeedbackEnabled = !isSpeechFeedbackEnabled
        cachePrefs.edit().putBoolean(PREF_SPEECH_FEEDBACK, isSpeechFeedbackEnabled).apply()
        val status = if (isSpeechFeedbackEnabled) "enabled" else "disabled"
        Toast.makeText(this, "Speech feedback $status", Toast.LENGTH_SHORT).show()
        transcriptText.text = "Speech feedback: $status"
        // Announce the change
        if (isSpeechFeedbackEnabled) {
            speakFeedback("Speech feedback enabled")
        }
        Log.d(TAG, "Speech feedback $status")
    }

    /**
     * Push saved note to EHR as FHIR DocumentReference
     */
    private fun pushNoteToEhr() {
        val noteId = lastSavedNoteId
        if (noteId == null) {
            Toast.makeText(this, "No saved note to push", Toast.LENGTH_SHORT).show()
            speakFeedback("No saved note to push. Save a note first.")
            return
        }

        if (!isNetworkAvailable()) {
            Toast.makeText(this, "No network - cannot push to EHR", Toast.LENGTH_SHORT).show()
            speakFeedback("No network connection. Cannot push to EHR.")
            return
        }

        statusText.text = "Pushing to EHR..."
        speakFeedback("Pushing note to EHR")

        Thread {
            try {
                val request = Request.Builder()
                    .url("$EHR_PROXY_URL/api/v1/notes/$noteId/push")
                    .post("".toRequestBody("application/json".toMediaType()))
                    .build()

                httpClient.newCall(request).enqueue(object : Callback {
                    override fun onFailure(call: Call, e: IOException) {
                        Log.e(TAG, "Push to EHR failed: ${e.message}")
                        runOnUiThread {
                            Toast.makeText(this@MainActivity, "Push failed: ${e.message}", Toast.LENGTH_LONG).show()
                            statusText.text = "Push failed"
                            speakFeedback("Push to EHR failed. Network error.")
                        }
                    }

                    override fun onResponse(call: Call, response: Response) {
                        val body = response.body?.string()
                        Log.d(TAG, "Push response: $body")

                        runOnUiThread {
                            try {
                                val result = JSONObject(body ?: "{}")
                                val success = result.optBoolean("success", false)

                                if (success) {
                                    val fhirId = result.optString("fhir_id", "")
                                    val alreadyPushed = result.optBoolean("already_pushed", false)

                                    if (alreadyPushed) {
                                        Toast.makeText(this@MainActivity, "Note was already pushed to EHR", Toast.LENGTH_SHORT).show()
                                        speakFeedback("Note was already pushed to EHR")
                                    } else {
                                        Toast.makeText(this@MainActivity, "Note pushed to EHR: $fhirId", Toast.LENGTH_LONG).show()
                                        speakFeedback("Note successfully pushed to EHR")
                                    }
                                    statusText.text = "Pushed to EHR"
                                    transcriptText.text = fhirId
                                } else {
                                    val error = result.optString("error", "Push failed")
                                    val statusCode = result.optInt("status_code", 0)

                                    // Handle sandbox read-only gracefully
                                    if (statusCode == 403) {
                                        Toast.makeText(this@MainActivity, "EHR sandbox is read-only", Toast.LENGTH_LONG).show()
                                        speakFeedback("EHR sandbox is read-only. Production credentials required.")
                                        statusText.text = "Sandbox read-only"
                                    } else {
                                        Toast.makeText(this@MainActivity, error, Toast.LENGTH_LONG).show()
                                        speakFeedback("Push to EHR failed")
                                        statusText.text = "Push failed"
                                    }
                                }
                            } catch (e: Exception) {
                                Toast.makeText(this@MainActivity, "Push response error", Toast.LENGTH_SHORT).show()
                                speakFeedback("Push response error")
                            }
                        }
                    }
                })
            } catch (e: Exception) {
                Log.e(TAG, "Failed to push note: ${e.message}")
                runOnUiThread {
                    Toast.makeText(this@MainActivity, "Push error: ${e.message}", Toast.LENGTH_LONG).show()
                    statusText.text = "Push error"
                    speakFeedback("Failed to push note to EHR")
                }
            }
        }.start()
    }

    /**
     * Speak feedback for actions (respects toggle setting)
     * Use this for confirmations like "Patient loaded", "Note saved", etc.
     */
    private fun speakFeedback(message: String) {
        if (isSpeechFeedbackEnabled && isTtsReady && textToSpeech != null) {
            textToSpeech?.speak(message, TextToSpeech.QUEUE_ADD, null, "feedback_${System.currentTimeMillis()}")
        }
    }

    /**
     * Speak allergy warnings when patient is loaded (safety-critical)
     * Always speaks allergies regardless of speech feedback toggle for patient safety
     */
    private fun speakAllergyWarnings(patient: JSONObject) {
        if (!isTtsReady || textToSpeech == null) return

        val allergies = patient.optJSONArray("allergies")
        if (allergies != null && allergies.length() > 0) {
            val count = allergies.length()
            val allergyWord = if (count == 1) "allergy" else "allergies"

            val speechBuilder = StringBuilder()
            speechBuilder.append("Alert: Patient has $count known $allergyWord. ")

            // Speak up to 5 allergies
            for (i in 0 until minOf(count, 5)) {
                speechBuilder.append("${allergies.getString(i)}. ")
            }
            if (count > 5) {
                speechBuilder.append("And ${count - 5} more.")
            }

            // Use QUEUE_ADD so it plays after "Patient loaded" message
            textToSpeech?.speak(speechBuilder.toString(), TextToSpeech.QUEUE_ADD, null, "allergy_warning_${System.currentTimeMillis()}")
            Log.d(TAG, "Spoke allergy warning: $count allergies")
        }
    }

    /**
     * Speak critical lab alerts when patient is loaded (safety-critical)
     * Always speaks critical labs regardless of speech feedback toggle for patient safety
     */
    private fun speakCriticalLabAlerts(patient: JSONObject) {
        if (!isTtsReady || textToSpeech == null) return

        val criticalLabs = patient.optJSONArray("critical_labs")
        if (criticalLabs != null && criticalLabs.length() > 0) {
            val count = criticalLabs.length()
            val labWord = if (count == 1) "lab value" else "lab values"

            val speechBuilder = StringBuilder()
            speechBuilder.append("Critical alert: Patient has $count critical $labWord. ")

            // Speak up to 3 critical labs with values
            for (i in 0 until minOf(count, 3)) {
                val lab = criticalLabs.getJSONObject(i)
                val name = lab.optString("name", "Unknown")
                val value = lab.optString("value", "")
                val unit = lab.optString("unit", "")
                val interp = lab.optString("interpretation", "")

                // Format interpretation for speech
                val interpText = when (interp) {
                    "HH" -> "critically high"
                    "LL" -> "critically low"
                    "H" -> "high"
                    "L" -> "low"
                    else -> "abnormal"
                }

                speechBuilder.append("$name is $interpText at $value $unit. ")
            }
            if (count > 3) {
                speechBuilder.append("Plus ${count - 3} more critical values.")
            }

            // Use QUEUE_ADD so it plays after allergies if both exist
            textToSpeech?.speak(speechBuilder.toString(), TextToSpeech.QUEUE_ADD, null, "critical_lab_alert_${System.currentTimeMillis()}")
            Log.d(TAG, "Spoke critical lab alert: $count critical labs")
        }
    }

    /**
     * Speak significant lab trends when patient is loaded
     * Alerts clinician to rising or falling lab values
     */
    private fun speakLabTrends(patient: JSONObject) {
        if (!isTtsReady || textToSpeech == null || !isSpeechFeedbackEnabled) return

        val labs = patient.optJSONArray("labs") ?: return
        if (labs.length() == 0) return

        val trendingLabs = mutableListOf<String>()

        for (i in 0 until labs.length()) {
            val lab = labs.getJSONObject(i)
            val trend = lab.optString("trend", "")
            val name = lab.optString("name", "")
            val value = lab.optString("value", "")
            val previousValue = lab.optString("previous_value", "")

            // Only speak rising or falling trends (skip stable/new)
            if (trend == "rising" || trend == "falling") {
                val direction = if (trend == "rising") "rising" else "falling"
                trendingLabs.add("$name $direction from $previousValue to $value")
            }
        }

        if (trendingLabs.isNotEmpty()) {
            val count = trendingLabs.size
            val labWord = if (count == 1) "lab" else "labs"

            val speechBuilder = StringBuilder()
            speechBuilder.append("Note: $count trending $labWord. ")

            // Speak up to 3 trending labs
            for (i in 0 until minOf(count, 3)) {
                speechBuilder.append("${trendingLabs[i]}. ")
            }
            if (count > 3) {
                speechBuilder.append("Plus ${count - 3} more trending.")
            }

            // Queue after critical alerts
            textToSpeech?.speak(speechBuilder.toString(), TextToSpeech.QUEUE_ADD, null, "lab_trend_alert_${System.currentTimeMillis()}")
            Log.d(TAG, "Spoke lab trend alert: $count trending labs")
        }
    }

    /**
     * Speak significant vital trends when patient is loaded
     * Alerts clinician to rising or falling vital values
     */
    private fun speakVitalTrends(patient: JSONObject) {
        if (!isTtsReady || textToSpeech == null || !isSpeechFeedbackEnabled) return

        val vitals = patient.optJSONArray("vitals") ?: return
        if (vitals.length() == 0) return

        val trendingVitals = mutableListOf<String>()

        for (i in 0 until vitals.length()) {
            val vital = vitals.getJSONObject(i)
            val trend = vital.optString("trend", "")
            val name = vital.optString("name", "")
            val value = vital.optString("value", "")
            val previousValue = vital.optString("previous_value", "")

            // Only speak rising or falling trends (skip stable/new)
            if (trend == "rising" || trend == "falling") {
                val direction = if (trend == "rising") "rising" else "falling"
                trendingVitals.add("$name $direction from $previousValue to $value")
            }
        }

        if (trendingVitals.isNotEmpty()) {
            val count = trendingVitals.size
            val vitalWord = if (count == 1) "vital" else "vitals"

            val speechBuilder = StringBuilder()
            speechBuilder.append("Note: $count trending $vitalWord. ")

            // Speak up to 3 trending vitals
            for (i in 0 until minOf(count, 3)) {
                speechBuilder.append("${trendingVitals[i]}. ")
            }
            if (count > 3) {
                speechBuilder.append("Plus ${count - 3} more trending.")
            }

            // Queue after other alerts
            textToSpeech?.speak(speechBuilder.toString(), TextToSpeech.QUEUE_ADD, null, "vital_trend_alert_${System.currentTimeMillis()}")
            Log.d(TAG, "Spoke vital trend alert: $count trending vitals")
        }
    }

    /**
     * Speak critical vital alerts when patient is loaded (safety-critical)
     * Always speaks critical vitals regardless of speech feedback toggle for patient safety
     */
    private fun speakCriticalVitalAlerts(patient: JSONObject) {
        if (!isTtsReady || textToSpeech == null) return

        val criticalVitals = patient.optJSONArray("critical_vitals")
        if (criticalVitals != null && criticalVitals.length() > 0) {
            val count = criticalVitals.length()
            val vitalWord = if (count == 1) "vital sign" else "vital signs"

            val speechBuilder = StringBuilder()
            speechBuilder.append("Warning: Patient has $count critical $vitalWord. ")

            // Speak up to 3 critical vitals with values
            for (i in 0 until minOf(count, 3)) {
                val vital = criticalVitals.getJSONObject(i)
                val name = vital.optString("name", "Unknown")
                val value = vital.optString("value", "")
                val unit = vital.optString("unit", "")
                val interp = vital.optString("interpretation", "")

                // Format interpretation for speech
                val interpText = when (interp) {
                    "HH" -> "critically high"
                    "LL" -> "critically low"
                    "H" -> "high"
                    "L" -> "low"
                    else -> "abnormal"
                }

                // Make vital names more speech-friendly
                val speechName = when {
                    name.contains("systolic", ignoreCase = true) -> "blood pressure systolic"
                    name.contains("diastolic", ignoreCase = true) -> "blood pressure diastolic"
                    name.contains("heart rate", ignoreCase = true) -> "heart rate"
                    name.contains("pulse", ignoreCase = true) -> "pulse"
                    name.contains("respiratory", ignoreCase = true) -> "respiratory rate"
                    name.contains("oxygen", ignoreCase = true) || name.contains("spo2", ignoreCase = true) -> "oxygen saturation"
                    name.contains("temp", ignoreCase = true) -> "temperature"
                    else -> name
                }

                speechBuilder.append("$speechName is $interpText at $value $unit. ")
            }
            if (count > 3) {
                speechBuilder.append("Plus ${count - 3} more critical vitals.")
            }

            // Use QUEUE_FLUSH to speak vitals FIRST (most urgent safety alert)
            textToSpeech?.speak(speechBuilder.toString(), TextToSpeech.QUEUE_FLUSH, null, "critical_vital_alert_${System.currentTimeMillis()}")
            Log.d(TAG, "Spoke critical vital alert: $count critical vitals")
        }
    }

    /**
     * Speak medication interaction alerts when patient is loaded (safety-critical)
     * High severity interactions always spoken regardless of speech feedback toggle
     */
    private fun speakMedicationInteractions(patient: JSONObject) {
        if (!isTtsReady || textToSpeech == null) return

        val interactions = patient.optJSONArray("medication_interactions")
        if (interactions != null && interactions.length() > 0) {
            // Filter for high severity interactions
            val highSeverityInteractions = mutableListOf<JSONObject>()
            for (i in 0 until interactions.length()) {
                val interaction = interactions.getJSONObject(i)
                if (interaction.optString("severity", "") == "high") {
                    highSeverityInteractions.add(interaction)
                }
            }

            if (highSeverityInteractions.isEmpty()) return

            val count = highSeverityInteractions.size
            val interactionWord = if (count == 1) "drug interaction" else "drug interactions"

            val speechBuilder = StringBuilder()
            speechBuilder.append("Warning: Patient has $count high-risk $interactionWord. ")

            // Speak up to 2 high severity interactions
            for (i in 0 until minOf(count, 2)) {
                val interaction = highSeverityInteractions[i]
                val drug1 = interaction.optString("drug1", "").split(" ").firstOrNull() ?: "medication"
                val drug2 = interaction.optString("drug2", "").split(" ").firstOrNull() ?: "medication"
                val effect = interaction.optString("effect", "potential interaction")

                // Simplify effect for speech (take first part before dash or period)
                val shortEffect = effect.split(" - ").firstOrNull()?.split(".")?.firstOrNull() ?: effect

                speechBuilder.append("$drug1 with $drug2: $shortEffect. ")
            }
            if (count > 2) {
                speechBuilder.append("Plus ${count - 2} more interactions.")
            }

            // Use QUEUE_ADD so it plays after vitals/allergies/labs
            textToSpeech?.speak(speechBuilder.toString(), TextToSpeech.QUEUE_ADD, null, "medication_interaction_alert_${System.currentTimeMillis()}")
            Log.d(TAG, "Spoke medication interaction alert: $count high-severity interactions")
        }
    }

    private fun increaseFontSize() {
        if (currentFontSizeLevel < FONT_SIZE_EXTRA_LARGE) {
            currentFontSizeLevel++
            saveFontSizeSetting()
            Toast.makeText(this, "Font size: ${getFontSizeName()}", Toast.LENGTH_SHORT).show()
            transcriptText.text = "Font: ${getFontSizeName()}"
            Log.d(TAG, "Font size increased to ${getFontSizeName()}")
        } else {
            Toast.makeText(this, "Font size already at maximum", Toast.LENGTH_SHORT).show()
        }
    }

    private fun decreaseFontSize() {
        if (currentFontSizeLevel > FONT_SIZE_SMALL) {
            currentFontSizeLevel--
            saveFontSizeSetting()
            Toast.makeText(this, "Font size: ${getFontSizeName()}", Toast.LENGTH_SHORT).show()
            transcriptText.text = "Font: ${getFontSizeName()}"
            Log.d(TAG, "Font size decreased to ${getFontSizeName()}")
        } else {
            Toast.makeText(this, "Font size already at minimum", Toast.LENGTH_SHORT).show()
        }
    }

    private fun setFontSize(level: Int) {
        currentFontSizeLevel = level.coerceIn(FONT_SIZE_SMALL, FONT_SIZE_EXTRA_LARGE)
        saveFontSizeSetting()
        Toast.makeText(this, "Font size: ${getFontSizeName()}", Toast.LENGTH_SHORT).show()
        transcriptText.text = "Font: ${getFontSizeName()}"
        Log.d(TAG, "Font size set to ${getFontSizeName()}")
    }

    // ============ Auto-Scroll Methods ============

    private fun enableAutoScroll() {
        isAutoScrollEnabled = true
        Toast.makeText(this, "Auto-scroll enabled", Toast.LENGTH_SHORT).show()
        transcriptText.text = "Auto-scroll: ON"
        Log.d(TAG, "Auto-scroll enabled")
        // Immediately scroll to bottom
        liveTranscriptScrollView?.post {
            liveTranscriptScrollView?.fullScroll(android.view.View.FOCUS_DOWN)
        }
    }

    private fun disableAutoScroll() {
        isAutoScrollEnabled = false
        Toast.makeText(this, "Auto-scroll disabled", Toast.LENGTH_SHORT).show()
        transcriptText.text = "Auto-scroll: OFF"
        Log.d(TAG, "Auto-scroll disabled")
    }

    private fun toggleAutoScroll() {
        if (isAutoScrollEnabled) {
            disableAutoScroll()
        } else {
            enableAutoScroll()
        }
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

        // Update activity on any voice command
        updateLastActivity()

        // If session is locked, only process unlock command
        if (isSessionLocked) {
            if (lower.contains("unlock")) {
                unlockSession()
            }
            startVoiceRecognition()
            return
        }

        // If in dictation mode, handle dictation-specific commands or capture text
        if (isDictationMode) {
            when {
                lower.contains("stop dictating") || lower.contains("stop dictation") ||
                lower.contains("end dictation") || lower.contains("done dictating") ||
                lower.contains("finish dictating") -> {
                    stopDictation()
                }
                lower.contains("cancel dictation") || lower.contains("cancel dictating") ||
                lower.contains("discard dictation") -> {
                    cancelDictation()
                }
                else -> {
                    // Capture speech to dictation buffer
                    addToDictationBuffer(transcript)
                }
            }
            startVoiceRecognition()
            return
        }

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
            lower.contains("push note") || lower.contains("send to ehr") || lower.contains("push to ehr") || lower.contains("upload note") -> {
                // Voice command to push saved note to EHR
                pushNoteToEhr()
            }
            lower.contains("reset note") || lower.contains("undo changes") || lower.contains("undo edit") || lower.contains("restore note") -> {
                // Voice command to reset edited note to original
                resetNoteEdits()
            }
            lower.contains("edit note") || lower.contains("modify note") -> {
                // Voice command to focus on note editing (bring up keyboard)
                focusNoteEdit()
            }
            // Voice Note Editing Commands
            (lower.contains("change") || lower.contains("set")) &&
                (lower.contains("subjective") || lower.contains("objective") ||
                 lower.contains("assessment") || lower.contains("plan") ||
                 lower.contains("chief complaint") || lower.contains("diagnosis")) &&
                lower.contains(" to ") -> {
                // "Change assessment to viral URI", "Set plan to follow up in 1 week"
                val section = extractSectionFromCommand(lower)
                val content = extractContentAfter(transcript, " to ")
                if (section != null && content.isNotEmpty()) {
                    updateNoteSection(section, content)
                } else {
                    Toast.makeText(this, "Say: change [section] to [content]", Toast.LENGTH_SHORT).show()
                }
            }
            (lower.contains("add to") || lower.contains("append to") || lower.contains("include in")) &&
                (lower.contains("subjective") || lower.contains("objective") ||
                 lower.contains("assessment") || lower.contains("plan")) -> {
                // "Add to plan: order CBC", "Append to assessment: rule out strep"
                val section = extractSectionFromCommand(lower)
                // Extract content after colon or after the section name
                val content = if (transcript.contains(":")) {
                    transcript.substringAfter(":").trim()
                } else {
                    extractContentAfter(transcript, section ?: "")
                }
                if (section != null && content.isNotEmpty()) {
                    appendToNoteSection(section, content)
                } else {
                    Toast.makeText(this, "Say: add to [section]: [content]", Toast.LENGTH_SHORT).show()
                }
            }
            lower.contains("delete last sentence") || lower.contains("remove last sentence") -> {
                deleteLastSentence()
            }
            lower.contains("delete last line") || lower.contains("remove last line") -> {
                deleteLastLine()
            }
            lower.contains("delete") && lower.contains("item") && Regex("\\d+").containsMatchIn(lower) -> {
                // "Delete plan item 2", "Remove assessment item 1"
                val section = extractSectionFromCommand(lower)
                val itemMatch = Regex("\\d+").find(lower)
                if (section != null && itemMatch != null) {
                    val itemNumber = itemMatch.value.toIntOrNull() ?: 0
                    deleteSectionItem(section, itemNumber)
                }
            }
            lower.contains("clear") && (lower.contains("subjective") || lower.contains("objective") ||
                lower.contains("assessment") || lower.contains("plan")) -> {
                // "Clear assessment", "Clear plan"
                val section = extractSectionFromCommand(lower)
                if (section != null) {
                    clearSection(section)
                }
            }
            lower.contains("insert") && lower.contains("normal") && lower.contains("exam") -> {
                insertMacro("normal_exam")
            }
            lower.contains("insert") && lower.contains("normal") && lower.contains("vital") -> {
                insertMacro("normal_vitals")
            }
            lower.contains("insert") && (lower.contains("negative ros") || lower.contains("negative review")) -> {
                insertMacro("negative_ros")
            }
            lower.contains("insert") && lower.contains("follow") && lower.contains("up") -> {
                insertMacro("follow_up")
            }
            lower.contains("insert") && lower.contains("diabetes") -> {
                insertMacro("diabetes_followup")
            }
            lower.contains("insert") && lower.contains("hypertension") -> {
                insertMacro("hypertension_followup")
            }
            lower == "undo" || lower.contains("undo last") || lower.contains("undo change") -> {
                undoLastEdit()
            }
            lower.contains("live transcri") || lower.contains("start transcri") || lower.contains("transcribe") -> {
                // Voice command to start/stop live transcription
                toggleLiveTranscription()
            }
            lower.contains("stop transcri") -> {
                // Voice command to stop live transcription
                if (isLiveTranscribing) stopLiveTranscription()
            }
            // Transcript preview voice commands
            lower.contains("generate note") || lower.contains("create note") || lower.contains("looks good") || lower.contains("that's good") -> {
                // Generate note from pending transcript
                pendingTranscript?.let { pending ->
                    hideDataOverlay()
                    generateClinicalNote(pending)
                    pendingTranscript = null
                } ?: run {
                    transcriptText.text = "No transcript to generate from"
                }
            }
            lower.contains("re-record") || lower.contains("rerecord") || lower.contains("record again") || lower.contains("try again") -> {
                // Start new transcription (discard current)
                pendingTranscript = null
                hideDataOverlay()
                toggleLiveTranscription()
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
            lower.contains("condition") || lower.contains("problem") || lower.contains("diagnosis") || lower.contains("diagnoses") -> {
                // Show conditions/problems
                fetchPatientSection("conditions")
            }
            lower.contains("care plan") || lower.contains("treatment plan") || lower.contains("care plans") -> {
                // Show care plans
                fetchPatientSection("care_plans")
            }
            lower.contains("clinical note") || lower.contains("show notes") || lower.contains("patient notes") || lower.contains("previous notes") || lower.contains("history notes") -> {
                // Show clinical notes from EHR
                fetchPatientSection("clinical_notes")
            }
            lower == "help" || lower.contains("what can i say") || lower.contains("voice commands") || lower.contains("show commands") || lower.contains("list commands") || lower.contains("available commands") -> {
                // Show voice command help
                showVoiceCommandHelp()
            }
            // Patient summary commands - spoken and visual
            lower.contains("tell me about") || lower.contains("read summary") || lower.contains("speak summary") ||
            lower.contains("brief me") || lower.contains("briefing") || lower.contains("tell me about patient") -> {
                // Hands-free spoken summary while walking to patient
                speakPatientSummary()
            }
            lower.contains("patient summary") || lower.contains("summarize patient") || lower.contains("quick summary") ||
            lower.contains("show summary") || lower.contains("overview") -> {
                // Show visual summary (no TTS)
                showQuickPatientSummary()
            }
            lower.contains("stop talking") || lower.contains("stop speaking") || lower.contains("be quiet") || lower.contains("quiet") -> {
                // Stop any ongoing TTS
                stopSpeaking()
                transcriptText.text = "Speech stopped"
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
            // Patient history voice commands
            lower.contains("show history") || lower.contains("recent patients") || lower.contains("patient history") -> {
                showHistoryOverlay()
            }
            lower.contains("clear history") -> {
                clearPatientHistory()
                hideDataOverlay()
            }
            // Session timeout voice commands (HIPAA compliance)
            lower.contains("lock session") || lower == "lock" -> {
                lockSession()
            }
            lower.contains("unlock") -> {
                if (isSessionLocked) {
                    unlockSession()
                } else {
                    Toast.makeText(this, "Session is not locked", Toast.LENGTH_SHORT).show()
                }
            }
            lower.contains("timeout") && Regex("(\\d+)\\s*min").containsMatchIn(lower) -> {
                // Set timeout: "timeout 10 minutes", "set timeout 5 min"
                val match = Regex("(\\d+)\\s*min").find(lower)
                if (match != null) {
                    val minutes = match.groupValues[1].toIntOrNull() ?: DEFAULT_SESSION_TIMEOUT_MINUTES
                    setSessionTimeout(minutes)
                }
            }
            lower.contains("load ") && Regex("load\\s+(\\d+)").containsMatchIn(lower) -> {
                // Load patient from history by number (e.g., "load 1", "load 2")
                val match = Regex("load\\s+(\\d+)").find(lower)
                if (match != null) {
                    val index = match.groupValues[1].toIntOrNull() ?: 0
                    loadPatientFromHistory(index)
                }
            }
            // Voice Navigation Commands
            lower.contains("scroll down") || lower.contains("page down") || lower.contains("next page") -> {
                scrollDown()
            }
            lower.contains("scroll up") || lower.contains("page up") || lower.contains("previous page") -> {
                scrollUp()
            }
            lower.contains("go to top") || lower.contains("scroll to top") || lower.contains("top of page") -> {
                scrollToTop()
            }
            lower.contains("go to bottom") || lower.contains("scroll to bottom") || lower.contains("bottom of page") -> {
                scrollToBottom()
            }
            (lower.contains("go to") || lower.contains("jump to") || lower.contains("navigate to")) &&
                (lower.contains("subjective") || lower.contains("objective") ||
                 lower.contains("assessment") || lower.contains("plan") ||
                 lower.contains("chief complaint")) -> {
                // Navigate to specific section: "go to assessment", "jump to plan"
                val section = extractSectionFromCommand(lower)
                if (section != null) {
                    goToSection(section)
                }
            }
            lower.contains("show") && lower.contains("only") &&
                (lower.contains("subjective") || lower.contains("objective") ||
                 lower.contains("assessment") || lower.contains("plan")) -> {
                // Show only one section: "show plan only", "show assessment only"
                val section = extractSectionFromCommand(lower)
                if (section != null) {
                    showSectionOnly(section)
                }
            }
            (lower.contains("read") || lower.contains("read back") || lower.contains("say")) &&
                (lower.contains("subjective") || lower.contains("objective") ||
                 lower.contains("assessment") || lower.contains("plan") ||
                 lower.contains("chief complaint")) -> {
                // Read a section aloud: "read assessment", "read back the plan"
                val section = extractSectionFromCommand(lower)
                if (section != null) {
                    readSection(section)
                }
            }
            lower.contains("read note") || lower.contains("read entire note") || lower.contains("read the note") || lower.contains("read all") -> {
                // Read entire note aloud
                readEntireNote()
            }
            // Voice Dictation Mode Commands
            (lower.contains("dictate to") || lower.contains("dictate into") || lower.contains("start dictating")) &&
                (lower.contains("subjective") || lower.contains("objective") ||
                 lower.contains("assessment") || lower.contains("plan") ||
                 lower.contains("chief complaint") || lower.contains("history")) -> {
                // Start dictation to a specific section: "dictate to assessment", "start dictating subjective"
                val section = extractSectionFromCommand(lower)
                if (section != null) {
                    startDictation(section)
                } else {
                    Toast.makeText(this, "Say: dictate to [section]", Toast.LENGTH_SHORT).show()
                }
            }
            lower == "dictate" || lower.contains("start dictation") -> {
                // Start dictation to default section (plan is most common for orders)
                Toast.makeText(this, "Say 'dictate to [section]' (e.g., 'dictate to plan')", Toast.LENGTH_LONG).show()
                speakFeedback("Say dictate to and the section name. For example, dictate to plan.")
            }
            // Offline note drafts voice commands
            lower.contains("sync notes") || lower.contains("sync drafts") || lower.contains("upload drafts") -> {
                val draftCount = getPendingDraftCount()
                if (draftCount > 0) {
                    if (isNetworkAvailable()) {
                        syncPendingDrafts()
                    } else {
                        Toast.makeText(this, "No network - cannot sync", Toast.LENGTH_SHORT).show()
                        speakFeedback("No network connection. Cannot sync drafts.")
                    }
                } else {
                    Toast.makeText(this, "No pending drafts", Toast.LENGTH_SHORT).show()
                }
            }
            lower.contains("show drafts") || lower.contains("view drafts") || lower.contains("pending notes") || lower.contains("pending drafts") -> {
                showPendingDraftsOverlay()
            }
            lower.contains("delete draft") -> {
                // Extract draft number from command
                val match = Regex("\\d+").find(lower)
                if (match != null) {
                    val draftIndex = match.value.toIntOrNull()?.minus(1) ?: -1
                    val drafts = getPendingDrafts()
                    if (draftIndex in drafts.indices) {
                        val draftId = drafts[draftIndex].optString("draft_id")
                        deleteDraft(draftId)
                        Toast.makeText(this, "Draft ${draftIndex + 1} deleted", Toast.LENGTH_SHORT).show()
                        speakFeedback("Draft deleted")
                    } else {
                        Toast.makeText(this, "Invalid draft number", Toast.LENGTH_SHORT).show()
                    }
                } else {
                    showPendingDraftsOverlay()
                    transcriptText.text = "Say 'delete draft [number]'"
                }
            }
            lower.contains("view draft") && Regex("\\d+").containsMatchIn(lower) -> {
                // View specific draft by number
                val match = Regex("\\d+").find(lower)
                if (match != null) {
                    val draftIndex = match.value.toIntOrNull()?.minus(1) ?: -1
                    val drafts = getPendingDrafts()
                    if (draftIndex in drafts.indices) {
                        showDraftDetails(drafts[draftIndex])
                    } else {
                        Toast.makeText(this, "Invalid draft number", Toast.LENGTH_SHORT).show()
                    }
                }
            }
            lower.contains("increase font") || lower.contains("bigger font") || lower.contains("larger font") || lower.contains("font bigger") || lower.contains("font larger") -> {
                // Voice command to increase font size
                increaseFontSize()
            }
            lower.contains("decrease font") || lower.contains("smaller font") || lower.contains("font smaller") -> {
                // Voice command to decrease font size
                decreaseFontSize()
            }
            lower.contains("font small") && !lower.contains("smaller") -> {
                setFontSize(FONT_SIZE_SMALL)
            }
            lower.contains("font medium") -> {
                setFontSize(FONT_SIZE_MEDIUM)
            }
            lower.contains("font large") && !lower.contains("larger") -> {
                setFontSize(FONT_SIZE_LARGE)
            }
            lower.contains("font extra large") || lower.contains("extra large font") -> {
                setFontSize(FONT_SIZE_EXTRA_LARGE)
            }
            lower.contains("auto scroll on") || lower.contains("enable auto scroll") || lower.contains("scroll on") -> {
                enableAutoScroll()
            }
            lower.contains("auto scroll off") || lower.contains("disable auto scroll") || lower.contains("scroll off") -> {
                disableAutoScroll()
            }
            lower.contains("toggle scroll") || lower.contains("toggle auto scroll") -> {
                toggleAutoScroll()
            }
            // Speech feedback toggle
            lower.contains("speech feedback") || lower.contains("voice feedback") || lower.contains("audio feedback") ||
            lower.contains("toggle feedback") || lower.contains("mute feedback") || lower.contains("unmute feedback") -> {
                toggleSpeechFeedback()
            }
            // Note type selection voice commands
            lower.contains("soap note") || lower.contains("note type soap") -> {
                setNoteType("SOAP")
            }
            lower.contains("progress note") || lower.contains("note type progress") -> {
                setNoteType("PROGRESS")
            }
            lower.contains("h&p note") || lower.contains("hp note") || lower.contains("history and physical") || lower.contains("note type hp") -> {
                setNoteType("HP")
            }
            lower.contains("consult note") || lower.contains("consultation note") || lower.contains("note type consult") -> {
                setNoteType("CONSULT")
            }
            lower.contains("auto note") || lower.contains("auto detect") || lower.contains("automatic note") || lower.contains("note type auto") -> {
                setNoteType("AUTO")
            }
            // Set clinician name: "my name is Dr. Smith" or "I am Dr. Jones" or "clinician name Dr. Brown"
            lower.contains("my name is") || lower.contains("i am dr") || lower.contains("clinician name") -> {
                // Extract name from transcript
                val name = when {
                    lower.contains("my name is") -> transcript.substringAfter("my name is", "").trim()
                    lower.contains("i am dr") -> "Dr." + transcript.substringAfter("i am dr", "").substringAfter("I am Dr", "").trim()
                    lower.contains("clinician name") -> transcript.substringAfter("clinician name", "").trim()
                    else -> ""
                }.replace(Regex("^\\s*\\.\\s*"), "").trim()
                if (name.isNotEmpty()) {
                    setClinicianName(name)
                } else {
                    transcriptText.text = "Say: My name is Dr. [Name]"
                }
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
                "conditions" -> formatConditions(patient)
                "care_plans" -> formatCarePlans(patient)
                "clinical_notes" -> formatClinicalNotes(patient)
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
                                    "conditions" -> formatConditions(patient)
                                    "care_plans" -> formatCarePlans(patient)
                                    "clinical_notes" -> formatClinicalNotes(patient)
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
        if (vitals.length() == 0) return "No vitals available"

        val sb = StringBuilder()

        // Show critical vitals warning first if any
        val criticalVitals = patient.optJSONArray("critical_vitals")
        if (criticalVitals != null && criticalVitals.length() > 0) {
            sb.append("🚨 CRITICAL VITALS\n${"─".repeat(30)}\n")
            for (i in 0 until criticalVitals.length()) {
                val v = criticalVitals.getJSONObject(i)
                val interp = v.optString("interpretation", "")
                val flag = if (interp == "HH" || interp == "LL") "‼️" else "⚠️"
                sb.append("$flag ${v.getString("name")}: ${v.getString("value")} ${v.optString("unit", "")}")
                if (interp.isNotEmpty()) sb.append(" [$interp]")
                sb.append("\n")
            }
            sb.append("${"─".repeat(30)}\n\n")
        }

        sb.append("VITALS\n${"─".repeat(30)}\n")
        for (i in 0 until minOf(vitals.length(), 8)) {
            val v = vitals.getJSONObject(i)
            val interp = v.optString("interpretation", "")
            val isCritical = v.optBoolean("is_critical", false)
            val isAbnormal = v.optBoolean("is_abnormal", false)
            val trend = v.optString("trend", "")
            val delta = v.optString("delta", "")

            // Add interpretation flag
            val flag = when {
                interp == "HH" || interp == "LL" -> "‼️"
                interp == "H" -> "↑"
                interp == "L" -> "↓"
                isCritical -> "‼️"
                isAbnormal -> "⚠"
                else -> "•"
            }

            // Trend indicator
            val trendIcon = when (trend) {
                "rising" -> " ↗️"
                "falling" -> " ↘️"
                "stable" -> " →"
                "new" -> " 🆕"
                else -> ""
            }

            // Delta display
            val deltaStr = if (delta.isNotEmpty()) " ($delta)" else ""

            sb.append("$flag ${v.getString("name")}: ${v.getString("value")}${v.optString("unit", "")}$trendIcon$deltaStr")
            if (interp.isNotEmpty() && interp != "N") sb.append(" [$interp]")
            sb.append("\n")
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
        val interactions = patient.optJSONArray("medication_interactions")

        val sb = StringBuilder()

        // Show drug interactions warning first if any
        if (interactions != null && interactions.length() > 0) {
            sb.append("⚠️ DRUG INTERACTIONS\n${"─".repeat(30)}\n")
            for (i in 0 until minOf(interactions.length(), 5)) {
                val inter = interactions.getJSONObject(i)
                val drug1 = inter.optString("drug1", "").split(" ").firstOrNull() ?: "Drug1"
                val drug2 = inter.optString("drug2", "").split(" ").firstOrNull() ?: "Drug2"
                val severity = inter.optString("severity", "moderate")
                val effect = inter.optString("effect", "Potential interaction")
                val shortEffect = effect.split(" - ").firstOrNull()?.take(40) ?: effect.take(40)

                val flag = when (severity) {
                    "high" -> "🔴"
                    "moderate" -> "🟡"
                    else -> "🟢"
                }
                sb.append("$flag $drug1 + $drug2\n")
                sb.append("   $shortEffect\n")
            }
            sb.append("${"─".repeat(30)}\n\n")
        }

        sb.append("💊 MEDICATIONS\n${"─".repeat(30)}\n")
        for (i in 0 until minOf(meds.length(), 8)) {
            sb.append("• ${meds.getString(i)}\n")
        }
        return sb.toString()
    }

    private fun formatLabs(patient: JSONObject): String {
        val labs = patient.optJSONArray("labs") ?: return "No lab results"
        if (labs.length() == 0) return "No lab results available"

        val sb = StringBuilder()

        // Show critical labs warning first if any
        val criticalLabs = patient.optJSONArray("critical_labs")
        if (criticalLabs != null && criticalLabs.length() > 0) {
            sb.append("🚨 CRITICAL LABS\n${"─".repeat(30)}\n")
            for (i in 0 until criticalLabs.length()) {
                val l = criticalLabs.getJSONObject(i)
                val interp = l.optString("interpretation", "")
                val flag = if (interp == "HH" || interp == "LL") "‼️" else "⚠️"
                val refRange = l.optString("reference_range", "")
                sb.append("$flag ${l.getString("name")}: ${l.getString("value")} ${l.optString("unit", "")}")
                if (interp.isNotEmpty()) sb.append(" [$interp]")
                if (refRange.isNotEmpty()) sb.append(" (ref: $refRange)")
                sb.append("\n")
            }
            sb.append("${"─".repeat(30)}\n\n")
        }

        sb.append("🔬 LAB RESULTS\n${"─".repeat(30)}\n")
        for (i in 0 until minOf(labs.length(), 10)) {
            val l = labs.getJSONObject(i)
            val interp = l.optString("interpretation", "")
            val isCritical = l.optBoolean("is_critical", false)
            val isAbnormal = l.optBoolean("is_abnormal", false)
            val trend = l.optString("trend", "")
            val delta = l.optString("delta", "")

            // Add interpretation flag
            val flag = when {
                interp == "HH" || interp == "LL" -> "‼️"
                interp == "H" -> "↑"
                interp == "L" -> "↓"
                isCritical -> "‼️"
                isAbnormal -> "⚠"
                else -> "•"
            }

            // Trend indicator
            val trendIcon = when (trend) {
                "rising" -> " ↗️"
                "falling" -> " ↘️"
                "stable" -> " →"
                "new" -> " 🆕"
                else -> ""
            }

            // Delta display
            val deltaStr = if (delta.isNotEmpty()) " ($delta)" else ""

            sb.append("$flag ${l.getString("name")}: ${l.getString("value")}${l.optString("unit", "")}$trendIcon$deltaStr")
            if (interp.isNotEmpty() && interp != "N") sb.append(" [$interp]")
            sb.append("\n")
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

    private fun formatConditions(patient: JSONObject): String {
        val conds = patient.optJSONArray("conditions") ?: return "No conditions recorded"
        if (conds.length() == 0) return "No conditions/problems recorded"
        val sb = StringBuilder("📋 CONDITIONS/PROBLEMS\n${"─".repeat(30)}\n")
        for (i in 0 until minOf(conds.length(), 10)) {
            val cond = conds.getJSONObject(i)
            sb.append("• ${cond.getString("name")}")
            val status = cond.optString("status", "")
            if (status.isNotEmpty()) sb.append(" [$status]")
            val onset = cond.optString("onset", "")
            if (onset.isNotEmpty()) sb.append(" (since $onset)")
            sb.append("\n")
        }
        return sb.toString()
    }

    private fun formatCarePlans(patient: JSONObject): String {
        val plans = patient.optJSONArray("care_plans") ?: return "No care plans recorded"
        if (plans.length() == 0) return "No care plans recorded"
        val sb = StringBuilder("📑 CARE PLANS\n${"─".repeat(30)}\n")
        for (i in 0 until minOf(plans.length(), 10)) {
            val plan = plans.getJSONObject(i)
            sb.append("• ${plan.getString("title")}")
            val status = plan.optString("status", "")
            if (status.isNotEmpty()) sb.append(" [$status]")
            val intent = plan.optString("intent", "")
            if (intent.isNotEmpty()) sb.append(" ($intent)")
            sb.append("\n")
            // Show period if available
            val periodStart = plan.optString("period_start", "")
            val periodEnd = plan.optString("period_end", "")
            if (periodStart.isNotEmpty() || periodEnd.isNotEmpty()) {
                sb.append("  Period: ${periodStart.ifEmpty { "?" }} → ${periodEnd.ifEmpty { "ongoing" }}\n")
            }
            // Show description if available
            val description = plan.optString("description", "")
            if (description.isNotEmpty()) {
                sb.append("  ${description.take(100)}${if (description.length > 100) "..." else ""}\n")
            }
        }
        return sb.toString()
    }

    private fun formatClinicalNotes(patient: JSONObject): String {
        val notes = patient.optJSONArray("clinical_notes") ?: return "No clinical notes found"
        if (notes.length() == 0) return "No clinical notes found"
        val sb = StringBuilder("📄 CLINICAL NOTES\n${"─".repeat(30)}\n")
        for (i in 0 until minOf(notes.length(), 10)) {
            val note = notes.getJSONObject(i)
            sb.append("• ${note.getString("title")}")
            val docType = note.optString("doc_type", "")
            if (docType.isNotEmpty() && docType != note.getString("title")) {
                sb.append(" ($docType)")
            }
            sb.append("\n")
            // Show date and author
            val date = note.optString("date", "")
            val author = note.optString("author", "")
            if (date.isNotEmpty() || author.isNotEmpty()) {
                sb.append("  ")
                if (date.isNotEmpty()) sb.append("Date: $date")
                if (date.isNotEmpty() && author.isNotEmpty()) sb.append(" | ")
                if (author.isNotEmpty()) sb.append("By: $author")
                sb.append("\n")
            }
            // Show status
            val status = note.optString("status", "")
            if (status.isNotEmpty()) {
                sb.append("  Status: $status\n")
            }
            // Show content preview if available
            val preview = note.optString("content_preview", "")
            if (preview.isNotEmpty()) {
                sb.append("  ${preview.take(100)}${if (preview.length > 100) "..." else ""}\n")
            }
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

    override fun onResume() {
        super.onResume()
        // Update activity on resume and restart timeout checker
        updateLastActivity()
        if (sessionCheckHandler == null) {
            startSessionTimeoutChecker()
        }
    }

    override fun onPause() {
        super.onPause()
        // Stop timeout checker when app is in background
        stopSessionTimeoutChecker()
    }

    override fun onDestroy() {
        super.onDestroy()
        if (::speechRecognizer.isInitialized) {
            speechRecognizer.destroy()
        }
        // Clean up audio streaming service
        audioStreamingService?.destroy()
        // Clean up Text-to-Speech
        textToSpeech?.stop()
        textToSpeech?.shutdown()
        // Clean up network callback
        unregisterNetworkCallback()
        // Clean up session timeout checker
        stopSessionTimeoutChecker()
    }

    override fun dispatchTouchEvent(ev: android.view.MotionEvent?): Boolean {
        // Update activity on any touch event
        updateLastActivity()
        return super.dispatchTouchEvent(ev)
    }
}
