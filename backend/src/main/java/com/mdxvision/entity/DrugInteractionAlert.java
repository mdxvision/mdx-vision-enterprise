package com.mdxvision.entity;

import jakarta.persistence.*;
import lombok.*;

@Entity
@Table(name = "drug_interaction_alerts")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class DrugInteractionAlert extends BaseEntity {

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "clinical_note_id")
    private ClinicalNote clinicalNote;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "encounter_id")
    private Encounter encounter;

    @Column(name = "drug_1_name", nullable = false)
    private String drug1Name;

    @Column(name = "drug_1_rxnorm_code")
    private String drug1RxnormCode;

    @Column(name = "drug_2_name", nullable = false)
    private String drug2Name;

    @Column(name = "drug_2_rxnorm_code")
    private String drug2RxnormCode;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private Severity severity;

    @Column(name = "description", columnDefinition = "TEXT")
    private String description;

    @Column(name = "clinical_effect", columnDefinition = "TEXT")
    private String clinicalEffect;

    @Column(name = "recommendation", columnDefinition = "TEXT")
    private String recommendation;

    @Column(name = "acknowledged")
    private boolean acknowledged = false;

    @Column(name = "acknowledged_by")
    private String acknowledgedBy;

    public enum Severity {
        LOW,
        MODERATE,
        HIGH,
        CONTRAINDICATED
    }
}
