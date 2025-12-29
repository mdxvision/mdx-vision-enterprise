package com.mdxvision.entity;

import jakarta.persistence.*;
import lombok.*;

import java.time.Instant;

@Entity
@Table(name = "transcriptions")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Transcription extends BaseEntity {

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "encounter_id", nullable = false)
    private Encounter encounter;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "session_id")
    private Session session;

    @Column(name = "speaker_label")
    private String speakerLabel; // PROVIDER, PATIENT, UNKNOWN

    @Column(name = "original_text", columnDefinition = "TEXT", nullable = false)
    private String originalText;

    @Column(name = "translated_text", columnDefinition = "TEXT")
    private String translatedText;

    @Column(name = "source_language")
    private String sourceLanguage;

    @Column(name = "target_language")
    private String targetLanguage;

    @Column(name = "confidence_score")
    private Double confidenceScore;

    @Column(name = "start_timestamp")
    private Instant startTimestamp;

    @Column(name = "end_timestamp")
    private Instant endTimestamp;

    @Column(name = "audio_offset_ms")
    private Long audioOffsetMs;

    @Column(name = "duration_ms")
    private Long durationMs;

    @Enumerated(EnumType.STRING)
    @Column(name = "processing_status")
    private ProcessingStatus processingStatus;

    public enum ProcessingStatus {
        PENDING,
        PROCESSING,
        COMPLETED,
        FAILED
    }
}
