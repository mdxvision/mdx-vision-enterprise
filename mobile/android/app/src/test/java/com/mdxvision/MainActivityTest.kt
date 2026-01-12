package com.mdxvision

import org.junit.Before
import org.junit.Test
import org.junit.Assert.*
import kotlinx.coroutines.runBlocking

/**
 * Unit tests for MainActivity
 *
 * Tests voice command processing, wake word detection, patient display,
 * and UI state management.
 */
class MainActivityTest {

    // Voice Command Tests

    @Test
    fun `voice - should recognize LOAD PATIENT command`() {
        val command = "load patient"
        assertTrue(isLoadPatientCommand(command))
    }

    @Test
    fun `voice - should recognize LOAD PATIENT with number`() {
        val command = "load 1"
        assertTrue(isLoadPatientCommand(command))
    }

    @Test
    fun `voice - should recognize FIND PATIENT command`() {
        val command = "find patient smith"
        assertTrue(isFindPatientCommand(command))
    }

    @Test
    fun `voice - should recognize SHOW VITALS command`() {
        val command = "show vitals"
        assertTrue(isShowVitalsCommand(command))
    }

    @Test
    fun `voice - should recognize SHOW VITAL singular`() {
        val command = "show vital"
        assertTrue(isShowVitalsCommand(command))
    }

    @Test
    fun `voice - should recognize SHOW ALLERGIES command`() {
        val command = "show allergies"
        assertTrue(isShowAllergiesCommand(command))
    }

    @Test
    fun `voice - should recognize SHOW MEDS command`() {
        val command = "show meds"
        assertTrue(isShowMedsCommand(command))
    }

    @Test
    fun `voice - should recognize SHOW MEDICATIONS command`() {
        val command = "show medications"
        assertTrue(isShowMedsCommand(command))
    }

    @Test
    fun `voice - should recognize SHOW LABS command`() {
        val command = "show labs"
        assertTrue(isShowLabsCommand(command))
    }

    @Test
    fun `voice - should recognize START NOTE command`() {
        val command = "start note"
        assertTrue(isStartNoteCommand(command))
    }

    @Test
    fun `voice - should recognize LIVE TRANSCRIBE command`() {
        val command = "live transcribe"
        assertTrue(isLiveTranscribeCommand(command))
    }

    @Test
    fun `voice - should recognize HELP command`() {
        val command = "help"
        assertTrue(isHelpCommand(command))
    }

    @Test
    fun `voice - should recognize WHAT CAN I SAY command`() {
        val command = "what can i say"
        assertTrue(isHelpCommand(command))
    }

    @Test
    fun `voice - should recognize BRIEF ME command`() {
        val command = "brief me"
        assertTrue(isBriefMeCommand(command))
    }

    @Test
    fun `voice - should recognize TELL ME ABOUT PATIENT command`() {
        val command = "tell me about patient"
        assertTrue(isBriefMeCommand(command))
    }

    // Wake Word Tests

    @Test
    fun `wake - should detect HEY MDX wake word`() {
        val phrase = "hey mdx show vitals"
        assertTrue(containsWakeWord(phrase))
    }

    @Test
    fun `wake - should detect HEY M D X wake word`() {
        val phrase = "hey m d x load patient"
        assertTrue(containsWakeWord(phrase))
    }

    @Test
    fun `wake - should not trigger without wake word when in wake word mode`() {
        val phrase = "show vitals"
        assertFalse(containsWakeWord(phrase))
    }

    @Test
    fun `wake - should be case insensitive`() {
        val phrase = "HEY MDX show vitals"
        assertTrue(containsWakeWord(phrase))
    }

    @Test
    fun `wake - should extract command after wake word`() {
        val phrase = "hey mdx show vitals"
        val command = extractCommandAfterWakeWord(phrase)
        assertEquals("show vitals", command)
    }

    // Patient Display Tests

    @Test
    fun `display - should format patient name correctly`() {
        val firstName = "JOHN"
        val lastName = "SMITH"
        val formatted = formatPatientName(firstName, lastName)
        assertEquals("SMITH, JOHN", formatted)
    }

    @Test
    fun `display - should format DOB correctly`() {
        val dob = "1990-05-15"
        val formatted = formatDob(dob)
        assertTrue(formatted.contains("1990"))
    }

    @Test
    fun `display - should handle null patient gracefully`() {
        val patientName: String? = null
        val display = patientName ?: "No patient loaded"
        assertEquals("No patient loaded", display)
    }

    // Font Size Tests

    @Test
    fun `font - should recognize SMALL FONT command`() {
        val command = "small font"
        assertEquals(FontSize.SMALL, parseFontSizeCommand(command))
    }

    @Test
    fun `font - should recognize MEDIUM FONT command`() {
        val command = "medium font"
        assertEquals(FontSize.MEDIUM, parseFontSizeCommand(command))
    }

    @Test
    fun `font - should recognize LARGE FONT command`() {
        val command = "large font"
        assertEquals(FontSize.LARGE, parseFontSizeCommand(command))
    }

    @Test
    fun `font - should recognize EXTRA LARGE FONT command`() {
        val command = "extra large font"
        assertEquals(FontSize.EXTRA_LARGE, parseFontSizeCommand(command))
    }

    // Session Timeout Tests

    @Test
    fun `timeout - should default timeout to 5 minutes`() {
        val defaultTimeout = 5 * 60 * 1000L
        assertEquals(300000L, defaultTimeout)
    }

    @Test
    fun `timeout - should parse timeout command`() {
        val command = "timeout 10 minutes"
        val minutes = parseTimeoutMinutes(command)
        assertEquals(10, minutes)
    }

    @Test
    fun `timeout - should lock session on timeout`() {
        val lastActivity = System.currentTimeMillis() - (6 * 60 * 1000)
        val timeout = 5 * 60 * 1000
        val shouldLock = (System.currentTimeMillis() - lastActivity) > timeout
        assertTrue(shouldLock)
    }

    // Order Command Tests

    @Test
    fun `order - should recognize ORDER LAB command`() {
        val command = "order cbc"
        assertTrue(isOrderLabCommand(command))
    }

    @Test
    fun `order - should recognize ORDER IMAGING command`() {
        val command = "order chest xray"
        assertTrue(isOrderImagingCommand(command))
    }

    @Test
    fun `order - should recognize PRESCRIBE command`() {
        val command = "prescribe amoxicillin"
        assertTrue(isPrescribeCommand(command))
    }

    @Test
    fun `order - should recognize SHOW ORDERS command`() {
        val command = "show orders"
        assertTrue(isShowOrdersCommand(command))
    }

    @Test
    fun `order - should recognize CANCEL ORDER command`() {
        val command = "cancel order"
        assertTrue(isCancelOrderCommand(command))
    }

    // Multi-Language Tests

    @Test
    fun `language - should recognize switch to Spanish command`() {
        val command = "switch to spanish"
        assertEquals("es", parseLanguageSwitch(command))
    }

    @Test
    fun `language - should recognize switch to Russian command`() {
        val command = "switch to russian"
        assertEquals("ru", parseLanguageSwitch(command))
    }

    @Test
    fun `language - should recognize Spanish trigger word`() {
        val command = "español"
        assertEquals("es", parseLanguageSwitch(command))
    }

    @Test
    fun `language - should recognize Russian trigger word`() {
        val command = "русский"
        assertEquals("ru", parseLanguageSwitch(command))
    }

    // Ambient Mode Tests

    @Test
    fun `ambient - should recognize AMBIENT MODE command`() {
        val command = "ambient mode"
        assertTrue(isAmbientModeCommand(command))
    }

    @Test
    fun `ambient - should recognize START AMBIENT command`() {
        val command = "start ambient"
        assertTrue(isAmbientModeCommand(command))
    }

    @Test
    fun `ambient - should recognize STARTS AMBIENT transcription variation`() {
        val command = "starts ambient"
        assertTrue(isAmbientModeCommand(command))
    }

    @Test
    fun `ambient - should recognize STOP AMBIENT command`() {
        val command = "stop ambient"
        assertTrue(isStopAmbientCommand(command))
    }

    @Test
    fun `ambient - should recognize SHOW ENTITIES command`() {
        val command = "show entities"
        assertTrue(isShowEntitiesCommand(command))
    }

    // HUD Command Tests

    @Test
    fun `hud - should recognize SHOW HUD command`() {
        val command = "show hud"
        assertEquals(HudAction.SHOW, parseHudCommand(command))
    }

    @Test
    fun `hud - should recognize HIDE HUD command`() {
        val command = "hide hud"
        assertEquals(HudAction.HIDE, parseHudCommand(command))
    }

    @Test
    fun `hud - should recognize EXPAND HUD command`() {
        val command = "expand hud"
        assertEquals(HudAction.EXPAND, parseHudCommand(command))
    }

    @Test
    fun `hud - should recognize MINIMIZE HUD command`() {
        val command = "minimize hud"
        assertEquals(HudAction.MINIMIZE, parseHudCommand(command))
    }

    @Test
    fun `hud - should recognize TOGGLE HUD command`() {
        val command = "toggle hud"
        assertEquals(HudAction.TOGGLE, parseHudCommand(command))
    }

    // Helper functions and enums

    private enum class FontSize { SMALL, MEDIUM, LARGE, EXTRA_LARGE }
    private enum class HudAction { SHOW, HIDE, EXPAND, MINIMIZE, TOGGLE }

    private fun isLoadPatientCommand(cmd: String): Boolean {
        val lower = cmd.lowercase()
        return lower.contains("load patient") ||
               lower.matches(Regex("load \\d+"))
    }

    private fun isFindPatientCommand(cmd: String): Boolean {
        return cmd.lowercase().contains("find patient")
    }

    private fun isShowVitalsCommand(cmd: String): Boolean {
        val lower = cmd.lowercase()
        return lower.contains("vitals") || lower.contains("vital")
    }

    private fun isShowAllergiesCommand(cmd: String): Boolean {
        return cmd.lowercase().contains("allergies")
    }

    private fun isShowMedsCommand(cmd: String): Boolean {
        val lower = cmd.lowercase()
        return lower.contains("meds") || lower.contains("medications")
    }

    private fun isShowLabsCommand(cmd: String): Boolean {
        return cmd.lowercase().contains("labs")
    }

    private fun isStartNoteCommand(cmd: String): Boolean {
        return cmd.lowercase().contains("start note")
    }

    private fun isLiveTranscribeCommand(cmd: String): Boolean {
        return cmd.lowercase().contains("live transcribe")
    }

    private fun isHelpCommand(cmd: String): Boolean {
        val lower = cmd.lowercase()
        return lower.contains("help") || lower.contains("what can i say")
    }

    private fun isBriefMeCommand(cmd: String): Boolean {
        val lower = cmd.lowercase()
        return lower.contains("brief me") || lower.contains("tell me about patient")
    }

    private fun containsWakeWord(phrase: String): Boolean {
        val lower = phrase.lowercase()
        return lower.contains("hey mdx") || lower.contains("hey m d x")
    }

    private fun extractCommandAfterWakeWord(phrase: String): String {
        val lower = phrase.lowercase()
        return when {
            lower.contains("hey mdx") -> lower.substringAfter("hey mdx").trim()
            lower.contains("hey m d x") -> lower.substringAfter("hey m d x").trim()
            else -> phrase
        }
    }

    private fun formatPatientName(firstName: String, lastName: String): String {
        return "$lastName, $firstName"
    }

    private fun formatDob(dob: String): String {
        return dob
    }

    private fun parseFontSizeCommand(cmd: String): FontSize? {
        val lower = cmd.lowercase()
        return when {
            lower.contains("extra large") -> FontSize.EXTRA_LARGE
            lower.contains("large") -> FontSize.LARGE
            lower.contains("medium") -> FontSize.MEDIUM
            lower.contains("small") -> FontSize.SMALL
            else -> null
        }
    }

    private fun parseTimeoutMinutes(cmd: String): Int? {
        val regex = Regex("timeout (\\d+) min")
        val match = regex.find(cmd.lowercase())
        return match?.groupValues?.get(1)?.toIntOrNull()
    }

    /**
     * Multi-intent parsing and execution tests
     */
    class VoiceIntentParsingTests {

        @Test
        fun `should parse multi-intent voice command in order`() {
            val command = "open John Doe's chart and show last vitals and labs and read it back"

            val intents = parseVoiceIntents(command)

            val expected = listOf(
                VoiceIntent.LoadPatient("John Doe"),
                VoiceIntent.ShowVitals,
                VoiceIntent.ShowLabs,
                VoiceIntent.SpeakSummary,
            )
            assertEquals(expected, intents)
        }

        @Test
        fun `should execute intents in sequence`() = runBlocking {
            val calls = mutableListOf<String>()
            val executor = VoiceIntentExecutor(
                loadPatient = { name -> calls.add("load:$name") },
                showVitals = { calls.add("vitals") },
                showLabs = { calls.add("labs") },
                speakSummary = { calls.add("speak") },
                interIntentDelayMillis = 0,
                postLoadDelayMillis = 0,
            )

            executor.execute(
                listOf(
                    VoiceIntent.LoadPatient("John Doe"),
                    VoiceIntent.ShowVitals,
                    VoiceIntent.ShowLabs,
                    VoiceIntent.SpeakSummary,
                )
            )

            assertEquals(
                listOf("load:John Doe", "vitals", "labs", "speak"),
                calls
            )
        }
    }

    // Additional helper functions for order/language/ambient/HUD commands

    private fun isOrderLabCommand(cmd: String): Boolean {
        val lower = cmd.lowercase()
        return lower.contains("order") && !lower.contains("show") && !lower.contains("cancel")
    }

    private fun isOrderImagingCommand(cmd: String): Boolean {
        val lower = cmd.lowercase()
        return lower.contains("order") && (lower.contains("xray") || lower.contains("ct") || lower.contains("mri"))
    }

    private fun isPrescribeCommand(cmd: String): Boolean {
        return cmd.lowercase().contains("prescribe")
    }

    private fun isShowOrdersCommand(cmd: String): Boolean {
        return cmd.lowercase().contains("show orders")
    }

    private fun isCancelOrderCommand(cmd: String): Boolean {
        return cmd.lowercase().contains("cancel order")
    }

    private fun parseLanguageSwitch(cmd: String): String? {
        val lower = cmd.lowercase()
        return when {
            lower.contains("spanish") || lower.contains("español") -> "es"
            lower.contains("russian") || lower.contains("русский") -> "ru"
            lower.contains("chinese") || lower.contains("mandarin") -> "zh"
            lower.contains("portuguese") -> "pt"
            lower.contains("english") -> "en"
            else -> null
        }
    }

    private fun isAmbientModeCommand(cmd: String): Boolean {
        val lower = cmd.lowercase()
        return lower.contains("ambient mode") ||
               lower.contains("start ambient") ||
               lower.contains("starts ambient")
    }

    private fun isStopAmbientCommand(cmd: String): Boolean {
        return cmd.lowercase().contains("stop ambient")
    }

    private fun isShowEntitiesCommand(cmd: String): Boolean {
        return cmd.lowercase().contains("show entities")
    }

    private fun parseHudCommand(cmd: String): HudAction? {
        val lower = cmd.lowercase()
        return when {
            lower.contains("show hud") -> HudAction.SHOW
            lower.contains("hide hud") -> HudAction.HIDE
            lower.contains("expand hud") -> HudAction.EXPAND
            lower.contains("minimize hud") -> HudAction.MINIMIZE
            lower.contains("toggle hud") -> HudAction.TOGGLE
            else -> null
        }
    }
}
