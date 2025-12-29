package com.mdxvision.entity;

import jakarta.persistence.*;
import lombok.*;

import java.time.Instant;

@Entity
@Table(name = "sessions")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Session extends BaseEntity {

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "user_id", nullable = false)
    private User user;

    @OneToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "encounter_id")
    private Encounter encounter;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private SessionStatus status;

    @Column(name = "device_type")
    private String deviceType; // VUZIX, IOS, ANDROID, WEB

    @Column(name = "device_id")
    private String deviceId;

    @Column(name = "start_time")
    private Instant startTime;

    @Column(name = "end_time")
    private Instant endTime;

    @Column(name = "audio_channel_id")
    private String audioChannelId; // For real-time audio streaming

    @Column(name = "transcription_enabled")
    private boolean transcriptionEnabled = true;

    @Column(name = "ai_suggestions_enabled")
    private boolean aiSuggestionsEnabled = true;

    @Column(name = "language_code")
    private String languageCode = "en-US";

    @Column(name = "translation_target_language")
    private String translationTargetLanguage;

    public enum SessionStatus {
        INITIALIZING,
        ACTIVE,
        PAUSED,
        COMPLETED,
        ERROR
    }
}
