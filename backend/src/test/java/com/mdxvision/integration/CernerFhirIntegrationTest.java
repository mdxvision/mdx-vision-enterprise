package com.mdxvision.integration;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Real Integration Tests against Cerner FHIR Sandbox
 *
 * These tests hit the actual Cerner sandbox - no mocking.
 * Run with: mvn test -Dtest=CernerFhirIntegrationTest
 */
@DisplayName("Cerner FHIR Integration Tests")
class CernerFhirIntegrationTest {

    private static final String CERNER_BASE = "https://fhir-open.cerner.com/r4/ec2458f2-1e24-41c8-b71b-0e701af7583d";
    private static final String TEST_PATIENT_ID = "12724066"; // SMARTS SR., NANCYS II

    private HttpClient httpClient;
    private ObjectMapper objectMapper;

    @BeforeEach
    void setUp() {
        httpClient = HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(60))
                .build();
        objectMapper = new ObjectMapper();
    }

    // Gateway errors that indicate Cerner sandbox is under load (not our fault)
    private static final int[] ACCEPTABLE_GATEWAY_ERRORS = {502, 503, 504};

    // Helper method to check if response is a gateway error
    private boolean isGatewayError(int statusCode) {
        for (int code : ACCEPTABLE_GATEWAY_ERRORS) {
            if (code == statusCode) return true;
        }
        return false;
    }

    // Helper method to skip test gracefully on gateway errors
    private void skipOnGatewayError(HttpResponse<String> response, String endpoint) {
        if (isGatewayError(response.statusCode())) {
            System.out.println("⚠ Cerner returned " + response.statusCode() +
                " on " + endpoint + " (sandbox under load) - test skipped");
            org.junit.jupiter.api.Assumptions.assumeTrue(false,
                "Cerner sandbox returned " + response.statusCode() + " - skipping test");
        }
    }

    // Helper to safely parse JSON only after checking for gateway errors
    private JsonNode parseJsonResponse(HttpResponse<String> response, String endpoint) throws Exception {
        skipOnGatewayError(response, endpoint);
        return objectMapper.readTree(response.body());
    }

    @Nested
    @DisplayName("Patient Resource Tests")
    class PatientResourceTests {

        @Test
        @DisplayName("Should fetch patient by ID from Cerner sandbox")
        void fetchPatientById() throws Exception {
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(CERNER_BASE + "/Patient/" + TEST_PATIENT_ID))
                    .header("Accept", "application/fhir+json")
                    .timeout(Duration.ofSeconds(120))
                    .GET()
                    .build();

            HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
            skipOnGatewayError(response, "/Patient/" + TEST_PATIENT_ID);
            assertEquals(200, response.statusCode(), "Expected 200 OK from Cerner");

            JsonNode patient = parseJsonResponse(response, "/Patient/" + TEST_PATIENT_ID);
            assertEquals("Patient", patient.get("resourceType").asText());
            assertEquals(TEST_PATIENT_ID, patient.get("id").asText());
            assertTrue(patient.has("name"), "Patient should have name");

            String familyName = patient.get("name").get(0).get("family").asText();
            System.out.println("✓ Fetched patient: " + familyName);
        }

        @Test
        @DisplayName("Should search patients by name")
        void searchPatientsByName() throws Exception {
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(CERNER_BASE + "/Patient?name=SMART"))
                    .header("Accept", "application/fhir+json")
                    .timeout(Duration.ofSeconds(120))
                    .GET()
                    .build();

            HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
            skipOnGatewayError(response, "/Patient?name=SMART");
            assertEquals(200, response.statusCode());

            JsonNode bundle = parseJsonResponse(response, "/Patient?name=SMART");
            assertEquals("Bundle", bundle.get("resourceType").asText());

            int total = bundle.has("total") ? bundle.get("total").asInt() :
                        (bundle.has("entry") ? bundle.get("entry").size() : 0);
            assertTrue(total > 0, "Should find at least one patient named SMART");
            System.out.println("✓ Found " + total + " patients matching 'SMART'");
        }

        @Test
        @DisplayName("Should return 404 for non-existent patient")
        void fetchNonExistentPatient() throws Exception {
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(CERNER_BASE + "/Patient/99999999999"))
                    .header("Accept", "application/fhir+json")
                    .timeout(Duration.ofSeconds(120))
                    .GET()
                    .build();

            HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
            skipOnGatewayError(response, "/Patient/99999999999");

            // Cerner returns 404 for not found
            assertTrue(response.statusCode() == 404 || response.statusCode() == 400,
                    "Expected 404 or 400 for non-existent patient");
            System.out.println("✓ Correctly returned " + response.statusCode() + " for non-existent patient");
        }
    }

    @Nested
    @DisplayName("Condition Resource Tests")
    class ConditionResourceTests {

        @Test
        @DisplayName("Should fetch conditions for patient")
        void fetchPatientConditions() throws Exception {
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(CERNER_BASE + "/Condition?patient=" + TEST_PATIENT_ID))
                    .header("Accept", "application/fhir+json")
                    .timeout(Duration.ofSeconds(120))
                    .GET()
                    .build();

            HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());

            // Accept 200 (success) or 502/503/504 (Cerner sandbox under load)
            skipOnGatewayError(response, "/Condition");
            assertEquals(200, response.statusCode(), "Expected 200 OK from Cerner");

            JsonNode bundle = parseJsonResponse(response, "/Condition");
            assertEquals("Bundle", bundle.get("resourceType").asText());

            if (bundle.has("entry")) {
                int count = bundle.get("entry").size();
                System.out.println("✓ Found " + count + " conditions for patient");

                // Print first few conditions
                for (int i = 0; i < Math.min(3, count); i++) {
                    JsonNode condition = bundle.get("entry").get(i).get("resource");
                    if (condition.has("code") && condition.get("code").has("coding")) {
                        String display = condition.get("code").get("coding").get(0).get("display").asText();
                        System.out.println("  - " + display);
                    }
                }
            } else {
                System.out.println("✓ No conditions documented for patient");
            }
        }
    }

    @Nested
    @DisplayName("Medication Resource Tests")
    class MedicationResourceTests {

        @Test
        @DisplayName("Should fetch medication requests for patient")
        void fetchPatientMedications() throws Exception {
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(CERNER_BASE + "/MedicationRequest?patient=" + TEST_PATIENT_ID))
                    .header("Accept", "application/fhir+json")
                    .timeout(Duration.ofSeconds(120))
                    .GET()
                    .build();

            HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
            skipOnGatewayError(response, "/MedicationRequest");
            assertEquals(200, response.statusCode());

            JsonNode bundle = parseJsonResponse(response, "/MedicationRequest");
            assertEquals("Bundle", bundle.get("resourceType").asText());

            int count = bundle.has("entry") ? bundle.get("entry").size() : 0;
            System.out.println("✓ Found " + count + " medication requests");
        }
    }

    @Nested
    @DisplayName("Allergy Resource Tests")
    class AllergyResourceTests {

        @Test
        @DisplayName("Should fetch allergies for patient")
        void fetchPatientAllergies() throws Exception {
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(CERNER_BASE + "/AllergyIntolerance?patient=" + TEST_PATIENT_ID))
                    .header("Accept", "application/fhir+json")
                    .timeout(Duration.ofSeconds(120))
                    .GET()
                    .build();

            HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
            skipOnGatewayError(response, "/AllergyIntolerance");
            assertEquals(200, response.statusCode());

            JsonNode bundle = parseJsonResponse(response, "/AllergyIntolerance");
            assertEquals("Bundle", bundle.get("resourceType").asText());

            int count = bundle.has("entry") ? bundle.get("entry").size() : 0;
            System.out.println("✓ Found " + count + " allergies");
        }
    }

    @Nested
    @DisplayName("Observation Resource Tests")
    class ObservationResourceTests {

        @Test
        @DisplayName("Should fetch vital signs for patient")
        void fetchPatientVitals() throws Exception {
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(CERNER_BASE + "/Observation?patient=" + TEST_PATIENT_ID + "&category=vital-signs"))
                    .header("Accept", "application/fhir+json")
                    .timeout(Duration.ofSeconds(120))
                    .GET()
                    .build();

            HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
            skipOnGatewayError(response, "/Observation?category=vital-signs");
            assertEquals(200, response.statusCode());

            JsonNode bundle = parseJsonResponse(response, "/Observation?category=vital-signs");
            int count = bundle.has("entry") ? bundle.get("entry").size() : 0;
            System.out.println("✓ Found " + count + " vital sign observations");
        }

        @Test
        @DisplayName("Should fetch lab results for patient")
        void fetchPatientLabs() throws Exception {
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(CERNER_BASE + "/Observation?patient=" + TEST_PATIENT_ID + "&category=laboratory"))
                    .header("Accept", "application/fhir+json")
                    .timeout(Duration.ofSeconds(120))
                    .GET()
                    .build();

            HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
            skipOnGatewayError(response, "/Observation?category=laboratory");
            assertEquals(200, response.statusCode());

            JsonNode bundle = parseJsonResponse(response, "/Observation?category=laboratory");
            int count = bundle.has("entry") ? bundle.get("entry").size() : 0;
            System.out.println("✓ Found " + count + " lab observations");
        }
    }

    @Nested
    @DisplayName("Capability Statement Tests")
    class CapabilityStatementTests {

        @Test
        @DisplayName("Should fetch server capability statement")
        void fetchCapabilityStatement() throws Exception {
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(CERNER_BASE + "/metadata"))
                    .header("Accept", "application/fhir+json")
                    .timeout(Duration.ofSeconds(120))
                    .GET()
                    .build();

            HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
            skipOnGatewayError(response, "/metadata");
            assertEquals(200, response.statusCode());

            JsonNode capability = parseJsonResponse(response, "/metadata");
            assertEquals("CapabilityStatement", capability.get("resourceType").asText());

            String fhirVersion = capability.get("fhirVersion").asText();
            System.out.println("✓ Cerner FHIR version: " + fhirVersion);

            // Check supported resources
            if (capability.has("rest")) {
                int resourceCount = capability.get("rest").get(0).get("resource").size();
                System.out.println("✓ Server supports " + resourceCount + " resource types");
            }
        }
    }

    @Nested
    @DisplayName("End-to-End Patient Summary Tests")
    class EndToEndTests {

        @Test
        @DisplayName("Should build complete patient summary from multiple resources")
        void buildPatientSummary() throws Exception {
            StringBuilder summary = new StringBuilder();
            summary.append("\n=== Patient Summary ===\n");

            // 1. Fetch patient demographics
            HttpRequest patientRequest = HttpRequest.newBuilder()
                    .uri(URI.create(CERNER_BASE + "/Patient/" + TEST_PATIENT_ID))
                    .header("Accept", "application/fhir+json")
                    .timeout(Duration.ofSeconds(120))
                    .GET()
                    .build();

            HttpResponse<String> patientResponse = httpClient.send(patientRequest, HttpResponse.BodyHandlers.ofString());
            skipOnGatewayError(patientResponse, "/Patient/" + TEST_PATIENT_ID);
            assertEquals(200, patientResponse.statusCode());

            JsonNode patient = parseJsonResponse(patientResponse, "/Patient/" + TEST_PATIENT_ID);
            String name = patient.get("name").get(0).get("given").get(0).asText() + " " +
                         patient.get("name").get(0).get("family").asText();
            String dob = patient.has("birthDate") ? patient.get("birthDate").asText() : "Unknown";
            String gender = patient.has("gender") ? patient.get("gender").asText() : "Unknown";

            summary.append("Name: ").append(name).append("\n");
            summary.append("DOB: ").append(dob).append("\n");
            summary.append("Gender: ").append(gender).append("\n");

            // 2. Fetch conditions
            HttpRequest conditionsRequest = HttpRequest.newBuilder()
                    .uri(URI.create(CERNER_BASE + "/Condition?patient=" + TEST_PATIENT_ID))
                    .header("Accept", "application/fhir+json")
                    .timeout(Duration.ofSeconds(120))
                    .GET()
                    .build();

            HttpResponse<String> conditionsResponse = httpClient.send(conditionsRequest, HttpResponse.BodyHandlers.ofString());
            skipOnGatewayError(conditionsResponse, "/Condition");
            JsonNode conditionsBundle = parseJsonResponse(conditionsResponse, "/Condition");

            summary.append("\nConditions:\n");
            if (conditionsBundle.has("entry")) {
                for (int i = 0; i < Math.min(5, conditionsBundle.get("entry").size()); i++) {
                    JsonNode condition = conditionsBundle.get("entry").get(i).get("resource");
                    if (condition.has("code") && condition.get("code").has("coding")) {
                        String display = condition.get("code").get("coding").get(0).get("display").asText();
                        summary.append("  - ").append(display).append("\n");
                    }
                }
            } else {
                summary.append("  None documented\n");
            }

            // 3. Fetch allergies
            HttpRequest allergiesRequest = HttpRequest.newBuilder()
                    .uri(URI.create(CERNER_BASE + "/AllergyIntolerance?patient=" + TEST_PATIENT_ID))
                    .header("Accept", "application/fhir+json")
                    .timeout(Duration.ofSeconds(120))
                    .GET()
                    .build();

            HttpResponse<String> allergiesResponse = httpClient.send(allergiesRequest, HttpResponse.BodyHandlers.ofString());
            skipOnGatewayError(allergiesResponse, "/AllergyIntolerance");
            JsonNode allergiesBundle = parseJsonResponse(allergiesResponse, "/AllergyIntolerance");

            summary.append("\nAllergies:\n");
            if (allergiesBundle.has("entry")) {
                for (JsonNode entry : allergiesBundle.get("entry")) {
                    JsonNode allergy = entry.get("resource");
                    if (allergy.has("code") && allergy.get("code").has("coding")) {
                        String display = allergy.get("code").get("coding").get(0).get("display").asText();
                        summary.append("  - ").append(display).append("\n");
                    }
                }
            } else {
                summary.append("  NKDA\n");
            }

            summary.append("\n======================\n");
            System.out.println(summary);
            System.out.println("✓ Complete patient summary built from real Cerner data");
        }
    }
}
