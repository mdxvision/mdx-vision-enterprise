package com.mdxvision.fhir;

import java.util.ArrayList;
import java.util.List;
import java.util.Optional;

import org.hl7.fhir.r4.model.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import ca.uhn.fhir.context.FhirContext;
import ca.uhn.fhir.rest.client.api.IGenericClient;
import ca.uhn.fhir.rest.client.interceptor.BearerTokenAuthInterceptor;
import ca.uhn.fhir.rest.gclient.StringClientParam;

/**
 * Veradigm (formerly Allscripts) FHIR R4 Service
 *
 * Veradigm FHIR API:
 * - Developer Portal: https://developer.veradigm.com
 * - Sandbox: https://fhir.fhirpoint.open.allscripts.com/fhirroute/open/sandbox/r4
 * - Supports: TouchWorks, Professional, Sunrise
 *
 * Implements MDx Vision Patent - EHR Integration:
 * - Works with Allscripts (now Veradigm) as specified in patent
 */
@Service
public class VeradigmFhirService {

    private static final Logger log = LoggerFactory.getLogger(VeradigmFhirService.class);

    private final FhirContext fhirContext;
    private IGenericClient fhirClient;

    @Value("${mdx.veradigm.base-url:https://fhir.fhirpoint.open.allscripts.com/fhirroute/open/sandbox/r4}")
    private String veradigmBaseUrl;

    @Value("${mdx.veradigm.access-token:}")
    private String accessToken;

    public VeradigmFhirService(FhirContext fhirContext) {
        this.fhirContext = fhirContext;
    }

    private IGenericClient getClient() {
        if (fhirClient == null) {
            fhirClient = fhirContext.newRestfulGenericClient(veradigmBaseUrl);
            if (accessToken != null && !accessToken.isEmpty()) {
                fhirClient.registerInterceptor(new BearerTokenAuthInterceptor(accessToken));
            }
        }
        return fhirClient;
    }

    /**
     * Get patient by FHIR ID
     */
    public Optional<Patient> getPatientById(String patientId) {
        try {
            Patient patient = getClient().read()
                    .resource(Patient.class)
                    .withId(patientId)
                    .execute();
            return Optional.of(patient);
        } catch (Exception e) {
            log.error("Veradigm: Error fetching patient {}: {}", patientId, e.getMessage());
        }
        return Optional.empty();
    }

    /**
     * Search patients by name
     */
    public List<Patient> searchPatientsByName(String name) {
        List<Patient> patients = new ArrayList<>();
        try {
            Bundle results = getClient().search()
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
            log.error("Veradigm: Error searching patients: {}", e.getMessage());
        }
        return patients;
    }

    /**
     * Get patient by MRN
     */
    public Optional<Patient> getPatientByMrn(String mrn) {
        try {
            Bundle results = getClient().search()
                    .forResource(Patient.class)
                    .where(new StringClientParam("identifier").matches().value(mrn))
                    .returnBundle(Bundle.class)
                    .execute();

            if (results.hasEntry()) {
                return Optional.of((Patient) results.getEntryFirstRep().getResource());
            }
        } catch (Exception e) {
            log.error("Veradigm: Error fetching patient by MRN {}: {}", mrn, e.getMessage());
        }
        return Optional.empty();
    }

    /**
     * Get vital signs
     */
    public List<Observation> getPatientVitals(String patientId) {
        List<Observation> vitals = new ArrayList<>();
        try {
            Bundle results = getClient().search()
                    .forResource(Observation.class)
                    .where(Observation.PATIENT.hasId(patientId))
                    .and(Observation.CATEGORY.exactly().code("vital-signs"))
                    .sort().descending(Observation.DATE)
                    .count(20)
                    .returnBundle(Bundle.class)
                    .execute();

            results.getEntry().forEach(entry -> {
                if (entry.getResource() instanceof Observation) {
                    vitals.add((Observation) entry.getResource());
                }
            });
        } catch (Exception e) {
            log.error("Veradigm: Error fetching vitals for patient {}: {}", patientId, e.getMessage());
        }
        return vitals;
    }

    /**
     * Get conditions/problems
     */
    public List<Condition> getPatientConditions(String patientId) {
        List<Condition> conditions = new ArrayList<>();
        try {
            Bundle results = getClient().search()
                    .forResource(Condition.class)
                    .where(Condition.PATIENT.hasId(patientId))
                    .returnBundle(Bundle.class)
                    .execute();

            results.getEntry().forEach(entry -> {
                if (entry.getResource() instanceof Condition) {
                    conditions.add((Condition) entry.getResource());
                }
            });
        } catch (Exception e) {
            log.error("Veradigm: Error fetching conditions for patient {}: {}", patientId, e.getMessage());
        }
        return conditions;
    }

    /**
     * Get medications
     */
    public List<MedicationRequest> getPatientMedications(String patientId) {
        List<MedicationRequest> medications = new ArrayList<>();
        try {
            Bundle results = getClient().search()
                    .forResource(MedicationRequest.class)
                    .where(MedicationRequest.PATIENT.hasId(patientId))
                    .returnBundle(Bundle.class)
                    .execute();

            results.getEntry().forEach(entry -> {
                if (entry.getResource() instanceof MedicationRequest) {
                    medications.add((MedicationRequest) entry.getResource());
                }
            });
        } catch (Exception e) {
            log.error("Veradigm: Error fetching medications for patient {}: {}", patientId, e.getMessage());
        }
        return medications;
    }

    /**
     * Get allergies
     */
    public List<AllergyIntolerance> getPatientAllergies(String patientId) {
        List<AllergyIntolerance> allergies = new ArrayList<>();
        try {
            Bundle results = getClient().search()
                    .forResource(AllergyIntolerance.class)
                    .where(AllergyIntolerance.PATIENT.hasId(patientId))
                    .returnBundle(Bundle.class)
                    .execute();

            results.getEntry().forEach(entry -> {
                if (entry.getResource() instanceof AllergyIntolerance) {
                    allergies.add((AllergyIntolerance) entry.getResource());
                }
            });
        } catch (Exception e) {
            log.error("Veradigm: Error fetching allergies for patient {}: {}", patientId, e.getMessage());
        }
        return allergies;
    }

    /**
     * Get clinical documents (CDA/CCDA)
     */
    public List<DocumentReference> getPatientDocuments(String patientId) {
        List<DocumentReference> documents = new ArrayList<>();
        try {
            Bundle results = getClient().search()
                    .forResource(DocumentReference.class)
                    .where(DocumentReference.PATIENT.hasId(patientId))
                    .sort().descending(DocumentReference.DATE)
                    .count(10)
                    .returnBundle(Bundle.class)
                    .execute();

            results.getEntry().forEach(entry -> {
                if (entry.getResource() instanceof DocumentReference) {
                    documents.add((DocumentReference) entry.getResource());
                }
            });
        } catch (Exception e) {
            log.error("Veradigm: Error fetching documents for patient {}: {}", patientId, e.getMessage());
        }
        return documents;
    }
}
