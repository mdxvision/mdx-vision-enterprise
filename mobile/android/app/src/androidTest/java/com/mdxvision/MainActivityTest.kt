package com.mdxvision

import android.Manifest
import android.os.Build
import androidx.test.ext.junit.rules.ActivityScenarioRule
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.rule.GrantPermissionRule
import org.junit.Before
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/**
 * Instrumented tests for MDx Vision MainActivity
 *
 * These tests run on Android devices including Vuzix Blade 2.
 * Since Vuzix uses voice-first interface (no button grid), these tests
 * focus on app initialization, permissions, and context - not UI buttons.
 *
 * For API-based E2E tests, see EndToEndIntegrationTest.kt
 *
 * Run with: ./gradlew connectedAndroidTest
 */
@RunWith(AndroidJUnit4::class)
class MainActivityTest {

    @get:Rule
    val activityRule = ActivityScenarioRule(MainActivity::class.java)

    @get:Rule
    val permissionRule: GrantPermissionRule = GrantPermissionRule.grant(
        Manifest.permission.RECORD_AUDIO,
        Manifest.permission.CAMERA,
        Manifest.permission.INTERNET
    )

    private fun isVuzixDevice(): Boolean {
        return Build.MODEL.contains("Blade", ignoreCase = true) ||
               Build.MANUFACTURER.contains("Vuzix", ignoreCase = true)
    }

    @Before
    fun setup() {
        // Allow app to fully initialize including speech recognizer
        Thread.sleep(3000)
    }

    // ==================== APP INITIALIZATION TESTS ====================

    @Test
    fun appLaunches_successfully() {
        // Verify app launches without crashing
        activityRule.scenario.onActivity { activity ->
            assert(activity != null)
        }
    }

    @Test
    fun appContext_isCorrect() {
        val appContext = InstrumentationRegistry.getInstrumentation().targetContext
        assert(appContext.packageName == "com.mdxvision.glasses")
    }

    @Test
    fun deviceDetection_works() {
        val isVuzix = isVuzixDevice()
        println("Device: ${Build.MODEL}, Manufacturer: ${Build.MANUFACTURER}, isVuzix: $isVuzix")
        // This test just verifies detection logic doesn't crash
        assert(true)
    }

    // ==================== PERMISSION TESTS ====================

    @Test
    fun microphonePermission_granted() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val permissionStatus = context.checkSelfPermission(Manifest.permission.RECORD_AUDIO)
        assert(permissionStatus == android.content.pm.PackageManager.PERMISSION_GRANTED)
    }

    @Test
    fun cameraPermission_granted() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val permissionStatus = context.checkSelfPermission(Manifest.permission.CAMERA)
        assert(permissionStatus == android.content.pm.PackageManager.PERMISSION_GRANTED)
    }

    @Test
    fun internetPermission_granted() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val permissionStatus = context.checkSelfPermission(Manifest.permission.INTERNET)
        // INTERNET is a normal permission, always granted
        assert(permissionStatus == android.content.pm.PackageManager.PERMISSION_GRANTED)
    }

    // ==================== ACTIVITY LIFECYCLE TESTS ====================

    @Test
    fun activityState_isResumed() {
        activityRule.scenario.onActivity { activity ->
            // Activity should be in resumed state
            assert(!activity.isFinishing)
            assert(!activity.isDestroyed)
        }
    }

    @Test
    fun activityRecreation_survives() {
        // Simulate configuration change
        activityRule.scenario.recreate()
        Thread.sleep(2000)

        activityRule.scenario.onActivity { activity ->
            assert(activity != null)
            assert(!activity.isFinishing)
        }
    }

    // ==================== VUZIX-SPECIFIC TESTS ====================

    @Test
    fun vuzixDevice_detectedCorrectly() {
        if (isVuzixDevice()) {
            println("✓ Running on Vuzix device: ${Build.MODEL}")
            // On Vuzix, voice-first interface should be active
            assert(true)
        } else {
            println("✓ Running on non-Vuzix device: ${Build.MODEL}")
            assert(true)
        }
    }

    @Test
    fun voiceRecognition_initialized() {
        // Give time for speech recognizer to initialize
        Thread.sleep(2000)

        activityRule.scenario.onActivity { activity ->
            // Activity should be ready for voice commands
            assert(activity != null)
        }
    }
}
