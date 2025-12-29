package com.mdxvision

import android.app.Application
import android.util.Log

/**
 * MDx Vision - Main Application
 * AR Smart Glasses Healthcare Documentation
 */
class MainApplication : Application() {

    companion object {
        private const val TAG = "MDxVisionApp"
    }

    override fun onCreate() {
        super.onCreate()
        Log.d(TAG, "MDx Vision Application starting...")
        Log.d(TAG, "Device: ${android.os.Build.MANUFACTURER} ${android.os.Build.MODEL}")
        Log.d(TAG, "Android Version: ${android.os.Build.VERSION.SDK_INT}")
    }
}
