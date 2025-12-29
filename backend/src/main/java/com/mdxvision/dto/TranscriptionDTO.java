package com.mdxvision.dto;

import lombok.*;

import java.time.Instant;
import java.util.UUID;

public class TranscriptionDTO {

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class Response {
        private UUID id;
        private String speakerLabel;
        private String originalText;
        private String translatedText;
        private String sourceLanguage;
        private String targetLanguage;
        private Double confidenceScore;
        private Instant startTimestamp;
        private Instant endTimestamp;
        private Long audioOffsetMs;
        private Long durationMs;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class RealTimeUpdate {
        private UUID sessionId;
        private UUID encounterId;
        private String text;
        private String speakerLabel;
        private boolean isFinal;
        private Double confidence;
        private Long offsetMs;
    }
}
