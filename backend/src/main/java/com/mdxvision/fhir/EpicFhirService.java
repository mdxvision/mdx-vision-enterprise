package com.mdxvision.fhir;

import java.util.ArrayList;
import java.util.List;
import java.util.Optional;

import org.hl7.fhir.r4.model.Bundle;
import org.hl7.fhir.r4.model.Encounter;
import org.hl7.fhir.r4.model.Observation;
import org.hl7.fhir.r4.model.Patient;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import ca.uhn.fhir.rest.client.api.IGenericClient;
import ca.uhn.fhir.rest.gclient.StringClientParam;

/**
 * Epic FHIR R4 Service
 *
 * Provides access to Epic EHR data via FHIR R4 API:
 * - Patient demographics
 * - Vital signs (Observations)
 * - Encounters
 * - Allergies
 * - Medications
 *
 * Implements MDx Vision Patent Claims:
 * - Claim 9: Wireless connection to EHR
 * - Integration with Epic (and other EHR systems)
 */
@Service
public class EpicFhirService {

    private static final Logger log = LoggerFactory.getLogger(EpicFhirService.class);

    private final IGenericClient fhirClient;

    public EpicFhirService(IGenericClient epicFhirClient) {
        this.fhirClient = epicFhirClient;
    }

    /**
     * Look up patient by MRN (Medical Record Number)
     */
    public Optional<Patient> getPatientByMrn(String mrn) {
        try {
            Bundle results = fhirClient.search()
                    .forResource(Patient.class)
                    .where(new StringClientParam("identifier").matches().value(mrn))
                    .returnBundle(Bundle.class)
                    .execute();

            if (results.hasEntry()) {
                return Optional.of((Patient) results.getEntryFirstRep().getResource());
            }
        } catch (Exception e) {
            log.error("Error fetching patient by MRN {}: {}", mrn, e.getMessage());
        }
        return Optional.empty();
    }

    /**
     * Look up patient by FHIR ID
     */
    public Optional<Patient> getPatientById(String patientId) {
        try {
            Patient patient = fhirClient.read()
                    .resource(Patient.class)
                    .withId(patientId)
                    .execute();
            return Optional.of(patient);
        } catch (Exception e) {
            log.error("Error fetching patient {}: {}", patientId, e.getMessage());
        }
        return Optional.empty();
    }

    /**
     * Search patients by name
     */
    public List<Patient> searchPatientsByName(String name) {
        List<Patient> patients = new ArrayList<>();
        try {
            Bundle results = fhirClient.search()
                    .forResource(Patient.class)
                    .where(new StringClientParam("name").matches().value(name))
                    .returnBundle(Bundle.class)
                    .execute();

            results.getEntry().forEach(entry -> {
                if (entry.getResource() instanceof Patient) {
                    patients.add((Patient) entry.getResource());
                }
            });
        } catch (Exception e) {
            log.error("Error searching patients: {}", e.getMessage());
        }
        return patients;
    }

    /**
     * Get latest vital signs for a patient
     */
    public List<Observation> getPatientVitals(String patientId) {
        List<Observation> vitals = new ArrayList<>();
        try {
            // LOINC codes for common vitals
            String[] vitalCodes = {
                    "8867-4",  // Heart rate
                    "8480-6",  // Systolic BP
                    "8462-4",  // Diastolic BP
                    "8310-5",  // Body temperature
                    "9279-1",  // Respiratory rate
                    "59408-5", // SpO2
                    "29463-7"  // Body weight
            };

            for (String code : vitalCodes) {
                Bundle results = fhirClient.search()
                        .forResource(Observation.class)
                        .where(Observation.PATIENT.hasId(patientId))
                        .and(Observation.CODE.exactly().code(code))
                        .sort().descending(Observation.DATE)
                        .count(1)
                        .returnBundle(Bundle.class)
                        .execute();

                results.getEntry().forEach(entry -> {
                    if (entry.getResource() instanceof Observation) {
                        vitals.add((Observation) entry.getResource());
                    }
                });
            }
        } catch (Exception e) {
            log.error("Error fetching vitals for patient {}: {}", patientId, e.getMessage());
        }
        return vitals;
    }

    /**
     * Get active encounters for a patient
     */
    public List<Encounter> getPatientEncounters(String patientId) {
        List<Encounter> encounters = new ArrayList<>();
        try {
            Bundle results = fhirClient.search()
                    .forResource(Encounter.class)
                    .where(Encounter.PATIENT.hasId(patientId))
                    .and(Encounter.STATUS.exactly().code("in-progress"))
                    .returnBundle(Bundle.class)
                    .execute();

            results.getEntry().forEach(entry -> {
                if (entry.getResource() instanceof Encounter) {
                    encounters.add((Encounter) entry.getResource());
                }
            });
        } catch (Exception e) {
            log.error("Error fetching encounters for patient {}: {}", patientId, e.getMessage());
        }
        return encounters;
    }

    /**
     * Create a clinical note observation
     */
    public Observation createClinicalNote(String patientId, String encounterId, String noteText) {
        try {
            Observation note = new Observation();
            note.setStatus(Observation.ObservationStatus.FINAL);

            // Set patient reference
            note.getSubject().setReference("Patient/" + patientId);

            // Set encounter reference if provided
            if (encounterId != null) {
                note.getEncounter().setReference("Encounter/" + encounterId);
            }

            // Set category as clinical note
            note.addCategory()
                    .addCoding()
                    .setSystem("http://terminology.hl7.org/CodeSystem/observation-category")
                    .setCode("exam")
                    .setDisplay("Exam");

            // Set the note text
            note.getValueStringType().setValue(noteText);

            // Create in Epic
            return (Observation) fhirClient.create()
                    .resource(note)
                    .execute()
                    .getResource();

        } catch (Exception e) {
            log.error("Error creating clinical note: {}", e.getMessage());
            throw new RuntimeException("Failed to create clinical note", e);
        }
    }

    /**
     * Format patient data for AR glasses display
     */
    public PatientSummary getPatientSummaryForDisplay(String patientId) {
        Optional<Patient> patientOpt = getPatientById(patientId);
        if (patientOpt.isEmpty()) {
            return null;
        }

        Patient patient = patientOpt.get();
        List<Observation> vitals = getPatientVitals(patientId);

        PatientSummary summary = new PatientSummary();
        summary.setPatientId(patientId);

        // Extract name
        if (patient.hasName()) {
            summary.setName(patient.getNameFirstRep().getNameAsSingleString());
        }

        // Extract DOB
        if (patient.hasBirthDate()) {
            summary.setDateOfBirth(patient.getBirthDate().toString());
        }

        // Extract vitals
        for (Observation vital : vitals) {
            String code = vital.getCode().getCodingFirstRep().getCode();
            String value = "";

            if (vital.hasValueQuantity()) {
                value = vital.getValueQuantity().getValue().toString() +
                        " " + vital.getValueQuantity().getUnit();
            }

            switch (code) {
                case "8867-4":
                    summary.setHeartRate(value);
                    break;
                case "8480-6":
                    summary.setSystolicBp(value);
                    break;
                case "8462-4":
                    summary.setDiastolicBp(value);
                    break;
                case "8310-5":
                    summary.setTemperature(value);
                    break;
                case "59408-5":
                    summary.setSpO2(value);
                    break;
            }
        }

        return summary;
    }

    /**
     * Patient summary DTO for AR display
     */
    public static class PatientSummary {
        private String patientId;
        private String name;
        private String dateOfBirth;
        private String heartRate;
        private String systolicBp;
        private String diastolicBp;
        private String temperature;
        private String spO2;

        // Getters and setters
        public String getPatientId() { return patientId; }
        public void setPatientId(String patientId) { this.patientId = patientId; }
        public String getName() { return name; }
        public void setName(String name) { this.name = name; }
        public String getDateOfBirth() { return dateOfBirth; }
        public void setDateOfBirth(String dateOfBirth) { this.dateOfBirth = dateOfBirth; }
        public String getHeartRate() { return heartRate; }
        public void setHeartRate(String heartRate) { this.heartRate = heartRate; }
        public String getSystolicBp() { return systolicBp; }
        public void setSystolicBp(String systolicBp) { this.systolicBp = systolicBp; }
        public String getDiastolicBp() { return diastolicBp; }
        public void setDiastolicBp(String diastolicBp) { this.diastolicBp = diastolicBp; }
        public String getTemperature() { return temperature; }
        public void setTemperature(String temperature) { this.temperature = temperature; }
        public String getSpO2() { return spO2; }
        public void setSpO2(String spO2) { this.spO2 = spO2; }

        @Override
        public String toString() {
            return String.format(
                    "%s | DOB: %s\nHR: %s | BP: %s/%s | Temp: %s | SpO2: %s",
                    name, dateOfBirth, heartRate, systolicBp, diastolicBp, temperature, spO2
            );
        }
    }
}
