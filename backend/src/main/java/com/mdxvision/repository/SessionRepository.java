package com.mdxvision.repository;

import com.mdxvision.entity.Session;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public interface SessionRepository extends JpaRepository<Session, UUID> {
    List<Session> findByUserIdAndStatus(UUID userId, Session.SessionStatus status);
    Optional<Session> findByEncounterId(UUID encounterId);
    Optional<Session> findByAudioChannelId(String audioChannelId);
}
