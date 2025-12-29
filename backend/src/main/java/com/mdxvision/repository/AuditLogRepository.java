package com.mdxvision.repository;

import com.mdxvision.entity.AuditLog;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.time.Instant;
import java.util.UUID;

@Repository
public interface AuditLogRepository extends JpaRepository<AuditLog, UUID> {
    Page<AuditLog> findByUserId(UUID userId, Pageable pageable);
    Page<AuditLog> findByPatientId(UUID patientId, Pageable pageable);
    Page<AuditLog> findByTimestampBetween(Instant start, Instant end, Pageable pageable);
    Page<AuditLog> findByAction(AuditLog.AuditAction action, Pageable pageable);
}
