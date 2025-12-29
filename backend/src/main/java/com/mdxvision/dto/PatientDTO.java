package com.mdxvision.dto;

import com.mdxvision.entity.Patient;
import lombok.*;

import java.time.LocalDate;
import java.util.UUID;

public class PatientDTO {

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class Response {
        private UUID id;
        private String fhirId;
        private String epicPatientId;
        private String mrn;
        private String firstName;
        private String lastName;
        private String fullName;
        private LocalDate dateOfBirth;
        private Patient.Gender gender;
        private String phone;
        private String email;
        private AddressDTO address;
        private String preferredLanguage;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class AddressDTO {
        private String line1;
        private String line2;
        private String city;
        private String state;
        private String postalCode;
        private String country;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class SearchRequest {
        private String query;
        private int page = 0;
        private int size = 20;
    }
}
