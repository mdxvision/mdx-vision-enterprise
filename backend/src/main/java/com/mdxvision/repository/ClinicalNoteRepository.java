package com.mdxvision.repository;

import com.mdxvision.entity.ClinicalNote;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public interface ClinicalNoteRepository extends JpaRepository<ClinicalNote, UUID> {
    List<ClinicalNote> findByEncounterId(UUID encounterId);
    Page<ClinicalNote> findByAuthorId(UUID authorId, Pageable pageable);
    Optional<ClinicalNote> findByFhirDocumentReferenceId(String fhirId);
    List<ClinicalNote> findByEncounterIdAndStatus(UUID encounterId, ClinicalNote.NoteStatus status);
}
