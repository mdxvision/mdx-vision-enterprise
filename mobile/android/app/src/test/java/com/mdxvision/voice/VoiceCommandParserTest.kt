package com.mdxvision.voice

import kotlinx.coroutines.runBlocking
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test

/**
 * Tests for VoiceCommandParser (Issue #31)
 * Validates voice command parsing and macro expansion
 */
class VoiceCommandParserTest {

    private lateinit var parser: VoiceCommandParser

    @Before
    fun setup() {
        // Use a mock URL that won't make real network calls
        parser = VoiceCommandParser(baseUrl = "http://localhost:9999")
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // PATIENT LOADING
    // ═══════════════════════════════════════════════════════════════════════════

    @Test
    fun `parse - load patient by ID`() = runBlocking {
        val result = parser.parse("load patient 12724066")
        assertEquals(1, result.intents.size)
        assertTrue(result.intents[0] is VoiceCommandParser.VoiceIntent.LoadPatient)
        assertEquals("12724066", (result.intents[0] as VoiceCommandParser.VoiceIntent.LoadPatient).identifier)
    }

    @Test
    fun `parse - load patient by index`() = runBlocking {
        val result = parser.parse("load 3")
        assertEquals(1, result.intents.size)
        assertTrue(result.intents[0] is VoiceCommandParser.VoiceIntent.LoadPatient)
        assertEquals("3", (result.intents[0] as VoiceCommandParser.VoiceIntent.LoadPatient).identifier)
    }

    @Test
    fun `parse - load patient with mishearing`() = runBlocking {
        val result = parser.parse("load patine 12724066")  // Common mishearing
        assertEquals(1, result.intents.size)
        assertTrue(result.intents[0] is VoiceCommandParser.VoiceIntent.LoadPatient)
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // SHOW DATA SECTIONS
    // ═══════════════════════════════════════════════════════════════════════════

    @Test
    fun `parse - show vitals`() = runBlocking {
        val result = parser.parse("show vitals")
        assertEquals(1, result.intents.size)
        assertTrue(result.intents[0] is VoiceCommandParser.VoiceIntent.ShowSection)
        assertEquals("vitals", (result.intents[0] as VoiceCommandParser.VoiceIntent.ShowSection).section)
    }

    @Test
    fun `parse - show labs`() = runBlocking {
        val result = parser.parse("show labs")
        assertEquals(1, result.intents.size)
        assertTrue(result.intents[0] is VoiceCommandParser.VoiceIntent.ShowSection)
        assertEquals("labs", (result.intents[0] as VoiceCommandParser.VoiceIntent.ShowSection).section)
    }

    @Test
    fun `parse - show allergies`() = runBlocking {
        val result = parser.parse("show allergies")
        assertEquals(1, result.intents.size)
        assertTrue(result.intents[0] is VoiceCommandParser.VoiceIntent.ShowSection)
        assertEquals("allergies", (result.intents[0] as VoiceCommandParser.VoiceIntent.ShowSection).section)
    }

    @Test
    fun `parse - show medications`() = runBlocking {
        val result = parser.parse("show meds")
        assertEquals(1, result.intents.size)
        assertTrue(result.intents[0] is VoiceCommandParser.VoiceIntent.ShowSection)
        assertEquals("medications", (result.intents[0] as VoiceCommandParser.VoiceIntent.ShowSection).section)
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // MULTI-INTENT COMMANDS
    // ═══════════════════════════════════════════════════════════════════════════

    @Test
    fun `parse - multi-intent with then`() = runBlocking {
        val result = parser.parse("load patient 12724066 then show vitals")
        assertEquals(2, result.intents.size)
        assertTrue(result.intents[0] is VoiceCommandParser.VoiceIntent.LoadPatient)
        assertTrue(result.intents[1] is VoiceCommandParser.VoiceIntent.ShowSection)
    }

    @Test
    fun `parse - multi-intent with and then`() = runBlocking {
        val result = parser.parse("show vitals and then show labs and then show allergies")
        assertEquals(3, result.intents.size)
        assertTrue(result.intents.all { it is VoiceCommandParser.VoiceIntent.ShowSection })
    }

    @Test
    fun `parse - multi-intent with and`() = runBlocking {
        val result = parser.parse("show vitals and show labs")
        assertEquals(2, result.intents.size)
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // EHR SWITCHING
    // ═══════════════════════════════════════════════════════════════════════════

    @Test
    fun `parse - switch to epic`() = runBlocking {
        val result = parser.parse("switch to epic")
        assertEquals(1, result.intents.size)
        assertTrue(result.intents[0] is VoiceCommandParser.VoiceIntent.SwitchEhr)
        assertEquals("epic", (result.intents[0] as VoiceCommandParser.VoiceIntent.SwitchEhr).ehr)
    }

    @Test
    fun `parse - switch to cerner`() = runBlocking {
        val result = parser.parse("switch to cerner")
        assertEquals(1, result.intents.size)
        assertTrue(result.intents[0] is VoiceCommandParser.VoiceIntent.SwitchEhr)
        assertEquals("cerner", (result.intents[0] as VoiceCommandParser.VoiceIntent.SwitchEhr).ehr)
    }

    @Test
    fun `parse - switch to cerner with mishearing`() = runBlocking {
        // "center" is commonly transcribed instead of "cerner"
        val result = parser.parse("switch to center")
        assertEquals(1, result.intents.size)
        assertTrue(result.intents[0] is VoiceCommandParser.VoiceIntent.SwitchEhr)
        assertEquals("cerner", (result.intents[0] as VoiceCommandParser.VoiceIntent.SwitchEhr).ehr)
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // MINERVA AI
    // ═══════════════════════════════════════════════════════════════════════════

    @Test
    fun `parse - hey minerva`() = runBlocking {
        val result = parser.parse("hey minerva")
        assertEquals(1, result.intents.size)
        assertTrue(result.intents[0] is VoiceCommandParser.VoiceIntent.ActivateMinerva)
    }

    @Test
    fun `parse - minerva with query`() = runBlocking {
        val result = parser.parse("hey minerva what is the differential diagnosis")
        assertEquals(1, result.intents.size)
        assertTrue(result.intents[0] is VoiceCommandParser.VoiceIntent.ActivateMinerva)
        val intent = result.intents[0] as VoiceCommandParser.VoiceIntent.ActivateMinerva
        assertTrue(intent.query?.contains("differential") == true)
    }

    @Test
    fun `parse - minerva mishearing murder`() = runBlocking {
        // "murder" is commonly transcribed instead of "minerva"
        val result = parser.parse("hey murder what should I do")
        assertTrue(result.normalizedText.contains("minerva"))
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // ORDERS
    // ═══════════════════════════════════════════════════════════════════════════

    @Test
    fun `parse - order CBC`() = runBlocking {
        val result = parser.parse("order CBC")
        assertEquals(1, result.intents.size)
        assertTrue(result.intents[0] is VoiceCommandParser.VoiceIntent.Order)
        val order = result.intents[0] as VoiceCommandParser.VoiceIntent.Order
        assertEquals("lab", order.orderType)
        assertEquals("CBC", order.details)
    }

    @Test
    fun `parse - order chest x-ray`() = runBlocking {
        val result = parser.parse("order chest x-ray")
        assertEquals(1, result.intents.size)
        assertTrue(result.intents[0] is VoiceCommandParser.VoiceIntent.Order)
        val order = result.intents[0] as VoiceCommandParser.VoiceIntent.Order
        assertEquals("imaging", order.orderType)
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // WORKLIST
    // ═══════════════════════════════════════════════════════════════════════════

    @Test
    fun `parse - show worklist`() = runBlocking {
        val result = parser.parse("show worklist")
        assertEquals(1, result.intents.size)
        assertTrue(result.intents[0] is VoiceCommandParser.VoiceIntent.ShowWorklist)
    }

    @Test
    fun `parse - check in patient`() = runBlocking {
        val result = parser.parse("check in 3")
        assertEquals(1, result.intents.size)
        assertTrue(result.intents[0] is VoiceCommandParser.VoiceIntent.CheckIn)
        assertEquals(3, (result.intents[0] as VoiceCommandParser.VoiceIntent.CheckIn).patientIndex)
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // TRANSCRIPTION & DOCUMENTATION
    // ═══════════════════════════════════════════════════════════════════════════

    @Test
    fun `parse - start transcription`() = runBlocking {
        val result = parser.parse("start transcription")
        assertEquals(1, result.intents.size)
        assertTrue(result.intents[0] is VoiceCommandParser.VoiceIntent.StartTranscription)
    }

    @Test
    fun `parse - stop transcription`() = runBlocking {
        val result = parser.parse("stop transcription")
        assertEquals(1, result.intents.size)
        assertTrue(result.intents[0] is VoiceCommandParser.VoiceIntent.StopTranscription)
    }

    @Test
    fun `parse - generate note`() = runBlocking {
        val result = parser.parse("generate note")
        assertEquals(1, result.intents.size)
        assertTrue(result.intents[0] is VoiceCommandParser.VoiceIntent.GenerateNote)
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // CUSTOM MACRO CREATION
    // ═══════════════════════════════════════════════════════════════════════════

    @Test
    fun `parse - create macro`() = runBlocking {
        val result = parser.parse("create command morning rounds that does show vitals then show meds then show labs")
        assertEquals(1, result.intents.size)
        assertTrue(result.intents[0] is VoiceCommandParser.VoiceIntent.CreateMacro)
        val macro = result.intents[0] as VoiceCommandParser.VoiceIntent.CreateMacro
        assertEquals("morning rounds", macro.trigger)
        assertEquals(3, macro.actions.size)
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // HELP & UNKNOWN
    // ═══════════════════════════════════════════════════════════════════════════

    @Test
    fun `parse - help`() = runBlocking {
        val result = parser.parse("help")
        assertEquals(1, result.intents.size)
        assertTrue(result.intents[0] is VoiceCommandParser.VoiceIntent.ShowHelp)
    }

    @Test
    fun `parse - unknown command`() = runBlocking {
        val result = parser.parse("random gibberish that makes no sense")
        assertEquals(1, result.intents.size)
        assertTrue(result.intents[0] is VoiceCommandParser.VoiceIntent.Unknown)
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // NORMALIZATION
    // ═══════════════════════════════════════════════════════════════════════════

    @Test
    fun `normalization - fixes mishearings`() = runBlocking {
        // Test various mishearings
        val tests = listOf(
            "murder" to "minerva",
            "center" to "cerner",
            "patine" to "patient",
        )

        for ((input, expected) in tests) {
            val result = parser.parse(input)
            assertTrue("Expected '$expected' in normalized text, got: ${result.normalizedText}",
                result.normalizedText.lowercase().contains(expected))
        }
    }
}
