package com.mdxvision.drone

import android.content.Context
import android.content.SharedPreferences

/**
 * Feature flag for Drone Voice Control
 *
 * Default: OFF (false)
 *
 * To enable:
 * 1. Via ADB: adb shell "run-as com.mdxvision sh -c 'echo true > /data/data/com.mdxvision/shared_prefs/drone_feature_flag'"
 * 2. Via code: DroneFeatureFlag.setEnabled(context, true)
 * 3. Triple-tap on version text in MainActivity (if implemented)
 *
 * Storage: SharedPreferences "drone_feature"
 */
object DroneFeatureFlag {
    private const val PREFS_NAME = "drone_feature"
    private const val KEY_ENABLED = "drone_control_enabled"

    // Default OFF for safety
    private const val DEFAULT_ENABLED = false

    private fun getPrefs(context: Context): SharedPreferences {
        return context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
    }

    /**
     * Check if drone control feature is enabled
     */
    fun isEnabled(context: Context): Boolean {
        return getPrefs(context).getBoolean(KEY_ENABLED, DEFAULT_ENABLED)
    }

    /**
     * Enable or disable drone control feature
     */
    fun setEnabled(context: Context, enabled: Boolean) {
        getPrefs(context).edit().putBoolean(KEY_ENABLED, enabled).apply()
    }

    /**
     * Toggle drone control feature
     * @return new enabled state
     */
    fun toggle(context: Context): Boolean {
        val newState = !isEnabled(context)
        setEnabled(context, newState)
        return newState
    }

    /**
     * Reset to default (disabled)
     */
    fun reset(context: Context) {
        getPrefs(context).edit().remove(KEY_ENABLED).apply()
    }
}
