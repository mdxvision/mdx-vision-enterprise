package com.mdxvision.fhir;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

import java.util.List;
import java.util.Optional;

import org.hl7.fhir.r4.model.*;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;

import com.mdxvision.fhir.UnifiedEhrService.EhrSystem;
import com.mdxvision.fhir.UnifiedEhrService.PatientData;
import com.mdxvision.fhir.UnifiedEhrService.PatientSummary;
import com.mdxvision.fhir.UnifiedEhrService.VitalSign;

/**
 * Unit tests for UnifiedEhrService
 *
 * Tests the multi-EHR abstraction layer that provides a single interface
 * for AR glasses to access patient data from Epic, Cerner, and Veradigm.
 */
@ExtendWith(MockitoExtension.class)
@DisplayName("UnifiedEhrService Tests")
class UnifiedEhrServiceTest {

    @Mock
    private EpicFhirService epicService;

    @Mock
    private CernerFhirService cernerService;

    @Mock
    private VeradigmFhirService veradigmService;

    @InjectMocks
    private UnifiedEhrService unifiedEhrService;

    private Patient testPatient;

    @BeforeEach
    void setUp() {
        // Set default EHR system
        ReflectionTestUtils.setField(unifiedEhrService, "defaultEhrSystem", "CERNER");

        // Create test patient
        testPatient = createTestPatient("12724066", "SMARTS SR., NANCYS II", "1990-09-15", "female");
    }

    private Patient createTestPatient(String id, String name, String birthDate, String gender) {
        Patient patient = new Patient();
        patient.setId(id);
        patient.addName().setFamily(name.split(",")[0]).addGiven(name.contains(",") ? name.split(",")[1].trim() : "");
        patient.setBirthDateElement(new DateType(birthDate));
        patient.setGender(Enumerations.AdministrativeGender.fromCode(gender));
        patient.addIdentifier().setValue("MRN-" + id);
        return patient;
    }

    @Nested
    @DisplayName("getPatient Tests")
    class GetPatientTests {

        @Test
        @DisplayName("Should get patient from Cerner when default is CERNER")
        void shouldGetPatientFromCernerByDefault() {
            // Arrange
            when(cernerService.getPatientById("12724066")).thenReturn(Optional.of(testPatient));

            // Act
            Optional<PatientData> result = unifiedEhrService.getPatient("12724066");

            // Assert
            assertTrue(result.isPresent());
            assertEquals("12724066", result.get().getPatientId());
            assertEquals("CERNER", result.get().getEhrSystem());
            verify(cernerService).getPatientById("12724066");
            verifyNoInteractions(epicService, veradigmService);
        }

        @Test
        @DisplayName("Should get patient from Epic when explicitly specified")
        void shouldGetPatientFromEpicWhenSpecified() {
            // Arrange
            when(epicService.getPatientById("epic-123")).thenReturn(Optional.of(testPatient));

            // Act
            Optional<PatientData> result = unifiedEhrService.getPatient("epic-123", EhrSystem.EPIC);

            // Assert
            assertTrue(result.isPresent());
            assertEquals("EPIC", result.get().getEhrSystem());
            verify(epicService).getPatientById("epic-123");
            verifyNoInteractions(cernerService, veradigmService);
        }

        @Test
        @DisplayName("Should get patient from Veradigm when explicitly specified")
        void shouldGetPatientFromVeradigmWhenSpecified() {
            // Arrange
            when(veradigmService.getPatientById("vera-456")).thenReturn(Optional.of(testPatient));

            // Act
            Optional<PatientData> result = unifiedEhrService.getPatient("vera-456", EhrSystem.VERADIGM);

            // Assert
            assertTrue(result.isPresent());
            assertEquals("VERADIGM", result.get().getEhrSystem());
            verify(veradigmService).getPatientById("vera-456");
            verifyNoInteractions(cernerService, epicService);
        }

        @Test
        @DisplayName("Should return empty when patient not found")
        void shouldReturnEmptyWhenPatientNotFound() {
            // Arrange
            when(cernerService.getPatientById("unknown")).thenReturn(Optional.empty());

            // Act
            Optional<PatientData> result = unifiedEhrService.getPatient("unknown");

            // Assert
            assertTrue(result.isEmpty());
        }

        @Test
        @DisplayName("Should return empty for unsupported EHR system")
        void shouldReturnEmptyForUnsupportedEhrSystem() {
            // Act
            Optional<PatientData> result = unifiedEhrService.getPatient("123", EhrSystem.GENERIC_FHIR);

            // Assert
            assertTrue(result.isEmpty());
        }

        @Test
        @DisplayName("Should handle service exceptions gracefully")
        void shouldHandleServiceExceptionsGracefully() {
            // Arrange
            when(cernerService.getPatientById("error-patient"))
                    .thenThrow(new RuntimeException("Network error"));

            // Act
            Optional<PatientData> result = unifiedEhrService.getPatient("error-patient");

            // Assert
            assertTrue(result.isEmpty());
        }
    }

    @Nested
    @DisplayName("getPatientByMrn Tests")
    class GetPatientByMrnTests {

        @Test
        @DisplayName("Should get patient by MRN from default EHR")
        void shouldGetPatientByMrnFromDefaultEhr() {
            // Arrange
            when(cernerService.getPatientByMrn("MRN-123")).thenReturn(Optional.of(testPatient));

            // Act
            Optional<PatientData> result = unifiedEhrService.getPatientByMrn("MRN-123");

            // Assert
            assertTrue(result.isPresent());
            verify(cernerService).getPatientByMrn("MRN-123");
        }

        @Test
        @DisplayName("Should get patient by MRN from specified EHR")
        void shouldGetPatientByMrnFromSpecifiedEhr() {
            // Arrange
            when(epicService.getPatientByMrn("EPIC-MRN-456")).thenReturn(Optional.of(testPatient));

            // Act
            Optional<PatientData> result = unifiedEhrService.getPatientByMrn("EPIC-MRN-456", EhrSystem.EPIC);

            // Assert
            assertTrue(result.isPresent());
            verify(epicService).getPatientByMrn("EPIC-MRN-456");
        }

        @Test
        @DisplayName("Should handle MRN not found")
        void shouldHandleMrnNotFound() {
            // Arrange
            when(cernerService.getPatientByMrn("INVALID-MRN")).thenReturn(Optional.empty());

            // Act
            Optional<PatientData> result = unifiedEhrService.getPatientByMrn("INVALID-MRN");

            // Assert
            assertTrue(result.isEmpty());
        }
    }

    @Nested
    @DisplayName("searchPatients Tests")
    class SearchPatientsTests {

        @Test
        @DisplayName("Should search patients by name")
        void shouldSearchPatientsByName() {
            // Arrange
            Patient patient1 = createTestPatient("1", "SMITH, JOHN", "1980-01-01", "male");
            Patient patient2 = createTestPatient("2", "SMITH, JANE", "1985-05-15", "female");
            when(cernerService.searchPatientsByName("SMITH")).thenReturn(List.of(patient1, patient2));

            // Act
            List<PatientData> results = unifiedEhrService.searchPatients("SMITH");

            // Assert
            assertEquals(2, results.size());
            verify(cernerService).searchPatientsByName("SMITH");
        }

        @Test
        @DisplayName("Should return empty list when no patients found")
        void shouldReturnEmptyListWhenNoPatientsFound() {
            // Arrange
            when(cernerService.searchPatientsByName("UNKNOWN")).thenReturn(List.of());

            // Act
            List<PatientData> results = unifiedEhrService.searchPatients("UNKNOWN");

            // Assert
            assertTrue(results.isEmpty());
        }

        @Test
        @DisplayName("Should search in specified EHR system")
        void shouldSearchInSpecifiedEhrSystem() {
            // Arrange
            when(epicService.searchPatientsByName("DOE")).thenReturn(List.of(testPatient));

            // Act
            List<PatientData> results = unifiedEhrService.searchPatients("DOE", EhrSystem.EPIC);

            // Assert
            assertEquals(1, results.size());
            verify(epicService).searchPatientsByName("DOE");
        }
    }

    @Nested
    @DisplayName("getPatientSummary Tests")
    class GetPatientSummaryTests {

        @Test
        @DisplayName("Should get complete patient summary with all data")
        void shouldGetCompletePatientSummary() {
            // Arrange
            when(cernerService.getPatientById("12724066")).thenReturn(Optional.of(testPatient));
            when(cernerService.getPatientVitals("12724066")).thenReturn(createTestVitals());
            when(cernerService.getPatientConditions("12724066")).thenReturn(createTestConditions());
            when(cernerService.getPatientAllergies("12724066")).thenReturn(createTestAllergies());
            when(cernerService.getPatientMedications("12724066")).thenReturn(createTestMedications());

            // Act
            Optional<PatientSummary> result = unifiedEhrService.getPatientSummary("12724066");

            // Assert
            assertTrue(result.isPresent());
            PatientSummary summary = result.get();
            assertEquals("12724066", summary.getPatientId());
            assertNotNull(summary.getVitals());
            assertNotNull(summary.getActiveConditions());
            assertNotNull(summary.getAllergies());
            assertNotNull(summary.getActiveMedications());
        }

        @Test
        @DisplayName("Should return empty when patient not found")
        void shouldReturnEmptyWhenPatientNotFoundForSummary() {
            // Arrange
            when(cernerService.getPatientById("unknown")).thenReturn(Optional.empty());

            // Act
            Optional<PatientSummary> result = unifiedEhrService.getPatientSummary("unknown");

            // Assert
            assertTrue(result.isEmpty());
        }

        @Test
        @DisplayName("toArDisplay should format summary for AR glasses")
        void toArDisplayShouldFormatSummaryForArGlasses() {
            // Arrange
            PatientSummary summary = new PatientSummary();
            summary.setName("SMARTS SR., NANCYS II");
            summary.setGender("female");
            summary.setDateOfBirth("1990-09-15");
            summary.setAllergies(List.of("Penicillin", "Sulfa"));

            // Act
            String arDisplay = summary.toArDisplay();

            // Assert
            assertTrue(arDisplay.contains("SMARTS SR., NANCYS II"));
            assertTrue(arDisplay.contains("female"));
            assertTrue(arDisplay.contains("1990-09-15"));
            assertTrue(arDisplay.contains("ALLERGIES:"));
            assertTrue(arDisplay.contains("Penicillin"));
        }
    }

    @Nested
    @DisplayName("getVitals Tests")
    class GetVitalsTests {

        @Test
        @DisplayName("Should get vitals with proper conversion")
        void shouldGetVitalsWithProperConversion() {
            // Arrange
            when(cernerService.getPatientVitals("12724066")).thenReturn(createTestVitals());

            // Act
            List<VitalSign> vitals = unifiedEhrService.getVitals("12724066", EhrSystem.CERNER);

            // Assert
            assertFalse(vitals.isEmpty());
        }

        @Test
        @DisplayName("Should handle empty vitals")
        void shouldHandleEmptyVitals() {
            // Arrange
            when(cernerService.getPatientVitals("12724066")).thenReturn(List.of());

            // Act
            List<VitalSign> vitals = unifiedEhrService.getVitals("12724066", EhrSystem.CERNER);

            // Assert
            assertTrue(vitals.isEmpty());
        }
    }

    @Nested
    @DisplayName("PatientData DTO Tests")
    class PatientDataDtoTests {

        @Test
        @DisplayName("Should properly convert Patient to PatientData")
        void shouldProperlyConvertPatientToPatientData() {
            // Arrange
            when(cernerService.getPatientById("12724066")).thenReturn(Optional.of(testPatient));

            // Act
            Optional<PatientData> result = unifiedEhrService.getPatient("12724066");

            // Assert
            assertTrue(result.isPresent());
            PatientData data = result.get();
            assertEquals("12724066", data.getPatientId());
            assertNotNull(data.getName());
            assertEquals("female", data.getGender());
            assertEquals("CERNER", data.getEhrSystem());
        }

        @Test
        @DisplayName("PatientData getters and setters should work")
        void patientDataGettersAndSettersShouldWork() {
            // Arrange
            PatientData data = new PatientData();

            // Act
            data.setPatientId("123");
            data.setName("Test Patient");
            data.setMrn("MRN-123");
            data.setDateOfBirth("2000-01-01");
            data.setGender("male");
            data.setEhrSystem("EPIC");

            // Assert
            assertEquals("123", data.getPatientId());
            assertEquals("Test Patient", data.getName());
            assertEquals("MRN-123", data.getMrn());
            assertEquals("2000-01-01", data.getDateOfBirth());
            assertEquals("male", data.getGender());
            assertEquals("EPIC", data.getEhrSystem());
        }
    }

    @Nested
    @DisplayName("VitalSign DTO Tests")
    class VitalSignDtoTests {

        @Test
        @DisplayName("VitalSign toString should format properly")
        void vitalSignToStringShouldFormatProperly() {
            // Arrange
            VitalSign vital = new VitalSign();
            vital.setName("Blood Pressure");
            vital.setValue("120/80");
            vital.setUnit("mmHg");

            // Act
            String result = vital.toString();

            // Assert
            assertEquals("Blood Pressure: 120/80 mmHg", result);
        }

        @Test
        @DisplayName("VitalSign getters and setters should work")
        void vitalSignGettersAndSettersShouldWork() {
            // Arrange
            VitalSign vital = new VitalSign();

            // Act
            vital.setCode("8480-6");
            vital.setName("Systolic BP");
            vital.setValue("120");
            vital.setUnit("mmHg");
            vital.setTimestamp("2025-01-05T10:00:00");

            // Assert
            assertEquals("8480-6", vital.getCode());
            assertEquals("Systolic BP", vital.getName());
            assertEquals("120", vital.getValue());
            assertEquals("mmHg", vital.getUnit());
            assertEquals("2025-01-05T10:00:00", vital.getTimestamp());
        }
    }

    @Nested
    @DisplayName("EHR System Selection Tests")
    class EhrSystemSelectionTests {

        @Test
        @DisplayName("Should default to EPIC when config is invalid")
        void shouldDefaultToEpicWhenConfigIsInvalid() {
            // Arrange
            ReflectionTestUtils.setField(unifiedEhrService, "defaultEhrSystem", "INVALID");
            when(epicService.getPatientById("123")).thenReturn(Optional.of(testPatient));

            // Act
            Optional<PatientData> result = unifiedEhrService.getPatient("123");

            // Assert
            assertTrue(result.isPresent());
            assertEquals("EPIC", result.get().getEhrSystem());
        }

        @Test
        @DisplayName("All EhrSystem enum values should be valid")
        void allEhrSystemEnumValuesShouldBeValid() {
            // Assert all expected values exist
            assertNotNull(EhrSystem.EPIC);
            assertNotNull(EhrSystem.CERNER);
            assertNotNull(EhrSystem.VERADIGM);
            assertNotNull(EhrSystem.MEDITECH);
            assertNotNull(EhrSystem.ATHENA);
            assertNotNull(EhrSystem.NEXTGEN);
            assertNotNull(EhrSystem.ECLINICALWORKS);
            assertNotNull(EhrSystem.GENERIC_FHIR);
        }
    }

    // Helper methods to create test data

    private List<Observation> createTestVitals() {
        Observation bp = new Observation();
        bp.setId("vital-1");
        bp.getCode().addCoding()
                .setSystem("http://loinc.org")
                .setCode("8480-6")
                .setDisplay("Systolic Blood Pressure");
        bp.setValue(new Quantity().setValue(120).setUnit("mmHg"));
        bp.setEffective(new DateTimeType("2025-01-05T10:00:00"));
        return List.of(bp);
    }

    private List<Condition> createTestConditions() {
        Condition condition = new Condition();
        condition.setId("condition-1");
        condition.getCode().setText("Type 2 Diabetes Mellitus");
        return List.of(condition);
    }

    private List<AllergyIntolerance> createTestAllergies() {
        AllergyIntolerance allergy = new AllergyIntolerance();
        allergy.setId("allergy-1");
        allergy.getCode().setText("Penicillin");
        return List.of(allergy);
    }

    private List<MedicationRequest> createTestMedications() {
        MedicationRequest med = new MedicationRequest();
        med.setId("med-1");
        CodeableConcept medConcept = new CodeableConcept();
        medConcept.setText("Metformin 500mg");
        med.setMedication(medConcept);
        return List.of(med);
    }
}
