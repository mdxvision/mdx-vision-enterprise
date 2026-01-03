package com.mdxvision

import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import org.json.JSONArray
import org.json.JSONObject

/**
 * Unit tests for Vuzix HUD feature (#73)
 * Tests HUD state management, patient data parsing, and voice commands
 */
class VuzixHudTest {

    private lateinit var hudStateManager: HudStateManager
    private lateinit var hudDataParser: HudDataParser
    private lateinit var hudCommandParser: HudCommandParser

    @Before
    fun setUp() {
        hudStateManager = HudStateManager()
        hudDataParser = HudDataParser()
        hudCommandParser = HudCommandParser()
    }

    // ==================== HUD STATE TESTS ====================

    @Test
    fun `initial state is HIDDEN`() {
        assertEquals(HudState.HIDDEN, hudStateManager.currentState)
    }

    @Test
    fun `show command transitions from HIDDEN to COMPACT`() {
        hudStateManager.show()
        assertEquals(HudState.COMPACT, hudStateManager.currentState)
    }

    @Test
    fun `show command on already visible HUD does nothing`() {
        hudStateManager.show()
        hudStateManager.show()
        assertEquals(HudState.COMPACT, hudStateManager.currentState)
    }

    @Test
    fun `hide command transitions any state to HIDDEN`() {
        hudStateManager.show()
        hudStateManager.hide()
        assertEquals(HudState.HIDDEN, hudStateManager.currentState)

        hudStateManager.show()
        hudStateManager.expand()
        hudStateManager.hide()
        assertEquals(HudState.HIDDEN, hudStateManager.currentState)
    }

    @Test
    fun `expand command transitions from COMPACT to EXPANDED`() {
        hudStateManager.show()
        hudStateManager.expand()
        assertEquals(HudState.EXPANDED, hudStateManager.currentState)
    }

    @Test
    fun `expand command from HIDDEN goes to EXPANDED`() {
        hudStateManager.expand()
        assertEquals(HudState.EXPANDED, hudStateManager.currentState)
    }

    @Test
    fun `minimize command transitions from EXPANDED to COMPACT`() {
        hudStateManager.show()
        hudStateManager.expand()
        hudStateManager.minimize()
        assertEquals(HudState.COMPACT, hudStateManager.currentState)
    }

    @Test
    fun `minimize on COMPACT does nothing`() {
        hudStateManager.show()
        hudStateManager.minimize()
        assertEquals(HudState.COMPACT, hudStateManager.currentState)
    }

    @Test
    fun `toggle cycles through states correctly`() {
        // HIDDEN -> COMPACT
        hudStateManager.toggle()
        assertEquals(HudState.COMPACT, hudStateManager.currentState)

        // COMPACT -> EXPANDED
        hudStateManager.toggle()
        assertEquals(HudState.EXPANDED, hudStateManager.currentState)

        // EXPANDED -> HIDDEN
        hudStateManager.toggle()
        assertEquals(HudState.HIDDEN, hudStateManager.currentState)
    }

    // ==================== PATIENT DATA PARSING TESTS ====================

    @Test
    fun `parses patient name correctly`() {
        val patient = JSONObject().apply {
            put("name", "John Smith")
            put("patient_id", "12345")
        }
        val display = hudDataParser.parsePatientHeader(patient)
        assertEquals("JOHN SMITH", display.name)
        assertEquals("12345", display.id)
    }

    @Test
    fun `parses patient with alternative field names`() {
        val patient = JSONObject().apply {
            put("patient_name", "Jane Doe")
            put("id", "67890")
        }
        val display = hudDataParser.parsePatientHeader(patient)
        assertEquals("JANE DOE", display.name)
        assertEquals("67890", display.id)
    }

    @Test
    fun `handles missing patient name`() {
        val patient = JSONObject().apply {
            put("patient_id", "12345")
        }
        val display = hudDataParser.parsePatientHeader(patient)
        assertEquals("UNKNOWN", display.name)
    }

    @Test
    fun `parses allergies correctly`() {
        val allergies = JSONArray().apply {
            put(JSONObject().apply {
                put("substance", "Penicillin")
                put("severity", "high")
            })
            put(JSONObject().apply {
                put("substance", "Sulfa")
                put("severity", "moderate")
            })
        }
        val patient = JSONObject().apply {
            put("allergies", allergies)
        }

        val result = hudDataParser.parseAllergies(patient)
        assertEquals(2, result.size)
        assertEquals("Penicillin", result[0].substance)
        assertEquals("high", result[0].severity)
        assertEquals("Sulfa", result[1].substance)
    }

    @Test
    fun `handles no allergies (NKDA)`() {
        val patient = JSONObject()
        val result = hudDataParser.parseAllergies(patient)
        assertTrue(result.isEmpty())
    }

    @Test
    fun `formats compact allergies display`() {
        val allergies = listOf(
            AllergyInfo("Penicillin", "high", "anaphylaxis"),
            AllergyInfo("Sulfa", "moderate", "rash"),
            AllergyInfo("Latex", "low", "contact dermatitis")
        )
        val display = hudDataParser.formatCompactAllergies(allergies)
        assertEquals("ALLERGIES: Penicillin, Sulfa +1 more", display)
    }

    @Test
    fun `formats NKDA when no allergies`() {
        val display = hudDataParser.formatCompactAllergies(emptyList())
        assertEquals("NKDA", display)
    }

    @Test
    fun `parses medications count`() {
        val medications = JSONArray().apply {
            put(JSONObject().apply { put("name", "Lisinopril") })
            put(JSONObject().apply { put("name", "Metformin") })
            put(JSONObject().apply { put("name", "Atorvastatin") })
        }
        val patient = JSONObject().apply {
            put("medications", medications)
        }

        val count = hudDataParser.getMedicationCount(patient)
        assertEquals(3, count)
    }

    @Test
    fun `parses vitals for display`() {
        val vitals = JSONArray().apply {
            put(JSONObject().apply {
                put("type", "blood_pressure")
                put("value", "120/80")
            })
            put(JSONObject().apply {
                put("type", "heart_rate")
                put("value", "72")
            })
            put(JSONObject().apply {
                put("type", "oxygen_saturation")
                put("value", "98")
            })
        }
        val patient = JSONObject().apply {
            put("vitals", vitals)
        }

        val display = hudDataParser.formatVitalsCompact(patient)
        assertTrue(display.contains("BP: 120/80"))
        assertTrue(display.contains("HR: 72"))
        assertTrue(display.contains("SpO2: 98%"))
    }

    @Test
    fun `handles missing vitals`() {
        val patient = JSONObject()
        val display = hudDataParser.formatVitalsCompact(patient)
        assertEquals("No vitals", display)
    }

    // ==================== VOICE COMMAND TESTS ====================

    @Test
    fun `show HUD command recognized`() {
        assertEquals(HudCommand.SHOW, hudCommandParser.parse("show hud"))
        assertEquals(HudCommand.SHOW, hudCommandParser.parse("display hud"))
        assertEquals(HudCommand.SHOW, hudCommandParser.parse("SHOW HUD"))
    }

    @Test
    fun `hide HUD command recognized`() {
        assertEquals(HudCommand.HIDE, hudCommandParser.parse("hide hud"))
        assertEquals(HudCommand.HIDE, hudCommandParser.parse("HIDE HUD"))
    }

    @Test
    fun `expand HUD command recognized`() {
        assertEquals(HudCommand.EXPAND, hudCommandParser.parse("expand hud"))
        assertEquals(HudCommand.EXPAND, hudCommandParser.parse("full hud"))
        assertEquals(HudCommand.EXPAND, hudCommandParser.parse("full details"))
    }

    @Test
    fun `minimize HUD command recognized`() {
        assertEquals(HudCommand.MINIMIZE, hudCommandParser.parse("minimize hud"))
        assertEquals(HudCommand.MINIMIZE, hudCommandParser.parse("compact hud"))
        assertEquals(HudCommand.MINIMIZE, hudCommandParser.parse("compact view"))
    }

    @Test
    fun `toggle HUD command recognized`() {
        assertEquals(HudCommand.TOGGLE, hudCommandParser.parse("toggle hud"))
    }

    @Test
    fun `non-HUD commands return NONE`() {
        assertEquals(HudCommand.NONE, hudCommandParser.parse("show vitals"))
        assertEquals(HudCommand.NONE, hudCommandParser.parse("load patient"))
        assertEquals(HudCommand.NONE, hudCommandParser.parse("random text"))
    }

    // ==================== HUD DIMENSIONS TESTS ====================

    @Test
    fun `compact dimensions are correct`() {
        val dims = HudDimensions.COMPACT
        assertEquals(320, dims.width)
        assertEquals(180, dims.height)
    }

    @Test
    fun `expanded dimensions are correct`() {
        val dims = HudDimensions.EXPANDED
        assertEquals(768, dims.width)
        assertEquals(400, dims.height)
    }

    // ==================== DEVICE DETECTION TESTS ====================

    @Test
    fun `detects Vuzix device by manufacturer`() {
        assertTrue(VuzixDeviceDetector.isVuzix("Vuzix", "Blade 2"))
        assertTrue(VuzixDeviceDetector.isVuzix("VUZIX", "Shield"))
        assertTrue(VuzixDeviceDetector.isVuzix("vuzix", "M400"))
    }

    @Test
    fun `detects Vuzix device by model name`() {
        assertTrue(VuzixDeviceDetector.isVuzix("Unknown", "Blade"))
        assertTrue(VuzixDeviceDetector.isVuzix("Unknown", "blade 2"))
    }

    @Test
    fun `non-Vuzix devices return false`() {
        assertFalse(VuzixDeviceDetector.isVuzix("Samsung", "Galaxy S24"))
        assertFalse(VuzixDeviceDetector.isVuzix("Google", "Pixel 8"))
        assertFalse(VuzixDeviceDetector.isVuzix("Unknown", "Unknown"))
    }

    // ==================== EDGE CASES ====================

    @Test
    fun `handles malformed JSON gracefully`() {
        val patient = JSONObject()
        // Should not throw exceptions
        val header = hudDataParser.parsePatientHeader(patient)
        val allergies = hudDataParser.parseAllergies(patient)
        val medCount = hudDataParser.getMedicationCount(patient)

        assertEquals("UNKNOWN", header.name)
        assertTrue(allergies.isEmpty())
        assertEquals(0, medCount)
    }

    @Test
    fun `handles null values in JSON`() {
        val patient = JSONObject().apply {
            put("name", JSONObject.NULL)
            put("allergies", JSONObject.NULL)
        }

        val header = hudDataParser.parsePatientHeader(patient)
        assertEquals("UNKNOWN", header.name)
    }
}

// ==================== SUPPORT CLASSES ====================

enum class HudState {
    HIDDEN,
    COMPACT,
    EXPANDED
}

enum class HudCommand {
    SHOW,
    HIDE,
    EXPAND,
    MINIMIZE,
    TOGGLE,
    NONE
}

data class PatientHeaderDisplay(
    val name: String,
    val id: String
)

data class AllergyInfo(
    val substance: String,
    val severity: String,
    val reaction: String = ""
)

enum class HudDimensions(val width: Int, val height: Int) {
    COMPACT(320, 180),
    EXPANDED(768, 400)
}

/**
 * Manages HUD state transitions
 */
class HudStateManager {
    var currentState: HudState = HudState.HIDDEN
        private set

    fun show() {
        if (currentState == HudState.HIDDEN) {
            currentState = HudState.COMPACT
        }
    }

    fun hide() {
        currentState = HudState.HIDDEN
    }

    fun expand() {
        currentState = when (currentState) {
            HudState.HIDDEN -> HudState.EXPANDED
            HudState.COMPACT -> HudState.EXPANDED
            HudState.EXPANDED -> HudState.EXPANDED
        }
    }

    fun minimize() {
        if (currentState == HudState.EXPANDED) {
            currentState = HudState.COMPACT
        }
    }

    fun toggle() {
        currentState = when (currentState) {
            HudState.HIDDEN -> HudState.COMPACT
            HudState.COMPACT -> HudState.EXPANDED
            HudState.EXPANDED -> HudState.HIDDEN
        }
    }
}

/**
 * Parses patient data for HUD display
 */
class HudDataParser {

    fun parsePatientHeader(patient: JSONObject): PatientHeaderDisplay {
        val name = patient.optString("name", "").ifEmpty {
            patient.optString("patient_name", "Unknown")
        }
        val id = patient.optString("patient_id", "").ifEmpty {
            patient.optString("id", "")
        }
        return PatientHeaderDisplay(
            name = if (name == "Unknown" || name.isEmpty()) "UNKNOWN" else name.uppercase(),
            id = id
        )
    }

    fun parseAllergies(patient: JSONObject): List<AllergyInfo> {
        val allergies = patient.optJSONArray("allergies") ?: return emptyList()
        val result = mutableListOf<AllergyInfo>()

        for (i in 0 until allergies.length()) {
            val allergy = allergies.optJSONObject(i) ?: continue
            result.add(AllergyInfo(
                substance = allergy.optString("substance", allergy.optString("name", "Unknown")),
                severity = allergy.optString("severity", ""),
                reaction = allergy.optString("reaction", "")
            ))
        }
        return result
    }

    fun formatCompactAllergies(allergies: List<AllergyInfo>): String {
        if (allergies.isEmpty()) return "NKDA"

        val display = allergies.take(2).joinToString(", ") { it.substance }
        val suffix = if (allergies.size > 2) " +${allergies.size - 2} more" else ""
        return "ALLERGIES: $display$suffix"
    }

    fun getMedicationCount(patient: JSONObject): Int {
        return patient.optJSONArray("medications")?.length() ?: 0
    }

    fun formatVitalsCompact(patient: JSONObject): String {
        val vitals = patient.optJSONArray("vitals") ?: return "No vitals"
        if (vitals.length() == 0) return "No vitals"

        val parts = mutableListOf<String>()
        for (i in 0 until vitals.length()) {
            val vital = vitals.optJSONObject(i) ?: continue
            val type = vital.optString("type", "").lowercase()
            val value = vital.optString("value", "")

            when {
                type.contains("blood_pressure") || type == "bp" -> parts.add("BP: $value")
                type.contains("heart_rate") || type == "hr" || type == "pulse" -> parts.add("HR: $value")
                type.contains("oxygen") || type == "spo2" -> parts.add("SpO2: $value%")
                type.contains("temp") -> parts.add("Temp: $value")
            }
        }

        return if (parts.isNotEmpty()) parts.joinToString(" | ") else "No vitals"
    }
}

/**
 * Parses HUD voice commands
 */
class HudCommandParser {
    fun parse(transcript: String): HudCommand {
        val lower = transcript.lowercase().trim()

        return when {
            lower.contains("show hud") || lower.contains("display hud") -> HudCommand.SHOW
            lower.contains("hide hud") -> HudCommand.HIDE
            lower.contains("expand hud") || lower.contains("full hud") || lower.contains("full details") -> HudCommand.EXPAND
            lower.contains("minimize hud") || lower.contains("compact hud") || lower.contains("compact view") -> HudCommand.MINIMIZE
            lower.contains("toggle hud") -> HudCommand.TOGGLE
            else -> HudCommand.NONE
        }
    }
}

/**
 * Detects Vuzix devices
 */
object VuzixDeviceDetector {
    fun isVuzix(manufacturer: String, model: String): Boolean {
        val mfr = manufacturer.lowercase()
        val mdl = model.lowercase()
        return mfr.contains("vuzix") || mdl.contains("blade")
    }
}
