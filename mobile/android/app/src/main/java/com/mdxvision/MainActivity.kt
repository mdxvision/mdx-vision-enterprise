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
import org.json.JSONArray
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

    // ═══════════════════════════════════════════════════════════════════════════
    // ENCOUNTER TIMER - Track time spent with patient
    // ═══════════════════════════════════════════════════════════════════════════
    private var encounterStartTime: Long? = null  // System.currentTimeMillis() when timer started
    private var encounterTimerRunning: Boolean = false
    private var timerIndicatorView: TextView? = null  // Visual indicator showing elapsed time
    private var timerUpdateHandler: android.os.Handler? = null
    private var timerUpdateRunnable: Runnable? = null

    // ═══════════════════════════════════════════════════════════════════════════
    // VOICE ORDERS - State Variables
    // ═══════════════════════════════════════════════════════════════════════════
    private val orderQueue = mutableListOf<Order>()  // Pending orders for current patient
    private var pendingConfirmationOrder: Order? = null  // Order awaiting yes/no confirmation
    private val pendingPlanItems = mutableListOf<String>()  // Orders to add to Plan when note is generated
    private val ORDERS_KEY = "pending_orders"
    private val ORDERS_PATIENT_KEY = "orders_patient_id"

    // Lab orders database
    private val labOrders = mapOf(
        "cbc" to LabOrderInfo("CBC", "Complete Blood Count", "85025", listOf("cbc", "complete blood count", "blood count", "hemogram")),
        "cmp" to LabOrderInfo("CMP", "Comprehensive Metabolic Panel", "80053", listOf("cmp", "comprehensive metabolic", "metabolic panel", "chem 14")),
        "bmp" to LabOrderInfo("BMP", "Basic Metabolic Panel", "80048", listOf("bmp", "basic metabolic", "chem 7", "electrolytes")),
        "ua" to LabOrderInfo("UA", "Urinalysis", "81003", listOf("ua", "urinalysis", "urine test", "urine analysis")),
        "lipid" to LabOrderInfo("Lipid Panel", "Lipid Panel", "80061", listOf("lipid panel", "lipids", "cholesterol panel", "cholesterol")),
        "tsh" to LabOrderInfo("TSH", "Thyroid Stimulating Hormone", "84443", listOf("tsh", "thyroid", "thyroid function")),
        "hba1c" to LabOrderInfo("HbA1c", "Hemoglobin A1c", "83036", listOf("a1c", "hba1c", "hemoglobin a1c", "glycated")),
        "ptinr" to LabOrderInfo("PT/INR", "Prothrombin Time / INR", "85610", listOf("pt", "inr", "pt inr", "protime", "coagulation")),
        "troponin" to LabOrderInfo("Troponin", "Troponin I/T", "84484", listOf("troponin", "trop", "cardiac enzymes")),
        "bun" to LabOrderInfo("BUN/Creatinine", "BUN / Creatinine", "84520", listOf("bun", "creatinine", "renal function", "kidney function")),
        "uculture" to LabOrderInfo("Urine Culture", "Urine Culture and Sensitivity", "87086", listOf("urine culture", "ucx", "u culture")),
        "bculture" to LabOrderInfo("Blood Culture", "Blood Culture", "87040", listOf("blood culture", "bcx", "blood cx"))
    )

    // Imaging orders database
    private val imagingOrders = mapOf(
        "cxr" to ImagingOrderInfo("Chest X-ray", "Chest Radiograph", "71046", "chest", "xray", listOf("chest x-ray", "chest xray", "cxr", "chest radiograph", "chest film")),
        "cthead" to ImagingOrderInfo("CT Head", "CT Scan of Head", "70450", "head", "ct", listOf("ct head", "head ct", "ct brain", "brain ct", "ct scan head"), true),
        "ctchest" to ImagingOrderInfo("CT Chest", "CT Scan of Chest", "71250", "chest", "ct", listOf("ct chest", "chest ct", "ct thorax"), true),
        "ctabdomen" to ImagingOrderInfo("CT Abdomen/Pelvis", "CT Scan of Abdomen and Pelvis", "74176", "abdomen", "ct", listOf("ct abdomen", "abdominal ct", "ct abd pelvis", "ct belly", "ct abdomen pelvis"), true),
        "mribrain" to ImagingOrderInfo("MRI Brain", "MRI of Brain", "70551", "brain", "mri", listOf("mri brain", "brain mri", "mri head", "head mri"), true),
        "mrispine" to ImagingOrderInfo("MRI Spine", "MRI of Spine", "72148", "spine", "mri", listOf("mri spine", "spine mri", "mri lumbar", "mri cervical", "lumbar mri", "cervical mri"), true),
        "usabdomen" to ImagingOrderInfo("Ultrasound Abdomen", "Abdominal Ultrasound", "76700", "abdomen", "ultrasound", listOf("ultrasound abdomen", "abdominal ultrasound", "us abdomen", "abd us", "ruq ultrasound")),
        "uspelvis" to ImagingOrderInfo("Ultrasound Pelvis", "Pelvic Ultrasound", "76856", "pelvis", "ultrasound", listOf("pelvic ultrasound", "ultrasound pelvis", "us pelvis", "pelvic us")),
        "echo" to ImagingOrderInfo("Echocardiogram", "Transthoracic Echocardiogram", "93306", "heart", "ultrasound", listOf("echo", "echocardiogram", "tte", "heart ultrasound")),
        "xray" to ImagingOrderInfo("X-ray", "Radiograph", "73030", "extremity", "xray", listOf("x-ray", "xray", "radiograph"))
    )

    // Medication orders database
    private val medicationOrders = mapOf(
        "amoxicillin" to MedicationOrderInfo("Amoxicillin", "antibiotic", listOf("250mg", "500mg", "875mg"), listOf("TID", "BID"), listOf("7 days", "10 days", "14 days"), "PO", listOf("amoxicillin", "amox", "amoxil"), listOf("warfarin", "methotrexate"), listOf("penicillin", "ampicillin", "cephalosporin")),
        "azithromycin" to MedicationOrderInfo("Azithromycin", "antibiotic", listOf("250mg", "500mg"), listOf("daily"), listOf("3 days", "5 days"), "PO", listOf("azithromycin", "zithromax", "z-pack", "zpack"), listOf("warfarin"), listOf("macrolide", "erythromycin")),
        "ibuprofen" to MedicationOrderInfo("Ibuprofen", "nsaid", listOf("200mg", "400mg", "600mg", "800mg"), listOf("TID", "Q6H", "PRN"), listOf("5 days", "7 days", "as needed"), "PO", listOf("ibuprofen", "advil", "motrin"), listOf("warfarin", "aspirin", "lisinopril", "lithium", "methotrexate"), listOf("nsaid", "aspirin")),
        "acetaminophen" to MedicationOrderInfo("Acetaminophen", "analgesic", listOf("325mg", "500mg", "650mg", "1000mg"), listOf("Q4-6H", "PRN"), listOf("as needed"), "PO", listOf("acetaminophen", "tylenol", "apap"), listOf("warfarin"), listOf()),
        "prednisone" to MedicationOrderInfo("Prednisone", "corticosteroid", listOf("5mg", "10mg", "20mg", "40mg", "60mg"), listOf("daily", "BID"), listOf("5 days", "7 days", "taper"), "PO", listOf("prednisone", "deltasone", "pred"), listOf("nsaid", "warfarin", "insulin"), listOf("corticosteroid")),
        "omeprazole" to MedicationOrderInfo("Omeprazole", "ppi", listOf("20mg", "40mg"), listOf("daily", "BID"), listOf("2 weeks", "4 weeks", "8 weeks"), "PO", listOf("omeprazole", "prilosec", "ppi"), listOf("clopidogrel", "methotrexate"), listOf()),
        "metformin" to MedicationOrderInfo("Metformin", "antidiabetic", listOf("500mg", "850mg", "1000mg"), listOf("BID", "TID"), listOf("ongoing"), "PO", listOf("metformin", "glucophage"), listOf("contrast", "alcohol"), listOf()),
        "lisinopril" to MedicationOrderInfo("Lisinopril", "ace_inhibitor", listOf("2.5mg", "5mg", "10mg", "20mg", "40mg"), listOf("daily"), listOf("ongoing"), "PO", listOf("lisinopril", "zestril", "prinivil"), listOf("potassium", "spironolactone", "nsaid", "lithium"), listOf("ace inhibitor")),
        "amlodipine" to MedicationOrderInfo("Amlodipine", "calcium_channel_blocker", listOf("2.5mg", "5mg", "10mg"), listOf("daily"), listOf("ongoing"), "PO", listOf("amlodipine", "norvasc"), listOf("simvastatin"), listOf()),
        "hydrocodone" to MedicationOrderInfo("Hydrocodone/APAP", "opioid", listOf("5/325mg", "7.5/325mg", "10/325mg"), listOf("Q4-6H PRN"), listOf("3 days", "5 days", "7 days"), "PO", listOf("hydrocodone", "vicodin", "norco", "lortab"), listOf("benzodiazepine", "alcohol", "gabapentin"), listOf("opioid"), true)
    )

    // Frequency aliases for natural language parsing
    private val frequencyAliases = mapOf(
        "once daily" to "daily", "one time a day" to "daily", "once a day" to "daily",
        "twice daily" to "BID", "two times daily" to "BID", "twice a day" to "BID",
        "three times daily" to "TID", "three times a day" to "TID",
        "four times daily" to "QID", "four times a day" to "QID",
        "every 4 hours" to "Q4H", "every 6 hours" to "Q6H", "every 8 hours" to "Q8H", "every 12 hours" to "Q12H",
        "as needed" to "PRN", "when needed" to "PRN", "prn" to "PRN",
        "at bedtime" to "QHS", "before bed" to "QHS"
    )

    // ═══════════════════════════════════════════════════════════════════════════
    // ORDER SETS - Predefined bundles of orders for common clinical scenarios
    // ═══════════════════════════════════════════════════════════════════════════

    data class OrderSetItem(
        val type: OrderType,
        val orderKey: String,  // Key in the respective order database (labOrders, imagingOrders, etc.)
        val details: String = ""  // Optional details (e.g., "with contrast" for imaging)
    )

    data class OrderSetInfo(
        val id: String,
        val name: String,
        val displayName: String,
        val description: String,
        val items: List<OrderSetItem>,
        val aliases: List<String>
    )

    private val orderSets = mapOf(
        "chest_pain" to OrderSetInfo(
            id = "chest_pain",
            name = "Chest Pain Workup",
            displayName = "Chest Pain Workup",
            description = "Initial workup for acute chest pain / ACS rule-out",
            items = listOf(
                OrderSetItem(OrderType.LAB, "troponin"),
                OrderSetItem(OrderType.LAB, "cbc"),
                OrderSetItem(OrderType.LAB, "bmp"),
                OrderSetItem(OrderType.LAB, "ptinr"),
                OrderSetItem(OrderType.IMAGING, "cxr"),
                OrderSetItem(OrderType.IMAGING, "echo")
            ),
            aliases = listOf("chest pain", "chest pain workup", "acs workup", "acs", "cardiac workup", "rule out mi", "mi workup")
        ),
        "sepsis" to OrderSetInfo(
            id = "sepsis",
            name = "Sepsis Bundle",
            displayName = "Sepsis Bundle / Workup",
            description = "Initial sepsis workup per Surviving Sepsis guidelines",
            items = listOf(
                OrderSetItem(OrderType.LAB, "bculture"),
                OrderSetItem(OrderType.LAB, "cbc"),
                OrderSetItem(OrderType.LAB, "cmp"),
                OrderSetItem(OrderType.LAB, "ua"),
                OrderSetItem(OrderType.LAB, "uculture"),
                OrderSetItem(OrderType.IMAGING, "cxr")
            ),
            aliases = listOf("sepsis", "sepsis bundle", "sepsis workup", "septic workup", "infection workup")
        ),
        "dka" to OrderSetInfo(
            id = "dka",
            name = "DKA Protocol",
            displayName = "Diabetic Ketoacidosis Protocol",
            description = "Initial workup for DKA / hyperglycemic emergency",
            items = listOf(
                OrderSetItem(OrderType.LAB, "bmp"),
                OrderSetItem(OrderType.LAB, "cbc"),
                OrderSetItem(OrderType.LAB, "ua"),
                OrderSetItem(OrderType.LAB, "hba1c")
            ),
            aliases = listOf("dka", "dka protocol", "dka workup", "diabetic ketoacidosis", "hyperglycemia workup")
        ),
        "admission" to OrderSetInfo(
            id = "admission",
            name = "Admission Labs",
            displayName = "Standard Admission Labs",
            description = "Basic admission laboratory panel",
            items = listOf(
                OrderSetItem(OrderType.LAB, "cbc"),
                OrderSetItem(OrderType.LAB, "cmp"),
                OrderSetItem(OrderType.LAB, "ua"),
                OrderSetItem(OrderType.LAB, "ptinr")
            ),
            aliases = listOf("admission labs", "admission", "admit labs", "admission panel", "admit workup")
        ),
        "preop" to OrderSetInfo(
            id = "preop",
            name = "Preop Labs",
            displayName = "Preoperative Laboratory Panel",
            description = "Standard preoperative clearance labs",
            items = listOf(
                OrderSetItem(OrderType.LAB, "cbc"),
                OrderSetItem(OrderType.LAB, "bmp"),
                OrderSetItem(OrderType.LAB, "ptinr"),
                OrderSetItem(OrderType.IMAGING, "cxr")
            ),
            aliases = listOf("preop", "preop labs", "pre op", "pre-op labs", "surgical clearance", "preoperative")
        ),
        "stroke" to OrderSetInfo(
            id = "stroke",
            name = "Stroke Workup",
            displayName = "Acute Stroke Workup",
            description = "Initial workup for suspected stroke/CVA",
            items = listOf(
                OrderSetItem(OrderType.LAB, "cbc"),
                OrderSetItem(OrderType.LAB, "bmp"),
                OrderSetItem(OrderType.LAB, "ptinr"),
                OrderSetItem(OrderType.IMAGING, "cthead")
            ),
            aliases = listOf("stroke", "stroke workup", "cva", "cva workup", "code stroke")
        ),
        "chf" to OrderSetInfo(
            id = "chf",
            name = "CHF Exacerbation",
            displayName = "CHF Exacerbation Workup",
            description = "Workup for acute heart failure exacerbation",
            items = listOf(
                OrderSetItem(OrderType.LAB, "cbc"),
                OrderSetItem(OrderType.LAB, "bmp"),
                OrderSetItem(OrderType.LAB, "troponin"),
                OrderSetItem(OrderType.IMAGING, "cxr"),
                OrderSetItem(OrderType.IMAGING, "echo")
            ),
            aliases = listOf("chf", "chf exacerbation", "heart failure", "hf exacerbation", "fluid overload")
        ),
        "copd" to OrderSetInfo(
            id = "copd",
            name = "COPD Exacerbation",
            displayName = "COPD Exacerbation Workup",
            description = "Workup for acute COPD exacerbation",
            items = listOf(
                OrderSetItem(OrderType.LAB, "cbc"),
                OrderSetItem(OrderType.LAB, "bmp"),
                OrderSetItem(OrderType.IMAGING, "cxr")
            ),
            aliases = listOf("copd", "copd exacerbation", "copd flare", "respiratory distress")
        ),
        "abdominal_pain" to OrderSetInfo(
            id = "abdominal_pain",
            name = "Abdominal Pain Workup",
            displayName = "Acute Abdominal Pain Workup",
            description = "Initial workup for acute abdominal pain",
            items = listOf(
                OrderSetItem(OrderType.LAB, "cbc"),
                OrderSetItem(OrderType.LAB, "cmp"),
                OrderSetItem(OrderType.LAB, "lipid"),
                OrderSetItem(OrderType.LAB, "ua"),
                OrderSetItem(OrderType.IMAGING, "ctabdomen")
            ),
            aliases = listOf("abdominal pain", "abd pain", "belly pain", "abdominal workup", "acute abdomen")
        ),
        "uti" to OrderSetInfo(
            id = "uti",
            name = "UTI Workup",
            displayName = "Urinary Tract Infection Workup",
            description = "Workup for suspected urinary tract infection",
            items = listOf(
                OrderSetItem(OrderType.LAB, "ua"),
                OrderSetItem(OrderType.LAB, "uculture"),
                OrderSetItem(OrderType.LAB, "cbc"),
                OrderSetItem(OrderType.LAB, "bmp")
            ),
            aliases = listOf("uti", "uti workup", "urinary tract infection", "dysuria workup", "pyelonephritis")
        ),
        "pneumonia" to OrderSetInfo(
            id = "pneumonia",
            name = "Pneumonia Workup",
            displayName = "Community Acquired Pneumonia Workup",
            description = "Workup for suspected pneumonia",
            items = listOf(
                OrderSetItem(OrderType.LAB, "cbc"),
                OrderSetItem(OrderType.LAB, "bmp"),
                OrderSetItem(OrderType.LAB, "bculture"),
                OrderSetItem(OrderType.IMAGING, "cxr")
            ),
            aliases = listOf("pneumonia", "pneumonia workup", "cap", "community acquired pneumonia", "lung infection")
        ),
        "pe" to OrderSetInfo(
            id = "pe",
            name = "PE Workup",
            displayName = "Pulmonary Embolism Workup",
            description = "Workup for suspected pulmonary embolism",
            items = listOf(
                OrderSetItem(OrderType.LAB, "cbc"),
                OrderSetItem(OrderType.LAB, "bmp"),
                OrderSetItem(OrderType.LAB, "ptinr"),
                OrderSetItem(OrderType.LAB, "troponin"),
                OrderSetItem(OrderType.IMAGING, "ctchest")
            ),
            aliases = listOf("pe", "pe workup", "pulmonary embolism", "pulmonary embolus", "dvt pe workup")
        )
    )

    // ═══════════════════════════════════════════════════════════════════════════
    // VOICE VITALS ENTRY - Capture vitals by voice
    // ═══════════════════════════════════════════════════════════════════════════

    enum class VitalType {
        BLOOD_PRESSURE,
        HEART_RATE,
        TEMPERATURE,
        OXYGEN_SATURATION,
        RESPIRATORY_RATE,
        WEIGHT,
        HEIGHT,
        PAIN_LEVEL
    }

    data class CapturedVital(
        val type: VitalType,
        val value: String,           // "120/80", "72", "98.6"
        val unit: String,            // "mmHg", "bpm", "°F"
        val displayName: String,     // "Blood Pressure", "Heart Rate"
        val timestamp: Long = System.currentTimeMillis()
    )

    // Vital reference ranges for validation
    data class VitalRange(
        val min: Double,
        val max: Double,
        val criticalLow: Double? = null,
        val criticalHigh: Double? = null
    )

    private val vitalRanges = mapOf(
        "systolic" to VitalRange(60.0, 250.0, 70.0, 180.0),
        "diastolic" to VitalRange(30.0, 150.0, 40.0, 120.0),
        "heart_rate" to VitalRange(20.0, 250.0, 40.0, 150.0),
        "temperature_f" to VitalRange(90.0, 110.0, 95.0, 104.0),
        "temperature_c" to VitalRange(32.0, 43.0, 35.0, 40.0),
        "oxygen_saturation" to VitalRange(50.0, 100.0, 88.0, null),
        "respiratory_rate" to VitalRange(4.0, 60.0, 8.0, 30.0),
        "weight_lbs" to VitalRange(1.0, 1000.0),
        "weight_kg" to VitalRange(0.5, 500.0),
        "height_in" to VitalRange(10.0, 100.0),
        "height_cm" to VitalRange(25.0, 250.0),
        "pain" to VitalRange(0.0, 10.0)
    )

    // Vital aliases for voice recognition
    private val vitalAliases = mapOf(
        VitalType.BLOOD_PRESSURE to listOf("bp", "blood pressure", "pressure", "b p"),
        VitalType.HEART_RATE to listOf("heart rate", "pulse", "hr", "heartrate", "heart beat", "bpm"),
        VitalType.TEMPERATURE to listOf("temp", "temperature", "fever"),
        VitalType.OXYGEN_SATURATION to listOf("o2", "oxygen", "sat", "sats", "o2 sat", "oxygen saturation", "spo2", "pulse ox"),
        VitalType.RESPIRATORY_RATE to listOf("respiratory rate", "respirations", "resp rate", "rr", "breathing rate", "breaths"),
        VitalType.WEIGHT to listOf("weight", "wt"),
        VitalType.HEIGHT to listOf("height", "ht", "tall"),
        VitalType.PAIN_LEVEL to listOf("pain", "pain level", "pain scale", "pain score")
    )

    // Captured vitals storage
    private val capturedVitals = mutableListOf<CapturedVital>()

    // Voice templates - built-in note templates with auto-fill variables
    // Variables: {{patient_name}}, {{dob}}, {{age}}, {{gender}}, {{medications}}, {{allergies}}, {{vitals}}, {{conditions}}, {{date}}
    private val USER_TEMPLATES_KEY = "user_note_templates"

    // Custom voice commands - user-defined command aliases and macros
    private val CUSTOM_COMMANDS_KEY = "custom_voice_commands"

    /**
     * Custom voice command that maps a trigger phrase to one or more actions
     */
    data class CustomCommand(
        val name: String,           // Display name (e.g., "Admission Check")
        val trigger: String,        // Trigger phrase (e.g., "admission check")
        val actions: List<String>,  // List of actions to execute (e.g., ["show vitals", "show meds"])
        val description: String = "" // Optional description
    ) {
        fun toJson(): JSONObject {
            return JSONObject().apply {
                put("name", name)
                put("trigger", trigger)
                put("actions", JSONArray(actions))
                put("description", description)
            }
        }

        companion object {
            fun fromJson(json: JSONObject): CustomCommand {
                val actionsArray = json.optJSONArray("actions") ?: JSONArray()
                val actions = mutableListOf<String>()
                for (i in 0 until actionsArray.length()) {
                    actions.add(actionsArray.getString(i))
                }
                return CustomCommand(
                    name = json.optString("name", ""),
                    trigger = json.optString("trigger", ""),
                    actions = actions,
                    description = json.optString("description", "")
                )
            }
        }
    }

    private val builtInTemplates = mapOf(
        "diabetes" to NoteTemplate(
            name = "Diabetes Follow-up",
            category = "Primary Care",
            noteType = "SOAP",
            content = """▸ S:
{{patient_name}} presents for diabetes follow-up.
Reports compliance with medications and diet.
No hypoglycemic episodes. No polyuria/polydipsia.
Current medications: {{medications}}

▸ O:
Vitals: {{vitals}}
General: Alert, well-appearing
Foot exam: Skin intact, sensation normal, pulses palpable
Eyes: No retinopathy noted

▸ A:
Type 2 Diabetes Mellitus - management ongoing
{{conditions}}

▸ P:
• Continue current diabetes regimen
• A1C recheck in 3 months
• Annual eye exam reminder given
• Foot care education reinforced
• Diet and exercise counseling provided
• Follow up in 3 months"""
        ),
        "hypertension" to NoteTemplate(
            name = "Hypertension Follow-up",
            category = "Primary Care",
            noteType = "SOAP",
            content = """▸ S:
{{patient_name}} presents for hypertension follow-up.
Reports taking medications as prescribed.
Denies headaches, chest pain, or shortness of breath.
Home BP readings: [patient to report]
Current medications: {{medications}}

▸ O:
Vitals: {{vitals}}
General: Alert, no acute distress
CV: Regular rate and rhythm, no murmurs
Lungs: Clear bilaterally

▸ A:
Essential Hypertension - {{controlled/uncontrolled}}
{{conditions}}

▸ P:
• Continue current antihypertensive regimen
• Low sodium diet reinforced
• Continue home BP monitoring
• Labs: BMP, lipid panel if due
• Follow up in 1-3 months"""
        ),
        "uri" to NoteTemplate(
            name = "Upper Respiratory Infection",
            category = "Urgent Care",
            noteType = "SOAP",
            content = """▸ S:
{{patient_name}} presents with upper respiratory symptoms.
Duration: [X] days
Symptoms: Nasal congestion, rhinorrhea, sore throat, cough
Denies fever, shortness of breath, ear pain.
No known sick contacts. Allergies: {{allergies}}

▸ O:
Vitals: {{vitals}}
General: Mild distress, appears fatigued
HEENT: TMs clear, oropharynx mildly erythematous, no exudates
Neck: No lymphadenopathy
Lungs: Clear to auscultation bilaterally

▸ A:
Acute Upper Respiratory Infection (viral)

▸ P:
• Supportive care: rest, fluids, OTC decongestants
• Honey for cough (if >1 year old)
• Acetaminophen or ibuprofen for discomfort
• Return if: fever >101, symptoms >10 days, difficulty breathing
• No antibiotics indicated at this time"""
        ),
        "annual_physical" to NoteTemplate(
            name = "Annual Physical",
            category = "Primary Care",
            noteType = "HP",
            content = """▸ CHIEF COMPLAINT:
Annual wellness examination

▸ HPI:
{{patient_name}}, {{age}} year old {{gender}}, presents for annual physical.
No acute complaints today.
Medications: {{medications}}
Allergies: {{allergies}}

▸ PMH:
{{conditions}}

▸ SOCIAL HISTORY:
Tobacco: [Never/Former/Current]
Alcohol: [None/Social/Daily]
Exercise: [Frequency]
Diet: [Description]

▸ FAMILY HISTORY:
[To be documented]

▸ ROS:
Constitutional: No fever, weight changes
Eyes: No vision changes
ENT: No hearing loss, sore throat
CV: No chest pain, palpitations
Respiratory: No cough, shortness of breath
GI: No abdominal pain, changes in bowel habits
GU: No dysuria, frequency
MSK: No joint pain
Neuro: No headaches, weakness
Psych: No depression, anxiety

▸ PHYSICAL EXAM:
Vitals: {{vitals}}
General: Well-appearing, no acute distress
HEENT: Normocephalic, PERRL, TMs clear, oropharynx normal
Neck: Supple, no lymphadenopathy, thyroid normal
Lungs: Clear to auscultation bilaterally
Heart: Regular rate and rhythm, no murmurs
Abdomen: Soft, non-tender, no masses
Extremities: No edema, pulses intact
Skin: No suspicious lesions
Neuro: Alert, oriented, cranial nerves intact

▸ ASSESSMENT:
Annual wellness examination - {{age}} year old {{gender}}
{{conditions}}

▸ PLAN:
• Health maintenance counseling provided
• Age-appropriate cancer screenings discussed
• Immunizations: [Updated/Due]
• Labs ordered: CBC, CMP, Lipid panel, A1C
• Follow up in 1 year or as needed"""
        ),
        "back_pain" to NoteTemplate(
            name = "Low Back Pain",
            category = "Urgent Care",
            noteType = "SOAP",
            content = """▸ S:
{{patient_name}} presents with low back pain.
Onset: [Acute/Gradual]
Duration: [X] days/weeks
Location: [Lumbar/Sacral], [Unilateral/Bilateral]
Radiation: [None/To legs]
Severity: [X]/10
Aggravating factors: [Bending/Lifting/Sitting]
Relieving factors: [Rest/Ice/Heat/Medication]
Red flags: Denies bowel/bladder dysfunction, saddle anesthesia, fever
No trauma reported. Allergies: {{allergies}}

▸ O:
Vitals: {{vitals}}
General: Mild distress due to pain
Back: Tenderness at [location], no spinal step-off
ROM: Limited [flexion/extension] due to pain
Neuro: Strength 5/5 bilateral lower extremities
Sensation intact, DTRs 2+ symmetric
Straight leg raise: [Negative/Positive]
Gait: [Antalgic/Normal]

▸ A:
Acute Low Back Pain - Musculoskeletal/Mechanical
No red flag symptoms

▸ P:
• NSAIDs: Ibuprofen 600mg TID with food x 7 days
• Muscle relaxant: [If appropriate]
• Ice/heat as needed
• Gentle stretching, avoid heavy lifting
• Activity as tolerated, avoid bed rest
• Return if: weakness, numbness, bowel/bladder changes
• Follow up in 1-2 weeks if not improving"""
        ),
        "uti" to NoteTemplate(
            name = "Urinary Tract Infection",
            category = "Urgent Care",
            noteType = "SOAP",
            content = """▸ S:
{{patient_name}} presents with urinary symptoms.
Duration: [X] days
Symptoms: Dysuria, frequency, urgency
[Hematuria: Yes/No]
Denies fever, flank pain, nausea/vomiting.
No vaginal discharge. LMP: [Date]
Allergies: {{allergies}}

▸ O:
Vitals: {{vitals}}
General: No acute distress
Abdomen: Soft, mild suprapubic tenderness, no CVA tenderness
UA: [Results - typically positive LE, nitrites]

▸ A:
Acute Uncomplicated Urinary Tract Infection (Cystitis)

▸ P:
• Nitrofurantoin 100mg BID x 5 days
  OR Trimethoprim-sulfamethoxazole DS BID x 3 days
• Increase fluid intake
• Urinate frequently, especially after intercourse
• Return if: fever, flank pain, symptoms not improving in 48h
• Follow up if recurrent UTIs"""
        ),
        "well_child" to NoteTemplate(
            name = "Well Child Visit",
            category = "Pediatrics",
            noteType = "HP",
            content = """▸ CHIEF COMPLAINT:
Well child visit - [Age] month/year check

▸ HPI:
{{patient_name}}, {{age}}, presents for routine well child examination.
Parent reports child is doing well.
Feeding: [Breast/Formula/Table foods]
Sleep: [Hours, pattern]
Development: Meeting milestones appropriately

▸ BIRTH HISTORY:
[Term/Preterm], [Vaginal/C-section]
Birth weight: [X] lbs
No NICU stay

▸ MEDICATIONS:
{{medications}}

▸ ALLERGIES:
{{allergies}}

▸ DEVELOPMENT:
Gross Motor: [Age appropriate]
Fine Motor: [Age appropriate]
Language: [Age appropriate]
Social: [Age appropriate]

▸ PHYSICAL EXAM:
Vitals: {{vitals}}
Growth: Weight [X]%, Height [X]%, HC [X]%
General: Alert, active, well-appearing
HEENT: Normocephalic, fontanelle [if applicable], TMs clear, red reflex present
Neck: Supple
Heart: Regular rhythm, no murmurs
Lungs: Clear
Abdomen: Soft, no hepatosplenomegaly
GU: [Normal male/female]
Hips: Stable, no click
Skin: No rashes
Neuro: Age-appropriate tone and reflexes

▸ ASSESSMENT:
Well child - {{age}} - healthy, developing appropriately

▸ PLAN:
• Immunizations: [Given today]
• Anticipatory guidance provided
• Safety counseling: [Age appropriate]
• Nutrition counseling provided
• Next visit: [Age] check"""
        ),
        "chest_pain" to NoteTemplate(
            name = "Chest Pain Evaluation",
            category = "Urgent Care",
            noteType = "SOAP",
            content = """▸ S:
{{patient_name}} presents with chest pain.
Onset: [Sudden/Gradual]
Duration: [Minutes/Hours/Days]
Location: [Substernal/Left/Right chest]
Quality: [Sharp/Pressure/Burning]
Radiation: [None/Arm/Jaw/Back]
Severity: [X]/10
Associated symptoms: [SOB/Diaphoresis/Nausea/Palpitations]
Aggravating factors: [Exertion/Breathing/Position/Food]
Relieving factors: [Rest/Antacids/Position change]
Risk factors: [HTN/DM/Smoking/Family hx CAD/Hyperlipidemia]
Medications: {{medications}}
Allergies: {{allergies}}

▸ O:
Vitals: {{vitals}}
General: [Distress level]
CV: Regular rate and rhythm, no murmurs, no JVD
Lungs: Clear bilaterally, no wheezes
Chest wall: [Reproducible tenderness: Yes/No]
Extremities: No edema, pulses equal
EKG: [Normal sinus rhythm/Findings]

▸ A:
Chest Pain - [Etiology]
Differential: [Musculoskeletal/GERD/Anxiety/ACS ruled out]

▸ P:
• [Based on presentation]
• Return immediately if: worsening pain, shortness of breath, diaphoresis
• Follow up with PCP in [X] days
• Consider cardiology referral if indicated"""
        ),
        // ═══════════════════════════════════════════════════════════════════════════
        // SPECIALTY-SPECIFIC TEMPLATES
        // ═══════════════════════════════════════════════════════════════════════════

        // CARDIOLOGY
        "cardiology_chest_pain" to NoteTemplate(
            name = "Cardiology - Chest Pain Evaluation",
            category = "Cardiology",
            noteType = "HP",
            content = """▸ CHIEF COMPLAINT:
Chest pain evaluation

▸ HPI:
{{patient_name}} presents with chest pain.
Location: substernal / left-sided / right-sided
Quality: sharp / dull / pressure / burning
Radiation: jaw / left arm / back / none
Duration: [X] hours/days
Provoking factors: exertion / rest / eating / breathing
Relieving factors: rest / nitroglycerin / antacids
Associated symptoms: dyspnea, diaphoresis, nausea, palpitations
Risk factors: HTN, DM, hyperlipidemia, smoking, family history

▸ PAST MEDICAL HISTORY:
{{conditions}}

▸ MEDICATIONS:
{{medications}}

▸ ALLERGIES:
{{allergies}}

▸ PHYSICAL EXAM:
Vitals: {{vitals}}
General: Alert, no acute distress / mild distress
CV: Regular rate and rhythm, no murmurs, gallops, or rubs
Lungs: Clear bilaterally, no wheezes or crackles
Chest wall: Non-tender to palpation
Extremities: No edema, pulses 2+ bilaterally

▸ DIAGNOSTICS:
ECG: [pending/results]
Troponin: [pending/results]
CXR: [pending/results]

▸ ASSESSMENT:
Chest pain - differential includes ACS, stable angina, GERD, MSK

▸ PLAN:
• Serial troponins q3-6h
• Continuous telemetry monitoring
• ASA 325mg if not contraindicated
• Risk stratification with HEART score
• Cardiology consultation if indicated"""
        ),
        "cardiology_heart_failure" to NoteTemplate(
            name = "Cardiology - Heart Failure",
            category = "Cardiology",
            noteType = "SOAP",
            content = """▸ S:
{{patient_name}} presents with heart failure symptoms.
Dyspnea: at rest / with exertion / PND / orthopnea
Edema: lower extremity / abdominal / none
Weight change: gained [X] lbs over [X] days
Diet compliance: low sodium adherence
Medication compliance: taking all medications as prescribed
Current medications: {{medications}}

▸ O:
Vitals: {{vitals}}
General: Mild respiratory distress / no acute distress
Neck: JVD present / absent
CV: Irregularly irregular / regular, S3 present / absent
Lungs: Crackles bases / clear
Abdomen: Hepatomegaly present / absent
Extremities: 2+ pitting edema / trace / none
Daily weight: [X] kg

▸ A:
Heart Failure - NYHA Class [I-IV]
Acute exacerbation / compensated
EF: [X]% (HFrEF / HFpEF)
{{conditions}}

▸ P:
• IV diuretics: Lasix [X]mg IV
• Daily weights and strict I/Os
• Fluid restriction 1.5-2L/day
• Low sodium diet <2g/day
• Optimize GDMT: BB, ACEi/ARB/ARNI, MRA, SGLT2i
• BNP/proBNP trending
• Consider inotropes if decompensated
• Echo if not recent"""
        ),
        "cardiology_afib" to NoteTemplate(
            name = "Cardiology - Atrial Fibrillation",
            category = "Cardiology",
            noteType = "SOAP",
            content = """▸ S:
{{patient_name}} presents with atrial fibrillation.
Symptoms: palpitations / chest discomfort / dyspnea / fatigue / asymptomatic
Duration: paroxysmal / persistent / permanent
Onset: [date/time]
Triggers identified: alcohol, caffeine, stress, illness
Current medications: {{medications}}

▸ O:
Vitals: {{vitals}}
General: No acute distress
CV: Irregularly irregular rhythm, rate [X], no murmurs
Lungs: Clear bilaterally
Extremities: No edema

▸ A:
Atrial Fibrillation - paroxysmal / persistent / permanent
Rate: controlled / uncontrolled
CHADS2-VASc Score: [X]
HAS-BLED Score: [X]
{{conditions}}

▸ P:
Rate control:
• Beta-blocker: Metoprolol [X]mg
• Or Diltiazem [X]mg
Target HR <110 at rest

Anticoagulation (CHADS2-VASc ≥2):
• Apixaban 5mg BID / Rivaroxaban 20mg daily / Warfarin
• Bleeding risk counseling provided

Rhythm control (if indicated):
• Consider cardioversion if <48h or anticoagulated ≥3 weeks
• Antiarrhythmic consideration
• Cardiology/EP referral"""
        ),

        // ORTHOPEDICS
        "ortho_joint_pain" to NoteTemplate(
            name = "Orthopedics - Joint Pain",
            category = "Orthopedics",
            noteType = "SOAP",
            content = """▸ S:
{{patient_name}} presents with joint pain.
Location: [specific joint]
Laterality: right / left / bilateral
Onset: acute / chronic / gradual
Duration: [X] days/weeks/months
Mechanism: injury / overuse / spontaneous
Quality: sharp / dull / aching / throbbing
Severity: [X]/10
Aggravating factors: movement / weight-bearing / rest
Alleviating factors: rest / ice / heat / medications
Associated: swelling, stiffness, locking, instability, weakness
Prior episodes: yes / no
Current medications: {{medications}}

▸ O:
Vitals: {{vitals}}
Inspection: Swelling / erythema / deformity / atrophy
Palpation: Point tenderness at [location]
ROM: Active [X]° / Passive [X]° (normal [X]°)
Strength: [X]/5
Special tests: [test name] positive / negative
Neurovascular: Intact distally

▸ A:
[Diagnosis] - right/left [joint]
Differential: OA, RA, gout, septic arthritis, bursitis, tendinitis
{{conditions}}

▸ P:
• RICE: Rest, Ice, Compression, Elevation
• NSAIDs: Ibuprofen 600mg TID with food
• Activity modification
• Physical therapy referral
• X-ray [joint] if not done
• Consider MRI if no improvement
• Follow up in [X] weeks"""
        ),
        "ortho_fracture" to NoteTemplate(
            name = "Orthopedics - Fracture Follow-up",
            category = "Orthopedics",
            noteType = "SOAP",
            content = """▸ S:
{{patient_name}} presents for fracture follow-up.
Fracture: [bone] fracture, [date of injury]
Treatment: cast / splint / ORIF / conservative
Pain level: [X]/10 (improving / stable / worsening)
Swelling: improved / stable / worse
Neurovascular symptoms: numbness / tingling / none
Weight-bearing status: non-weight bearing / TTWB / WBAT / FWB
Compliance with restrictions: yes / no

▸ O:
Vitals: {{vitals}}
Cast/Splint: Intact, no odor, no drainage
Skin: Intact at edges, no pressure sores
Distal circulation: Cap refill <2 sec, pulses palpable
Sensation: Intact to light touch
Motor: [X]/5 strength distal to injury

X-ray findings: [describe alignment, callus formation, hardware position]

▸ A:
[Bone] fracture - [weeks] post injury/surgery
Healing: progressing well / delayed union / non-union concern
{{conditions}}

▸ P:
• Continue immobilization for [X] more weeks
• Weight-bearing status: [status]
• Pain management: [medication]
• Repeat X-ray in [X] weeks
• Physical therapy when cleared
• Return precautions given
• Follow up in [X] weeks"""
        ),

        // NEUROLOGY
        "neuro_headache" to NoteTemplate(
            name = "Neurology - Headache Evaluation",
            category = "Neurology",
            noteType = "HP",
            content = """▸ CHIEF COMPLAINT:
Headache evaluation

▸ HPI:
{{patient_name}} presents with headache.
Location: frontal / temporal / occipital / unilateral / bilateral
Quality: throbbing / pressure / sharp / dull
Severity: [X]/10
Duration: [X] hours/days
Frequency: [X] episodes per week/month
Aura: visual / sensory / motor / none
Associated: nausea, vomiting, photophobia, phonophobia
Red flags: worst headache, thunderclap, fever, neuro deficits, papilledema
Triggers: stress, sleep, foods, menses
Family history of migraines: yes / no

▸ PAST MEDICAL HISTORY:
{{conditions}}

▸ MEDICATIONS:
{{medications}}
Previous headache treatments tried: [list]

▸ ALLERGIES:
{{allergies}}

▸ PHYSICAL EXAM:
Vitals: {{vitals}}
General: Comfortable / photophobic / distressed
HEENT: No temporal artery tenderness, sinuses non-tender
Neck: Supple, no meningismus
Neuro: CN II-XII intact, strength 5/5, sensation intact, reflexes 2+, coordination normal
Fundoscopic: No papilledema

▸ ASSESSMENT:
Headache - Primary: Migraine / Tension / Cluster
Secondary causes ruled out

▸ PLAN:
Acute treatment:
• NSAIDs / Triptans / Antiemetics

Preventive (if frequent):
• Beta-blocker / Topiramate / Amitriptyline / CGRP inhibitor

Lifestyle:
• Headache diary
• Sleep hygiene
• Trigger avoidance
• Hydration
• Follow up in 4-6 weeks"""
        ),
        "neuro_stroke" to NoteTemplate(
            name = "Neurology - Stroke Follow-up",
            category = "Neurology",
            noteType = "SOAP",
            content = """▸ S:
{{patient_name}} presents for stroke follow-up.
Stroke date: [date]
Type: ischemic / hemorrhagic
Territory: MCA / PCA / ACA / vertebrobasilar
Treatment received: tPA / thrombectomy / conservative
Residual deficits: weakness / numbness / speech / vision / none
Rehabilitation: PT / OT / Speech therapy
Medication compliance: yes / no
Current medications: {{medications}}

▸ O:
Vitals: {{vitals}}
General: Alert and oriented x3
Speech: Fluent / non-fluent / dysarthric
Cranial Nerves: [document any deficits]
Motor: RUE [X]/5, RLE [X]/5, LUE [X]/5, LLE [X]/5
Sensation: Intact / diminished [location]
Coordination: Finger-to-nose, heel-to-shin
Gait: Normal / wide-based / hemiparetic
NIHSS Score: [X]

▸ A:
Status post [ischemic/hemorrhagic] stroke - [territory]
[X] weeks/months post event
Functional status: improving / stable / declining
{{conditions}}

▸ P:
Secondary Prevention:
• Antiplatelet: ASA 81mg / Plavix 75mg / Aggrenox
• Statin: High-intensity (Atorvastatin 80mg)
• BP goal <130/80
• Diabetes control if applicable
• Smoking cessation

Ongoing:
• Continue rehabilitation
• Driving restrictions discussed
• Depression screening
• Follow up MRI/MRA if indicated
• Neurology follow-up in [X] months"""
        ),

        // GASTROENTEROLOGY
        "gi_abdominal_pain" to NoteTemplate(
            name = "GI - Abdominal Pain",
            category = "Gastroenterology",
            noteType = "HP",
            content = """▸ CHIEF COMPLAINT:
Abdominal pain evaluation

▸ HPI:
{{patient_name}} presents with abdominal pain.
Location: RUQ / LUQ / RLQ / LLQ / epigastric / periumbilical / diffuse
Quality: sharp / crampy / burning / colicky
Severity: [X]/10
Onset: sudden / gradual
Duration: [X] hours/days
Radiation: back / shoulder / groin
Timing: constant / intermittent / postprandial
Associated: nausea, vomiting, diarrhea, constipation, fever, blood
Last bowel movement: [date], quality
Last meal: [time]
Menstrual history (if applicable): LMP [date]

▸ PAST MEDICAL HISTORY:
{{conditions}}
Prior abdominal surgeries: [list]

▸ MEDICATIONS:
{{medications}}

▸ ALLERGIES:
{{allergies}}

▸ PHYSICAL EXAM:
Vitals: {{vitals}}
General: Comfortable / distressed, lying still / moving
Abdomen:
  Inspection: Flat / distended, no surgical scars / scars present
  Auscultation: Bowel sounds present / hyperactive / absent
  Palpation: Soft / rigid, tender [location], no rebound / guarding
  Special signs: Murphy's / McBurney's / Rovsing's / psoas negative

▸ DIAGNOSTICS:
Labs: CBC, CMP, lipase, UA, urine pregnancy
Imaging: CT abdomen/pelvis / ultrasound / X-ray

▸ ASSESSMENT:
Abdominal pain - differential includes [list based on location]

▸ PLAN:
• NPO status
• IV fluids
• Pain management
• Labs and imaging as above
• Surgical consultation if indicated
• GI consultation if indicated"""
        ),
        "gi_gerd" to NoteTemplate(
            name = "GI - GERD Follow-up",
            category = "Gastroenterology",
            noteType = "SOAP",
            content = """▸ S:
{{patient_name}} presents for GERD follow-up.
Symptoms: heartburn / regurgitation / dysphagia / chest pain
Frequency: daily / weekly / monthly
Timing: postprandial / nocturnal / with bending
Triggers: spicy foods, citrus, caffeine, alcohol, large meals
Alarm symptoms: weight loss / dysphagia / bleeding / anemia - NONE
PPI compliance: taking as prescribed
Current medications: {{medications}}

▸ O:
Vitals: {{vitals}}
General: No acute distress
Abdomen: Soft, non-tender, no organomegaly
Oropharynx: No erythema or lesions

▸ A:
GERD - controlled / uncontrolled
No alarm symptoms
{{conditions}}

▸ P:
Medications:
• Continue PPI: [medication] [dose] daily/BID
• Step down to H2 blocker if controlled >8 weeks
• PRN antacids

Lifestyle modifications:
• Avoid trigger foods
• Small frequent meals
• No eating 3 hours before bed
• Elevate head of bed
• Weight loss if overweight
• Smoking cessation

If refractory:
• EGD referral
• pH monitoring
• Consider GI referral
• Follow up in [X] months"""
        ),

        // PULMONOLOGY
        "pulm_copd" to NoteTemplate(
            name = "Pulmonology - COPD",
            category = "Pulmonology",
            noteType = "SOAP",
            content = """▸ S:
{{patient_name}} presents for COPD management.
Baseline dyspnea: at rest / with activity / with exertion
Current symptoms: stable / worsening
Exacerbations in past year: [X]
Hospitalizations in past year: [X]
Oxygen use: none / PRN / continuous at [X] L/min
Smoking status: current / former / never, [X] pack-years
Inhaler technique reviewed: yes
Medication compliance: yes / no
Current medications: {{medications}}

▸ O:
Vitals: {{vitals}}
SpO2: [X]% on room air / [X]L O2
General: No acute distress / using accessory muscles
Chest: Barrel chest / normal
Lungs: Decreased breath sounds / wheezes / prolonged expiration
Extremities: No clubbing or cyanosis

▸ A:
COPD - GOLD Stage [I-IV], Group [A-D]
FEV1: [X]% predicted
Currently: stable / acute exacerbation
{{conditions}}

▸ P:
Maintenance therapy (stepwise):
• LAMA: Tiotropium / Umeclidinium
• LABA: Salmeterol / Formoterol
• ICS (if frequent exacerbations): Fluticasone / Budesonide
• Triple therapy if severe

Rescue: Albuterol PRN

Preventive:
• Annual flu vaccine
• Pneumococcal vaccines (PCV20, PPSV23)
• Smoking cessation counseling
• Pulmonary rehabilitation referral

Monitoring:
• PFTs annually
• Assess CAT score / mMRC dyspnea
• Follow up in [X] months"""
        ),
        "pulm_asthma" to NoteTemplate(
            name = "Pulmonology - Asthma",
            category = "Pulmonology",
            noteType = "SOAP",
            content = """▸ S:
{{patient_name}} presents for asthma management.
Daytime symptoms: [X] times per week
Nighttime symptoms: [X] times per month
Rescue inhaler use: [X] times per week
Activity limitation: yes / no
Exacerbations: [X] in past year requiring steroids / ED / hospitalization
Triggers: allergens, exercise, cold air, illness, stress
Peak flow: [X] L/min (personal best [X])
Current medications: {{medications}}

▸ O:
Vitals: {{vitals}}
SpO2: [X]% on room air
General: No acute distress / mild distress / severe distress
Lungs: Clear / wheezes / prolonged expiration
Peak flow: [X] L/min ([X]% of personal best)

▸ A:
Asthma - intermittent / mild persistent / moderate persistent / severe persistent
Currently: well-controlled / not well-controlled / very poorly controlled
{{conditions}}

▸ P:
Step therapy (based on control):
Step 1: PRN SABA (albuterol)
Step 2: Add low-dose ICS
Step 3: Low-dose ICS + LABA or medium-dose ICS
Step 4: Medium-dose ICS + LABA
Step 5: High-dose ICS + LABA, consider biologics

Current regimen:
• Controller: [medication]
• Rescue: Albuterol 2 puffs PRN

Action plan:
• Green zone: Continue maintenance
• Yellow zone: Increase controller, add rescue
• Red zone: Oral steroids, seek care

• Trigger avoidance education
• Spacer technique reviewed
• Peak flow monitoring
• Follow up in [X] months"""
        ),

        // PSYCHIATRY
        "psych_depression" to NoteTemplate(
            name = "Psychiatry - Depression",
            category = "Psychiatry",
            noteType = "SOAP",
            content = """▸ S:
{{patient_name}} presents for depression management.
PHQ-9 Score: [X]/27
Mood: depressed / sad / hopeless / irritable
Duration: [X] weeks/months
Sleep: insomnia / hypersomnia / [X] hours per night
Appetite: decreased / increased / stable
Energy: low / fatigue
Concentration: impaired / intact
Interest/pleasure: anhedonia present / absent
Psychomotor: agitation / retardation / normal
Guilt: excessive / appropriate
Suicidal ideation: DENIES / passive ("better off dead") / active with plan
Safety: No access to firearms / medications secured
Substance use: alcohol [X]/week, drugs none
Current medications: {{medications}}

▸ O:
Vitals: {{vitals}}
Appearance: Groomed / disheveled
Behavior: Cooperative / guarded / agitated
Speech: Normal rate/tone / slow / pressured
Mood: "depressed" / "[patient's words]"
Affect: Constricted / flat / congruent / tearful
Thought process: Linear / circumstantial
Thought content: No SI/HI, no delusions
Cognition: Alert and oriented x3
Insight/Judgment: Fair / poor / good

▸ A:
Major Depressive Disorder - mild / moderate / severe
Episode: single / recurrent
PHQ-9: [X] (minimal/mild/moderate/moderately severe/severe)
{{conditions}}

▸ P:
Pharmacotherapy:
• SSRI: [medication] [dose] (continue / start / adjust)
• Consider augmentation if partial response

Psychotherapy:
• CBT / IPT referral
• Continue current therapy

Safety:
• Crisis resources provided (988 Suicide & Crisis Lifeline)
• Safety plan reviewed
• Emergency plan if worsening

Lifestyle:
• Sleep hygiene
• Exercise recommendation
• Social support engagement
• Follow up in [X] weeks"""
        ),
        "psych_anxiety" to NoteTemplate(
            name = "Psychiatry - Anxiety",
            category = "Psychiatry",
            noteType = "SOAP",
            content = """▸ S:
{{patient_name}} presents for anxiety management.
GAD-7 Score: [X]/21
Primary symptoms: worry / panic / social anxiety / specific phobia
Duration: [X] weeks/months
Panic attacks: frequency [X]/week, duration [X] minutes
Physical symptoms: palpitations, sweating, tremor, GI upset, dyspnea
Avoidance behaviors: [describe]
Functional impairment: work / social / daily activities
Sleep: difficulty initiating / maintaining / [X] hours
Substances: caffeine / alcohol / none
Current medications: {{medications}}

▸ O:
Vitals: {{vitals}}
Appearance: Anxious / restless / fidgeting / calm
Behavior: Cooperative / hypervigilant
Speech: Rapid / normal / pressured
Mood: "anxious" / "nervous"
Affect: Anxious / constricted
Thought process: Linear / racing
Thought content: Worried about [topics], no SI/HI
Cognition: Intact, distractible
Insight/Judgment: Fair

▸ A:
Generalized Anxiety Disorder / Panic Disorder / Social Anxiety
GAD-7: [X] (minimal/mild/moderate/severe)
{{conditions}}

▸ P:
Pharmacotherapy:
• First-line: SSRI/SNRI - [medication] [dose]
• PRN rescue: Hydroxyzine 25mg for acute anxiety
• Avoid benzodiazepines if possible (short-term only if needed)

Psychotherapy:
• CBT referral (gold standard)
• Exposure therapy if specific phobia

Lifestyle:
• Limit caffeine
• Regular exercise
• Sleep hygiene
• Relaxation techniques (deep breathing, mindfulness)

• Follow up in [X] weeks"""
        ),

        // EMERGENCY
        "ed_trauma" to NoteTemplate(
            name = "Emergency - Trauma",
            category = "Emergency",
            noteType = "HP",
            content = """▸ CHIEF COMPLAINT:
Trauma evaluation - [mechanism]

▸ HPI:
{{patient_name}} presents following [mechanism of injury].
Time of injury: [time]
Mechanism: MVC / fall / assault / penetrating / blunt
Loss of consciousness: yes / no, duration [X]
Neck pain: yes / no
Back pain: yes / no
Extremity complaints: [list]
Ambulatory at scene: yes / no
GCS at scene: [X]/15

▸ ALLERGIES:
{{allergies}}

▸ MEDICATIONS:
{{medications}}
Anticoagulants: yes / no

▸ PRIMARY SURVEY:
A - Airway: Patent / compromised, C-spine immobilized
B - Breathing: Bilateral breath sounds, no crepitus, SpO2 [X]%
C - Circulation: HR [X], BP [X], pulses present, no active hemorrhage
D - Disability: GCS [X] (E[X]V[X]M[X]), pupils equal/reactive
E - Exposure: Temp [X], logrolled, no deformities

▸ SECONDARY SURVEY:
Head: No lacerations, no hematoma, no step-off
Face: No deformity, no malocclusion
Neck: Midline, no TTP, C-collar in place
Chest: No crepitus, no flail, breath sounds equal
Abdomen: Soft, non-tender / tender [location], no distension
Pelvis: Stable, no tenderness
Spine: No step-off, no midline TTP
Extremities: No deformity, pulses intact, sensation intact
Neuro: Moving all extremities, no focal deficits

▸ DIAGNOSTICS:
Labs: Type and screen, CBC, CMP, coags, lactate, UA
Imaging: CXR, pelvis XR, FAST exam, CT [areas]

▸ ASSESSMENT:
Trauma - [blunt/penetrating] to [areas]
Injuries identified: [list]

▸ PLAN:
• Trauma team activation if indicated
• Resuscitation: [IV fluids, blood products if needed]
• Pain management
• Tetanus prophylaxis if indicated
• Trauma surgery consultation
• Admit / observe / discharge with precautions"""
        ),
        "ed_sepsis" to NoteTemplate(
            name = "Emergency - Sepsis",
            category = "Emergency",
            noteType = "HP",
            content = """▸ CHIEF COMPLAINT:
Sepsis evaluation / Suspected infection

▸ HPI:
{{patient_name}} presents with suspected sepsis.
Source suspected: pulmonary / urinary / abdominal / skin/soft tissue / unknown
Symptoms: fever / chills / altered mental status / weakness
Duration: [X] hours/days
Associated: cough / dysuria / abdominal pain / wound
Immune status: normal / immunocompromised
Recent antibiotics: yes / no
Recent hospitalization: yes / no

▸ PAST MEDICAL HISTORY:
{{conditions}}

▸ MEDICATIONS:
{{medications}}

▸ ALLERGIES:
{{allergies}}

▸ PHYSICAL EXAM:
Vitals: {{vitals}}
SIRS Criteria: Temp >38 or <36, HR >90, RR >20, WBC >12k or <4k
qSOFA: AMS, SBP ≤100, RR ≥22

General: Ill-appearing / toxic / diaphoretic
Mental status: Alert / confused / obtunded
Skin: Warm / cool, mottled / petechiae / rash
Lungs: Clear / crackles / rhonchi
CV: Tachycardic, hypotensive / normotensive
Abdomen: Soft / tender / peritoneal signs
GU: CVA tenderness / suprapubic tenderness

▸ DIAGNOSTICS:
Labs: CBC, CMP, lactate, procalcitonin, coags, blood cultures x2
UA and urine culture
CXR
Consider: CT chest/abdomen/pelvis, LP

▸ SEPSIS BUNDLE - HOUR 1:
[ ] Lactate measured: [X] mmol/L
[ ] Blood cultures before antibiotics
[ ] Broad-spectrum antibiotics given: [medication]
[ ] Crystalloid 30 mL/kg for hypotension/lactate ≥4
[ ] Vasopressors if hypotensive after fluids (MAP ≥65)

▸ ASSESSMENT:
Sepsis / Severe sepsis / Septic shock
Source: [suspected source]
SOFA Score: [X]

▸ PLAN:
• Continue aggressive resuscitation
• Source control if identified
• ICU admission for shock
• Re-measure lactate if initial >2
• Central line / arterial line if vasopressors
• Reassess volume status frequently"""
        )
    )

    // Data class for note templates
    data class NoteTemplate(
        val name: String,
        val category: String,
        val noteType: String,  // SOAP, HP, PROGRESS, CONSULT
        val content: String
    )

    // ═══════════════════════════════════════════════════════════════════════════
    // VOICE ORDERS - Data Classes
    // ═══════════════════════════════════════════════════════════════════════════

    // Order type enum
    enum class OrderType {
        LAB, IMAGING, MEDICATION
    }

    // Order status enum
    enum class OrderStatus {
        PENDING, CONFIRMED, CANCELLED
    }

    // Safety warning types
    enum class SafetyWarningType {
        ALLERGY, DRUG_INTERACTION, DUPLICATE_ORDER, CONTRAINDICATION
    }

    // Safety warning data class
    data class SafetyWarning(
        val type: SafetyWarningType,
        val severity: String,  // "high", "moderate", "low"
        val message: String,
        val details: String = ""
    )

    // Order data class
    data class Order(
        val id: String = java.util.UUID.randomUUID().toString(),
        val type: OrderType,
        val name: String,                    // "CBC", "Amoxicillin"
        val displayName: String,             // "Complete Blood Count"
        val details: String = "",            // "500mg TID x 10 days"
        val status: OrderStatus = OrderStatus.PENDING,
        val timestamp: Long = System.currentTimeMillis(),
        val safetyWarnings: List<SafetyWarning> = emptyList(),
        val requiresConfirmation: Boolean = false,
        // Medication-specific fields
        val dose: String? = null,
        val frequency: String? = null,
        val duration: String? = null,
        val route: String? = null,
        val prn: Boolean = false,
        // Imaging-specific fields
        val contrast: Boolean? = null,
        val bodyPart: String? = null,
        val laterality: String? = null
    ) {
        fun toJson(): org.json.JSONObject {
            return org.json.JSONObject().apply {
                put("id", id)
                put("type", type.name)
                put("name", name)
                put("displayName", displayName)
                put("details", details)
                put("status", status.name)
                put("timestamp", timestamp)
                put("dose", dose)
                put("frequency", frequency)
                put("duration", duration)
                put("route", route)
                put("prn", prn)
                put("contrast", contrast)
                put("bodyPart", bodyPart)
                put("laterality", laterality)
                put("safetyWarnings", org.json.JSONArray().apply {
                    safetyWarnings.forEach { warning ->
                        put(org.json.JSONObject().apply {
                            put("type", warning.type.name)
                            put("severity", warning.severity)
                            put("message", warning.message)
                            put("details", warning.details)
                        })
                    }
                })
            }
        }

        companion object {
            fun fromJson(json: org.json.JSONObject): Order {
                val warnings = mutableListOf<SafetyWarning>()
                val warningsArray = json.optJSONArray("safetyWarnings")
                if (warningsArray != null) {
                    for (i in 0 until warningsArray.length()) {
                        val w = warningsArray.getJSONObject(i)
                        warnings.add(SafetyWarning(
                            type = SafetyWarningType.valueOf(w.getString("type")),
                            severity = w.getString("severity"),
                            message = w.getString("message"),
                            details = w.optString("details", "")
                        ))
                    }
                }
                return Order(
                    id = json.getString("id"),
                    type = OrderType.valueOf(json.getString("type")),
                    name = json.getString("name"),
                    displayName = json.getString("displayName"),
                    details = json.optString("details", ""),
                    status = OrderStatus.valueOf(json.getString("status")),
                    timestamp = json.getLong("timestamp"),
                    safetyWarnings = warnings,
                    dose = json.optString("dose", null),
                    frequency = json.optString("frequency", null),
                    duration = json.optString("duration", null),
                    route = json.optString("route", null),
                    prn = json.optBoolean("prn", false),
                    contrast = if (json.has("contrast") && !json.isNull("contrast")) json.getBoolean("contrast") else null,
                    bodyPart = json.optString("bodyPart", null),
                    laterality = json.optString("laterality", null)
                )
            }
        }
    }

    // Lab order info
    data class LabOrderInfo(
        val name: String,
        val displayName: String,
        val cptCode: String,
        val aliases: List<String>
    )

    // Imaging order info
    data class ImagingOrderInfo(
        val name: String,
        val displayName: String,
        val cptCode: String,
        val bodyPart: String,
        val modality: String,
        val aliases: List<String>,
        val supportsContrast: Boolean = false
    )

    // Medication order info
    data class MedicationOrderInfo(
        val name: String,
        val drugClass: String,
        val commonDoses: List<String>,
        val commonFrequencies: List<String>,
        val commonDurations: List<String>,
        val route: String,
        val aliases: List<String>,
        val interactionsWith: List<String>,
        val allergyCrossReact: List<String>,
        val isControlled: Boolean = false
    )

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

    // ============ Voice Template Functions ============

    /**
     * Apply a template to the current note, replacing variables with patient data.
     */
    private fun applyTemplate(templateKey: String) {
        val template = builtInTemplates[templateKey] ?: getUserTemplate(templateKey)
        if (template == null) {
            Toast.makeText(this, "Template not found: $templateKey", Toast.LENGTH_SHORT).show()
            speakFeedback("Template not found")
            return
        }

        // Need a patient loaded for auto-fill
        val patient = currentPatientData
        if (patient == null) {
            Toast.makeText(this, "Load a patient first", Toast.LENGTH_SHORT).show()
            speakFeedback("Load a patient first to use templates")
            return
        }

        // Replace variables with patient data
        val filledContent = fillTemplateVariables(template.content, patient)

        // Set note type based on template
        currentNoteType = template.noteType

        // Show the note in edit overlay
        showNoteForEditing(filledContent, template.noteType)

        speakFeedback("${template.name} template applied")
        transcriptText.text = "Template: ${template.name}"
        Log.d(TAG, "Applied template: ${template.name}")
    }

    /**
     * Fill template variables with patient data.
     * Variables: {{patient_name}}, {{dob}}, {{age}}, {{gender}}, {{medications}}, {{allergies}}, {{vitals}}, {{conditions}}, {{date}}
     */
    private fun fillTemplateVariables(content: String, patient: JSONObject): String {
        var result = content

        // Patient name
        val name = patient.optString("name", "Patient")
        result = result.replace("{{patient_name}}", name)

        // Date of birth
        val dob = patient.optString("date_of_birth", "Unknown")
        result = result.replace("{{dob}}", dob)

        // Calculate age from DOB
        val age = calculateAge(dob)
        result = result.replace("{{age}}", age)

        // Gender
        val gender = patient.optString("gender", "").lowercase()
        val genderText = when (gender) {
            "male" -> "male"
            "female" -> "female"
            else -> gender
        }
        result = result.replace("{{gender}}", genderText)

        // Current date
        val dateFormat = java.text.SimpleDateFormat("MMMM d, yyyy", Locale.US)
        val currentDate = dateFormat.format(java.util.Date())
        result = result.replace("{{date}}", currentDate)

        // Medications
        val medications = patient.optJSONArray("medications")
        val medsText = if (medications != null && medications.length() > 0) {
            val medList = mutableListOf<String>()
            for (i in 0 until minOf(medications.length(), 5)) {
                val med = medications.optJSONObject(i)
                val medName = med?.optString("name", "") ?: ""
                if (medName.isNotEmpty()) medList.add(medName)
            }
            if (medList.isEmpty()) "None documented" else medList.joinToString(", ")
        } else {
            "None documented"
        }
        result = result.replace("{{medications}}", medsText)

        // Allergies
        val allergies = patient.optJSONArray("allergies")
        val allergiesText = if (allergies != null && allergies.length() > 0) {
            val allergyList = mutableListOf<String>()
            for (i in 0 until allergies.length()) {
                val allergy = allergies.optJSONObject(i)
                val allergyName = allergy?.optString("substance", "") ?: ""
                if (allergyName.isNotEmpty()) allergyList.add(allergyName)
            }
            if (allergyList.isEmpty()) "NKDA" else allergyList.joinToString(", ")
        } else {
            "NKDA"
        }
        result = result.replace("{{allergies}}", allergiesText)

        // Vitals
        val vitals = patient.optJSONArray("vitals")
        val vitalsText = if (vitals != null && vitals.length() > 0) {
            val vitalList = mutableListOf<String>()
            for (i in 0 until minOf(vitals.length(), 5)) {
                val vital = vitals.optJSONObject(i)
                val vitalName = vital?.optString("type", "") ?: ""
                val vitalValue = vital?.optString("value", "") ?: ""
                val vitalUnit = vital?.optString("unit", "") ?: ""
                if (vitalName.isNotEmpty() && vitalValue.isNotEmpty()) {
                    vitalList.add("$vitalName: $vitalValue $vitalUnit".trim())
                }
            }
            if (vitalList.isEmpty()) "Not available" else vitalList.joinToString(", ")
        } else {
            "Not available"
        }
        result = result.replace("{{vitals}}", vitalsText)

        // Conditions
        val conditions = patient.optJSONArray("conditions")
        val conditionsText = if (conditions != null && conditions.length() > 0) {
            val condList = mutableListOf<String>()
            for (i in 0 until minOf(conditions.length(), 5)) {
                val condition = conditions.optJSONObject(i)
                val condName = condition?.optString("name", "") ?: ""
                if (condName.isNotEmpty()) condList.add("• $condName")
            }
            if (condList.isEmpty()) "None documented" else condList.joinToString("\n")
        } else {
            "None documented"
        }
        result = result.replace("{{conditions}}", conditionsText)

        return result
    }

    /**
     * Calculate age from date of birth string.
     */
    private fun calculateAge(dob: String): String {
        try {
            val formats = listOf(
                java.text.SimpleDateFormat("yyyy-MM-dd", Locale.US),
                java.text.SimpleDateFormat("MM/dd/yyyy", Locale.US)
            )
            for (format in formats) {
                try {
                    val birthDate = format.parse(dob) ?: continue
                    val today = java.util.Calendar.getInstance()
                    val birth = java.util.Calendar.getInstance().apply { time = birthDate }

                    var age = today.get(java.util.Calendar.YEAR) - birth.get(java.util.Calendar.YEAR)
                    if (today.get(java.util.Calendar.DAY_OF_YEAR) < birth.get(java.util.Calendar.DAY_OF_YEAR)) {
                        age--
                    }
                    return age.toString()
                } catch (e: Exception) {
                    continue
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error calculating age: ${e.message}")
        }
        return "Unknown"
    }

    /**
     * Show the template list overlay.
     */
    private fun showTemplateListOverlay() {
        val sb = StringBuilder()
        sb.append("📋 AVAILABLE TEMPLATES\n")
        sb.append("${"═".repeat(30)}\n\n")

        // Group by category
        val categories = builtInTemplates.values.groupBy { it.category }

        for ((category, templates) in categories) {
            sb.append("▸ $category\n")
            for (template in templates) {
                val key = builtInTemplates.entries.find { it.value == template }?.key ?: ""
                sb.append("  • ${template.name} (\"use $key template\")\n")
            }
            sb.append("\n")
        }

        // User templates
        val userTemplates = getUserTemplates()
        if (userTemplates.isNotEmpty()) {
            sb.append("▸ My Templates\n")
            for ((key, template) in userTemplates) {
                sb.append("  • ${template.name} (\"use $key template\")\n")
            }
            sb.append("\n")
        }

        sb.append("${"─".repeat(30)}\n")
        sb.append("Say \"use [name] template\" to apply")

        showDataOverlay("Note Templates", sb.toString())
        speakFeedback("${builtInTemplates.size} templates available")
        Log.d(TAG, "Showing template list")
    }

    /**
     * Show note content for editing (used by templates).
     */
    private fun showNoteForEditing(content: String, noteType: String) {
        // Store the note for editing
        editableNoteContent = content
        isNoteEditing = true
        editHistory.clear()

        // Create a mock note object for the existing edit overlay
        val noteJson = JSONObject().apply {
            put("content", content)
            put("note_type", noteType)
        }
        lastGeneratedNote = noteJson

        // Show the edit overlay
        showNoteEditOverlay(content)
    }

    /**
     * Show note edit overlay (extracted for reuse with templates).
     */
    private fun showNoteEditOverlay(content: String) {
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

            // Title row with note type
            val titleRow = android.widget.LinearLayout(context).apply {
                orientation = android.widget.LinearLayout.HORIZONTAL
                gravity = android.view.Gravity.CENTER_VERTICAL
                setPadding(0, 0, 0, 8)
            }

            val titleText = TextView(context).apply {
                text = "📝 Edit Note"
                textSize = getTitleFontSize()
                setTextColor(0xFF10B981.toInt())
                layoutParams = android.widget.LinearLayout.LayoutParams(0, android.widget.LinearLayout.LayoutParams.WRAP_CONTENT, 1f)
            }
            titleRow.addView(titleText)
            innerLayout.addView(titleRow)

            // Hint text
            val hintText = TextView(context).apply {
                text = "Edit the note below, then tap SAVE or say 'save note'"
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
                setBackgroundColor(0x00000000)
                setPadding(16, 16, 16, 16)
                gravity = android.view.Gravity.TOP or android.view.Gravity.START
                inputType = android.text.InputType.TYPE_CLASS_TEXT or
                        android.text.InputType.TYPE_TEXT_FLAG_MULTI_LINE or
                        android.text.InputType.TYPE_TEXT_FLAG_NO_SUGGESTIONS
                isSingleLine = false
                minLines = 10

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

            // Button row
            val buttonRow = android.widget.LinearLayout(context).apply {
                orientation = android.widget.LinearLayout.HORIZONTAL
                setPadding(0, 16, 0, 0)
            }

            // Reset button
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
                    editHistory.clear()
                    Toast.makeText(context, "Note reset", Toast.LENGTH_SHORT).show()
                }
            }
            buttonRow.addView(resetButton)

            // Save button
            val saveButton = android.widget.Button(context).apply {
                text = "💾 SAVE"
                setBackgroundColor(0xFF10B981.toInt())
                setTextColor(0xFFFFFFFF.toInt())
                textSize = 14f
                layoutParams = android.widget.LinearLayout.LayoutParams(0, android.widget.LinearLayout.LayoutParams.WRAP_CONTENT, 1f).apply {
                    marginStart = 4
                    marginEnd = 4
                }
                setOnClickListener {
                    saveCurrentNote()
                }
            }
            buttonRow.addView(saveButton)

            // Close button
            val closeButton = android.widget.Button(context).apply {
                text = "✕"
                setBackgroundColor(0xFF475569.toInt())
                setTextColor(0xFFFFFFFF.toInt())
                textSize = 14f
                layoutParams = android.widget.LinearLayout.LayoutParams(0, android.widget.LinearLayout.LayoutParams.WRAP_CONTENT, 0.5f).apply {
                    marginStart = 4
                }
                setOnClickListener {
                    hideDataOverlay()
                    noteEditText = null
                    editableNoteContent = null
                    isNoteEditing = false
                }
            }
            buttonRow.addView(closeButton)

            innerLayout.addView(buttonRow)
            addView(innerLayout)
        }

        rootView.addView(dataOverlay)
        statusText.text = "Edit Note"
        transcriptText.text = "Edit note or say 'save note'"
    }

    /**
     * Get user-created templates from SharedPreferences.
     */
    private fun getUserTemplates(): Map<String, NoteTemplate> {
        val templatesJson = cachePrefs.getString(USER_TEMPLATES_KEY, null) ?: return emptyMap()
        return try {
            val result = mutableMapOf<String, NoteTemplate>()
            val json = JSONObject(templatesJson)
            for (key in json.keys()) {
                val templateJson = json.getJSONObject(key)
                result[key] = NoteTemplate(
                    name = templateJson.optString("name", key),
                    category = templateJson.optString("category", "My Templates"),
                    noteType = templateJson.optString("noteType", "SOAP"),
                    content = templateJson.optString("content", "")
                )
            }
            result
        } catch (e: Exception) {
            Log.e(TAG, "Error loading user templates: ${e.message}")
            emptyMap()
        }
    }

    /**
     * Get a specific user template.
     */
    private fun getUserTemplate(key: String): NoteTemplate? {
        return getUserTemplates()[key]
    }

    /**
     * Save the current note as a user template.
     */
    private fun saveAsTemplate(templateName: String) {
        val content = editableNoteContent
        if (content.isNullOrEmpty()) {
            Toast.makeText(this, "No note content to save as template", Toast.LENGTH_SHORT).show()
            return
        }

        // Create template key from name
        val key = templateName.lowercase().replace(Regex("[^a-z0-9]"), "_")

        // Load existing templates
        val existingJson = cachePrefs.getString(USER_TEMPLATES_KEY, null)
        val templates = if (existingJson != null) JSONObject(existingJson) else JSONObject()

        // Add new template
        val templateJson = JSONObject().apply {
            put("name", templateName)
            put("category", "My Templates")
            put("noteType", currentNoteType)
            put("content", content)
        }
        templates.put(key, templateJson)

        // Save
        cachePrefs.edit().putString(USER_TEMPLATES_KEY, templates.toString()).apply()

        Toast.makeText(this, "Saved template: $templateName", Toast.LENGTH_SHORT).show()
        speakFeedback("Template saved as $templateName")
        Log.d(TAG, "Saved user template: $key")
    }

    /**
     * Delete a user template.
     */
    private fun deleteUserTemplate(templateName: String) {
        val key = templateName.lowercase().replace(Regex("[^a-z0-9]"), "_")

        val existingJson = cachePrefs.getString(USER_TEMPLATES_KEY, null) ?: return
        val templates = JSONObject(existingJson)

        if (templates.has(key)) {
            templates.remove(key)
            cachePrefs.edit().putString(USER_TEMPLATES_KEY, templates.toString()).apply()
            Toast.makeText(this, "Deleted template: $templateName", Toast.LENGTH_SHORT).show()
            speakFeedback("Template deleted")
            Log.d(TAG, "Deleted user template: $key")
        } else {
            Toast.makeText(this, "Template not found: $templateName", Toast.LENGTH_SHORT).show()
        }
    }

    /**
     * Find template by name (searches both built-in and user templates).
     */
    private fun findTemplateByName(name: String): String? {
        val lowerName = name.lowercase().trim()

        // Check built-in templates
        for ((key, template) in builtInTemplates) {
            if (key == lowerName || template.name.lowercase().contains(lowerName)) {
                return key
            }
        }

        // Check user templates
        for ((key, template) in getUserTemplates()) {
            if (key == lowerName || template.name.lowercase().contains(lowerName)) {
                return key
            }
        }

        // Check common aliases
        val aliases = mapOf(
            "dm" to "diabetes",
            "dm2" to "diabetes",
            "htn" to "hypertension",
            "bp" to "hypertension",
            "cold" to "uri",
            "physical" to "annual_physical",
            "wellness" to "annual_physical",
            "annual" to "annual_physical",
            "lbp" to "back_pain",
            "backache" to "back_pain",
            "chest" to "chest_pain",
            "cp" to "chest_pain",
            "peds" to "well_child",
            "child" to "well_child",
            "pediatric" to "well_child"
        )

        return aliases[lowerName]
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // CUSTOM VOICE COMMANDS - User-defined command aliases and macros
    // ═══════════════════════════════════════════════════════════════════════════

    /**
     * Get all custom commands from SharedPreferences
     */
    private fun getCustomCommands(): Map<String, CustomCommand> {
        val commandsJson = cachePrefs.getString(CUSTOM_COMMANDS_KEY, null) ?: return emptyMap()
        return try {
            val result = mutableMapOf<String, CustomCommand>()
            val json = JSONObject(commandsJson)
            for (key in json.keys()) {
                result[key] = CustomCommand.fromJson(json.getJSONObject(key))
            }
            result
        } catch (e: Exception) {
            Log.e(TAG, "Error loading custom commands: ${e.message}")
            emptyMap()
        }
    }

    /**
     * Save a custom command
     */
    private fun saveCustomCommand(command: CustomCommand) {
        val key = command.trigger.lowercase().replace(Regex("[^a-z0-9 ]"), "").trim()

        val existingJson = cachePrefs.getString(CUSTOM_COMMANDS_KEY, null)
        val commands = if (existingJson != null) JSONObject(existingJson) else JSONObject()

        commands.put(key, command.toJson())
        cachePrefs.edit().putString(CUSTOM_COMMANDS_KEY, commands.toString()).apply()

        Log.d(TAG, "Saved custom command: ${command.name} -> ${command.actions}")
    }

    /**
     * Delete a custom command
     */
    private fun deleteCustomCommand(commandName: String) {
        val key = commandName.lowercase().replace(Regex("[^a-z0-9 ]"), "").trim()

        val existingJson = cachePrefs.getString(CUSTOM_COMMANDS_KEY, null) ?: return
        val commands = JSONObject(existingJson)

        // Try exact match first
        if (commands.has(key)) {
            commands.remove(key)
            cachePrefs.edit().putString(CUSTOM_COMMANDS_KEY, commands.toString()).apply()
            speakFeedback("Deleted command: $commandName")
            Log.d(TAG, "Deleted custom command: $key")
            return
        }

        // Try partial match
        for (cmdKey in commands.keys()) {
            val cmd = CustomCommand.fromJson(commands.getJSONObject(cmdKey))
            if (cmd.name.lowercase().contains(key) || cmd.trigger.lowercase().contains(key)) {
                commands.remove(cmdKey)
                cachePrefs.edit().putString(CUSTOM_COMMANDS_KEY, commands.toString()).apply()
                speakFeedback("Deleted command: ${cmd.name}")
                Log.d(TAG, "Deleted custom command: $cmdKey")
                return
            }
        }

        speakFeedback("Command not found: $commandName")
    }

    /**
     * Find a custom command by trigger phrase
     */
    private fun findCustomCommand(phrase: String): CustomCommand? {
        val lowerPhrase = phrase.lowercase().trim()
        val commands = getCustomCommands()

        // Exact match
        for ((_, cmd) in commands) {
            if (lowerPhrase == cmd.trigger.lowercase() ||
                lowerPhrase.contains(cmd.trigger.lowercase())) {
                return cmd
            }
        }

        return null
    }

    /**
     * Execute a custom command by running its actions in sequence
     */
    private fun executeCustomCommand(command: CustomCommand) {
        Log.d(TAG, "Executing custom command: ${command.name} with ${command.actions.size} actions")
        speakFeedback("Running ${command.name}")

        // Execute actions with a small delay between each
        var delay = 0L
        for (action in command.actions) {
            android.os.Handler(mainLooper).postDelayed({
                Log.d(TAG, "Executing action: $action")
                processTranscript(action)
            }, delay)
            delay += 500L // 500ms between actions
        }
    }

    /**
     * Parse and create a custom command from voice input
     * Patterns:
     * - "create command [name] that does [action1] then [action2]"
     * - "when I say [phrase] do [action]"
     * - "teach [name] to do [action1] and [action2]"
     */
    private fun parseAndCreateCommand(input: String): Boolean {
        val lower = input.lowercase().trim()

        // Pattern: "create command [name] that does [actions]"
        val createPattern = Regex("(?:create|make|add|new) (?:command|macro|shortcut) ([\\w\\s]+?) (?:that does?|to do|which does?|:) (.+)")
        val createMatch = createPattern.find(lower)
        if (createMatch != null) {
            val name = createMatch.groupValues[1].trim()
            val actionsStr = createMatch.groupValues[2].trim()
            val actions = parseActionList(actionsStr)

            if (actions.isNotEmpty()) {
                val command = CustomCommand(
                    name = name.split(" ").joinToString(" ") { it.replaceFirstChar { c -> c.uppercase() } },
                    trigger = name,
                    actions = actions,
                    description = "Custom command created by voice"
                )
                saveCustomCommand(command)
                speakFeedback("Created command: ${command.name}. Say \"${command.trigger}\" to run it.")
                showCommandCreatedOverlay(command)
                return true
            }
        }

        // Pattern: "when I say [phrase] do [action]"
        val whenPattern = Regex("when (?:i|I) say ([\\w\\s]+?) (?:do|run|execute) (.+)")
        val whenMatch = whenPattern.find(lower)
        if (whenMatch != null) {
            val trigger = whenMatch.groupValues[1].trim()
            val actionsStr = whenMatch.groupValues[2].trim()
            val actions = parseActionList(actionsStr)

            if (actions.isNotEmpty()) {
                val command = CustomCommand(
                    name = trigger.split(" ").joinToString(" ") { it.replaceFirstChar { c -> c.uppercase() } },
                    trigger = trigger,
                    actions = actions,
                    description = "Voice alias"
                )
                saveCustomCommand(command)
                speakFeedback("Got it! When you say \"$trigger\", I'll do that.")
                return true
            }
        }

        // Pattern: "teach [name] to [action]"
        val teachPattern = Regex("teach ([\\w\\s]+?) to (.+)")
        val teachMatch = teachPattern.find(lower)
        if (teachMatch != null) {
            val name = teachMatch.groupValues[1].trim()
            val actionsStr = teachMatch.groupValues[2].trim()
            val actions = parseActionList(actionsStr)

            if (actions.isNotEmpty()) {
                val command = CustomCommand(
                    name = name.split(" ").joinToString(" ") { it.replaceFirstChar { c -> c.uppercase() } },
                    trigger = name,
                    actions = actions,
                    description = "Taught command"
                )
                saveCustomCommand(command)
                speakFeedback("Learned! Say \"$name\" to run this command.")
                return true
            }
        }

        return false
    }

    /**
     * Parse action list from voice input
     * Handles: "then", "and", "and then", commas
     */
    private fun parseActionList(actionsStr: String): List<String> {
        // Split by common separators
        val parts = actionsStr
            .replace(" and then ", "|")
            .replace(" then ", "|")
            .replace(" and ", "|")
            .replace(", ", "|")
            .replace(",", "|")
            .split("|")
            .map { it.trim() }
            .filter { it.isNotEmpty() }

        return parts
    }

    /**
     * Show overlay confirming command creation
     */
    private fun showCommandCreatedOverlay(command: CustomCommand) {
        val content = StringBuilder()
        content.append("═══════════════════════════════════\n")
        content.append("✅ COMMAND CREATED\n")
        content.append("═══════════════════════════════════\n\n")
        content.append("📢 Name: ${command.name}\n\n")
        content.append("🎤 Say: \"${command.trigger}\"\n\n")
        content.append("📋 Actions:\n")
        command.actions.forEachIndexed { index, action ->
            content.append("  ${index + 1}. $action\n")
        }
        content.append("\n───────────────────────────────────\n")
        content.append("Say \"my commands\" to see all")

        showDataOverlay("Command Created", content.toString())
    }

    /**
     * Show all custom commands
     */
    private fun showCustomCommands() {
        val commands = getCustomCommands()

        if (commands.isEmpty()) {
            speakFeedback("No custom commands yet. Say: create command morning rounds that does show vitals then show meds")
            showDataOverlay("Custom Commands", "No custom commands created yet.\n\n" +
                "📝 To create a command, say:\n" +
                "• \"Create command [name] that does [actions]\"\n" +
                "• \"When I say [phrase] do [action]\"\n" +
                "• \"Teach [name] to [actions]\"\n\n" +
                "Example:\n" +
                "\"Create command morning rounds that does\n" +
                " show vitals then show meds then show labs\"")
            return
        }

        val content = StringBuilder()
        content.append("═══════════════════════════════════\n")
        content.append("🎤 MY CUSTOM COMMANDS\n")
        content.append("═══════════════════════════════════\n\n")

        commands.values.forEachIndexed { index, cmd ->
            content.append("${index + 1}. ${cmd.name}\n")
            content.append("   Say: \"${cmd.trigger}\"\n")
            content.append("   Does: ${cmd.actions.joinToString(" → ")}\n\n")
        }

        content.append("───────────────────────────────────\n")
        content.append("• \"Delete command [name]\" to remove\n")
        content.append("• \"Create command...\" to add new")

        showDataOverlay("My Commands", content.toString())
        speakFeedback("You have ${commands.size} custom commands.")
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // MEDICAL CALCULATOR - Voice-activated clinical calculations
    // ═══════════════════════════════════════════════════════════════════════════

    /**
     * Available medical calculators
     */
    enum class MedCalcType(val displayName: String, val description: String) {
        BMI("BMI", "Body Mass Index"),
        EGFR("eGFR", "Estimated Glomerular Filtration Rate"),
        CHADS_VASC("CHADS₂-VASc", "Stroke Risk in AFib"),
        CORRECTED_CALCIUM("Corrected Calcium", "Calcium adjusted for albumin"),
        ANION_GAP("Anion Gap", "From BMP values"),
        A1C_TO_GLUCOSE("A1c to Glucose", "HbA1c to average glucose"),
        GLUCOSE_TO_A1C("Glucose to A1c", "Average glucose to HbA1c"),
        CREATININE_CLEARANCE("CrCl", "Cockcroft-Gault Creatinine Clearance"),
        WELLS_DVT("Wells DVT", "DVT Probability Score"),
        MELD("MELD", "Model for End-Stage Liver Disease"),
        MAP("MAP", "Mean Arterial Pressure"),
        BMI_PEDIATRIC("Pediatric BMI", "BMI percentile for children")
    }

    /**
     * Calculate BMI from weight (kg or lbs) and height (cm or ft/in)
     */
    private fun calculateBMI(weightKg: Double, heightCm: Double): Double {
        val heightM = heightCm / 100.0
        return weightKg / (heightM * heightM)
    }

    /**
     * Interpret BMI category
     */
    private fun interpretBMI(bmi: Double): String {
        return when {
            bmi < 18.5 -> "Underweight"
            bmi < 25.0 -> "Normal"
            bmi < 30.0 -> "Overweight"
            bmi < 35.0 -> "Obese Class I"
            bmi < 40.0 -> "Obese Class II"
            else -> "Obese Class III"
        }
    }

    /**
     * Calculate eGFR using CKD-EPI 2021 formula (race-free)
     * Returns mL/min/1.73m²
     */
    private fun calculateEGFR(creatinine: Double, age: Int, isFemale: Boolean): Double {
        // CKD-EPI 2021 (race-free) formula
        val kappa = if (isFemale) 0.7 else 0.9
        val alpha = if (isFemale) -0.241 else -0.302
        val multiplier = if (isFemale) 1.012 else 1.0

        val scrKappa = creatinine / kappa
        val minTerm = minOf(scrKappa, 1.0)
        val maxTerm = maxOf(scrKappa, 1.0)

        return 142 * Math.pow(minTerm, alpha) * Math.pow(maxTerm, -1.200) *
               Math.pow(0.9938, age.toDouble()) * multiplier
    }

    /**
     * Interpret eGFR stage
     */
    private fun interpretEGFR(egfr: Double): String {
        return when {
            egfr >= 90 -> "G1 - Normal"
            egfr >= 60 -> "G2 - Mild decrease"
            egfr >= 45 -> "G3a - Mild-moderate"
            egfr >= 30 -> "G3b - Moderate-severe"
            egfr >= 15 -> "G4 - Severe"
            else -> "G5 - Kidney failure"
        }
    }

    /**
     * Calculate corrected calcium for albumin
     */
    private fun calculateCorrectedCalcium(calcium: Double, albumin: Double): Double {
        return calcium + 0.8 * (4.0 - albumin)
    }

    /**
     * Calculate anion gap
     */
    private fun calculateAnionGap(sodium: Double, chloride: Double, bicarb: Double): Double {
        return sodium - (chloride + bicarb)
    }

    /**
     * Interpret anion gap
     */
    private fun interpretAnionGap(ag: Double): String {
        return when {
            ag < 3 -> "Low (lab error?)"
            ag <= 12 -> "Normal (3-12)"
            ag <= 20 -> "Elevated - consider MUDPILES"
            else -> "High - metabolic acidosis likely"
        }
    }

    /**
     * Convert A1c to estimated average glucose (mg/dL)
     */
    private fun a1cToGlucose(a1c: Double): Double {
        return 28.7 * a1c - 46.7
    }

    /**
     * Convert average glucose to estimated A1c
     */
    private fun glucoseToA1c(glucose: Double): Double {
        return (glucose + 46.7) / 28.7
    }

    /**
     * Calculate Mean Arterial Pressure
     */
    private fun calculateMAP(systolic: Double, diastolic: Double): Double {
        return diastolic + (systolic - diastolic) / 3.0
    }

    /**
     * Calculate Creatinine Clearance (Cockcroft-Gault)
     */
    private fun calculateCrCl(creatinine: Double, age: Int, weightKg: Double, isFemale: Boolean): Double {
        val result = ((140 - age) * weightKg) / (72 * creatinine)
        return if (isFemale) result * 0.85 else result
    }

    /**
     * Show list of available calculators
     */
    private fun showCalculatorList() {
        val content = StringBuilder()
        content.append("═══════════════════════════════════\n")
        content.append("🧮 MEDICAL CALCULATORS\n")
        content.append("═══════════════════════════════════\n\n")

        content.append("📊 BODY MEASUREMENTS\n")
        content.append("• \"Calculate BMI\" - Body Mass Index\n")
        content.append("• \"Calculate MAP\" - Mean Arterial Pressure\n\n")

        content.append("🩺 KIDNEY FUNCTION\n")
        content.append("• \"Calculate GFR\" - eGFR (CKD-EPI 2021)\n")
        content.append("• \"Calculate creatinine clearance\"\n\n")

        content.append("🧪 LAB CORRECTIONS\n")
        content.append("• \"Corrected calcium\" - Adjust for albumin\n")
        content.append("• \"Anion gap\" - From BMP\n\n")

        content.append("🩸 DIABETES\n")
        content.append("• \"A1c to glucose\" - Convert HbA1c\n")
        content.append("• \"Glucose to A1c\" - Reverse conversion\n\n")

        content.append("❤️ CARDIAC\n")
        content.append("• \"CHADS VASc\" - Stroke risk in AFib\n\n")

        content.append("───────────────────────────────────\n")
        content.append("Values auto-pulled from patient chart\n")
        content.append("when available")

        showDataOverlay("Calculators", content.toString())
        speakFeedback("12 medical calculators available. Say the calculation you need.")
    }

    /**
     * Process calculator voice command
     */
    private fun processCalculatorCommand(command: String) {
        val lower = command.lowercase()

        when {
            // BMI
            lower.contains("bmi") || lower.contains("body mass") -> {
                calculateAndShowBMI()
            }
            // eGFR
            lower.contains("gfr") || lower.contains("glomerular") ||
            lower.contains("kidney function") -> {
                calculateAndShowEGFR()
            }
            // Corrected Calcium
            lower.contains("corrected calcium") || lower.contains("calcium correct") -> {
                calculateAndShowCorrectedCalcium()
            }
            // Anion Gap
            lower.contains("anion gap") || lower.contains("anion") -> {
                calculateAndShowAnionGap()
            }
            // A1c conversions
            lower.contains("a1c to glucose") || lower.contains("a1c glucose") ||
            (lower.contains("convert") && lower.contains("a1c")) -> {
                calculateAndShowA1cToGlucose()
            }
            lower.contains("glucose to a1c") -> {
                calculateAndShowGlucoseToA1c()
            }
            // MAP
            lower.contains("map") || lower.contains("mean arterial") -> {
                calculateAndShowMAP()
            }
            // Creatinine Clearance
            lower.contains("creatinine clearance") || lower.contains("crcl") ||
            lower.contains("cockcroft") -> {
                calculateAndShowCrCl()
            }
            // CHADS-VASc
            lower.contains("chads") || lower.contains("stroke risk") -> {
                calculateAndShowCHADSVASc()
            }
            else -> {
                showCalculatorList()
            }
        }
    }

    /**
     * Calculate and show BMI using patient data or captured vitals
     */
    private fun calculateAndShowBMI() {
        // Try to get weight and height from captured vitals or patient data
        var weightKg: Double? = null
        var heightCm: Double? = null

        // Check captured vitals first
        for (vital in capturedVitals) {
            when (vital.type) {
                VitalType.WEIGHT -> {
                    val value = vital.value.replace(Regex("[^0-9.]"), "").toDoubleOrNull()
                    if (value != null) {
                        weightKg = if (vital.unit.contains("lb", ignoreCase = true)) value * 0.453592 else value
                    }
                }
                VitalType.HEIGHT -> {
                    val value = vital.value.replace(Regex("[^0-9.]"), "").toDoubleOrNull()
                    if (value != null) {
                        heightCm = if (vital.unit.contains("in", ignoreCase = true)) value * 2.54 else value
                    }
                }
                else -> {}
            }
        }

        // Try patient data if not in captured vitals
        if (weightKg == null || heightCm == null) {
            currentPatientData?.optJSONArray("vitals")?.let { vitals ->
                for (i in 0 until vitals.length()) {
                    val v = vitals.getJSONObject(i)
                    val name = v.optString("name", "").lowercase()
                    val value = v.optString("value", "").replace(Regex("[^0-9.]"), "").toDoubleOrNull()
                    val unit = v.optString("unit", "").lowercase()

                    if (value != null) {
                        when {
                            name.contains("weight") && weightKg == null -> {
                                weightKg = if (unit.contains("lb")) value * 0.453592 else value
                            }
                            name.contains("height") && heightCm == null -> {
                                heightCm = if (unit.contains("in")) value * 2.54 else value
                            }
                        }
                    }
                }
            }
        }

        val weight = weightKg
        val height = heightCm
        if (weight != null && height != null) {
            val bmi = calculateBMI(weight, height)
            val category = interpretBMI(bmi)
            val result = String.format("%.1f", bmi)

            val content = """
                |═══════════════════════════════════
                |🧮 BMI CALCULATION
                |═══════════════════════════════════
                |
                |Weight: ${String.format("%.1f", weight)} kg
                |Height: ${String.format("%.1f", height)} cm
                |
                |📊 BMI = $result
                |
                |Category: $category
                |
                |───────────────────────────────────
                |Normal range: 18.5 - 24.9
            """.trimMargin()

            showDataOverlay("BMI Result", content)
            speakFeedback("BMI is $result. Category: $category")
        } else {
            speakFeedback("Need weight and height. Say: weight 180 pounds, height 5 foot 10")
            showDataOverlay("BMI Calculator",
                "Missing data:\n\n" +
                "• Weight: ${if (weightKg != null) "✓" else "❌ needed"}\n" +
                "• Height: ${if (heightCm != null) "✓" else "❌ needed"}\n\n" +
                "Say vitals to capture:\n" +
                "\"Weight 180 pounds\"\n" +
                "\"Height 5 foot 10\"")
        }
    }

    /**
     * Calculate and show eGFR
     */
    private fun calculateAndShowEGFR() {
        var creatinine: Double? = null
        var age: Int? = null
        var isFemale: Boolean? = null

        // Get from patient data
        currentPatientData?.let { patient ->
            // Age from DOB
            patient.optString("date_of_birth", "")?.let { dob ->
                if (dob.isNotEmpty()) {
                    try {
                        val birthYear = dob.substring(0, 4).toInt()
                        val currentYear = java.util.Calendar.getInstance().get(java.util.Calendar.YEAR)
                        age = currentYear - birthYear
                    } catch (e: Exception) {}
                }
            }

            // Gender
            val gender = patient.optString("gender", "").lowercase()
            isFemale = gender == "female" || gender == "f"

            // Creatinine from labs
            patient.optJSONArray("labs")?.let { labs ->
                for (i in 0 until labs.length()) {
                    val lab = labs.getJSONObject(i)
                    val name = lab.optString("name", "").lowercase()
                    if (name.contains("creatinine") && !name.contains("clearance")) {
                        creatinine = lab.optString("value", "").replace(Regex("[^0-9.]"), "").toDoubleOrNull()
                        break
                    }
                }
            }
        }

        if (creatinine != null && age != null && isFemale != null) {
            val egfr = calculateEGFR(creatinine!!, age!!, isFemale!!)
            val stage = interpretEGFR(egfr)
            val result = String.format("%.0f", egfr)

            val content = """
                |═══════════════════════════════════
                |🧮 eGFR CALCULATION (CKD-EPI 2021)
                |═══════════════════════════════════
                |
                |Creatinine: $creatinine mg/dL
                |Age: $age years
                |Sex: ${if (isFemale!!) "Female" else "Male"}
                |
                |📊 eGFR = $result mL/min/1.73m²
                |
                |Stage: $stage
                |
                |───────────────────────────────────
                |Normal: ≥90 mL/min/1.73m²
            """.trimMargin()

            showDataOverlay("eGFR Result", content)
            speakFeedback("eGFR is $result. Stage: $stage")
        } else {
            speakFeedback("Need creatinine, age, and sex for GFR calculation")
            showDataOverlay("eGFR Calculator",
                "Missing data:\n\n" +
                "• Creatinine: ${if (creatinine != null) "$creatinine mg/dL ✓" else "❌ needed"}\n" +
                "• Age: ${if (age != null) "$age years ✓" else "❌ needed"}\n" +
                "• Sex: ${if (isFemale != null) (if (isFemale!!) "Female" else "Male") + " ✓" else "❌ needed"}\n\n" +
                "Load patient with labs to calculate")
        }
    }

    /**
     * Calculate and show corrected calcium
     */
    private fun calculateAndShowCorrectedCalcium() {
        var calcium: Double? = null
        var albumin: Double? = null

        currentPatientData?.optJSONArray("labs")?.let { labs ->
            for (i in 0 until labs.length()) {
                val lab = labs.getJSONObject(i)
                val name = lab.optString("name", "").lowercase()
                val value = lab.optString("value", "").replace(Regex("[^0-9.]"), "").toDoubleOrNull()

                when {
                    name.contains("calcium") && !name.contains("corrected") && calcium == null -> calcium = value
                    name.contains("albumin") && albumin == null -> albumin = value
                }
            }
        }

        if (calcium != null && albumin != null) {
            val corrected = calculateCorrectedCalcium(calcium!!, albumin!!)
            val result = String.format("%.1f", corrected)

            val interpretation = when {
                corrected < 8.5 -> "Low (hypocalcemia)"
                corrected > 10.5 -> "High (hypercalcemia)"
                else -> "Normal (8.5-10.5)"
            }

            val content = """
                |═══════════════════════════════════
                |🧮 CORRECTED CALCIUM
                |═══════════════════════════════════
                |
                |Measured Ca: $calcium mg/dL
                |Albumin: $albumin g/dL
                |
                |📊 Corrected Ca = $result mg/dL
                |
                |$interpretation
                |
                |───────────────────────────────────
                |Formula: Ca + 0.8 × (4.0 - Albumin)
            """.trimMargin()

            showDataOverlay("Corrected Calcium", content)
            speakFeedback("Corrected calcium is $result. $interpretation")
        } else {
            speakFeedback("Need calcium and albumin from labs")
            showDataOverlay("Corrected Calcium",
                "Missing data:\n\n" +
                "• Calcium: ${if (calcium != null) "$calcium mg/dL ✓" else "❌ needed"}\n" +
                "• Albumin: ${if (albumin != null) "$albumin g/dL ✓" else "❌ needed"}\n\n" +
                "Load patient with labs to calculate")
        }
    }

    /**
     * Calculate and show anion gap
     */
    private fun calculateAndShowAnionGap() {
        var sodium: Double? = null
        var chloride: Double? = null
        var bicarb: Double? = null

        currentPatientData?.optJSONArray("labs")?.let { labs ->
            for (i in 0 until labs.length()) {
                val lab = labs.getJSONObject(i)
                val name = lab.optString("name", "").lowercase()
                val value = lab.optString("value", "").replace(Regex("[^0-9.]"), "").toDoubleOrNull()

                when {
                    name.contains("sodium") && sodium == null -> sodium = value
                    name.contains("chloride") && chloride == null -> chloride = value
                    (name.contains("bicarb") || name.contains("co2") || name.contains("hco3")) && bicarb == null -> bicarb = value
                }
            }
        }

        if (sodium != null && chloride != null && bicarb != null) {
            val ag = calculateAnionGap(sodium!!, chloride!!, bicarb!!)
            val result = String.format("%.0f", ag)
            val interpretation = interpretAnionGap(ag)

            val content = """
                |═══════════════════════════════════
                |🧮 ANION GAP
                |═══════════════════════════════════
                |
                |Sodium: $sodium mEq/L
                |Chloride: $chloride mEq/L
                |Bicarb: $bicarb mEq/L
                |
                |📊 Anion Gap = $result mEq/L
                |
                |$interpretation
                |
                |───────────────────────────────────
                |Formula: Na - (Cl + HCO₃)
                |MUDPILES: Methanol, Uremia, DKA,
                |Propylene glycol, INH, Lactic acid,
                |Ethylene glycol, Salicylates
            """.trimMargin()

            showDataOverlay("Anion Gap", content)
            speakFeedback("Anion gap is $result. $interpretation")
        } else {
            speakFeedback("Need sodium, chloride, and bicarbonate from BMP")
            showDataOverlay("Anion Gap Calculator",
                "Missing data:\n\n" +
                "• Sodium: ${if (sodium != null) "$sodium mEq/L ✓" else "❌ needed"}\n" +
                "• Chloride: ${if (chloride != null) "$chloride mEq/L ✓" else "❌ needed"}\n" +
                "• Bicarb: ${if (bicarb != null) "$bicarb mEq/L ✓" else "❌ needed"}\n\n" +
                "Load patient with BMP to calculate")
        }
    }

    /**
     * Calculate and show A1c to glucose conversion
     */
    private fun calculateAndShowA1cToGlucose() {
        var a1c: Double? = null

        currentPatientData?.optJSONArray("labs")?.let { labs ->
            for (i in 0 until labs.length()) {
                val lab = labs.getJSONObject(i)
                val name = lab.optString("name", "").lowercase()
                if (name.contains("a1c") || name.contains("hemoglobin a1c") || name.contains("hba1c")) {
                    a1c = lab.optString("value", "").replace(Regex("[^0-9.]"), "").toDoubleOrNull()
                    break
                }
            }
        }

        if (a1c != null) {
            val glucose = a1cToGlucose(a1c!!)
            val result = String.format("%.0f", glucose)

            val control = when {
                a1c!! < 5.7 -> "Normal"
                a1c!! < 6.5 -> "Prediabetes"
                a1c!! < 7.0 -> "Good control"
                a1c!! < 8.0 -> "Fair control"
                a1c!! < 9.0 -> "Poor control"
                else -> "Very poor control"
            }

            val content = """
                |═══════════════════════════════════
                |🧮 A1c TO GLUCOSE
                |═══════════════════════════════════
                |
                |HbA1c: ${String.format("%.1f", a1c)}%
                |
                |📊 Est. Avg Glucose = $result mg/dL
                |
                |Control: $control
                |
                |───────────────────────────────────
                |Target A1c: <7% for most adults
                |Formula: eAG = 28.7 × A1c - 46.7
            """.trimMargin()

            showDataOverlay("A1c Conversion", content)
            speakFeedback("A1c of ${String.format("%.1f", a1c)} percent equals average glucose of $result. $control")
        } else {
            speakFeedback("No A1c found in labs. Load patient with A1c result.")
            showDataOverlay("A1c Conversion", "No HbA1c found in patient labs.\n\nLoad a patient with A1c result to convert.")
        }
    }

    /**
     * Calculate and show glucose to A1c conversion
     */
    private fun calculateAndShowGlucoseToA1c() {
        var glucose: Double? = null

        currentPatientData?.optJSONArray("labs")?.let { labs ->
            for (i in 0 until labs.length()) {
                val lab = labs.getJSONObject(i)
                val name = lab.optString("name", "").lowercase()
                if (name.contains("glucose") && !name.contains("a1c")) {
                    glucose = lab.optString("value", "").replace(Regex("[^0-9.]"), "").toDoubleOrNull()
                    break
                }
            }
        }

        if (glucose != null) {
            val a1c = glucoseToA1c(glucose!!)
            val result = String.format("%.1f", a1c)

            val content = """
                |═══════════════════════════════════
                |🧮 GLUCOSE TO A1c
                |═══════════════════════════════════
                |
                |Avg Glucose: ${String.format("%.0f", glucose)} mg/dL
                |
                |📊 Est. A1c = $result%
                |
                |───────────────────────────────────
                |Formula: A1c = (Glucose + 46.7) / 28.7
            """.trimMargin()

            showDataOverlay("Glucose to A1c", content)
            speakFeedback("Average glucose of ${String.format("%.0f", glucose)} equals estimated A1c of $result percent")
        } else {
            speakFeedback("No glucose found in labs")
            showDataOverlay("Glucose to A1c", "No glucose found in patient labs.\n\nLoad a patient with glucose result.")
        }
    }

    /**
     * Calculate and show MAP
     */
    private fun calculateAndShowMAP() {
        var systolic: Double? = null
        var diastolic: Double? = null

        // Check captured vitals first
        for (vital in capturedVitals) {
            if (vital.type == VitalType.BLOOD_PRESSURE) {
                val parts = vital.value.split("/")
                if (parts.size == 2) {
                    systolic = parts[0].replace(Regex("[^0-9]"), "").toDoubleOrNull()
                    diastolic = parts[1].replace(Regex("[^0-9]"), "").toDoubleOrNull()
                }
            }
        }

        // Try patient vitals if not captured
        if (systolic == null || diastolic == null) {
            currentPatientData?.optJSONArray("vitals")?.let { vitals ->
                for (i in 0 until vitals.length()) {
                    val v = vitals.getJSONObject(i)
                    val name = v.optString("name", "").lowercase()
                    val value = v.optString("value", "").replace(Regex("[^0-9.]"), "").toDoubleOrNull()

                    when {
                        name.contains("systolic") && systolic == null -> systolic = value
                        name.contains("diastolic") && diastolic == null -> diastolic = value
                    }
                }
            }
        }

        if (systolic != null && diastolic != null) {
            val map = calculateMAP(systolic!!, diastolic!!)
            val result = String.format("%.0f", map)

            val interpretation = when {
                map < 60 -> "Low - risk of organ hypoperfusion"
                map < 70 -> "Low-normal"
                map <= 100 -> "Normal (70-100)"
                map <= 110 -> "High-normal"
                else -> "High"
            }

            val content = """
                |═══════════════════════════════════
                |🧮 MEAN ARTERIAL PRESSURE
                |═══════════════════════════════════
                |
                |BP: ${systolic!!.toInt()}/${diastolic!!.toInt()} mmHg
                |
                |📊 MAP = $result mmHg
                |
                |$interpretation
                |
                |───────────────────────────────────
                |Formula: DBP + (SBP - DBP) / 3
                |Target: ≥65 mmHg for organ perfusion
            """.trimMargin()

            showDataOverlay("MAP Result", content)
            speakFeedback("Mean arterial pressure is $result. $interpretation")
        } else {
            speakFeedback("Need blood pressure. Say: BP 120 over 80")
            showDataOverlay("MAP Calculator",
                "Missing blood pressure.\n\n" +
                "Say: \"BP 120 over 80\"\n\n" +
                "Or load a patient with vitals.")
        }
    }

    /**
     * Calculate and show Creatinine Clearance
     */
    private fun calculateAndShowCrCl() {
        var creatinine: Double? = null
        var age: Int? = null
        var weightKg: Double? = null
        var isFemale: Boolean? = null

        currentPatientData?.let { patient ->
            // Age
            patient.optString("date_of_birth", "")?.let { dob ->
                if (dob.isNotEmpty()) {
                    try {
                        val birthYear = dob.substring(0, 4).toInt()
                        val currentYear = java.util.Calendar.getInstance().get(java.util.Calendar.YEAR)
                        age = currentYear - birthYear
                    } catch (e: Exception) {}
                }
            }

            // Gender
            val gender = patient.optString("gender", "").lowercase()
            isFemale = gender == "female" || gender == "f"

            // Creatinine
            patient.optJSONArray("labs")?.let { labs ->
                for (i in 0 until labs.length()) {
                    val lab = labs.getJSONObject(i)
                    val name = lab.optString("name", "").lowercase()
                    if (name.contains("creatinine") && !name.contains("clearance")) {
                        creatinine = lab.optString("value", "").replace(Regex("[^0-9.]"), "").toDoubleOrNull()
                        break
                    }
                }
            }

            // Weight
            patient.optJSONArray("vitals")?.let { vitals ->
                for (i in 0 until vitals.length()) {
                    val v = vitals.getJSONObject(i)
                    val name = v.optString("name", "").lowercase()
                    if (name.contains("weight")) {
                        val value = v.optString("value", "").replace(Regex("[^0-9.]"), "").toDoubleOrNull()
                        val unit = v.optString("unit", "").lowercase()
                        if (value != null) {
                            weightKg = if (unit.contains("lb")) value * 0.453592 else value
                        }
                        break
                    }
                }
            }
        }

        // Check captured vitals for weight
        if (weightKg == null) {
            for (vital in capturedVitals) {
                if (vital.type == VitalType.WEIGHT) {
                    val value = vital.value.replace(Regex("[^0-9.]"), "").toDoubleOrNull()
                    if (value != null) {
                        weightKg = if (vital.unit.contains("lb", ignoreCase = true)) value * 0.453592 else value
                    }
                }
            }
        }

        if (creatinine != null && age != null && weightKg != null && isFemale != null) {
            val crcl = calculateCrCl(creatinine!!, age!!, weightKg!!, isFemale!!)
            val result = String.format("%.0f", crcl)

            val interpretation = when {
                crcl >= 90 -> "Normal"
                crcl >= 60 -> "Mild impairment"
                crcl >= 30 -> "Moderate impairment"
                crcl >= 15 -> "Severe impairment"
                else -> "Kidney failure"
            }

            val content = """
                |═══════════════════════════════════
                |🧮 CREATININE CLEARANCE
                |═══════════════════════════════════
                |
                |Creatinine: $creatinine mg/dL
                |Age: $age years
                |Weight: ${String.format("%.1f", weightKg)} kg
                |Sex: ${if (isFemale!!) "Female" else "Male"}
                |
                |📊 CrCl = $result mL/min
                |
                |$interpretation
                |
                |───────────────────────────────────
                |Cockcroft-Gault formula
                |Use for drug dosing adjustments
            """.trimMargin()

            showDataOverlay("CrCl Result", content)
            speakFeedback("Creatinine clearance is $result mL per minute. $interpretation")
        } else {
            speakFeedback("Need creatinine, age, weight, and sex for creatinine clearance")
            showDataOverlay("CrCl Calculator",
                "Missing data:\n\n" +
                "• Creatinine: ${if (creatinine != null) "$creatinine mg/dL ✓" else "❌ needed"}\n" +
                "• Age: ${if (age != null) "$age years ✓" else "❌ needed"}\n" +
                "• Weight: ${if (weightKg != null) "${String.format("%.1f", weightKg)} kg ✓" else "❌ needed"}\n" +
                "• Sex: ${if (isFemale != null) (if (isFemale!!) "Female" else "Male") + " ✓" else "❌ needed"}\n\n" +
                "Load patient and capture weight if needed")
        }
    }

    /**
     * Calculate and show CHADS₂-VASc score
     */
    private fun calculateAndShowCHADSVASc() {
        // This would need more patient history data
        // For now, show the criteria
        val content = """
            |═══════════════════════════════════
            |🧮 CHADS₂-VASc SCORE
            |═══════════════════════════════════
            |
            |Score criteria (1 point each):
            |• CHF / LV dysfunction
            |• Hypertension
            |• Age 65-74
            |• Diabetes
            |• Vascular disease (MI, PAD, aortic plaque)
            |• Female sex
            |
            |2 points each:
            |• Age ≥75
            |• Prior Stroke/TIA/thromboembolism
            |
            |───────────────────────────────────
            |ANTICOAGULATION:
            |0 = Low risk (no anticoag)
            |1 = Low-moderate (consider anticoag)
            |≥2 = Anticoagulation recommended
            |
            |───────────────────────────────────
            |Say conditions to calculate:
            |"Patient has CHF and hypertension"
        """.trimMargin()

        showDataOverlay("CHADS₂-VASc", content)
        speakFeedback("CHADS VASc score requires patient history. See criteria on screen.")
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // VOICE ORDERS - Order Processing Functions
    // ═══════════════════════════════════════════════════════════════════════════

    /**
     * Find lab order by alias text
     */
    private fun findLabByAlias(text: String): LabOrderInfo? {
        val lower = text.lowercase().trim()
        for ((_, lab) in labOrders) {
            if (lab.aliases.any { lower.contains(it) }) {
                return lab
            }
        }
        return null
    }

    /**
     * Find imaging order by alias text
     */
    private fun findImagingByAlias(text: String): ImagingOrderInfo? {
        val lower = text.lowercase().trim()
        for ((_, imaging) in imagingOrders) {
            if (imaging.aliases.any { lower.contains(it) }) {
                return imaging
            }
        }
        return null
    }

    /**
     * Find medication order by alias text
     */
    private fun findMedicationByAlias(text: String): MedicationOrderInfo? {
        val lower = text.lowercase().trim()
        for ((_, med) in medicationOrders) {
            if (med.aliases.any { lower.contains(it) }) {
                return med
            }
        }
        return null
    }

    /**
     * Check if text is a lab order
     */
    private fun isLabOrder(text: String): Boolean {
        return findLabByAlias(text) != null
    }

    /**
     * Check if text is an imaging order
     */
    private fun isImagingOrder(text: String): Boolean {
        return findImagingByAlias(text) != null
    }

    /**
     * Check if text is a medication order
     */
    private fun isMedicationOrder(text: String): Boolean {
        return findMedicationByAlias(text) != null
    }

    /**
     * Process a lab order voice command
     */
    private fun processLabOrder(text: String) {
        val lab = findLabByAlias(text)
        if (lab == null) {
            speakFeedback("Lab test not recognized. Try: CBC, CMP, BMP, UA, lipids, A1C, or TSH.")
            return
        }

        // Check for duplicate
        val duplicateWarning = checkDuplicateOrder(OrderType.LAB, lab.name)
        val warnings = listOfNotNull(duplicateWarning)

        val order = Order(
            type = OrderType.LAB,
            name = lab.name,
            displayName = lab.displayName,
            safetyWarnings = warnings,
            requiresConfirmation = warnings.isNotEmpty()
        )

        if (order.requiresConfirmation) {
            pendingConfirmationOrder = order
            speakFeedback("${duplicateWarning?.message} Do you still want to order? Say yes or no.")
        } else {
            addOrderToQueue(order)
            speakFeedback("Ordered ${lab.displayName}")
        }
    }

    /**
     * Process an imaging order voice command
     */
    private fun processImagingOrder(text: String) {
        val imaging = findImagingByAlias(text)
        if (imaging == null) {
            speakFeedback("Imaging study not recognized. Try: chest x-ray, CT head, MRI brain, or ultrasound.")
            return
        }

        // Parse contrast preference
        val lower = text.lowercase()
        val contrast = when {
            lower.contains("without contrast") -> false
            lower.contains("with and without") -> null  // Both phases
            lower.contains("with contrast") -> true
            else -> null  // Not specified
        }

        // Parse laterality
        val laterality = when {
            lower.contains("left") -> "left"
            lower.contains("right") -> "right"
            lower.contains("bilateral") -> "bilateral"
            else -> null
        }

        val warnings = mutableListOf<SafetyWarning>()

        // Check for duplicate
        checkDuplicateOrder(OrderType.IMAGING, imaging.name)?.let { warnings.add(it) }

        // Check metformin + contrast warning
        if (contrast == true) {
            checkMetforminContrastWarning()?.let { warnings.add(it) }
        }

        val contrastText = when (contrast) {
            true -> " with contrast"
            false -> " without contrast"
            null -> ""
        }

        val order = Order(
            type = OrderType.IMAGING,
            name = imaging.name,
            displayName = "${imaging.displayName}$contrastText",
            contrast = contrast,
            bodyPart = imaging.bodyPart,
            laterality = laterality,
            safetyWarnings = warnings,
            requiresConfirmation = warnings.isNotEmpty()
        )

        if (order.requiresConfirmation) {
            pendingConfirmationOrder = order
            val warningMsg = warnings.joinToString(". ") { it.message }
            if (warnings.any { it.severity == "high" }) {
                speakFeedback("Critical warning: $warningMsg Say yes to confirm or no to cancel.")
            } else {
                speakFeedback("Warning: $warningMsg Say yes to confirm or no to cancel.")
            }
        } else {
            addOrderToQueue(order)
            speakFeedback("Ordered ${order.displayName}")
        }
    }

    /**
     * Process a medication order voice command
     */
    private fun processMedicationOrder(text: String) {
        val med = findMedicationByAlias(text)
        if (med == null) {
            speakFeedback("Medication not recognized. Try common medications like amoxicillin, ibuprofen, or prednisone.")
            return
        }

        val lower = text.lowercase()

        // Parse dose (e.g., "500mg", "500 mg")
        val dosePattern = Regex("(\\d+)\\s*(mg|mcg|ml|g)")
        val doseMatch = dosePattern.find(lower)
        val dose = doseMatch?.value?.replace(" ", "") ?: med.commonDoses.firstOrNull()

        // Parse frequency
        var frequency: String? = null
        for ((alias, canonical) in frequencyAliases) {
            if (lower.contains(alias)) {
                frequency = canonical
                break
            }
        }
        frequency = frequency ?: med.commonFrequencies.firstOrNull()

        // Parse duration (e.g., "for 10 days", "for 2 weeks")
        val durationPattern = Regex("for\\s+(\\d+)\\s*(days?|weeks?)")
        val durationMatch = durationPattern.find(lower)
        val duration = durationMatch?.value?.replace("for ", "") ?: med.commonDurations.firstOrNull()

        // Check if PRN
        val prn = lower.contains("prn") || lower.contains("as needed") || lower.contains("when needed")

        // Safety checks
        val warnings = mutableListOf<SafetyWarning>()

        // 1. Allergy check
        checkMedicationAllergy(med)?.let { warnings.add(it) }

        // 2. Drug interaction check
        warnings.addAll(checkMedicationInteractions(med))

        // 3. Duplicate check
        checkDuplicateOrder(OrderType.MEDICATION, med.name)?.let { warnings.add(it) }

        // Build details string
        val details = buildString {
            append(dose ?: "")
            frequency?.let { append(" $it") }
            duration?.let { append(" x $it") }
            if (prn) append(" PRN")
        }.trim()

        val order = Order(
            type = OrderType.MEDICATION,
            name = med.name,
            displayName = med.name,
            details = details,
            dose = dose,
            frequency = frequency,
            duration = duration,
            route = med.route,
            prn = prn,
            safetyWarnings = warnings,
            requiresConfirmation = warnings.isNotEmpty()
        )

        if (order.requiresConfirmation) {
            pendingConfirmationOrder = order
            val highWarnings = warnings.filter { it.severity == "high" }
            if (highWarnings.isNotEmpty()) {
                val warningMsg = highWarnings.joinToString(". ") { it.message }
                speakFeedback("Critical warning: $warningMsg Do you still want to prescribe? Say yes to confirm or no to cancel.")
            } else {
                speakFeedback("Warning: ${warnings.first().message} Say yes to confirm or no to cancel.")
            }
        } else {
            addOrderToQueue(order)
            speakFeedback("Prescribed ${med.name} $details")
        }
    }

    /**
     * Check for duplicate order in queue
     */
    private fun checkDuplicateOrder(type: OrderType, name: String): SafetyWarning? {
        val duplicate = orderQueue.find { it.type == type && it.name.equals(name, ignoreCase = true) }
        return if (duplicate != null) {
            SafetyWarning(
                type = SafetyWarningType.DUPLICATE_ORDER,
                severity = "moderate",
                message = "$name has already been ordered in this session"
            )
        } else null
    }

    /**
     * Check for allergy to medication
     */
    private fun checkMedicationAllergy(med: MedicationOrderInfo): SafetyWarning? {
        val patient = currentPatientData ?: return null
        val allergies = patient.optJSONArray("allergies") ?: return null

        val patientAllergies = mutableListOf<String>()
        for (i in 0 until allergies.length()) {
            patientAllergies.add(allergies.getString(i).lowercase())
        }

        // Check cross-reactivity
        val crossMatch = med.allergyCrossReact.find { cross ->
            patientAllergies.any { allergy ->
                allergy.contains(cross.lowercase()) || cross.lowercase().contains(allergy)
            }
        }

        // Check direct match
        val directMatch = patientAllergies.find { allergy ->
            med.name.lowercase().contains(allergy) || allergy.contains(med.name.lowercase()) ||
            med.aliases.any { alias -> allergy.contains(alias) || alias.contains(allergy) }
        }

        return if (crossMatch != null || directMatch != null) {
            SafetyWarning(
                type = SafetyWarningType.ALLERGY,
                severity = "high",
                message = "Patient has documented allergy to ${directMatch ?: crossMatch}. ${med.name} may cause allergic reaction.",
                details = if (med.allergyCrossReact.isNotEmpty()) "Cross-reactivity: ${med.allergyCrossReact.joinToString(", ")}" else ""
            )
        } else null
    }

    /**
     * Check for drug interactions with current medications
     */
    private fun checkMedicationInteractions(med: MedicationOrderInfo): List<SafetyWarning> {
        val patient = currentPatientData ?: return emptyList()
        val currentMeds = patient.optJSONArray("medications") ?: return emptyList()

        val warnings = mutableListOf<SafetyWarning>()
        val patientMedNames = mutableListOf<String>()
        for (i in 0 until currentMeds.length()) {
            patientMedNames.add(currentMeds.getString(i).lowercase())
        }

        for (interactingDrug in med.interactionsWith) {
            val match = patientMedNames.find { patientMed ->
                patientMed.contains(interactingDrug.lowercase()) ||
                interactingDrug.lowercase().contains(patientMed)
            }
            if (match != null) {
                // Determine severity based on drug class
                val severity = when {
                    med.drugClass == "opioid" && (interactingDrug.contains("benzodiazepine") || interactingDrug.contains("alcohol")) -> "high"
                    interactingDrug.contains("warfarin") -> "high"
                    med.drugClass == "nsaid" && interactingDrug.contains("lithium") -> "high"
                    else -> "moderate"
                }
                warnings.add(SafetyWarning(
                    type = SafetyWarningType.DRUG_INTERACTION,
                    severity = severity,
                    message = "${med.name} interacts with patient's current medication: $match",
                    details = "Use with caution"
                ))
            }
        }

        return warnings
    }

    /**
     * Check for metformin + contrast warning
     */
    private fun checkMetforminContrastWarning(): SafetyWarning? {
        val patient = currentPatientData ?: return null
        val currentMeds = patient.optJSONArray("medications") ?: return null

        for (i in 0 until currentMeds.length()) {
            val med = currentMeds.getString(i).lowercase()
            if (med.contains("metformin") || med.contains("glucophage")) {
                return SafetyWarning(
                    type = SafetyWarningType.CONTRAINDICATION,
                    severity = "high",
                    message = "Patient takes metformin. Hold metformin 48 hours before and after contrast imaging to prevent lactic acidosis.",
                    details = "Recommend holding metformin around contrast administration"
                )
            }
        }
        return null
    }

    /**
     * Add order to queue and auto-add to Plan section
     */
    private fun addOrderToQueue(order: Order) {
        val confirmedOrder = order.copy(status = OrderStatus.CONFIRMED)
        orderQueue.add(confirmedOrder)
        saveOrdersToPrefs()
        addOrderToPlanSection(confirmedOrder)
        Log.d(TAG, "Order added: ${order.name}, queue size: ${orderQueue.size}")
    }

    /**
     * Save orders to SharedPreferences
     */
    private fun saveOrdersToPrefs() {
        try {
            val ordersJson = org.json.JSONArray()
            for (order in orderQueue) {
                ordersJson.put(order.toJson())
            }
            cachePrefs.edit()
                .putString(ORDERS_KEY, ordersJson.toString())
                .putString(ORDERS_PATIENT_KEY, currentPatientData?.optString("patient_id", "") ?: "")
                .apply()
        } catch (e: Exception) {
            Log.e(TAG, "Error saving orders: ${e.message}")
        }
    }

    /**
     * Load orders from SharedPreferences
     */
    private fun loadOrdersFromPrefs() {
        try {
            val currentPatientId = currentPatientData?.optString("patient_id", "") ?: ""
            val savedPatientId = cachePrefs.getString(ORDERS_PATIENT_KEY, "") ?: ""

            // Only load if same patient
            if (currentPatientId.isNotEmpty() && currentPatientId == savedPatientId) {
                val ordersStr = cachePrefs.getString(ORDERS_KEY, "[]") ?: "[]"
                val ordersJson = org.json.JSONArray(ordersStr)
                orderQueue.clear()
                for (i in 0 until ordersJson.length()) {
                    orderQueue.add(Order.fromJson(ordersJson.getJSONObject(i)))
                }
                Log.d(TAG, "Loaded ${orderQueue.size} orders for patient $currentPatientId")
            } else {
                // Different patient - clear orders
                orderQueue.clear()
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error loading orders: ${e.message}")
            orderQueue.clear()
        }
    }

    /**
     * Add order to Plan section of note
     */
    private fun addOrderToPlanSection(order: Order) {
        val orderText = when (order.type) {
            OrderType.LAB -> "• Order ${order.displayName}"
            OrderType.IMAGING -> {
                val contrastText = when (order.contrast) {
                    true -> " with contrast"
                    false -> " without contrast"
                    else -> ""
                }
                "• Order ${order.displayName}$contrastText"
            }
            OrderType.MEDICATION -> "• Rx: ${order.name} ${order.details}"
        }

        // If note is being edited, append to plan section
        if (noteEditText != null && editableNoteContent != null) {
            appendToNoteSection("plan", orderText)
        } else {
            // Store for when note is generated
            pendingPlanItems.add(orderText)
        }
    }

    /**
     * Show order queue overlay
     */
    private fun showOrderQueue() {
        if (orderQueue.isEmpty()) {
            val emptyText = """
                |📋 NO PENDING ORDERS
                |${"─".repeat(30)}
                |
                |Voice Commands:
                |• "Order CBC" - Order a lab test
                |• "Order chest x-ray" - Order imaging
                |• "Prescribe amoxicillin 500mg TID" - Prescribe medication
                |
                |Available Labs:
                |CBC, CMP, BMP, UA, Lipids, TSH, A1c, PT/INR, Troponin
                |
                |Available Imaging:
                |Chest X-ray, CT Head/Chest/Abdomen, MRI Brain/Spine, Echo
                |
                |Say "close" to dismiss
            """.trimMargin()
            showDataOverlay("📋 Orders", emptyText)
            speakFeedback("No pending orders")
            return
        }

        val sb = StringBuilder()

        // Group by type
        val labs = orderQueue.filter { it.type == OrderType.LAB }
        val imaging = orderQueue.filter { it.type == OrderType.IMAGING }
        val meds = orderQueue.filter { it.type == OrderType.MEDICATION }

        if (labs.isNotEmpty()) {
            sb.appendLine("🔬 LABS (${labs.size})")
            labs.forEachIndexed { index, order ->
                sb.appendLine("  ${index + 1}. ${order.displayName}")
            }
            sb.appendLine()
        }

        if (imaging.isNotEmpty()) {
            sb.appendLine("📷 IMAGING (${imaging.size})")
            imaging.forEachIndexed { index, order ->
                sb.appendLine("  ${index + 1}. ${order.displayName}")
            }
            sb.appendLine()
        }

        if (meds.isNotEmpty()) {
            sb.appendLine("💊 MEDICATIONS (${meds.size})")
            meds.forEachIndexed { index, order ->
                sb.appendLine("  ${index + 1}. ${order.name} ${order.details}")
                if (order.safetyWarnings.isNotEmpty()) {
                    order.safetyWarnings.forEach { warning ->
                        val icon = if (warning.severity == "high") "🚨" else "⚠️"
                        sb.appendLine("      $icon ${warning.message}")
                    }
                }
            }
            sb.appendLine()
        }

        sb.appendLine("─".repeat(40))
        sb.appendLine("Voice Commands:")
        sb.appendLine("• \"Cancel order\" - Remove last order")
        sb.appendLine("• \"Clear all orders\" - Remove all")
        sb.appendLine("• \"Close\" - Dismiss")

        showDataOverlay("📋 Orders (${orderQueue.size})", sb.toString())
        speakFeedback("${orderQueue.size} orders pending")
    }

    /**
     * Cancel the last order in queue
     */
    private fun cancelLastOrder() {
        if (orderQueue.isEmpty()) {
            speakFeedback("No orders to cancel")
            return
        }
        val removed = orderQueue.removeAt(orderQueue.size - 1)
        saveOrdersToPrefs()
        speakFeedback("Cancelled order for ${removed.displayName}")
        Log.d(TAG, "Cancelled order: ${removed.name}")
    }

    /**
     * Clear all orders in queue
     */
    private fun clearAllOrders() {
        val count = orderQueue.size
        orderQueue.clear()
        pendingPlanItems.clear()
        saveOrdersToPrefs()
        speakFeedback("Cleared $count orders")
        hideDataOverlay()
    }

    /**
     * Confirm pending order after safety warning
     */
    private fun confirmPendingOrder() {
        val order = pendingConfirmationOrder ?: return
        pendingConfirmationOrder = null
        addOrderToQueue(order)

        val message = when (order.type) {
            OrderType.LAB -> "Ordered ${order.displayName}"
            OrderType.IMAGING -> "Ordered ${order.displayName}"
            OrderType.MEDICATION -> "Prescribed ${order.name} ${order.details}"
        }
        speakFeedback(message)
    }

    /**
     * Reject pending order after safety warning
     */
    private fun rejectPendingOrder() {
        val order = pendingConfirmationOrder ?: return
        pendingConfirmationOrder = null
        speakFeedback("Order cancelled")
        Log.d(TAG, "Order rejected: ${order.name}")
    }

    /**
     * Get pending plan items for note generation
     */
    private fun getPendingOrdersForPlan(): String {
        if (pendingPlanItems.isEmpty()) return ""
        val items = pendingPlanItems.joinToString("\n")
        return items
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // ORDER SETS - Batch ordering functions
    // ═══════════════════════════════════════════════════════════════════════════

    /**
     * Find an order set by alias
     */
    private fun findOrderSet(text: String): OrderSetInfo? {
        val lower = text.lowercase().trim()
        // Direct key match
        orderSets[lower]?.let { return it }
        // Alias match
        for ((_, setInfo) in orderSets) {
            if (setInfo.aliases.any { lower.contains(it) }) {
                return setInfo
            }
        }
        return null
    }

    /**
     * Check if text matches an order set pattern
     */
    private fun isOrderSet(text: String): Boolean {
        return findOrderSet(text) != null
    }

    /**
     * Process an order set - queue all orders with safety checks
     */
    private fun processOrderSet(setInfo: OrderSetInfo) {
        if (currentPatientData == null) {
            speakFeedback("Please load a patient first")
            return
        }

        val orderedItems = mutableListOf<String>()
        val warnings = mutableListOf<String>()
        var hasHighSeverityWarning = false

        // Process each item in the order set
        for (item in setInfo.items) {
            when (item.type) {
                OrderType.LAB -> {
                    val lab = labOrders[item.orderKey]
                    if (lab != null) {
                        // Check for duplicate
                        val duplicate = checkDuplicateOrder(OrderType.LAB, lab.name)
                        if (duplicate != null) {
                            warnings.add("${lab.name}: duplicate order")
                        } else {
                            val order = Order(
                                type = OrderType.LAB,
                                name = lab.name,
                                displayName = lab.displayName,
                                details = "CPT: ${lab.cptCode}"
                            )
                            orderQueue.add(order)
                            pendingPlanItems.add("• ${lab.displayName}")
                            orderedItems.add(lab.name)
                        }
                    }
                }
                OrderType.IMAGING -> {
                    val imaging = imagingOrders[item.orderKey]
                    if (imaging != null) {
                        // Check for duplicate
                        val duplicate = checkDuplicateOrder(OrderType.IMAGING, imaging.name)
                        if (duplicate != null) {
                            warnings.add("${imaging.name}: duplicate order")
                        } else {
                            // Check metformin/contrast warning
                            if (imaging.supportsContrast || item.details.contains("contrast")) {
                                val metforminWarning = checkMetforminContrastWarning()
                                if (metforminWarning != null) {
                                    warnings.add("${imaging.name}: ${metforminWarning.message}")
                                    hasHighSeverityWarning = true
                                }
                            }
                            val order = Order(
                                type = OrderType.IMAGING,
                                name = imaging.name,
                                displayName = imaging.displayName,
                                details = "CPT: ${imaging.cptCode}",
                                contrast = imaging.supportsContrast,
                                bodyPart = imaging.bodyPart
                            )
                            orderQueue.add(order)
                            pendingPlanItems.add("• ${imaging.displayName}")
                            orderedItems.add(imaging.name)
                        }
                    }
                }
                OrderType.MEDICATION -> {
                    // Order sets typically don't include medications, but support it
                    Log.d(TAG, "Medication in order set not processed: ${item.orderKey}")
                }
            }
        }

        saveOrdersToPrefs()

        // Build feedback message
        val message = StringBuilder()
        message.append("Ordered ${setInfo.name}: ")
        message.append(orderedItems.joinToString(", "))

        if (warnings.isNotEmpty()) {
            message.append(". Warnings: ")
            message.append(warnings.joinToString("; "))
        }

        // Show visual summary
        showOrderSetSummary(setInfo, orderedItems, warnings)

        // Speak feedback
        speakFeedback(message.toString())

        Log.d(TAG, "Order set ${setInfo.id}: ${orderedItems.size} orders placed, ${warnings.size} warnings")
    }

    /**
     * Show visual summary of order set
     */
    private fun showOrderSetSummary(setInfo: OrderSetInfo, ordered: List<String>, warnings: List<String>) {
        val content = StringBuilder()
        content.append("═══════════════════════════\n")
        content.append("📦 ${setInfo.displayName}\n")
        content.append("═══════════════════════════\n\n")

        content.append("✓ Orders Placed:\n")
        ordered.forEach { content.append("  • $it\n") }

        if (warnings.isNotEmpty()) {
            content.append("\n⚠️ Warnings:\n")
            warnings.forEach { content.append("  • $it\n") }
        }

        content.append("\n───────────────────────────\n")
        content.append("Total: ${ordered.size} orders\n")
        content.append("Say \"show orders\" to view queue")

        showDataOverlay("Order Set", content.toString())
    }

    /**
     * Show list of available order sets
     */
    private fun showOrderSetList() {
        val content = StringBuilder()
        content.append("═══════════════════════════\n")
        content.append("📦 ORDER SETS\n")
        content.append("═══════════════════════════\n\n")

        orderSets.values.forEach { setInfo ->
            val labCount = setInfo.items.count { it.type == OrderType.LAB }
            val imagingCount = setInfo.items.count { it.type == OrderType.IMAGING }
            content.append("• ${setInfo.name}\n")
            content.append("  \"Order ${setInfo.aliases.first()}\"\n")
            content.append("  $labCount labs")
            if (imagingCount > 0) content.append(", $imagingCount imaging")
            content.append("\n\n")
        }

        content.append("───────────────────────────\n")
        content.append("Say \"what's in [name]\" to preview")

        showDataOverlay("Order Sets", content.toString())
        speakFeedback("Showing ${orderSets.size} order sets. Say order followed by the set name to place orders.")
    }

    /**
     * Preview contents of an order set without ordering
     */
    private fun previewOrderSet(text: String) {
        val setInfo = findOrderSet(text)
        if (setInfo == null) {
            speakFeedback("Order set not found. Say list order sets to see available options.")
            return
        }

        val content = StringBuilder()
        content.append("═══════════════════════════\n")
        content.append("📦 ${setInfo.displayName}\n")
        content.append("═══════════════════════════\n\n")
        content.append("${setInfo.description}\n\n")

        val labs = setInfo.items.filter { it.type == OrderType.LAB }
        val imaging = setInfo.items.filter { it.type == OrderType.IMAGING }

        if (labs.isNotEmpty()) {
            content.append("🧪 Labs:\n")
            labs.forEach { item ->
                val lab = labOrders[item.orderKey]
                content.append("  • ${lab?.displayName ?: item.orderKey}\n")
            }
            content.append("\n")
        }

        if (imaging.isNotEmpty()) {
            content.append("📷 Imaging:\n")
            imaging.forEach { item ->
                val img = imagingOrders[item.orderKey]
                content.append("  • ${img?.displayName ?: item.orderKey}\n")
            }
            content.append("\n")
        }

        content.append("───────────────────────────\n")
        content.append("Say \"order ${setInfo.aliases.first()}\" to place")

        showDataOverlay("Order Set Preview", content.toString())
        speakFeedback("${setInfo.name} contains ${labs.size} labs and ${imaging.size} imaging studies. Say order ${setInfo.aliases.first()} to place these orders.")
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // VOICE VITALS ENTRY - Capture and manage vitals by voice
    // ═══════════════════════════════════════════════════════════════════════════

    /**
     * Check if text contains a vital sign entry
     */
    private fun isVitalEntry(text: String): Boolean {
        val lower = text.lowercase()
        return vitalAliases.values.any { aliases ->
            aliases.any { alias -> lower.contains(alias) }
        } && Regex("\\d+").containsMatchIn(lower)
    }

    /**
     * Parse and process a vital sign from voice input
     */
    private fun processVitalEntry(text: String) {
        val lower = text.lowercase()

        // Try to match each vital type
        when {
            // Blood Pressure: "BP 120 over 80", "blood pressure 120/80"
            vitalAliases[VitalType.BLOOD_PRESSURE]?.any { lower.contains(it) } == true -> {
                parseBloodPressure(lower)
            }
            // Heart Rate: "heart rate 72", "pulse 80 bpm"
            vitalAliases[VitalType.HEART_RATE]?.any { lower.contains(it) } == true -> {
                parseHeartRate(lower)
            }
            // Temperature: "temp 98.6", "temperature 101.2 fahrenheit"
            vitalAliases[VitalType.TEMPERATURE]?.any { lower.contains(it) } == true -> {
                parseTemperature(lower)
            }
            // Oxygen Saturation: "o2 sat 98", "oxygen 95 percent"
            vitalAliases[VitalType.OXYGEN_SATURATION]?.any { lower.contains(it) } == true -> {
                parseOxygenSaturation(lower)
            }
            // Respiratory Rate: "resp rate 16", "respirations 18"
            vitalAliases[VitalType.RESPIRATORY_RATE]?.any { lower.contains(it) } == true -> {
                parseRespiratoryRate(lower)
            }
            // Weight: "weight 180 pounds", "weight 82 kilos"
            vitalAliases[VitalType.WEIGHT]?.any { lower.contains(it) } == true -> {
                parseWeight(lower)
            }
            // Height: "height 5 foot 10", "height 178 centimeters"
            vitalAliases[VitalType.HEIGHT]?.any { lower.contains(it) } == true -> {
                parseHeight(lower)
            }
            // Pain Level: "pain 5 out of 10", "pain level 7"
            vitalAliases[VitalType.PAIN_LEVEL]?.any { lower.contains(it) } == true -> {
                parsePainLevel(lower)
            }
            else -> {
                speakFeedback("Could not recognize vital sign. Try: BP 120 over 80, pulse 72, or temp 98.6")
            }
        }
    }

    /**
     * Parse blood pressure: "120 over 80", "120/80", "120 80"
     */
    private fun parseBloodPressure(text: String) {
        // Match patterns like "120 over 80", "120/80", "120 80"
        val patterns = listOf(
            Regex("(\\d{2,3})\\s*(?:over|/)\\s*(\\d{2,3})"),
            Regex("(\\d{2,3})\\s+(\\d{2,3})")
        )

        for (pattern in patterns) {
            val match = pattern.find(text)
            if (match != null) {
                val systolic = match.groupValues[1].toIntOrNull() ?: continue
                val diastolic = match.groupValues[2].toIntOrNull() ?: continue

                // Validate ranges
                val sysRange = vitalRanges["systolic"]!!
                val diaRange = vitalRanges["diastolic"]!!

                if (systolic < sysRange.min || systolic > sysRange.max) {
                    speakFeedback("Systolic $systolic seems out of range. Please verify.")
                    return
                }
                if (diastolic < diaRange.min || diastolic > diaRange.max) {
                    speakFeedback("Diastolic $diastolic seems out of range. Please verify.")
                    return
                }

                val vital = CapturedVital(
                    type = VitalType.BLOOD_PRESSURE,
                    value = "$systolic/$diastolic",
                    unit = "mmHg",
                    displayName = "Blood Pressure"
                )
                addCapturedVital(vital)

                // Check for critical values
                val isCritical = (sysRange.criticalHigh != null && systolic >= sysRange.criticalHigh) ||
                                 (diaRange.criticalHigh != null && diastolic >= diaRange.criticalHigh) ||
                                 (sysRange.criticalLow != null && systolic <= sysRange.criticalLow)

                if (isCritical) {
                    speakFeedback("Warning! Blood pressure $systolic over $diastolic recorded. Critical value detected.")
                } else {
                    speakFeedback("Blood pressure $systolic over $diastolic recorded.")
                }
                return
            }
        }
        speakFeedback("Could not parse blood pressure. Say: BP 120 over 80")
    }

    /**
     * Parse heart rate: "72", "72 bpm", "pulse 80"
     */
    private fun parseHeartRate(text: String) {
        val match = Regex("(\\d{2,3})").find(text)
        if (match != null) {
            val hr = match.groupValues[1].toIntOrNull() ?: return
            val range = vitalRanges["heart_rate"]!!

            if (hr < range.min || hr > range.max) {
                speakFeedback("Heart rate $hr seems out of range. Please verify.")
                return
            }

            val vital = CapturedVital(
                type = VitalType.HEART_RATE,
                value = hr.toString(),
                unit = "bpm",
                displayName = "Heart Rate"
            )
            addCapturedVital(vital)

            val isCritical = (range.criticalHigh != null && hr >= range.criticalHigh) ||
                             (range.criticalLow != null && hr <= range.criticalLow)

            if (isCritical) {
                speakFeedback("Warning! Heart rate $hr recorded. Critical value detected.")
            } else {
                speakFeedback("Heart rate $hr recorded.")
            }
        } else {
            speakFeedback("Could not parse heart rate. Say: pulse 72")
        }
    }

    /**
     * Parse temperature: "98.6", "101.2 fahrenheit", "37.5 celsius"
     */
    private fun parseTemperature(text: String) {
        val match = Regex("(\\d{2,3}(?:\\.\\d)?)").find(text)
        if (match != null) {
            val temp = match.groupValues[1].toDoubleOrNull() ?: return

            // Determine if Celsius or Fahrenheit
            val isCelsius = text.contains("celsius") || text.contains("centigrade") || temp < 50
            val range = if (isCelsius) vitalRanges["temperature_c"]!! else vitalRanges["temperature_f"]!!
            val unit = if (isCelsius) "°C" else "°F"

            if (temp < range.min || temp > range.max) {
                speakFeedback("Temperature $temp $unit seems out of range. Please verify.")
                return
            }

            val vital = CapturedVital(
                type = VitalType.TEMPERATURE,
                value = temp.toString(),
                unit = unit,
                displayName = "Temperature"
            )
            addCapturedVital(vital)

            val isCritical = (range.criticalHigh != null && temp >= range.criticalHigh) ||
                             (range.criticalLow != null && temp <= range.criticalLow)

            if (isCritical) {
                speakFeedback("Warning! Temperature $temp $unit recorded. Critical value detected.")
            } else {
                speakFeedback("Temperature $temp $unit recorded.")
            }
        } else {
            speakFeedback("Could not parse temperature. Say: temp 98.6")
        }
    }

    /**
     * Parse oxygen saturation: "98", "95 percent"
     */
    private fun parseOxygenSaturation(text: String) {
        val match = Regex("(\\d{2,3})").find(text)
        if (match != null) {
            val o2 = match.groupValues[1].toIntOrNull() ?: return
            val range = vitalRanges["oxygen_saturation"]!!

            if (o2 < range.min || o2 > range.max) {
                speakFeedback("Oxygen saturation $o2% seems out of range. Please verify.")
                return
            }

            val vital = CapturedVital(
                type = VitalType.OXYGEN_SATURATION,
                value = o2.toString(),
                unit = "%",
                displayName = "Oxygen Saturation"
            )
            addCapturedVital(vital)

            val isCritical = range.criticalLow != null && o2 <= range.criticalLow

            if (isCritical) {
                speakFeedback("Warning! Oxygen saturation $o2% recorded. Critical low value detected.")
            } else {
                speakFeedback("Oxygen saturation $o2% recorded.")
            }
        } else {
            speakFeedback("Could not parse oxygen saturation. Say: O2 sat 98")
        }
    }

    /**
     * Parse respiratory rate: "16", "18 breaths per minute"
     */
    private fun parseRespiratoryRate(text: String) {
        val match = Regex("(\\d{1,2})").find(text)
        if (match != null) {
            val rr = match.groupValues[1].toIntOrNull() ?: return
            val range = vitalRanges["respiratory_rate"]!!

            if (rr < range.min || rr > range.max) {
                speakFeedback("Respiratory rate $rr seems out of range. Please verify.")
                return
            }

            val vital = CapturedVital(
                type = VitalType.RESPIRATORY_RATE,
                value = rr.toString(),
                unit = "/min",
                displayName = "Respiratory Rate"
            )
            addCapturedVital(vital)

            val isCritical = (range.criticalHigh != null && rr >= range.criticalHigh) ||
                             (range.criticalLow != null && rr <= range.criticalLow)

            if (isCritical) {
                speakFeedback("Warning! Respiratory rate $rr recorded. Critical value detected.")
            } else {
                speakFeedback("Respiratory rate $rr recorded.")
            }
        } else {
            speakFeedback("Could not parse respiratory rate. Say: resp rate 16")
        }
    }

    /**
     * Parse weight: "180 pounds", "82 kilos", "180 lbs"
     */
    private fun parseWeight(text: String) {
        val match = Regex("(\\d{1,3}(?:\\.\\d)?)").find(text)
        if (match != null) {
            val weight = match.groupValues[1].toDoubleOrNull() ?: return

            // Determine unit
            val isKg = text.contains("kilo") || text.contains("kg")
            val unit = if (isKg) "kg" else "lbs"
            val range = if (isKg) vitalRanges["weight_kg"]!! else vitalRanges["weight_lbs"]!!

            if (weight < range.min || weight > range.max) {
                speakFeedback("Weight $weight $unit seems out of range. Please verify.")
                return
            }

            val vital = CapturedVital(
                type = VitalType.WEIGHT,
                value = weight.toString(),
                unit = unit,
                displayName = "Weight"
            )
            addCapturedVital(vital)
            speakFeedback("Weight $weight $unit recorded.")
        } else {
            speakFeedback("Could not parse weight. Say: weight 180 pounds")
        }
    }

    /**
     * Parse height: "5 foot 10", "178 centimeters", "70 inches"
     */
    private fun parseHeight(text: String) {
        // Try feet and inches: "5 foot 10", "5'10"
        val feetInchesMatch = Regex("(\\d)\\s*(?:foot|feet|ft|')\\s*(\\d{1,2})").find(text)
        if (feetInchesMatch != null) {
            val feet = feetInchesMatch.groupValues[1].toIntOrNull() ?: 0
            val inches = feetInchesMatch.groupValues[2].toIntOrNull() ?: 0
            val totalInches = feet * 12 + inches

            val vital = CapturedVital(
                type = VitalType.HEIGHT,
                value = "$feet'$inches\"",
                unit = "ft/in",
                displayName = "Height"
            )
            addCapturedVital(vital)
            speakFeedback("Height $feet foot $inches recorded.")
            return
        }

        // Try just a number with unit
        val match = Regex("(\\d{2,3})").find(text)
        if (match != null) {
            val height = match.groupValues[1].toIntOrNull() ?: return

            val isCm = text.contains("centimeter") || text.contains("cm") || height > 100
            val unit = if (isCm) "cm" else "in"

            val vital = CapturedVital(
                type = VitalType.HEIGHT,
                value = height.toString(),
                unit = unit,
                displayName = "Height"
            )
            addCapturedVital(vital)
            speakFeedback("Height $height $unit recorded.")
        } else {
            speakFeedback("Could not parse height. Say: height 5 foot 10")
        }
    }

    /**
     * Parse pain level: "5 out of 10", "pain level 7", "pain 8"
     */
    private fun parsePainLevel(text: String) {
        val match = Regex("(\\d{1,2})").find(text)
        if (match != null) {
            val pain = match.groupValues[1].toIntOrNull() ?: return
            val range = vitalRanges["pain"]!!

            if (pain < range.min || pain > range.max) {
                speakFeedback("Pain level must be 0 to 10.")
                return
            }

            val vital = CapturedVital(
                type = VitalType.PAIN_LEVEL,
                value = pain.toString(),
                unit = "/10",
                displayName = "Pain Level"
            )
            addCapturedVital(vital)
            speakFeedback("Pain level $pain out of 10 recorded.")
        } else {
            speakFeedback("Could not parse pain level. Say: pain 5 out of 10")
        }
    }

    /**
     * Add a captured vital and update the display
     */
    private fun addCapturedVital(vital: CapturedVital) {
        // Remove any existing vital of the same type (keep most recent)
        capturedVitals.removeAll { it.type == vital.type }
        capturedVitals.add(vital)
        Log.d(TAG, "Captured vital: ${vital.displayName} = ${vital.value} ${vital.unit}")
    }

    /**
     * Show all captured vitals
     */
    private fun showCapturedVitals() {
        if (capturedVitals.isEmpty()) {
            speakFeedback("No vitals captured yet. Say a vital like: BP 120 over 80")
            return
        }

        val content = StringBuilder()
        content.append("═══════════════════════════\n")
        content.append("📊 CAPTURED VITALS\n")
        content.append("═══════════════════════════\n\n")

        capturedVitals.forEach { vital ->
            val timeAgo = getTimeAgo(vital.timestamp)
            content.append("${vital.displayName}: ${vital.value} ${vital.unit}\n")
            content.append("  ($timeAgo)\n\n")
        }

        content.append("───────────────────────────\n")
        content.append("Say \"add vitals to note\" or\n")
        content.append("\"clear vitals\" to reset")

        showDataOverlay("Captured Vitals", content.toString())
        speakFeedback("${capturedVitals.size} vitals captured.")
    }

    /**
     * Clear all captured vitals
     */
    private fun clearCapturedVitals() {
        val count = capturedVitals.size
        capturedVitals.clear()
        hideDataOverlay()
        speakFeedback("Cleared $count vitals.")
    }

    /**
     * Format captured vitals for note insertion
     */
    private fun getCapturedVitalsForNote(): String {
        if (capturedVitals.isEmpty()) return ""

        val sb = StringBuilder()
        sb.append("Vitals:\n")
        capturedVitals.forEach { vital ->
            sb.append("• ${vital.displayName}: ${vital.value} ${vital.unit}\n")
        }
        return sb.toString()
    }

    /**
     * Add captured vitals to the current note
     */
    private fun addVitalsToNote() {
        if (capturedVitals.isEmpty()) {
            speakFeedback("No vitals to add. Capture vitals first.")
            return
        }

        val vitalsText = getCapturedVitalsForNote()

        // Add to objective section if note is active
        if (noteEditText != null && editableNoteContent != null) {
            appendToNoteSection("objective", vitalsText)
            speakFeedback("Added ${capturedVitals.size} vitals to objective section.")
        } else {
            // Store for later use
            pendingPlanItems.add(vitalsText)
            speakFeedback("${capturedVitals.size} vitals saved. They will be included in your next note.")
        }
    }

    /**
     * Get relative time ago string
     */
    private fun getTimeAgo(timestamp: Long): String {
        val diff = System.currentTimeMillis() - timestamp
        val seconds = diff / 1000
        val minutes = seconds / 60
        val hours = minutes / 60

        return when {
            seconds < 60 -> "just now"
            minutes < 60 -> "$minutes min ago"
            hours < 24 -> "$hours hr ago"
            else -> "${hours / 24} days ago"
        }
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // VITAL HISTORY - Historical Vital Sign Display
    // ═══════════════════════════════════════════════════════════════════════════

    /**
     * Fetch and display vital sign history from EHR
     */
    private fun fetchVitalHistory() {
        val patientId = currentPatientData?.optString("patient_id")
        if (patientId.isNullOrEmpty()) {
            speakFeedback("No patient loaded. Load a patient first.")
            return
        }

        statusText.text = "Loading vital history..."
        transcriptText.text = "Fetching from EHR"

        Thread {
            try {
                val request = Request.Builder()
                    .url("$EHR_PROXY_URL/api/v1/patient/$patientId/vital-history")
                    .get()
                    .build()

                httpClient.newCall(request).enqueue(object : Callback {
                    override fun onFailure(call: Call, e: IOException) {
                        Log.e(TAG, "Vital history fetch error: ${e.message}")
                        runOnUiThread {
                            statusText.text = "Failed to load"
                            transcriptText.text = "Error: ${e.message}"
                            speakFeedback("Failed to load vital history.")
                        }
                    }

                    override fun onResponse(call: Call, response: Response) {
                        val body = response.body?.string()
                        Log.d(TAG, "Vital history response: $body")

                        runOnUiThread {
                            try {
                                val json = JSONObject(body ?: "{}")
                                showVitalHistoryOverlay(json)
                            } catch (e: Exception) {
                                Log.e(TAG, "Parse error: ${e.message}")
                                showDataOverlay("Error", "Parse error: ${e.message}")
                            }
                        }
                    }
                })
            } catch (e: Exception) {
                Log.e(TAG, "Failed to fetch vital history: ${e.message}")
            }
        }.start()
    }

    /**
     * Display vital history in a timeline format
     */
    private fun showVitalHistoryOverlay(historyJson: JSONObject) {
        val history = historyJson.optJSONObject("history")
        if (history == null || history.length() == 0) {
            showDataOverlay("Vital History", "No vital sign history available.")
            speakFeedback("No vital history found for this patient.")
            return
        }

        val content = StringBuilder()
        content.append("═══════════════════════════════════\n")
        content.append("📊 VITAL SIGN HISTORY\n")
        content.append("═══════════════════════════════════\n\n")

        // Define the order we want to display vitals
        val vitalOrder = listOf(
            "Blood Pressure",
            "Systolic Blood Pressure",
            "Diastolic Blood Pressure",
            "Heart rate",
            "Body temperature",
            "Oxygen saturation",
            "Respiratory rate",
            "Body Weight",
            "Body Height",
            "BMI"
        )

        // Track displayed vitals
        val displayedVitals = mutableSetOf<String>()

        // First, display vitals in preferred order
        for (vitalName in vitalOrder) {
            if (history.has(vitalName)) {
                displayVitalTimeline(content, vitalName, history.getJSONArray(vitalName))
                displayedVitals.add(vitalName)
            }
        }

        // Then display any remaining vitals not in our preferred order
        val keys = history.keys()
        while (keys.hasNext()) {
            val vitalName = keys.next()
            if (vitalName !in displayedVitals) {
                displayVitalTimeline(content, vitalName, history.getJSONArray(vitalName))
            }
        }

        content.append("\n───────────────────────────────────\n")
        content.append("📅 Last ${historyJson.optInt("vital_types", 0)} vital types shown")

        showDataOverlay("Vital History", content.toString())

        // Provide TTS summary
        val vitalCount = historyJson.optInt("vital_types", 0)
        speakFeedback("Showing history for $vitalCount vital types.")
    }

    /**
     * Display a single vital's timeline with trend indicators
     */
    private fun displayVitalTimeline(sb: StringBuilder, vitalName: String, readings: JSONArray) {
        if (readings.length() == 0) return

        // Get emoji for vital type
        val emoji = when {
            vitalName.contains("Blood Pressure", ignoreCase = true) -> "🩸"
            vitalName.contains("Heart", ignoreCase = true) || vitalName.contains("Pulse", ignoreCase = true) -> "💓"
            vitalName.contains("Temperature", ignoreCase = true) -> "🌡️"
            vitalName.contains("Oxygen", ignoreCase = true) || vitalName.contains("SpO2", ignoreCase = true) -> "🫁"
            vitalName.contains("Respiratory", ignoreCase = true) -> "💨"
            vitalName.contains("Weight", ignoreCase = true) -> "⚖️"
            vitalName.contains("Height", ignoreCase = true) -> "📏"
            vitalName.contains("BMI", ignoreCase = true) -> "📊"
            else -> "•"
        }

        sb.append("$emoji $vitalName\n")
        sb.append("───────────────────────────────────\n")

        var previousValue: Double? = null

        for (i in 0 until readings.length()) {
            val reading = readings.getJSONObject(i)
            val value = reading.optString("value", "N/A")
            val unit = reading.optString("unit", "")
            val dateStr = reading.optString("date", "")
            val interpretation = reading.optString("interpretation", "")

            // Parse numeric value for trend calculation
            val numericValue = value.replace(Regex("[^0-9.-]"), "").toDoubleOrNull()

            // Calculate trend indicator
            val trendIcon = if (numericValue != null && previousValue != null) {
                val diff = numericValue - previousValue
                when {
                    diff > 0 -> "↗️"
                    diff < 0 -> "↘️"
                    else -> "→"
                }
            } else if (i == 0) {
                "🆕"  // Most recent
            } else {
                ""
            }

            // Format date to be more readable
            val formattedDate = formatVitalDate(dateStr)

            // Interpretation indicator
            val interpIndicator = when (interpretation) {
                "HH" -> "‼️"
                "LL" -> "‼️"
                "H" -> "↑"
                "L" -> "↓"
                else -> ""
            }

            // Build the reading line
            sb.append("  $trendIcon $value $unit $interpIndicator")
            if (formattedDate.isNotEmpty()) {
                sb.append(" ($formattedDate)")
            }
            sb.append("\n")

            previousValue = numericValue
        }

        sb.append("\n")
    }

    /**
     * Format FHIR date string to readable format
     */
    private fun formatVitalDate(dateStr: String): String {
        if (dateStr.isEmpty()) return ""

        try {
            // Parse ISO date format (e.g., "2024-12-29T10:30:00Z" or "2024-12-29")
            val inputFormat = if (dateStr.contains("T")) {
                java.text.SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss", java.util.Locale.US)
            } else {
                java.text.SimpleDateFormat("yyyy-MM-dd", java.util.Locale.US)
            }
            val outputFormat = java.text.SimpleDateFormat("MMM d", java.util.Locale.US)

            val date = inputFormat.parse(dateStr.substringBefore("Z").substringBefore("+"))
            return date?.let { outputFormat.format(it) } ?: dateStr.substring(0, minOf(10, dateStr.length))
        } catch (e: Exception) {
            // Return first 10 chars if parsing fails
            return dateStr.substring(0, minOf(10, dateStr.length))
        }
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // ENCOUNTER TIMER - Timer Control Functions
    // ═══════════════════════════════════════════════════════════════════════════

    /**
     * Start the encounter timer
     */
    private fun startEncounterTimer() {
        if (encounterTimerRunning) {
            val elapsed = getElapsedTimeFormatted()
            speakFeedback("Timer already running. $elapsed elapsed.")
            return
        }

        encounterStartTime = System.currentTimeMillis()
        encounterTimerRunning = true
        showTimerIndicator()
        startTimerUpdates()
        speakFeedback("Encounter timer started")
        Log.d(TAG, "Encounter timer started")
    }

    /**
     * Stop the encounter timer
     */
    private fun stopEncounterTimer() {
        if (!encounterTimerRunning) {
            speakFeedback("No timer running")
            return
        }

        val elapsed = getElapsedTimeFormatted()
        val minutes = getElapsedMinutes()
        encounterTimerRunning = false
        stopTimerUpdates()
        hideTimerIndicator()

        // Speak the total time
        speakFeedback("Encounter timer stopped. Total time: $elapsed")

        // Show summary
        Toast.makeText(this, "Encounter: $elapsed ($minutes min)", Toast.LENGTH_LONG).show()
        Log.d(TAG, "Encounter timer stopped: $elapsed")
    }

    /**
     * Report the current elapsed time
     */
    private fun reportEncounterTime() {
        if (!encounterTimerRunning) {
            speakFeedback("No timer running. Say start timer to begin.")
            return
        }

        val elapsed = getElapsedTimeFormatted()
        val minutes = getElapsedMinutes()
        speakFeedback("You have been with this patient for $elapsed. That's $minutes minutes.")
    }

    /**
     * Reset the encounter timer without stopping
     */
    private fun resetEncounterTimer() {
        if (!encounterTimerRunning) {
            speakFeedback("No timer running")
            return
        }

        encounterStartTime = System.currentTimeMillis()
        speakFeedback("Timer reset")
        updateTimerDisplay()
    }

    /**
     * Get elapsed time in formatted string (e.g., "5 minutes 30 seconds")
     */
    private fun getElapsedTimeFormatted(): String {
        val startTime = encounterStartTime ?: return "0 seconds"
        val elapsedMs = System.currentTimeMillis() - startTime
        val totalSeconds = elapsedMs / 1000
        val minutes = totalSeconds / 60
        val seconds = totalSeconds % 60

        return when {
            minutes == 0L -> "$seconds seconds"
            seconds == 0L -> "$minutes minutes"
            else -> "$minutes minutes $seconds seconds"
        }
    }

    /**
     * Get elapsed time in minutes (for billing)
     */
    private fun getElapsedMinutes(): Int {
        val startTime = encounterStartTime ?: return 0
        val elapsedMs = System.currentTimeMillis() - startTime
        return (elapsedMs / 60000).toInt()
    }

    /**
     * Get elapsed time in MM:SS format for display
     */
    private fun getElapsedTimeDisplay(): String {
        val startTime = encounterStartTime ?: return "00:00"
        val elapsedMs = System.currentTimeMillis() - startTime
        val totalSeconds = elapsedMs / 1000
        val minutes = totalSeconds / 60
        val seconds = totalSeconds % 60
        return String.format("%02d:%02d", minutes, seconds)
    }

    /**
     * Get elapsed time in seconds
     */
    private fun getElapsedSeconds(): Long {
        val startTime = encounterStartTime ?: return 0
        return (System.currentTimeMillis() - startTime) / 1000
    }

    /**
     * Show the timer indicator on screen
     */
    private fun showTimerIndicator() {
        if (timerIndicatorView != null) return

        timerIndicatorView = TextView(this).apply {
            text = "⏱ 00:00"
            textSize = 14f
            setTextColor(0xFFFFFFFF.toInt())
            setBackgroundColor(0xCC2563EB.toInt())  // Blue with transparency
            setPadding(16, 8, 16, 8)
            gravity = android.view.Gravity.CENTER

            // Position at top right
            val params = android.widget.FrameLayout.LayoutParams(
                android.widget.FrameLayout.LayoutParams.WRAP_CONTENT,
                android.widget.FrameLayout.LayoutParams.WRAP_CONTENT
            ).apply {
                gravity = android.view.Gravity.TOP or android.view.Gravity.END
                topMargin = 100
                rightMargin = 16
            }
            layoutParams = params
        }

        val rootView = findViewById<android.view.ViewGroup>(android.R.id.content)
        rootView.addView(timerIndicatorView)
    }

    /**
     * Hide the timer indicator
     */
    private fun hideTimerIndicator() {
        timerIndicatorView?.let { view ->
            val rootView = findViewById<android.view.ViewGroup>(android.R.id.content)
            rootView.removeView(view)
        }
        timerIndicatorView = null
    }

    /**
     * Start periodic timer updates
     */
    private fun startTimerUpdates() {
        timerUpdateHandler = android.os.Handler(android.os.Looper.getMainLooper())
        timerUpdateRunnable = object : Runnable {
            override fun run() {
                if (encounterTimerRunning) {
                    updateTimerDisplay()
                    timerUpdateHandler?.postDelayed(this, 1000)  // Update every second
                }
            }
        }
        timerUpdateHandler?.post(timerUpdateRunnable!!)
    }

    /**
     * Stop periodic timer updates
     */
    private fun stopTimerUpdates() {
        timerUpdateRunnable?.let { timerUpdateHandler?.removeCallbacks(it) }
        timerUpdateHandler = null
        timerUpdateRunnable = null
    }

    /**
     * Update the timer display
     */
    private fun updateTimerDisplay() {
        timerIndicatorView?.text = "⏱ ${getElapsedTimeDisplay()}"
    }

    /**
     * Get encounter time for documentation (adds to note)
     */
    private fun getEncounterTimeForNote(): String {
        if (!encounterTimerRunning && encounterStartTime == null) return ""
        val minutes = getElapsedMinutes()
        return "Time spent with patient: $minutes minutes"
    }

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
            |📋 SBAR HANDOFF
            |• "Handoff report" - Generate SBAR report
            |• "SBAR" - Show handoff report
            |• "Read handoff" - Speak handoff aloud
            |• "Give handoff" - Verbal SBAR report
            |
            |📄 DISCHARGE SUMMARY
            |• "Discharge summary" - Generate summary
            |• "Discharge instructions" - Patient instructions
            |• "Read discharge" - Speak to patient
            |• "Patient education" - Verbal instructions
            |
            |✅ PROCEDURE CHECKLISTS
            |• "Show checklists" - List available checklists
            |• "Start timeout checklist" - Begin timeout
            |• "Start central line checklist" - CL insertion
            |• "Check [number]" - Check off item
            |• "Check all" - Mark all complete
            |• "Read checklist" - Speak items aloud
            |
            |🔔 CLINICAL REMINDERS
            |• "Clinical reminders" - Show care reminders
            |• "Preventive care" - Age/condition-based alerts
            |• "Health reminders" - Screening prompts
            |
            |⚖️ MED RECONCILIATION
            |• "Med reconciliation" - Start med rec
            |• "Add home med [name]" - Add medication
            |• "Remove home med [#]" - Remove by number
            |• "Compare meds" - Show discrepancies
            |• "Clear home meds" - Start over
            |
            |📤 REFERRAL TRACKING
            |• "Show referrals" - View all referrals
            |• "Refer to [specialty] for [reason]"
            |• "Urgent referral to [specialty]"
            |• "Mark referral [#] scheduled"
            |• "Mark referral [#] complete"
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
            |📄 VOICE TEMPLATES
            |• "Use [template] template" - Apply template
            |• "List templates" - Show all templates
            |• "Save as template [name]" - Save current note
            |• "Delete template [name]" - Remove user template
            |  (diabetes, hypertension, URI, physical,
            |   back pain, UTI, well child, chest pain)
            |
            |📋 VOICE ORDERS
            |• "Order [lab]" - Order a lab test
            |  (CBC, CMP, BMP, UA, Lipids, TSH, A1c, PT/INR)
            |• "Order [imaging]" - Order imaging study
            |  (chest x-ray, CT head/chest, MRI, echo)
            |• "Order CT [part] with/without contrast"
            |• "Prescribe [med] [dose] [freq] for [duration]"
            |  (amoxicillin, ibuprofen, prednisone, etc.)
            |• "Show orders" - View pending orders
            |• "Cancel order" - Remove last order
            |• "Clear all orders" - Remove all orders
            |• "Yes" / "No" - Confirm/reject after warning
            |
            |📦 ORDER SETS (Batch Orders)
            |• "Order chest pain workup" - ACS rule-out
            |• "Order sepsis bundle" - Sepsis workup
            |• "Order stroke workup" - CVA workup
            |• "Order admission labs" - Standard admission
            |• "Order preop labs" - Surgical clearance
            |• "Order PE workup" - Pulmonary embolism
            |• "Order DKA protocol" - Diabetic ketoacidosis
            |• "Order pneumonia workup" - CAP workup
            |• "List order sets" - Show all sets
            |• "What's in [set]" - Preview set contents
            |
            |⏱️ ENCOUNTER TIMER
            |• "Start timer" - Begin timing encounter
            |• "Stop timer" - End timer, report total
            |• "How long" - Check elapsed time
            |• "Reset timer" - Restart from zero
            |
            |📊 VOICE VITALS ENTRY
            |• "BP 120 over 80" - Record blood pressure
            |• "Pulse 72" / "Heart rate 80" - Record HR
            |• "Temp 98.6" - Record temperature
            |• "O2 sat 98" / "Oxygen 95" - Record SpO2
            |• "Resp rate 16" - Record respiratory rate
            |• "Weight 180 pounds" - Record weight
            |• "Height 5 foot 10" - Record height
            |• "Pain 5 out of 10" - Record pain level
            |• "Show captured vitals" - View all vitals
            |• "Vital history" - View past readings
            |• "Add vitals to note" - Insert into note
            |• "Clear vitals" - Remove all captured
            |
            |🧮 MEDICAL CALCULATORS
            |• "Calculate BMI" - Body mass index
            |• "Calculate GFR" - Kidney function
            |• "Corrected calcium" - Adjust for albumin
            |• "Anion gap" - From BMP labs
            |• "A1c to glucose" - Convert HbA1c
            |• "Calculate MAP" - Mean arterial pressure
            |• "Creatinine clearance" - CrCl
            |• "CHADS VASc" - Stroke risk
            |• "Calculators" - Show all
            |
            |🎤 CUSTOM COMMANDS
            |• "Create command [name] that does [actions]"
            |• "When I say [phrase] do [action]"
            |• "Teach [name] to [actions]"
            |• "My commands" - List custom commands
            |• "Delete command [name]" - Remove
            |
            |🏥 SPECIALTY TEMPLATES
            |• "Specialty templates" - List all 14 templates
            |• "Use [template] template" - Apply template
            |  (cardiology chest pain, heart failure, afib,
            |   ortho joint pain, fracture, neuro headache,
            |   stroke, gi abdominal pain, gerd, pulm copd,
            |   asthma, psych depression, anxiety, trauma, sepsis)
            |
            |📜 NOTE VERSIONING
            |• "Version history" - Show all note versions
            |• "Restore version [N]" - Restore older version
            |• "Compare versions" - Diff current vs previous
            |• "Clear version history" - Clear all versions
            |
            |🔐 DATA ENCRYPTION
            |• "Encryption status" - Show security info
            |• "Wipe data" - Securely erase all PHI
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

    // ═══════════════════════════════════════════════════════════════════════════
    // HANDOFF REPORT - SBAR format for shift handoffs
    // ═══════════════════════════════════════════════════════════════════════════

    /**
     * Generate and display SBAR handoff report for current patient
     * SBAR = Situation, Background, Assessment, Recommendation
     */
    private fun generateHandoffReport() {
        val patient = currentPatientData
        if (patient == null) {
            speakFeedback("No patient loaded. Load a patient first for handoff report.")
            return
        }

        val name = patient.optString("name", "Unknown")
        val dob = patient.optString("date_of_birth", "")
        val gender = patient.optString("gender", "").uppercase()
        val patientId = patient.optString("patient_id", "")

        val content = StringBuilder()
        content.append("═══════════════════════════════════\n")
        content.append("📋 SBAR HANDOFF REPORT\n")
        content.append("═══════════════════════════════════\n\n")

        // Header with patient info
        content.append("👤 $name")
        if (gender.isNotEmpty()) content.append(" ($gender)")
        if (dob.isNotEmpty()) content.append(" DOB: $dob")
        content.append("\n")
        if (patientId.isNotEmpty()) content.append("MRN: $patientId\n")
        content.append("\n")

        // S - SITUATION
        content.append("▸ S - SITUATION\n")
        content.append("───────────────────────────────────\n")
        val conditions = patient.optJSONArray("conditions")
        if (conditions != null && conditions.length() > 0) {
            val primaryCondition = conditions.getJSONObject(0).optString("name", "")
            content.append("Primary: $primaryCondition\n")
            if (conditions.length() > 1) {
                content.append("+ ${conditions.length() - 1} other active problems\n")
            }
        } else {
            content.append("No active problems documented\n")
        }

        // Check for critical vitals
        val criticalVitals = patient.optJSONArray("critical_vitals")
        if (criticalVitals != null && criticalVitals.length() > 0) {
            content.append("⚠️ CRITICAL: ")
            for (i in 0 until criticalVitals.length()) {
                val cv = criticalVitals.getJSONObject(i)
                content.append("${cv.optString("name")}: ${cv.optString("value")} ")
            }
            content.append("\n")
        }
        content.append("\n")

        // B - BACKGROUND
        content.append("▸ B - BACKGROUND\n")
        content.append("───────────────────────────────────\n")

        // Allergies (critical for handoff)
        val allergies = patient.optJSONArray("allergies")
        if (allergies != null && allergies.length() > 0) {
            content.append("🚨 Allergies: ")
            for (i in 0 until minOf(allergies.length(), 4)) {
                if (i > 0) content.append(", ")
                content.append(allergies.getString(i))
            }
            if (allergies.length() > 4) content.append(" +${allergies.length() - 4} more")
            content.append("\n")
        } else {
            content.append("Allergies: NKDA\n")
        }

        // Current medications
        val meds = patient.optJSONArray("medications")
        if (meds != null && meds.length() > 0) {
            content.append("💊 Meds: ${meds.length()} active\n")
            for (i in 0 until minOf(meds.length(), 3)) {
                content.append("  • ${meds.getString(i)}\n")
            }
            if (meds.length() > 3) content.append("  + ${meds.length() - 3} more\n")
        }

        // Relevant history
        if (conditions != null && conditions.length() > 1) {
            content.append("Hx: ")
            for (i in 1 until minOf(conditions.length(), 4)) {
                val cond = conditions.getJSONObject(i)
                if (i > 1) content.append(", ")
                content.append(cond.optString("name", ""))
            }
            content.append("\n")
        }
        content.append("\n")

        // A - ASSESSMENT
        content.append("▸ A - ASSESSMENT\n")
        content.append("───────────────────────────────────\n")

        // Current vitals
        val vitals = patient.optJSONArray("vitals")
        if (vitals != null && vitals.length() > 0) {
            content.append("Vitals:\n")
            for (i in 0 until minOf(vitals.length(), 6)) {
                val v = vitals.getJSONObject(i)
                val vName = v.optString("name", "")
                val vValue = v.optString("value", "")
                val vUnit = v.optString("unit", "")
                val interp = v.optString("interpretation", "")
                val flag = when (interp) {
                    "HH", "LL" -> "‼️"
                    "H" -> "↑"
                    "L" -> "↓"
                    else -> ""
                }
                content.append("  $vName: $vValue $vUnit $flag\n")
            }
        }

        // Recent/pending labs
        val labs = patient.optJSONArray("labs")
        if (labs != null && labs.length() > 0) {
            content.append("Recent Labs:\n")
            for (i in 0 until minOf(labs.length(), 4)) {
                val lab = labs.getJSONObject(i)
                val labName = lab.optString("name", "")
                val labValue = lab.optString("value", "")
                val labUnit = lab.optString("unit", "")
                content.append("  $labName: $labValue $labUnit\n")
            }
        }
        content.append("\n")

        // R - RECOMMENDATION
        content.append("▸ R - RECOMMENDATION\n")
        content.append("───────────────────────────────────\n")

        // Include pending orders if any
        if (orderQueue.isNotEmpty()) {
            content.append("Pending Orders:\n")
            for (order in orderQueue.take(5)) {
                content.append("  • ${order.displayName}\n")
            }
            if (orderQueue.size > 5) {
                content.append("  + ${orderQueue.size - 5} more\n")
            }
        }

        // Care plans
        val carePlans = patient.optJSONArray("care_plans")
        if (carePlans != null && carePlans.length() > 0) {
            content.append("Active Care Plans:\n")
            for (i in 0 until minOf(carePlans.length(), 2)) {
                val plan = carePlans.getJSONObject(i)
                content.append("  • ${plan.optString("title", "Care Plan")}\n")
            }
        }

        // Include encounter time if timer was running
        val elapsedSeconds = getElapsedSeconds()
        if (elapsedSeconds > 0) {
            val mins = elapsedSeconds / 60
            val secs = elapsedSeconds % 60
            content.append("\n⏱️ Encounter time: ${mins}m ${secs}s\n")
        }

        content.append("\n───────────────────────────────────\n")
        content.append("Report generated: ${java.text.SimpleDateFormat("HH:mm", java.util.Locale.US).format(java.util.Date())}")

        showDataOverlay("SBAR Handoff", content.toString())
        speakFeedback("Handoff report ready for $name")
    }

    /**
     * Speak the SBAR handoff report aloud
     */
    private fun speakHandoffReport() {
        val patient = currentPatientData
        if (patient == null) {
            speak("No patient loaded for handoff.")
            return
        }

        val name = patient.optString("name", "Unknown")
        val speech = StringBuilder()

        // S - Situation
        speech.append("SBAR handoff for $name. ")
        speech.append("Situation: ")
        val conditions = patient.optJSONArray("conditions")
        if (conditions != null && conditions.length() > 0) {
            val primary = conditions.getJSONObject(0).optString("name", "")
            speech.append("Primary problem is $primary. ")
        }

        // Check critical
        val criticalVitals = patient.optJSONArray("critical_vitals")
        if (criticalVitals != null && criticalVitals.length() > 0) {
            speech.append("Alert: Patient has critical vitals. ")
        }

        // B - Background
        speech.append("Background: ")
        val allergies = patient.optJSONArray("allergies")
        if (allergies != null && allergies.length() > 0) {
            speech.append("Allergies include ${allergies.getString(0)}. ")
        } else {
            speech.append("No known drug allergies. ")
        }

        val meds = patient.optJSONArray("medications")
        if (meds != null && meds.length() > 0) {
            speech.append("On ${meds.length()} medications. ")
        }

        // A - Assessment
        speech.append("Assessment: ")
        val vitals = patient.optJSONArray("vitals")
        if (vitals != null && vitals.length() > 0) {
            for (i in 0 until minOf(vitals.length(), 3)) {
                val v = vitals.getJSONObject(i)
                speech.append("${formatVitalNameForSpeech(v.optString("name", ""))}: ${v.optString("value", "")}. ")
            }
        }

        // R - Recommendation
        speech.append("Recommendation: ")
        if (orderQueue.isNotEmpty()) {
            speech.append("${orderQueue.size} pending orders. ")
        }
        speech.append("Continue current plan. ")

        speech.append("End of handoff.")

        // Show visual report too
        generateHandoffReport()

        // Speak
        speak(speech.toString())
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // DISCHARGE SUMMARY - Patient discharge instructions
    // ═══════════════════════════════════════════════════════════════════════════

    /**
     * Generate and display discharge summary with instructions
     */
    private fun generateDischargeSummary() {
        val patient = currentPatientData
        if (patient == null) {
            speakFeedback("No patient loaded. Load a patient first for discharge summary.")
            return
        }

        val name = patient.optString("name", "Unknown")
        val dob = patient.optString("date_of_birth", "")
        val patientId = patient.optString("patient_id", "")

        val content = StringBuilder()
        content.append("═══════════════════════════════════\n")
        content.append("📄 DISCHARGE SUMMARY\n")
        content.append("═══════════════════════════════════\n\n")

        // Header
        content.append("👤 $name")
        if (dob.isNotEmpty()) content.append(" | DOB: $dob")
        content.append("\n")
        if (patientId.isNotEmpty()) content.append("MRN: $patientId\n")
        content.append("Date: ${java.text.SimpleDateFormat("MM/dd/yyyy", java.util.Locale.US).format(java.util.Date())}\n")
        content.append("\n")

        // DIAGNOSIS
        content.append("▸ DIAGNOSIS\n")
        content.append("───────────────────────────────────\n")
        val conditions = patient.optJSONArray("conditions")
        if (conditions != null && conditions.length() > 0) {
            for (i in 0 until minOf(conditions.length(), 5)) {
                val cond = conditions.getJSONObject(i)
                content.append("• ${cond.optString("name", "")}\n")
            }
        } else {
            content.append("• See provider notes\n")
        }
        content.append("\n")

        // MEDICATIONS
        content.append("▸ MEDICATIONS TO TAKE\n")
        content.append("───────────────────────────────────\n")
        val meds = patient.optJSONArray("medications")
        if (meds != null && meds.length() > 0) {
            for (i in 0 until meds.length()) {
                content.append("💊 ${meds.getString(i)}\n")
            }
        } else {
            content.append("• No medications prescribed\n")
        }

        // Include pending orders as new prescriptions
        val newMeds = orderQueue.filter { it.type == OrderType.MEDICATION }
        if (newMeds.isNotEmpty()) {
            content.append("\n📋 NEW PRESCRIPTIONS:\n")
            for (med in newMeds) {
                content.append("💊 ${med.displayName}\n")
            }
        }
        content.append("\n")

        // ALLERGIES WARNING
        val allergies = patient.optJSONArray("allergies")
        if (allergies != null && allergies.length() > 0) {
            content.append("▸ ⚠️ ALLERGIES\n")
            content.append("───────────────────────────────────\n")
            for (i in 0 until allergies.length()) {
                content.append("🚫 ${allergies.getString(i)}\n")
            }
            content.append("\n")
        }

        // FOLLOW-UP INSTRUCTIONS
        content.append("▸ FOLLOW-UP\n")
        content.append("───────────────────────────────────\n")
        val carePlans = patient.optJSONArray("care_plans")
        if (carePlans != null && carePlans.length() > 0) {
            for (i in 0 until minOf(carePlans.length(), 3)) {
                val plan = carePlans.getJSONObject(i)
                content.append("• ${plan.optString("title", "Follow care plan")}\n")
            }
        }

        // Pending labs/imaging as follow-up
        val pendingLabs = orderQueue.filter { it.type == OrderType.LAB }
        val pendingImaging = orderQueue.filter { it.type == OrderType.IMAGING }
        if (pendingLabs.isNotEmpty()) {
            content.append("• Complete lab work: ${pendingLabs.joinToString(", ") { it.displayName }}\n")
        }
        if (pendingImaging.isNotEmpty()) {
            content.append("• Complete imaging: ${pendingImaging.joinToString(", ") { it.displayName }}\n")
        }

        // Default follow-up
        content.append("• Follow up with your provider as directed\n")
        content.append("• Call if symptoms worsen\n")
        content.append("\n")

        // RETURN PRECAUTIONS
        content.append("▸ WHEN TO SEEK CARE\n")
        content.append("───────────────────────────────────\n")
        content.append("Return to ER or call 911 if:\n")
        content.append("• Difficulty breathing\n")
        content.append("• Chest pain\n")
        content.append("• Severe pain not relieved by medication\n")
        content.append("• High fever (>101.5°F)\n")
        content.append("• Confusion or altered mental status\n")
        content.append("• Signs of infection (redness, swelling, pus)\n")
        content.append("\n")

        // ACTIVITY & DIET
        content.append("▸ ACTIVITY & DIET\n")
        content.append("───────────────────────────────────\n")
        content.append("• Resume normal activities as tolerated\n")
        content.append("• Stay hydrated\n")
        content.append("• Follow dietary restrictions if prescribed\n")
        content.append("\n")

        content.append("───────────────────────────────────\n")
        content.append("Questions? Call your provider's office\n")
        content.append("Generated: ${java.text.SimpleDateFormat("HH:mm", java.util.Locale.US).format(java.util.Date())}")

        showDataOverlay("Discharge Summary", content.toString())
        speakFeedback("Discharge summary ready for $name")
    }

    /**
     * Speak discharge instructions aloud for patient education
     */
    private fun speakDischargeInstructions() {
        val patient = currentPatientData
        if (patient == null) {
            speak("No patient loaded for discharge instructions.")
            return
        }

        val name = patient.optString("name", "Unknown")
        val speech = StringBuilder()

        speech.append("Discharge instructions for $name. ")

        // Diagnosis
        val conditions = patient.optJSONArray("conditions")
        if (conditions != null && conditions.length() > 0) {
            val primary = conditions.getJSONObject(0).optString("name", "")
            speech.append("You were seen for $primary. ")
        }

        // Medications
        val meds = patient.optJSONArray("medications")
        if (meds != null && meds.length() > 0) {
            speech.append("Continue taking your ${meds.length()} medications as prescribed. ")
        }

        // New prescriptions
        val newMedsSpeech = orderQueue.filter { it.type == OrderType.MEDICATION }
        if (newMedsSpeech.isNotEmpty()) {
            speech.append("You have ${newMedsSpeech.size} new prescriptions. ")
        }

        // Allergies reminder
        val allergies = patient.optJSONArray("allergies")
        if (allergies != null && allergies.length() > 0) {
            speech.append("Remember, you are allergic to ${allergies.getString(0)}. ")
        }

        // Follow-up
        val pendingLabsSpeech = orderQueue.filter { it.type == OrderType.LAB }
        if (pendingLabsSpeech.isNotEmpty()) {
            speech.append("You need to complete lab work. ")
        }

        speech.append("Follow up with your provider as directed. ")
        speech.append("Return to the emergency room if you have difficulty breathing, chest pain, or your symptoms get worse. ")
        speech.append("End of discharge instructions.")

        // Show visual too
        generateDischargeSummary()

        // Speak
        speak(speech.toString())
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // PROCEDURE CHECKLISTS - Safety workflows for common procedures
    // ═══════════════════════════════════════════════════════════════════════════

    private data class ProcedureChecklist(
        val name: String,
        val category: String,
        val items: List<String>,
        val timeoutItems: List<String> = emptyList(),
        val signOutItems: List<String> = emptyList()
    )

    private val procedureChecklists = mapOf(
        "timeout" to ProcedureChecklist(
            name = "Universal Protocol Timeout",
            category = "surgical",
            items = listOf(
                "Correct patient identity confirmed",
                "Correct procedure confirmed",
                "Correct site marked and visible",
                "Patient consent signed",
                "Relevant images displayed",
                "Allergies reviewed",
                "Antibiotics given (if applicable)",
                "VTE prophylaxis addressed",
                "All team members introduced"
            )
        ),
        "central line" to ProcedureChecklist(
            name = "Central Line Insertion",
            category = "procedure",
            items = listOf(
                "Hand hygiene performed",
                "Sterile gown and gloves",
                "Full barrier precautions",
                "Chlorhexidine skin prep",
                "Sterile drape placement",
                "Ultrasound guidance available",
                "Lidocaine for local anesthesia",
                "Confirm catheter type and size",
                "Flush all lumens"
            ),
            signOutItems = listOf(
                "Placement confirmed by aspiration",
                "Catheter secured",
                "Sterile dressing applied",
                "Chest X-ray ordered (if applicable)",
                "Document insertion site and attempts"
            )
        ),
        "intubation" to ProcedureChecklist(
            name = "Intubation Checklist",
            category = "airway",
            items = listOf(
                "Equipment check: laryngoscope, ETT, stylet",
                "Suction available and working",
                "Bag-valve-mask ready",
                "Capnography available",
                "IV access confirmed",
                "Medications drawn: sedation, paralytic",
                "Backup airway available (LMA, cric kit)",
                "Patient positioned (sniffing position)",
                "Pre-oxygenation complete"
            ),
            signOutItems = listOf(
                "ETT placement confirmed by capnography",
                "Bilateral breath sounds confirmed",
                "ETT secured at appropriate depth",
                "Ventilator settings ordered",
                "Chest X-ray ordered",
                "Sedation drip started"
            )
        ),
        "lumbar puncture" to ProcedureChecklist(
            name = "Lumbar Puncture",
            category = "procedure",
            items = listOf(
                "Consent obtained",
                "Coagulation status checked",
                "Platelet count adequate (>50k)",
                "No anticoagulants or held appropriately",
                "Sterile field prepared",
                "Local anesthesia ready",
                "Spinal needle and manometer available",
                "Collection tubes labeled",
                "Patient positioned (lateral or sitting)"
            ),
            signOutItems = listOf(
                "Opening pressure documented",
                "Appropriate tubes collected",
                "Closing pressure documented",
                "Site dressed",
                "Patient instructed to lie flat"
            )
        ),
        "blood transfusion" to ProcedureChecklist(
            name = "Blood Transfusion Safety",
            category = "transfusion",
            items = listOf(
                "Consent for transfusion obtained",
                "Type and screen on file",
                "Two-nurse verification at bedside",
                "Patient ID band matches blood product",
                "Blood product type matches order",
                "Expiration date checked",
                "IV access adequate (18g or larger)",
                "Baseline vital signs documented",
                "Emergency medications available"
            ),
            signOutItems = listOf(
                "Transfusion start time documented",
                "Vital signs at 15 minutes",
                "Monitor for transfusion reaction",
                "Vital signs at completion",
                "Total volume and duration documented"
            )
        ),
        "sedation" to ProcedureChecklist(
            name = "Procedural Sedation",
            category = "sedation",
            items = listOf(
                "NPO status confirmed",
                "Airway assessment completed",
                "ASA classification documented",
                "Consent obtained",
                "IV access confirmed",
                "Monitoring equipment ready",
                "Oxygen and suction available",
                "Reversal agents available",
                "Crash cart nearby",
                "Recovery plan in place"
            )
        )
    )

    private val activeChecklistItems = mutableMapOf<String, MutableSet<Int>>()
    private var currentChecklist: String? = null

    /**
     * Show available procedure checklists
     */
    private fun showProcedureChecklists() {
        val content = StringBuilder()
        content.append("═══════════════════════════════════\n")
        content.append("📋 PROCEDURE CHECKLISTS\n")
        content.append("═══════════════════════════════════\n\n")
        content.append("Say \"start [checklist] checklist\" to begin:\n\n")

        procedureChecklists.forEach { (key, checklist) ->
            val emoji = when (checklist.category) {
                "surgical" -> "🔪"
                "airway" -> "🫁"
                "transfusion" -> "🩸"
                "sedation" -> "💉"
                else -> "📋"
            }
            content.append("$emoji $key - ${checklist.name}\n")
        }

        content.append("\n───────────────────────────────────\n")
        content.append("Examples:\n")
        content.append("• \"Start timeout checklist\"\n")
        content.append("• \"Start central line checklist\"\n")
        content.append("• \"Start intubation checklist\"")

        showDataOverlay("Procedure Checklists", content.toString())
        speakFeedback("${procedureChecklists.size} procedure checklists available")
    }

    /**
     * Start a specific procedure checklist
     */
    private fun startProcedureChecklist(checklistName: String) {
        val key = checklistName.lowercase().trim()
        val checklist = procedureChecklists[key]
            ?: procedureChecklists.entries.find { it.value.name.lowercase().contains(key) }?.value

        if (checklist == null) {
            speakFeedback("Checklist not found. Say 'show checklists' to see available options.")
            return
        }

        currentChecklist = procedureChecklists.entries.find { it.value == checklist }?.key
        activeChecklistItems[currentChecklist!!] = mutableSetOf()

        displayChecklist(checklist)
        speakFeedback("${checklist.name} checklist started. ${checklist.items.size} items to verify.")
    }

    /**
     * Display current checklist state
     */
    private fun displayChecklist(checklist: ProcedureChecklist) {
        val content = StringBuilder()
        val key = currentChecklist ?: return
        val checked = activeChecklistItems[key] ?: mutableSetOf()

        content.append("═══════════════════════════════════\n")
        content.append("📋 ${checklist.name.uppercase()}\n")
        content.append("═══════════════════════════════════\n\n")

        content.append("▸ PRE-PROCEDURE\n")
        content.append("───────────────────────────────────\n")
        checklist.items.forEachIndexed { index, item ->
            val checkMark = if (checked.contains(index)) "✅" else "⬜"
            content.append("$checkMark ${index + 1}. $item\n")
        }

        if (checklist.signOutItems.isNotEmpty()) {
            content.append("\n▸ POST-PROCEDURE\n")
            content.append("───────────────────────────────────\n")
            val offset = checklist.items.size
            checklist.signOutItems.forEachIndexed { index, item ->
                val checkMark = if (checked.contains(offset + index)) "✅" else "⬜"
                content.append("$checkMark ${offset + index + 1}. $item\n")
            }
        }

        val totalItems = checklist.items.size + checklist.signOutItems.size
        val completedCount = checked.size
        val progress = (completedCount * 100) / totalItems

        content.append("\n───────────────────────────────────\n")
        content.append("Progress: $completedCount/$totalItems ($progress%)\n")
        content.append("Say \"check [number]\" or \"check all\"")

        showDataOverlay("Checklist", content.toString())
    }

    /**
     * Check off an item in the current checklist
     */
    private fun checkChecklistItem(itemNumber: Int) {
        val key = currentChecklist
        if (key == null) {
            speakFeedback("No active checklist. Say 'start timeout checklist' to begin.")
            return
        }

        val checklist = procedureChecklists[key] ?: return
        val totalItems = checklist.items.size + checklist.signOutItems.size
        val index = itemNumber - 1

        if (index < 0 || index >= totalItems) {
            speakFeedback("Invalid item number. Valid range is 1 to $totalItems.")
            return
        }

        val checked = activeChecklistItems.getOrPut(key) { mutableSetOf() }

        if (checked.contains(index)) {
            checked.remove(index)
            speakFeedback("Item $itemNumber unchecked")
        } else {
            checked.add(index)
            val remaining = totalItems - checked.size
            if (remaining == 0) {
                speakFeedback("All items complete! Checklist verified.")
            } else {
                speakFeedback("Item $itemNumber checked. $remaining remaining.")
            }
        }

        displayChecklist(checklist)
    }

    /**
     * Check all items in current checklist
     */
    private fun checkAllChecklistItems() {
        val key = currentChecklist
        if (key == null) {
            speakFeedback("No active checklist.")
            return
        }

        val checklist = procedureChecklists[key] ?: return
        val totalItems = checklist.items.size + checklist.signOutItems.size
        val checked = activeChecklistItems.getOrPut(key) { mutableSetOf() }

        for (i in 0 until totalItems) {
            checked.add(i)
        }

        displayChecklist(checklist)
        speakFeedback("All ${totalItems} items checked. Checklist complete.")
    }

    /**
     * Read the current checklist aloud
     */
    private fun readChecklist() {
        val key = currentChecklist
        if (key == null) {
            speakFeedback("No active checklist.")
            return
        }

        val checklist = procedureChecklists[key] ?: return
        val checked = activeChecklistItems[key] ?: mutableSetOf()
        val speech = StringBuilder()

        speech.append("${checklist.name}. ")
        checklist.items.forEachIndexed { index, item ->
            val status = if (checked.contains(index)) "checked" else "not checked"
            speech.append("Item ${index + 1}: $item. $status. ")
        }

        val remaining = checklist.items.size - checked.count { it < checklist.items.size }
        speech.append("$remaining items remaining in pre-procedure.")

        speak(speech.toString())
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // CLINICAL REMINDERS - Preventive care prompts based on patient data
    // ═══════════════════════════════════════════════════════════════════════════

    private data class ClinicalReminder(
        val category: String,
        val reminder: String,
        val priority: String, // high, medium, low
        val source: String
    )

    /**
     * Generate clinical reminders based on patient data
     */
    private fun generateClinicalReminders() {
        val patient = currentPatientData
        if (patient == null) {
            speakFeedback("No patient loaded. Load a patient first.")
            return
        }

        val name = patient.optString("name", "Unknown")
        val dob = patient.optString("date_of_birth", "")
        val gender = patient.optString("gender", "").lowercase()
        val conditions = patient.optJSONArray("conditions")
        val meds = patient.optJSONArray("medications")
        val immunizations = patient.optJSONArray("immunizations")
        val labs = patient.optJSONArray("labs")

        val reminders = mutableListOf<ClinicalReminder>()

        // Calculate age
        val age = calculateAgeFromDob(dob)

        // Age-based screening reminders
        if (age >= 50) {
            reminders.add(ClinicalReminder("screening", "Colonoscopy due if not done in 10 years", "medium", "USPSTF"))
        }
        if (age >= 45) {
            reminders.add(ClinicalReminder("screening", "Diabetes screening (A1c or FPG) if not done", "medium", "ADA"))
        }
        if (age >= 40) {
            reminders.add(ClinicalReminder("screening", "Lipid panel due if not done in 5 years", "low", "ACC/AHA"))
        }
        if (gender == "female" && age >= 40) {
            reminders.add(ClinicalReminder("screening", "Mammogram due if not done in 1-2 years", "medium", "USPSTF"))
        }
        if (gender == "female" && age in 21..65) {
            reminders.add(ClinicalReminder("screening", "Pap smear due if not done in 3 years", "medium", "USPSTF"))
        }
        if (age >= 65) {
            reminders.add(ClinicalReminder("screening", "DEXA scan for osteoporosis screening", "low", "USPSTF"))
            reminders.add(ClinicalReminder("vaccine", "Pneumococcal vaccine (PCV20 or PPSV23)", "medium", "CDC"))
            reminders.add(ClinicalReminder("vaccine", "Shingrix (2-dose series) if not received", "medium", "CDC"))
        }

        // Condition-based reminders
        if (conditions != null) {
            for (i in 0 until conditions.length()) {
                val condition = conditions.getJSONObject(i).optString("name", "").lowercase()

                if (condition.contains("diabetes") || condition.contains("a1c")) {
                    reminders.add(ClinicalReminder("monitoring", "A1c check due if >3 months", "high", "ADA"))
                    reminders.add(ClinicalReminder("monitoring", "Annual eye exam for diabetic retinopathy", "medium", "ADA"))
                    reminders.add(ClinicalReminder("monitoring", "Annual foot exam", "medium", "ADA"))
                    reminders.add(ClinicalReminder("monitoring", "Annual urine microalbumin", "medium", "ADA"))
                }
                if (condition.contains("hypertension") || condition.contains("htn")) {
                    reminders.add(ClinicalReminder("monitoring", "Blood pressure goal <130/80", "high", "ACC/AHA"))
                    reminders.add(ClinicalReminder("monitoring", "Annual BMP for electrolytes/kidney function", "medium", "JNC"))
                }
                if (condition.contains("heart failure") || condition.contains("chf")) {
                    reminders.add(ClinicalReminder("monitoring", "Daily weight monitoring", "high", "ACC/AHA"))
                    reminders.add(ClinicalReminder("monitoring", "BNP/proBNP if symptoms change", "medium", "ACC/AHA"))
                    reminders.add(ClinicalReminder("medication", "Verify on GDMT (BB, ACEi/ARB/ARNI, MRA, SGLT2i)", "high", "ACC/AHA"))
                }
                if (condition.contains("copd")) {
                    reminders.add(ClinicalReminder("vaccine", "Annual influenza vaccine", "high", "CDC"))
                    reminders.add(ClinicalReminder("vaccine", "Pneumococcal vaccine", "high", "CDC"))
                    reminders.add(ClinicalReminder("monitoring", "Pulmonary function test annually", "medium", "GOLD"))
                }
                if (condition.contains("afib") || condition.contains("atrial fibrillation")) {
                    reminders.add(ClinicalReminder("monitoring", "CHADS2-VASc score for anticoagulation", "high", "ACC/AHA"))
                    reminders.add(ClinicalReminder("monitoring", "Rate control goal HR <110", "medium", "ACC/AHA"))
                }
                if (condition.contains("ckd") || condition.contains("kidney")) {
                    reminders.add(ClinicalReminder("monitoring", "GFR and urine albumin every 3-6 months", "high", "KDIGO"))
                    reminders.add(ClinicalReminder("medication", "Review nephrotoxic medications", "high", "KDIGO"))
                }
            }
        }

        // Medication-based reminders
        if (meds != null) {
            for (i in 0 until meds.length()) {
                val med = meds.getString(i).lowercase()

                if (med.contains("warfarin") || med.contains("coumadin")) {
                    reminders.add(ClinicalReminder("monitoring", "INR check due if >4 weeks", "high", "Pharmacy"))
                }
                if (med.contains("metformin")) {
                    reminders.add(ClinicalReminder("monitoring", "Annual B12 level", "low", "ADA"))
                }
                if (med.contains("statin")) {
                    reminders.add(ClinicalReminder("monitoring", "Lipid panel in 4-12 weeks if new", "medium", "ACC/AHA"))
                }
                if (med.contains("lithium")) {
                    reminders.add(ClinicalReminder("monitoring", "Lithium level, TSH, creatinine every 6 months", "high", "APA"))
                }
                if (med.contains("amiodarone")) {
                    reminders.add(ClinicalReminder("monitoring", "TSH, LFTs, PFTs every 6 months", "high", "ACC/AHA"))
                }
            }
        }

        // Universal reminders
        reminders.add(ClinicalReminder("vaccine", "Annual influenza vaccine", "medium", "CDC"))

        // Display reminders
        displayClinicalReminders(name, age, reminders)
    }

    private fun calculateAgeFromDob(dob: String): Int {
        return try {
            val parts = dob.split("-")
            if (parts.size >= 1) {
                val birthYear = parts[0].toInt()
                val currentYear = java.util.Calendar.getInstance().get(java.util.Calendar.YEAR)
                currentYear - birthYear
            } else 0
        } catch (e: Exception) { 0 }
    }

    private fun displayClinicalReminders(patientName: String, age: Int, reminders: List<ClinicalReminder>) {
        val content = StringBuilder()
        content.append("═══════════════════════════════════\n")
        content.append("🔔 CLINICAL REMINDERS\n")
        content.append("═══════════════════════════════════\n\n")
        content.append("👤 $patientName")
        if (age > 0) content.append(" (${age}yo)")
        content.append("\n\n")

        val highPriority = reminders.filter { it.priority == "high" }
        val mediumPriority = reminders.filter { it.priority == "medium" }
        val lowPriority = reminders.filter { it.priority == "low" }

        if (highPriority.isNotEmpty()) {
            content.append("▸ ⚠️ HIGH PRIORITY\n")
            content.append("───────────────────────────────────\n")
            highPriority.forEach { r ->
                val icon = when (r.category) {
                    "vaccine" -> "💉"
                    "screening" -> "🔍"
                    "monitoring" -> "📊"
                    "medication" -> "💊"
                    else -> "•"
                }
                content.append("$icon ${r.reminder}\n")
                content.append("   [${r.source}]\n")
            }
            content.append("\n")
        }

        if (mediumPriority.isNotEmpty()) {
            content.append("▸ 📋 RECOMMENDED\n")
            content.append("───────────────────────────────────\n")
            mediumPriority.forEach { r ->
                val icon = when (r.category) {
                    "vaccine" -> "💉"
                    "screening" -> "🔍"
                    "monitoring" -> "📊"
                    "medication" -> "💊"
                    else -> "•"
                }
                content.append("$icon ${r.reminder}\n")
            }
            content.append("\n")
        }

        if (lowPriority.isNotEmpty()) {
            content.append("▸ 📝 CONSIDER\n")
            content.append("───────────────────────────────────\n")
            lowPriority.forEach { r ->
                content.append("• ${r.reminder}\n")
            }
        }

        content.append("\n───────────────────────────────────\n")
        content.append("${reminders.size} reminders generated")

        showDataOverlay("Clinical Reminders", content.toString())

        val highCount = highPriority.size
        if (highCount > 0) {
            speakFeedback("$highCount high priority reminders for $patientName")
        } else {
            speakFeedback("${reminders.size} clinical reminders generated")
        }
    }

    /**
     * Speak high-priority reminders aloud
     */
    private fun speakClinicalReminders() {
        val patient = currentPatientData
        if (patient == null) {
            speak("No patient loaded.")
            return
        }

        // Regenerate and speak
        generateClinicalReminders()
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // MEDICATION RECONCILIATION - Compare home meds vs current meds
    // ═══════════════════════════════════════════════════════════════════════════

    private var homeMedications = mutableListOf<String>()

    /**
     * Start medication reconciliation process
     */
    private fun startMedReconciliation() {
        val patient = currentPatientData
        if (patient == null) {
            speakFeedback("No patient loaded. Load a patient first.")
            return
        }

        val name = patient.optString("name", "Unknown")
        val currentMeds = patient.optJSONArray("medications")

        val content = StringBuilder()
        content.append("═══════════════════════════════════\n")
        content.append("💊 MEDICATION RECONCILIATION\n")
        content.append("═══════════════════════════════════\n\n")
        content.append("👤 $name\n\n")

        content.append("▸ CURRENT MEDICATIONS (EHR)\n")
        content.append("───────────────────────────────────\n")
        if (currentMeds != null && currentMeds.length() > 0) {
            for (i in 0 until currentMeds.length()) {
                content.append("💊 ${currentMeds.getString(i)}\n")
            }
        } else {
            content.append("• No medications on file\n")
        }
        content.append("\n")

        content.append("▸ HOME MEDICATIONS (Patient Report)\n")
        content.append("───────────────────────────────────\n")
        if (homeMedications.isNotEmpty()) {
            homeMedications.forEachIndexed { index, med ->
                content.append("${index + 1}. $med\n")
            }
        } else {
            content.append("• None recorded yet\n")
            content.append("\nSay \"add home med [medication]\" to add\n")
        }

        content.append("\n───────────────────────────────────\n")
        content.append("Commands:\n")
        content.append("• \"Add home med [name]\" - Add medication\n")
        content.append("• \"Remove home med [#]\" - Remove by number\n")
        content.append("• \"Compare meds\" - Show discrepancies\n")
        content.append("• \"Clear home meds\" - Start over")

        showDataOverlay("Med Reconciliation", content.toString())
        speakFeedback("Medication reconciliation started for $name")
    }

    /**
     * Add a home medication
     */
    private fun addHomeMedication(medication: String) {
        homeMedications.add(medication.trim())
        speakFeedback("Added ${medication.trim()}. ${homeMedications.size} home medications.")
        startMedReconciliation() // Refresh display
    }

    /**
     * Remove a home medication by index
     */
    private fun removeHomeMedication(index: Int) {
        if (index in 1..homeMedications.size) {
            val removed = homeMedications.removeAt(index - 1)
            speakFeedback("Removed $removed")
            startMedReconciliation() // Refresh display
        } else {
            speakFeedback("Invalid medication number")
        }
    }

    /**
     * Compare home meds vs EHR meds and show discrepancies
     */
    private fun compareMedications() {
        val patient = currentPatientData
        if (patient == null) {
            speakFeedback("No patient loaded.")
            return
        }

        val name = patient.optString("name", "Unknown")
        val currentMeds = patient.optJSONArray("medications")
        val ehrMedList = mutableListOf<String>()

        if (currentMeds != null) {
            for (i in 0 until currentMeds.length()) {
                ehrMedList.add(currentMeds.getString(i).lowercase())
            }
        }

        val homeMedLower = homeMedications.map { it.lowercase() }

        // Find discrepancies
        val onlyInEhr = ehrMedList.filter { ehrMed ->
            homeMedLower.none { home -> ehrMed.contains(home) || home.contains(ehrMed) }
        }
        val onlyAtHome = homeMedications.filter { homeMed ->
            ehrMedList.none { ehr -> ehr.contains(homeMed.lowercase()) || homeMed.lowercase().contains(ehr) }
        }
        val matched = homeMedications.filter { homeMed ->
            ehrMedList.any { ehr -> ehr.contains(homeMed.lowercase()) || homeMed.lowercase().contains(ehr) }
        }

        val content = StringBuilder()
        content.append("═══════════════════════════════════\n")
        content.append("⚖️ MED RECONCILIATION RESULTS\n")
        content.append("═══════════════════════════════════\n\n")
        content.append("👤 $name\n\n")

        if (matched.isNotEmpty()) {
            content.append("▸ ✅ CONFIRMED (Match)\n")
            content.append("───────────────────────────────────\n")
            matched.forEach { content.append("• $it\n") }
            content.append("\n")
        }

        if (onlyInEhr.isNotEmpty()) {
            content.append("▸ ⚠️ IN EHR ONLY (Verify with patient)\n")
            content.append("───────────────────────────────────\n")
            onlyInEhr.forEach { content.append("• $it\n") }
            content.append("\n")
        }

        if (onlyAtHome.isNotEmpty()) {
            content.append("▸ 🆕 HOME ONLY (Add to EHR?)\n")
            content.append("───────────────────────────────────\n")
            onlyAtHome.forEach { content.append("• $it\n") }
            content.append("\n")
        }

        val discrepancies = onlyInEhr.size + onlyAtHome.size
        content.append("───────────────────────────────────\n")
        if (discrepancies == 0) {
            content.append("✅ No discrepancies found!")
        } else {
            content.append("⚠️ $discrepancies discrepancies to reconcile")
        }

        showDataOverlay("Med Comparison", content.toString())

        if (discrepancies > 0) {
            speakFeedback("$discrepancies medication discrepancies found")
        } else {
            speakFeedback("Medications reconciled. No discrepancies.")
        }
    }

    /**
     * Clear home medications list
     */
    private fun clearHomeMedications() {
        homeMedications.clear()
        speakFeedback("Home medications cleared")
        startMedReconciliation()
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // REFERRAL TRACKING - Track specialist referrals
    // ═══════════════════════════════════════════════════════════════════════════

    private data class Referral(
        val specialty: String,
        val reason: String,
        val urgency: String, // routine, urgent, stat
        val status: String, // pending, scheduled, completed
        val date: String,
        val notes: String = ""
    )

    private val patientReferrals = mutableListOf<Referral>()

    private val commonSpecialties = listOf(
        "cardiology", "pulmonology", "gastroenterology", "neurology",
        "orthopedics", "dermatology", "endocrinology", "nephrology",
        "rheumatology", "oncology", "urology", "psychiatry",
        "ophthalmology", "ENT", "physical therapy", "pain management"
    )

    /**
     * Show referral tracking panel
     */
    private fun showReferrals() {
        val patient = currentPatientData
        val name = patient?.optString("name", "Unknown") ?: "Unknown"

        val content = StringBuilder()
        content.append("═══════════════════════════════════\n")
        content.append("📤 REFERRAL TRACKING\n")
        content.append("═══════════════════════════════════\n\n")
        content.append("👤 $name\n\n")

        if (patientReferrals.isEmpty()) {
            content.append("No active referrals.\n\n")
            content.append("Say \"refer to [specialty] for [reason]\"\n")
            content.append("Example: \"Refer to cardiology for chest pain\"\n")
        } else {
            val pending = patientReferrals.filter { it.status == "pending" }
            val scheduled = patientReferrals.filter { it.status == "scheduled" }
            val completed = patientReferrals.filter { it.status == "completed" }

            if (pending.isNotEmpty()) {
                content.append("▸ ⏳ PENDING (${pending.size})\n")
                content.append("───────────────────────────────────\n")
                pending.forEachIndexed { i, ref ->
                    val urgencyIcon = when (ref.urgency) {
                        "stat" -> "🔴"
                        "urgent" -> "🟡"
                        else -> "🟢"
                    }
                    content.append("${i + 1}. $urgencyIcon ${ref.specialty.uppercase()}\n")
                    content.append("   Reason: ${ref.reason}\n")
                    content.append("   Created: ${ref.date}\n")
                }
                content.append("\n")
            }

            if (scheduled.isNotEmpty()) {
                content.append("▸ 📅 SCHEDULED (${scheduled.size})\n")
                content.append("───────────────────────────────────\n")
                scheduled.forEach { ref ->
                    content.append("• ${ref.specialty}: ${ref.reason}\n")
                }
                content.append("\n")
            }

            if (completed.isNotEmpty()) {
                content.append("▸ ✅ COMPLETED (${completed.size})\n")
                content.append("───────────────────────────────────\n")
                completed.forEach { ref ->
                    content.append("• ${ref.specialty}: ${ref.reason}\n")
                }
            }
        }

        content.append("\n───────────────────────────────────\n")
        content.append("Commands:\n")
        content.append("• \"Refer to [specialty] for [reason]\"\n")
        content.append("• \"Urgent referral to [specialty]\"\n")
        content.append("• \"Mark referral [#] scheduled\"\n")
        content.append("• \"Mark referral [#] complete\"")

        showDataOverlay("Referrals", content.toString())

        val pendingCount = patientReferrals.count { it.status == "pending" }
        if (pendingCount > 0) {
            speakFeedback("$pendingCount pending referrals")
        }
    }

    /**
     * Create a new referral
     */
    private fun createReferral(specialty: String, reason: String, urgency: String = "routine") {
        val matchedSpecialty = commonSpecialties.find { it.contains(specialty.lowercase()) }
            ?: specialty.lowercase().replaceFirstChar { it.uppercase() }

        val today = java.text.SimpleDateFormat("MM/dd/yyyy", java.util.Locale.US).format(java.util.Date())

        val referral = Referral(
            specialty = matchedSpecialty,
            reason = reason,
            urgency = urgency,
            status = "pending",
            date = today
        )

        patientReferrals.add(referral)

        val urgencyText = if (urgency != "routine") " ($urgency)" else ""
        speakFeedback("Referral to $matchedSpecialty created$urgencyText")
        showReferrals()
    }

    /**
     * Update referral status
     */
    private fun updateReferralStatus(index: Int, newStatus: String) {
        if (index in 1..patientReferrals.size) {
            val referral = patientReferrals[index - 1]
            patientReferrals[index - 1] = referral.copy(status = newStatus)
            speakFeedback("Referral to ${referral.specialty} marked as $newStatus")
            showReferrals()
        } else {
            speakFeedback("Invalid referral number")
        }
    }

    /**
     * Clear all referrals
     */
    private fun clearReferrals() {
        patientReferrals.clear()
        speakFeedback("All referrals cleared")
        showReferrals()
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // NOTE VERSIONING - Track changes to notes with version history
    // ═══════════════════════════════════════════════════════════════════════════

    private data class NoteVersion(
        val version: Int,
        val content: String,
        val timestamp: Long,
        val changeType: String, // "created", "edited", "section_update", "signed"
        val changeDescription: String
    )

    private val noteVersionHistory = mutableListOf<NoteVersion>()
    private var currentNoteVersion = 0

    /**
     * Save a new version of the note
     */
    private fun saveNoteVersion(content: String, changeType: String, description: String) {
        currentNoteVersion++
        val version = NoteVersion(
            version = currentNoteVersion,
            content = content,
            timestamp = System.currentTimeMillis(),
            changeType = changeType,
            changeDescription = description
        )
        noteVersionHistory.add(version)

        // Keep only last 20 versions to manage memory
        if (noteVersionHistory.size > 20) {
            noteVersionHistory.removeAt(0)
        }
    }

    /**
     * Get the current note version number
     */
    private fun getCurrentNoteVersion(): Int = currentNoteVersion

    /**
     * Show note version history
     */
    private fun showNoteVersionHistory() {
        if (noteVersionHistory.isEmpty()) {
            speakFeedback("No version history available")
            return
        }

        val content = StringBuilder()
        content.append("═══════════════════════════════════\n")
        content.append("📜 NOTE VERSION HISTORY\n")
        content.append("═══════════════════════════════════\n\n")
        content.append("Total versions: ${noteVersionHistory.size}\n")
        content.append("Current version: v$currentNoteVersion\n\n")

        noteVersionHistory.reversed().take(10).forEachIndexed { index, version ->
            val timeAgo = getTimeAgo(version.timestamp)
            val icon = when (version.changeType) {
                "created" -> "🆕"
                "edited" -> "✏️"
                "section_update" -> "📝"
                "signed" -> "✅"
                "restored" -> "🔄"
                else -> "📋"
            }
            content.append("$icon v${version.version} - $timeAgo\n")
            content.append("   ${version.changeDescription}\n")
            if (index < noteVersionHistory.size - 1) content.append("\n")
        }

        content.append("\n───────────────────────────────────\n")
        content.append("Commands:\n")
        content.append("• \"Restore version [#]\" - Restore to version\n")
        content.append("• \"Compare versions\" - Show diff\n")
        content.append("• \"Clear history\" - Clear version history")

        showDataOverlay("Version History", content.toString())
        speakFeedback("${noteVersionHistory.size} versions in history")
    }

    /**
     * Restore a previous version of the note
     */
    private fun restoreNoteVersion(versionNumber: Int) {
        val version = noteVersionHistory.find { it.version == versionNumber }
        if (version == null) {
            speakFeedback("Version $versionNumber not found")
            return
        }

        // Save current state before restoring
        val currentContent = lastGeneratedNote?.toString() ?: ""
        saveNoteVersion(currentContent, "restored", "Before restoring to v$versionNumber")

        // Restore the old version
        try {
            lastGeneratedNote = org.json.JSONObject().apply {
                put("content", version.content)
                put("restored_from", versionNumber)
                put("restored_at", System.currentTimeMillis())
            }

            // Save the restoration as a new version
            saveNoteVersion(version.content, "restored", "Restored from v$versionNumber")

            speakFeedback("Restored to version $versionNumber")
            showNoteWithSaveOption("Restored Note (v$versionNumber)", version.content)
        } catch (e: Exception) {
            speakFeedback("Error restoring version")
        }
    }

    /**
     * Compare two versions of the note
     */
    private fun compareNoteVersions() {
        if (noteVersionHistory.size < 2) {
            speakFeedback("Need at least 2 versions to compare")
            return
        }

        val current = noteVersionHistory.last()
        val previous = noteVersionHistory[noteVersionHistory.size - 2]

        val currentLines = current.content.lines()
        val previousLines = previous.content.lines()

        val content = StringBuilder()
        content.append("═══════════════════════════════════\n")
        content.append("⚖️ VERSION COMPARISON\n")
        content.append("═══════════════════════════════════\n\n")
        content.append("Comparing v${previous.version} → v${current.version}\n\n")

        // Simple diff - show added and removed lines
        val added = currentLines.filter { it !in previousLines }
        val removed = previousLines.filter { it !in currentLines }

        if (added.isEmpty() && removed.isEmpty()) {
            content.append("No differences found.\n")
        } else {
            if (removed.isNotEmpty()) {
                content.append("▸ REMOVED (${removed.size} lines)\n")
                content.append("───────────────────────────────────\n")
                removed.take(5).forEach { line ->
                    content.append("- ${line.take(50)}...\n")
                }
                if (removed.size > 5) content.append("  ...and ${removed.size - 5} more\n")
                content.append("\n")
            }

            if (added.isNotEmpty()) {
                content.append("▸ ADDED (${added.size} lines)\n")
                content.append("───────────────────────────────────\n")
                added.take(5).forEach { line ->
                    content.append("+ ${line.take(50)}...\n")
                }
                if (added.size > 5) content.append("  ...and ${added.size - 5} more\n")
            }
        }

        content.append("\n───────────────────────────────────\n")
        content.append("v${previous.version}: ${previous.changeDescription}\n")
        content.append("v${current.version}: ${current.changeDescription}")

        showDataOverlay("Version Diff", content.toString())
    }

    /**
     * Clear version history
     */
    private fun clearNoteVersionHistory() {
        noteVersionHistory.clear()
        currentNoteVersion = 0
        speakFeedback("Version history cleared")
    }

    /**
     * Initialize version tracking for a new note
     */
    private fun initNoteVersioning(noteContent: String) {
        noteVersionHistory.clear()
        currentNoteVersion = 0
        saveNoteVersion(noteContent, "created", "Initial note created")
    }

    /**
     * Track section edits
     */
    private fun trackNoteEdit(section: String, action: String) {
        val content = lastGeneratedNote?.optString("content", "") ?: ""
        saveNoteVersion(content, "section_update", "$action in $section section")
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // DATA ENCRYPTION AT REST - Secure local storage of PHI
    // ═══════════════════════════════════════════════════════════════════════════

    private var encryptedPrefs: android.content.SharedPreferences? = null
    private var isEncryptionEnabled = false

    /**
     * Initialize encrypted storage using Android Keystore
     */
    private fun initializeEncryptedStorage() {
        try {
            // Use AndroidX Security library for EncryptedSharedPreferences
            val masterKey = androidx.security.crypto.MasterKey.Builder(this)
                .setKeyScheme(androidx.security.crypto.MasterKey.KeyScheme.AES256_GCM)
                .build()

            encryptedPrefs = androidx.security.crypto.EncryptedSharedPreferences.create(
                this,
                "mdx_vision_encrypted_prefs",
                masterKey,
                androidx.security.crypto.EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
                androidx.security.crypto.EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
            )

            isEncryptionEnabled = true
            android.util.Log.d("MDxVision", "Encrypted storage initialized successfully")
        } catch (e: Exception) {
            android.util.Log.e("MDxVision", "Failed to initialize encrypted storage: ${e.message}")
            // Fall back to regular SharedPreferences
            encryptedPrefs = getSharedPreferences("mdx_vision_prefs", MODE_PRIVATE)
            isEncryptionEnabled = false
        }
    }

    /**
     * Securely store sensitive patient data
     */
    private fun secureStorePatientData(patientId: String, data: String) {
        val prefs = encryptedPrefs ?: return
        prefs.edit().apply {
            putString("patient_$patientId", data)
            putLong("patient_${patientId}_timestamp", System.currentTimeMillis())
            apply()
        }
    }

    /**
     * Securely retrieve patient data
     */
    private fun secureRetrievePatientData(patientId: String): String? {
        val prefs = encryptedPrefs ?: return null
        return prefs.getString("patient_$patientId", null)
    }

    /**
     * Securely store notes
     */
    private fun secureStoreNote(noteId: String, noteContent: String) {
        val prefs = encryptedPrefs ?: return
        prefs.edit().apply {
            putString("note_$noteId", noteContent)
            putLong("note_${noteId}_timestamp", System.currentTimeMillis())
            apply()
        }
    }

    /**
     * Securely retrieve notes
     */
    private fun secureRetrieveNote(noteId: String): String? {
        val prefs = encryptedPrefs ?: return null
        return prefs.getString("note_$noteId", null)
    }

    /**
     * Securely store draft notes (offline mode)
     */
    private fun secureStoreDraft(draftId: String, content: String) {
        val prefs = encryptedPrefs ?: return
        val drafts = prefs.getStringSet("draft_ids", mutableSetOf())?.toMutableSet() ?: mutableSetOf()
        drafts.add(draftId)
        prefs.edit().apply {
            putString("draft_$draftId", content)
            putStringSet("draft_ids", drafts)
            apply()
        }
    }

    /**
     * Get all draft IDs
     */
    private fun getSecureDraftIds(): Set<String> {
        val prefs = encryptedPrefs ?: return emptySet()
        return prefs.getStringSet("draft_ids", emptySet()) ?: emptySet()
    }

    /**
     * Securely store user credentials/tokens
     */
    private fun secureStoreCredential(key: String, value: String) {
        val prefs = encryptedPrefs ?: return
        prefs.edit().putString("credential_$key", value).apply()
    }

    /**
     * Securely retrieve credentials
     */
    private fun secureRetrieveCredential(key: String): String? {
        val prefs = encryptedPrefs ?: return null
        return prefs.getString("credential_$key", null)
    }

    /**
     * Securely wipe all stored data (for logout or device wipe)
     */
    private fun secureWipeAllData() {
        val prefs = encryptedPrefs ?: return
        prefs.edit().clear().apply()
        speakFeedback("All encrypted data securely wiped")
    }

    /**
     * Check encryption status
     */
    private fun showEncryptionStatus() {
        val content = StringBuilder()
        content.append("═══════════════════════════════════\n")
        content.append("🔐 DATA ENCRYPTION STATUS\n")
        content.append("═══════════════════════════════════\n\n")

        if (isEncryptionEnabled) {
            content.append("✅ Encryption: ENABLED\n")
            content.append("🔑 Algorithm: AES-256-GCM\n")
            content.append("🔒 Key Storage: Android Keystore\n")
            content.append("📱 Key Protection: Hardware-backed (if available)\n\n")

            content.append("▸ PROTECTED DATA\n")
            content.append("───────────────────────────────────\n")
            content.append("• Patient demographics\n")
            content.append("• Clinical notes\n")
            content.append("• Draft notes\n")
            content.append("• User credentials\n")
            content.append("• Session tokens\n")
            content.append("• Audit logs\n\n")

            val prefs = encryptedPrefs
            if (prefs != null) {
                val patientCount = prefs.all.keys.count { it.startsWith("patient_") && !it.contains("timestamp") }
                val noteCount = prefs.all.keys.count { it.startsWith("note_") && !it.contains("timestamp") }
                val draftCount = getSecureDraftIds().size

                content.append("▸ STORED ITEMS\n")
                content.append("───────────────────────────────────\n")
                content.append("Cached patients: $patientCount\n")
                content.append("Saved notes: $noteCount\n")
                content.append("Draft notes: $draftCount\n")
            }
        } else {
            content.append("⚠️ Encryption: DISABLED\n")
            content.append("Using standard SharedPreferences\n\n")
            content.append("Reason: Device may not support\n")
            content.append("hardware-backed encryption\n")
        }

        content.append("\n───────────────────────────────────\n")
        content.append("HIPAA Compliant: ${if (isEncryptionEnabled) "YES" else "PARTIAL"}")

        showDataOverlay("Encryption Status", content.toString())
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // SPECIALTY TEMPLATES - Voice command helpers
    // ═══════════════════════════════════════════════════════════════════════════

    /**
     * Show list of available specialty templates
     */
    private fun showSpecialtyTemplates() {
        val content = StringBuilder()
        content.append("🏥 SPECIALTY TEMPLATES\n")
        content.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n")

        // Group templates by category
        val categories = mapOf(
            "Cardiology" to listOf("cardiology_chest_pain", "cardiology_heart_failure", "cardiology_afib"),
            "Orthopedics" to listOf("ortho_joint_pain", "ortho_fracture"),
            "Neurology" to listOf("neuro_headache", "neuro_stroke"),
            "GI" to listOf("gi_abdominal_pain", "gi_gerd"),
            "Pulmonology" to listOf("pulm_copd", "pulm_asthma"),
            "Psychiatry" to listOf("psych_depression", "psych_anxiety"),
            "Emergency" to listOf("ed_trauma", "ed_sepsis")
        )

        categories.forEach { (category, templateKeys) ->
            content.append("▸ $category\n")
            templateKeys.forEach { key ->
                val template = builtInTemplates[key]
                if (template != null) {
                    val shortName = template.name.substringAfter(" - ")
                    content.append("   • $shortName\n")
                }
            }
            content.append("\n")
        }

        content.append("───────────────────────────────────\n")
        content.append("Say: \"Use cardiology chest pain template\"\n")
        content.append("     \"Apply neuro headache template\"")

        showDataOverlay("Specialty Templates", content.toString())
        speakFeedback("14 specialty templates available. Say use followed by template name.")
    }

    /**
     * Extract template key from voice command
     */
    private fun extractSpecialtyTemplateKey(command: String): String? {
        val lower = command.lowercase()

        // Map spoken phrases to template keys
        val mappings = mapOf(
            // Cardiology
            "cardiology chest pain" to "cardiology_chest_pain",
            "chest pain" to "cardiology_chest_pain",
            "cardiology heart failure" to "cardiology_heart_failure",
            "heart failure" to "cardiology_heart_failure",
            "chf" to "cardiology_heart_failure",
            "cardiology afib" to "cardiology_afib",
            "afib" to "cardiology_afib",
            "atrial fibrillation" to "cardiology_afib",
            // Orthopedics
            "ortho joint pain" to "ortho_joint_pain",
            "joint pain" to "ortho_joint_pain",
            "ortho fracture" to "ortho_fracture",
            "fracture" to "ortho_fracture",
            // Neurology
            "neuro headache" to "neuro_headache",
            "headache" to "neuro_headache",
            "migraine" to "neuro_headache",
            "neuro stroke" to "neuro_stroke",
            "stroke" to "neuro_stroke",
            "cva" to "neuro_stroke",
            // GI
            "gi abdominal pain" to "gi_abdominal_pain",
            "abdominal pain" to "gi_abdominal_pain",
            "belly pain" to "gi_abdominal_pain",
            "gi gerd" to "gi_gerd",
            "gerd" to "gi_gerd",
            "acid reflux" to "gi_gerd",
            // Pulmonology
            "pulm copd" to "pulm_copd",
            "copd" to "pulm_copd",
            "pulm asthma" to "pulm_asthma",
            "asthma" to "pulm_asthma",
            // Psychiatry
            "psych depression" to "psych_depression",
            "depression" to "psych_depression",
            "psych anxiety" to "psych_anxiety",
            "anxiety" to "psych_anxiety",
            // Emergency
            "ed trauma" to "ed_trauma",
            "trauma" to "ed_trauma",
            "ed sepsis" to "ed_sepsis",
            "sepsis" to "ed_sepsis"
        )

        // Find matching template
        for ((phrase, key) in mappings) {
            if (lower.contains(phrase)) {
                return key
            }
        }
        return null
    }

    /**
     * Apply a specialty template to the current note
     */
    private fun applySpecialtyTemplate(templateKey: String) {
        val template = builtInTemplates[templateKey]
        if (template == null) {
            speakFeedback("Template not found")
            return
        }

        // Apply template - substitute patient data
        var content = template.content

        currentPatientData?.let { patient ->
            content = content.replace("{{patient_name}}", patient.optString("name", "Patient"))
            content = content.replace("{{age}}", patient.optString("age", ""))
            content = content.replace("{{gender}}", patient.optString("gender", ""))
            content = content.replace("{{mrn}}", patient.optString("mrn", ""))
            content = content.replace("{{dob}}", patient.optString("dob", ""))
            content = content.replace("{{date}}", java.text.SimpleDateFormat("yyyy-MM-dd", java.util.Locale.US).format(java.util.Date()))
        }

        // Store as current note
        val noteJson = org.json.JSONObject()
        noteJson.put("content", content as Any)
        noteJson.put("note_type", template.noteType as Any)
        noteJson.put("template", templateKey as Any)
        noteJson.put("generated_at", System.currentTimeMillis() as Any)
        lastGeneratedNote = noteJson
        currentNoteType = template.noteType

        // Initialize version tracking
        initNoteVersioning(content)

        // Display the template
        val displayContent = StringBuilder()
        displayContent.append("📋 ${template.name}\n")
        displayContent.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n")
        displayContent.append(content.toString())

        showDataOverlay("Specialty Template Applied", displayContent.toString())
        speakFeedback("${template.category} template applied. You can edit sections by voice.")
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
            // SBAR Handoff report commands
            lower.contains("handoff report") || lower.contains("hand off report") || lower.contains("sbar report") ||
            lower.contains("sbar") || lower.contains("shift report") || lower.contains("handoff") -> {
                // Generate visual SBAR handoff report
                generateHandoffReport()
            }
            lower.contains("read handoff") || lower.contains("speak handoff") || lower.contains("tell me handoff") ||
            lower.contains("verbal handoff") || lower.contains("give handoff") -> {
                // Speak SBAR handoff report aloud
                speakHandoffReport()
            }
            // Discharge summary commands
            lower.contains("discharge summary") || lower.contains("discharge instructions") ||
            lower.contains("discharge") || lower.contains("patient instructions") -> {
                // Generate visual discharge summary
                generateDischargeSummary()
            }
            lower.contains("read discharge") || lower.contains("speak discharge") || lower.contains("explain discharge") ||
            lower.contains("tell patient") || lower.contains("patient education") -> {
                // Speak discharge instructions aloud
                speakDischargeInstructions()
            }
            // Procedure Checklist commands
            lower.contains("show checklists") || lower.contains("procedure checklists") || lower.contains("safety checklists") -> {
                showProcedureChecklists()
            }
            lower.contains("start") && lower.contains("checklist") -> {
                val checklistName = lower.replace("start", "").replace("checklist", "").trim()
                startProcedureChecklist(checklistName)
            }
            lower.contains("check all") -> {
                checkAllChecklistItems()
            }
            lower.contains("check ") && lower.matches(Regex(".*check\\s+\\d+.*")) -> {
                val num = lower.replace(Regex(".*check\\s+(\\d+).*"), "$1").toIntOrNull() ?: 0
                checkChecklistItem(num)
            }
            lower.contains("read checklist") || lower.contains("speak checklist") -> {
                readChecklist()
            }
            // Clinical Reminders commands
            lower.contains("clinical reminders") || lower.contains("reminders") || lower.contains("preventive care") ||
            lower.contains("care reminders") || lower.contains("health reminders") -> {
                generateClinicalReminders()
            }
            // Medication Reconciliation commands
            lower.contains("med reconciliation") || lower.contains("medication reconciliation") ||
            lower.contains("reconcile meds") || lower.contains("med rec") -> {
                startMedReconciliation()
            }
            lower.contains("add home med") -> {
                val med = lower.replace("add home med", "").replace("add home medication", "").trim()
                if (med.isNotEmpty()) addHomeMedication(med)
            }
            lower.contains("remove home med") -> {
                val num = lower.replace(Regex(".*remove home med\\w*\\s*(\\d+).*"), "$1").toIntOrNull() ?: 0
                if (num > 0) removeHomeMedication(num)
            }
            lower.contains("compare meds") || lower.contains("compare medications") || lower.contains("med comparison") -> {
                compareMedications()
            }
            lower.contains("clear home meds") || lower.contains("clear home medications") -> {
                clearHomeMedications()
            }
            // Referral Tracking commands
            lower.contains("show referrals") || lower.contains("referrals") || lower.contains("pending referrals") -> {
                showReferrals()
            }
            lower.contains("urgent referral to") || lower.contains("stat referral to") -> {
                val urgency = if (lower.contains("stat")) "stat" else "urgent"
                val afterTo = lower.substringAfter("referral to").trim()
                val parts = afterTo.split(" for ", limit = 2)
                val specialty = parts[0].trim()
                val reason = if (parts.size > 1) parts[1].trim() else "evaluation"
                createReferral(specialty, reason, urgency)
            }
            lower.contains("refer to") -> {
                val afterTo = lower.substringAfter("refer to").trim()
                val parts = afterTo.split(" for ", limit = 2)
                val specialty = parts[0].trim()
                val reason = if (parts.size > 1) parts[1].trim() else "evaluation"
                createReferral(specialty, reason)
            }
            lower.contains("mark referral") && lower.contains("scheduled") -> {
                val num = lower.replace(Regex(".*referral\\s*(\\d+).*"), "$1").toIntOrNull() ?: 0
                if (num > 0) updateReferralStatus(num, "scheduled")
            }
            lower.contains("mark referral") && (lower.contains("complete") || lower.contains("completed")) -> {
                val num = lower.replace(Regex(".*referral\\s*(\\d+).*"), "$1").toIntOrNull() ?: 0
                if (num > 0) updateReferralStatus(num, "completed")
            }
            lower.contains("clear referrals") -> {
                clearReferrals()
            }
            // ═══════════════════════════════════════════════════════════════════════════
            // SPECIALTY TEMPLATES - Feature #56
            // ═══════════════════════════════════════════════════════════════════════════
            lower.contains("list specialty templates") || lower.contains("specialty templates") ||
            lower.contains("show specialty templates") -> {
                showSpecialtyTemplates()
            }
            lower.contains("use template") || lower.contains("apply template") -> {
                // Extract template name: "use cardiology chest pain template"
                val templateKey = extractSpecialtyTemplateKey(lower)
                if (templateKey != null) {
                    applySpecialtyTemplate(templateKey)
                } else {
                    showSpecialtyTemplates()
                }
            }
            // ═══════════════════════════════════════════════════════════════════════════
            // NOTE VERSIONING - Feature #57
            // ═══════════════════════════════════════════════════════════════════════════
            lower.contains("version history") || lower.contains("note versions") || lower.contains("show versions") -> {
                showNoteVersionHistory()
            }
            lower.contains("restore version") -> {
                val num = lower.replace(Regex(".*version\\s*(\\d+).*"), "$1").toIntOrNull() ?: 0
                if (num > 0) restoreNoteVersion(num)
            }
            lower.contains("compare versions") || lower.contains("diff versions") || lower.contains("version diff") -> {
                compareNoteVersions()
            }
            lower.contains("clear version history") || lower.contains("clear versions") -> {
                clearNoteVersionHistory()
            }
            // ═══════════════════════════════════════════════════════════════════════════
            // DATA ENCRYPTION - Feature #60
            // ═══════════════════════════════════════════════════════════════════════════
            lower.contains("encryption status") || lower.contains("security status") -> {
                showEncryptionStatus()
            }
            lower.contains("wipe data") || lower.contains("secure wipe") || lower.contains("erase data") -> {
                secureWipeAllData()
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
            // ═══════════════════════════════════════════════════════════════════════════
            // VOICE ORDERS - Order commands
            // ═══════════════════════════════════════════════════════════════════════════

            // Show orders: "show orders", "list orders", "pending orders"
            lower.contains("show order") || lower.contains("list order") || lower.contains("pending order") ||
            lower.contains("what are the order") -> {
                showOrderQueue()
            }
            // List order sets: "list order sets", "show order sets", "available order sets"
            lower.contains("order set") && (lower.contains("list") || lower.contains("show") || lower.contains("available") || lower.contains("what")) -> {
                showOrderSetList()
            }
            // Preview order set: "what's in chest pain", "preview sepsis bundle", "show me chest pain workup"
            (lower.contains("what's in") || lower.contains("whats in") || lower.contains("preview") ||
             lower.contains("show me") && lower.contains("workup")) -> {
                val setName = lower.replace(Regex("(what's in|whats in|preview|show me|workup)"), "").trim()
                if (setName.isNotEmpty()) {
                    previewOrderSet(setName)
                } else {
                    speakFeedback("Say what's in followed by the order set name, like what's in chest pain.")
                }
            }
            // Cancel order: "cancel order", "remove order", "remove last order"
            lower.contains("cancel order") || lower.contains("remove order") ||
            lower.contains("remove last order") || lower.contains("delete order") -> {
                cancelLastOrder()
            }
            // Clear all orders: "clear all orders", "delete all orders"
            lower.contains("clear all order") || lower.contains("delete all order") -> {
                clearAllOrders()
            }
            // Confirmation: "yes", "confirm" (when order pending)
            (lower == "yes" || lower == "confirm" || lower.contains("confirm order") ||
             lower.contains("place order") || lower.contains("go ahead")) && pendingConfirmationOrder != null -> {
                confirmPendingOrder()
            }
            // Rejection: "no", "cancel" (when order pending)
            (lower == "no" || lower == "reject" || lower.contains("don't order") ||
             lower.contains("do not order")) && pendingConfirmationOrder != null -> {
                rejectPendingOrder()
            }
            // Prescribe medication: "prescribe amoxicillin 500mg three times daily for 10 days"
            lower.startsWith("prescribe ") -> {
                val medText = lower.substringAfter("prescribe ").trim()
                processMedicationOrder(medText)
            }
            // Order command - determine type based on content (check order sets first)
            lower.startsWith("order ") -> {
                val orderText = lower.substringAfter("order ").trim()
                val orderSet = findOrderSet(orderText)
                when {
                    orderSet != null -> processOrderSet(orderSet)
                    isLabOrder(orderText) -> processLabOrder(orderText)
                    isImagingOrder(orderText) -> processImagingOrder(orderText)
                    isMedicationOrder(orderText) -> processMedicationOrder(orderText)
                    else -> speakFeedback("Order not recognized. Try: order CBC, order chest pain workup, or prescribe amoxicillin.")
                }
            }
            // ═══════════════════════════════════════════════════════════════════════════
            // VOICE VITALS ENTRY - Capture vitals by voice
            // ═══════════════════════════════════════════════════════════════════════════

            // Show captured vitals: "show vitals captured", "captured vitals", "my vitals"
            lower.contains("captured vital") || lower.contains("my vital") ||
            lower.contains("show captured") || lower.contains("vitals captured") -> {
                showCapturedVitals()
            }
            // Clear captured vitals: "clear vitals", "clear captured vitals", "reset vitals"
            lower.contains("clear vital") || lower.contains("reset vital") ||
            lower.contains("delete vital") -> {
                clearCapturedVitals()
            }
            // Add vitals to note: "add vitals to note", "insert vitals", "vitals to note"
            lower.contains("add vital") && lower.contains("note") ||
            lower.contains("insert vital") || lower.contains("vitals to note") -> {
                addVitalsToNote()
            }
            // Vital history: "vital history", "show vital history", "past vitals", "vitals over time"
            lower.contains("vital history") || lower.contains("vitals history") ||
            lower.contains("past vital") || lower.contains("vitals over time") ||
            lower.contains("previous vital") || lower.contains("historical vital") ||
            (lower.contains("history") && lower.contains("vital")) -> {
                fetchVitalHistory()
            }
            // Vital entry: "BP 120 over 80", "pulse 72", "temp 98.6", etc.
            isVitalEntry(lower) -> {
                processVitalEntry(lower)
            }
            // ═══════════════════════════════════════════════════════════════════════════
            // ENCOUNTER TIMER - Timer commands
            // ═══════════════════════════════════════════════════════════════════════════

            // Start timer: "start timer", "begin timer", "start encounter"
            lower.contains("start timer") || lower.contains("begin timer") ||
            lower.contains("start encounter") || lower.contains("start the timer") -> {
                startEncounterTimer()
            }
            // Stop timer: "stop timer", "end timer", "stop encounter"
            lower.contains("stop timer") || lower.contains("end timer") ||
            lower.contains("stop encounter") || lower.contains("end encounter") -> {
                stopEncounterTimer()
            }
            // Check time: "how long", "what's the time", "check timer", "elapsed time"
            lower.contains("how long") || lower.contains("what time") || lower.contains("check timer") ||
            lower.contains("elapsed time") || lower.contains("time elapsed") ||
            lower.contains("how much time") || lower.contains("time spent") -> {
                reportEncounterTime()
            }
            // Reset timer: "reset timer", "restart timer"
            lower.contains("reset timer") || lower.contains("restart timer") -> {
                resetEncounterTimer()
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
            // Voice Template Commands
            lower.contains("use") && lower.contains("template") -> {
                // "Use diabetes template", "Use URI template", "Use my headache template"
                val templateName = lower
                    .replace("use", "")
                    .replace("template", "")
                    .replace("the", "")
                    .replace("my", "")
                    .trim()
                if (templateName.isNotEmpty()) {
                    val templateKey = findTemplateByName(templateName)
                    if (templateKey != null) {
                        applyTemplate(templateKey)
                    } else {
                        Toast.makeText(this, "Template not found: $templateName", Toast.LENGTH_SHORT).show()
                        speakFeedback("Template not found. Say list templates to see available options.")
                    }
                } else {
                    showTemplateListOverlay()
                }
            }
            lower.contains("list template") || lower.contains("show template") || lower.contains("available template") ||
            lower == "templates" || lower.contains("what template") -> {
                // List available templates
                showTemplateListOverlay()
            }
            lower.contains("my template") || lower.contains("custom template") || lower.contains("saved template") -> {
                // Show user templates
                val userTemplates = getUserTemplates()
                if (userTemplates.isEmpty()) {
                    Toast.makeText(this, "No custom templates saved", Toast.LENGTH_SHORT).show()
                    speakFeedback("No custom templates. Say save as template to create one.")
                } else {
                    showTemplateListOverlay()
                }
            }
            lower.contains("save as template") || lower.contains("save template") -> {
                // "Save as template headache", "Save template diabetes followup"
                val templateName = lower
                    .replace("save as template", "")
                    .replace("save template", "")
                    .trim()
                if (templateName.isNotEmpty()) {
                    saveAsTemplate(templateName)
                } else {
                    Toast.makeText(this, "Say 'save as template [name]'", Toast.LENGTH_SHORT).show()
                    speakFeedback("Say save as template followed by a name")
                }
            }
            lower.contains("delete template") || lower.contains("remove template") -> {
                // "Delete template headache"
                val templateName = lower
                    .replace("delete template", "")
                    .replace("remove template", "")
                    .trim()
                if (templateName.isNotEmpty()) {
                    deleteUserTemplate(templateName)
                } else {
                    Toast.makeText(this, "Say 'delete template [name]'", Toast.LENGTH_SHORT).show()
                }
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
            // ═══════════════════════════════════════════════════════════════════════════
            // MEDICAL CALCULATOR - Voice-activated clinical calculations
            // ═══════════════════════════════════════════════════════════════════════════

            // Calculator list: "calculators", "show calculators", "medical calculators"
            lower.contains("calculator") || lower.contains("calculations") -> {
                if (lower.contains("bmi") || lower.contains("gfr") || lower.contains("calcium") ||
                    lower.contains("anion") || lower.contains("a1c") || lower.contains("map") ||
                    lower.contains("creatinine") || lower.contains("chads")) {
                    processCalculatorCommand(lower)
                } else {
                    showCalculatorList()
                }
            }
            // Calculate BMI: "calculate BMI", "what's the BMI", "BMI"
            lower.contains("calculate bmi") || lower.contains("what's the bmi") ||
            lower.contains("whats the bmi") || lower.contains("body mass index") ||
            (lower.contains("bmi") && !lower.contains("calculator")) -> {
                calculateAndShowBMI()
            }
            // Calculate eGFR: "calculate GFR", "what's the GFR", "kidney function"
            lower.contains("calculate gfr") || lower.contains("egfr") ||
            lower.contains("what's the gfr") || lower.contains("whats the gfr") ||
            lower.contains("kidney function") || lower.contains("glomerular") -> {
                calculateAndShowEGFR()
            }
            // Corrected Calcium: "corrected calcium", "calcium corrected"
            lower.contains("corrected calcium") || lower.contains("correct calcium") ||
            lower.contains("calcium correct") -> {
                calculateAndShowCorrectedCalcium()
            }
            // Anion Gap: "anion gap", "calculate anion"
            lower.contains("anion gap") || lower.contains("calculate anion") -> {
                calculateAndShowAnionGap()
            }
            // A1c conversions: "A1c to glucose", "convert A1c"
            lower.contains("a1c to glucose") || lower.contains("convert a1c") ||
            lower.contains("a1c conversion") -> {
                calculateAndShowA1cToGlucose()
            }
            lower.contains("glucose to a1c") -> {
                calculateAndShowGlucoseToA1c()
            }
            // MAP: "calculate MAP", "mean arterial pressure"
            lower.contains("calculate map") || lower.contains("mean arterial") ||
            (lower == "map" || lower.contains("what's the map") || lower.contains("whats the map")) -> {
                calculateAndShowMAP()
            }
            // Creatinine Clearance: "creatinine clearance", "CrCl", "cockcroft"
            lower.contains("creatinine clearance") || lower.contains("crcl") ||
            lower.contains("cockcroft") || lower.contains("calculate clearance") -> {
                calculateAndShowCrCl()
            }
            // CHADS-VASc: "CHADS VASc", "stroke risk"
            lower.contains("chads") || lower.contains("stroke risk") -> {
                calculateAndShowCHADSVASc()
            }

            // ═══════════════════════════════════════════════════════════════════════════
            // CUSTOM VOICE COMMANDS - User-defined macros and aliases
            // ═══════════════════════════════════════════════════════════════════════════

            // Create command: "create command [name] that does [actions]"
            lower.contains("create command") || lower.contains("make command") ||
            lower.contains("new command") || lower.contains("add command") ||
            lower.contains("create macro") || lower.contains("make macro") ||
            lower.contains("new macro") || lower.contains("add macro") ||
            lower.startsWith("when i say") || lower.startsWith("when I say") ||
            lower.startsWith("teach ") -> {
                if (!parseAndCreateCommand(transcript)) {
                    speakFeedback("Could not create command. Try: create command morning rounds that does show vitals then show meds")
                }
            }
            // Show custom commands: "my commands", "list commands", "show commands"
            lower.contains("my command") || lower.contains("list command") ||
            lower.contains("show command") || lower.contains("custom command") ||
            lower.contains("my macro") || lower.contains("list macro") -> {
                showCustomCommands()
            }
            // Delete command: "delete command [name]", "remove command [name]"
            lower.contains("delete command") || lower.contains("remove command") ||
            lower.contains("delete macro") || lower.contains("remove macro") -> {
                val commandName = lower
                    .replace("delete command", "")
                    .replace("remove command", "")
                    .replace("delete macro", "")
                    .replace("remove macro", "")
                    .trim()
                if (commandName.isNotEmpty()) {
                    deleteCustomCommand(commandName)
                } else {
                    speakFeedback("Say delete command followed by the command name")
                }
            }

            lower.contains("clear") || lower.contains("reset") -> {
                // Clear current patient data (not cache)
                currentPatientData = null
                hideDataOverlay()
                transcriptText.text = "Patient data cleared"
            }
            else -> {
                // Check for custom commands before falling through
                val customCommand = findCustomCommand(lower)
                if (customCommand != null) {
                    executeCustomCommand(customCommand)
                } else {
                    // Display transcribed text
                    transcriptText.text = "\"$transcript\""
                    Log.d(TAG, "Voice command: $transcript")
                }
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
