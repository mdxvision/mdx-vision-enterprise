package com.mdxvision

import org.junit.Assert.*
import org.junit.Before
import org.junit.Test

/**
 * Unit tests for Head Gesture Detector (Features #75, #76)
 * Tests gesture detection state machine, thresholds, and cooldowns
 */
class HeadGestureDetectorTest {

    private lateinit var nodDetector: TestableNodDetector
    private lateinit var shakeDetector: TestableShakeDetector
    private lateinit var winkDetector: TestableWinkDetector

    @Before
    fun setUp() {
        nodDetector = TestableNodDetector()
        shakeDetector = TestableShakeDetector()
        winkDetector = TestableWinkDetector()
    }

    // ==================== NOD DETECTION TESTS ====================

    @Test
    fun `nod detector starts in IDLE state`() {
        assertEquals(NodState.IDLE, nodDetector.state)
    }

    @Test
    fun `downward rotation transitions from IDLE to DOWN`() {
        nodDetector.processGyro(2.0f, 0L)
        assertEquals(NodState.DOWN, nodDetector.state)
    }

    @Test
    fun `upward rotation after down transitions to UP`() {
        nodDetector.processGyro(2.0f, 0L)
        nodDetector.processGyro(-2.0f, 100L)
        assertEquals(NodState.UP, nodDetector.state)
    }

    @Test
    fun `complete nod gesture detected`() {
        nodDetector.processGyro(2.0f, 0L)
        nodDetector.processGyro(-2.0f, 150L)
        // State is UP, complete gesture
        nodDetector.finishGesture(200L)
        assertTrue(nodDetector.wasNodDetected)
    }

    @Test
    fun `rotation below threshold is ignored`() {
        nodDetector.processGyro(0.5f, 0L)
        assertEquals(NodState.IDLE, nodDetector.state)
    }

    @Test
    fun `gesture timeout resets state`() {
        nodDetector.processGyro(2.0f, 0L)
        nodDetector.checkTimeout(1000L)
        assertEquals(NodState.IDLE, nodDetector.state)
    }

    @Test
    fun `cooldown prevents rapid nod detection`() {
        // First nod
        nodDetector.processGyro(2.0f, 0L)
        nodDetector.processGyro(-2.0f, 100L)
        nodDetector.finishGesture(200L)
        assertTrue(nodDetector.wasNodDetected)

        nodDetector.wasNodDetected = false

        // Second attempt within cooldown
        nodDetector.processGyro(2.0f, 300L)
        assertEquals(NodState.IDLE, nodDetector.state)
    }

    @Test
    fun `nod after cooldown is detected`() {
        // First nod
        nodDetector.processGyro(2.0f, 0L)
        nodDetector.processGyro(-2.0f, 100L)
        nodDetector.finishGesture(200L)
        assertTrue(nodDetector.wasNodDetected)
        nodDetector.wasNodDetected = false

        // Second nod after cooldown expires (200 + 600 = 800ms)
        nodDetector.processGyro(2.0f, 850L)
        nodDetector.processGyro(-2.0f, 900L)
        nodDetector.finishGesture(950L)

        assertTrue(nodDetector.wasNodDetected)
    }

    // ==================== SHAKE DETECTION TESTS ====================

    @Test
    fun `shake detector starts in IDLE state`() {
        assertEquals(ShakeState.IDLE, shakeDetector.state)
    }

    @Test
    fun `left rotation transitions from IDLE to LEFT`() {
        shakeDetector.processGyro(2.5f, 0L)
        assertEquals(ShakeState.LEFT, shakeDetector.state)
    }

    @Test
    fun `right rotation after left transitions to RIGHT`() {
        shakeDetector.processGyro(2.5f, 0L)
        shakeDetector.processGyro(-2.5f, 100L)
        assertEquals(ShakeState.RIGHT, shakeDetector.state)
    }

    @Test
    fun `complete shake gesture (left-right-left) detected`() {
        shakeDetector.processGyro(2.5f, 0L)
        shakeDetector.processGyro(-2.5f, 100L)
        shakeDetector.processGyro(2.5f, 200L)
        shakeDetector.finishGesture(300L)
        assertTrue(shakeDetector.wasShakeDetected)
    }

    @Test
    fun `incomplete shake (only left-right) not detected`() {
        shakeDetector.processGyro(2.5f, 0L)
        shakeDetector.processGyro(-2.5f, 100L)
        shakeDetector.checkTimeout(1000L)
        assertFalse(shakeDetector.wasShakeDetected)
    }

    @Test
    fun `shake cooldown prevents rapid detection`() {
        // First shake
        shakeDetector.processGyro(2.5f, 0L)
        shakeDetector.processGyro(-2.5f, 100L)
        shakeDetector.processGyro(2.5f, 200L)
        shakeDetector.finishGesture(300L)
        assertTrue(shakeDetector.wasShakeDetected)

        shakeDetector.wasShakeDetected = false

        // Second shake too soon
        shakeDetector.processGyro(2.5f, 500L)
        assertEquals(ShakeState.IDLE, shakeDetector.state)
    }

    // ==================== WINK DETECTION TESTS (Feature #76) ====================

    @Test
    fun `wink detector starts in IDLE state`() {
        assertEquals(WinkState.IDLE, winkDetector.state)
    }

    @Test
    fun `small rotation in wink range transitions to DOWN`() {
        winkDetector.processGyro(1.0f, 0L)  // In range 0.8-1.5
        assertEquals(WinkState.DOWN, winkDetector.state)
    }

    @Test
    fun `complete wink gesture detected`() {
        winkDetector.processGyro(1.0f, 0L)   // Start wink
        winkDetector.processGyro(0.1f, 100L) // Return to neutral
        assertTrue(winkDetector.wasWinkDetected)
    }

    @Test
    fun `wink too slow is not detected`() {
        winkDetector.processGyro(1.0f, 0L)   // Start wink
        winkDetector.checkTimeout(250L)       // Exceeds 200ms
        assertEquals(WinkState.IDLE, winkDetector.state)
        assertFalse(winkDetector.wasWinkDetected)
    }

    @Test
    fun `rotation above wink max becomes nod not wink`() {
        winkDetector.processGyro(1.0f, 0L)   // Start in wink range
        winkDetector.processGyro(1.6f, 50L)  // Goes above wink max (1.5)
        assertEquals(WinkState.IDLE, winkDetector.state)
        assertFalse(winkDetector.wasWinkDetected)
    }

    @Test
    fun `rotation below wink min is ignored`() {
        winkDetector.processGyro(0.5f, 0L)   // Below 0.8 threshold
        assertEquals(WinkState.IDLE, winkDetector.state)
    }

    @Test
    fun `wink cooldown prevents rapid detection`() {
        // First wink
        winkDetector.processGyro(1.0f, 0L)
        winkDetector.processGyro(0.1f, 100L)
        assertTrue(winkDetector.wasWinkDetected)

        winkDetector.wasWinkDetected = false

        // Second wink too soon (within 300ms cooldown)
        winkDetector.processGyro(1.0f, 200L)
        assertEquals(WinkState.IDLE, winkDetector.state)
    }

    @Test
    fun `wink after cooldown is detected`() {
        // First wink at time 0
        winkDetector.processGyro(1.0f, 0L)
        winkDetector.processGyro(0.1f, 100L)
        assertTrue(winkDetector.wasWinkDetected)
        winkDetector.wasWinkDetected = false

        // Second wink after cooldown (100 + 300 = 400ms minimum)
        winkDetector.processGyro(1.0f, 450L)
        winkDetector.processGyro(0.1f, 500L)
        assertTrue(winkDetector.wasWinkDetected)
    }

    @Test
    fun `wink enable and disable toggle works`() {
        assertTrue(winkDetector.isEnabled)
        winkDetector.disable()
        assertFalse(winkDetector.isEnabled)
        winkDetector.enable()
        assertTrue(winkDetector.isEnabled)
    }

    @Test
    fun `disabled wink ignores input`() {
        winkDetector.disable()
        winkDetector.processGyro(1.0f, 0L)
        assertEquals(WinkState.IDLE, winkDetector.state)
    }

    // ==================== WINK THRESHOLD TESTS ====================

    @Test
    fun `wink min threshold is correct`() {
        assertEquals(0.8f, TestableWinkDetector.MIN_THRESHOLD, 0.01f)
    }

    @Test
    fun `wink max threshold is correct`() {
        assertEquals(1.5f, TestableWinkDetector.MAX_THRESHOLD, 0.01f)
    }

    @Test
    fun `wink max duration is 200ms`() {
        assertEquals(200L, TestableWinkDetector.MAX_DURATION_MS)
    }

    @Test
    fun `wink cooldown is 300ms`() {
        assertEquals(300L, TestableWinkDetector.COOLDOWN_MS)
    }

    // ==================== THRESHOLD TESTS ====================

    @Test
    fun `nod rotation threshold is correct`() {
        assertEquals(1.8f, TestableNodDetector.THRESHOLD, 0.01f)
    }

    @Test
    fun `shake rotation threshold is correct`() {
        assertEquals(2.0f, TestableShakeDetector.THRESHOLD, 0.01f)
    }

    @Test
    fun `gesture timeout is 800ms`() {
        assertEquals(800L, TestableNodDetector.TIMEOUT_MS)
    }

    @Test
    fun `nod cooldown is 600ms`() {
        assertEquals(600L, TestableNodDetector.COOLDOWN_MS)
    }

    @Test
    fun `shake cooldown is 700ms`() {
        assertEquals(700L, TestableShakeDetector.COOLDOWN_MS)
    }

    @Test
    fun `double nod window is 600ms`() {
        assertEquals(600L, TestableNodDetector.DOUBLE_NOD_WINDOW_MS)
    }

    // ==================== EDGE CASE TESTS ====================

    @Test
    fun `very fast gesture is still detected`() {
        nodDetector.processGyro(3.0f, 0L)
        nodDetector.processGyro(-3.0f, 50L)
        nodDetector.finishGesture(100L)
        assertTrue(nodDetector.wasNodDetected)
    }

    @Test
    fun `gesture at exact threshold is detected`() {
        nodDetector.processGyro(1.8f, 0L)
        nodDetector.processGyro(-1.8f, 100L)
        nodDetector.finishGesture(200L)
        assertTrue(nodDetector.wasNodDetected)
    }

    @Test
    fun `gesture just below threshold is not detected`() {
        nodDetector.processGyro(1.79f, 0L)
        assertEquals(NodState.IDLE, nodDetector.state)
    }

    @Test
    fun `enable and disable toggle works`() {
        assertTrue(nodDetector.isEnabled)
        nodDetector.disable()
        assertFalse(nodDetector.isEnabled)
        nodDetector.enable()
        assertTrue(nodDetector.isEnabled)
    }

    @Test
    fun `disabled gesture control ignores input`() {
        nodDetector.disable()
        nodDetector.processGyro(2.0f, 0L)
        assertEquals(NodState.IDLE, nodDetector.state)
    }
}

// ==================== TEST HELPER CLASSES ====================

enum class NodState { IDLE, DOWN, UP }
enum class ShakeState { IDLE, LEFT, RIGHT, LEFT2 }
enum class WinkState { IDLE, DOWN }

/**
 * Testable nod detector
 */
class TestableNodDetector {
    companion object {
        const val THRESHOLD = 1.8f
        const val TIMEOUT_MS = 800L
        const val COOLDOWN_MS = 600L
        const val DOUBLE_NOD_WINDOW_MS = 600L
    }

    var state = NodState.IDLE
    var wasNodDetected = false
    var wasDoubleNodDetected = false
    var isEnabled = true

    private var gestureStartTime = 0L
    private var lastGestureTime = 0L
    private var lastNodCompletionTime = 0L
    private var nodCount = 0

    fun processGyro(pitch: Float, time: Long) {
        if (!isEnabled) return
        // Only apply cooldown if a gesture was actually detected
        if (state == NodState.IDLE && lastGestureTime > 0 && time - lastGestureTime < COOLDOWN_MS) return

        when (state) {
            NodState.IDLE -> {
                if (pitch >= THRESHOLD) {
                    state = NodState.DOWN
                    gestureStartTime = time
                }
            }
            NodState.DOWN -> {
                if (pitch <= -THRESHOLD) {
                    state = NodState.UP
                }
            }
            NodState.UP -> { }
        }
    }

    fun checkTimeout(time: Long) {
        if (state != NodState.IDLE && time - gestureStartTime > TIMEOUT_MS) {
            state = NodState.IDLE
        }
    }

    fun finishGesture(time: Long) {
        if (state == NodState.UP) {
            wasNodDetected = true
            lastGestureTime = time

            if (time - lastNodCompletionTime < DOUBLE_NOD_WINDOW_MS) {
                nodCount++
                if (nodCount >= 2) {
                    wasDoubleNodDetected = true
                    nodCount = 0
                }
            } else {
                nodCount = 1
            }
            lastNodCompletionTime = time
        }
        state = NodState.IDLE
    }

    fun enable() { isEnabled = true }
    fun disable() { isEnabled = false }
}

/**
 * Testable shake detector
 */
class TestableShakeDetector {
    companion object {
        const val THRESHOLD = 2.0f
        const val TIMEOUT_MS = 800L
        const val COOLDOWN_MS = 700L
    }

    var state = ShakeState.IDLE
    var wasShakeDetected = false

    private var gestureStartTime = 0L
    private var lastGestureTime = 0L

    fun processGyro(yaw: Float, time: Long) {
        // Only apply cooldown if a gesture was actually detected
        if (state == ShakeState.IDLE && lastGestureTime > 0 && time - lastGestureTime < COOLDOWN_MS) return

        when (state) {
            ShakeState.IDLE -> {
                if (yaw >= THRESHOLD) {
                    state = ShakeState.LEFT
                    gestureStartTime = time
                }
            }
            ShakeState.LEFT -> {
                if (yaw <= -THRESHOLD) {
                    state = ShakeState.RIGHT
                }
            }
            ShakeState.RIGHT -> {
                if (yaw >= THRESHOLD) {
                    state = ShakeState.LEFT2
                }
            }
            ShakeState.LEFT2 -> { }
        }
    }

    fun checkTimeout(time: Long) {
        if (state != ShakeState.IDLE && time - gestureStartTime > TIMEOUT_MS) {
            state = ShakeState.IDLE
        }
    }

    fun finishGesture(time: Long) {
        if (state == ShakeState.LEFT2) {
            wasShakeDetected = true
            lastGestureTime = time
        }
        state = ShakeState.IDLE
    }
}

/**
 * Testable wink detector (Feature #76)
 */
class TestableWinkDetector {
    companion object {
        const val MIN_THRESHOLD = 0.8f
        const val MAX_THRESHOLD = 1.5f
        const val MAX_DURATION_MS = 200L
        const val COOLDOWN_MS = 300L
        const val RETURN_THRESHOLD = 0.3f
    }

    var state = WinkState.IDLE
    var wasWinkDetected = false
    var isEnabled = true

    private var winkStartTime = 0L
    private var lastWinkTime = 0L

    fun processGyro(pitch: Float, time: Long) {
        if (!isEnabled) return
        // Only apply cooldown if a wink was actually detected
        if (state == WinkState.IDLE && lastWinkTime > 0 && time - lastWinkTime < COOLDOWN_MS) return

        when (state) {
            WinkState.IDLE -> {
                if (pitch >= MIN_THRESHOLD && pitch < MAX_THRESHOLD) {
                    state = WinkState.DOWN
                    winkStartTime = time
                }
            }
            WinkState.DOWN -> {
                val duration = time - winkStartTime

                // Timeout - too slow
                if (duration > MAX_DURATION_MS) {
                    state = WinkState.IDLE
                    return
                }

                // If pitch goes above max, it's becoming a nod
                if (pitch >= MAX_THRESHOLD) {
                    state = WinkState.IDLE
                    return
                }

                // Quick return to neutral = wink detected
                if (Math.abs(pitch) < RETURN_THRESHOLD && duration >= 50L) {
                    wasWinkDetected = true
                    lastWinkTime = time
                    state = WinkState.IDLE
                }
            }
        }
    }

    fun checkTimeout(time: Long) {
        if (state != WinkState.IDLE && time - winkStartTime > MAX_DURATION_MS) {
            state = WinkState.IDLE
        }
    }

    fun enable() { isEnabled = true }
    fun disable() { isEnabled = false }
}
