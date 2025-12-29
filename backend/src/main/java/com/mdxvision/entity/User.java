package com.mdxvision.entity;

import jakarta.persistence.*;
import lombok.*;

import java.util.HashSet;
import java.util.Set;

@Entity
@Table(name = "users")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class User extends BaseEntity {

    @Column(nullable = false, unique = true)
    private String email;

    @Column(name = "external_id", unique = true)
    private String externalId; // Auth0 or Azure AD ID

    @Column(name = "first_name")
    private String firstName;

    @Column(name = "last_name")
    private String lastName;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private UserRole role;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private UserVertical vertical;

    @Column(name = "organization_id")
    private String organizationId;

    @Column(name = "npi_number")
    private String npiNumber; // For healthcare providers

    @Column(name = "specialty")
    private String specialty;

    @Column(name = "is_active")
    private boolean active = true;

    @Column(name = "epic_provider_id")
    private String epicProviderId;

    @Column(name = "epic_user_id")
    private String epicUserId;

    @OneToMany(mappedBy = "user", cascade = CascadeType.ALL, orphanRemoval = true)
    @Builder.Default
    private Set<Session> sessions = new HashSet<>();

    public enum UserRole {
        ADMIN,
        PHYSICIAN,
        NURSE,
        EMT,
        PARAMEDIC,
        COMBAT_MEDIC,
        FIRST_RESPONDER,
        CAREGIVER
    }

    public enum UserVertical {
        HEALTHCARE,
        MILITARY,
        FIRST_RESPONDER,
        ACCESSIBILITY
    }
}
