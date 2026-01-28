package com.mdxvision.controller;

import com.mdxvision.dto.ClinicalNoteDTO;
import com.mdxvision.dto.EncounterDTO;
import com.mdxvision.dto.TranscriptionDTO;
import com.mdxvision.entity.*;
import com.mdxvision.repository.*;
import com.mdxvision.service.AiPipelineService;
import com.mdxvision.service.AuditService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.*;
import reactor.core.publisher.Mono;

import java.time.Instant;
import java.util.List;
import java.util.UUID;
import java.util.stream.Collectors;

@RestController
@RequestMapping("/v1/encounters")
@RequiredArgsConstructor
@Tag(name = "Encounters", description = "Patient encounter management")
public class EncounterController {

    private final EncounterRepository encounterRepository;
    private final PatientRepository patientRepository;
    private final UserRepository userRepository;
    private final ClinicalNoteRepository clinicalNoteRepository;
    private final TranscriptionRepository transcriptionRepository;
    private final AiPipelineService aiPipelineService;
    private final AuditService auditService;

    @PostMapping
    @Operation(summary = "Create a new encounter")
    public ResponseEntity<EncounterDTO.Response> createEncounter(
            @AuthenticationPrincipal Jwt jwt,
            @RequestBody EncounterDTO.CreateRequest request) {
        
        UUID userId = UUID.fromString(jwt.getSubject());
        
        Patient patient = patientRepository.findById(request.getPatientId())
            .orElseThrow(() -> new RuntimeException("Patient not found"));
        
        User provider = userRepository.findById(userId)
            .orElseThrow(() -> new RuntimeException("User not found"));

        Encounter encounter = Encounter.builder()
            .patient(patient)
            .provider(provider)
            .status(Encounter.EncounterStatus.PLANNED)
            .type(request.getType())
            .location(request.getLocation())
            .chiefComplaint(request.getChiefComplaint())
            .reasonForVisit(request.getReasonForVisit())
            .build();

        encounter = encounterRepository.save(encounter);

        auditService.log(AuditLog.AuditAction.CREATE, "Encounter", 
            encounter.getId().toString(), patient.getId(), "Encounter created");

        return ResponseEntity.ok(mapToResponse(encounter));
    }

    @GetMapping("/{encounterId}")
    @Operation(summary = "Get encounter details")
    public ResponseEntity<EncounterDTO.Response> getEncounter(
            @AuthenticationPrincipal Jwt jwt,
            @PathVariable UUID encounterId) {
        
        Encounter encounter = encounterRepository.findById(encounterId)
            .orElseThrow(() -> new RuntimeException("Encounter not found"));
        
        auditService.logPHIAccess(
            UUID.fromString(jwt.getSubject()),
            encounter.getPatient().getId(),
            "View encounter"
        );
        
        return ResponseEntity.ok(mapToResponse(encounter));
    }

    @PutMapping("/{encounterId}")
    @Operation(summary = "Update encounter")
    public ResponseEntity<EncounterDTO.Response> updateEncounter(
            @PathVariable UUID encounterId,
            @RequestBody EncounterDTO.UpdateRequest request) {
        
        Encounter encounter = encounterRepository.findById(encounterId)
            .orElseThrow(() -> new RuntimeException("Encounter not found"));
        
        if (request.getStatus() != null) {
            encounter.setStatus(request.getStatus());
            if (request.getStatus() == Encounter.EncounterStatus.COMPLETED) {
                encounter.setEndTime(Instant.now());
            }
        }
        if (request.getChiefComplaint() != null) {
            encounter.setChiefComplaint(request.getChiefComplaint());
        }
        if (request.getReasonForVisit() != null) {
            encounter.setReasonForVisit(request.getReasonForVisit());
        }
        
        encounter = encounterRepository.save(encounter);
        return ResponseEntity.ok(mapToResponse(encounter));
    }

    @GetMapping("/{encounterId}/transcriptions")
    @Operation(summary = "Get all transcriptions for an encounter")
    public ResponseEntity<List<TranscriptionDTO.Response>> getTranscriptions(
            @PathVariable UUID encounterId) {
        
        List<Transcription> transcriptions = 
            transcriptionRepository.findByEncounterIdOrderByStartTimestampAsc(encounterId);
        
        return ResponseEntity.ok(transcriptions.stream()
            .map(this::mapTranscriptionToResponse)
            .collect(Collectors.toList()));
    }

    @GetMapping("/{encounterId}/notes")
    @Operation(summary = "Get clinical notes for an encounter")
    public ResponseEntity<List<ClinicalNoteDTO.Response>> getClinicalNotes(
            @PathVariable UUID encounterId) {
        
        List<ClinicalNote> notes = clinicalNoteRepository.findByEncounterId(encounterId);
        
        return ResponseEntity.ok(notes.stream()
            .map(this::mapNoteToResponse)
            .collect(Collectors.toList()));
    }

    @PostMapping("/{encounterId}/notes/generate")
    @Operation(summary = "Generate AI clinical note from transcriptions")
    public Mono<ResponseEntity<ClinicalNoteDTO.Response>> generateNote(
            @AuthenticationPrincipal Jwt jwt,
            @PathVariable UUID encounterId,
            @RequestParam(defaultValue = "SOAP") String noteType) {

        UUID userId = UUID.fromString(jwt.getSubject());

        // Fetch encounter and user synchronously (JPA repositories)
        Encounter encounter = encounterRepository.findById(encounterId)
            .orElseThrow(() -> new RuntimeException("Encounter not found"));

        User author = userRepository.findById(userId)
            .orElseThrow(() -> new RuntimeException("User not found"));

        // Call AI service reactively - no blocking!
        return aiPipelineService.generateClinicalNote(encounterId.toString(), noteType)
            .map(aiResponse -> {
                ClinicalNote note = ClinicalNote.builder()
                    .encounter(encounter)
                    .author(author)
                    .noteType(ClinicalNote.NoteType.valueOf(noteType))
                    .status(ClinicalNote.NoteStatus.AI_GENERATED)
                    .subjective((String) aiResponse.get("subjective"))
                    .objective((String) aiResponse.get("objective"))
                    .assessment((String) aiResponse.get("assessment"))
                    .plan((String) aiResponse.get("plan"))
                    .aiSummary((String) aiResponse.get("summary"))
                    .icd10Codes(aiResponse.get("icd10Codes") != null ?
                        aiResponse.get("icd10Codes").toString() : null)
                    .build();

                note = clinicalNoteRepository.save(note);

                auditService.log(AuditLog.AuditAction.GENERATE_NOTE, "ClinicalNote",
                    note.getId().toString(), encounter.getPatient().getId(),
                    "AI note generated");

                return ResponseEntity.ok(mapNoteToResponse(note));
            })
            .defaultIfEmpty(ResponseEntity.notFound().build())
            .onErrorResume(e -> Mono.just(ResponseEntity.internalServerError().build()));
    }

    private EncounterDTO.Response mapToResponse(Encounter encounter) {
        return EncounterDTO.Response.builder()
            .id(encounter.getId())
            .fhirId(encounter.getFhirId())
            .status(encounter.getStatus())
            .type(encounter.getType())
            .startTime(encounter.getStartTime())
            .endTime(encounter.getEndTime())
            .location(encounter.getLocation())
            .chiefComplaint(encounter.getChiefComplaint())
            .reasonForVisit(encounter.getReasonForVisit())
            .hasActiveSession(encounter.getActiveSession() != null)
            .build();
    }

    private TranscriptionDTO.Response mapTranscriptionToResponse(Transcription t) {
        return TranscriptionDTO.Response.builder()
            .id(t.getId())
            .speakerLabel(t.getSpeakerLabel())
            .originalText(t.getOriginalText())
            .translatedText(t.getTranslatedText())
            .sourceLanguage(t.getSourceLanguage())
            .targetLanguage(t.getTargetLanguage())
            .confidenceScore(t.getConfidenceScore())
            .startTimestamp(t.getStartTimestamp())
            .endTimestamp(t.getEndTimestamp())
            .audioOffsetMs(t.getAudioOffsetMs())
            .durationMs(t.getDurationMs())
            .build();
    }

    private ClinicalNoteDTO.Response mapNoteToResponse(ClinicalNote note) {
        return ClinicalNoteDTO.Response.builder()
            .id(note.getId())
            .encounterId(note.getEncounter().getId())
            .noteType(note.getNoteType())
            .status(note.getStatus())
            .subjective(note.getSubjective())
            .objective(note.getObjective())
            .assessment(note.getAssessment())
            .plan(note.getPlan())
            .fullContent(note.getFullContent())
            .aiSummary(note.getAiSummary())
            .signedAt(note.getSignedAt())
            .pushedToEhrAt(note.getPushedToEhrAt())
            .build();
    }
}
