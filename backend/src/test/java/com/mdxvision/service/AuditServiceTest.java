package com.mdxvision.service;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

import java.util.UUID;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContext;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.oauth2.jwt.Jwt;

import com.mdxvision.entity.AuditLog;
import com.mdxvision.entity.AuditLog.AuditAction;
import com.mdxvision.repository.AuditLogRepository;

/**
 * Unit tests for AuditService
 *
 * Tests HIPAA-compliant audit logging functionality.
 * Validates that all PHI access is properly logged.
 */
@ExtendWith(MockitoExtension.class)
@DisplayName("AuditService Tests")
class AuditServiceTest {

    @Mock
    private AuditLogRepository auditLogRepository;

    @Mock
    private SecurityContext securityContext;

    @Mock
    private Authentication authentication;

    @InjectMocks
    private AuditService auditService;

    private UUID testPatientId;
    private UUID testUserId;
    private Jwt testJwt;

    @BeforeEach
    void setUp() {
        testPatientId = UUID.randomUUID();
        testUserId = UUID.randomUUID();

        // Create mock JWT
        testJwt = Jwt.withTokenValue("test-token")
                .header("alg", "RS256")
                .claim("sub", testUserId.toString())
                .claim("email", "doctor@hospital.com")
                .build();
    }

    @Nested
    @DisplayName("log() Method Tests")
    class LogMethodTests {

        @Test
        @DisplayName("Should create audit log entry with all fields")
        void shouldCreateAuditLogEntryWithAllFields() {
            // Arrange
            ArgumentCaptor<AuditLog> auditLogCaptor = ArgumentCaptor.forClass(AuditLog.class);
            when(auditLogRepository.save(any(AuditLog.class))).thenAnswer(invocation -> invocation.getArgument(0));

            // Act
            auditService.log(
                    AuditAction.VIEW_PHI,
                    "Patient",
                    testPatientId.toString(),
                    testPatientId,
                    "Viewed patient demographics"
            );

            // Assert - async method, verify save was called
            verify(auditLogRepository, timeout(1000)).save(auditLogCaptor.capture());
            AuditLog savedLog = auditLogCaptor.getValue();

            assertNotNull(savedLog);
            assertEquals(AuditAction.VIEW_PHI, savedLog.getAction());
            assertEquals("Patient", savedLog.getEntityType());
            assertEquals(testPatientId.toString(), savedLog.getEntityId());
            assertEquals(testPatientId, savedLog.getPatientId());
            assertEquals("Viewed patient demographics", savedLog.getDescription());
            assertNotNull(savedLog.getTimestamp());
        }

        @Test
        @DisplayName("Should capture user email from JWT")
        void shouldCaptureUserEmailFromJwt() {
            // Arrange
            SecurityContextHolder.setContext(securityContext);
            when(securityContext.getAuthentication()).thenReturn(authentication);
            when(authentication.getPrincipal()).thenReturn(testJwt);

            ArgumentCaptor<AuditLog> auditLogCaptor = ArgumentCaptor.forClass(AuditLog.class);
            when(auditLogRepository.save(any(AuditLog.class))).thenAnswer(invocation -> invocation.getArgument(0));

            // Act
            auditService.log(
                    AuditAction.CREATE,
                    "ClinicalNote",
                    "note-123",
                    testPatientId,
                    "Created clinical note"
            );

            // Assert
            verify(auditLogRepository, timeout(1000)).save(auditLogCaptor.capture());
            AuditLog savedLog = auditLogCaptor.getValue();
            assertEquals("doctor@hospital.com", savedLog.getUserEmail());

            // Clean up
            SecurityContextHolder.clearContext();
        }

        @Test
        @DisplayName("Should handle missing authentication gracefully")
        void shouldHandleMissingAuthenticationGracefully() {
            // Arrange
            SecurityContextHolder.clearContext();
            when(auditLogRepository.save(any(AuditLog.class))).thenAnswer(invocation -> invocation.getArgument(0));

            // Act - should not throw
            assertDoesNotThrow(() -> auditService.log(
                    AuditAction.VIEW_PHI,
                    "Patient",
                    "123",
                    testPatientId,
                    "View patient"
            ));

            // Assert
            verify(auditLogRepository, timeout(1000)).save(any(AuditLog.class));
        }

        @Test
        @DisplayName("Should handle repository errors gracefully")
        void shouldHandleRepositoryErrorsGracefully() {
            // Arrange
            when(auditLogRepository.save(any(AuditLog.class)))
                    .thenThrow(new RuntimeException("Database error"));

            // Act - should not throw, just log error
            assertDoesNotThrow(() -> auditService.log(
                    AuditAction.VIEW_PHI,
                    "Patient",
                    "123",
                    testPatientId,
                    "View patient"
            ));
        }
    }

    @Nested
    @DisplayName("logPHIAccess() Method Tests")
    class LogPhiAccessMethodTests {

        @Test
        @DisplayName("Should log PHI access with correct action")
        void shouldLogPhiAccessWithCorrectAction() {
            // Arrange
            ArgumentCaptor<AuditLog> auditLogCaptor = ArgumentCaptor.forClass(AuditLog.class);
            when(auditLogRepository.save(any(AuditLog.class))).thenAnswer(invocation -> invocation.getArgument(0));

            // Act
            auditService.logPHIAccess(testUserId, testPatientId, "viewed vitals");

            // Assert
            verify(auditLogRepository, timeout(1000)).save(auditLogCaptor.capture());
            AuditLog savedLog = auditLogCaptor.getValue();

            assertEquals(AuditAction.VIEW_PHI, savedLog.getAction());
            assertEquals("Patient", savedLog.getEntityType());
            assertEquals(testPatientId, savedLog.getPatientId());
            assertTrue(savedLog.getDescription().contains("viewed vitals"));
        }

        @Test
        @DisplayName("Should include action description in PHI access log")
        void shouldIncludeActionDescriptionInPhiAccessLog() {
            // Arrange
            ArgumentCaptor<AuditLog> auditLogCaptor = ArgumentCaptor.forClass(AuditLog.class);
            when(auditLogRepository.save(any(AuditLog.class))).thenAnswer(invocation -> invocation.getArgument(0));

            // Act
            auditService.logPHIAccess(testUserId, testPatientId, "exported medications list");

            // Assert
            verify(auditLogRepository, timeout(1000)).save(auditLogCaptor.capture());
            AuditLog savedLog = auditLogCaptor.getValue();
            assertTrue(savedLog.getDescription().contains("exported medications list"));
        }
    }

    @Nested
    @DisplayName("AuditAction Enum Tests")
    class AuditActionEnumTests {

        @Test
        @DisplayName("All expected audit actions should exist")
        void allExpectedAuditActionsShouldExist() {
            // Assert all HIPAA-required actions exist
            assertNotNull(AuditAction.CREATE);
            assertNotNull(AuditAction.VIEW_PHI);
            // Add more as defined in the AuditLog entity
        }

        @Test
        @DisplayName("Audit actions should be logged for different operations")
        void auditActionsShouldBeLoggedForDifferentOperations() {
            // Arrange
            when(auditLogRepository.save(any(AuditLog.class))).thenAnswer(invocation -> invocation.getArgument(0));

            // Test CREATE action
            auditService.log(AuditAction.CREATE, "ClinicalNote", "note-1", testPatientId, "Created note");
            verify(auditLogRepository, timeout(1000).atLeast(1)).save(any(AuditLog.class));

            // Test VIEW_PHI action
            auditService.log(AuditAction.VIEW_PHI, "Patient", "patient-1", testPatientId, "Viewed patient");
            verify(auditLogRepository, timeout(1000).atLeast(2)).save(any(AuditLog.class));
        }
    }

    @Nested
    @DisplayName("HIPAA Compliance Tests")
    class HipaaComplianceTests {

        @Test
        @DisplayName("Should capture timestamp for all audit logs")
        void shouldCaptureTimestampForAllAuditLogs() {
            // Arrange
            ArgumentCaptor<AuditLog> auditLogCaptor = ArgumentCaptor.forClass(AuditLog.class);
            when(auditLogRepository.save(any(AuditLog.class))).thenAnswer(invocation -> invocation.getArgument(0));

            // Act
            auditService.log(AuditAction.VIEW_PHI, "Patient", "123", testPatientId, "View");

            // Assert
            verify(auditLogRepository, timeout(1000)).save(auditLogCaptor.capture());
            assertNotNull(auditLogCaptor.getValue().getTimestamp());
        }

        @Test
        @DisplayName("Should always include patient ID in audit logs")
        void shouldAlwaysIncludePatientIdInAuditLogs() {
            // Arrange
            ArgumentCaptor<AuditLog> auditLogCaptor = ArgumentCaptor.forClass(AuditLog.class);
            when(auditLogRepository.save(any(AuditLog.class))).thenAnswer(invocation -> invocation.getArgument(0));

            // Act
            auditService.log(AuditAction.VIEW_PHI, "Vitals", "vitals-123", testPatientId, "Viewed vitals");

            // Assert
            verify(auditLogRepository, timeout(1000)).save(auditLogCaptor.capture());
            assertEquals(testPatientId, auditLogCaptor.getValue().getPatientId());
        }

        @Test
        @DisplayName("Should be async to not block main thread")
        void shouldBeAsyncToNotBlockMainThread() {
            // Arrange
            when(auditLogRepository.save(any(AuditLog.class))).thenAnswer(invocation -> {
                Thread.sleep(100); // Simulate slow DB
                return invocation.getArgument(0);
            });

            long startTime = System.currentTimeMillis();

            // Act
            auditService.log(AuditAction.VIEW_PHI, "Patient", "123", testPatientId, "View");

            long endTime = System.currentTimeMillis();

            // Assert - should return immediately (< 50ms) due to async
            assertTrue(endTime - startTime < 50, "log() should be async and return immediately");

            // Wait for async to complete
            verify(auditLogRepository, timeout(1000)).save(any(AuditLog.class));
        }
    }
}
