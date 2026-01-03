package com.mdxvision

import android.content.Context
import android.graphics.Color
import android.graphics.drawable.GradientDrawable
import android.util.TypedValue
import android.view.Gravity
import android.view.View
import android.widget.FrameLayout
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import org.json.JSONArray
import org.json.JSONObject

/**
 * VuzixHudView - Custom View for HUD overlay content
 *
 * Displays patient information in a compact or expanded layout optimized
 * for Vuzix Blade 2 AR glasses (1280x720 display).
 *
 * Design principles:
 * - High contrast text (18sp minimum)
 * - Dark background for AR visibility
 * - Critical info (allergies) in red
 * - Programmatic layout (consistent with MainActivity pattern)
 */
class VuzixHudView(context: Context, private var isExpanded: Boolean = false) : FrameLayout(context) {

    companion object {
        // Colors matching MainActivity theme
        private const val BACKGROUND_COLOR = 0xEE0A1628.toInt()  // Semi-transparent dark
        private const val BORDER_COLOR = 0xFF3B82F6.toInt()      // Blue border
        private const val TEXT_PRIMARY = 0xFFF8FAFC.toInt()      // White
        private const val TEXT_SECONDARY = 0xFF94A3B8.toInt()    // Gray
        private const val TEXT_CRITICAL = 0xFFEF4444.toInt()     // Red for allergies
        private const val TEXT_SUCCESS = 0xFF10B981.toInt()      // Green
        private const val TEXT_WARNING = 0xFFF59E0B.toInt()      // Yellow/amber
    }

    // UI Components
    private lateinit var contentLayout: LinearLayout
    private lateinit var patientNameText: TextView
    private lateinit var patientIdText: TextView
    private lateinit var allergiesText: TextView
    private lateinit var medsVitalsText: TextView
    private lateinit var roomText: TextView

    // Expanded view components
    private var allergiesDetailText: TextView? = null
    private var medsDetailText: TextView? = null
    private var vitalsDetailText: TextView? = null

    init {
        setupView()
    }

    private fun setupView() {
        // Create rounded rectangle background
        val background = GradientDrawable().apply {
            setColor(BACKGROUND_COLOR)
            cornerRadius = dpToPx(12f)
            setStroke(dpToPx(2f).toInt(), BORDER_COLOR)
        }
        setBackground(background)

        // Create content layout
        contentLayout = LinearLayout(context).apply {
            orientation = LinearLayout.VERTICAL
            layoutParams = LayoutParams(
                LayoutParams.MATCH_PARENT,
                LayoutParams.MATCH_PARENT
            )
            setPadding(dpToPx(12f).toInt(), dpToPx(10f).toInt(), dpToPx(12f).toInt(), dpToPx(10f).toInt())
        }

        if (isExpanded) {
            buildExpandedLayout()
        } else {
            buildCompactLayout()
        }

        addView(contentLayout)
    }

    private fun buildCompactLayout() {
        contentLayout.removeAllViews()

        // Row 1: Patient name + ID
        val headerRow = LinearLayout(context).apply {
            orientation = LinearLayout.HORIZONTAL
            layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            )
        }

        patientNameText = createTextView(
            text = "No Patient Loaded",
            sizeSp = 18f,
            color = TEXT_PRIMARY,
            bold = true
        ).apply {
            layoutParams = LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f)
        }
        headerRow.addView(patientNameText)

        patientIdText = createTextView(
            text = "",
            sizeSp = 14f,
            color = TEXT_SECONDARY
        )
        headerRow.addView(patientIdText)

        contentLayout.addView(headerRow)

        // Row 2: Allergies (critical - red)
        allergiesText = createTextView(
            text = "",
            sizeSp = 16f,
            color = TEXT_CRITICAL
        ).apply {
            layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            ).apply {
                topMargin = dpToPx(6f).toInt()
            }
        }
        contentLayout.addView(allergiesText)

        // Row 3: Meds count + Vitals status
        medsVitalsText = createTextView(
            text = "",
            sizeSp = 14f,
            color = TEXT_SECONDARY
        ).apply {
            layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            ).apply {
                topMargin = dpToPx(4f).toInt()
            }
        }
        contentLayout.addView(medsVitalsText)

        // Row 4: Room/Location
        roomText = createTextView(
            text = "",
            sizeSp = 14f,
            color = TEXT_SECONDARY
        ).apply {
            layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            ).apply {
                topMargin = dpToPx(4f).toInt()
            }
        }
        contentLayout.addView(roomText)
    }

    private fun buildExpandedLayout() {
        contentLayout.removeAllViews()

        // Header: Patient name + demographics
        val headerLayout = LinearLayout(context).apply {
            orientation = LinearLayout.VERTICAL
            layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            )
        }

        patientNameText = createTextView(
            text = "No Patient Loaded",
            sizeSp = 22f,
            color = TEXT_PRIMARY,
            bold = true
        )
        headerLayout.addView(patientNameText)

        patientIdText = createTextView(
            text = "",
            sizeSp = 14f,
            color = TEXT_SECONDARY
        ).apply {
            layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            ).apply {
                topMargin = dpToPx(2f).toInt()
            }
        }
        headerLayout.addView(patientIdText)

        contentLayout.addView(headerLayout)

        // Divider
        contentLayout.addView(createDivider())

        // Scrollable content area
        val scrollView = ScrollView(context).apply {
            layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                0,
                1f
            )
        }

        val scrollContent = LinearLayout(context).apply {
            orientation = LinearLayout.VERTICAL
            layoutParams = LayoutParams(
                LayoutParams.MATCH_PARENT,
                LayoutParams.WRAP_CONTENT
            )
        }

        // Allergies Section
        scrollContent.addView(createSectionHeader("ALLERGIES", TEXT_CRITICAL))
        allergiesDetailText = createTextView(
            text = "None documented",
            sizeSp = 16f,
            color = TEXT_CRITICAL
        ).apply {
            layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            ).apply {
                bottomMargin = dpToPx(12f).toInt()
            }
        }
        scrollContent.addView(allergiesDetailText)

        // Medications Section
        scrollContent.addView(createSectionHeader("ACTIVE MEDICATIONS", TEXT_PRIMARY))
        medsDetailText = createTextView(
            text = "None",
            sizeSp = 15f,
            color = TEXT_PRIMARY
        ).apply {
            layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            ).apply {
                bottomMargin = dpToPx(12f).toInt()
            }
        }
        scrollContent.addView(medsDetailText)

        // Vitals Section
        scrollContent.addView(createSectionHeader("VITALS", TEXT_PRIMARY))
        vitalsDetailText = createTextView(
            text = "No vitals recorded",
            sizeSp = 15f,
            color = TEXT_PRIMARY
        ).apply {
            layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            )
        }
        scrollContent.addView(vitalsDetailText)

        scrollView.addView(scrollContent)
        contentLayout.addView(scrollView)

        // Footer: Room + minimize hint
        roomText = createTextView(
            text = "Say \"minimize HUD\" to compact",
            sizeSp = 12f,
            color = TEXT_SECONDARY
        ).apply {
            layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            ).apply {
                topMargin = dpToPx(8f).toInt()
            }
            gravity = Gravity.CENTER
        }
        contentLayout.addView(roomText)

        // Also need simple reference for compact mode
        allergiesText = allergiesDetailText!!
        medsVitalsText = medsDetailText!!
    }

    private fun createSectionHeader(title: String, color: Int): TextView {
        return createTextView(
            text = title,
            sizeSp = 12f,
            color = color,
            bold = true
        ).apply {
            layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            ).apply {
                bottomMargin = dpToPx(4f).toInt()
            }
        }
    }

    private fun createDivider(): View {
        return View(context).apply {
            layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                dpToPx(1f).toInt()
            ).apply {
                topMargin = dpToPx(8f).toInt()
                bottomMargin = dpToPx(8f).toInt()
            }
            setBackgroundColor(0xFF3B82F6.toInt())
        }
    }

    private fun createTextView(
        text: String,
        sizeSp: Float,
        color: Int,
        bold: Boolean = false
    ): TextView {
        return TextView(context).apply {
            this.text = text
            setTextSize(TypedValue.COMPLEX_UNIT_SP, sizeSp)
            setTextColor(color)
            if (bold) {
                setTypeface(typeface, android.graphics.Typeface.BOLD)
            }
        }
    }

    fun setExpanded(expanded: Boolean) {
        if (this.isExpanded != expanded) {
            this.isExpanded = expanded
            setupView()
        }
    }

    fun updatePatientData(patient: JSONObject) {
        // Extract patient info
        val name = patient.optString("name", patient.optString("patient_name", "Unknown"))
        val id = patient.optString("id", patient.optString("patient_id", ""))
        val dob = patient.optString("birthDate", patient.optString("dob", ""))
        val gender = patient.optString("gender", "")

        // Update name
        patientNameText.text = name.uppercase()

        // Update ID line
        val idParts = mutableListOf<String>()
        if (id.isNotEmpty()) idParts.add("ID: $id")
        if (dob.isNotEmpty()) idParts.add("DOB: $dob")
        if (gender.isNotEmpty()) idParts.add(gender.uppercase().take(1))
        patientIdText.text = idParts.joinToString(" | ")

        // Extract allergies
        val allergies = patient.optJSONArray("allergies") ?: JSONArray()
        updateAllergiesDisplay(allergies)

        // Extract medications
        val medications = patient.optJSONArray("medications") ?: JSONArray()
        updateMedicationsDisplay(medications)

        // Extract vitals
        val vitals = patient.optJSONArray("vitals") ?: JSONArray()
        updateVitalsDisplay(vitals)

        // Room (if available)
        val room = patient.optString("room", "")
        if (room.isNotEmpty()) {
            roomText.text = "Room: $room"
        } else if (!isExpanded) {
            roomText.visibility = View.GONE
        }
    }

    private fun updateAllergiesDisplay(allergies: JSONArray) {
        if (allergies.length() == 0) {
            if (isExpanded) {
                allergiesDetailText?.text = "No known allergies (NKDA)"
                allergiesDetailText?.setTextColor(TEXT_SUCCESS)
            } else {
                allergiesText.text = "NKDA"
                allergiesText.setTextColor(TEXT_SUCCESS)
            }
            return
        }

        val allergyList = mutableListOf<String>()
        for (i in 0 until allergies.length()) {
            val allergy = allergies.optJSONObject(i)
            if (allergy != null) {
                val name = allergy.optString("substance", allergy.optString("name", "Unknown"))
                val severity = allergy.optString("severity", "")
                val reaction = allergy.optString("reaction", "")

                if (isExpanded) {
                    val detail = buildString {
                        append("- $name")
                        if (severity.isNotEmpty()) append(" ($severity)")
                        if (reaction.isNotEmpty()) append(" - $reaction")
                    }
                    allergyList.add(detail)
                } else {
                    allergyList.add(name)
                }
            } else {
                // Simple string allergy
                allergyList.add(allergies.optString(i, "Unknown"))
            }
        }

        if (isExpanded) {
            allergiesDetailText?.text = allergyList.joinToString("\n")
            allergiesDetailText?.setTextColor(TEXT_CRITICAL)
        } else {
            // Compact: show first 2 with warning icon
            val display = allergyList.take(2).joinToString(", ")
            val suffix = if (allergyList.size > 2) " +${allergyList.size - 2} more" else ""
            allergiesText.text = "ALLERGIES: $display$suffix"
            allergiesText.setTextColor(TEXT_CRITICAL)
        }
    }

    private fun updateMedicationsDisplay(medications: JSONArray) {
        val medCount = medications.length()

        if (isExpanded) {
            if (medCount == 0) {
                medsDetailText?.text = "No active medications"
            } else {
                val medList = mutableListOf<String>()
                for (i in 0 until minOf(medCount, 6)) {  // Show up to 6 in expanded
                    val med = medications.optJSONObject(i)
                    if (med != null) {
                        val name = med.optString("name", med.optString("medication", "Unknown"))
                        val dosage = med.optString("dosage", "")
                        medList.add(if (dosage.isNotEmpty()) "$name $dosage" else name)
                    }
                }
                val suffix = if (medCount > 6) "\n... +${medCount - 6} more" else ""
                medsDetailText?.text = medList.joinToString(" | ") + suffix
            }
        } else {
            // Compact: just show count
            val vitalsStatus = "OK"  // TODO: Calculate from vitals
            medsVitalsText.text = "Meds: $medCount | Vitals: $vitalsStatus"
        }
    }

    private fun updateVitalsDisplay(vitals: JSONArray) {
        if (!isExpanded) return  // Only shown in expanded view

        if (vitals.length() == 0) {
            vitalsDetailText?.text = "No vitals recorded"
            return
        }

        val vitalsList = mutableListOf<String>()
        for (i in 0 until vitals.length()) {
            val vital = vitals.optJSONObject(i)
            if (vital != null) {
                val type = vital.optString("type", vital.optString("code", ""))
                val value = vital.optString("value", "")
                val unit = vital.optString("unit", "")

                when (type.lowercase()) {
                    "blood_pressure", "bp", "blood pressure" -> {
                        vitalsList.add("BP: $value")
                    }
                    "heart_rate", "hr", "pulse" -> {
                        vitalsList.add("HR: $value")
                    }
                    "oxygen_saturation", "spo2", "o2sat" -> {
                        vitalsList.add("SpO2: $value%")
                    }
                    "temperature", "temp" -> {
                        vitalsList.add("Temp: $value$unit")
                    }
                    "respiratory_rate", "rr" -> {
                        vitalsList.add("RR: $value")
                    }
                    else -> {
                        if (value.isNotEmpty()) {
                            vitalsList.add("$type: $value$unit")
                        }
                    }
                }
            }
        }

        vitalsDetailText?.text = if (vitalsList.isNotEmpty()) {
            vitalsList.joinToString(" | ")
        } else {
            "No vitals recorded"
        }
    }

    private fun dpToPx(dp: Float): Float {
        return TypedValue.applyDimension(
            TypedValue.COMPLEX_UNIT_DIP,
            dp,
            context.resources.displayMetrics
        )
    }
}
