package com.mdxvision.entity;

import jakarta.persistence.*;
import lombok.*;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;

@Entity
@Table(name = "clinical_notes")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class ClinicalNote extends BaseEntity {

    @Column(name = "fhir_document_reference_id")
    private String fhirDocumentReferenceId;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "encounter_id", nullable = false)
    private Encounter encounter;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "author_id", nullable = false)
    private User author;

    @Enumerated(EnumType.STRING)
    @Column(name = "note_type", nullable = false)
    private NoteType noteType;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private NoteStatus status;

    // SOAP Note Structure
    @Column(name = "subjective", columnDefinition = "TEXT")
    private String subjective;

    @Column(name = "objective", columnDefinition = "TEXT")
    private String objective;

    @Column(name = "assessment", columnDefinition = "TEXT")
    private String assessment;

    @Column(name = "plan", columnDefinition = "TEXT")
    private String plan;

    // Full note content
    @Column(name = "full_content", columnDefinition = "TEXT")
    private String fullContent;

    // AI-generated summary
    @Column(name = "ai_summary", columnDefinition = "TEXT")
    private String aiSummary;

    // ICD-10 Codes (stored as JSON array)
    @Column(name = "icd10_codes", columnDefinition = "TEXT")
    private String icd10Codes;

    // CPT Codes (stored as JSON array)
    @Column(name = "cpt_codes", columnDefinition = "TEXT")
    private String cptCodes;

    @Column(name = "signed_at")
    private Instant signedAt;

    @Column(name = "pushed_to_ehr_at")
    private Instant pushedToEhrAt;

    @Column(name = "ehr_document_id")
    private String ehrDocumentId;

    @OneToMany(mappedBy = "clinicalNote", cascade = CascadeType.ALL, orphanRemoval = true)
    @Builder.Default
    private List<DrugInteractionAlert> drugInteractionAlerts = new ArrayList<>();

    public enum NoteType {
        SOAP,           // Standard SOAP note
        PROGRESS,       // Progress note
        PROCEDURE,      // Procedure note
        DISCHARGE,      // Discharge summary
        CONSULTATION,   // Consultation note
        NINE_LINE,      // Military 9-line medevac
        PCR,           // Pre-hospital Care Report (EMS)
        HANDOFF        // Patient handoff note
    }

    public enum NoteStatus {
        DRAFT,
        AI_GENERATED,
        REVIEWED,
        SIGNED,
        AMENDED,
        PUSHED_TO_EHR
    }
}
