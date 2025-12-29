-- MDx Vision Enterprise Database Schema
-- Version: 1.0.0
-- HIPAA Compliant Design

-- Users Table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL UNIQUE,
    external_id VARCHAR(255) UNIQUE,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    role VARCHAR(50) NOT NULL,
    vertical VARCHAR(50) NOT NULL,
    organization_id VARCHAR(100),
    npi_number VARCHAR(20),
    specialty VARCHAR(100),
    is_active BOOLEAN DEFAULT true,
    epic_provider_id VARCHAR(100),
    epic_user_id VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE,
    created_by VARCHAR(255),
    updated_by VARCHAR(255),
    version BIGINT DEFAULT 0
);

-- Patients Table (PHI - Protected Health Information)
CREATE TABLE patients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fhir_id VARCHAR(100) UNIQUE,
    epic_patient_id VARCHAR(100),
    mrn VARCHAR(50),
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    date_of_birth DATE,
    gender VARCHAR(20),
    phone VARCHAR(30),
    email VARCHAR(255),
    address_line1 VARCHAR(255),
    address_line2 VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(50),
    postal_code VARCHAR(20),
    country VARCHAR(50),
    preferred_language VARCHAR(10) DEFAULT 'en',
    organization_id VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE,
    created_by VARCHAR(255),
    updated_by VARCHAR(255),
    version BIGINT DEFAULT 0
);

-- Encounters Table
CREATE TABLE encounters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fhir_id VARCHAR(100) UNIQUE,
    epic_encounter_id VARCHAR(100),
    patient_id UUID NOT NULL REFERENCES patients(id),
    provider_id UUID NOT NULL REFERENCES users(id),
    status VARCHAR(30) NOT NULL,
    encounter_type VARCHAR(30) NOT NULL,
    start_time TIMESTAMP WITH TIME ZONE,
    end_time TIMESTAMP WITH TIME ZONE,
    location VARCHAR(255),
    chief_complaint TEXT,
    reason_for_visit TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE,
    created_by VARCHAR(255),
    updated_by VARCHAR(255),
    version BIGINT DEFAULT 0
);

-- Sessions Table (Recording Sessions)
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    encounter_id UUID REFERENCES encounters(id),
    status VARCHAR(30) NOT NULL,
    device_type VARCHAR(50),
    device_id VARCHAR(100),
    start_time TIMESTAMP WITH TIME ZONE,
    end_time TIMESTAMP WITH TIME ZONE,
    audio_channel_id VARCHAR(100),
    transcription_enabled BOOLEAN DEFAULT true,
    ai_suggestions_enabled BOOLEAN DEFAULT true,
    language_code VARCHAR(10) DEFAULT 'en-US',
    translation_target_language VARCHAR(10),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE,
    created_by VARCHAR(255),
    updated_by VARCHAR(255),
    version BIGINT DEFAULT 0
);

-- Transcriptions Table
CREATE TABLE transcriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    encounter_id UUID NOT NULL REFERENCES encounters(id),
    session_id UUID REFERENCES sessions(id),
    speaker_label VARCHAR(50),
    original_text TEXT NOT NULL,
    translated_text TEXT,
    source_language VARCHAR(10),
    target_language VARCHAR(10),
    confidence_score DECIMAL(5,4),
    start_timestamp TIMESTAMP WITH TIME ZONE,
    end_timestamp TIMESTAMP WITH TIME ZONE,
    audio_offset_ms BIGINT,
    duration_ms BIGINT,
    processing_status VARCHAR(30),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE,
    created_by VARCHAR(255),
    updated_by VARCHAR(255),
    version BIGINT DEFAULT 0
);

-- Clinical Notes Table
CREATE TABLE clinical_notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fhir_document_reference_id VARCHAR(100),
    encounter_id UUID NOT NULL REFERENCES encounters(id),
    author_id UUID NOT NULL REFERENCES users(id),
    note_type VARCHAR(30) NOT NULL,
    status VARCHAR(30) NOT NULL,
    subjective TEXT,
    objective TEXT,
    assessment TEXT,
    plan TEXT,
    full_content TEXT,
    ai_summary TEXT,
    icd10_codes TEXT,
    cpt_codes TEXT,
    signed_at TIMESTAMP WITH TIME ZONE,
    pushed_to_ehr_at TIMESTAMP WITH TIME ZONE,
    ehr_document_id VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE,
    created_by VARCHAR(255),
    updated_by VARCHAR(255),
    version BIGINT DEFAULT 0
);

-- Drug Interaction Alerts Table
CREATE TABLE drug_interaction_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clinical_note_id UUID REFERENCES clinical_notes(id),
    encounter_id UUID REFERENCES encounters(id),
    drug_1_name VARCHAR(255) NOT NULL,
    drug_1_rxnorm_code VARCHAR(50),
    drug_2_name VARCHAR(255) NOT NULL,
    drug_2_rxnorm_code VARCHAR(50),
    severity VARCHAR(30) NOT NULL,
    description TEXT,
    clinical_effect TEXT,
    recommendation TEXT,
    acknowledged BOOLEAN DEFAULT false,
    acknowledged_by VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE,
    created_by VARCHAR(255),
    updated_by VARCHAR(255),
    version BIGINT DEFAULT 0
);

-- Audit Logs Table (HIPAA Compliance)
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,
    user_email VARCHAR(255),
    action VARCHAR(50) NOT NULL,
    entity_type VARCHAR(100) NOT NULL,
    entity_id VARCHAR(100),
    patient_id UUID,
    description TEXT,
    old_value TEXT,
    new_value TEXT,
    ip_address VARCHAR(50),
    user_agent VARCHAR(500),
    device_type VARCHAR(50),
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    organization_id VARCHAR(100)
);

-- Indexes for Performance
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_external_id ON users(external_id);
CREATE INDEX idx_users_organization ON users(organization_id);

CREATE INDEX idx_patients_fhir_id ON patients(fhir_id);
CREATE INDEX idx_patients_epic_id ON patients(epic_patient_id);
CREATE INDEX idx_patients_mrn ON patients(mrn);
CREATE INDEX idx_patients_name ON patients(last_name, first_name);
CREATE INDEX idx_patients_organization ON patients(organization_id);

CREATE INDEX idx_encounters_patient ON encounters(patient_id);
CREATE INDEX idx_encounters_provider ON encounters(provider_id);
CREATE INDEX idx_encounters_status ON encounters(status);
CREATE INDEX idx_encounters_dates ON encounters(start_time, end_time);

CREATE INDEX idx_sessions_user ON sessions(user_id);
CREATE INDEX idx_sessions_encounter ON sessions(encounter_id);
CREATE INDEX idx_sessions_status ON sessions(status);
CREATE INDEX idx_sessions_audio_channel ON sessions(audio_channel_id);

CREATE INDEX idx_transcriptions_encounter ON transcriptions(encounter_id);
CREATE INDEX idx_transcriptions_session ON transcriptions(session_id);
CREATE INDEX idx_transcriptions_timestamp ON transcriptions(start_timestamp);

CREATE INDEX idx_clinical_notes_encounter ON clinical_notes(encounter_id);
CREATE INDEX idx_clinical_notes_author ON clinical_notes(author_id);
CREATE INDEX idx_clinical_notes_status ON clinical_notes(status);

CREATE INDEX idx_audit_user ON audit_logs(user_id);
CREATE INDEX idx_audit_patient ON audit_logs(patient_id);
CREATE INDEX idx_audit_timestamp ON audit_logs(timestamp);
CREATE INDEX idx_audit_action ON audit_logs(action);
CREATE INDEX idx_audit_entity ON audit_logs(entity_type, entity_id);
