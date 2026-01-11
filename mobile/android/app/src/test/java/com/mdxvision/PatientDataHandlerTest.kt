package com.mdxvision

import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test

/**
 * Unit tests for patient data parsing and handling in MDx Vision
 */
class PatientDataHandlerTest {

    private lateinit var handler: PatientDataHandler

    @Before
    fun setUp() {
        handler = PatientDataHandler()
    }

    // ==================== PATIENT PARSING TESTS ====================

    @Test
    fun `parses patient name correctly`() {
        val json = createPatientJson(name = "SMITH, JOHN")
        val patient = handler.parsePatient(json)
        assertEquals("SMITH, JOHN", patient.name)
    }

    @Test
    fun `parses patient demographics`() {
        val json = createPatientJson(
            name = "DOE, JANE",
            dob = "1990-05-15",
            gender = "female"
        )
        val patient = handler.parsePatient(json)
        assertEquals("1990-05-15", patient.dateOfBirth)
        assertEquals("female", patient.gender)
    }

    @Test
    fun `parses patient ID`() {
        val json = createPatientJson(patientId = "12724066")
        val patient = handler.parsePatient(json)
        assertEquals("12724066", patient.id)
    }

    // ==================== ALLERGIES TESTS ====================

    @Test
    fun `parses allergies list`() {
        val json = createPatientJson(
            allergies = listOf(
                Triple("Penicillin", "high", "Anaphylaxis"),
                Triple("Sulfa drugs", "moderate", "Rash")
            )
        )
        val patient = handler.parsePatient(json)
        assertEquals(2, patient.allergies.size)
        assertEquals("Penicillin", patient.allergies[0].substance)
        assertEquals("high", patient.allergies[0].severity)
    }

    @Test
    fun `identifies critical allergies`() {
        val json = createPatientJson(
            allergies = listOf(
                Triple("Penicillin", "high", "Anaphylaxis"),
                Triple("Aspirin", "low", "Upset stomach")
            )
        )
        val patient = handler.parsePatient(json)
        val critical = patient.allergies.filter { it.severity == "high" }
        assertEquals(1, critical.size)
        assertEquals("Penicillin", critical[0].substance)
    }

    @Test
    fun `handles empty allergies`() {
        val json = createPatientJson(allergies = emptyList())
        val patient = handler.parsePatient(json)
        assertTrue(patient.allergies.isEmpty())
    }

    // ==================== VITALS TESTS ====================

    @Test
    fun `parses vitals correctly`() {
        val json = createPatientJson(
            vitals = listOf(
                VitalData("Blood Pressure", "142/88", "mmHg", true),
                VitalData("Heart Rate", "92", "bpm", false)
            )
        )
        val patient = handler.parsePatient(json)
        assertEquals(2, patient.vitals.size)
        assertEquals("Blood Pressure", patient.vitals[0].name)
        assertEquals("142/88", patient.vitals[0].value)
    }

    @Test
    fun `identifies critical vitals`() {
        val json = createPatientJson(
            vitals = listOf(
                VitalData("Blood Pressure", "182/95", "mmHg", true),
                VitalData("SpO2", "85", "%", true),
                VitalData("Temperature", "98.6", "F", false)
            )
        )
        val patient = handler.parsePatient(json)
        val critical = patient.vitals.filter { it.isCritical }
        assertEquals(2, critical.size)
    }

    // ==================== MEDICATIONS TESTS ====================

    @Test
    fun `parses medications list`() {
        val json = createPatientJson(
            medications = listOf("Metformin 500mg BID", "Lisinopril 10mg daily")
        )
        val patient = handler.parsePatient(json)
        assertEquals(2, patient.medications.size)
        assertTrue(patient.medications.contains("Metformin 500mg BID"))
    }

    // ==================== CONDITIONS TESTS ====================

    @Test
    fun `parses conditions list`() {
        val json = createPatientJson(
            conditions = listOf("Type 2 Diabetes Mellitus", "Essential Hypertension")
        )
        val patient = handler.parsePatient(json)
        assertEquals(2, patient.conditions.size)
    }

    // ==================== CRITICAL VALUE DETECTION ====================

    @Test
    fun `detects critical blood pressure - high`() {
        assertTrue(handler.isCriticalBP("185/95"))
        assertTrue(handler.isCriticalBP("142/110"))
    }

    @Test
    fun `detects critical blood pressure - low`() {
        assertTrue(handler.isCriticalBP("85/50"))
        assertTrue(handler.isCriticalBP("88/55"))
    }

    @Test
    fun `normal blood pressure not critical`() {
        assertFalse(handler.isCriticalBP("120/80"))
        assertFalse(handler.isCriticalBP("135/85"))
    }

    @Test
    fun `detects critical heart rate - high`() {
        assertTrue(handler.isCriticalHR(155))
        assertTrue(handler.isCriticalHR(180))
    }

    @Test
    fun `detects critical heart rate - low`() {
        assertTrue(handler.isCriticalHR(35))
        assertTrue(handler.isCriticalHR(39))  // HR < 40 is critical
    }

    @Test
    fun `normal heart rate not critical`() {
        assertFalse(handler.isCriticalHR(72))
        assertFalse(handler.isCriticalHR(90))
    }

    @Test
    fun `detects critical SpO2`() {
        assertTrue(handler.isCriticalSpO2(85))
        assertTrue(handler.isCriticalSpO2(87))
        assertFalse(handler.isCriticalSpO2(95))
        assertFalse(handler.isCriticalSpO2(98))
    }

    @Test
    fun `detects critical temperature`() {
        assertTrue(handler.isCriticalTemp(104.5))
        assertTrue(handler.isCriticalTemp(95.0))
        assertFalse(handler.isCriticalTemp(98.6))
        assertFalse(handler.isCriticalTemp(99.5))
    }

    // ==================== DISPLAY TEXT FORMATTING ====================

    @Test
    fun `formats patient display text`() {
        val json = createPatientJson(
            name = "SMITH, JOHN",
            dob = "1990-05-15",
            gender = "male"
        )
        val patient = handler.parsePatient(json)
        val display = handler.formatDisplayText(patient)
        assertTrue(display.contains("SMITH, JOHN"))
        assertTrue(display.contains("1990-05-15"))
    }

    @Test
    fun `formats allergy warnings`() {
        val json = createPatientJson(
            allergies = listOf(
                Triple("Penicillin", "high", "Anaphylaxis")
            )
        )
        val patient = handler.parsePatient(json)
        val warnings = handler.formatAllergyWarnings(patient)
        assertTrue(warnings.contains("Penicillin"))
        assertTrue(warnings.contains("Anaphylaxis"))
    }

    // ==================== HELPER METHODS ====================

    private fun createPatientJson(
        patientId: String = "12345",
        name: String = "TEST, PATIENT",
        dob: String = "2000-01-01",
        gender: String = "unknown",
        allergies: List<Triple<String, String, String>> = emptyList(),
        vitals: List<VitalData> = emptyList(),
        medications: List<String> = emptyList(),
        conditions: List<String> = emptyList()
    ): JSONObject {
        return JSONObject().apply {
            put("patient_id", patientId)
            put("name", name)
            put("date_of_birth", dob)
            put("gender", gender)
            put("allergies", JSONArray().apply {
                allergies.forEach { (substance, severity, reaction) ->
                    put(JSONObject().apply {
                        put("substance", substance)
                        put("severity", severity)
                        put("reaction", reaction)
                    })
                }
            })
            put("vitals", JSONArray().apply {
                vitals.forEach { vital ->
                    put(JSONObject().apply {
                        put("name", vital.name)
                        put("value", vital.value)
                        put("unit", vital.unit)
                        put("is_critical", vital.isCritical)
                    })
                }
            })
            put("medications", JSONArray(medications))
            put("conditions", JSONArray(conditions))
        }
    }

    private data class VitalData(
        val name: String,
        val value: String,
        val unit: String,
        val isCritical: Boolean
    )
}

// ==================== DATA CLASSES ====================

data class Patient(
    val id: String,
    val name: String,
    val dateOfBirth: String,
    val gender: String,
    val allergies: List<Allergy>,
    val vitals: List<Vital>,
    val medications: List<String>,
    val conditions: List<String>
)

data class Allergy(
    val substance: String,
    val severity: String,
    val reaction: String
)

data class Vital(
    val name: String,
    val value: String,
    val unit: String,
    val isCritical: Boolean
)

// ==================== HANDLER CLASS ====================

class PatientDataHandler {

    fun parsePatient(json: JSONObject): Patient {
        val allergies = mutableListOf<Allergy>()
        val allergiesArray = json.optJSONArray("allergies") ?: JSONArray()
        for (i in 0 until allergiesArray.length()) {
            val a = allergiesArray.getJSONObject(i)
            allergies.add(Allergy(
                substance = a.optString("substance", ""),
                severity = a.optString("severity", ""),
                reaction = a.optString("reaction", "")
            ))
        }

        val vitals = mutableListOf<Vital>()
        val vitalsArray = json.optJSONArray("vitals") ?: JSONArray()
        for (i in 0 until vitalsArray.length()) {
            val v = vitalsArray.getJSONObject(i)
            vitals.add(Vital(
                name = v.optString("name", ""),
                value = v.optString("value", ""),
                unit = v.optString("unit", ""),
                isCritical = v.optBoolean("is_critical", false)
            ))
        }

        val medications = mutableListOf<String>()
        val medsArray = json.optJSONArray("medications") ?: JSONArray()
        for (i in 0 until medsArray.length()) {
            medications.add(medsArray.getString(i))
        }

        val conditions = mutableListOf<String>()
        val conditionsArray = json.optJSONArray("conditions") ?: JSONArray()
        for (i in 0 until conditionsArray.length()) {
            conditions.add(conditionsArray.getString(i))
        }

        return Patient(
            id = json.optString("patient_id", ""),
            name = json.optString("name", ""),
            dateOfBirth = json.optString("date_of_birth", ""),
            gender = json.optString("gender", ""),
            allergies = allergies,
            vitals = vitals,
            medications = medications,
            conditions = conditions
        )
    }

    fun isCriticalBP(bp: String): Boolean {
        val parts = bp.split("/")
        if (parts.size != 2) return false
        val systolic = parts[0].toIntOrNull() ?: return false
        val diastolic = parts[1].toIntOrNull() ?: return false
        return systolic >= 180 || systolic < 90 || diastolic >= 110 || diastolic < 60
    }

    fun isCriticalHR(hr: Int): Boolean {
        return hr < 40 || hr > 150
    }

    fun isCriticalSpO2(spo2: Int): Boolean {
        return spo2 < 88
    }

    fun isCriticalTemp(temp: Double): Boolean {
        return temp > 104.0 || temp < 95.5
    }

    fun formatDisplayText(patient: Patient): String {
        return buildString {
            appendLine("Patient: ${patient.name}")
            appendLine("DOB: ${patient.dateOfBirth}")
            appendLine("Gender: ${patient.gender}")
            if (patient.allergies.isNotEmpty()) {
                appendLine("Allergies: ${patient.allergies.size}")
            }
        }
    }

    fun formatAllergyWarnings(patient: Patient): String {
        return patient.allergies.filter { it.severity == "high" }
            .joinToString("\n") { "⚠️ ${it.substance}: ${it.reaction}" }
    }
}
