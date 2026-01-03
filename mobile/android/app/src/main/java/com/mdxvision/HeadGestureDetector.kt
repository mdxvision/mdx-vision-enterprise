package com.mdxvision

import android.content.Context
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.os.Handler
import android.os.Looper

/**
 * HeadGestureDetector - Feature #75
 * Detects head gestures (nod, shake, double nod) using gyroscope and accelerometer sensors
 * for hands-free interaction on Vuzix Blade 2 AR glasses.
 *
 * Gesture Mappings:
 * - Head Nod (Yes): X-axis rotation (pitch) - up-down motion
 * - Head Shake (No): Y-axis rotation (yaw) - left-right motion
 * - Double Nod: Two quick nods within 600ms - toggles HUD
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

        // State machine states
        private const val STATE_IDLE = 0
        private const val STATE_NOD_DOWN = 1
        private const val STATE_NOD_UP = 2
        private const val STATE_SHAKE_LEFT = 3
        private const val STATE_SHAKE_RIGHT = 4
        private const val STATE_SHAKE_LEFT2 = 5
    }

    // Sensor references
    private var sensorManager: SensorManager? = null
    private var gyroscope: Sensor? = null
    private var accelerometer: Sensor? = null

    // State tracking
    private var nodState = STATE_IDLE
    private var shakeState = STATE_IDLE
    private var lastNodTime = 0L
    private var lastShakeTime = 0L
    private var lastNodCompletionTime = 0L
    private var nodCount = 0
    private var gestureStartTime = 0L

    // Enable/disable control
    var isEnabled = true
        private set

    // Handler for timeout management
    private val handler = Handler(Looper.getMainLooper())
    private val resetNodStateRunnable = Runnable { resetNodState() }
    private val resetShakeStateRunnable = Runnable { resetShakeState() }

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
     * values[0] = X-axis (pitch) - nod detection
     * values[1] = Y-axis (yaw) - shake detection
     * values[2] = Z-axis (roll) - not used
     */
    private fun processGyroscopeData(event: SensorEvent) {
        val pitchVelocity = event.values[0]  // X-axis rotation (nod)
        val yawVelocity = event.values[1]    // Y-axis rotation (shake)
        val currentTime = System.currentTimeMillis()

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

    private fun resetNodState() {
        nodState = STATE_IDLE
        handler.removeCallbacks(resetNodStateRunnable)
    }

    private fun resetShakeState() {
        shakeState = STATE_IDLE
        handler.removeCallbacks(resetShakeStateRunnable)
    }

    /**
     * Get current gesture control status for voice feedback
     */
    fun getStatusDescription(): String {
        return if (isEnabled) {
            "Gesture control is enabled. Nod to confirm, shake to cancel."
        } else {
            "Gesture control is disabled."
        }
    }
}
