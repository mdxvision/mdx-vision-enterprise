package com.mdxvision.repository;

import com.mdxvision.entity.Encounter;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public interface EncounterRepository extends JpaRepository<Encounter, UUID> {
    Optional<Encounter> findByFhirId(String fhirId);
    Optional<Encounter> findByEpicEncounterId(String epicEncounterId);
    
    Page<Encounter> findByPatientId(UUID patientId, Pageable pageable);
    Page<Encounter> findByProviderId(UUID providerId, Pageable pageable);
    
    @Query("SELECT e FROM Encounter e WHERE e.provider.id = :providerId AND e.status = :status")
    List<Encounter> findByProviderIdAndStatus(
        @Param("providerId") UUID providerId, 
        @Param("status") Encounter.EncounterStatus status
    );
    
    @Query("SELECT e FROM Encounter e WHERE e.startTime BETWEEN :start AND :end")
    Page<Encounter> findByDateRange(
        @Param("start") Instant start, 
        @Param("end") Instant end, 
        Pageable pageable
    );
}
