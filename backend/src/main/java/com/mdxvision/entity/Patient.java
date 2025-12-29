package com.mdxvision.entity;

import jakarta.persistence.*;
import lombok.*;

import java.time.LocalDate;
import java.util.HashSet;
import java.util.Set;

@Entity
@Table(name = "patients")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Patient extends BaseEntity {

    @Column(name = "fhir_id", unique = true)
    private String fhirId; // Reference to FHIR Patient resource

    @Column(name = "epic_patient_id")
    private String epicPatientId;

    @Column(name = "mrn")
    private String mrn; // Medical Record Number

    @Column(name = "first_name")
    private String firstName;

    @Column(name = "last_name")
    private String lastName;

    @Column(name = "date_of_birth")
    private LocalDate dateOfBirth;

    @Enumerated(EnumType.STRING)
    private Gender gender;

    @Column(name = "phone")
    private String phone;

    @Column(name = "email")
    private String email;

    @Column(name = "address_line1")
    private String addressLine1;

    @Column(name = "address_line2")
    private String addressLine2;

    @Column(name = "city")
    private String city;

    @Column(name = "state")
    private String state;

    @Column(name = "postal_code")
    private String postalCode;

    @Column(name = "country")
    private String country;

    @Column(name = "preferred_language")
    private String preferredLanguage;

    @Column(name = "organization_id")
    private String organizationId;

    @OneToMany(mappedBy = "patient", cascade = CascadeType.ALL)
    @Builder.Default
    private Set<Encounter> encounters = new HashSet<>();

    public enum Gender {
        MALE,
        FEMALE,
        OTHER,
        UNKNOWN
    }

    public String getFullName() {
        return firstName + " " + lastName;
    }
}
