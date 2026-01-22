package com.mdxvision

import org.junit.Assert.*
import org.junit.Before
import org.junit.Test

/**
 * Unit tests for voice command parsing in MDx Vision
 * Tests the fuzzy matching and command recognition logic
 */
class VoiceCommandParserTest {

    private lateinit var parser: VoiceCommandParser

    @Before
    fun setUp() {
        parser = VoiceCommandParser()
    }

    // ==================== WAKE WORD TESTS ====================

    @Test
    fun `wake word Minerva is detected`() {
        assertTrue(parser.containsWakeWord("minerva load patient"))
        assertTrue(parser.containsWakeWord("MINERVA show vitals"))
        assertTrue(parser.containsWakeWord("Minerva live transcribe"))
    }

    @Test
    fun `wake word variations are detected`() {
        assertTrue(parser.containsWakeWord("m i n e r v a load patient"))
        assertTrue(parser.containsWakeWord("m.i.n.e.r.v.a show vitals"))
    }

    @Test
    fun `extracts command after wake word`() {
        assertEquals("load patient", parser.extractCommandAfterWakeWord("minerva load patient"))
        assertEquals("show vitals", parser.extractCommandAfterWakeWord("MINERVA show vitals"))
        assertEquals("live transcribe", parser.extractCommandAfterWakeWord("m i n e r v a live transcribe"))
    }

    // ==================== PATIENT COMMAND TESTS ====================

    @Test
    fun `load patient command recognized`() {
        assertEquals(VoiceCommand.LOAD_PATIENT, parser.parseCommand("load patient"))
        assertEquals(VoiceCommand.LOAD_PATIENT, parser.parseCommand("patient load"))
    }

    @Test
    fun `load patient with fuzzy matching for misrecognitions`() {
        // Common speech recognition errors
        assertEquals(VoiceCommand.LOAD_PATIENT, parser.parseCommand("load patine"))
        assertEquals(VoiceCommand.LOAD_PATIENT, parser.parseCommand("load patience"))
        assertEquals(VoiceCommand.LOAD_PATIENT, parser.parseCommand("load patent"))
    }

    @Test
    fun `find patient command recognized`() {
        assertEquals(VoiceCommand.FIND_PATIENT, parser.parseCommand("find patient Smith"))
        assertEquals(VoiceCommand.FIND_PATIENT, parser.parseCommand("search patient John"))
        assertEquals(VoiceCommand.FIND_PATIENT, parser.parseCommand("find patine Jones"))
    }

    @Test
    fun `extracts patient name from find command`() {
        assertEquals("Smith", parser.extractPatientName("find patient Smith"))
        assertEquals("John Doe", parser.extractPatientName("search John Doe"))
    }

    // ==================== VITALS/ALLERGIES/MEDS TESTS ====================

    @Test
    fun `show vitals command recognized`() {
        assertEquals(VoiceCommand.SHOW_VITALS, parser.parseCommand("show vitals"))
        assertEquals(VoiceCommand.SHOW_VITALS, parser.parseCommand("vitals"))
        assertEquals(VoiceCommand.SHOW_VITALS, parser.parseCommand("display vitals"))
    }

    @Test
    fun `show allergies command recognized`() {
        assertEquals(VoiceCommand.SHOW_ALLERGIES, parser.parseCommand("show allergies"))
        assertEquals(VoiceCommand.SHOW_ALLERGIES, parser.parseCommand("allergies"))
        assertEquals(VoiceCommand.SHOW_ALLERGIES, parser.parseCommand("what are the allergies"))
    }

    @Test
    fun `show medications command recognized`() {
        assertEquals(VoiceCommand.SHOW_MEDICATIONS, parser.parseCommand("show meds"))
        assertEquals(VoiceCommand.SHOW_MEDICATIONS, parser.parseCommand("medications"))
        assertEquals(VoiceCommand.SHOW_MEDICATIONS, parser.parseCommand("show medications"))
        assertEquals(VoiceCommand.SHOW_MEDICATIONS, parser.parseCommand("what meds"))
    }

    @Test
    fun `show labs command recognized`() {
        assertEquals(VoiceCommand.SHOW_LABS, parser.parseCommand("show labs"))
        assertEquals(VoiceCommand.SHOW_LABS, parser.parseCommand("lab results"))
        assertEquals(VoiceCommand.SHOW_LABS, parser.parseCommand("laboratories"))
    }

    // ==================== TRANSCRIPTION TESTS ====================

    @Test
    fun `live transcribe command recognized`() {
        assertEquals(VoiceCommand.LIVE_TRANSCRIBE, parser.parseCommand("live transcribe"))
        assertEquals(VoiceCommand.LIVE_TRANSCRIBE, parser.parseCommand("start transcription"))
        assertEquals(VoiceCommand.LIVE_TRANSCRIBE, parser.parseCommand("transcribe"))
        assertEquals(VoiceCommand.LIVE_TRANSCRIBE, parser.parseCommand("start recording"))
    }

    @Test
    fun `stop transcription command recognized`() {
        assertEquals(VoiceCommand.STOP_TRANSCRIPTION, parser.parseCommand("stop transcription"))
        assertEquals(VoiceCommand.STOP_TRANSCRIPTION, parser.parseCommand("stop recording"))
        // Note: "close" alone maps to CLOSE, not STOP_TRANSCRIPTION
        // Use "stop transcription" to stop recording
    }

    // ==================== NOTE COMMANDS TESTS ====================

    @Test
    fun `generate note command recognized`() {
        assertEquals(VoiceCommand.GENERATE_NOTE, parser.parseCommand("generate note"))
        assertEquals(VoiceCommand.GENERATE_NOTE, parser.parseCommand("create note"))
        assertEquals(VoiceCommand.GENERATE_NOTE, parser.parseCommand("looks good"))
        assertEquals(VoiceCommand.GENERATE_NOTE, parser.parseCommand("that's good"))
    }

    @Test
    fun `save note command recognized`() {
        assertEquals(VoiceCommand.SAVE_NOTE, parser.parseCommand("save note"))
        assertEquals(VoiceCommand.SAVE_NOTE, parser.parseCommand("submit note"))
    }

    @Test
    fun `push note command recognized`() {
        assertEquals(VoiceCommand.PUSH_NOTE, parser.parseCommand("push note"))
        assertEquals(VoiceCommand.PUSH_NOTE, parser.parseCommand("send to ehr"))
        assertEquals(VoiceCommand.PUSH_NOTE, parser.parseCommand("upload note"))
    }

    // ==================== BRIEFING COMMANDS TESTS ====================

    @Test
    fun `brief me command recognized`() {
        assertEquals(VoiceCommand.BRIEF_ME, parser.parseCommand("brief me"))
        assertEquals(VoiceCommand.BRIEF_ME, parser.parseCommand("briefing"))
        assertEquals(VoiceCommand.BRIEF_ME, parser.parseCommand("summarize"))
        assertEquals(VoiceCommand.BRIEF_ME, parser.parseCommand("read patient"))
        assertEquals(VoiceCommand.BRIEF_ME, parser.parseCommand("patient brief"))
    }

    @Test
    fun `patient summary command recognized`() {
        assertEquals(VoiceCommand.PATIENT_SUMMARY, parser.parseCommand("patient summary"))
        assertEquals(VoiceCommand.PATIENT_SUMMARY, parser.parseCommand("show summary"))
        assertEquals(VoiceCommand.PATIENT_SUMMARY, parser.parseCommand("overview"))
    }

    // ==================== NAVIGATION TESTS ====================

    @Test
    fun `close command recognized`() {
        assertEquals(VoiceCommand.CLOSE, parser.parseCommand("close"))
        assertEquals(VoiceCommand.CLOSE, parser.parseCommand("dismiss"))
        assertEquals(VoiceCommand.CLOSE, parser.parseCommand("back"))
    }

    @Test
    fun `help command recognized`() {
        assertEquals(VoiceCommand.HELP, parser.parseCommand("help"))
        assertEquals(VoiceCommand.HELP, parser.parseCommand("what can I say"))
        assertEquals(VoiceCommand.HELP, parser.parseCommand("voice commands"))
    }

    // ==================== EDGE CASES ====================

    @Test
    fun `empty input returns unknown command`() {
        assertEquals(VoiceCommand.UNKNOWN, parser.parseCommand(""))
        assertEquals(VoiceCommand.UNKNOWN, parser.parseCommand("   "))
    }

    @Test
    fun `random text returns unknown command`() {
        assertEquals(VoiceCommand.UNKNOWN, parser.parseCommand("hello world"))
        assertEquals(VoiceCommand.UNKNOWN, parser.parseCommand("random gibberish"))
    }

    @Test
    fun `case insensitivity works`() {
        assertEquals(VoiceCommand.SHOW_VITALS, parser.parseCommand("SHOW VITALS"))
        assertEquals(VoiceCommand.SHOW_VITALS, parser.parseCommand("Show Vitals"))
        assertEquals(VoiceCommand.SHOW_VITALS, parser.parseCommand("sHoW vItAlS"))
    }
}

/**
 * Voice command types recognized by MDx Vision
 */
enum class VoiceCommand {
    // Patient commands
    LOAD_PATIENT,
    FIND_PATIENT,
    SCAN_WRISTBAND,

    // Data display commands
    SHOW_VITALS,
    SHOW_ALLERGIES,
    SHOW_MEDICATIONS,
    SHOW_LABS,
    SHOW_PROCEDURES,
    SHOW_CONDITIONS,

    // Transcription commands
    LIVE_TRANSCRIBE,
    STOP_TRANSCRIPTION,

    // Note commands
    START_NOTE,
    STOP_NOTE,
    GENERATE_NOTE,
    SAVE_NOTE,
    PUSH_NOTE,

    // Summary commands
    BRIEF_ME,
    PATIENT_SUMMARY,

    // Navigation
    CLOSE,
    HELP,

    // Unknown
    UNKNOWN
}

/**
 * Voice command parser for MDx Vision
 * Extracts commands from speech recognition results with fuzzy matching
 */
class VoiceCommandParser {

    private val wakeWord = "minerva"
    private val wakeWordVariations = listOf("minerva", "m i n e r v a", "m.i.n.e.r.v.a")

    // Fuzzy matching for common misrecognitions
    private val patientVariations = listOf("patient", "patine", "patience", "patent")

    fun containsWakeWord(transcript: String): Boolean {
        val lower = transcript.lowercase()
        return wakeWordVariations.any { lower.contains(it) }
    }

    fun extractCommandAfterWakeWord(transcript: String): String {
        val lower = transcript.lowercase()
        for (variation in wakeWordVariations) {
            val index = lower.indexOf(variation)
            if (index >= 0) {
                return transcript.substring(index + variation.length).trim().lowercase()
            }
        }
        return transcript.trim().lowercase()
    }

    fun hasPatientWord(text: String): Boolean {
        val lower = text.lowercase()
        return patientVariations.any { lower.contains(it) }
    }

    fun parseCommand(transcript: String): VoiceCommand {
        val lower = transcript.lowercase().trim()

        if (lower.isEmpty()) return VoiceCommand.UNKNOWN

        return when {
            // Patient commands
            hasPatientWord(lower) && lower.contains("load") -> VoiceCommand.LOAD_PATIENT
            (hasPatientWord(lower) && lower.contains("find")) || lower.contains("search") -> VoiceCommand.FIND_PATIENT
            lower.contains("scan") && (lower.contains("wristband") || lower.contains("barcode")) -> VoiceCommand.SCAN_WRISTBAND

            // Data display
            lower.contains("vital") -> VoiceCommand.SHOW_VITALS
            lower.contains("allerg") -> VoiceCommand.SHOW_ALLERGIES
            lower.contains("med") && !lower.contains("medical") -> VoiceCommand.SHOW_MEDICATIONS
            lower.contains("lab") -> VoiceCommand.SHOW_LABS
            lower.contains("procedure") -> VoiceCommand.SHOW_PROCEDURES
            lower.contains("condition") -> VoiceCommand.SHOW_CONDITIONS

            // Transcription
            lower.contains("live transcri") || lower.contains("start transcri") ||
            lower.contains("transcribe") || lower.contains("start recording") -> VoiceCommand.LIVE_TRANSCRIBE
            lower.contains("stop transcri") || lower.contains("stop recording") -> VoiceCommand.STOP_TRANSCRIPTION

            // Notes
            lower.contains("start note") || lower.contains("start documentation") -> VoiceCommand.START_NOTE
            lower.contains("stop note") || lower.contains("end note") || lower.contains("finish note") -> VoiceCommand.STOP_NOTE
            lower.contains("generate note") || lower.contains("create note") ||
            lower.contains("looks good") || lower.contains("that's good") -> VoiceCommand.GENERATE_NOTE
            (lower.contains("save") && lower.contains("note")) || lower.contains("submit note") -> VoiceCommand.SAVE_NOTE
            lower.contains("push note") || lower.contains("send to ehr") || lower.contains("upload note") -> VoiceCommand.PUSH_NOTE

            // Summaries
            lower.contains("brief me") || lower.contains("briefing") || lower.contains("summarize") ||
            lower.contains("read patient") || lower.contains("patient brief") -> VoiceCommand.BRIEF_ME
            lower.contains("patient summary") || lower.contains("show summary") || lower.contains("overview") -> VoiceCommand.PATIENT_SUMMARY

            // Navigation
            lower == "close" || lower.contains("dismiss") || lower == "back" -> VoiceCommand.CLOSE
            lower == "help" || lower.contains("what can i say") || lower.contains("voice commands") -> VoiceCommand.HELP

            else -> VoiceCommand.UNKNOWN
        }
    }

    fun extractPatientName(transcript: String): String {
        val lower = transcript.lowercase()
        // Remove command words and patient variations
        var name = lower
        listOf("find", "search", "patient", "patine", "patience", "patent").forEach {
            name = name.replace(it, "")
        }
        return name.trim().split(" ").filter { it.isNotEmpty() }
            .joinToString(" ") { it.replaceFirstChar { c -> c.uppercase() } }
    }
}
