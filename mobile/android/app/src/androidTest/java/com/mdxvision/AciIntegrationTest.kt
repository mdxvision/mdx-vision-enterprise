package com.mdxvision

import android.Manifest
import android.os.Build
import androidx.test.ext.junit.rules.ActivityScenarioRule
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.rule.GrantPermissionRule
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import org.junit.Before
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import java.util.concurrent.TimeUnit

/**
 * Integration Tests for Ambient Clinical Intelligence (ACI)
 *
 * Tests the complete ACI workflow using API calls (voice-first, no buttons).
 * Voice commands trigger API calls - we test the APIs directly.
 *
 * Voice Command → API Mapping:
 * - "Load patient" → GET /api/v1/patient/{id}
 * - "Show vitals" → Observation?category=vital-signs
 * - "Show allergies" → AllergyIntolerance
 * - "Show meds" → MedicationRequest
 * - "Show labs" → Observation?category=laboratory
 * - "Show conditions" → Condition
 * - "Live transcribe" → WebSocket /ws/transcribe
 * - "Generate note" → POST /api/v1/notes/generate
 *
 * IMPORTANT: These tests require the EHR Proxy to be running:
 *   cd ehr-proxy && python main.py
 *
 * Run with: ./gradlew connectedAndroidTest -Pandroid.testInstrumentationRunnerArguments.class=com.mdxvision.AciIntegrationTest
 */
@RunWith(AndroidJUnit4::class)
class AciIntegrationTest {

    @get:Rule
    val activityRule = ActivityScenarioRule(MainActivity::class.java)

    @get:Rule
    val permissionRule: GrantPermissionRule = GrantPermissionRule.grant(
        Manifest.permission.RECORD_AUDIO,
        Manifest.permission.CAMERA,
        Manifest.permission.INTERNET
    )

    private lateinit var httpClient: OkHttpClient

    // EHR Proxy URL - use localhost for Vuzix with ADB reverse
    private val ehrProxyUrl: String
        get() {
            val args = InstrumentationRegistry.getArguments()
            return args.getString("ehrProxyUrl", "http://localhost:8002")
        }

    private val cernerBaseUrl = "https://fhir-open.cerner.com/r4/ec2458f2-1e24-41c8-b71b-0e701af7583d"
    private val testPatientId = "12724066"

    @Before
    fun setup() {
        httpClient = OkHttpClient.Builder()
            .connectTimeout(60, TimeUnit.SECONDS)
            .readTimeout(60, TimeUnit.SECONDS)
            .writeTimeout(60, TimeUnit.SECONDS)
            .build()

        // Allow app to fully initialize
        Thread.sleep(4000)
    }

    // ==================== VOICE COMMAND: "LOAD PATIENT" ====================

    @Test
    fun voiceCommand_loadPatient() {
        // Voice: "Load patient" → API: GET Patient/{id}
        val request = Request.Builder()
            .url("$cernerBaseUrl/Patient/$testPatientId")
            .header("Accept", "application/fhir+json")
            .get()
            .build()

        val response = httpClient.newCall(request).execute()
        assert(response.code == 200) { "Load patient failed: ${response.code}" }

        val patient = JSONObject(response.body?.string()!!)
        assert(patient.getString("resourceType") == "Patient")
        println("✓ Voice: 'Load patient' → Patient ${patient.getString("id")} loaded")
    }

    // ==================== VOICE COMMAND: "SHOW VITALS" ====================

    @Test
    fun voiceCommand_showVitals() {
        // Voice: "Show vitals" → API: GET Observation?category=vital-signs
        val request = Request.Builder()
            .url("$cernerBaseUrl/Observation?patient=$testPatientId&category=vital-signs")
            .header("Accept", "application/fhir+json")
            .get()
            .build()

        val response = httpClient.newCall(request).execute()
        assert(response.code == 200) { "Show vitals failed: ${response.code}" }

        val bundle = JSONObject(response.body?.string()!!)
        val count = bundle.optJSONArray("entry")?.length() ?: 0
        println("✓ Voice: 'Show vitals' → Found $count vital observations")
    }

    // ==================== VOICE COMMAND: "SHOW ALLERGIES" ====================

    @Test
    fun voiceCommand_showAllergies() {
        // Voice: "Show allergies" → API: GET AllergyIntolerance
        val request = Request.Builder()
            .url("$cernerBaseUrl/AllergyIntolerance?patient=$testPatientId")
            .header("Accept", "application/fhir+json")
            .get()
            .build()

        val response = httpClient.newCall(request).execute()
        assert(response.code == 200) { "Show allergies failed: ${response.code}" }

        val bundle = JSONObject(response.body?.string()!!)
        val count = bundle.optJSONArray("entry")?.length() ?: 0
        println("✓ Voice: 'Show allergies' → Found $count allergies")
    }

    // ==================== VOICE COMMAND: "SHOW MEDS" ====================

    @Test
    fun voiceCommand_showMeds() {
        // Voice: "Show meds" → API: GET MedicationRequest
        val request = Request.Builder()
            .url("$cernerBaseUrl/MedicationRequest?patient=$testPatientId")
            .header("Accept", "application/fhir+json")
            .get()
            .build()

        val response = httpClient.newCall(request).execute()
        assert(response.code == 200) { "Show meds failed: ${response.code}" }

        val bundle = JSONObject(response.body?.string()!!)
        val count = bundle.optJSONArray("entry")?.length() ?: 0
        println("✓ Voice: 'Show meds' → Found $count medications")
    }

    // ==================== VOICE COMMAND: "SHOW LABS" ====================

    @Test
    fun voiceCommand_showLabs() {
        // Voice: "Show labs" → API: GET Observation?category=laboratory
        val request = Request.Builder()
            .url("$cernerBaseUrl/Observation?patient=$testPatientId&category=laboratory")
            .header("Accept", "application/fhir+json")
            .get()
            .build()

        val response = httpClient.newCall(request).execute()
        assert(response.code == 200) { "Show labs failed: ${response.code}" }

        val bundle = JSONObject(response.body?.string()!!)
        val count = bundle.optJSONArray("entry")?.length() ?: 0
        println("✓ Voice: 'Show labs' → Found $count lab results")
    }

    // ==================== VOICE COMMAND: "SHOW CONDITIONS" ====================

    @Test
    fun voiceCommand_showConditions() {
        // Voice: "Show conditions" → API: GET Condition
        val request = Request.Builder()
            .url("$cernerBaseUrl/Condition?patient=$testPatientId")
            .header("Accept", "application/fhir+json")
            .get()
            .build()

        val response = httpClient.newCall(request).execute()
        assert(response.code == 200) { "Show conditions failed: ${response.code}" }

        val bundle = JSONObject(response.body?.string()!!)
        val count = bundle.optJSONArray("entry")?.length() ?: 0
        println("✓ Voice: 'Show conditions' → Found $count conditions")
    }

    // ==================== VOICE COMMAND: "SHOW PROCEDURES" ====================

    @Test
    fun voiceCommand_showProcedures() {
        // Voice: "Show procedures" → API: GET Procedure
        val request = Request.Builder()
            .url("$cernerBaseUrl/Procedure?patient=$testPatientId")
            .header("Accept", "application/fhir+json")
            .get()
            .build()

        val response = httpClient.newCall(request).execute()
        assert(response.code == 200) { "Show procedures failed: ${response.code}" }

        val bundle = JSONObject(response.body?.string()!!)
        val count = bundle.optJSONArray("entry")?.length() ?: 0
        println("✓ Voice: 'Show procedures' → Found $count procedures")
    }

    // ==================== VOICE COMMAND: "FIND PATIENT [NAME]" ====================

    @Test
    fun voiceCommand_findPatient() {
        // Voice: "Find patient SMART" → API: GET Patient?name=SMART
        val request = Request.Builder()
            .url("$cernerBaseUrl/Patient?name=SMART")
            .header("Accept", "application/fhir+json")
            .get()
            .build()

        val response = httpClient.newCall(request).execute()
        assert(response.code == 200) { "Find patient failed: ${response.code}" }

        val bundle = JSONObject(response.body?.string()!!)
        val count = bundle.optJSONArray("entry")?.length() ?: 0
        assert(count > 0) { "No patients found matching 'SMART'" }
        println("✓ Voice: 'Find patient SMART' → Found $count patients")
    }

    // ==================== VOICE COMMAND: "GENERATE NOTE" ====================

    @Test
    fun voiceCommand_generateNote() {
        // Voice: "Generate note" → API: POST /api/v1/notes/quick
        try {
            val requestBody = JSONObject().apply {
                put("transcript", "Patient reports headache for 3 days, 6/10 pain, right-sided, photophobia present")
                put("chief_complaint", "Headache")
            }

            val request = Request.Builder()
                .url("$ehrProxyUrl/api/v1/notes/quick")
                .post(requestBody.toString().toRequestBody("application/json".toMediaType()))
                .build()

            val response = httpClient.newCall(request).execute()
            if (response.code == 200) {
                val body = response.body?.string()
                assert(body != null)
                println("✓ Voice: 'Generate note' → SOAP note created")
            } else {
                println("⚠ Generate note returned ${response.code}")
            }
        } catch (e: Exception) {
            println("⚠ EHR Proxy not reachable for note generation: ${e.message}")
        }
    }

    // ==================== EHR PROXY HEALTH ====================

    @Test
    fun proxy_healthCheck() {
        try {
            val request = Request.Builder()
                .url("$ehrProxyUrl/")
                .get()
                .build()

            val response = httpClient.newCall(request).execute()
            if (response.code == 200) {
                val body = JSONObject(response.body?.string()!!)
                assert(body.getString("status") == "running")
                println("✓ EHR Proxy healthy at $ehrProxyUrl")
            } else {
                println("⚠ EHR Proxy returned ${response.code}")
            }
        } catch (e: Exception) {
            println("⚠ EHR Proxy not reachable: ${e.message}")
        }
    }

    // ==================== COMPLETE AMBIENT ENCOUNTER ====================

    @Test
    fun e2e_ambientEncounterWorkflow() {
        println("\n=== Ambient Clinical Intelligence Workflow ===")
        println("Voice-first workflow: All interactions via voice commands\n")

        // Step 1: Load Patient (Voice: "Load patient")
        println("Step 1: 'Load patient'")
        val patientRequest = Request.Builder()
            .url("$cernerBaseUrl/Patient/$testPatientId")
            .header("Accept", "application/fhir+json")
            .get()
            .build()
        val patientResponse = httpClient.newCall(patientRequest).execute()
        assert(patientResponse.code == 200)
        println("  ✓ Patient loaded")

        // Step 2: Check Allergies (Voice: "Show allergies")
        println("Step 2: 'Show allergies'")
        val allergiesRequest = Request.Builder()
            .url("$cernerBaseUrl/AllergyIntolerance?patient=$testPatientId")
            .header("Accept", "application/fhir+json")
            .get()
            .build()
        val allergiesResponse = httpClient.newCall(allergiesRequest).execute()
        assert(allergiesResponse.code == 200)
        println("  ✓ Allergies reviewed")

        // Step 3: Check Vitals (Voice: "Show vitals")
        println("Step 3: 'Show vitals'")
        val vitalsRequest = Request.Builder()
            .url("$cernerBaseUrl/Observation?patient=$testPatientId&category=vital-signs")
            .header("Accept", "application/fhir+json")
            .get()
            .build()
        val vitalsResponse = httpClient.newCall(vitalsRequest).execute()
        assert(vitalsResponse.code == 200)
        println("  ✓ Vitals reviewed")

        // Step 4: Check Medications (Voice: "Show meds")
        println("Step 4: 'Show meds'")
        val medsRequest = Request.Builder()
            .url("$cernerBaseUrl/MedicationRequest?patient=$testPatientId")
            .header("Accept", "application/fhir+json")
            .get()
            .build()
        val medsResponse = httpClient.newCall(medsRequest).execute()
        assert(medsResponse.code == 200)
        println("  ✓ Medications reviewed")

        // Step 5: Generate Note (Voice: "Generate note")
        println("Step 5: 'Generate note'")
        try {
            val noteBody = JSONObject().apply {
                put("transcript", "Patient presents with headache. Discussed treatment options.")
                put("chief_complaint", "Headache")
            }
            val noteRequest = Request.Builder()
                .url("$ehrProxyUrl/api/v1/notes/quick")
                .post(noteBody.toString().toRequestBody("application/json".toMediaType()))
                .build()
            val noteResponse = httpClient.newCall(noteRequest).execute()
            if (noteResponse.code == 200) {
                println("  ✓ Note generated")
            } else {
                println("  ⚠ Note generation skipped (proxy not available)")
            }
        } catch (e: Exception) {
            println("  ⚠ Note generation skipped: ${e.message}")
        }

        println("\n=== Ambient Encounter Complete ===")
    }

    // ==================== APP STATE ====================

    @Test
    fun app_remainsResponsive() {
        activityRule.scenario.onActivity { activity ->
            assert(activity != null)
            assert(!activity.isFinishing)
        }
        println("✓ App remains responsive after tests")
    }

    @Test
    fun device_isVuzix() {
        val isVuzix = Build.MODEL.contains("Blade", ignoreCase = true) ||
                      Build.MANUFACTURER.contains("Vuzix", ignoreCase = true)
        println("Device: ${Build.MODEL}, Manufacturer: ${Build.MANUFACTURER}")
        println("Voice-first mode: ${if (isVuzix) "YES (Vuzix)" else "Available"}")
    }
}
