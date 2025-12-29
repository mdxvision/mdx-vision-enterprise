package com.mdxvision

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
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
    }

    private lateinit var speechRecognizer: SpeechRecognizer
    private lateinit var statusText: TextView
    private lateinit var transcriptText: TextView
    private lateinit var patientDataText: TextView
    private val httpClient = OkHttpClient()

    // Documentation mode
    private var isDocumentationMode = false
    private val documentationTranscripts = mutableListOf<String>()

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

    private fun setupUI() {
        // Create a simple layout programmatically for AR glasses
        val layout = android.widget.LinearLayout(this).apply {
            orientation = android.widget.LinearLayout.VERTICAL
            setBackgroundColor(0xFF0A1628.toInt())
            setPadding(32, 32, 32, 32)
        }

        statusText = TextView(this).apply {
            text = "MDx Vision"
            textSize = 24f
            setTextColor(0xFFF8FAFC.toInt())
        }
        layout.addView(statusText)

        transcriptText = TextView(this).apply {
            text = "Say 'Hey MDx' to start..."
            textSize = 18f
            setTextColor(0xFF94A3B8.toInt())
            setPadding(0, 16, 0, 0)
        }
        layout.addView(transcriptText)

        // Voice button
        val voiceButton = android.widget.Button(this).apply {
            text = "Start Listening"
            setOnClickListener { startVoiceRecognition() }
        }
        layout.addView(voiceButton)

        // Patient data button
        val patientButton = android.widget.Button(this).apply {
            text = "Load Patient (Cerner)"
            setOnClickListener { fetchPatientData(TEST_PATIENT_ID) }
        }
        layout.addView(patientButton)

        // Scan wristband button (Patent Claims 5-7)
        val scanButton = android.widget.Button(this).apply {
            text = "Scan Wristband"
            setOnClickListener { startBarcodeScanner() }
        }
        layout.addView(scanButton)

        // Start Note button (AI Clinical Documentation)
        val noteButton = android.widget.Button(this).apply {
            text = "Start Note"
            setOnClickListener { toggleDocumentationMode() }
        }
        layout.addView(noteButton)

        // Scrollable patient data display
        val scrollView = android.widget.ScrollView(this).apply {
            layoutParams = android.widget.LinearLayout.LayoutParams(
                android.widget.LinearLayout.LayoutParams.MATCH_PARENT,
                0,
                1f  // Take remaining space
            )
        }

        patientDataText = TextView(this).apply {
            text = ""
            textSize = 14f
            setTextColor(0xFF10B981.toInt()) // Green for patient data
            setPadding(0, 24, 0, 24)
        }
        scrollView.addView(patientDataText)
        layout.addView(scrollView)

        setContentView(layout)
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
            statusText.text = "DOCUMENTING..."
            transcriptText.text = "Speak to document. Tap 'Start Note' again to generate."
            patientDataText.text = ""
            patientDataText.setTextColor(0xFFFFB800.toInt()) // Yellow for documentation
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

    private fun generateClinicalNote(transcript: String) {
        statusText.text = "Generating SOAP Note..."
        patientDataText.text = ""

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
                            statusText.text = "Note Generation Failed"
                            patientDataText.text = "Error: ${e.message}"
                            patientDataText.setTextColor(0xFF10B981.toInt())
                        }
                    }

                    override fun onResponse(call: Call, response: Response) {
                        val body = response.body?.string()
                        Log.d(TAG, "Generated note: $body")

                        runOnUiThread {
                            statusText.text = "SOAP Note Generated"
                            try {
                                val result = JSONObject(body ?: "{}")
                                val displayText = result.optString("display_text", "No note generated")
                                patientDataText.text = displayText
                                patientDataText.setTextColor(0xFF10B981.toInt())
                            } catch (e: Exception) {
                                patientDataText.text = body ?: "No response"
                            }
                        }
                    }
                })
            } catch (e: Exception) {
                Log.e(TAG, "Failed to generate note: ${e.message}")
                runOnUiThread {
                    patientDataText.text = "Error: ${e.message}"
                }
            }
        }.start()
    }

    private fun fetchPatientByMrn(mrn: String) {
        statusText.text = "Looking up MRN..."
        patientDataText.text = ""

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
                            statusText.text = "Lookup failed"
                            patientDataText.text = "Error: ${e.message}"
                        }
                    }

                    override fun onResponse(call: Call, response: Response) {
                        val body = response.body?.string()
                        Log.d(TAG, "MRN lookup response: $body")

                        runOnUiThread {
                            if (response.code == 200) {
                                statusText.text = "Patient Found!"
                                try {
                                    val patient = JSONObject(body ?: "{}")
                                    val displayText = patient.optString("display_text", "No data")
                                    patientDataText.text = displayText
                                } catch (e: Exception) {
                                    patientDataText.text = body ?: "No response"
                                }
                            } else {
                                statusText.text = "Patient Not Found"
                                patientDataText.text = "No patient with MRN: $mrn"
                            }
                        }
                    }
                })
            } catch (e: Exception) {
                Log.e(TAG, "MRN lookup failed: ${e.message}")
                runOnUiThread {
                    patientDataText.text = "Error: ${e.message}"
                }
            }
        }.start()
    }

    private fun fetchPatientData(patientId: String) {
        statusText.text = "Fetching patient..."
        patientDataText.text = ""

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
                            statusText.text = "Connection failed"
                            patientDataText.text = "Error: ${e.message}"
                        }
                    }

                    override fun onResponse(call: Call, response: Response) {
                        val body = response.body?.string()
                        Log.d(TAG, "Patient data: $body")

                        runOnUiThread {
                            statusText.text = "MDx Vision - Patient Loaded"
                            try {
                                val patient = JSONObject(body ?: "{}")
                                val displayText = patient.optString("display_text", "No data")
                                patientDataText.text = displayText
                            } catch (e: Exception) {
                                patientDataText.text = body ?: "No response"
                            }
                        }
                    }
                })
            } catch (e: Exception) {
                Log.e(TAG, "Failed to fetch patient: ${e.message}")
                runOnUiThread {
                    patientDataText.text = "Error: ${e.message}"
                }
            }
        }.start()
    }

    private fun isVuzixDevice(): Boolean {
        val manufacturer = android.os.Build.MANUFACTURER.lowercase()
        val model = android.os.Build.MODEL.lowercase()
        return manufacturer.contains("vuzix") || model.contains("blade")
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
                SpeechRecognizer.ERROR_NO_MATCH -> "No match"
                SpeechRecognizer.ERROR_RECOGNIZER_BUSY -> "Recognizer busy"
                SpeechRecognizer.ERROR_SERVER -> "Server error"
                SpeechRecognizer.ERROR_SPEECH_TIMEOUT -> "Speech timeout"
                else -> "Unknown error"
            }
            Log.e(TAG, "Speech error: $errorMessage")
            statusText.text = "Error: $errorMessage"
        }

        override fun onResults(results: Bundle?) {
            val matches = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
            val transcript = matches?.firstOrNull() ?: ""

            Log.d(TAG, "Transcript: $transcript")
            transcriptText.text = "\"$transcript\""
            statusText.text = "MDx Vision"

            // Process the transcript
            processTranscript(transcript)
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
                toggleDocumentationMode()
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
            else -> {
                // Display transcribed text
                transcriptText.text = "\"$transcript\""
                Log.d(TAG, "Voice command: $transcript")
            }
        }
    }

    private fun fetchPatientSection(section: String) {
        statusText.text = "Loading ${section}..."
        patientDataText.text = ""

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
                            patientDataText.text = "Error: ${e.message}"
                        }
                    }

                    override fun onResponse(call: Call, response: Response) {
                        val body = response.body?.string()
                        Log.d(TAG, "Patient data for $section: $body")

                        runOnUiThread {
                            try {
                                val patient = JSONObject(body ?: "{}")
                                val display = when (section) {
                                    "vitals" -> formatVitals(patient)
                                    "allergies" -> formatAllergies(patient)
                                    "medications" -> formatMedications(patient)
                                    "labs" -> formatLabs(patient)
                                    "procedures" -> formatProcedures(patient)
                                    else -> patient.optString("display_text", "No data")
                                }
                                statusText.text = section.uppercase()
                                patientDataText.text = display
                            } catch (e: Exception) {
                                patientDataText.text = "Parse error: ${e.message}"
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
    }
}
