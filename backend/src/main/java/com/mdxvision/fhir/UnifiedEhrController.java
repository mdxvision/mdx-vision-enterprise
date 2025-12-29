package com.mdxvision.fhir;

import java.util.List;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import com.mdxvision.fhir.UnifiedEhrService.*;

/**
 * Unified EHR REST Controller
 *
 * Single API for AR glasses to access ANY EHR system:
 * - Epic
 * - Cerner (Oracle Health)
 * - Veradigm (Allscripts)
 * - And more...
 *
 * MDx Vision Patent Implementation:
 * "Works with ALL EHR systems"
 */
@RestController
@RequestMapping("/api/v1/ehr")
@CrossOrigin(origins = "*")
public class UnifiedEhrController {

    private final UnifiedEhrService ehrService;

    public UnifiedEhrController(UnifiedEhrService ehrService) {
        this.ehrService = ehrService;
    }

    /**
     * Get patient summary (uses default EHR)
     * Optimized for AR glasses display
     */
    @GetMapping("/patient/{patientId}")
    public ResponseEntity<PatientSummary> getPatient(@PathVariable String patientId) {
        return ehrService.getPatientSummary(patientId)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    /**
     * Get patient from specific EHR system
     */
    @GetMapping("/patient/{patientId}/system/{system}")
    public ResponseEntity<PatientSummary> getPatientFromSystem(
            @PathVariable String patientId,
            @PathVariable String system) {
        try {
            UnifiedEhrService.EhrSystem ehrSystem = UnifiedEhrService.EhrSystem.valueOf(system.toUpperCase());
            return ehrService.getPatientSummary(patientId, ehrSystem)
                    .map(ResponseEntity::ok)
                    .orElse(ResponseEntity.notFound().build());
        } catch (IllegalArgumentException e) {
            return ResponseEntity.badRequest().build();
        }
    }

    /**
     * Get patient by MRN (wristband barcode scan)
     */
    @GetMapping("/patient/mrn/{mrn}")
    public ResponseEntity<PatientSummary> getPatientByMrn(@PathVariable String mrn) {
        return ehrService.getPatientByMrn(mrn)
                .flatMap(p -> ehrService.getPatientSummary(p.getPatientId()))
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    /**
     * Search patients by name (voice command: "Find patient John Smith")
     */
    @GetMapping("/patient/search")
    public ResponseEntity<List<PatientData>> searchPatients(@RequestParam String name) {
        List<PatientData> results = ehrService.searchPatients(name);
        return ResponseEntity.ok(results);
    }

    /**
     * Get patient vitals only (for quick display)
     */
    @GetMapping("/patient/{patientId}/vitals")
    public ResponseEntity<List<VitalSign>> getVitals(@PathVariable String patientId) {
        List<VitalSign> vitals = ehrService.getVitals(patientId, UnifiedEhrService.EhrSystem.EPIC);
        return ResponseEntity.ok(vitals);
    }

    /**
     * Get AR-optimized display string
     */
    @GetMapping("/patient/{patientId}/display")
    public ResponseEntity<ArDisplayResponse> getArDisplay(@PathVariable String patientId) {
        return ehrService.getPatientSummary(patientId)
                .map(summary -> ResponseEntity.ok(new ArDisplayResponse(
                        summary.getPatientId(),
                        summary.toArDisplay()
                )))
                .orElse(ResponseEntity.notFound().build());
    }

    /**
     * List supported EHR systems
     */
    @GetMapping("/systems")
    public ResponseEntity<EhrSystemsResponse> getSupportedSystems() {
        return ResponseEntity.ok(new EhrSystemsResponse(
                List.of(
                        new EhrSystemInfo("EPIC", "Epic", "https://fhir.epic.com"),
                        new EhrSystemInfo("CERNER", "Cerner (Oracle Health)", "https://fhir-open.cerner.com"),
                        new EhrSystemInfo("VERADIGM", "Veradigm (Allscripts)", "https://fhir.fhirpoint.open.allscripts.com"),
                        new EhrSystemInfo("MEDITECH", "MEDITECH", "Coming Soon"),
                        new EhrSystemInfo("ATHENA", "athenahealth", "Coming Soon"),
                        new EhrSystemInfo("NEXTGEN", "NextGen", "Coming Soon")
                )
        ));
    }

    // Response DTOs

    public record ArDisplayResponse(String patientId, String displayText) {}

    public record EhrSystemsResponse(List<EhrSystemInfo> systems) {}

    public record EhrSystemInfo(String code, String name, String endpoint) {}
}
