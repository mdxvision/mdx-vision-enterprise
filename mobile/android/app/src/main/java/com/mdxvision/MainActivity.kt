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

        // Patient data display
        patientDataText = TextView(this).apply {
            text = ""
            textSize = 14f
            setTextColor(0xFF10B981.toInt()) // Green for patient data
            setPadding(0, 24, 0, 0)
        }
        layout.addView(patientDataText)

        setContentView(layout)
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
            else -> {
                // Display transcribed text
                transcriptText.text = "\"$transcript\""
                Log.d(TAG, "Voice command: $transcript")
            }
        }
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
