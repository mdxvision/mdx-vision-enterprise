package com.mdxvision.fhir;

import java.util.ArrayList;
import java.util.List;
import java.util.Optional;

import org.hl7.fhir.r4.model.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

/**
 * Unified EHR Service
 *
 * MDx Vision Patent Implementation:
 * "Interfaces with ALL EHR systems: Epic, Cerner, Allscripts,
 * Eclypsis, Soarian, Meditech, McKesson, MedHost"
 *
 * This service provides a single interface for AR glasses
 * to access patient data regardless of which EHR system
 * the healthcare facility uses.
 *
 * Supports automatic EHR detection based on configuration
 * or can be explicitly set per-organization.
 */
@Service
public class UnifiedEhrService {

    private static final Logger log = LoggerFactory.getLogger(UnifiedEhrService.class);

    public enum EhrSystem {
        EPIC,
        CERNER,
        VERADIGM,  // Allscripts
        MEDITECH,
        ATHENA,
        NEXTGEN,
        ECLINICALWORKS,
        GENERIC_FHIR
    }

    private final EpicFhirService epicService;
    private final CernerFhirService cernerService;
    private final VeradigmFhirService veradigmService;

    @Value("${mdx.ehr.default-system:EPIC}")
    private String defaultEhrSystem;

    public UnifiedEhrService(
            EpicFhirService epicService,
            CernerFhirService cernerService,
            VeradigmFhirService veradigmService) {
        this.epicService = epicService;
        this.cernerService = cernerService;
        this.veradigmService = veradigmService;
    }

    /**
     * Get patient by ID from the configured EHR
     */
    public Optional<PatientData> getPatient(String patientId) {
        return getPatient(patientId, getDefaultSystem());
    }

    /**
     * Get patient by ID from specific EHR system
     */
    public Optional<PatientData> getPatient(String patientId, EhrSystem system) {
        try {
            Optional<Patient> patientOpt = switch (system) {
                case EPIC -> epicService.getPatientById(patientId);
                case CERNER -> cernerService.getPatientById(patientId);
                case VERADIGM -> veradigmService.getPatientById(patientId);
                default -> Optional.empty();
            };

            return patientOpt.map(p -> convertToPatientData(p, system));
        } catch (Exception e) {
            log.error("Error fetching patient {} from {}: {}", patientId, system, e.getMessage());
            return Optional.empty();
        }
    }

    /**
     * Get patient by MRN (wristband scan)
     */
    public Optional<PatientData> getPatientByMrn(String mrn) {
        return getPatientByMrn(mrn, getDefaultSystem());
    }

    public Optional<PatientData> getPatientByMrn(String mrn, EhrSystem system) {
        try {
            Optional<Patient> patientOpt = switch (system) {
                case EPIC -> epicService.getPatientByMrn(mrn);
                case CERNER -> cernerService.getPatientByMrn(mrn);
                case VERADIGM -> veradigmService.getPatientByMrn(mrn);
                default -> Optional.empty();
            };

            return patientOpt.map(p -> convertToPatientData(p, system));
        } catch (Exception e) {
            log.error("Error fetching patient by MRN {} from {}: {}", mrn, system, e.getMessage());
            return Optional.empty();
        }
    }

    /**
     * Search patients by name (voice command)
     */
    public List<PatientData> searchPatients(String name) {
        return searchPatients(name, getDefaultSystem());
    }

    public List<PatientData> searchPatients(String name, EhrSystem system) {
        List<PatientData> results = new ArrayList<>();
        try {
            List<Patient> patients = switch (system) {
                case EPIC -> epicService.searchPatientsByName(name);
                case CERNER -> cernerService.searchPatientsByName(name);
                case VERADIGM -> veradigmService.searchPatientsByName(name);
                default -> List.of();
            };

            patients.forEach(p -> results.add(convertToPatientData(p, system)));
        } catch (Exception e) {
            log.error("Error searching patients '{}' in {}: {}", name, system, e.getMessage());
        }
        return results;
    }

    /**
     * Get complete patient summary for AR display
     */
    public Optional<PatientSummary> getPatientSummary(String patientId) {
        return getPatientSummary(patientId, getDefaultSystem());
    }

    public Optional<PatientSummary> getPatientSummary(String patientId, EhrSystem system) {
        Optional<PatientData> patientOpt = getPatient(patientId, system);
        if (patientOpt.isEmpty()) {
            return Optional.empty();
        }

        PatientData patient = patientOpt.get();
        PatientSummary summary = new PatientSummary();
        summary.setPatientId(patientId);
        summary.setName(patient.getName());
        summary.setDateOfBirth(patient.getDateOfBirth());
        summary.setGender(patient.getGender());
        summary.setEhrSystem(system.name());

        // Get vitals
        List<VitalSign> vitals = getVitals(patientId, system);
        summary.setVitals(vitals);

        // Get conditions
        List<String> conditions = getConditionNames(patientId, system);
        summary.setActiveConditions(conditions);

        // Get allergies
        List<String> allergies = getAllergyNames(patientId, system);
        summary.setAllergies(allergies);

        // Get medications
        List<String> medications = getMedicationNames(patientId, system);
        summary.setActiveMedications(medications);

        return Optional.of(summary);
    }

    /**
     * Get vital signs
     */
    public List<VitalSign> getVitals(String patientId, EhrSystem system) {
        List<VitalSign> vitals = new ArrayList<>();
        try {
            List<Observation> observations = switch (system) {
                case EPIC -> epicService.getPatientVitals(patientId);
                case CERNER -> cernerService.getPatientVitals(patientId);
                case VERADIGM -> veradigmService.getPatientVitals(patientId);
                default -> List.of();
            };

            for (Observation obs : observations) {
                VitalSign vital = new VitalSign();
                if (obs.hasCode() && obs.getCode().hasCoding()) {
                    vital.setCode(obs.getCode().getCodingFirstRep().getCode());
                    vital.setName(obs.getCode().getCodingFirstRep().getDisplay());
                }
                if (obs.hasValueQuantity()) {
                    vital.setValue(obs.getValueQuantity().getValue().toString());
                    vital.setUnit(obs.getValueQuantity().getUnit());
                }
                if (obs.hasEffectiveDateTimeType()) {
                    vital.setTimestamp(obs.getEffectiveDateTimeType().toHumanDisplay());
                }
                vitals.add(vital);
            }
        } catch (Exception e) {
            log.error("Error fetching vitals for patient {} from {}: {}", patientId, system, e.getMessage());
        }
        return vitals;
    }

    private List<String> getConditionNames(String patientId, EhrSystem system) {
        List<String> conditions = new ArrayList<>();
        try {
            List<Condition> conditionList = switch (system) {
                case CERNER -> cernerService.getPatientConditions(patientId);
                case VERADIGM -> veradigmService.getPatientConditions(patientId);
                default -> List.of();
            };

            conditionList.forEach(c -> {
                if (c.hasCode() && c.getCode().hasText()) {
                    conditions.add(c.getCode().getText());
                }
            });
        } catch (Exception e) {
            log.error("Error fetching conditions: {}", e.getMessage());
        }
        return conditions;
    }

    private List<String> getAllergyNames(String patientId, EhrSystem system) {
        List<String> allergies = new ArrayList<>();
        try {
            List<AllergyIntolerance> allergyList = switch (system) {
                case CERNER -> cernerService.getPatientAllergies(patientId);
                case VERADIGM -> veradigmService.getPatientAllergies(patientId);
                default -> List.of();
            };

            allergyList.forEach(a -> {
                if (a.hasCode() && a.getCode().hasText()) {
                    allergies.add(a.getCode().getText());
                }
            });
        } catch (Exception e) {
            log.error("Error fetching allergies: {}", e.getMessage());
        }
        return allergies;
    }

    private List<String> getMedicationNames(String patientId, EhrSystem system) {
        List<String> medications = new ArrayList<>();
        try {
            List<MedicationRequest> medList = switch (system) {
                case CERNER -> cernerService.getPatientMedications(patientId);
                case VERADIGM -> veradigmService.getPatientMedications(patientId);
                default -> List.of();
            };

            medList.forEach(m -> {
                if (m.hasMedicationCodeableConcept() && m.getMedicationCodeableConcept().hasText()) {
                    medications.add(m.getMedicationCodeableConcept().getText());
                }
            });
        } catch (Exception e) {
            log.error("Error fetching medications: {}", e.getMessage());
        }
        return medications;
    }

    private PatientData convertToPatientData(Patient patient, EhrSystem system) {
        PatientData data = new PatientData();
        data.setPatientId(patient.getIdElement().getIdPart());
        data.setEhrSystem(system.name());

        if (patient.hasName()) {
            data.setName(patient.getNameFirstRep().getNameAsSingleString());
        }
        if (patient.hasBirthDate()) {
            data.setDateOfBirth(patient.getBirthDate().toString());
        }
        if (patient.hasGender()) {
            data.setGender(patient.getGender().toCode());
        }
        if (patient.hasIdentifier()) {
            data.setMrn(patient.getIdentifierFirstRep().getValue());
        }

        return data;
    }

    private EhrSystem getDefaultSystem() {
        try {
            return EhrSystem.valueOf(defaultEhrSystem.toUpperCase());
        } catch (Exception e) {
            return EhrSystem.EPIC;
        }
    }

    // DTOs

    public static class PatientData {
        private String patientId;
        private String mrn;
        private String name;
        private String dateOfBirth;
        private String gender;
        private String ehrSystem;

        // Getters and setters
        public String getPatientId() { return patientId; }
        public void setPatientId(String patientId) { this.patientId = patientId; }
        public String getMrn() { return mrn; }
        public void setMrn(String mrn) { this.mrn = mrn; }
        public String getName() { return name; }
        public void setName(String name) { this.name = name; }
        public String getDateOfBirth() { return dateOfBirth; }
        public void setDateOfBirth(String dateOfBirth) { this.dateOfBirth = dateOfBirth; }
        public String getGender() { return gender; }
        public void setGender(String gender) { this.gender = gender; }
        public String getEhrSystem() { return ehrSystem; }
        public void setEhrSystem(String ehrSystem) { this.ehrSystem = ehrSystem; }
    }

    public static class VitalSign {
        private String code;
        private String name;
        private String value;
        private String unit;
        private String timestamp;

        // Getters and setters
        public String getCode() { return code; }
        public void setCode(String code) { this.code = code; }
        public String getName() { return name; }
        public void setName(String name) { this.name = name; }
        public String getValue() { return value; }
        public void setValue(String value) { this.value = value; }
        public String getUnit() { return unit; }
        public void setUnit(String unit) { this.unit = unit; }
        public String getTimestamp() { return timestamp; }
        public void setTimestamp(String timestamp) { this.timestamp = timestamp; }

        @Override
        public String toString() {
            return name + ": " + value + " " + unit;
        }
    }

    public static class PatientSummary {
        private String patientId;
        private String name;
        private String dateOfBirth;
        private String gender;
        private String ehrSystem;
        private List<VitalSign> vitals;
        private List<String> activeConditions;
        private List<String> allergies;
        private List<String> activeMedications;

        // Getters and setters
        public String getPatientId() { return patientId; }
        public void setPatientId(String patientId) { this.patientId = patientId; }
        public String getName() { return name; }
        public void setName(String name) { this.name = name; }
        public String getDateOfBirth() { return dateOfBirth; }
        public void setDateOfBirth(String dateOfBirth) { this.dateOfBirth = dateOfBirth; }
        public String getGender() { return gender; }
        public void setGender(String gender) { this.gender = gender; }
        public String getEhrSystem() { return ehrSystem; }
        public void setEhrSystem(String ehrSystem) { this.ehrSystem = ehrSystem; }
        public List<VitalSign> getVitals() { return vitals; }
        public void setVitals(List<VitalSign> vitals) { this.vitals = vitals; }
        public List<String> getActiveConditions() { return activeConditions; }
        public void setActiveConditions(List<String> activeConditions) { this.activeConditions = activeConditions; }
        public List<String> getAllergies() { return allergies; }
        public void setAllergies(List<String> allergies) { this.allergies = allergies; }
        public List<String> getActiveMedications() { return activeMedications; }
        public void setActiveMedications(List<String> activeMedications) { this.activeMedications = activeMedications; }

        /**
         * Format for AR glasses display (compact)
         */
        public String toArDisplay() {
            StringBuilder sb = new StringBuilder();
            sb.append(name).append(" | ").append(gender).append(" | DOB: ").append(dateOfBirth).append("\n");

            if (vitals != null && !vitals.isEmpty()) {
                sb.append("VITALS: ");
                vitals.forEach(v -> sb.append(v.getName()).append(": ").append(v.getValue()).append(" "));
                sb.append("\n");
            }

            if (allergies != null && !allergies.isEmpty()) {
                sb.append("ALLERGIES: ").append(String.join(", ", allergies)).append("\n");
            }

            return sb.toString();
        }
    }
}
