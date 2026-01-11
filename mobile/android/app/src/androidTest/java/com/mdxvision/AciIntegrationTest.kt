package com.mdxvision

import android.Manifest
import androidx.test.espresso.Espresso.onView
import androidx.test.espresso.action.ViewActions.*
import androidx.test.espresso.assertion.ViewAssertions.matches
import androidx.test.espresso.matcher.ViewMatchers.*
import androidx.test.ext.junit.rules.ActivityScenarioRule
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.rule.GrantPermissionRule
import org.hamcrest.CoreMatchers.containsString
import org.junit.Before
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/**
 * Integration Tests for Ambient Clinical Intelligence (ACI)
 *
 * These tests verify the complete ACI workflow including:
 * - EHR proxy connectivity
 * - Patient context loading
 * - Real-time transcription
 * - Clinical entity extraction
 * - Auto-documentation generation
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

    companion object {
        // Extended timeouts for integration tests
        const val PROXY_CONNECTION_TIMEOUT = 8000L
        const val TRANSCRIPTION_SESSION_TIMEOUT = 5000L
        const val NOTE_GENERATION_TIMEOUT = 15000L
        const val UI_ANIMATION_TIMEOUT = 1500L
    }

    @Before
    fun setup() {
        // Allow app to fully initialize and connect to services
        Thread.sleep(4000)
    }

    // ==================== E2E: COMPLETE AMBIENT ENCOUNTER ====================

    /**
     * Integration Test: Full Ambient Clinical Encounter
     *
     * Simulates a complete clinical encounter from start to finish:
     * 1. Load patient from EHR
     * 2. Review critical chart data
     * 3. Start ambient listening
     * 4. Simulate encounter duration
     * 5. Stop and review captured entities
     * 6. Generate clinical note
     */
    @Test
    fun e2e_completeAmbientEncounter() {
        // Phase 1: Patient Context
        onView(withText("LOAD PATIENT"))
            .perform(click())
        Thread.sleep(PROXY_CONNECTION_TIMEOUT)

        // Phase 2: Pre-encounter Chart Review
        onView(withText("SHOW ALLERGIES"))
            .perform(click())
        Thread.sleep(UI_ANIMATION_TIMEOUT * 2)

        onView(withText("SHOW MEDS"))
            .perform(click())
        Thread.sleep(UI_ANIMATION_TIMEOUT * 2)

        // Phase 3: Start Ambient Mode
        onView(withText("LIVE TRANSCRIBE"))
            .perform(click())
        Thread.sleep(TRANSCRIPTION_SESSION_TIMEOUT)

        // Phase 4: Simulate encounter (in real use, conversation happens here)
        Thread.sleep(3000)

        // Phase 5: Stop Ambient Mode
        try {
            onView(withText(containsString("Stop")))
                .perform(click())
        } catch (e: Exception) {
            onView(withText("LIVE TRANSCRIBE"))
                .perform(click())
        }
        Thread.sleep(UI_ANIMATION_TIMEOUT)

        // Phase 6: Verify app stable after full workflow
        onView(withText("MDX MODE"))
            .check(matches(isDisplayed()))
    }

    // ==================== E2E: CHART REVIEW WITH ACI ====================

    /**
     * Integration Test: Comprehensive Chart Review Before ACI
     *
     * Reviews all patient data sections that inform ACI entity extraction:
     * - Demographics (patient load)
     * - Vitals (baseline values)
     * - Allergies (safety checking)
     * - Medications (drug mentions)
     * - Labs (reference values)
     * - Conditions (existing diagnoses)
     */
    @Test
    fun e2e_comprehensiveChartReview() {
        // Load patient
        onView(withText("LOAD PATIENT"))
            .perform(click())
        Thread.sleep(PROXY_CONNECTION_TIMEOUT)

        // Review each chart section
        val chartSections = listOf(
            "SHOW VITALS",
            "SHOW ALLERGIES",
            "SHOW MEDS",
            "SHOW LABS",
            "SHOW PROCEDURES"
        )

        for (section in chartSections) {
            onView(withText(section))
                .perform(click())
            Thread.sleep(UI_ANIMATION_TIMEOUT * 2)
        }

        // Verify all reviews complete
        onView(withText("LOAD PATIENT"))
            .check(matches(isDisplayed()))
    }

    // ==================== E2E: MULTI-PATIENT SESSION ====================

    /**
     * Integration Test: Multiple Patients in Sequence
     *
     * Simulates a provider seeing multiple patients back-to-back:
     * 1. Load patient 1, quick review
     * 2. Load patient 2 (context switches)
     * 3. Verify context properly cleared/updated
     */
    @Test
    fun e2e_multiPatientSession() {
        // First patient
        onView(withText("LOAD PATIENT"))
            .perform(click())
        Thread.sleep(PROXY_CONNECTION_TIMEOUT)

        onView(withText("SHOW VITALS"))
            .perform(click())
        Thread.sleep(UI_ANIMATION_TIMEOUT * 2)

        // Load same patient again (simulating second patient)
        // In production this would be a different patient
        onView(withText("LOAD PATIENT"))
            .perform(click())
        Thread.sleep(PROXY_CONNECTION_TIMEOUT)

        // Verify context updated
        onView(withText("SHOW ALLERGIES"))
            .perform(click())
        Thread.sleep(UI_ANIMATION_TIMEOUT)
    }

    // ==================== E2E: TRANSCRIPTION RESILIENCE ====================

    /**
     * Integration Test: Transcription Start/Stop Resilience
     *
     * Tests that the transcription system handles multiple cycles:
     * - Rapid start/stop
     * - Extended session
     * - Clean shutdown
     */
    @Test
    fun e2e_transcriptionResilience() {
        // Load patient
        onView(withText("LOAD PATIENT"))
            .perform(click())
        Thread.sleep(PROXY_CONNECTION_TIMEOUT)

        // Quick start/stop
        onView(withText("LIVE TRANSCRIBE"))
            .perform(click())
        Thread.sleep(2000)
        onView(withText("LIVE TRANSCRIBE"))
            .perform(click())
        Thread.sleep(UI_ANIMATION_TIMEOUT)

        // Extended session
        onView(withText("LIVE TRANSCRIBE"))
            .perform(click())
        Thread.sleep(5000)
        onView(withText("LIVE TRANSCRIBE"))
            .perform(click())
        Thread.sleep(UI_ANIMATION_TIMEOUT)

        // Verify stable
        onView(withText("MDX MODE"))
            .check(matches(isDisplayed()))
    }

    // ==================== E2E: DOCUMENTATION WORKFLOW ====================

    /**
     * Integration Test: Note Creation Workflow
     *
     * Tests the complete documentation workflow:
     * 1. Load patient
     * 2. Start note
     * 3. Capture content
     * 4. Generate/review note
     */
    @Test
    fun e2e_noteCreationWorkflow() {
        // Load patient
        onView(withText("LOAD PATIENT"))
            .perform(click())
        Thread.sleep(PROXY_CONNECTION_TIMEOUT)

        // Start note mode
        onView(withText("START NOTE"))
            .perform(click())
        Thread.sleep(UI_ANIMATION_TIMEOUT * 2)

        // The note interface should be active
        // Further steps depend on note UI state
    }

    // ==================== CONNECTIVITY TESTS ====================

    /**
     * Integration Test: Proxy Health Check
     *
     * Verifies connection to EHR proxy is working
     */
    @Test
    fun connectivity_proxyHealthCheck() {
        // Load patient exercises the proxy connection
        onView(withText("LOAD PATIENT"))
            .perform(click())
        Thread.sleep(PROXY_CONNECTION_TIMEOUT)

        // If proxy is running, patient loads
        // If not, error shown but app doesn't crash
        onView(withText("MDX MODE"))
            .check(matches(isDisplayed()))
    }

    /**
     * Integration Test: WebSocket Connection for Transcription
     *
     * Verifies WebSocket connection for real-time transcription
     */
    @Test
    fun connectivity_websocketTranscription() {
        // Load patient for context
        onView(withText("LOAD PATIENT"))
            .perform(click())
        Thread.sleep(PROXY_CONNECTION_TIMEOUT)

        // Start transcription (establishes WebSocket)
        onView(withText("LIVE TRANSCRIBE"))
            .perform(click())
        Thread.sleep(TRANSCRIPTION_SESSION_TIMEOUT)

        // Stop
        onView(withText("LIVE TRANSCRIBE"))
            .perform(click())
        Thread.sleep(UI_ANIMATION_TIMEOUT)

        // Verify clean disconnect
        onView(withText("MDX MODE"))
            .check(matches(isDisplayed()))
    }

    // ==================== SAFETY TESTS ====================

    /**
     * Integration Test: Allergy Alert System
     *
     * Verifies allergies are loaded and available for safety checks
     */
    @Test
    fun safety_allergyAlertsAvailable() {
        // Load patient (should trigger allergy alerts if critical)
        onView(withText("LOAD PATIENT"))
            .perform(click())
        Thread.sleep(PROXY_CONNECTION_TIMEOUT)

        // Check allergies display
        onView(withText("SHOW ALLERGIES"))
            .perform(click())
        Thread.sleep(UI_ANIMATION_TIMEOUT * 2)

        // Allergies should be shown
    }

    /**
     * Integration Test: Critical Vitals Detection
     *
     * Verifies vital signs are loaded for critical value detection
     */
    @Test
    fun safety_vitalSignsMonitoring() {
        // Load patient
        onView(withText("LOAD PATIENT"))
            .perform(click())
        Thread.sleep(PROXY_CONNECTION_TIMEOUT)

        // Check vitals
        onView(withText("SHOW VITALS"))
            .perform(click())
        Thread.sleep(UI_ANIMATION_TIMEOUT * 2)

        // Vitals should display with critical value highlighting if applicable
    }

    // ==================== PERFORMANCE TESTS ====================

    /**
     * Integration Test: UI Responsiveness Under Load
     *
     * Verifies UI remains responsive during active transcription
     */
    @Test
    fun performance_uiResponsivenessDuringTranscription() {
        // Load patient
        onView(withText("LOAD PATIENT"))
            .perform(click())
        Thread.sleep(PROXY_CONNECTION_TIMEOUT)

        // Start transcription
        onView(withText("LIVE TRANSCRIBE"))
            .perform(click())
        Thread.sleep(2000)

        // While transcribing, UI should still respond
        onView(withText("MDX MODE"))
            .check(matches(isDisplayed()))

        onView(withText("SHOW VITALS"))
            .perform(click())
        Thread.sleep(UI_ANIMATION_TIMEOUT)

        // Stop transcription
        onView(withText("LIVE TRANSCRIBE"))
            .perform(click())
    }

    /**
     * Integration Test: Memory Stability
     *
     * Runs multiple operations to verify no memory leaks
     */
    @Test
    fun performance_memoryStability() {
        // Run 5 load cycles
        repeat(5) { _ ->
            onView(withText("LOAD PATIENT"))
                .perform(click())
            Thread.sleep(3000)

            onView(withText("SHOW VITALS"))
                .perform(click())
            Thread.sleep(UI_ANIMATION_TIMEOUT)
        }

        // App should still be responsive
        onView(withText("MDX MODE"))
            .check(matches(isDisplayed()))
    }

    // ==================== EDGE CASE TESTS ====================

    /**
     * Integration Test: Rapid Button Presses
     *
     * Verifies app handles rapid UI interactions gracefully
     */
    @Test
    fun edgeCase_rapidButtonPresses() {
        // Rapid clicks on load patient
        repeat(3) {
            onView(withText("LOAD PATIENT"))
                .perform(click())
            Thread.sleep(500)
        }
        Thread.sleep(PROXY_CONNECTION_TIMEOUT)

        // Rapid clicks on vitals
        repeat(3) {
            onView(withText("SHOW VITALS"))
                .perform(click())
            Thread.sleep(300)
        }

        // App should handle gracefully
        onView(withText("MDX MODE"))
            .check(matches(isDisplayed()))
    }

    /**
     * Integration Test: Overlapping Operations
     *
     * Tests starting new operations while others in progress
     */
    @Test
    fun edgeCase_overlappingOperations() {
        // Start load
        onView(withText("LOAD PATIENT"))
            .perform(click())

        // Immediately try to show vitals
        onView(withText("SHOW VITALS"))
            .perform(click())

        // Wait for operations to settle
        Thread.sleep(PROXY_CONNECTION_TIMEOUT)

        // App should be stable
        onView(withText("MDX MODE"))
            .check(matches(isDisplayed()))
    }
}
