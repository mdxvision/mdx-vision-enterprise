package com.mdxvision.controller;

import com.mdxvision.dto.EncounterDTO;
import com.mdxvision.dto.PatientDTO;
import com.mdxvision.entity.Encounter;
import com.mdxvision.entity.Patient;
import com.mdxvision.repository.EncounterRepository;
import com.mdxvision.repository.PatientRepository;
import com.mdxvision.service.AuditService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.*;

import java.util.UUID;

@RestController
@RequestMapping("/v1/patients")
@RequiredArgsConstructor
@Tag(name = "Patients", description = "Patient management")
public class PatientController {

    private final PatientRepository patientRepository;
    private final EncounterRepository encounterRepository;
    private final AuditService auditService;

    @GetMapping
    @Operation(summary = "Search patients")
    public ResponseEntity<Page<PatientDTO.Response>> searchPatients(
            @RequestParam(required = false) String search,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        
        Page<Patient> patients;
        if (search != null && !search.isEmpty()) {
            patients = patientRepository.searchPatients(search, PageRequest.of(page, size));
        } else {
            patients = patientRepository.findAll(PageRequest.of(page, size));
        }
        
        return ResponseEntity.ok(patients.map(this::mapToResponse));
    }

    @GetMapping("/{patientId}")
    @Operation(summary = "Get patient by ID")
    public ResponseEntity<PatientDTO.Response> getPatient(
            @AuthenticationPrincipal Jwt jwt,
            @PathVariable UUID patientId) {
        
        Patient patient = patientRepository.findById(patientId)
            .orElseThrow(() -> new RuntimeException("Patient not found"));
        
        // Audit PHI access
        auditService.logPHIAccess(
            UUID.fromString(jwt.getSubject()), 
            patientId, 
            "View patient details"
        );
        
        return ResponseEntity.ok(mapToResponse(patient));
    }

    @GetMapping("/{patientId}/encounters")
    @Operation(summary = "Get patient encounters")
    public ResponseEntity<Page<EncounterDTO.Response>> getPatientEncounters(
            @PathVariable UUID patientId,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        
        Page<Encounter> encounters = encounterRepository.findByPatientId(
            patientId, PageRequest.of(page, size));
        
        return ResponseEntity.ok(encounters.map(this::mapEncounterToResponse));
    }

    @GetMapping("/mrn/{mrn}")
    @Operation(summary = "Get patient by MRN")
    public ResponseEntity<PatientDTO.Response> getPatientByMrn(
            @AuthenticationPrincipal Jwt jwt,
            @PathVariable String mrn) {
        
        Patient patient = patientRepository.findByMrn(mrn)
            .orElseThrow(() -> new RuntimeException("Patient not found"));
        
        auditService.logPHIAccess(
            UUID.fromString(jwt.getSubject()), 
            patient.getId(), 
            "View patient by MRN"
        );
        
        return ResponseEntity.ok(mapToResponse(patient));
    }

    private PatientDTO.Response mapToResponse(Patient patient) {
        return PatientDTO.Response.builder()
            .id(patient.getId())
            .fhirId(patient.getFhirId())
            .epicPatientId(patient.getEpicPatientId())
            .mrn(patient.getMrn())
            .firstName(patient.getFirstName())
            .lastName(patient.getLastName())
            .fullName(patient.getFullName())
            .dateOfBirth(patient.getDateOfBirth())
            .gender(patient.getGender())
            .phone(patient.getPhone())
            .email(patient.getEmail())
            .preferredLanguage(patient.getPreferredLanguage())
            .address(PatientDTO.AddressDTO.builder()
                .line1(patient.getAddressLine1())
                .line2(patient.getAddressLine2())
                .city(patient.getCity())
                .state(patient.getState())
                .postalCode(patient.getPostalCode())
                .country(patient.getCountry())
                .build())
            .build();
    }

    private EncounterDTO.Response mapEncounterToResponse(Encounter encounter) {
        return EncounterDTO.Response.builder()
            .id(encounter.getId())
            .fhirId(encounter.getFhirId())
            .status(encounter.getStatus())
            .type(encounter.getType())
            .startTime(encounter.getStartTime())
            .endTime(encounter.getEndTime())
            .location(encounter.getLocation())
            .chiefComplaint(encounter.getChiefComplaint())
            .build();
    }
}
