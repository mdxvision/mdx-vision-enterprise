package com.mdxvision.dto;

import com.mdxvision.entity.Session;
import lombok.*;

import java.time.Instant;
import java.util.UUID;

public class SessionDTO {

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class CreateRequest {
        private UUID encounterId;
        private String deviceType;
        private String deviceId;
        private boolean transcriptionEnabled = true;
        private boolean aiSuggestionsEnabled = true;
        private String languageCode = "en-US";
        private String translationTargetLanguage;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class Response {
        private UUID id;
        private UUID userId;
        private UUID encounterId;
        private Session.SessionStatus status;
        private String deviceType;
        private String audioChannelId;
        private Instant startTime;
        private Instant endTime;
        private boolean transcriptionEnabled;
        private boolean aiSuggestionsEnabled;
        private String languageCode;
        private String translationTargetLanguage;
        private PatientDTO.Response patient;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class StatusUpdate {
        private Session.SessionStatus status;
    }
}
