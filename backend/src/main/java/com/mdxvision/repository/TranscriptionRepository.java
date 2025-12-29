package com.mdxvision.repository;

import com.mdxvision.entity.Transcription;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.UUID;

@Repository
public interface TranscriptionRepository extends JpaRepository<Transcription, UUID> {
    List<Transcription> findByEncounterIdOrderByStartTimestampAsc(UUID encounterId);
    Page<Transcription> findBySessionId(UUID sessionId, Pageable pageable);
    
    @Query("SELECT t FROM Transcription t WHERE t.encounter.id = :encounterId ORDER BY t.startTimestamp")
    List<Transcription> findAllForEncounter(@Param("encounterId") UUID encounterId);
}
