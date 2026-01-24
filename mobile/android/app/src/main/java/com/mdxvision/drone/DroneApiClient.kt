package com.mdxvision.drone

import android.util.Log
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.util.concurrent.TimeUnit

/**
 * Drone Voice Control - API Client
 * Handles communication with ehr-proxy drone endpoints.
 *
 * Follows existing OkHttp patterns from MainActivity.
 */
class DroneApiClient(
    private var baseUrl: String = DEFAULT_BASE_URL
) {
    companion object {
        private const val TAG = "DroneApiClient"
        private const val DEFAULT_BASE_URL = "http://10.251.30.181:8002"
        private val JSON_MEDIA_TYPE = "application/json; charset=utf-8".toMediaType()

        // Singleton instance for shared use
        @Volatile
        private var instance: DroneApiClient? = null

        fun getInstance(baseUrl: String = DEFAULT_BASE_URL): DroneApiClient {
            return instance ?: synchronized(this) {
                instance ?: DroneApiClient(baseUrl).also { instance = it }
            }
        }

        fun setBaseUrl(url: String) {
            instance?.baseUrl = url.trimEnd('/')
        }
    }

    private val httpClient = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(60, TimeUnit.SECONDS)
        .writeTimeout(30, TimeUnit.SECONDS)
        .retryOnConnectionFailure(true)
        .build()

    /**
     * GET /api/drone/status
     * Check if drone control is enabled on server
     */
    suspend fun getStatus(): Result<DroneStatus> = withContext(Dispatchers.IO) {
        try {
            val request = Request.Builder()
                .url("$baseUrl/api/drone/status")
                .get()
                .build()

            val response = httpClient.newCall(request).execute()
            val body = response.body?.string() ?: "{}"

            Log.d(TAG, "Status response: $body")

            if (response.isSuccessful) {
                Result.success(DroneStatus.fromJson(JSONObject(body)))
            } else {
                // If endpoint returns disabled response
                val json = JSONObject(body)
                if (json.has("enabled") && !json.getBoolean("enabled")) {
                    Result.success(DroneStatus.fromJson(json))
                } else {
                    Result.failure(Exception("Status check failed: ${response.code}"))
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Status error: ${e.message}", e)
            Result.failure(e)
        }
    }

    /**
     * GET /api/drone/capabilities
     * Get adapter capabilities and supported intents
     */
    suspend fun getCapabilities(): Result<CapabilitiesResponse> = withContext(Dispatchers.IO) {
        try {
            val request = Request.Builder()
                .url("$baseUrl/api/drone/capabilities")
                .get()
                .build()

            val response = httpClient.newCall(request).execute()
            val body = response.body?.string() ?: "{}"

            Log.d(TAG, "Capabilities response: $body")

            if (response.isSuccessful) {
                val json = JSONObject(body)
                // Check if disabled
                if (json.has("enabled") && !json.getBoolean("enabled")) {
                    Result.failure(Exception(json.optString("message", "Drone control disabled")))
                } else {
                    Result.success(CapabilitiesResponse.fromJson(json))
                }
            } else {
                Result.failure(Exception("Capabilities fetch failed: ${response.code}"))
            }
        } catch (e: Exception) {
            Log.e(TAG, "Capabilities error: ${e.message}", e)
            Result.failure(e)
        }
    }

    /**
     * POST /api/drone/voice/parse
     * Parse voice transcript into intent and slots
     */
    suspend fun parse(
        transcript: String,
        sessionId: String
    ): Result<ParseResponse> = withContext(Dispatchers.IO) {
        try {
            val requestBody = JSONObject().apply {
                put("transcript", transcript)
                put("session_id", sessionId)
            }

            Log.d(TAG, "Parse request: $requestBody")

            val request = Request.Builder()
                .url("$baseUrl/api/drone/voice/parse")
                .post(requestBody.toString().toRequestBody(JSON_MEDIA_TYPE))
                .build()

            val response = httpClient.newCall(request).execute()
            val body = response.body?.string() ?: "{}"

            Log.d(TAG, "Parse response: $body")

            if (response.isSuccessful) {
                val json = JSONObject(body)
                // Check if disabled
                if (json.has("enabled") && !json.getBoolean("enabled")) {
                    Result.failure(Exception(json.optString("message", "Drone control disabled")))
                } else {
                    Result.success(ParseResponse.fromJson(json))
                }
            } else {
                Result.failure(Exception("Parse failed: ${response.code}"))
            }
        } catch (e: Exception) {
            Log.e(TAG, "Parse error: ${e.message}", e)
            Result.failure(e)
        }
    }

    /**
     * POST /api/drone/voice/execute
     * Execute a parsed drone command
     */
    suspend fun execute(
        intent: String,
        slots: ParsedSlots,
        confirm: Boolean?,
        sessionId: String
    ): Result<ExecuteResponse> = withContext(Dispatchers.IO) {
        try {
            val requestBody = JSONObject().apply {
                put("intent", intent)
                put("slots", slots.toJson())
                put("session_id", sessionId)
                confirm?.let { put("confirm", it) }
            }

            Log.d(TAG, "Execute request: $requestBody")

            val request = Request.Builder()
                .url("$baseUrl/api/drone/voice/execute")
                .post(requestBody.toString().toRequestBody(JSON_MEDIA_TYPE))
                .build()

            val response = httpClient.newCall(request).execute()
            val body = response.body?.string() ?: "{}"

            Log.d(TAG, "Execute response: $body")

            if (response.isSuccessful) {
                val json = JSONObject(body)
                // Check if disabled
                if (json.has("enabled") && !json.getBoolean("enabled")) {
                    Result.failure(Exception(json.optString("message", "Drone control disabled")))
                } else {
                    Result.success(ExecuteResponse.fromJson(json))
                }
            } else {
                Result.failure(Exception("Execute failed: ${response.code}"))
            }
        } catch (e: Exception) {
            Log.e(TAG, "Execute error: ${e.message}", e)
            Result.failure(e)
        }
    }

    /**
     * Emergency STOP - convenience method
     * Executes STOP immediately without confirmation
     */
    suspend fun emergencyStop(sessionId: String): Result<ExecuteResponse> {
        return execute(
            intent = "STOP",
            slots = ParsedSlots(),
            confirm = null,
            sessionId = sessionId
        )
    }
}
