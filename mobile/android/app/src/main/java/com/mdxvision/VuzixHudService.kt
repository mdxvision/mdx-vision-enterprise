package com.mdxvision

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.graphics.PixelFormat
import android.os.Build
import android.os.IBinder
import android.util.Log
import android.view.Gravity
import android.view.WindowManager
import androidx.core.app.NotificationCompat
import androidx.localbroadcastmanager.content.LocalBroadcastManager
import org.json.JSONArray
import org.json.JSONObject

/**
 * VuzixHudService - Feature #73: Vuzix Blade 2 HUD Native Overlay
 *
 * Foreground Service that displays an always-on HUD overlay on Vuzix AR glasses.
 * Shows patient info, critical allergies, vitals, and medications.
 *
 * States:
 * - HIDDEN: HUD not visible
 * - COMPACT: Minimal view (320x180dp) - patient name, allergies, room
 * - EXPANDED: Full view (768x400dp) - complete patient details
 */
class VuzixHudService : Service() {

    companion object {
        private const val TAG = "VuzixHudService"
        private const val CHANNEL_ID = "mdx_hud_channel"
        private const val NOTIFICATION_ID = 73

        // Actions for controlling HUD from MainActivity
        const val ACTION_SHOW = "com.mdxvision.HUD_SHOW"
        const val ACTION_HIDE = "com.mdxvision.HUD_HIDE"
        const val ACTION_EXPAND = "com.mdxvision.HUD_EXPAND"
        const val ACTION_MINIMIZE = "com.mdxvision.HUD_MINIMIZE"
        const val ACTION_TOGGLE = "com.mdxvision.HUD_TOGGLE"
        const val ACTION_UPDATE_PATIENT = "com.mdxvision.PATIENT_UPDATE"
        const val ACTION_MINERVA_ALERT = "com.mdxvision.MINERVA_ALERT"

        // Extra keys
        const val EXTRA_PATIENT_DATA = "patient_data"
        const val EXTRA_MINERVA_ALERT = "minerva_alert"
        const val EXTRA_MINERVA_CRITICAL = "minerva_critical"
    }

    enum class HudState {
        HIDDEN,
        COMPACT,
        EXPANDED
    }

    private var windowManager: WindowManager? = null
    private var hudView: VuzixHudView? = null
    private var currentState = HudState.HIDDEN
    private var currentPatientData: JSONObject? = null
    private var currentMinervaAlert: String? = null
    private var isMinervaAlertCritical: Boolean = false

    // Broadcast receiver for patient updates and HUD commands
    private val hudReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) {
            when (intent?.action) {
                ACTION_UPDATE_PATIENT -> {
                    val dataString = intent.getStringExtra(EXTRA_PATIENT_DATA)
                    if (dataString != null) {
                        try {
                            currentPatientData = JSONObject(dataString)
                            updateHudContent()
                        } catch (e: Exception) {
                            Log.e(TAG, "Error parsing patient data: ${e.message}")
                        }
                    }
                }
                ACTION_MINERVA_ALERT -> {
                    val alertText = intent.getStringExtra(EXTRA_MINERVA_ALERT)
                    val isCritical = intent.getBooleanExtra(EXTRA_MINERVA_CRITICAL, false)
                    showMinervaAlert(alertText, isCritical)
                }
                ACTION_SHOW -> showHud()
                ACTION_HIDE -> hideHud()
                ACTION_EXPAND -> expandHud()
                ACTION_MINIMIZE -> minimizeHud()
                ACTION_TOGGLE -> toggleHud()
            }
        }
    }

    override fun onCreate() {
        super.onCreate()
        Log.d(TAG, "VuzixHudService created")

        windowManager = getSystemService(WINDOW_SERVICE) as WindowManager
        createNotificationChannel()

        // Register broadcast receiver
        val filter = IntentFilter().apply {
            addAction(ACTION_UPDATE_PATIENT)
            addAction(ACTION_MINERVA_ALERT)
            addAction(ACTION_SHOW)
            addAction(ACTION_HIDE)
            addAction(ACTION_EXPAND)
            addAction(ACTION_MINIMIZE)
            addAction(ACTION_TOGGLE)
        }
        LocalBroadcastManager.getInstance(this).registerReceiver(hudReceiver, filter)
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        Log.d(TAG, "VuzixHudService started with action: ${intent?.action}")

        // Start as foreground service
        startForeground(NOTIFICATION_ID, createNotification())

        // Handle action if provided
        intent?.action?.let { action ->
            when (action) {
                ACTION_SHOW -> showHud()
                ACTION_HIDE -> hideHud()
                ACTION_EXPAND -> expandHud()
                ACTION_MINIMIZE -> minimizeHud()
                ACTION_TOGGLE -> toggleHud()
                ACTION_UPDATE_PATIENT -> {
                    val dataString = intent.getStringExtra(EXTRA_PATIENT_DATA)
                    if (dataString != null) {
                        try {
                            currentPatientData = JSONObject(dataString)
                            updateHudContent()
                        } catch (e: Exception) {
                            Log.e(TAG, "Error parsing patient data: ${e.message}")
                        }
                    }
                }
                ACTION_MINERVA_ALERT -> {
                    val alertText = intent.getStringExtra(EXTRA_MINERVA_ALERT)
                    val isCritical = intent.getBooleanExtra(EXTRA_MINERVA_CRITICAL, false)
                    showMinervaAlert(alertText, isCritical)
                }
            }
        }

        return START_STICKY
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onDestroy() {
        super.onDestroy()
        Log.d(TAG, "VuzixHudService destroyed")

        LocalBroadcastManager.getInstance(this).unregisterReceiver(hudReceiver)
        removeHudView()
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "MDx Vision HUD",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Persistent HUD overlay for AR glasses"
                setShowBadge(false)
            }

            val notificationManager = getSystemService(NotificationManager::class.java)
            notificationManager.createNotificationChannel(channel)
        }
    }

    private fun createNotification(): Notification {
        val pendingIntent = PendingIntent.getActivity(
            this,
            0,
            Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE
        )

        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("MDx Vision HUD Active")
            .setContentText("Patient info displayed on glasses")
            .setSmallIcon(android.R.drawable.ic_menu_view)
            .setOngoing(true)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .setContentIntent(pendingIntent)
            .build()
    }

    // ========== HUD State Management ==========

    private fun showHud() {
        if (currentState == HudState.HIDDEN) {
            currentState = HudState.COMPACT
            createHudView()
            Log.d(TAG, "HUD shown (compact)")
        }
    }

    private fun hideHud() {
        if (currentState != HudState.HIDDEN) {
            currentState = HudState.HIDDEN
            removeHudView()
            Log.d(TAG, "HUD hidden")
        }
    }

    private fun expandHud() {
        if (currentState == HudState.COMPACT) {
            currentState = HudState.EXPANDED
            updateHudLayout()
            Log.d(TAG, "HUD expanded")
        } else if (currentState == HudState.HIDDEN) {
            currentState = HudState.EXPANDED
            createHudView()
            Log.d(TAG, "HUD shown (expanded)")
        }
    }

    private fun minimizeHud() {
        if (currentState == HudState.EXPANDED) {
            currentState = HudState.COMPACT
            updateHudLayout()
            Log.d(TAG, "HUD minimized")
        }
    }

    private fun toggleHud() {
        when (currentState) {
            HudState.HIDDEN -> showHud()
            HudState.COMPACT -> expandHud()
            HudState.EXPANDED -> hideHud()
        }
    }

    /**
     * Show Minerva alert on the HUD - expands HUD and displays alert prominently.
     * Critical alerts are shown with red border, non-critical with amber.
     */
    private fun showMinervaAlert(alertText: String?, isCritical: Boolean) {
        if (alertText.isNullOrBlank()) {
            currentMinervaAlert = null
            isMinervaAlertCritical = false
            updateHudContent()
            return
        }

        currentMinervaAlert = alertText
        isMinervaAlertCritical = isCritical

        // Auto-expand HUD to show full alert
        if (currentState == HudState.HIDDEN) {
            currentState = HudState.EXPANDED
            createHudView()
        } else if (currentState == HudState.COMPACT) {
            currentState = HudState.EXPANDED
            updateHudLayout()
        }

        // Update HUD with Minerva alert
        hudView?.showMinervaAlert(alertText, isCritical)
        Log.d(TAG, "Minerva alert shown on HUD: critical=$isCritical")
    }

    /**
     * Clear Minerva alert from the HUD.
     */
    fun clearMinervaAlert() {
        currentMinervaAlert = null
        isMinervaAlertCritical = false
        hudView?.clearMinervaAlert()
        Log.d(TAG, "Minerva alert cleared from HUD")
    }

    // ========== HUD View Management ==========

    private fun createHudView() {
        if (hudView != null) {
            removeHudView()
        }

        hudView = VuzixHudView(this, currentState == HudState.EXPANDED)

        val params = createWindowParams()

        try {
            windowManager?.addView(hudView, params)
            updateHudContent()
        } catch (e: Exception) {
            Log.e(TAG, "Error adding HUD view: ${e.message}")
        }
    }

    private fun removeHudView() {
        hudView?.let {
            try {
                windowManager?.removeView(it)
            } catch (e: Exception) {
                Log.e(TAG, "Error removing HUD view: ${e.message}")
            }
            hudView = null
        }
    }

    private fun updateHudLayout() {
        hudView?.let {
            it.setExpanded(currentState == HudState.EXPANDED)

            val params = createWindowParams()
            try {
                windowManager?.updateViewLayout(it, params)
            } catch (e: Exception) {
                Log.e(TAG, "Error updating HUD layout: ${e.message}")
            }
        }
    }

    private fun createWindowParams(): WindowManager.LayoutParams {
        val isExpanded = currentState == HudState.EXPANDED

        // Vuzix Blade 2: 1280x720 display
        // Compact: 320x180dp (25% width)
        // Expanded: 768x400dp (60% width)
        val width = if (isExpanded) dpToPx(768) else dpToPx(320)
        val height = if (isExpanded) dpToPx(400) else dpToPx(180)

        return WindowManager.LayoutParams(
            width,
            height,
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O)
                WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
            else
                @Suppress("DEPRECATION")
                WindowManager.LayoutParams.TYPE_PHONE,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or
                    WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL or
                    WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS,
            PixelFormat.TRANSLUCENT
        ).apply {
            gravity = Gravity.TOP or Gravity.END
            x = dpToPx(16)
            y = dpToPx(16)
        }
    }

    private fun updateHudContent() {
        val patient = currentPatientData ?: return
        hudView?.updatePatientData(patient)
    }

    private fun dpToPx(dp: Int): Int {
        val density = resources.displayMetrics.density
        return (dp * density).toInt()
    }
}
