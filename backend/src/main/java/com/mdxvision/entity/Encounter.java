package com.mdxvision.entity;

import jakarta.persistence.*;
import lombok.*;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;

@Entity
@Table(name = "encounters")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Encounter extends BaseEntity {

    @Column(name = "fhir_id", unique = true)
    private String fhirId;

    @Column(name = "epic_encounter_id")
    private String epicEncounterId;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "patient_id", nullable = false)
    private Patient patient;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "provider_id", nullable = false)
    private User provider;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private EncounterStatus status;

    @Enumerated(EnumType.STRING)
    @Column(name = "encounter_type", nullable = false)
    private EncounterType type;

    @Column(name = "start_time")
    private Instant startTime;

    @Column(name = "end_time")
    private Instant endTime;

    @Column(name = "location")
    private String location;

    @Column(name = "chief_complaint", columnDefinition = "TEXT")
    private String chiefComplaint;

    @Column(name = "reason_for_visit", columnDefinition = "TEXT")
    private String reasonForVisit;

    @OneToMany(mappedBy = "encounter", cascade = CascadeType.ALL, orphanRemoval = true)
    @Builder.Default
    private List<ClinicalNote> clinicalNotes = new ArrayList<>();

    @OneToMany(mappedBy = "encounter", cascade = CascadeType.ALL, orphanRemoval = true)
    @Builder.Default
    private List<Transcription> transcriptions = new ArrayList<>();

    @OneToOne(mappedBy = "encounter", cascade = CascadeType.ALL, orphanRemoval = true)
    private Session activeSession;

    public enum EncounterStatus {
        PLANNED,
        IN_PROGRESS,
        ON_HOLD,
        COMPLETED,
        CANCELLED
    }

    public enum EncounterType {
        OUTPATIENT,
        INPATIENT,
        EMERGENCY,
        HOME_VISIT,
        TELEHEALTH,
        FIELD_RESPONSE,  // For first responders/military
        MEDEVAC          // Military medical evacuation
    }
}
