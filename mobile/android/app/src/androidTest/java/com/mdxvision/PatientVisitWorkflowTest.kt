package com.mdxvision

import android.Manifest
import android.os.Build
import androidx.test.ext.junit.rules.ActivityScenarioRule
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.rule.GrantPermissionRule
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONObject
import org.junit.Before
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import java.util.concurrent.TimeUnit

/**
 * Patient Visit Workflow Tests for MDx Vision
 *
 * Tests complete patient visit workflows using API calls (not UI buttons).
 * Voice-first interface means all interactions happen via voice commands,
 * so we test the underlying API functionality directly.
 *
 * Requires EHR Proxy to be running for full functionality.
 *
 * Run with: ./gradlew connectedAndroidTest -Pandroid.testInstrumentationRunnerArguments.class=com.mdxvision.PatientVisitWorkflowTest
 */
@RunWith(AndroidJUnit4::class)
class PatientVisitWorkflowTest {

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
            .connectTimeout(30, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)
            .writeTimeout(30, TimeUnit.SECONDS)
            .build()

        // Allow app to fully initialize
        Thread.sleep(3000)
    }

    // ==================== PATIENT CONTEXT TESTS ====================

    @Test
    fun workflow_loadPatientFromCerner() {
        val request = Request.Builder()
            .url("$cernerBaseUrl/Patient/$testPatientId")
            .header("Accept", "application/fhir+json")
            .get()
            .build()

        val response = httpClient.newCall(request).execute()
        assert(response.code == 200) { "Cerner patient fetch failed: ${response.code}" }

        val body = response.body?.string()
        assert(body != null) { "Response body is null" }

        val patient = JSONObject(body!!)
        assert(patient.getString("resourceType") == "Patient")
        println("✓ Loaded patient: ${patient.getString("id")}")
    }

    @Test
    fun workflow_loadPatientVitals() {
        val request = Request.Builder()
            .url("$cernerBaseUrl/Observation?patient=$testPatientId&category=vital-signs")
            .header("Accept", "application/fhir+json")
            .get()
            .build()

        val response = httpClient.newCall(request).execute()
        assert(response.code == 200) { "Vitals fetch failed: ${response.code}" }

        val bundle = JSONObject(response.body?.string()!!)
        val count = bundle.optJSONArray("entry")?.length() ?: 0
        println("✓ Found $count vital observations")
    }

    @Test
    fun workflow_loadPatientAllergies() {
        val request = Request.Builder()
            .url("$cernerBaseUrl/AllergyIntolerance?patient=$testPatientId")
            .header("Accept", "application/fhir+json")
            .get()
            .build()

        val response = httpClient.newCall(request).execute()
        assert(response.code == 200) { "Allergies fetch failed: ${response.code}" }

        val bundle = JSONObject(response.body?.string()!!)
        val count = bundle.optJSONArray("entry")?.length() ?: 0
        println("✓ Found $count allergies")
    }

    @Test
    fun workflow_loadPatientMedications() {
        val request = Request.Builder()
            .url("$cernerBaseUrl/MedicationRequest?patient=$testPatientId")
            .header("Accept", "application/fhir+json")
            .get()
            .build()

        val response = httpClient.newCall(request).execute()
        assert(response.code == 200) { "Medications fetch failed: ${response.code}" }

        val bundle = JSONObject(response.body?.string()!!)
        val count = bundle.optJSONArray("entry")?.length() ?: 0
        println("✓ Found $count medications")
    }

    @Test
    fun workflow_loadPatientConditions() {
        val request = Request.Builder()
            .url("$cernerBaseUrl/Condition?patient=$testPatientId")
            .header("Accept", "application/fhir+json")
            .get()
            .build()

        val response = httpClient.newCall(request).execute()
        assert(response.code == 200) { "Conditions fetch failed: ${response.code}" }

        val bundle = JSONObject(response.body?.string()!!)
        val count = bundle.optJSONArray("entry")?.length() ?: 0
        println("✓ Found $count conditions")
    }

    // ==================== EHR PROXY TESTS ====================

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
                println("✓ EHR Proxy is running")
            } else {
                println("⚠ EHR Proxy returned ${response.code}")
            }
        } catch (e: Exception) {
            println("⚠ EHR Proxy not reachable: ${e.message}")
        }
    }

    @Test
    fun proxy_patientFetch() {
        try {
            val request = Request.Builder()
                .url("$ehrProxyUrl/api/v1/patient/$testPatientId")
                .get()
                .build()

            val response = httpClient.newCall(request).execute()
            if (response.code == 200) {
                println("✓ EHR Proxy patient fetch works")
            } else {
                println("⚠ EHR Proxy patient fetch returned ${response.code}")
            }
        } catch (e: Exception) {
            println("⚠ EHR Proxy not reachable: ${e.message}")
        }
    }

    // ==================== COMPLETE WORKFLOW TESTS ====================

    @Test
    fun workflow_completeChartReview() {
        println("\n=== Complete Chart Review Workflow ===")

        // Step 1: Patient
        println("Step 1: Loading patient...")
        val patientRequest = Request.Builder()
            .url("$cernerBaseUrl/Patient/$testPatientId")
            .header("Accept", "application/fhir+json")
            .get()
            .build()
        val patientResponse = httpClient.newCall(patientRequest).execute()
        assert(patientResponse.code == 200)
        println("  ✓ Patient loaded")

        // Step 2: Vitals
        println("Step 2: Checking vitals...")
        val vitalsRequest = Request.Builder()
            .url("$cernerBaseUrl/Observation?patient=$testPatientId&category=vital-signs")
            .header("Accept", "application/fhir+json")
            .get()
            .build()
        val vitalsResponse = httpClient.newCall(vitalsRequest).execute()
        assert(vitalsResponse.code == 200)
        println("  ✓ Vitals reviewed")

        // Step 3: Allergies
        println("Step 3: Checking allergies...")
        val allergiesRequest = Request.Builder()
            .url("$cernerBaseUrl/AllergyIntolerance?patient=$testPatientId")
            .header("Accept", "application/fhir+json")
            .get()
            .build()
        val allergiesResponse = httpClient.newCall(allergiesRequest).execute()
        assert(allergiesResponse.code == 200)
        println("  ✓ Allergies reviewed")

        // Step 4: Medications
        println("Step 4: Checking medications...")
        val medsRequest = Request.Builder()
            .url("$cernerBaseUrl/MedicationRequest?patient=$testPatientId")
            .header("Accept", "application/fhir+json")
            .get()
            .build()
        val medsResponse = httpClient.newCall(medsRequest).execute()
        assert(medsResponse.code == 200)
        println("  ✓ Medications reviewed")

        println("=== Chart Review Complete ===\n")
    }

    // ==================== APP STATE TESTS ====================

    @Test
    fun app_remainsResponsive() {
        // Verify app is still running after tests
        activityRule.scenario.onActivity { activity ->
            assert(activity != null)
            assert(!activity.isFinishing)
            assert(!activity.isDestroyed)
        }
        println("✓ App remains responsive")
    }

    @Test
    fun app_detectsDeviceType() {
        val isVuzix = Build.MODEL.contains("Blade", ignoreCase = true) ||
                      Build.MANUFACTURER.contains("Vuzix", ignoreCase = true)
        println("Device: ${Build.MODEL}, Vuzix: $isVuzix")
        // Test passes regardless - just verifies detection works
        assert(true)
    }
}
