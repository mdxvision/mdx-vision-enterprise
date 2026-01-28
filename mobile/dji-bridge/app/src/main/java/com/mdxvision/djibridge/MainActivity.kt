package com.mdxvision.djibridge

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Bundle
import android.util.Log
import android.widget.Button
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import com.mdxvision.djibridge.service.BridgeServerService
import dji.v5.common.error.IDJIError
import dji.v5.common.register.DJISDKInitEvent
import dji.v5.manager.SDKManager
import dji.v5.manager.interfaces.SDKManagerCallback

/**
 * MDx DJI Bridge - Main Activity
 *
 * Displays connection status and starts the HTTP bridge server.
 * This app runs on the DJI RC 2 controller or a phone connected to it.
 */
class MainActivity : AppCompatActivity() {

    companion object {
        private const val TAG = "MdxBridge"
        private const val PERMISSION_REQUEST_CODE = 1001

        private val REQUIRED_PERMISSIONS = arrayOf(
            Manifest.permission.BLUETOOTH,
            Manifest.permission.BLUETOOTH_ADMIN,
            Manifest.permission.ACCESS_FINE_LOCATION,
            Manifest.permission.ACCESS_COARSE_LOCATION,
            Manifest.permission.RECORD_AUDIO,
            Manifest.permission.CAMERA,
            Manifest.permission.WRITE_EXTERNAL_STORAGE,
            Manifest.permission.READ_EXTERNAL_STORAGE,
            Manifest.permission.READ_PHONE_STATE,
        )
    }

    // UI Elements
    private lateinit var statusText: TextView
    private lateinit var droneStatus: TextView
    private lateinit var serverStatus: TextView
    private lateinit var ipAddressText: TextView
    private lateinit var batteryText: TextView
    private lateinit var startServerBtn: Button
    private lateinit var stopServerBtn: Button

    // State
    private var isServerRunning = false
    private var isDroneConnected = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        initViews()
        checkPermissions()
    }

    private fun initViews() {
        statusText = findViewById(R.id.statusText)
        droneStatus = findViewById(R.id.droneStatus)
        serverStatus = findViewById(R.id.serverStatus)
        ipAddressText = findViewById(R.id.ipAddressText)
        batteryText = findViewById(R.id.batteryText)
        startServerBtn = findViewById(R.id.startServerBtn)
        stopServerBtn = findViewById(R.id.stopServerBtn)

        startServerBtn.setOnClickListener { startBridgeServer() }
        stopServerBtn.setOnClickListener { stopBridgeServer() }

        updateUI()
    }

    private fun checkPermissions() {
        val missingPermissions = REQUIRED_PERMISSIONS.filter {
            ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED
        }

        if (missingPermissions.isNotEmpty()) {
            ActivityCompat.requestPermissions(
                this,
                missingPermissions.toTypedArray(),
                PERMISSION_REQUEST_CODE
            )
        } else {
            initDJISDK()
        }
    }

    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == PERMISSION_REQUEST_CODE) {
            if (grantResults.all { it == PackageManager.PERMISSION_GRANTED }) {
                initDJISDK()
            } else {
                statusText.text = "Permissions required"
            }
        }
    }

    private fun initDJISDK() {
        statusText.text = "Initializing DJI SDK..."
        Log.d(TAG, "Initializing DJI SDK")

        SDKManager.getInstance().init(this, object : SDKManagerCallback {
            override fun onRegisterSuccess() {
                Log.d(TAG, "DJI SDK registered successfully")
                runOnUiThread {
                    statusText.text = "SDK Ready"
                    checkDroneConnection()
                }
            }

            override fun onRegisterFailure(error: IDJIError?) {
                Log.e(TAG, "DJI SDK registration failed: ${error?.description()}")
                runOnUiThread {
                    statusText.text = "SDK Error: ${error?.description()}"
                }
            }

            override fun onProductDisconnect(productId: Int) {
                Log.d(TAG, "Drone disconnected")
                runOnUiThread {
                    isDroneConnected = false
                    updateUI()
                }
            }

            override fun onProductConnect(productId: Int) {
                Log.d(TAG, "Drone connected: $productId")
                runOnUiThread {
                    isDroneConnected = true
                    updateUI()
                }
            }

            override fun onProductChanged(productId: Int) {
                Log.d(TAG, "Product changed: $productId")
            }

            override fun onInitProcess(event: DJISDKInitEvent?, totalProcess: Int) {
                Log.d(TAG, "Init process: $event ($totalProcess%)")
                runOnUiThread {
                    statusText.text = "Initializing... $totalProcess%"
                }
            }

            override fun onDatabaseDownloadProgress(current: Long, total: Long) {
                // Database update progress
            }
        })
    }

    private fun checkDroneConnection() {
        // Check if aircraft is connected
        val aircraft = SDKManager.getInstance().product
        isDroneConnected = aircraft != null
        updateUI()

        if (isDroneConnected) {
            Log.d(TAG, "Aircraft detected: ${aircraft?.model}")
        }
    }

    private fun startBridgeServer() {
        Log.d(TAG, "Starting bridge server...")

        val intent = Intent(this, BridgeServerService::class.java)
        ContextCompat.startForegroundService(this, intent)

        isServerRunning = true
        updateUI()
    }

    private fun stopBridgeServer() {
        Log.d(TAG, "Stopping bridge server...")

        val intent = Intent(this, BridgeServerService::class.java)
        stopService(intent)

        isServerRunning = false
        updateUI()
    }

    private fun updateUI() {
        // Drone status
        droneStatus.text = if (isDroneConnected) {
            "DJI Air 3: Connected"
        } else {
            "DJI Air 3: Not Connected"
        }
        droneStatus.setTextColor(
            getColor(if (isDroneConnected) android.R.color.holo_green_light else android.R.color.holo_red_light)
        )

        // Server status
        serverStatus.text = if (isServerRunning) {
            "Bridge Server: Running"
        } else {
            "Bridge Server: Stopped"
        }
        serverStatus.setTextColor(
            getColor(if (isServerRunning) android.R.color.holo_green_light else android.R.color.holo_orange_light)
        )

        // IP Address
        val ip = getLocalIpAddress()
        ipAddressText.text = "API: http://$ip:8080"

        // Buttons
        startServerBtn.isEnabled = !isServerRunning
        stopServerBtn.isEnabled = isServerRunning
    }

    private fun getLocalIpAddress(): String {
        try {
            val interfaces = java.net.NetworkInterface.getNetworkInterfaces()
            while (interfaces.hasMoreElements()) {
                val iface = interfaces.nextElement()
                val addresses = iface.inetAddresses
                while (addresses.hasMoreElements()) {
                    val addr = addresses.nextElement()
                    if (!addr.isLoopbackAddress && addr is java.net.Inet4Address) {
                        return addr.hostAddress ?: "unknown"
                    }
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error getting IP: ${e.message}")
        }
        return "unknown"
    }

    override fun onDestroy() {
        super.onDestroy()
        if (isServerRunning) {
            stopBridgeServer()
        }
    }
}
