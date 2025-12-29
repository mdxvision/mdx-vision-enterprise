package com.mdxvision.repository;

import com.mdxvision.entity.User;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;
import java.util.UUID;

@Repository
public interface UserRepository extends JpaRepository<User, UUID> {
    Optional<User> findByEmail(String email);
    Optional<User> findByExternalId(String externalId);
    Optional<User> findByEpicProviderId(String epicProviderId);
    boolean existsByEmail(String email);
}
