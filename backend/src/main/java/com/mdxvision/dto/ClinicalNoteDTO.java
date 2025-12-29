package com.mdxvision.dto;

import com.mdxvision.entity.ClinicalNote;
import lombok.*;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

public class ClinicalNoteDTO {

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class Response {
        private UUID id;
        private UUID encounterId;
        private UserDTO.Response author;
        private ClinicalNote.NoteType noteType;
        private ClinicalNote.NoteStatus status;
        private String subjective;
        private String objective;
        private String assessment;
        private String plan;
        private String fullContent;
        private String aiSummary;
        private List<String> icd10Codes;
        private List<String> cptCodes;
        private Instant signedAt;
        private Instant pushedToEhrAt;
        private List<DrugInteractionAlertDTO> drugInteractionAlerts;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class CreateRequest {
        private UUID encounterId;
        private ClinicalNote.NoteType noteType;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class UpdateRequest {
        private String subjective;
        private String objective;
        private String assessment;
        private String plan;
        private String fullContent;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class SignRequest {
        private String signature; // Digital signature/attestation
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class DrugInteractionAlertDTO {
        private UUID id;
        private String drug1Name;
        private String drug2Name;
        private String severity;
        private String description;
        private String recommendation;
        private boolean acknowledged;
    }
}
