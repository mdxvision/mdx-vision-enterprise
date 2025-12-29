package com.mdxvision.fhir;

import java.util.List;
import java.util.stream.Collectors;

import org.hl7.fhir.r4.model.Patient;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import com.mdxvision.fhir.EpicFhirService.PatientSummary;

/**
 * Epic FHIR REST Controller
 *
 * Endpoints for AR glasses to access Epic EHR data:
 * - Patient lookup (by ID, MRN, or name)
 * - Vital signs
 * - Clinical notes
 *
 * All responses optimized for AR glasses display
 */
@RestController
@RequestMapping("/api/v1/epic")
@CrossOrigin(origins = "*")
public class EpicFhirController {

    private final EpicFhirService epicFhirService;

    public EpicFhirController(EpicFhirService epicFhirService) {
        this.epicFhirService = epicFhirService;
    }

    /**
     * Get patient by FHIR ID
     * Used after QR/barcode scan or face recognition
     */
    @GetMapping("/patient/{patientId}")
    public ResponseEntity<PatientSummary> getPatient(@PathVariable String patientId) {
        PatientSummary summary = epicFhirService.getPatientSummaryForDisplay(patientId);
        if (summary == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(summary);
    }

    /**
     * Get patient by MRN (Medical Record Number)
     * Typically scanned from wristband
     */
    @GetMapping("/patient/mrn/{mrn}")
    public ResponseEntity<PatientSummary> getPatientByMrn(@PathVariable String mrn) {
        return epicFhirService.getPatientByMrn(mrn)
                .map(patient -> {
                    PatientSummary summary = epicFhirService.getPatientSummaryForDisplay(
                            patient.getIdElement().getIdPart()
                    );
                    return ResponseEntity.ok(summary);
                })
                .orElse(ResponseEntity.notFound().build());
    }

    /**
     * Search patients by name
     * Used for voice search: "Find patient John Smith"
     */
    @GetMapping("/patient/search")
    public ResponseEntity<List<PatientSearchResult>> searchPatients(@RequestParam String name) {
        List<Patient> patients = epicFhirService.searchPatientsByName(name);

        List<PatientSearchResult> results = patients.stream()
                .map(p -> new PatientSearchResult(
                        p.getIdElement().getIdPart(),
                        p.hasName() ? p.getNameFirstRep().getNameAsSingleString() : "Unknown",
                        p.hasBirthDate() ? p.getBirthDate().toString() : null
                ))
                .collect(Collectors.toList());

        return ResponseEntity.ok(results);
    }

    /**
     * Get patient vitals formatted for AR display
     */
    @GetMapping("/patient/{patientId}/vitals")
    public ResponseEntity<VitalsDisplay> getPatientVitals(@PathVariable String patientId) {
        PatientSummary summary = epicFhirService.getPatientSummaryForDisplay(patientId);
        if (summary == null) {
            return ResponseEntity.notFound().build();
        }

        VitalsDisplay vitals = new VitalsDisplay();
        vitals.setPatientId(patientId);
        vitals.setHeartRate(summary.getHeartRate());
        vitals.setBloodPressure(summary.getSystolicBp() + "/" + summary.getDiastolicBp());
        vitals.setTemperature(summary.getTemperature());
        vitals.setSpO2(summary.getSpO2());

        return ResponseEntity.ok(vitals);
    }

    /**
     * Create clinical note from voice transcription
     */
    @PostMapping("/patient/{patientId}/note")
    public ResponseEntity<NoteResponse> createNote(
            @PathVariable String patientId,
            @RequestBody CreateNoteRequest request) {
        try {
            epicFhirService.createClinicalNote(
                    patientId,
                    request.getEncounterId(),
                    request.getNoteText()
            );
            return ResponseEntity.ok(new NoteResponse("Note saved successfully"));
        } catch (Exception e) {
            return ResponseEntity.internalServerError()
                    .body(new NoteResponse("Failed to save note: " + e.getMessage()));
        }
    }

    // DTOs for API responses

    public static class PatientSearchResult {
        private String patientId;
        private String name;
        private String dateOfBirth;

        public PatientSearchResult(String patientId, String name, String dateOfBirth) {
            this.patientId = patientId;
            this.name = name;
            this.dateOfBirth = dateOfBirth;
        }

        public String getPatientId() { return patientId; }
        public String getName() { return name; }
        public String getDateOfBirth() { return dateOfBirth; }
    }

    public static class VitalsDisplay {
        private String patientId;
        private String heartRate;
        private String bloodPressure;
        private String temperature;
        private String spO2;

        public String getPatientId() { return patientId; }
        public void setPatientId(String patientId) { this.patientId = patientId; }
        public String getHeartRate() { return heartRate; }
        public void setHeartRate(String heartRate) { this.heartRate = heartRate; }
        public String getBloodPressure() { return bloodPressure; }
        public void setBloodPressure(String bloodPressure) { this.bloodPressure = bloodPressure; }
        public String getTemperature() { return temperature; }
        public void setTemperature(String temperature) { this.temperature = temperature; }
        public String getSpO2() { return spO2; }
        public void setSpO2(String spO2) { this.spO2 = spO2; }
    }

    public static class CreateNoteRequest {
        private String encounterId;
        private String noteText;

        public String getEncounterId() { return encounterId; }
        public void setEncounterId(String encounterId) { this.encounterId = encounterId; }
        public String getNoteText() { return noteText; }
        public void setNoteText(String noteText) { this.noteText = noteText; }
    }

    public static class NoteResponse {
        private String message;

        public NoteResponse(String message) {
            this.message = message;
        }

        public String getMessage() { return message; }
    }
}
