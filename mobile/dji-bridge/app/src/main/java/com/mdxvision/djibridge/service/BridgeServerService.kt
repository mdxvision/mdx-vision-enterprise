package com.mdxvision.djibridge.service

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Intent
import android.os.Build
import android.os.IBinder
import android.util.Log
import androidx.core.app.NotificationCompat
import com.google.gson.Gson
import com.mdxvision.djibridge.R
import com.mdxvision.djibridge.drone.DroneController
import fi.iki.elonen.NanoHTTPD
import java.io.IOException

/**
 * MDx Bridge HTTP Server Service
 *
 * Runs an embedded HTTP server that exposes drone control APIs.
 * Allows ehr-proxy to send voice commands to the drone.
 *
 * API Endpoints:
 * - GET  /api/status         - Get drone connection status
 * - POST /api/flight/takeoff - Takeoff
 * - POST /api/flight/land    - Land
 * - POST /api/flight/move    - Move in direction
 * - POST /api/flight/rotate  - Rotate drone
 * - POST /api/camera/photo   - Take photo
 * - POST /api/camera/zoom    - Set zoom level
 * - GET  /api/video/frame    - Get current video frame (base64)
 */
class BridgeServerService : Service() {

    companion object {
        private const val TAG = "BridgeServer"
        private const val PORT = 8080
        private const val CHANNEL_ID = "mdx_bridge_channel"
        private const val NOTIFICATION_ID = 1
    }

    private var httpServer: BridgeHttpServer? = null
    private val droneController = DroneController()
    private val gson = Gson()

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        Log.d(TAG, "Starting bridge server on port $PORT")

        // Start foreground service
        startForeground(NOTIFICATION_ID, createNotification())

        // Start HTTP server
        try {
            httpServer = BridgeHttpServer(PORT)
            httpServer?.start()
            Log.d(TAG, "Bridge server started successfully")
        } catch (e: IOException) {
            Log.e(TAG, "Failed to start server: ${e.message}")
            stopSelf()
        }

        return START_STICKY
    }

    override fun onDestroy() {
        super.onDestroy()
        httpServer?.stop()
        Log.d(TAG, "Bridge server stopped")
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "MDx Bridge Server",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Drone control bridge server"
            }
            val manager = getSystemService(NotificationManager::class.java)
            manager.createNotificationChannel(channel)
        }
    }

    private fun createNotification(): Notification {
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("MDx DJI Bridge")
            .setContentText("Bridge server running on port $PORT")
            .setSmallIcon(android.R.drawable.ic_menu_compass)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .build()
    }

    /**
     * Embedded HTTP Server using NanoHTTPD
     */
    inner class BridgeHttpServer(port: Int) : NanoHTTPD(port) {

        override fun serve(session: IHTTPSession): Response {
            val uri = session.uri
            val method = session.method

            Log.d(TAG, "Request: $method $uri")

            // Add CORS headers
            val response = when {
                // Status
                uri == "/api/status" && method == Method.GET -> handleStatus()

                // Flight control
                uri == "/api/flight/takeoff" && method == Method.POST -> handleTakeoff()
                uri == "/api/flight/land" && method == Method.POST -> handleLand()
                uri == "/api/flight/hover" && method == Method.POST -> handleHover()
                uri == "/api/flight/emergency_stop" && method == Method.POST -> handleEmergencyStop()
                uri == "/api/flight/rth" && method == Method.POST -> handleReturnHome()
                uri == "/api/flight/move" && method == Method.POST -> handleMove(session)
                uri == "/api/flight/rotate" && method == Method.POST -> handleRotate(session)
                uri == "/api/flight/set_speed" && method == Method.POST -> handleSetSpeed(session)
                uri == "/api/flight/speed_mode" && method == Method.POST -> handleSpeedMode(session)

                // Camera control
                uri == "/api/camera/photo" && method == Method.POST -> handlePhoto(session)
                uri == "/api/camera/record_start" && method == Method.POST -> handleRecordStart(session)
                uri == "/api/camera/record_stop" && method == Method.POST -> handleRecordStop()
                uri == "/api/camera/zoom" && method == Method.POST -> handleZoom(session)
                uri == "/api/camera/switch" && method == Method.POST -> handleSwitchCamera(session)

                // Gimbal
                uri == "/api/gimbal/pitch" && method == Method.POST -> handleGimbalPitch(session)

                // Status queries
                uri == "/api/status/battery" && method == Method.GET -> handleBattery()
                uri == "/api/status/altitude" && method == Method.GET -> handleAltitude()
                uri == "/api/status/gps" && method == Method.GET -> handleGPS()
                uri == "/api/status/signal" && method == Method.GET -> handleSignal()

                // Video
                uri == "/api/video/frame" && method == Method.GET -> handleVideoFrame()
                uri == "/api/video/start_stream" && method == Method.POST -> handleStartStream()

                // Tracking (for facial recognition follow)
                uri == "/api/tracking/start" && method == Method.POST -> handleStartTracking(session)

                else -> jsonResponse(mapOf("error" to "Unknown endpoint: $uri"), Response.Status.NOT_FOUND)
            }

            // Add CORS headers
            response.addHeader("Access-Control-Allow-Origin", "*")
            response.addHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            response.addHeader("Access-Control-Allow-Headers", "Content-Type")

            return response
        }

        private fun parseBody(session: IHTTPSession): Map<String, Any> {
            val files = HashMap<String, String>()
            session.parseBody(files)
            val body = files["postData"] ?: "{}"
            return try {
                gson.fromJson(body, Map::class.java) as Map<String, Any>
            } catch (e: Exception) {
                emptyMap()
            }
        }

        private fun jsonResponse(data: Any, status: Response.Status = Response.Status.OK): Response {
            val json = gson.toJson(data)
            return newFixedLengthResponse(status, "application/json", json)
        }

        // ═══════════════════════════════════════════════════════════════════
        // STATUS
        // ═══════════════════════════════════════════════════════════════════

        private fun handleStatus(): Response {
            val status = droneController.getStatus()
            return jsonResponse(status)
        }

        // ═══════════════════════════════════════════════════════════════════
        // FLIGHT CONTROL
        // ═══════════════════════════════════════════════════════════════════

        private fun handleTakeoff(): Response {
            val result = droneController.takeoff()
            return jsonResponse(result)
        }

        private fun handleLand(): Response {
            val result = droneController.land()
            return jsonResponse(result)
        }

        private fun handleHover(): Response {
            val result = droneController.hover()
            return jsonResponse(result)
        }

        private fun handleEmergencyStop(): Response {
            val result = droneController.emergencyStop()
            return jsonResponse(result)
        }

        private fun handleReturnHome(): Response {
            val result = droneController.returnToHome()
            return jsonResponse(result)
        }

        private fun handleMove(session: IHTTPSession): Response {
            val body = parseBody(session)
            val direction = body["direction"] as? Map<String, Any> ?: emptyMap()
            val distance = (body["distance_meters"] as? Number)?.toFloat() ?: 1f

            val result = droneController.move(
                pitch = (direction["pitch"] as? Number)?.toFloat() ?: 0f,
                roll = (direction["roll"] as? Number)?.toFloat() ?: 0f,
                throttle = (direction["throttle"] as? Number)?.toFloat() ?: 0f,
                distanceMeters = distance
            )
            return jsonResponse(result)
        }

        private fun handleRotate(session: IHTTPSession): Response {
            val body = parseBody(session)
            val direction = body["direction"] as? String ?: "cw"
            val degrees = (body["degrees"] as? Number)?.toFloat() ?: 90f

            val result = droneController.rotate(direction, degrees)
            return jsonResponse(result)
        }

        private fun handleSetSpeed(session: IHTTPSession): Response {
            val body = parseBody(session)
            val speed = (body["speed_ms"] as? Number)?.toFloat() ?: 5f

            val result = droneController.setSpeed(speed)
            return jsonResponse(result)
        }

        private fun handleSpeedMode(session: IHTTPSession): Response {
            val body = parseBody(session)
            val mode = body["mode"] as? String ?: "normal"

            val result = droneController.setSpeedMode(mode)
            return jsonResponse(result)
        }

        // ═══════════════════════════════════════════════════════════════════
        // CAMERA CONTROL
        // ═══════════════════════════════════════════════════════════════════

        private fun handlePhoto(session: IHTTPSession): Response {
            val body = parseBody(session)
            val camera = body["camera"] as? String ?: "wide"

            val result = droneController.takePhoto(camera)
            return jsonResponse(result)
        }

        private fun handleRecordStart(session: IHTTPSession): Response {
            val body = parseBody(session)
            val camera = body["camera"] as? String ?: "wide"

            val result = droneController.startRecording(camera)
            return jsonResponse(result)
        }

        private fun handleRecordStop(): Response {
            val result = droneController.stopRecording()
            return jsonResponse(result)
        }

        private fun handleZoom(session: IHTTPSession): Response {
            val body = parseBody(session)
            val level = (body["level"] as? Number)?.toFloat() ?: 1f
            val camera = body["camera"] as? String ?: "wide"

            val result = droneController.setZoom(level, camera)
            return jsonResponse(result)
        }

        private fun handleSwitchCamera(session: IHTTPSession): Response {
            val body = parseBody(session)
            val camera = body["camera"] as? String ?: "wide"

            val result = droneController.switchCamera(camera)
            return jsonResponse(result)
        }

        // ═══════════════════════════════════════════════════════════════════
        // GIMBAL
        // ═══════════════════════════════════════════════════════════════════

        private fun handleGimbalPitch(session: IHTTPSession): Response {
            val body = parseBody(session)
            val angle = (body["angle"] as? Number)?.toFloat() ?: 0f

            val result = droneController.setGimbalPitch(angle)
            return jsonResponse(result)
        }

        // ═══════════════════════════════════════════════════════════════════
        // STATUS QUERIES
        // ═══════════════════════════════════════════════════════════════════

        private fun handleBattery(): Response {
            val battery = droneController.getBattery()
            return jsonResponse(mapOf("success" to true, "battery" to battery))
        }

        private fun handleAltitude(): Response {
            val altitude = droneController.getAltitude()
            return jsonResponse(mapOf("success" to true, "altitude" to altitude))
        }

        private fun handleGPS(): Response {
            val gps = droneController.getGPS()
            return jsonResponse(mapOf("success" to true, "lat" to gps.first, "lon" to gps.second))
        }

        private fun handleSignal(): Response {
            val signal = droneController.getSignalStrength()
            return jsonResponse(mapOf("success" to true, "signal" to signal))
        }

        // ═══════════════════════════════════════════════════════════════════
        // VIDEO
        // ═══════════════════════════════════════════════════════════════════

        private fun handleVideoFrame(): Response {
            val frame = droneController.getCurrentFrameBase64()
            return if (frame != null) {
                jsonResponse(mapOf("success" to true, "frame_base64" to frame))
            } else {
                jsonResponse(mapOf("success" to false, "message" to "No video frame available"))
            }
        }

        private fun handleStartStream(): Response {
            val result = droneController.startVideoStream()
            return jsonResponse(result)
        }

        // ═══════════════════════════════════════════════════════════════════
        // TRACKING (for facial recognition follow)
        // ═══════════════════════════════════════════════════════════════════

        private fun handleStartTracking(session: IHTTPSession): Response {
            val body = parseBody(session)
            val bbox = body["bbox"] as? List<Number> ?: listOf(0, 0, 100, 100)
            val mode = body["mode"] as? String ?: "trace"

            val result = droneController.startTracking(
                x = bbox[0].toInt(),
                y = bbox[1].toInt(),
                width = bbox[2].toInt(),
                height = bbox[3].toInt(),
                mode = mode
            )
            return jsonResponse(result)
        }
    }
}
