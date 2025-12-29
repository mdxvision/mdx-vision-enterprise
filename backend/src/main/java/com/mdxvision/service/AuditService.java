package com.mdxvision.service;

import com.mdxvision.entity.AuditLog;
import com.mdxvision.repository.AuditLogRepository;
import jakarta.servlet.http.HttpServletRequest;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Async;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.stereotype.Service;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

import java.time.Instant;
import java.util.UUID;

@Service
@RequiredArgsConstructor
@Slf4j
public class AuditService {

    private final AuditLogRepository auditLogRepository;

    @Async
    public void log(AuditLog.AuditAction action, String entityType, String entityId, 
                    UUID patientId, String description) {
        try {
            AuditLog.AuditLogBuilder builder = AuditLog.builder()
                .action(action)
                .entityType(entityType)
                .entityId(entityId)
                .patientId(patientId)
                .description(description)
                .timestamp(Instant.now());

            // Get current user from security context
            Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
            if (authentication != null && authentication.getPrincipal() instanceof Jwt jwt) {
                builder.userEmail(jwt.getClaimAsString("email"));
                String sub = jwt.getSubject();
                // Parse user ID from subject if available
            }

            // Get request details
            ServletRequestAttributes attrs = 
                (ServletRequestAttributes) RequestContextHolder.getRequestAttributes();
            if (attrs != null) {
                HttpServletRequest request = attrs.getRequest();
                builder.ipAddress(getClientIpAddress(request));
                builder.userAgent(request.getHeader("User-Agent"));
            }

            auditLogRepository.save(builder.build());
            
        } catch (Exception e) {
            log.error("Failed to create audit log: {}", e.getMessage(), e);
        }
    }

    public void logPHIAccess(UUID userId, UUID patientId, String action) {
        log(AuditLog.AuditAction.VIEW_PHI, "Patient", patientId.toString(), patientId,
            "PHI accessed: " + action);
    }

    private String getClientIpAddress(HttpServletRequest request) {
        String xForwardedFor = request.getHeader("X-Forwarded-For");
        if (xForwardedFor != null && !xForwardedFor.isEmpty()) {
            return xForwardedFor.split(",")[0].trim();
        }
        return request.getRemoteAddr();
    }
}
