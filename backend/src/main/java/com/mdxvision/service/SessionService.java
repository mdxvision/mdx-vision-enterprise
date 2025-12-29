package com.mdxvision.service;

import com.mdxvision.dto.SessionDTO;
import com.mdxvision.entity.*;
import com.mdxvision.repository.*;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.UUID;

@Service
@RequiredArgsConstructor
@Slf4j
public class SessionService {

    private final SessionRepository sessionRepository;
    private final EncounterRepository encounterRepository;
    private final UserRepository userRepository;
    private final AuditService auditService;
    private final WebSocketService webSocketService;
    private final AiPipelineService aiPipelineService;

    @Transactional
    public SessionDTO.Response startSession(UUID userId, SessionDTO.CreateRequest request) {
        User user = userRepository.findById(userId)
            .orElseThrow(() -> new RuntimeException("User not found"));

        Encounter encounter = null;
        Patient patient = null;
        
        if (request.getEncounterId() != null) {
            encounter = encounterRepository.findById(request.getEncounterId())
                .orElseThrow(() -> new RuntimeException("Encounter not found"));
            patient = encounter.getPatient();
            
            // Update encounter status
            encounter.setStatus(Encounter.EncounterStatus.IN_PROGRESS);
            if (encounter.getStartTime() == null) {
                encounter.setStartTime(Instant.now());
            }
        }

        // Generate audio channel ID for real-time streaming
        String audioChannelId = UUID.randomUUID().toString();

        Session session = Session.builder()
            .user(user)
            .encounter(encounter)
            .status(Session.SessionStatus.ACTIVE)
            .deviceType(request.getDeviceType())
            .deviceId(request.getDeviceId())
            .startTime(Instant.now())
            .audioChannelId(audioChannelId)
            .transcriptionEnabled(request.isTranscriptionEnabled())
            .aiSuggestionsEnabled(request.isAiSuggestionsEnabled())
            .languageCode(request.getLanguageCode())
            .translationTargetLanguage(request.getTranslationTargetLanguage())
            .build();

        session = sessionRepository.save(session);

        // Start AI transcription pipeline
        if (request.isTranscriptionEnabled()) {
            aiPipelineService.initializeTranscription(session);
        }

        // Audit log
        auditService.log(AuditLog.AuditAction.START_SESSION, "Session", session.getId().toString(),
            patient != null ? patient.getId() : null, "Session started");

        log.info("Session started: {} for user: {}", session.getId(), userId);

        return mapToResponse(session, patient);
    }

    @Transactional
    public SessionDTO.Response endSession(UUID sessionId, UUID userId) {
        Session session = sessionRepository.findById(sessionId)
            .orElseThrow(() -> new RuntimeException("Session not found"));

        if (!session.getUser().getId().equals(userId)) {
            throw new RuntimeException("Unauthorized to end this session");
        }

        session.setStatus(Session.SessionStatus.COMPLETED);
        session.setEndTime(Instant.now());

        // End encounter if associated
        if (session.getEncounter() != null) {
            Encounter encounter = session.getEncounter();
            encounter.setStatus(Encounter.EncounterStatus.COMPLETED);
            encounter.setEndTime(Instant.now());
        }

        session = sessionRepository.save(session);

        // Stop AI transcription
        aiPipelineService.stopTranscription(session);

        // Notify via WebSocket
        webSocketService.notifySessionEnded(session);

        // Audit log
        auditService.log(AuditLog.AuditAction.END_SESSION, "Session", session.getId().toString(),
            session.getEncounter() != null ? session.getEncounter().getPatient().getId() : null, 
            "Session ended");

        log.info("Session ended: {}", sessionId);

        return mapToResponse(session, 
            session.getEncounter() != null ? session.getEncounter().getPatient() : null);
    }

    public SessionDTO.Response getSession(UUID sessionId) {
        Session session = sessionRepository.findById(sessionId)
            .orElseThrow(() -> new RuntimeException("Session not found"));
        return mapToResponse(session, 
            session.getEncounter() != null ? session.getEncounter().getPatient() : null);
    }

    private SessionDTO.Response mapToResponse(Session session, Patient patient) {
        return SessionDTO.Response.builder()
            .id(session.getId())
            .userId(session.getUser().getId())
            .encounterId(session.getEncounter() != null ? session.getEncounter().getId() : null)
            .status(session.getStatus())
            .deviceType(session.getDeviceType())
            .audioChannelId(session.getAudioChannelId())
            .startTime(session.getStartTime())
            .endTime(session.getEndTime())
            .transcriptionEnabled(session.isTranscriptionEnabled())
            .aiSuggestionsEnabled(session.isAiSuggestionsEnabled())
            .languageCode(session.getLanguageCode())
            .translationTargetLanguage(session.getTranslationTargetLanguage())
            .patient(patient != null ? mapPatient(patient) : null)
            .build();
    }

    private com.mdxvision.dto.PatientDTO.Response mapPatient(Patient patient) {
        return com.mdxvision.dto.PatientDTO.Response.builder()
            .id(patient.getId())
            .firstName(patient.getFirstName())
            .lastName(patient.getLastName())
            .fullName(patient.getFullName())
            .dateOfBirth(patient.getDateOfBirth())
            .gender(patient.getGender())
            .mrn(patient.getMrn())
            .build();
    }
}
