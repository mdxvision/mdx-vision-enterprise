package com.mdxvision.rayban

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Bundle
import android.provider.MediaStore
import android.speech.tts.TextToSpeech
import android.util.Log
import android.widget.Button
import android.widget.TextView
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import kotlinx.coroutines.*
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.io.IOException
import java.util.Locale
import java.util.concurrent.TimeUnit

/**
 * MDx Vision - Ray-Ban Meta Companion App (Feature #87)
 *
 * This app runs on the phone and connects to Ray-Ban Meta glasses via the
 * Meta Wearables Device Access Toolkit. It provides:
 *
 * 1. Voice command processing from glasses microphone
 * 2. Patient data display on glasses HUD
 * 3. AI Clinical Co-pilot integration
 * 4. Health equity features (SDOH, Literacy, Interpreter)
 * 5. Medical image capture and analysis
 * 6. TTS feedback through glasses speakers
 *
 * Architecture:
 * - Glasses (mic/camera/display) ←→ Phone (this app) ←→ EHR Proxy (backend)
 */
class RayBanCompanionActivity : AppCompatActivity(), TextToSpeech.OnInitListener {

    companion object {
        private const val TAG = "RayBanCompanion"
        private const val EHR_PROXY_URL = "http://10.0.2.2:8002"  // Host machine from emulator
        private const val PERMISSION_REQUEST_CODE = 1001
    }

    // UI Elements
    private lateinit var statusText: TextView
    private lateinit var transcriptText: TextView
    private lateinit var patientDataText: TextView
    private lateinit var glassesStatusText: TextView
    private lateinit var glassesDisplayText: TextView
    private lateinit var connectButton: Button
    private lateinit var streamButton: Button

    // Network
    private val httpClient = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(60, TimeUnit.SECONDS)
        .writeTimeout(30, TimeUnit.SECONDS)
        .build()

    // Coroutine scope
    private val scope = CoroutineScope(Dispatchers.Main + Job())

    // State
    private var isGlassesConnected = false
    private var isStreaming = false
    private var currentPatientId: String? = null
    private var currentPatientData: JSONObject? = null

    // Text-to-Speech for audio feedback through glasses
    private var tts: TextToSpeech? = null
    private var isTtsReady = false

    // Documentation mode
    private var isDocumenting = false
    private val noteBuffer = StringBuilder()

    // AI Copilot
    private var copilotHistory: MutableList<Pair<String, String>> = mutableListOf()
    private var isCopilotActive = false

    // Health Equity State
    private var patientLiteracyLevel: String = "adequate"
    private var patientPreferredLanguage: String? = null
    private var patientPreferredLanguageName: String? = null
    private var interpreterRequired = false
    private var sdohFactors: MutableList<String> = mutableListOf()

    // Camera for image capture
    private val cameraLauncher = registerForActivityResult(
        ActivityResultContracts.TakePicture()
    ) { success ->
        if (success) {
            currentImageUri?.let { analyzeImage(it) }
        }
    }
    private var currentImageUri: android.net.Uri? = null
    private var imageAnalysisContext: String = "general"

    // ═══════════════════════════════════════════════════════════════════════════
    // LIFECYCLE
    // ═══════════════════════════════════════════════════════════════════════════

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        initializeViews()
        initializeTts()
        requestPermissions()
    }

    override fun onDestroy() {
        super.onDestroy()
        scope.cancel()
        tts?.shutdown()
        disconnectGlasses()
    }

    private fun initializeViews() {
        statusText = findViewById(R.id.statusText)
        transcriptText = findViewById(R.id.transcriptText)
        patientDataText = findViewById(R.id.patientDataText)
        glassesStatusText = findViewById(R.id.glassesStatusText)
        glassesDisplayText = findViewById(R.id.glassesDisplayText)
        connectButton = findViewById(R.id.connectButton)
        streamButton = findViewById(R.id.streamButton)

        connectButton.setOnClickListener { connectToGlasses() }
        streamButton.setOnClickListener { toggleAudioStreaming() }
    }

    private fun initializeTts() {
        tts = TextToSpeech(this, this)
    }

    override fun onInit(status: Int) {
        if (status == TextToSpeech.SUCCESS) {
            val result = tts?.setLanguage(Locale.US)
            isTtsReady = result != TextToSpeech.LANG_MISSING_DATA &&
                         result != TextToSpeech.LANG_NOT_SUPPORTED
            Log.d(TAG, "TTS initialized: $isTtsReady")
        }
    }

    private fun speak(text: String) {
        if (isTtsReady) {
            tts?.speak(text, TextToSpeech.QUEUE_ADD, null, null)
        }
    }

    private fun requestPermissions() {
        val permissions = arrayOf(
            Manifest.permission.RECORD_AUDIO,
            Manifest.permission.BLUETOOTH,
            Manifest.permission.BLUETOOTH_CONNECT,
            Manifest.permission.BLUETOOTH_SCAN,
            Manifest.permission.CAMERA
        )

        val needed = permissions.filter {
            ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED
        }

        if (needed.isNotEmpty()) {
            ActivityCompat.requestPermissions(this, needed.toTypedArray(), PERMISSION_REQUEST_CODE)
        } else {
            onPermissionsGranted()
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
                onPermissionsGranted()
            } else {
                statusText.text = "Status: Permissions required"
                Toast.makeText(this, "Permissions required for glasses connection", Toast.LENGTH_LONG).show()
            }
        }
    }

    private fun onPermissionsGranted() {
        statusText.text = "Status: Ready to connect"
        Log.d(TAG, "Permissions granted, ready to connect to glasses")
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // META WEARABLES SDK INTEGRATION
    // ═══════════════════════════════════════════════════════════════════════════

    private fun connectToGlasses() {
        statusText.text = "Status: Connecting to glasses..."
        Log.d(TAG, "Attempting to connect to Ray-Ban Meta glasses")

        // TODO: Replace with actual Meta SDK calls when integrated
        // Simulated connection for testing without actual glasses
        simulateGlassesConnection()
    }

    private fun simulateGlassesConnection() {
        scope.launch {
            delay(1500)
            isGlassesConnected = true
            updateGlassesStatus(true)
            statusText.text = "Status: Connected"
            streamButton.isEnabled = true
            connectButton.text = "Disconnect"
            speak("Glasses connected. Say Hey M D X to activate.")
            Toast.makeText(this@RayBanCompanionActivity,
                "Connected (simulated - SDK not integrated)",
                Toast.LENGTH_SHORT).show()
        }
    }

    private fun disconnectGlasses() {
        if (isGlassesConnected) {
            isGlassesConnected = false
            isStreaming = false
            updateGlassesStatus(false)
            streamButton.isEnabled = false
            connectButton.text = "Connect"
        }
    }

    private fun updateGlassesStatus(connected: Boolean) {
        runOnUiThread {
            if (connected) {
                glassesStatusText.text = "👓 Glasses: Connected"
                glassesStatusText.setTextColor(getColor(R.color.success_green))
            } else {
                glassesStatusText.text = "👓 Glasses: Not Connected"
                glassesStatusText.setTextColor(getColor(R.color.warning_orange))
            }
        }
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // AUDIO STREAMING
    // ═══════════════════════════════════════════════════════════════════════════

    private fun toggleAudioStreaming() {
        if (!isGlassesConnected) {
            Toast.makeText(this, "Connect to glasses first", Toast.LENGTH_SHORT).show()
            return
        }

        if (isStreaming) {
            stopAudioStreaming()
        } else {
            startAudioStreaming()
        }
    }

    private fun startAudioStreaming() {
        isStreaming = true
        statusText.text = "Status: Streaming audio..."
        streamButton.text = "Stop Voice"
        Log.d(TAG, "Starting audio stream from glasses")
        sendToGlassesDisplay("🎤 Listening...\nSay a command")

        // Simulated transcription for testing
        simulateTranscription()
    }

    private fun stopAudioStreaming() {
        isStreaming = false
        statusText.text = "Status: Connected"
        streamButton.text = "Start Voice"
        Log.d(TAG, "Stopped audio stream")
    }

    private fun simulateTranscription() {
        val sampleCommands = listOf(
            "Hey MDx",
            "Load patient Smith",
            "Show vitals",
            "Show allergies",
            "Copilot what should I consider for chest pain",
            "Start note",
            "Patient presents with chest pain and shortness of breath",
            "Stop note"
        )

        scope.launch {
            for (command in sampleCommands) {
                if (!isStreaming) break
                delay(3000)
                updateTranscript(command)
                processVoiceCommand(command)
            }
        }
    }

    private fun updateTranscript(text: String) {
        runOnUiThread {
            val current = transcriptText.text.toString()
            if (current == "(waiting for audio...)") {
                transcriptText.text = text
            } else {
                transcriptText.text = "$current\n$text"
            }
        }
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // VOICE COMMAND PROCESSING
    // ═══════════════════════════════════════════════════════════════════════════

    private fun processVoiceCommand(transcript: String) {
        val lower = transcript.lowercase().trim()
        Log.d(TAG, "Processing command: $lower")

        when {
            // Wake word
            lower.contains("hey mdx") || lower.contains("hey m d x") -> {
                sendToGlassesDisplay("🎤 MDx Vision Active\nListening...")
                speak("M D X Vision active")
            }

            // Patient commands
            lower.contains("load patient") -> {
                val name = lower.substringAfter("load patient").trim()
                loadPatient(name)
            }
            lower.contains("show vitals") -> showVitalsOnGlasses()
            lower.contains("show allergies") -> showAllergiesOnGlasses()
            lower.contains("show meds") || lower.contains("show medications") -> showMedicationsOnGlasses()
            lower.contains("show labs") -> showLabsOnGlasses()

            // AI Copilot
            lower.contains("copilot") || lower.contains("co-pilot") -> {
                val question = lower.substringAfter("copilot").substringAfter("co-pilot").trim()
                askCopilot(question)
            }
            lower.contains("what should i") || lower.contains("what do you think") -> {
                askCopilot(transcript)
            }
            lower.contains("tell me more") || lower.contains("elaborate") -> {
                askCopilotFollowUp("Tell me more about that")
            }

            // Documentation
            lower.contains("start note") -> startDocumentation()
            lower.contains("stop note") || lower.contains("end note") -> stopDocumentation()

            // Vitals capture
            lower.contains("blood pressure") || lower.contains("bp ") -> captureVital("blood_pressure", transcript)
            lower.contains("pulse") || lower.contains("heart rate") -> captureVital("heart_rate", transcript)
            lower.contains("temp") || lower.contains("temperature") -> captureVital("temperature", transcript)
            lower.contains("oxygen") || lower.contains("sat") || lower.contains("spo2") -> captureVital("spo2", transcript)

            // Health Equity - Interpreter Integration
            lower.contains("interpreter") && (lower.contains("need") || lower.contains("request")) -> {
                requestInterpreter()
            }
            lower.contains("spanish interpreter") -> requestInterpreterForLanguage("es", "Spanish")
            lower.contains("chinese interpreter") || lower.contains("mandarin interpreter") -> {
                requestInterpreterForLanguage("zh", "Chinese")
            }
            lower.contains("vietnamese interpreter") -> requestInterpreterForLanguage("vi", "Vietnamese")
            lower.contains("interpreter status") -> showInterpreterStatus()
            lower.contains("clinical phrases") -> showClinicalPhrases()

            // Health Equity - Literacy
            lower.contains("literacy") && (lower.contains("screen") || lower.contains("assess")) -> {
                showLiteracyScreening()
            }
            lower.contains("low literacy") || lower.contains("inadequate literacy") -> {
                setLiteracyLevel("inadequate")
            }
            lower.contains("simplify") && lower.contains("instruction") -> {
                showSimplifiedInstructions()
            }

            // Health Equity - SDOH
            lower.contains("sdoh") || lower.contains("social determinants") -> {
                showSdohStatus()
            }
            lower.contains("food insecurity") -> addSdohFactor("food_insecurity")
            lower.contains("housing") && (lower.contains("unstable") || lower.contains("homeless")) -> {
                addSdohFactor("housing_instability")
            }
            lower.contains("transportation") && lower.contains("barrier") -> {
                addSdohFactor("transportation_barriers")
            }

            // Camera / Image Analysis
            lower.contains("take photo") || lower.contains("capture image") -> {
                captureImage("general")
            }
            lower.contains("analyze wound") -> captureImage("wound")
            lower.contains("analyze rash") -> captureImage("rash")
            lower.contains("analyze xray") || lower.contains("analyze x-ray") -> {
                captureImage("xray")
            }

            // Help
            lower == "help" || lower.contains("what can i say") -> showHelp()

            else -> {
                // If documenting, append to note
                if (isDocumenting) {
                    appendToNote(transcript)
                }
            }
        }
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // GLASSES DISPLAY OUTPUT
    // ═══════════════════════════════════════════════════════════════════════════

    private fun sendToGlassesDisplay(content: String) {
        Log.d(TAG, "Sending to glasses display: $content")

        // TODO: Actual SDK display call when integrated
        // For now, update local UI to show what would be on glasses
        runOnUiThread {
            glassesDisplayText.text = content
        }
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // EHR INTEGRATION
    // ═══════════════════════════════════════════════════════════════════════════

    private fun loadPatient(name: String) {
        if (name.isEmpty()) {
            speak("Please say the patient name")
            return
        }

        statusText.text = "Status: Loading patient..."
        sendToGlassesDisplay("🔍 Searching: $name")
        speak("Searching for patient $name")

        scope.launch(Dispatchers.IO) {
            try {
                val request = Request.Builder()
                    .url("$EHR_PROXY_URL/api/v1/patient/search?name=$name")
                    .get()
                    .build()

                val response = httpClient.newCall(request).execute()
                val responseBody = response.body?.string() ?: "[]"
                val patients = JSONArray(responseBody)

                withContext(Dispatchers.Main) {
                    if (patients.length() > 0) {
                        val patient = patients.getJSONObject(0)
                        currentPatientId = patient.optString("patient_id")
                        loadPatientDetails(currentPatientId!!)
                    } else {
                        sendToGlassesDisplay("❌ Patient not found: $name")
                        speak("Patient not found")
                        statusText.text = "Status: Patient not found"
                    }
                }
            } catch (e: Exception) {
                Log.e(TAG, "Error loading patient: ${e.message}")
                withContext(Dispatchers.Main) {
                    sendToGlassesDisplay("❌ Error loading patient")
                    speak("Error loading patient")
                }
            }
        }
    }

    private fun loadPatientDetails(patientId: String) {
        scope.launch(Dispatchers.IO) {
            try {
                val request = Request.Builder()
                    .url("$EHR_PROXY_URL/api/v1/patient/$patientId")
                    .get()
                    .build()

                val response = httpClient.newCall(request).execute()
                val responseBody = response.body?.string() ?: "{}"
                currentPatientData = JSONObject(responseBody)

                withContext(Dispatchers.Main) {
                    val name = currentPatientData?.optString("name", "Unknown")
                    val dob = currentPatientData?.optString("date_of_birth", "")
                    val allergies = currentPatientData?.optJSONArray("allergies")

                    var displayText = "👤 $name\n📅 DOB: $dob"

                    // Show critical allergies
                    if (allergies != null && allergies.length() > 0) {
                        displayText += "\n⚠️ ALLERGIES:"
                        val allergyNames = mutableListOf<String>()
                        for (i in 0 until minOf(allergies.length(), 3)) {
                            val allergy = allergies.getJSONObject(i)
                            val substance = allergy.optString("substance")
                            allergyNames.add(substance)
                            displayText += "\n  • $substance"
                        }
                        // Speak allergies
                        speak("Patient $name loaded. Allergies: ${allergyNames.joinToString(", ")}")
                    } else {
                        speak("Patient $name loaded. No known allergies.")
                    }

                    sendToGlassesDisplay(displayText)
                    patientDataText.text = displayText
                    statusText.text = "Status: Patient loaded"
                }
            } catch (e: Exception) {
                Log.e(TAG, "Error loading patient details: ${e.message}")
            }
        }
    }

    private fun showVitalsOnGlasses() {
        val vitals = currentPatientData?.optJSONArray("vitals")
        if (vitals == null || vitals.length() == 0) {
            sendToGlassesDisplay("📊 No vitals available")
            speak("No vitals available")
            return
        }

        val sb = StringBuilder("📊 VITALS:\n")
        for (i in 0 until minOf(vitals.length(), 5)) {
            val vital = vitals.getJSONObject(i)
            sb.append("${vital.optString("type")}: ${vital.optString("value")}\n")
        }
        sendToGlassesDisplay(sb.toString())
        speak("Vitals displayed")
    }

    private fun showAllergiesOnGlasses() {
        val allergies = currentPatientData?.optJSONArray("allergies")
        if (allergies == null || allergies.length() == 0) {
            sendToGlassesDisplay("💊 No known allergies")
            speak("No known allergies")
            return
        }

        val sb = StringBuilder("⚠️ ALLERGIES:\n")
        val allergyList = mutableListOf<String>()
        for (i in 0 until allergies.length()) {
            val allergy = allergies.getJSONObject(i)
            val substance = allergy.optString("substance")
            allergyList.add(substance)
            sb.append("• $substance")
            val severity = allergy.optString("severity", "")
            if (severity.isNotEmpty()) {
                sb.append(" ($severity)")
            }
            sb.append("\n")
        }
        sendToGlassesDisplay(sb.toString())
        speak("Allergies: ${allergyList.joinToString(", ")}")
    }

    private fun showMedicationsOnGlasses() {
        val meds = currentPatientData?.optJSONArray("medications")
        if (meds == null || meds.length() == 0) {
            sendToGlassesDisplay("💊 No active medications")
            speak("No active medications")
            return
        }

        val sb = StringBuilder("💊 MEDICATIONS:\n")
        for (i in 0 until minOf(meds.length(), 5)) {
            val med = meds.getJSONObject(i)
            sb.append("• ${med.optString("name")}\n")
        }
        if (meds.length() > 5) {
            sb.append("... +${meds.length() - 5} more")
        }
        sendToGlassesDisplay(sb.toString())
        speak("${meds.length()} active medications")
    }

    private fun showLabsOnGlasses() {
        val labs = currentPatientData?.optJSONArray("labs")
        if (labs == null || labs.length() == 0) {
            sendToGlassesDisplay("🔬 No recent labs")
            speak("No recent labs")
            return
        }

        val sb = StringBuilder("🔬 RECENT LABS:\n")
        for (i in 0 until minOf(labs.length(), 5)) {
            val lab = labs.getJSONObject(i)
            val name = lab.optString("name", "")
            val value = lab.optString("value", "")
            val flag = lab.optString("interpretation", "")
            sb.append("$name: $value")
            if (flag == "H" || flag == "L" || flag == "critical") {
                sb.append(" ⚠️")
            }
            sb.append("\n")
        }
        sendToGlassesDisplay(sb.toString())
        speak("Lab results displayed")
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // AI CLINICAL CO-PILOT
    // ═══════════════════════════════════════════════════════════════════════════

    private fun askCopilot(question: String) {
        if (question.isEmpty()) {
            speak("Please ask a question")
            return
        }

        sendToGlassesDisplay("🤖 Thinking...")
        speak("Thinking")

        scope.launch(Dispatchers.IO) {
            try {
                val json = JSONObject()
                json.put("message", question)

                // Add patient context if available
                currentPatientData?.let { patient ->
                    val context = JSONObject()
                    context.put("conditions", patient.optJSONArray("conditions"))
                    context.put("medications", patient.optJSONArray("medications"))
                    context.put("allergies", patient.optJSONArray("allergies"))
                    json.put("patient_context", context)
                }

                // Add conversation history
                val history = JSONArray()
                copilotHistory.takeLast(6).forEach { (role, content) ->
                    val msg = JSONObject()
                    msg.put("role", role)
                    msg.put("content", content)
                    history.put(msg)
                }
                json.put("conversation_history", history)

                val requestBody = json.toString().toRequestBody("application/json".toMediaType())
                val request = Request.Builder()
                    .url("$EHR_PROXY_URL/api/v1/copilot/chat")
                    .post(requestBody)
                    .build()

                val response = httpClient.newCall(request).execute()
                val responseBody = response.body?.string() ?: "{}"
                val result = JSONObject(responseBody)

                withContext(Dispatchers.Main) {
                    val copilotResponse = result.optString("response", "I couldn't generate a response.")

                    // Update history
                    copilotHistory.add(Pair("user", question))
                    copilotHistory.add(Pair("assistant", copilotResponse))

                    sendToGlassesDisplay("🤖 COPILOT:\n$copilotResponse")
                    speak(copilotResponse)
                }
            } catch (e: Exception) {
                Log.e(TAG, "Copilot error: ${e.message}")
                withContext(Dispatchers.Main) {
                    sendToGlassesDisplay("❌ Copilot unavailable")
                    speak("Copilot is unavailable")
                }
            }
        }
    }

    private fun askCopilotFollowUp(followUp: String) {
        if (copilotHistory.isEmpty()) {
            speak("No previous copilot conversation")
            return
        }
        askCopilot(followUp)
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // DOCUMENTATION
    // ═══════════════════════════════════════════════════════════════════════════

    private fun startDocumentation() {
        isDocumenting = true
        noteBuffer.clear()
        sendToGlassesDisplay("📝 Recording note...\nSay 'stop note' when done")
        speak("Recording note. Speak now.")
        statusText.text = "Status: Documenting..."
    }

    private fun stopDocumentation() {
        if (!isDocumenting) return
        isDocumenting = false
        statusText.text = "Status: Connected"

        val noteText = noteBuffer.toString()
        if (noteText.isNotEmpty()) {
            sendToGlassesDisplay("📝 Note captured:\n${noteText.take(100)}...")
            speak("Note captured. ${noteText.split(" ").size} words.")
            // TODO: Generate SOAP note from transcript
        } else {
            sendToGlassesDisplay("📝 No note content captured")
            speak("No note content captured")
        }
    }

    private fun appendToNote(text: String) {
        noteBuffer.append(text).append(" ")
        val preview = noteBuffer.toString().takeLast(80)
        sendToGlassesDisplay("📝 ...$preview")
    }

    private fun captureVital(type: String, transcript: String) {
        val value = extractVitalValue(type, transcript)
        if (value != null) {
            sendToGlassesDisplay("✓ Captured:\n$type: $value")
            speak("$type captured: $value")
        }
    }

    private fun extractVitalValue(type: String, transcript: String): String? {
        val numbers = Regex("\\d+").findAll(transcript).map { it.value }.toList()
        return when (type) {
            "blood_pressure" -> if (numbers.size >= 2) "${numbers[0]}/${numbers[1]}" else null
            else -> numbers.firstOrNull()
        }
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // INTERPRETER INTEGRATION (Feature #86)
    // ═══════════════════════════════════════════════════════════════════════════

    private fun requestInterpreter() {
        sendToGlassesDisplay("🌐 INTERPRETER\nSay language + interpreter\n• Spanish interpreter\n• Chinese interpreter\n• Vietnamese interpreter")
        speak("Say the language followed by interpreter. For example, Spanish interpreter.")
    }

    private fun requestInterpreterForLanguage(languageCode: String, languageName: String) {
        patientPreferredLanguage = languageCode
        patientPreferredLanguageName = languageName
        interpreterRequired = true

        sendToGlassesDisplay("📞 $languageName INTERPRETER\n\nLanguage Line:\n1-800-526-7625\n\nCyraCom:\n1-844-797-2266\n\nSay 'start interpreter' when connected")
        speak("$languageName interpreter requested. Call Language Line at 1-800-526-7625")
    }

    private fun showInterpreterStatus() {
        val sb = StringBuilder("🌐 INTERPRETER STATUS\n\n")
        if (patientPreferredLanguage != null) {
            sb.append("Language: $patientPreferredLanguageName\n")
            sb.append("Interpreter Required: ${if (interpreterRequired) "Yes" else "No"}")
        } else {
            sb.append("No language preference set\n")
            sb.append("Say 'set language Spanish' to set")
        }
        sendToGlassesDisplay(sb.toString())
    }

    private fun showClinicalPhrases() {
        val language = patientPreferredLanguage ?: "es"

        val sb = StringBuilder()
        when (language) {
            "es" -> {
                sb.append("📖 SPANISH PHRASES\n\n")
                sb.append("Where does it hurt?\n")
                sb.append("¿Dónde le duele?\n")
                sb.append("(DOHN-day leh DWEH-leh)\n\n")
                sb.append("Rate pain 1-10:\n")
                sb.append("Del 1 al 10, ¿cuánto?\n")
                sb.append("(del OO-no al dee-ES)")
            }
            "zh" -> {
                sb.append("📖 CHINESE PHRASES\n\n")
                sb.append("Where does it hurt?\n")
                sb.append("哪里痛？\n")
                sb.append("(Nǎlǐ tòng?)")
            }
            else -> {
                sb.append("📖 CLINICAL PHRASES\n")
                sb.append("Not available for: $language")
            }
        }
        sendToGlassesDisplay(sb.toString())
        speak("Clinical phrases displayed")
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // HEALTH LITERACY (Feature #85)
    // ═══════════════════════════════════════════════════════════════════════════

    private fun showLiteracyScreening() {
        sendToGlassesDisplay("📖 LITERACY SCREENING\n\nAsk patient:\n\"How confident are you\nfilling out medical forms?\"\n\n1 = Not at all\n5 = Extremely\n\nScore 1-2 = Low literacy")
        speak("Ask patient: How confident are you filling out medical forms? Score 1 to 5.")
    }

    private fun setLiteracyLevel(level: String) {
        patientLiteracyLevel = level
        val guidance = when (level) {
            "inadequate" -> "Use pictures only. Verbal instructions. 1-2 key points max."
            "marginal" -> "5th grade reading level. Bullet points. 3-4 messages."
            else -> "Standard instructions appropriate."
        }
        sendToGlassesDisplay("📖 LITERACY: ${level.uppercase()}\n\n$guidance")
        speak("Literacy level set to $level. $guidance")
    }

    private fun showSimplifiedInstructions() {
        val sb = StringBuilder("📖 SIMPLIFIED INSTRUCTIONS\n\n")
        sb.append("Use these principles:\n")
        sb.append("• Short sentences\n")
        sb.append("• Common words only\n")
        sb.append("• Pictures when possible\n")
        sb.append("• Teach-back verification\n")
        sb.append("• Written + verbal")
        sendToGlassesDisplay(sb.toString())
        speak("Simplified instructions guidance displayed")
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // SDOH INTEGRATION (Feature #84)
    // ═══════════════════════════════════════════════════════════════════════════

    private fun showSdohStatus() {
        val sb = StringBuilder("🏠 SDOH STATUS\n\n")
        if (sdohFactors.isEmpty()) {
            sb.append("No factors identified\n\n")
            sb.append("Say:\n")
            sb.append("• 'food insecurity'\n")
            sb.append("• 'housing unstable'\n")
            sb.append("• 'transportation barrier'")
        } else {
            sb.append("Factors:\n")
            sdohFactors.forEach { factor ->
                sb.append("• ${factor.replace("_", " ")}\n")
            }
        }
        sendToGlassesDisplay(sb.toString())
    }

    private fun addSdohFactor(factor: String) {
        if (!sdohFactors.contains(factor)) {
            sdohFactors.add(factor)
        }
        sendToGlassesDisplay("✓ SDOH ADDED:\n${factor.replace("_", " ").uppercase()}\n\nConsider interventions:\n• Social work referral\n• Community resources\n• Care plan modifications")
        speak("${factor.replace("_", " ")} documented. Consider social work referral.")
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // CAMERA / IMAGE ANALYSIS (Feature #70)
    // ═══════════════════════════════════════════════════════════════════════════

    private fun captureImage(context: String) {
        imageAnalysisContext = context

        try {
            val photoFile = java.io.File.createTempFile(
                "mdx_image_",
                ".jpg",
                cacheDir
            )
            currentImageUri = androidx.core.content.FileProvider.getUriForFile(
                this,
                "$packageName.fileprovider",
                photoFile
            )

            sendToGlassesDisplay("📷 Opening camera...\nContext: $context")
            speak("Opening camera for $context analysis")

            cameraLauncher.launch(currentImageUri)
        } catch (e: Exception) {
            Log.e(TAG, "Camera error: ${e.message}")
            sendToGlassesDisplay("❌ Camera unavailable")
            speak("Camera unavailable")
        }
    }

    private fun analyzeImage(uri: android.net.Uri) {
        sendToGlassesDisplay("🔍 Analyzing image...\nContext: $imageAnalysisContext")
        speak("Analyzing $imageAnalysisContext image")

        scope.launch(Dispatchers.IO) {
            try {
                // Read image as base64
                val inputStream = contentResolver.openInputStream(uri)
                val bytes = inputStream?.readBytes() ?: return@launch
                val base64Image = android.util.Base64.encodeToString(bytes, android.util.Base64.NO_WRAP)

                val json = JSONObject()
                json.put("image_base64", base64Image)
                json.put("context_type", imageAnalysisContext)
                currentPatientId?.let { json.put("patient_id", it) }

                val requestBody = json.toString().toRequestBody("application/json".toMediaType())
                val request = Request.Builder()
                    .url("$EHR_PROXY_URL/api/v1/image/analyze")
                    .post(requestBody)
                    .build()

                val response = httpClient.newCall(request).execute()
                val responseBody = response.body?.string() ?: "{}"
                val result = JSONObject(responseBody)

                withContext(Dispatchers.Main) {
                    val assessment = result.optString("assessment", "Analysis unavailable")
                    val findings = result.optJSONArray("findings")

                    val sb = StringBuilder("📷 IMAGE ANALYSIS\n\n")
                    sb.append("$assessment\n")

                    if (findings != null && findings.length() > 0) {
                        sb.append("\nFindings:\n")
                        for (i in 0 until minOf(findings.length(), 3)) {
                            val finding = findings.getJSONObject(i)
                            sb.append("• ${finding.optString("description")}\n")
                        }
                    }

                    sendToGlassesDisplay(sb.toString())
                    speak(assessment)
                }
            } catch (e: Exception) {
                Log.e(TAG, "Image analysis error: ${e.message}")
                withContext(Dispatchers.Main) {
                    sendToGlassesDisplay("❌ Analysis failed")
                    speak("Image analysis failed")
                }
            }
        }
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // HELP
    // ═══════════════════════════════════════════════════════════════════════════

    private fun showHelp() {
        val helpText = """
            🎤 VOICE COMMANDS

            PATIENT:
            • Load patient [name]
            • Show vitals/allergies/meds/labs

            AI COPILOT:
            • Copilot [question]
            • Tell me more

            DOCUMENTATION:
            • Start/stop note
            • BP 120 over 80

            INTERPRETER:
            • Spanish interpreter
            • Clinical phrases

            LITERACY:
            • Literacy screen
            • Simplify instructions

            SDOH:
            • Food insecurity
            • Housing unstable

            CAMERA:
            • Take photo
            • Analyze wound/rash
        """.trimIndent()

        sendToGlassesDisplay(helpText)
        speak("Voice commands displayed on glasses")
    }
}
