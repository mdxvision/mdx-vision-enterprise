package com.mdxvision.repository;

import com.mdxvision.entity.Patient;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.Optional;
import java.util.UUID;

@Repository
public interface PatientRepository extends JpaRepository<Patient, UUID> {
    Optional<Patient> findByFhirId(String fhirId);
    Optional<Patient> findByEpicPatientId(String epicPatientId);
    Optional<Patient> findByMrn(String mrn);
    
    @Query("SELECT p FROM Patient p WHERE " +
           "LOWER(p.firstName) LIKE LOWER(CONCAT('%', :search, '%')) OR " +
           "LOWER(p.lastName) LIKE LOWER(CONCAT('%', :search, '%')) OR " +
           "p.mrn LIKE CONCAT('%', :search, '%')")
    Page<Patient> searchPatients(@Param("search") String search, Pageable pageable);
    
    Page<Patient> findByOrganizationId(String organizationId, Pageable pageable);
}
