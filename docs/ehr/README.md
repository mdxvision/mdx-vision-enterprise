# EHR Integration Documentation

This directory contains all documentation related to EHR (Electronic Health Record) integration for MDx Vision.

## Quick Links

### Getting Started
- **[EHR_ACCESS_GUIDE.md](EHR_ACCESS_GUIDE.md)** - Start here! Complete guide to registering and connecting to 29 EHR platforms via FHIR

### Implementation Status
- **[EHR_IMPLEMENTATIONS.md](EHR_IMPLEMENTATIONS.md)** - Current status of live integrations (Cerner ✅, Epic ✅, Veradigm pending)

### Research & Strategy
- **[EHR_AGGREGATOR_PLATFORMS.md](EHR_AGGREGATOR_PLATFORMS.md)** - Aggregator platforms (Particle Health, Redox, Health Gorilla) for multi-EHR access
- **[EHR_AMBULATORY_RESEARCH.md](EHR_AMBULATORY_RESEARCH.md)** - Market research on ambulatory EHR systems
- **[INTERNATIONAL_EHR_EXPANSION.md](INTERNATIONAL_EHR_EXPANSION.md)** - International EHR platforms for global expansion

## Current Status

### Live Integrations ✅
- **Cerner/Oracle Health** - Production ready (Client ID: `0fab9b20-adc8-4940-bbf6-82034d1d39ab`)
- **Epic** - Production ready (OAuth credentials obtained)

### Pending Credentials
- **Veradigm** - Awaiting OAuth approval

### Planned Integrations
See EHR_ACCESS_GUIDE.md for full list of 29 supported platforms.

## Key Technologies

- **FHIR R4** - All integrations use HL7 FHIR Release 4
- **OAuth 2.0 / SMART on FHIR** - Authentication standard
- **Python FastAPI** - EHR proxy service (port 8002)

## Resources

- **FHIR Specification**: https://www.hl7.org/fhir/
- **SMART on FHIR**: https://docs.smarthealthit.org/
- **Test Patient**: Cerner sandbox patient ID `12724066` (SMARTS SR., NANCYS II)

## Quick Start

1. Read [EHR_ACCESS_GUIDE.md](EHR_ACCESS_GUIDE.md) to understand FHIR and registration process
2. Check [EHR_IMPLEMENTATIONS.md](EHR_IMPLEMENTATIONS.md) for current integration status
3. Use test credentials in `ehr-proxy/.env` for local development
4. See [SETUP.md](../development/SETUP.md) for running the EHR proxy service

## Support

For EHR integration issues:
1. Check [SETUP.md - Common Issues](../development/SETUP.md#common-issues)
2. Review FHIR error messages in EHR proxy logs
3. Verify OAuth tokens in `.ehr_tokens.json`
