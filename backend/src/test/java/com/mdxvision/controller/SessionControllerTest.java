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
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.core.MethodParameter;
import org.springframework.http.MediaType;
import org.springframework.http.converter.json.MappingJackson2HttpMessageConverter;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.web.bind.support.WebDataBinderFactory;
import org.springframework.web.context.request.NativeWebRequest;
import org.springframework.web.method.support.HandlerMethodArgumentResolver;
import org.springframework.web.method.support.ModelAndViewContainer;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import com.mdxvision.dto.SessionDTO;
import com.mdxvision.entity.Session;
import com.mdxvision.service.SessionService;

/**
 * Controller tests for SessionController
 *
 * Uses standalone MockMvc setup to avoid Spring Security context issues.
 * Tests REST API endpoints for recording session management.
 */
@ExtendWith(MockitoExtension.class)
@DisplayName("SessionController Tests")
class SessionControllerTest {

    private MockMvc mockMvc;

    private ObjectMapper objectMapper;

    @Mock
    private SessionService sessionService;

    @InjectMocks
    private SessionController sessionController;

    private UUID testUserId;
    private UUID testSessionId;
    private Jwt mockJwt;

    @BeforeEach
    void setUp() {
        testUserId = UUID.randomUUID();
        testSessionId = UUID.randomUUID();

        // Create mock JWT
        mockJwt = Jwt.withTokenValue("test-token")
                .header("alg", "RS256")
                .claim("sub", testUserId.toString())
                .build();

        // Configure ObjectMapper with Java 8 time support
        objectMapper = new ObjectMapper();
        objectMapper.registerModule(new JavaTimeModule());

        // Setup standalone MockMvc with custom argument resolver for JWT
        mockMvc = MockMvcBuilders.standaloneSetup(sessionController)
                .setCustomArgumentResolvers(new JwtArgumentResolver(mockJwt))
                .setMessageConverters(new MappingJackson2HttpMessageConverter(objectMapper))
                .build();
    }

    /**
     * Custom argument resolver that injects a mock JWT for @AuthenticationPrincipal
     */
    private static class JwtArgumentResolver implements HandlerMethodArgumentResolver {
        private final Jwt jwt;

        JwtArgumentResolver(Jwt jwt) {
            this.jwt = jwt;
        }

        @Override
        public boolean supportsParameter(MethodParameter parameter) {
            return parameter.getParameterType().equals(Jwt.class);
        }

        @Override
        public Object resolveArgument(MethodParameter parameter, ModelAndViewContainer mavContainer,
                NativeWebRequest webRequest, WebDataBinderFactory binderFactory) {
            return jwt;
        }
    }

    @Nested
    @DisplayName("POST /v1/sessions - Start Session")
    class StartSessionTests {

        @Test
        @DisplayName("Should start a new session successfully")
        void shouldStartNewSessionSuccessfully() throws Exception {
            // Arrange
            SessionDTO.CreateRequest request = SessionDTO.CreateRequest.builder()
                    .encounterId(UUID.randomUUID())
                    .deviceType("AR_GLASSES")
                    .build();

            SessionDTO.Response response = SessionDTO.Response.builder()
                    .id(testSessionId)
                    .status(Session.SessionStatus.ACTIVE)
                    .startTime(Instant.now())
                    .build();

            when(sessionService.startSession(any(), any(SessionDTO.CreateRequest.class)))
                    .thenReturn(response);

            // Act & Assert
            mockMvc.perform(post("/v1/sessions")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content(objectMapper.writeValueAsString(request)))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$.id").exists())
                    .andExpect(jsonPath("$.status").value("ACTIVE"));
        }

        @Test
        @DisplayName("Should create session with all request fields")
        void shouldCreateSessionWithAllRequestFields() throws Exception {
            // Arrange
            UUID encounterId = UUID.randomUUID();
            SessionDTO.CreateRequest request = SessionDTO.CreateRequest.builder()
                    .encounterId(encounterId)
                    .deviceType("AR_GLASSES")
                    .deviceId("device-123")
                    .transcriptionEnabled(true)
                    .aiSuggestionsEnabled(true)
                    .languageCode("en-US")
                    .translationTargetLanguage("es")
                    .build();

            SessionDTO.Response response = SessionDTO.Response.builder()
                    .id(testSessionId)
                    .encounterId(encounterId)
                    .status(Session.SessionStatus.ACTIVE)
                    .startTime(Instant.now())
                    .deviceType("AR_GLASSES")
                    .transcriptionEnabled(true)
                    .aiSuggestionsEnabled(true)
                    .languageCode("en-US")
                    .translationTargetLanguage("es")
                    .build();

            when(sessionService.startSession(any(), any(SessionDTO.CreateRequest.class)))
                    .thenReturn(response);

            // Act & Assert
            mockMvc.perform(post("/v1/sessions")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content(objectMapper.writeValueAsString(request)))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$.deviceType").value("AR_GLASSES"))
                    .andExpect(jsonPath("$.transcriptionEnabled").value(true));
        }
    }

    @Nested
    @DisplayName("POST /v1/sessions/{sessionId}/end - End Session")
    class EndSessionTests {

        @Test
        @DisplayName("Should end an active session")
        void shouldEndActiveSession() throws Exception {
            // Arrange
            SessionDTO.Response response = SessionDTO.Response.builder()
                    .id(testSessionId)
                    .status(Session.SessionStatus.COMPLETED)
                    .startTime(Instant.now().minusSeconds(300))
                    .endTime(Instant.now())
                    .build();

            when(sessionService.endSession(eq(testSessionId), any()))
                    .thenReturn(response);

            // Act & Assert
            mockMvc.perform(post("/v1/sessions/{sessionId}/end", testSessionId))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$.status").value("COMPLETED"))
                    .andExpect(jsonPath("$.endTime").exists());
        }

        @Test
        @DisplayName("Should include session duration when ended")
        void shouldIncludeSessionDurationWhenEnded() throws Exception {
            // Arrange
            Instant startTime = Instant.now().minusSeconds(600);
            Instant endTime = Instant.now();

            SessionDTO.Response response = SessionDTO.Response.builder()
                    .id(testSessionId)
                    .status(Session.SessionStatus.COMPLETED)
                    .startTime(startTime)
                    .endTime(endTime)
                    .build();

            when(sessionService.endSession(eq(testSessionId), any()))
                    .thenReturn(response);

            // Act & Assert
            mockMvc.perform(post("/v1/sessions/{sessionId}/end", testSessionId))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$.startTime").exists())
                    .andExpect(jsonPath("$.endTime").exists());
        }
    }

    @Nested
    @DisplayName("GET /v1/sessions/{sessionId} - Get Session")
    class GetSessionTests {

        @Test
        @DisplayName("Should get session details")
        void shouldGetSessionDetails() throws Exception {
            // Arrange
            SessionDTO.Response response = SessionDTO.Response.builder()
                    .id(testSessionId)
                    .status(Session.SessionStatus.ACTIVE)
                    .startTime(Instant.now())
                    .deviceType("AR_GLASSES")
                    .transcriptionEnabled(true)
                    .build();

            when(sessionService.getSession(testSessionId)).thenReturn(response);

            // Act & Assert
            mockMvc.perform(get("/v1/sessions/{sessionId}", testSessionId))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$.id").value(testSessionId.toString()))
                    .andExpect(jsonPath("$.status").value("ACTIVE"));
        }

        @Test
        @DisplayName("Should return completed session details")
        void shouldReturnCompletedSessionDetails() throws Exception {
            // Arrange
            SessionDTO.Response response = SessionDTO.Response.builder()
                    .id(testSessionId)
                    .status(Session.SessionStatus.COMPLETED)
                    .startTime(Instant.now().minusSeconds(600))
                    .endTime(Instant.now())
                    .build();

            when(sessionService.getSession(testSessionId)).thenReturn(response);

            // Act & Assert
            mockMvc.perform(get("/v1/sessions/{sessionId}", testSessionId))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$.status").value("COMPLETED"));
        }
    }

    @Nested
    @DisplayName("POST /v1/sessions/{sessionId}/pause - Pause Session")
    class PauseSessionTests {

        @Test
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
        @DisplayName("Should resume a paused session")
        void shouldResumePausedSession() throws Exception {
            // Act & Assert
            mockMvc.perform(post("/v1/sessions/{sessionId}/resume", testSessionId))
                    .andExpect(status().isOk());
        }
    }

    @Nested
    @DisplayName("Session State Tests")
    class SessionStateTests {

        @Test
        @DisplayName("Should verify session service is called")
        void shouldVerifySessionServiceIsCalled() throws Exception {
            // Arrange
            SessionDTO.CreateRequest request = SessionDTO.CreateRequest.builder()
                    .encounterId(UUID.randomUUID())
                    .deviceType("AR_GLASSES")
                    .build();

            SessionDTO.Response response = SessionDTO.Response.builder()
                    .id(testSessionId)
                    .status(Session.SessionStatus.ACTIVE)
                    .startTime(Instant.now())
                    .build();

            when(sessionService.startSession(any(), any(SessionDTO.CreateRequest.class)))
                    .thenReturn(response);

            // Act
            mockMvc.perform(post("/v1/sessions")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content(objectMapper.writeValueAsString(request)))
                    .andExpect(status().isOk());

            // Assert
            verify(sessionService).startSession(any(), any(SessionDTO.CreateRequest.class));
        }

        @Test
        @DisplayName("Should handle session status enum correctly")
        void shouldHandleSessionStatusEnumCorrectly() throws Exception {
            // Test each status value
            for (Session.SessionStatus status : Session.SessionStatus.values()) {
                SessionDTO.Response response = SessionDTO.Response.builder()
                        .id(testSessionId)
                        .status(status)
                        .startTime(Instant.now())
                        .build();

                when(sessionService.getSession(testSessionId)).thenReturn(response);

                mockMvc.perform(get("/v1/sessions/{sessionId}", testSessionId))
                        .andExpect(status().isOk())
                        .andExpect(jsonPath("$.status").value(status.name()));
            }
        }
    }
}
