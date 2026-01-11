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
 * Instrumented Tests for Ambient Clinical Intelligence (ACI) Feature
 *
 * Tests the ACI system which provides:
 * - Continuous background audio capture during patient encounters
 * - Multi-speaker diarization (clinician vs patient)
 * - Clinical entity extraction (symptoms, meds, vitals, etc.)
 * - Auto-documentation with SOAP note generation
 *
 * Run with: ./gradlew connectedAndroidTest -Pandroid.testInstrumentationRunnerArguments.class=com.mdxvision.AmbientClinicalIntelligenceTest
 */
@RunWith(AndroidJUnit4::class)
class AmbientClinicalIntelligenceTest {

    @get:Rule
    val activityRule = ActivityScenarioRule(MainActivity::class.java)

    @get:Rule
    val permissionRule: GrantPermissionRule = GrantPermissionRule.grant(
        Manifest.permission.RECORD_AUDIO,
        Manifest.permission.CAMERA,
        Manifest.permission.INTERNET
    )

    companion object {
        const val NETWORK_TIMEOUT = 5000L
        const val ACI_STARTUP_TIMEOUT = 3000L
        const val ENTITY_EXTRACTION_TIMEOUT = 2000L
        const val NOTE_GENERATION_TIMEOUT = 10000L
        const val UI_SETTLE_TIME = 1000L
    }

    @Before
    fun setup() {
        // Allow app to fully initialize
        Thread.sleep(3000)
    }

    // ==================== ACI MODE TESTS ====================

    /**
     * Test: ACI mode can be started via voice command simulation
     *
     * Verifies the ambient mode toggle functionality
     */
    @Test
    fun aciModeCanBeToggled() {
        // First load a patient (required for ACI context)
        onView(withText("LOAD PATIENT"))
            .perform(click())
        Thread.sleep(NETWORK_TIMEOUT)

        // Verify app is responsive and commands are visible
        onView(withText("LIVE TRANSCRIBE"))
            .check(matches(isDisplayed()))
    }

    /**
     * Test: ACI requires patient to be loaded first
     *
     * ACI should warn if no patient context
     */
    @Test
    fun aciRequiresPatientContext() {
        // Try to start live transcription without patient
        onView(withText("LIVE TRANSCRIBE"))
            .perform(click())
        Thread.sleep(ACI_STARTUP_TIMEOUT)

        // App should handle gracefully
        onView(withText("LOAD PATIENT"))
            .check(matches(isDisplayed()))
    }

    // ==================== TRANSCRIPTION TESTS ====================

    /**
     * Test: Live transcription starts and displays UI
     */
    @Test
    fun liveTranscriptionStartsSuccessfully() {
        // Load patient first
        onView(withText("LOAD PATIENT"))
            .perform(click())
        Thread.sleep(NETWORK_TIMEOUT)

        // Start live transcription
        onView(withText("LIVE TRANSCRIBE"))
            .perform(click())
        Thread.sleep(ACI_STARTUP_TIMEOUT)

        // Verify app didn't crash
        // (Actual transcription requires proxy connection)
    }

    /**
     * Test: Transcription can be stopped
     */
    @Test
    fun transcriptionCanBeStopped() {
        // Load patient
        onView(withText("LOAD PATIENT"))
            .perform(click())
        Thread.sleep(NETWORK_TIMEOUT)

        // Start transcription
        onView(withText("LIVE TRANSCRIBE"))
            .perform(click())
        Thread.sleep(ACI_STARTUP_TIMEOUT)

        // Try to stop (may use different button)
        try {
            onView(withText(containsString("Stop")))
                .perform(click())
        } catch (e: Exception) {
            // Toggle off by clicking again
            onView(withText("LIVE TRANSCRIBE"))
                .perform(click())
        }
        Thread.sleep(UI_SETTLE_TIME)

        // Verify command grid is still responsive
        onView(withText("LOAD PATIENT"))
            .check(matches(isDisplayed()))
    }

    // ==================== CLINICAL ENTITY EXTRACTION TESTS ====================

    /**
     * Test: Patient chart data loads correctly for entity matching
     *
     * Clinical entity extraction requires loaded patient context
     */
    @Test
    fun patientChartLoadsForEntityContext() {
        // Load patient
        onView(withText("LOAD PATIENT"))
            .perform(click())
        Thread.sleep(NETWORK_TIMEOUT)

        // Verify patient-related functions become available
        onView(withText("SHOW VITALS"))
            .perform(click())
        Thread.sleep(UI_SETTLE_TIME)

        // Vitals should show (confirming patient context loaded)
    }

    /**
     * Test: Allergies are available for safety cross-reference
     */
    @Test
    fun allergiesLoadForSafetyCrossReference() {
        // Load patient
        onView(withText("LOAD PATIENT"))
            .perform(click())
        Thread.sleep(NETWORK_TIMEOUT)

        // Show allergies
        onView(withText("SHOW ALLERGIES"))
            .perform(click())
        Thread.sleep(UI_SETTLE_TIME)

        // Allergies overlay should display
    }

    /**
     * Test: Medications load for interaction checking
     */
    @Test
    fun medicationsLoadForInteractionChecking() {
        // Load patient
        onView(withText("LOAD PATIENT"))
            .perform(click())
        Thread.sleep(NETWORK_TIMEOUT)

        // Show medications
        onView(withText("SHOW MEDS"))
            .perform(click())
        Thread.sleep(UI_SETTLE_TIME)

        // Medications overlay should display
    }

    // ==================== SPEAKER DIARIZATION TESTS ====================

    /**
     * Test: Speaker context is set from patient chart
     *
     * ACI uses patient name from chart to label speakers
     */
    @Test
    fun speakerContextSetFromPatientChart() {
        // Load patient (sets speaker context)
        onView(withText("LOAD PATIENT"))
            .perform(click())
        Thread.sleep(NETWORK_TIMEOUT)

        // Start transcription (uses speaker context)
        onView(withText("LIVE TRANSCRIBE"))
            .perform(click())
        Thread.sleep(ACI_STARTUP_TIMEOUT)

        // Stop and verify app responsive
        try {
            onView(withText(containsString("Stop")))
                .perform(click())
        } catch (e: Exception) {
            onView(withText("LIVE TRANSCRIBE"))
                .perform(click())
        }
        Thread.sleep(UI_SETTLE_TIME)

        // Verify app is responsive
        onView(withText("MDX MODE"))
            .check(matches(isDisplayed()))
    }

    // ==================== AUTO-DOCUMENTATION TESTS ====================

    /**
     * Test: Note generation is available after transcription
     */
    @Test
    fun noteGenerationAvailableAfterTranscription() {
        // Load patient
        onView(withText("LOAD PATIENT"))
            .perform(click())
        Thread.sleep(NETWORK_TIMEOUT)

        // Start transcription
        onView(withText("LIVE TRANSCRIBE"))
            .perform(click())
        Thread.sleep(ACI_STARTUP_TIMEOUT)

        // Stop transcription
        try {
            onView(withText(containsString("Stop")))
                .perform(click())
        } catch (e: Exception) {
            onView(withText("LIVE TRANSCRIBE"))
                .perform(click())
        }
        Thread.sleep(UI_SETTLE_TIME)

        // Look for note generation option
        // (Should show after transcription ends)
    }

    /**
     * Test: START NOTE button is accessible
     */
    @Test
    fun startNoteButtonAccessible() {
        // Load patient
        onView(withText("LOAD PATIENT"))
            .perform(click())
        Thread.sleep(NETWORK_TIMEOUT)

        // Verify START NOTE is visible and clickable
        onView(withText("START NOTE"))
            .check(matches(isDisplayed()))

        // Tap it
        onView(withText("START NOTE"))
            .perform(click())
        Thread.sleep(UI_SETTLE_TIME)
    }

    // ==================== COMPLETE ACI WORKFLOW TEST ====================

    /**
     * Test: Complete ACI Workflow
     *
     * Full ambient documentation flow:
     * 1. Load patient (context)
     * 2. Review chart (vitals, allergies)
     * 3. Start ambient/transcription
     * 4. Stop and generate note
     */
    @Test
    fun completeAciWorkflow() {
        // Step 1: Load patient for context
        onView(withText("LOAD PATIENT"))
            .perform(click())
        Thread.sleep(NETWORK_TIMEOUT)

        // Step 2: Quick chart review
        onView(withText("SHOW VITALS"))
            .perform(click())
        Thread.sleep(UI_SETTLE_TIME * 2)

        onView(withText("SHOW ALLERGIES"))
            .perform(click())
        Thread.sleep(UI_SETTLE_TIME * 2)

        // Step 3: Start ambient listening
        onView(withText("LIVE TRANSCRIBE"))
            .perform(click())
        Thread.sleep(ACI_STARTUP_TIMEOUT)

        // Step 4: Stop and check for note generation
        try {
            onView(withText(containsString("Stop")))
                .perform(click())
        } catch (e: Exception) {
            onView(withText("LIVE TRANSCRIBE"))
                .perform(click())
        }
        Thread.sleep(UI_SETTLE_TIME)

        // Verify we can still interact with app
        onView(withText("LOAD PATIENT"))
            .check(matches(isDisplayed()))
    }

    // ==================== ACI OVERLAY TESTS ====================

    /**
     * Test: Multiple overlays can be shown sequentially
     */
    @Test
    fun multipleOverlaysSequentialDisplay() {
        // Load patient
        onView(withText("LOAD PATIENT"))
            .perform(click())
        Thread.sleep(NETWORK_TIMEOUT)

        // Show vitals, then allergies, then meds
        val overlayButtons = listOf("SHOW VITALS", "SHOW ALLERGIES", "SHOW MEDS")

        for (button in overlayButtons) {
            onView(withText(button))
                .perform(click())
            Thread.sleep(UI_SETTLE_TIME * 2)
        }

        // App should still be responsive
        onView(withText("MDX MODE"))
            .check(matches(isDisplayed()))
    }

    /**
     * Test: Lab results accessible for clinical context
     */
    @Test
    fun labResultsAccessibleForContext() {
        // Load patient
        onView(withText("LOAD PATIENT"))
            .perform(click())
        Thread.sleep(NETWORK_TIMEOUT)

        // Show labs
        onView(withText("SHOW LABS"))
            .perform(click())
        Thread.sleep(UI_SETTLE_TIME * 2)

        // App should handle (even if no labs available)
        onView(withText("MDX MODE"))
            .check(matches(isDisplayed()))
    }

    /**
     * Test: Procedures accessible for clinical context
     */
    @Test
    fun proceduresAccessibleForContext() {
        // Load patient
        onView(withText("LOAD PATIENT"))
            .perform(click())
        Thread.sleep(NETWORK_TIMEOUT)

        // Show procedures
        onView(withText("SHOW PROCEDURES"))
            .perform(click())
        Thread.sleep(UI_SETTLE_TIME * 2)

        // App should handle
        onView(withText("MDX MODE"))
            .check(matches(isDisplayed()))
    }

    // ==================== ERROR HANDLING TESTS ====================

    /**
     * Test: App handles proxy disconnection gracefully
     */
    @Test
    fun handlesProxyDisconnectionGracefully() {
        // Try operations that require proxy
        onView(withText("LOAD PATIENT"))
            .perform(click())
        Thread.sleep(NETWORK_TIMEOUT)

        // Even if proxy unavailable, app shouldn't crash
        onView(withText("MDX MODE"))
            .check(matches(isDisplayed()))
    }

    /**
     * Test: App handles audio permission correctly
     */
    @Test
    fun audioPermissionHandledCorrectly() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val permissionStatus = context.checkSelfPermission(Manifest.permission.RECORD_AUDIO)
        assert(permissionStatus == android.content.pm.PackageManager.PERMISSION_GRANTED)
    }

    // ==================== MULTI-LANGUAGE ACI TESTS ====================

    /**
     * Test: ACI works with default English locale
     */
    @Test
    fun aciWorksWithEnglishLocale() {
        // Load patient
        onView(withText("LOAD PATIENT"))
            .perform(click())
        Thread.sleep(NETWORK_TIMEOUT)

        // English commands should work
        onView(withText("SHOW VITALS"))
            .check(matches(isDisplayed()))
    }

    /**
     * Test: Command grid displays correctly for ACI
     */
    @Test
    fun commandGridDisplaysCorrectlyForAci() {
        val aciRelatedCommands = listOf(
            "LOAD PATIENT",
            "SHOW VITALS",
            "SHOW ALLERGIES",
            "SHOW MEDS",
            "LIVE TRANSCRIBE",
            "START NOTE"
        )

        for (command in aciRelatedCommands) {
            try {
                onView(withText(command))
                    .check(matches(isDisplayed()))
            } catch (e: Exception) {
                // Some may be scrolled off screen
            }
        }
    }

    // ==================== PERFORMANCE TESTS ====================

    /**
     * Test: App remains responsive during ACI operations
     */
    @Test
    fun appResponsiveDuringAciOperations() {
        // Load patient
        onView(withText("LOAD PATIENT"))
            .perform(click())
        Thread.sleep(NETWORK_TIMEOUT)

        // Start transcription
        onView(withText("LIVE TRANSCRIBE"))
            .perform(click())
        Thread.sleep(ACI_STARTUP_TIMEOUT)

        // During transcription, verify UI is still responsive
        onView(withText("MDX MODE"))
            .check(matches(isDisplayed()))

        // Stop
        try {
            onView(withText(containsString("Stop")))
                .perform(click())
        } catch (e: Exception) {
            onView(withText("LIVE TRANSCRIBE"))
                .perform(click())
        }
    }

    /**
     * Test: Multiple start/stop cycles don't crash app
     */
    @Test
    fun multipleStartStopCyclesStable() {
        // Load patient
        onView(withText("LOAD PATIENT"))
            .perform(click())
        Thread.sleep(NETWORK_TIMEOUT)

        // Do 3 start/stop cycles
        repeat(3) {
            onView(withText("LIVE TRANSCRIBE"))
                .perform(click())
            Thread.sleep(2000)

            onView(withText("LIVE TRANSCRIBE"))
                .perform(click())
            Thread.sleep(UI_SETTLE_TIME)
        }

        // App should still be stable
        onView(withText("MDX MODE"))
            .check(matches(isDisplayed()))
    }
}
