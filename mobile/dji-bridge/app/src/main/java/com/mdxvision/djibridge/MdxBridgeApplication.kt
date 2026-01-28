package com.mdxvision.djibridge

import android.app.Application
import android.content.Context
import android.util.Log

/**
 * MDx DJI Bridge Application
 *
 * Initializes DJI SDK and manages drone connection.
 */
class MdxBridgeApplication : Application() {

    companion object {
        private const val TAG = "MdxBridgeApp"

        @Volatile
        private var instance: MdxBridgeApplication? = null

        fun getInstance(): MdxBridgeApplication {
            return instance ?: throw IllegalStateException("Application not initialized")
        }
    }

    override fun attachBaseContext(base: Context?) {
        super.attachBaseContext(base)
        instance = this
    }

    override fun onCreate() {
        super.onCreate()
        Log.d(TAG, "MDx DJI Bridge starting...")

        // DJI SDK initialization happens in MainActivity after permissions
    }
}
