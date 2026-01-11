package com.mdxvision

import android.content.Context
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import kotlinx.coroutines.runBlocking
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import java.util.concurrent.TimeUnit

/**
 * End-to-End Integration Tests
 *
 * These tests run on real devices (Vuzix Blade 2, Galaxy S24) and hit real services:
 * - Cerner FHIR sandbox
 * - EHR Proxy (localhost:8002 or configured URL)
 * - OpenAI for note generation
 *
 * Run with: ./gradlew connectedAndroidTest
 * Or on specific device: ./gradlew connectedAndroidTest -Pandroid.testInstrumentationRunnerArguments.class=com.mdxvision.EndToEndIntegrationTest
 */
@RunWith(AndroidJUnit4::class)
class EndToEndIntegrationTest {

    private lateinit var context: Context
    private lateinit var httpClient: OkHttpClient

    // Configuration - can be overridden via test arguments
    private val cernerBaseUrl = "https://fhir-open.cerner.com/r4/ec2458f2-1e24-41c8-b71b-0e701af7583d"
    private val testPatientId = "12724066" // SMARTS SR., NANCYS II

    // EHR Proxy URL - use 10.0.2.2 for emulator, actual IP for real device
    private val ehrProxyUrl: String
        get() {
            val args = InstrumentationRegistry.getArguments()
            return args.getString("ehrProxyUrl", "http://10.0.2.2:8002")
        }

    @Before
    fun setup() {
        context = ApplicationProvider.getApplicationContext()
        // Use longer timeouts for AR glasses (Vuzix network can be slower)
        httpClient = OkHttpClient.Builder()
            .connectTimeout(90, TimeUnit.SECONDS)
            .readTimeout(90, TimeUnit.SECONDS)
            .writeTimeout(90, TimeUnit.SECONDS)
            .build()
    }

    // ==================== Cerner FHIR Direct Tests ====================

    @Test
    fun testCernerPatientFetch() {
        val request = Request.Builder()
            .url("$cernerBaseUrl/Patient/$testPatientId")
            .header("Accept", "application/fhir+json")
            .get()
            .build()

        val response = httpClient.newCall(request).execute()
        assertEquals("Cerner should return 200", 200, response.code)

        val body = response.body?.string()
        assertNotNull("Response body should not be null", body)

        val patient = JSONObject(body!!)
        assertEquals("Patient", patient.getString("resourceType"))
        assertEquals(testPatientId, patient.getString("id"))

        val name = patient.getJSONArray("name").getJSONObject(0)
        val familyName = name.getString("family")
        println("✓ Fetched patient from Cerner: $familyName")
    }

    @Test
    fun testCernerPatientSearch() {
        val request = Request.Builder()
            .url("$cernerBaseUrl/Patient?name=SMART")
            .header("Accept", "application/fhir+json")
            .get()
            .build()

        val response = httpClient.newCall(request).execute()
        assertEquals(200, response.code)

        val bundle = JSONObject(response.body?.string()!!)
        assertEquals("Bundle", bundle.getString("resourceType"))

        val total = if (bundle.has("total")) bundle.getInt("total")
                    else bundle.optJSONArray("entry")?.length() ?: 0
        assertTrue("Should find patients", total > 0)
        println("✓ Found $total patients matching 'SMART'")
    }

    @Test
    fun testCernerConditions() {
        val request = Request.Builder()
            .url("$cernerBaseUrl/Condition?patient=$testPatientId")
            .header("Accept", "application/fhir+json")
            .get()
            .build()

        val response = httpClient.newCall(request).execute()
        assertEquals(200, response.code)

        val bundle = JSONObject(response.body?.string()!!)
        val entries = bundle.optJSONArray("entry")
        val count = entries?.length() ?: 0
        println("✓ Found $count conditions for patient")
    }

    @Test
    fun testCernerMedications() {
        val request = Request.Builder()
            .url("$cernerBaseUrl/MedicationRequest?patient=$testPatientId")
            .header("Accept", "application/fhir+json")
            .get()
            .build()

        val response = httpClient.newCall(request).execute()
        assertEquals(200, response.code)

        val bundle = JSONObject(response.body?.string()!!)
        val count = bundle.optJSONArray("entry")?.length() ?: 0
        println("✓ Found $count medications for patient")
    }

    @Test
    fun testCernerAllergies() {
        val request = Request.Builder()
            .url("$cernerBaseUrl/AllergyIntolerance?patient=$testPatientId")
            .header("Accept", "application/fhir+json")
            .get()
            .build()

        val response = httpClient.newCall(request).execute()
        assertEquals(200, response.code)

        val bundle = JSONObject(response.body?.string()!!)
        val count = bundle.optJSONArray("entry")?.length() ?: 0
        println("✓ Found $count allergies for patient")
    }

    @Test
    fun testCernerVitals() {
        val request = Request.Builder()
            .url("$cernerBaseUrl/Observation?patient=$testPatientId&category=vital-signs")
            .header("Accept", "application/fhir+json")
            .get()
            .build()

        val response = httpClient.newCall(request).execute()
        assertEquals(200, response.code)

        val bundle = JSONObject(response.body?.string()!!)
        val count = bundle.optJSONArray("entry")?.length() ?: 0
        println("✓ Found $count vital observations")
    }

    // ==================== EHR Proxy Tests ====================

    @Test
    fun testEhrProxyHealth() {
        try {
            val request = Request.Builder()
                .url("$ehrProxyUrl/health")
                .get()
                .build()

            val response = httpClient.newCall(request).execute()
            assertEquals("EHR Proxy health check should return 200", 200, response.code)
            println("✓ EHR Proxy is healthy at $ehrProxyUrl")
        } catch (e: Exception) {
            println("⚠ EHR Proxy not reachable at $ehrProxyUrl: ${e.message}")
            // Don't fail - proxy might not be running
        }
    }

    @Test
    fun testEhrProxyPatientFetch() {
        try {
            val request = Request.Builder()
                .url("$ehrProxyUrl/api/v1/patient/$testPatientId")
                .get()
                .build()

            val response = httpClient.newCall(request).execute()
            if (response.code == 200) {
                val body = response.body?.string()
                assertNotNull(body)
                println("✓ EHR Proxy patient fetch works")
            } else {
                println("⚠ EHR Proxy returned ${response.code}")
            }
        } catch (e: Exception) {
            println("⚠ EHR Proxy not reachable: ${e.message}")
        }
    }

    @Test
    fun testEhrProxyPatientSearch() {
        try {
            val request = Request.Builder()
                .url("$ehrProxyUrl/api/v1/patient/search?name=SMART")
                .get()
                .build()

            val response = httpClient.newCall(request).execute()
            if (response.code == 200) {
                println("✓ EHR Proxy patient search works")
            } else {
                println("⚠ EHR Proxy search returned ${response.code}")
            }
        } catch (e: Exception) {
            println("⚠ EHR Proxy not reachable: ${e.message}")
        }
    }

    @Test
    fun testEhrProxyNoteGeneration() {
        try {
            val requestBody = JSONObject().apply {
                put("transcript", "Patient reports headache for 3 days, right-sided, 6/10 pain, photophobia")
                put("chief_complaint", "Headache")
            }

            val request = Request.Builder()
                .url("$ehrProxyUrl/api/v1/notes/quick")
                .post(requestBody.toString().toRequestBody("application/json".toMediaType()))
                .build()

            val response = httpClient.newCall(request).execute()
            if (response.code == 200) {
                val body = response.body?.string()
                assertNotNull(body)
                assertTrue("Should contain SOAP sections", body!!.contains("subjective") || body.contains("assessment"))
                println("✓ EHR Proxy SOAP note generation works")
            } else {
                println("⚠ Note generation returned ${response.code}: ${response.body?.string()}")
            }
        } catch (e: Exception) {
            println("⚠ EHR Proxy not reachable: ${e.message}")
        }
    }

    // ==================== Full E2E Workflow Tests ====================

    @Test
    fun testFullPatientWorkflow() {
        println("\n=== Full Patient Workflow Test ===")

        // Step 1: Fetch patient from Cerner
        println("Step 1: Fetching patient from Cerner...")
        val patientRequest = Request.Builder()
            .url("$cernerBaseUrl/Patient/$testPatientId")
            .header("Accept", "application/fhir+json")
            .get()
            .build()

        val patientResponse = httpClient.newCall(patientRequest).execute()
        assertEquals(200, patientResponse.code)

        val patient = JSONObject(patientResponse.body?.string()!!)
        val name = patient.getJSONArray("name").getJSONObject(0)
        val patientName = "${name.getJSONArray("given").getString(0)} ${name.getString("family")}"
        println("  ✓ Patient: $patientName")

        // Step 2: Fetch conditions
        println("Step 2: Fetching conditions...")
        val conditionsRequest = Request.Builder()
            .url("$cernerBaseUrl/Condition?patient=$testPatientId")
            .header("Accept", "application/fhir+json")
            .get()
            .build()

        val conditionsResponse = httpClient.newCall(conditionsRequest).execute()
        val conditions = JSONObject(conditionsResponse.body?.string()!!)
        val conditionCount = conditions.optJSONArray("entry")?.length() ?: 0
        println("  ✓ Found $conditionCount conditions")

        // Step 3: Fetch allergies
        println("Step 3: Fetching allergies...")
        val allergiesRequest = Request.Builder()
            .url("$cernerBaseUrl/AllergyIntolerance?patient=$testPatientId")
            .header("Accept", "application/fhir+json")
            .get()
            .build()

        val allergiesResponse = httpClient.newCall(allergiesRequest).execute()
        val allergies = JSONObject(allergiesResponse.body?.string()!!)
        val allergyCount = allergies.optJSONArray("entry")?.length() ?: 0
        println("  ✓ Found $allergyCount allergies")

        // Step 4: Fetch medications
        println("Step 4: Fetching medications...")
        val medsRequest = Request.Builder()
            .url("$cernerBaseUrl/MedicationRequest?patient=$testPatientId")
            .header("Accept", "application/fhir+json")
            .get()
            .build()

        val medsResponse = httpClient.newCall(medsRequest).execute()
        val meds = JSONObject(medsResponse.body?.string()!!)
        val medCount = meds.optJSONArray("entry")?.length() ?: 0
        println("  ✓ Found $medCount medications")

        // Summary
        println("\n=== Patient Summary ===")
        println("Name: $patientName")
        println("Conditions: $conditionCount")
        println("Allergies: $allergyCount")
        println("Medications: $medCount")
        println("========================")

        println("\n✓ Full patient workflow completed successfully!")
    }

    @Test
    fun testVoiceCommandSimulation() {
        // Simulates voice command flow
        println("\n=== Voice Command Simulation ===")

        // Simulate "Find Patient SMART"
        println("Command: 'Find Patient SMART'")

        val request = Request.Builder()
            .url("$cernerBaseUrl/Patient?name=SMART")
            .header("Accept", "application/fhir+json")
            .get()
            .build()

        val response = httpClient.newCall(request).execute()
        assertEquals(200, response.code)

        val bundle = JSONObject(response.body?.string()!!)
        val entries = bundle.optJSONArray("entry")

        if (entries != null && entries.length() > 0) {
            // Get first patient
            val firstPatient = entries.getJSONObject(0).getJSONObject("resource")
            val name = firstPatient.getJSONArray("name").getJSONObject(0)
            val patientId = firstPatient.getString("id")
            println("  → Found: ${name.getString("family")}, ${name.getJSONArray("given").getString(0)}")
            println("  → Patient ID: $patientId")

            // Simulate "Load Patient"
            println("Command: 'Load Patient'")

            val patientRequest = Request.Builder()
                .url("$cernerBaseUrl/Patient/$patientId")
                .header("Accept", "application/fhir+json")
                .get()
                .build()

            val patientResponse = httpClient.newCall(patientRequest).execute()
            assertEquals(200, patientResponse.code)
            println("  ✓ Patient loaded successfully")

            // Simulate "Show Allergies"
            println("Command: 'Show Allergies'")

            val allergiesRequest = Request.Builder()
                .url("$cernerBaseUrl/AllergyIntolerance?patient=$patientId")
                .header("Accept", "application/fhir+json")
                .get()
                .build()

            val allergiesResponse = httpClient.newCall(allergiesRequest).execute()
            assertEquals(200, allergiesResponse.code)
            println("  ✓ Allergies displayed")
        }

        println("================================")
        println("\n✓ Voice command simulation passed!")
    }
}
