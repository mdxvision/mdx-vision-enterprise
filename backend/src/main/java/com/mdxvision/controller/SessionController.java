package com.mdxvision.controller;

import com.mdxvision.dto.SessionDTO;
import com.mdxvision.service.SessionService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.*;

import java.util.UUID;

@RestController
@RequestMapping("/v1/sessions")
@RequiredArgsConstructor
@Tag(name = "Sessions", description = "Real-time recording session management")
public class SessionController {

    private final SessionService sessionService;

    @PostMapping
    @Operation(summary = "Start a new recording session")
    public ResponseEntity<SessionDTO.Response> startSession(
            @AuthenticationPrincipal Jwt jwt,
            @RequestBody SessionDTO.CreateRequest request) {
        
        UUID userId = UUID.fromString(jwt.getClaimAsString("sub"));
        SessionDTO.Response response = sessionService.startSession(userId, request);
        return ResponseEntity.ok(response);
    }

    @PostMapping("/{sessionId}/end")
    @Operation(summary = "End a recording session")
    public ResponseEntity<SessionDTO.Response> endSession(
            @AuthenticationPrincipal Jwt jwt,
            @PathVariable UUID sessionId) {
        
        UUID userId = UUID.fromString(jwt.getClaimAsString("sub"));
        SessionDTO.Response response = sessionService.endSession(sessionId, userId);
        return ResponseEntity.ok(response);
    }

    @GetMapping("/{sessionId}")
    @Operation(summary = "Get session details")
    public ResponseEntity<SessionDTO.Response> getSession(@PathVariable UUID sessionId) {
        SessionDTO.Response response = sessionService.getSession(sessionId);
        return ResponseEntity.ok(response);
    }

    @PostMapping("/{sessionId}/pause")
    @Operation(summary = "Pause a session")
    public ResponseEntity<SessionDTO.Response> pauseSession(
            @AuthenticationPrincipal Jwt jwt,
            @PathVariable UUID sessionId) {
        // Implementation for pause
        return ResponseEntity.ok().build();
    }

    @PostMapping("/{sessionId}/resume")
    @Operation(summary = "Resume a paused session")
    public ResponseEntity<SessionDTO.Response> resumeSession(
            @AuthenticationPrincipal Jwt jwt,
            @PathVariable UUID sessionId) {
        // Implementation for resume
        return ResponseEntity.ok().build();
    }
}
