package com.mdxvision.drone

import org.json.JSONObject

/**
 * Drone Voice Control - Data Models
 * Maps to ehr-proxy/drone API responses
 */

/**
 * Response from GET /api/drone/status
 */
data class DroneStatus(
    val enabled: Boolean,
    val message: String? = null,
    val adapterName: String? = null,
    val adapterType: String? = null,
    val connected: Boolean = false
) {
    companion object {
        fun fromJson(json: JSONObject): DroneStatus {
            return DroneStatus(
                enabled = json.optBoolean("enabled", false),
                message = json.optString("message", null),
                adapterName = json.optString("adapter_name", null),
                adapterType = json.optString("adapter_type", null),
                connected = json.optBoolean("connected", false)
            )
        }
    }
}

/**
 * Parsed slots from voice command
 */
data class ParsedSlots(
    val distance: Double? = null,
    val unit: String? = null,
    val degrees: Double? = null,
    val zoomLevel: Double? = null,
    val speedLevel: String? = null,
    val speedNumeric: Double? = null
) {
    companion object {
        fun fromJson(json: JSONObject): ParsedSlots {
            return ParsedSlots(
                distance = if (json.has("distance") && !json.isNull("distance")) json.getDouble("distance") else null,
                unit = if (json.has("unit") && !json.isNull("unit")) json.getString("unit") else null,
                degrees = if (json.has("degrees") && !json.isNull("degrees")) json.getDouble("degrees") else null,
                zoomLevel = if (json.has("zoom_level") && !json.isNull("zoom_level")) json.getDouble("zoom_level") else null,
                speedLevel = if (json.has("speed_level") && !json.isNull("speed_level")) json.getString("speed_level") else null,
                speedNumeric = if (json.has("speed_numeric") && !json.isNull("speed_numeric")) json.getDouble("speed_numeric") else null
            )
        }
    }

    fun toJson(): JSONObject {
        val json = JSONObject()
        distance?.let { json.put("distance", it) }
        unit?.let { json.put("unit", it) }
        degrees?.let { json.put("degrees", it) }
        zoomLevel?.let { json.put("zoom_level", it) }
        speedLevel?.let { json.put("speed_level", it) }
        speedNumeric?.let { json.put("speed_numeric", it) }
        return json
    }
}

/**
 * Response from POST /api/drone/voice/parse
 */
data class ParseResponse(
    val intent: String,
    val slots: ParsedSlots,
    val requiresConfirmation: Boolean,
    val normalizedCommand: String,
    val confidence: Double,
    val originalTranscript: String
) {
    companion object {
        fun fromJson(json: JSONObject): ParseResponse {
            return ParseResponse(
                intent = json.getString("intent"),
                slots = ParsedSlots.fromJson(json.getJSONObject("slots")),
                requiresConfirmation = json.getBoolean("requires_confirmation"),
                normalizedCommand = json.getString("normalized_command"),
                confidence = json.getDouble("confidence"),
                originalTranscript = json.getString("original_transcript")
            )
        }
    }

    val isUnknown: Boolean
        get() = intent == "UNKNOWN"
}

/**
 * Response from POST /api/drone/voice/execute
 */
data class ExecuteResponse(
    val status: ExecutionStatus,
    val message: String,
    val commandExecuted: String? = null,
    val adapterResponse: JSONObject? = null
) {
    companion object {
        fun fromJson(json: JSONObject): ExecuteResponse {
            val statusStr = json.getString("status")
            return ExecuteResponse(
                status = ExecutionStatus.fromString(statusStr),
                message = json.getString("message"),
                commandExecuted = json.optString("command_executed", null),
                adapterResponse = json.optJSONObject("adapter_response")
            )
        }
    }
}

/**
 * Execution status from backend
 */
enum class ExecutionStatus(val value: String) {
    OK("ok"),
    BLOCKED("blocked"),
    NEEDS_CONFIRM("needs_confirm"),
    UNSUPPORTED("unsupported"),
    RATE_LIMITED("rate_limited"),
    DISABLED("disabled");

    companion object {
        fun fromString(value: String): ExecutionStatus {
            return entries.find { it.value == value } ?: BLOCKED
        }
    }

    val isSuccess: Boolean
        get() = this == OK

    val needsConfirmation: Boolean
        get() = this == NEEDS_CONFIRM
}

/**
 * Capability info from GET /api/drone/capabilities
 */
data class DroneCapability(
    val supported: Boolean,
    val description: String
) {
    companion object {
        fun fromJson(json: JSONObject): DroneCapability {
            return DroneCapability(
                supported = json.getBoolean("supported"),
                description = json.getString("description")
            )
        }
    }
}

/**
 * Response from GET /api/drone/capabilities
 */
data class CapabilitiesResponse(
    val adapterName: String,
    val adapterType: String,
    val connected: Boolean,
    val capabilities: Map<String, DroneCapability>,
    val supportedIntents: List<String>
) {
    companion object {
        fun fromJson(json: JSONObject): CapabilitiesResponse {
            val capsJson = json.getJSONObject("capabilities")
            val caps = mutableMapOf<String, DroneCapability>()
            capsJson.keys().forEach { key ->
                caps[key] = DroneCapability.fromJson(capsJson.getJSONObject(key))
            }

            val intentsArray = json.getJSONArray("supported_intents")
            val intents = mutableListOf<String>()
            for (i in 0 until intentsArray.length()) {
                intents.add(intentsArray.getString(i))
            }

            return CapabilitiesResponse(
                adapterName = json.getString("adapter_name"),
                adapterType = json.getString("adapter_type"),
                connected = json.getBoolean("connected"),
                capabilities = caps,
                supportedIntents = intents
            )
        }
    }
}

/**
 * UI state for drone control screen
 */
sealed class DroneUiState {
    object Idle : DroneUiState()
    object Listening : DroneUiState()
    object Processing : DroneUiState()
    data class Parsed(val response: ParseResponse) : DroneUiState()
    data class AwaitingConfirmation(val response: ParseResponse) : DroneUiState()
    data class Executed(val response: ExecuteResponse) : DroneUiState()
    data class Error(val message: String) : DroneUiState()
    object Disabled : DroneUiState()
}
