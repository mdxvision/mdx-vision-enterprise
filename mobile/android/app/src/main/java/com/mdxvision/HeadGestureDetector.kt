package com.mdxvision

import android.content.Context
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.os.Handler
import android.os.Looper

/**
 * HeadGestureDetector - Features #75, #76
 * Detects head gestures (nod, shake, double nod, wink) using gyroscope and accelerometer sensors
 * for hands-free interaction on Vuzix Blade 2 AR glasses.
 *
 * Gesture Mappings:
 * - Head Nod (Yes): X-axis rotation (pitch) - up-down motion (1.8+ rad/s)
 * - Head Shake (No): Y-axis rotation (yaw) - left-right motion (2.0+ rad/s)
 * - Double Nod: Two quick nods within 600ms - toggles HUD
 * - Wink (micro-tilt): Quick small head dip (0.8-1.5 rad/s, <200ms) - select/dismiss
 *
 * Uses state machine pattern for reliable gesture recognition with cooldown
 * timers to prevent false positives from normal head movement.
 */
class HeadGestureDetector(
    private val context: Context,
    private val listener: GestureListener
) : SensorEventListener {

    /**
     * Callback interface for gesture events
     */
    interface GestureListener {
        fun onHeadNod()      // Yes gesture - confirm action
        fun onHeadShake()    // No gesture - cancel action
        fun onDoubleNod()    // Toggle HUD visibility
        fun onWink()         // Quick select/dismiss gesture
    }

    companion object {
        // Detection thresholds (rad/s for gyroscope)
        private const val NOD_ROTATION_THRESHOLD = 1.8f      // Pitch velocity for nod
        private const val SHAKE_ROTATION_THRESHOLD = 2.0f    // Yaw velocity for shake
        private const val GESTURE_TIMEOUT_MS = 800L          // Max time to complete gesture
        private const val NOD_COOLDOWN_MS = 600L             // Cooldown between nod detections
        private const val SHAKE_COOLDOWN_MS = 700L           // Cooldown between shake detections
        private const val DOUBLE_NOD_WINDOW_MS = 600L        // Time window for double nod
        private const val MIN_GESTURE_DURATION_MS = 100L     // Minimum gesture duration

        // Wink detection thresholds (Feature #76)
        private const val WINK_MIN_THRESHOLD = 0.8f          // Lower bound for wink
        private const val WINK_MAX_THRESHOLD = 1.5f          // Upper bound (above = nod)
        private const val WINK_MAX_DURATION_MS = 200L        // Must be quick
        private const val WINK_COOLDOWN_MS = 300L            // Fast repeat allowed
        private const val WINK_RETURN_THRESHOLD = 0.3f       // Return to neutral threshold

        // State machine states
        private const val STATE_IDLE = 0
        private const val STATE_NOD_DOWN = 1
        private const val STATE_NOD_UP = 2
        private const val STATE_SHAKE_LEFT = 3
        private const val STATE_SHAKE_RIGHT = 4
        private const val STATE_SHAKE_LEFT2 = 5
        private const val STATE_WINK_DOWN = 6
    }

    // Sensor references
    private var sensorManager: SensorManager? = null
    private var gyroscope: Sensor? = null
    private var accelerometer: Sensor? = null

    // State tracking
    private var nodState = STATE_IDLE
    private var shakeState = STATE_IDLE
    private var winkState = STATE_IDLE
    private var lastNodTime = 0L
    private var lastShakeTime = 0L
    private var lastWinkTime = 0L
    private var lastNodCompletionTime = 0L
    private var nodCount = 0
    private var gestureStartTime = 0L
    private var winkStartTime = 0L

    // Enable/disable control
    var isEnabled = true
        private set
    var isWinkEnabled = true
        private set

    // Handler for timeout management
    private val handler = Handler(Looper.getMainLooper())
    private val resetNodStateRunnable = Runnable { resetNodState() }
    private val resetShakeStateRunnable = Runnable { resetShakeState() }
    private val resetWinkStateRunnable = Runnable { resetWinkState() }

    /**
     * Initialize sensors
     */
    fun initialize() {
        sensorManager = context.getSystemService(Context.SENSOR_SERVICE) as SensorManager
        gyroscope = sensorManager?.getDefaultSensor(Sensor.TYPE_GYROSCOPE)
        accelerometer = sensorManager?.getDefaultSensor(Sensor.TYPE_ACCELEROMETER)
    }

    /**
     * Start gesture detection - call in onResume
     */
    fun startDetection() {
        if (!isEnabled) return

        gyroscope?.let {
            sensorManager?.registerListener(this, it, SensorManager.SENSOR_DELAY_GAME)
        }
        accelerometer?.let {
            sensorManager?.registerListener(this, it, SensorManager.SENSOR_DELAY_GAME)
        }
    }

    /**
     * Stop gesture detection - call in onPause
     */
    fun stopDetection() {
        sensorManager?.unregisterListener(this)
        handler.removeCallbacksAndMessages(null)
        resetNodState()
        resetShakeState()
        resetWinkState()
    }

    /**
     * Enable gesture control
     */
    fun enable() {
        isEnabled = true
        startDetection()
    }

    /**
     * Disable gesture control
     */
    fun disable() {
        isEnabled = false
        stopDetection()
    }

    /**
     * Enable wink detection
     */
    fun enableWink() {
        isWinkEnabled = true
    }

    /**
     * Disable wink detection
     */
    fun disableWink() {
        isWinkEnabled = false
        resetWinkState()
    }

    override fun onSensorChanged(event: SensorEvent) {
        if (!isEnabled) return

        when (event.sensor.type) {
            Sensor.TYPE_GYROSCOPE -> processGyroscopeData(event)
            Sensor.TYPE_ACCELEROMETER -> processAccelerometerData(event)
        }
    }

    override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) {
        // Not used
    }

    /**
     * Process gyroscope data for gesture detection
     * values[0] = X-axis (pitch) - nod/wink detection
     * values[1] = Y-axis (yaw) - shake detection
     * values[2] = Z-axis (roll) - not used
     */
    private fun processGyroscopeData(event: SensorEvent) {
        val pitchVelocity = event.values[0]  // X-axis rotation (nod/wink)
        val yawVelocity = event.values[1]    // Y-axis rotation (shake)
        val currentTime = System.currentTimeMillis()

        // Detect wink (quick micro-tilt) - check first, before nod
        if (isWinkEnabled) {
            detectWink(pitchVelocity, currentTime)
        }

        // Detect head nod (pitch - up/down motion)
        detectNod(pitchVelocity, currentTime)

        // Detect head shake (yaw - left/right motion)
        detectShake(yawVelocity, currentTime)
    }

    /**
     * Process accelerometer data for validation
     */
    private fun processAccelerometerData(event: SensorEvent) {
        // Accelerometer used for future validation/filtering
        // Currently gyroscope provides sufficient accuracy
    }

    /**
     * Detect head nod gesture using state machine
     * Pattern: DOWN -> UP (single nod)
     */
    private fun detectNod(pitchVelocity: Float, currentTime: Long) {
        // Check cooldown
        if (currentTime - lastNodTime < NOD_COOLDOWN_MS) return

        when (nodState) {
            STATE_IDLE -> {
                // Looking for downward rotation (positive pitch)
                if (pitchVelocity > NOD_ROTATION_THRESHOLD) {
                    nodState = STATE_NOD_DOWN
                    gestureStartTime = currentTime
                    scheduleNodReset()
                }
            }
            STATE_NOD_DOWN -> {
                // Check for timeout
                if (currentTime - gestureStartTime > GESTURE_TIMEOUT_MS) {
                    resetNodState()
                    return
                }
                // Looking for upward rotation (negative pitch)
                if (pitchVelocity < -NOD_ROTATION_THRESHOLD) {
                    nodState = STATE_NOD_UP
                }
            }
            STATE_NOD_UP -> {
                // Check minimum duration
                if (currentTime - gestureStartTime >= MIN_GESTURE_DURATION_MS) {
                    // Nod detected!
                    handleNodDetected(currentTime)
                }
                resetNodState()
            }
        }
    }

    /**
     * Detect wink gesture (quick micro-tilt) using state machine
     * Pattern: Small DOWN (0.8-1.5 rad/s) -> Return to neutral (<200ms)
     * Must be faster and smaller than full nod
     */
    private fun detectWink(pitchVelocity: Float, currentTime: Long) {
        // Check cooldown
        if (lastWinkTime > 0 && currentTime - lastWinkTime < WINK_COOLDOWN_MS) return

        // Don't detect wink if nod is already in progress
        if (nodState != STATE_IDLE) return

        when (winkState) {
            STATE_IDLE -> {
                // Looking for small downward rotation (in wink range, below nod threshold)
                if (pitchVelocity > WINK_MIN_THRESHOLD && pitchVelocity < WINK_MAX_THRESHOLD) {
                    winkState = STATE_WINK_DOWN
                    winkStartTime = currentTime
                    scheduleWinkReset()
                }
            }
            STATE_WINK_DOWN -> {
                val duration = currentTime - winkStartTime

                // Timeout - too slow, might be starting a nod
                if (duration > WINK_MAX_DURATION_MS) {
                    resetWinkState()
                    return
                }

                // If velocity goes above wink max, it's becoming a nod - abort
                if (pitchVelocity > WINK_MAX_THRESHOLD) {
                    resetWinkState()
                    return
                }

                // Quick return to neutral = wink detected
                if (Math.abs(pitchVelocity) < WINK_RETURN_THRESHOLD && duration >= 50L) {
                    lastWinkTime = currentTime
                    listener.onWink()
                    resetWinkState()
                }
            }
        }
    }

    /**
     * Handle nod detection - check for double nod
     */
    private fun handleNodDetected(currentTime: Long) {
        lastNodTime = currentTime

        // Check for double nod
        if (currentTime - lastNodCompletionTime < DOUBLE_NOD_WINDOW_MS) {
            nodCount++
            if (nodCount >= 2) {
                // Double nod detected!
                nodCount = 0
                lastNodCompletionTime = 0L
                listener.onDoubleNod()
                return
            }
        } else {
            nodCount = 1
        }

        lastNodCompletionTime = currentTime

        // Delay single nod callback to check for double nod
        handler.postDelayed({
            if (nodCount == 1 && currentTime == lastNodCompletionTime) {
                nodCount = 0
                listener.onHeadNod()
            }
        }, DOUBLE_NOD_WINDOW_MS)
    }

    /**
     * Detect head shake gesture using state machine
     * Pattern: LEFT -> RIGHT -> LEFT (shake motion)
     */
    private fun detectShake(yawVelocity: Float, currentTime: Long) {
        // Check cooldown
        if (currentTime - lastShakeTime < SHAKE_COOLDOWN_MS) return

        when (shakeState) {
            STATE_IDLE -> {
                // Looking for left rotation (positive yaw)
                if (yawVelocity > SHAKE_ROTATION_THRESHOLD) {
                    shakeState = STATE_SHAKE_LEFT
                    gestureStartTime = currentTime
                    scheduleShakeReset()
                }
            }
            STATE_SHAKE_LEFT -> {
                // Check for timeout
                if (currentTime - gestureStartTime > GESTURE_TIMEOUT_MS) {
                    resetShakeState()
                    return
                }
                // Looking for right rotation (negative yaw)
                if (yawVelocity < -SHAKE_ROTATION_THRESHOLD) {
                    shakeState = STATE_SHAKE_RIGHT
                }
            }
            STATE_SHAKE_RIGHT -> {
                // Check for timeout
                if (currentTime - gestureStartTime > GESTURE_TIMEOUT_MS) {
                    resetShakeState()
                    return
                }
                // Looking for left rotation again (positive yaw)
                if (yawVelocity > SHAKE_ROTATION_THRESHOLD) {
                    shakeState = STATE_SHAKE_LEFT2
                }
            }
            STATE_SHAKE_LEFT2 -> {
                // Check minimum duration
                if (currentTime - gestureStartTime >= MIN_GESTURE_DURATION_MS) {
                    // Shake detected!
                    lastShakeTime = currentTime
                    listener.onHeadShake()
                }
                resetShakeState()
            }
        }
    }

    private fun scheduleNodReset() {
        handler.removeCallbacks(resetNodStateRunnable)
        handler.postDelayed(resetNodStateRunnable, GESTURE_TIMEOUT_MS)
    }

    private fun scheduleShakeReset() {
        handler.removeCallbacks(resetShakeStateRunnable)
        handler.postDelayed(resetShakeStateRunnable, GESTURE_TIMEOUT_MS)
    }

    private fun scheduleWinkReset() {
        handler.removeCallbacks(resetWinkStateRunnable)
        handler.postDelayed(resetWinkStateRunnable, WINK_MAX_DURATION_MS)
    }

    private fun resetNodState() {
        nodState = STATE_IDLE
        handler.removeCallbacks(resetNodStateRunnable)
    }

    private fun resetShakeState() {
        shakeState = STATE_IDLE
        handler.removeCallbacks(resetShakeStateRunnable)
    }

    private fun resetWinkState() {
        winkState = STATE_IDLE
        handler.removeCallbacks(resetWinkStateRunnable)
    }

    /**
     * Get current gesture control status for voice feedback
     */
    fun getStatusDescription(): String {
        return if (isEnabled) {
            val winkStatus = if (isWinkEnabled) "Wink to select." else ""
            "Gesture control is enabled. Nod to confirm, shake to cancel. $winkStatus".trim()
        } else {
            "Gesture control is disabled."
        }
    }

    /**
     * Get wink-specific status
     */
    fun getWinkStatusDescription(): String {
        return if (isWinkEnabled) {
            "Wink detection is enabled. Quick head dip to select."
        } else {
            "Wink detection is disabled."
        }
    }
}
