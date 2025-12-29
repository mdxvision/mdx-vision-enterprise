package com.mdxvision.dto;

import com.mdxvision.entity.Encounter;
import lombok.*;

import java.time.Instant;
import java.util.UUID;

public class EncounterDTO {

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class CreateRequest {
        private UUID patientId;
        private Encounter.EncounterType type;
        private String location;
        private String chiefComplaint;
        private String reasonForVisit;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class Response {
        private UUID id;
        private String fhirId;
        private PatientDTO.Response patient;
        private UserDTO.Response provider;
        private Encounter.EncounterStatus status;
        private Encounter.EncounterType type;
        private Instant startTime;
        private Instant endTime;
        private String location;
        private String chiefComplaint;
        private String reasonForVisit;
        private boolean hasActiveSession;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class UpdateRequest {
        private Encounter.EncounterStatus status;
        private String chiefComplaint;
        private String reasonForVisit;
    }
}
