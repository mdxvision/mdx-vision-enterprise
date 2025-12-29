package com.mdxvision.entity;

import jakarta.persistence.*;
import lombok.*;

import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "audit_logs", indexes = {
    @Index(name = "idx_audit_user", columnList = "user_id"),
    @Index(name = "idx_audit_entity", columnList = "entity_type, entity_id"),
    @Index(name = "idx_audit_timestamp", columnList = "timestamp")
})
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class AuditLog {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(name = "user_id")
    private UUID userId;

    @Column(name = "user_email")
    private String userEmail;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private AuditAction action;

    @Column(name = "entity_type", nullable = false)
    private String entityType;

    @Column(name = "entity_id")
    private String entityId;

    @Column(name = "patient_id")
    private UUID patientId; // For HIPAA tracking - PHI access

    @Column(name = "description", columnDefinition = "TEXT")
    private String description;

    @Column(name = "old_value", columnDefinition = "TEXT")
    private String oldValue;

    @Column(name = "new_value", columnDefinition = "TEXT")
    private String newValue;

    @Column(name = "ip_address")
    private String ipAddress;

    @Column(name = "user_agent")
    private String userAgent;

    @Column(name = "device_type")
    private String deviceType;

    @Column(nullable = false)
    private Instant timestamp;

    @Column(name = "organization_id")
    private String organizationId;

    public enum AuditAction {
        // Authentication
        LOGIN,
        LOGOUT,
        LOGIN_FAILED,
        
        // CRUD Operations
        CREATE,
        READ,
        UPDATE,
        DELETE,
        
        // Clinical Actions
        VIEW_PATIENT,
        VIEW_PHI,
        EXPORT_DATA,
        START_SESSION,
        END_SESSION,
        SIGN_NOTE,
        PUSH_TO_EHR,
        
        // AI Actions
        GENERATE_NOTE,
        TRANSCRIPTION_START,
        TRANSCRIPTION_END,
        TRANSLATION,
        
        // System
        SYSTEM_ERROR,
        PERMISSION_DENIED
    }
}
