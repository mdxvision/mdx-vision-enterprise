package com.mdxvision.controller;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

import java.time.Instant;
import java.util.UUID;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.http.MediaType;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.jwt.JwtDecoder;
import org.springframework.security.test.context.support.WithMockUser;
import org.springframework.test.web.servlet.MockMvc;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.mdxvision.dto.SessionDTO;
import com.mdxvision.service.SessionService;

/**
 * Controller tests for SessionController
 *
 * Tests REST API endpoints for recording session management.
 * Uses Spring Security test utilities for JWT authentication testing.
 */
@WebMvcTest(SessionController.class)
@DisplayName("SessionController Tests")
class SessionControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @MockBean
    private SessionService sessionService;

    @MockBean
    private JwtDecoder jwtDecoder;

    private UUID testUserId;
    private UUID testSessionId;
    private Jwt testJwt;

    @BeforeEach
    void setUp() {
        testUserId = UUID.randomUUID();
        testSessionId = UUID.randomUUID();

        // Create mock JWT
        testJwt = Jwt.withTokenValue("test-token")
                .header("alg", "RS256")
                .claim("sub", testUserId.toString())
                .claim("email", "doctor@hospital.com")
                .build();
    }

    @Nested
    @DisplayName("POST /v1/sessions - Start Session")
    class StartSessionTests {

        @Test
        @WithMockUser
        @DisplayName("Should start a new session successfully")
        void shouldStartNewSessionSuccessfully() throws Exception {
            // Arrange
            SessionDTO.CreateRequest request = new SessionDTO.CreateRequest();
            request.setPatientId(UUID.randomUUID());
            request.setEncounterType("OUTPATIENT");

            SessionDTO.Response response = new SessionDTO.Response();
            response.setSessionId(testSessionId);
            response.setStatus("ACTIVE");
            response.setStartedAt(Instant.now());

            when(sessionService.startSession(any(UUID.class), any(SessionDTO.CreateRequest.class)))
                    .thenReturn(response);

            // Act & Assert
            mockMvc.perform(post("/v1/sessions")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content(objectMapper.writeValueAsString(request)))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$.sessionId").exists())
                    .andExpect(jsonPath("$.status").value("ACTIVE"));
        }

        @Test
        @DisplayName("Should return 401 when not authenticated")
        void shouldReturn401WhenNotAuthenticated() throws Exception {
            // Arrange
            SessionDTO.CreateRequest request = new SessionDTO.CreateRequest();

            // Act & Assert
            mockMvc.perform(post("/v1/sessions")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content(objectMapper.writeValueAsString(request)))
                    .andExpect(status().isUnauthorized());
        }
    }

    @Nested
    @DisplayName("POST /v1/sessions/{sessionId}/end - End Session")
    class EndSessionTests {

        @Test
        @WithMockUser
        @DisplayName("Should end an active session")
        void shouldEndActiveSession() throws Exception {
            // Arrange
            SessionDTO.Response response = new SessionDTO.Response();
            response.setSessionId(testSessionId);
            response.setStatus("COMPLETED");
            response.setEndedAt(Instant.now());

            when(sessionService.endSession(eq(testSessionId), any(UUID.class)))
                    .thenReturn(response);

            // Act & Assert
            mockMvc.perform(post("/v1/sessions/{sessionId}/end", testSessionId))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$.status").value("COMPLETED"));
        }

        @Test
        @DisplayName("Should return 401 when ending session without auth")
        void shouldReturn401WhenEndingSessionWithoutAuth() throws Exception {
            // Act & Assert
            mockMvc.perform(post("/v1/sessions/{sessionId}/end", testSessionId))
                    .andExpect(status().isUnauthorized());
        }
    }

    @Nested
    @DisplayName("GET /v1/sessions/{sessionId} - Get Session")
    class GetSessionTests {

        @Test
        @WithMockUser
        @DisplayName("Should get session details")
        void shouldGetSessionDetails() throws Exception {
            // Arrange
            SessionDTO.Response response = new SessionDTO.Response();
            response.setSessionId(testSessionId);
            response.setStatus("ACTIVE");
            response.setStartedAt(Instant.now());

            when(sessionService.getSession(testSessionId)).thenReturn(response);

            // Act & Assert
            mockMvc.perform(get("/v1/sessions/{sessionId}", testSessionId))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$.sessionId").value(testSessionId.toString()))
                    .andExpect(jsonPath("$.status").value("ACTIVE"));
        }
    }

    @Nested
    @DisplayName("POST /v1/sessions/{sessionId}/pause - Pause Session")
    class PauseSessionTests {

        @Test
        @WithMockUser
        @DisplayName("Should pause an active session")
        void shouldPauseActiveSession() throws Exception {
            // Act & Assert
            mockMvc.perform(post("/v1/sessions/{sessionId}/pause", testSessionId))
                    .andExpect(status().isOk());
        }
    }

    @Nested
    @DisplayName("POST /v1/sessions/{sessionId}/resume - Resume Session")
    class ResumeSessionTests {

        @Test
        @WithMockUser
        @DisplayName("Should resume a paused session")
        void shouldResumePausedSession() throws Exception {
            // Act & Assert
            mockMvc.perform(post("/v1/sessions/{sessionId}/resume", testSessionId))
                    .andExpect(status().isOk());
        }
    }

    @Nested
    @DisplayName("Security Tests")
    class SecurityTests {

        @Test
        @DisplayName("All endpoints should require authentication")
        void allEndpointsShouldRequireAuthentication() throws Exception {
            // Test each endpoint without authentication
            mockMvc.perform(post("/v1/sessions")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content("{}"))
                    .andExpect(status().isUnauthorized());

            mockMvc.perform(get("/v1/sessions/{sessionId}", testSessionId))
                    .andExpect(status().isUnauthorized());

            mockMvc.perform(post("/v1/sessions/{sessionId}/end", testSessionId))
                    .andExpect(status().isUnauthorized());

            mockMvc.perform(post("/v1/sessions/{sessionId}/pause", testSessionId))
                    .andExpect(status().isUnauthorized());

            mockMvc.perform(post("/v1/sessions/{sessionId}/resume", testSessionId))
                    .andExpect(status().isUnauthorized());
        }
    }
}
