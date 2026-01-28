package com.mdxvision.voice

import android.util.Log
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

/**
 * VoiceCommandParser - Extracted from MainActivity (Issue #31)
 *
 * Handles parsing of voice commands including:
 * - Built-in commands (show vitals, load patient, etc.)
 * - Custom macros via backend Voice Macros API (Feature #99)
 * - Multi-intent commands ("load patient then show vitals")
 * - Fuzzy matching for misheard commands
 *
 * Patent Reference: US 15/237,980 - Claims 1-2 (Voice commands via microphone)
 */
class VoiceCommandParser(
    private val baseUrl: String = "http://10.0.2.2:8002"  // Android emulator → localhost
) {
    companion object {
        private const val TAG = "VoiceCommandParser"

        // Common mishearings from AssemblyAI/Deepgram
        private val MISHEARINGS = mapOf(
            // Minerva
            "murder" to "minerva",
            "marvel" to "minerva",
            "menurva" to "minerva",
            "minerba" to "minerva",
            "minurva" to "minerva",
            // Cerner
            "center" to "cerner",
            "sinner" to "cerner",
            "sink" to "cerner",
            "cenner" to "cerner",
            "colonial" to "cerner",
            "corner" to "cerner",
            // Patient
            "patine" to "patient",
            "patience" to "patient",
            "patent" to "patient",
            // Vitals
            "vitales" to "vitals",
            "bytals" to "vitals",
        )
    }

    /**
     * Voice Intent - represents a parsed voice command
     */
    sealed class VoiceIntent {
        data class LoadPatient(val identifier: String) : VoiceIntent()
        data class SearchPatient(val query: String) : VoiceIntent()
        data class ShowSection(val section: String) : VoiceIntent()  // vitals, labs, allergies, etc.
        data class SwitchEhr(val ehr: String) : VoiceIntent()  // cerner, epic
        data class ActivateMinerva(val query: String?) : VoiceIntent()
        data class Order(val orderType: String, val details: String) : VoiceIntent()  // lab, imaging, medication
        data class PushVital(val vitalType: String, val value: String) : VoiceIntent()
        data class AddAllergy(val substance: String) : VoiceIntent()
        object StartTranscription : VoiceIntent()
        object StopTranscription : VoiceIntent()
        object StartDocumentation : VoiceIntent()
        object GenerateNote : VoiceIntent()
        object ShowHelp : VoiceIntent()
        object ShowWorklist : VoiceIntent()
        data class CheckIn(val patientIndex: Int) : VoiceIntent()
        data class MacroExpansion(val macroId: String, val expansionText: String?, val action: MacroAction?) : VoiceIntent()
        data class CreateMacro(val trigger: String, val actions: List<String>) : VoiceIntent()
        data class Custom(val command: String) : VoiceIntent()
        object Unknown : VoiceIntent()
    }

    /**
     * Macro action from backend
     */
    data class MacroAction(
        val type: String,  // ORDER_SET, NAVIGATION, CUSTOM
        val payload: JSONObject?
    )

    /**
     * Parse result containing intents and metadata
     */
    data class ParseResult(
        val intents: List<VoiceIntent>,
        val originalText: String,
        val normalizedText: String,
        val confidence: Float = 1.0f,
        val macroExpanded: Boolean = false
    )

    /**
     * Main parsing function - parses voice input into list of intents
     */
    suspend fun parse(utterance: String, clinicianId: String = "default"): ParseResult {
        val original = utterance.trim()
        val normalized = normalizeText(original)
        val lower = normalized.lowercase()

        Log.d(TAG, "Parsing: '$original' → normalized: '$normalized'")

        // Check for macro expansion first (backend Voice Macros API)
        val macroResult = checkMacroExpansion(lower, clinicianId)
        if (macroResult != null) {
            Log.d(TAG, "Macro matched: ${macroResult.first}")
            return ParseResult(
                intents = listOf(macroResult.first),
                originalText = original,
                normalizedText = normalized,
                macroExpanded = true
            )
        }

        // Parse multi-intent commands
        val intents = parseMultiIntent(lower, original)

        return ParseResult(
            intents = intents.ifEmpty { listOf(VoiceIntent.Unknown) },
            originalText = original,
            normalizedText = normalized
        )
    }

    /**
     * Normalize text by fixing common mishearings
     */
    private fun normalizeText(text: String): String {
        var normalized = text
        MISHEARINGS.forEach { (wrong, correct) ->
            normalized = normalized.replace(wrong, correct, ignoreCase = true)
        }
        return normalized
    }

    /**
     * Parse multi-intent commands (e.g., "load patient then show vitals")
     */
    private fun parseMultiIntent(lower: String, original: String): List<VoiceIntent> {
        // Split by conjunctions
        val clauses = lower
            .replace(" and then ", "|")
            .replace(" then ", "|")
            .replace(" and ", "|")
            .split("|")
            .map { it.trim() }
            .filter { it.isNotEmpty() }

        val intents = mutableListOf<VoiceIntent>()
        for (clause in clauses) {
            val intent = parseSingleIntent(clause, original)
            if (intent != VoiceIntent.Unknown) {
                intents.add(intent)
            }
        }
        return intents
    }

    /**
     * Parse a single intent from a clause
     */
    private fun parseSingleIntent(lower: String, original: String): VoiceIntent {
        return when {
            // ═══ PATIENT LOADING ═══
            lower.contains("load patient") || lower.contains("load patine") -> {
                val id = extractPatientId(original)
                VoiceIntent.LoadPatient(id ?: "default")
            }
            lower.contains("load") && lower.matches(Regex(".*load\\s+(\\d+).*")) -> {
                val match = Regex("load\\s+(\\d+)").find(lower)
                val index = match?.groupValues?.get(1) ?: "1"
                VoiceIntent.LoadPatient(index)
            }

            // ═══ PATIENT SEARCH ═══
            lower.contains("search") || lower.contains("find patient") -> {
                val query = lower.replace(Regex("(search|find|patient)"), "").trim()
                VoiceIntent.SearchPatient(query.ifEmpty { "" })
            }

            // ═══ SHOW DATA SECTIONS ═══
            lower.contains("show vitals") || lower == "vitals" -> VoiceIntent.ShowSection("vitals")
            lower.contains("show labs") || lower == "labs" || lower.contains("lab results") -> VoiceIntent.ShowSection("labs")
            lower.contains("show allergies") || lower == "allergies" -> VoiceIntent.ShowSection("allergies")
            lower.contains("show meds") || lower.contains("medications") -> VoiceIntent.ShowSection("medications")
            lower.contains("show conditions") || lower.contains("diagnoses") -> VoiceIntent.ShowSection("conditions")
            lower.contains("show procedures") -> VoiceIntent.ShowSection("procedures")
            lower.contains("show immunizations") -> VoiceIntent.ShowSection("immunizations")
            lower.contains("show summary") || lower.contains("patient summary") -> VoiceIntent.ShowSection("summary")

            // ═══ WORKLIST ═══
            lower.contains("show worklist") || lower.contains("worklist") || lower.contains("work list") -> VoiceIntent.ShowWorklist
            lower.contains("check in") && lower.matches(Regex(".*check in\\s+(\\d+).*")) -> {
                val match = Regex("check in\\s+(\\d+)").find(lower)
                val index = match?.groupValues?.get(1)?.toIntOrNull() ?: 1
                VoiceIntent.CheckIn(index)
            }

            // ═══ EHR SWITCHING ═══
            lower.contains("switch to epic") || lower.contains("use epic") -> VoiceIntent.SwitchEhr("epic")
            lower.contains("switch to cerner") || lower.contains("use cerner") -> VoiceIntent.SwitchEhr("cerner")

            // ═══ MINERVA AI ═══
            lower.contains("hey minerva") || lower.contains("hi minerva") || lower.startsWith("minerva") -> {
                val query = lower.replace(Regex("(hey|hi|minerva)[,.]?"), "").trim()
                VoiceIntent.ActivateMinerva(query.ifEmpty { null })
            }

            // ═══ ORDERS ═══
            lower.contains("order cbc") || lower.contains("order complete blood") -> VoiceIntent.Order("lab", "CBC")
            lower.contains("order bmp") || lower.contains("order basic metabolic") -> VoiceIntent.Order("lab", "BMP")
            lower.contains("order cmp") || lower.contains("order comprehensive") -> VoiceIntent.Order("lab", "CMP")
            lower.contains("order lipid") -> VoiceIntent.Order("lab", "LIPID")
            lower.contains("order troponin") -> VoiceIntent.Order("lab", "TROP")
            lower.contains("order chest x-ray") || lower.contains("order cxr") -> VoiceIntent.Order("imaging", "CXR")
            lower.contains("order ct") -> VoiceIntent.Order("imaging", "CT")
            lower.contains("order mri") -> VoiceIntent.Order("imaging", "MRI")
            lower.contains("order ekg") || lower.contains("order ecg") -> VoiceIntent.Order("imaging", "EKG")
            lower.matches(Regex("order\\s+(.+)")) -> {
                val match = Regex("order\\s+(.+)").find(lower)
                VoiceIntent.Order("general", match?.groupValues?.get(1) ?: "")
            }

            // ═══ VITALS PUSH ═══
            lower.contains("push vital") || lower.contains("record vital") -> {
                val vitalMatch = Regex("(blood pressure|bp|heart rate|hr|temperature|temp|oxygen|spo2|weight)\\s*(\\d+[/.]?\\d*)").find(lower)
                if (vitalMatch != null) {
                    VoiceIntent.PushVital(vitalMatch.groupValues[1], vitalMatch.groupValues[2])
                } else {
                    VoiceIntent.Custom(lower)
                }
            }

            // ═══ ALLERGIES ═══
            lower.contains("add allergy") || lower.contains("allergic to") -> {
                val substance = lower.replace(Regex("(add allergy|allergic to|patient is)"), "").trim()
                VoiceIntent.AddAllergy(substance)
            }

            // ═══ TRANSCRIPTION ═══
            lower.contains("start transcription") || lower.contains("live transcribe") || lower.contains("transcribe") -> VoiceIntent.StartTranscription
            lower.contains("stop transcription") || lower.contains("end transcription") -> VoiceIntent.StopTranscription

            // ═══ DOCUMENTATION ═══
            lower.contains("start documentation") || lower.contains("start note") || lower.contains("begin note") -> VoiceIntent.StartDocumentation
            lower.contains("generate note") || lower.contains("create note") || lower.contains("make note") -> VoiceIntent.GenerateNote

            // ═══ HELP ═══
            lower.contains("help") || lower.contains("what can i say") || lower.contains("commands") -> VoiceIntent.ShowHelp

            // ═══ CUSTOM MACRO CREATION ═══
            lower.matches(Regex("(create|make|add) (command|macro|shortcut) (.+?) (that does?|to do|:) (.+)")) -> {
                val match = Regex("(create|make|add) (command|macro|shortcut) (.+?) (that does?|to do|:) (.+)").find(lower)
                if (match != null) {
                    val trigger = match.groupValues[3].trim()
                    val actionsStr = match.groupValues[5].trim()
                    val actions = parseActionList(actionsStr)
                    VoiceIntent.CreateMacro(trigger, actions)
                } else {
                    VoiceIntent.Unknown
                }
            }

            else -> VoiceIntent.Unknown
        }
    }

    /**
     * Extract patient ID from utterance
     */
    private fun extractPatientId(text: String): String? {
        // Look for numeric ID
        val numericMatch = Regex("\\b(\\d{5,})\\b").find(text)
        if (numericMatch != null) return numericMatch.groupValues[1]

        // Look for "patient X" where X is a number
        val indexMatch = Regex("patient\\s+(\\d+)").find(text.lowercase())
        if (indexMatch != null) return indexMatch.groupValues[1]

        return null
    }

    /**
     * Parse action list from voice input
     */
    private fun parseActionList(actionsStr: String): List<String> {
        return actionsStr
            .replace(" and then ", "|")
            .replace(" then ", "|")
            .replace(" and ", "|")
            .replace(", ", "|")
            .split("|")
            .map { it.trim() }
            .filter { it.isNotEmpty() }
    }

    /**
     * Check if phrase matches a backend Voice Macro (Feature #99)
     */
    private suspend fun checkMacroExpansion(phrase: String, clinicianId: String): Pair<VoiceIntent.MacroExpansion, JSONObject>? {
        return withContext(Dispatchers.IO) {
            try {
                val url = URL("$baseUrl/api/v1/macros/expand")
                val connection = url.openConnection() as HttpURLConnection
                connection.requestMethod = "POST"
                connection.setRequestProperty("Content-Type", "application/json")
                connection.setRequestProperty("X-Clinician-Id", clinicianId)
                connection.doOutput = true
                connection.connectTimeout = 3000
                connection.readTimeout = 3000

                val body = JSONObject().apply {
                    put("phrase", phrase)
                }

                connection.outputStream.bufferedWriter().use { it.write(body.toString()) }

                if (connection.responseCode == 200) {
                    val response = connection.inputStream.bufferedReader().readText()
                    val json = JSONObject(response)

                    if (json.optBoolean("found", false)) {
                        val macroId = json.optString("macro_id", "")
                        val expansionText = json.optString("expansion_text", null)
                        val actionJson = json.optJSONObject("action")
                        val action = actionJson?.let {
                            MacroAction(
                                type = it.optString("type", ""),
                                payload = it.optJSONObject("payload")
                            )
                        }

                        Log.d(TAG, "Macro expanded: $macroId")
                        return@withContext Pair(
                            VoiceIntent.MacroExpansion(macroId, expansionText, action),
                            json
                        )
                    }
                }
                null
            } catch (e: Exception) {
                Log.w(TAG, "Macro expansion check failed: ${e.message}")
                null
            }
        }
    }

    /**
     * Get available macros from backend
     */
    suspend fun getAvailableMacros(clinicianId: String = "default", specialty: String? = null): List<JSONObject> {
        return withContext(Dispatchers.IO) {
            try {
                val urlStr = if (specialty != null) {
                    "$baseUrl/api/v1/macros?specialty=$specialty"
                } else {
                    "$baseUrl/api/v1/macros"
                }
                val url = URL(urlStr)
                val connection = url.openConnection() as HttpURLConnection
                connection.setRequestProperty("X-Clinician-Id", clinicianId)
                connection.connectTimeout = 5000

                if (connection.responseCode == 200) {
                    val response = connection.inputStream.bufferedReader().readText()
                    val json = JSONObject(response)
                    val macrosArray = json.optJSONArray("macros") ?: JSONArray()

                    (0 until macrosArray.length()).map { macrosArray.getJSONObject(it) }
                } else {
                    emptyList()
                }
            } catch (e: Exception) {
                Log.w(TAG, "Failed to fetch macros: ${e.message}")
                emptyList()
            }
        }
    }

    /**
     * Create a custom macro via backend API
     */
    suspend fun createMacro(
        clinicianId: String,
        triggerPhrase: String,
        expansionText: String? = null,
        actionType: String? = null,
        actionPayload: JSONObject? = null
    ): Boolean {
        return withContext(Dispatchers.IO) {
            try {
                val url = URL("$baseUrl/api/v1/macros")
                val connection = url.openConnection() as HttpURLConnection
                connection.requestMethod = "POST"
                connection.setRequestProperty("Content-Type", "application/json")
                connection.setRequestProperty("X-Clinician-Id", clinicianId)
                connection.doOutput = true

                val body = JSONObject().apply {
                    put("trigger_phrase", triggerPhrase)
                    put("macro_type", when {
                        expansionText != null && actionType != null -> "hybrid"
                        actionType != null -> "action"
                        else -> "text_expansion"
                    })
                    expansionText?.let { put("expansion_text", it) }
                    actionType?.let { put("action_type", it) }
                    actionPayload?.let { put("action_payload", it) }
                }

                connection.outputStream.bufferedWriter().use { it.write(body.toString()) }

                connection.responseCode == 200 || connection.responseCode == 201
            } catch (e: Exception) {
                Log.e(TAG, "Failed to create macro: ${e.message}")
                false
            }
        }
    }
}
