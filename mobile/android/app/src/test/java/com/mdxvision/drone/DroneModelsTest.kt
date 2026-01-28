package com.mdxvision.drone

import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

/**
 * Unit tests for Drone Voice Control data models
 */
class DroneModelsTest {

    @Test
    fun `DroneStatus parses enabled status correctly`() {
        val json = JSONObject().apply {
            put("enabled", true)
            put("adapter_name", "Mock Drone Simulator")
            put("adapter_type", "mock")
            put("connected", true)
        }

        val status = DroneStatus.fromJson(json)

        assertTrue(status.enabled)
        assertEquals("Mock Drone Simulator", status.adapterName)
        assertEquals("mock", status.adapterType)
        assertTrue(status.connected)
    }

    @Test
    fun `DroneStatus parses disabled status correctly`() {
        val json = JSONObject().apply {
            put("enabled", false)
            put("message", "Drone control disabled on server")
        }

        val status = DroneStatus.fromJson(json)

        assertFalse(status.enabled)
        assertEquals("Drone control disabled on server", status.message)
        assertFalse(status.connected)
    }

    @Test
    fun `ParsedSlots parses distance and unit`() {
        val json = JSONObject().apply {
            put("distance", 5.0)
            put("unit", "meters")
        }

        val slots = ParsedSlots.fromJson(json)

        assertEquals(5.0, slots.distance)
        assertEquals("meters", slots.unit)
        assertNull(slots.degrees)
    }

    @Test
    fun `ParsedSlots handles null values`() {
        val json = JSONObject().apply {
            put("distance", JSONObject.NULL)
            put("unit", JSONObject.NULL)
        }

        val slots = ParsedSlots.fromJson(json)

        assertNull(slots.distance)
        assertNull(slots.unit)
    }

    @Test
    fun `ParsedSlots toJson roundtrip`() {
        val original = ParsedSlots(
            distance = 10.0,
            unit = "feet",
            degrees = 90.0
        )

        val json = original.toJson()
        val restored = ParsedSlots.fromJson(json)

        assertEquals(original.distance, restored.distance)
        assertEquals(original.unit, restored.unit)
        assertEquals(original.degrees, restored.degrees)
    }

    @Test
    fun `ParseResponse parses MOVE_LEFT intent`() {
        val json = JSONObject().apply {
            put("intent", "MOVE_LEFT")
            put("slots", JSONObject().apply {
                put("distance", 5.0)
                put("unit", "meters")
            })
            put("requires_confirmation", false)
            put("normalized_command", "MOVE_LEFT 5.0 meters")
            put("confidence", 0.95)
            put("original_transcript", "go left 5 meters")
        }

        val response = ParseResponse.fromJson(json)

        assertEquals("MOVE_LEFT", response.intent)
        assertFalse(response.isUnknown)
        assertFalse(response.requiresConfirmation)
        assertEquals(5.0, response.slots.distance)
        assertEquals("meters", response.slots.unit)
        assertEquals(0.95, response.confidence, 0.001)
    }

    @Test
    fun `ParseResponse detects UNKNOWN intent`() {
        val json = JSONObject().apply {
            put("intent", "UNKNOWN")
            put("slots", JSONObject())
            put("requires_confirmation", false)
            put("normalized_command", "UNKNOWN")
            put("confidence", 0.0)
            put("original_transcript", "random gibberish")
        }

        val response = ParseResponse.fromJson(json)

        assertTrue(response.isUnknown)
    }

    @Test
    fun `ParseResponse detects confirmation requirement`() {
        val json = JSONObject().apply {
            put("intent", "TAKEOFF")
            put("slots", JSONObject())
            put("requires_confirmation", true)
            put("normalized_command", "TAKEOFF")
            put("confidence", 0.95)
            put("original_transcript", "take off")
        }

        val response = ParseResponse.fromJson(json)

        assertEquals("TAKEOFF", response.intent)
        assertTrue(response.requiresConfirmation)
    }

    @Test
    fun `ExecuteResponse parses OK status`() {
        val json = JSONObject().apply {
            put("status", "ok")
            put("message", "Moved left 5.0 meters")
            put("command_executed", "MOVE_LEFT 5.0 meters")
        }

        val response = ExecuteResponse.fromJson(json)

        assertEquals(ExecutionStatus.OK, response.status)
        assertTrue(response.status.isSuccess)
        assertFalse(response.status.needsConfirmation)
        assertEquals("Moved left 5.0 meters", response.message)
    }

    @Test
    fun `ExecuteResponse parses needs_confirm status`() {
        val json = JSONObject().apply {
            put("status", "needs_confirm")
            put("message", "Confirm TAKEOFF?")
            put("command_executed", "TAKEOFF")
        }

        val response = ExecuteResponse.fromJson(json)

        assertEquals(ExecutionStatus.NEEDS_CONFIRM, response.status)
        assertFalse(response.status.isSuccess)
        assertTrue(response.status.needsConfirmation)
    }

    @Test
    fun `ExecutionStatus fromString handles all values`() {
        assertEquals(ExecutionStatus.OK, ExecutionStatus.fromString("ok"))
        assertEquals(ExecutionStatus.BLOCKED, ExecutionStatus.fromString("blocked"))
        assertEquals(ExecutionStatus.NEEDS_CONFIRM, ExecutionStatus.fromString("needs_confirm"))
        assertEquals(ExecutionStatus.UNSUPPORTED, ExecutionStatus.fromString("unsupported"))
        assertEquals(ExecutionStatus.RATE_LIMITED, ExecutionStatus.fromString("rate_limited"))
        assertEquals(ExecutionStatus.DISABLED, ExecutionStatus.fromString("disabled"))
        // Unknown values default to BLOCKED
        assertEquals(ExecutionStatus.BLOCKED, ExecutionStatus.fromString("unknown_status"))
    }

    @Test
    fun `DroneCapability parses correctly`() {
        val json = JSONObject().apply {
            put("supported", true)
            put("description", "Full flight control")
        }

        val capability = DroneCapability.fromJson(json)

        assertTrue(capability.supported)
        assertEquals("Full flight control", capability.description)
    }

    @Test
    fun `CapabilitiesResponse parses all fields`() {
        val json = JSONObject().apply {
            put("adapter_name", "Mock Drone Simulator")
            put("adapter_type", "mock")
            put("connected", true)
            put("capabilities", JSONObject().apply {
                put("flight", JSONObject().apply {
                    put("supported", true)
                    put("description", "Flight control")
                })
                put("camera", JSONObject().apply {
                    put("supported", true)
                    put("description", "Camera control")
                })
            })
            put("supported_intents", org.json.JSONArray().apply {
                put("TAKEOFF")
                put("LAND")
                put("MOVE_LEFT")
            })
        }

        val response = CapabilitiesResponse.fromJson(json)

        assertEquals("Mock Drone Simulator", response.adapterName)
        assertEquals("mock", response.adapterType)
        assertTrue(response.connected)
        assertEquals(2, response.capabilities.size)
        assertTrue(response.capabilities["flight"]?.supported == true)
        assertEquals(3, response.supportedIntents.size)
        assertTrue(response.supportedIntents.contains("TAKEOFF"))
    }
}
