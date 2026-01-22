# CLAUDE.md - MDx Vision Development Context

> **Quick Reference:** This file provides essential context for Claude Code. For detailed information, see the linked documentation in `docs/`.

## Project Overview

MDx Vision is an **AR smart glasses platform for healthcare documentation**. It implements US Patent 15/237,980 - voice-activated AR glasses that connect to EHR systems via FHIR.

**Core Capabilities:** Voice-activated patient lookup, real-time transcription with RNNoise, AI-powered SOAP notes with RAG, Ambient Clinical Intelligence, health equity features, Minerva AI assistant.

## Project Structure

```
/backend                    # Java Spring Boot (legacy, being replaced)
/ehr-proxy                  # Python FastAPI (port 8002) - PRIMARY BACKEND
/mobile/android             # Kotlin app for Vuzix Blade 2
/web                        # Next.js 14 dashboard (port 5173)
/docs                       # All documentation
  ├── development/          # Technical docs (start here)
  ├── ehr/                  # EHR integration guides
  ├── clinical/             # Clinical research
  ├── business/             # Strategy & pricing
  └── planning/             # Roadmaps & session logs
```

## Essential Documentation

### For Development Tasks
- **[SETUP.md](docs/development/SETUP.md)** - Development environment, commands, troubleshooting
- **[ARCHITECTURE.md](docs/development/ARCHITECTURE.md)** - System design, tech stack, data flows
- **[API_REFERENCE.md](docs/development/API_REFERENCE.md)** - All API endpoints and test data
- **[FEATURES.md](docs/development/FEATURES.md)** - Complete feature checklist (98 features)
- **[TESTING.md](docs/development/TESTING.md)** - Testing strategy (2,879 automated tests)

### For Specific Domains
- **[VOICE_COMMANDS.md](docs/development/VOICE_COMMANDS.md)** - All voice commands
- **[MINERVA.md](docs/development/MINERVA.md)** - Minerva AI assistant implementation
- **[EHR_ACCESS_GUIDE.md](docs/ehr/EHR_ACCESS_GUIDE.md)** - Connect to 29 EHR platforms
- **[CONVERSATIONS.md](docs/planning/CONVERSATIONS.md)** - Session history & decisions

## Quick Start

### Run EHR Proxy (Primary Backend)
```bash
cd ehr-proxy
ASSEMBLYAI_API_KEY=your_key python main.py  # Port 8002
```

### Run Web Dashboard
```bash
cd web
npm run dev  # Port 5173
```

### Build Android App
```bash
cd mobile/android
export JAVA_HOME=/opt/homebrew/opt/openjdk@17
./gradlew assembleDebug
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

**Troubleshooting?** See [SETUP.md](docs/development/SETUP.md#common-issues)

## Current Status

### What's Working
- ✅ **98 features implemented** (SOAP notes, transcription, health equity, billing, security)
- ✅ **Cerner/Oracle EHR** live integration (client ID: `0fab9b20-adc8-4940-bbf6-82034d1d39ab`)
- ✅ **Minerva AI** Phase 1-3 complete (chat, wake word, proactive alerts)
- ✅ **2,879 automated tests** at 99% pass rate

### Current Focus
- **Minerva Phase 4-6:** Reasoning modes, voice actions, personalization
- **Epic/Veradigm:** EHR integration pending credentials
- See [MINERVA.md](docs/development/MINERVA.md) for detailed roadmap

## Test Patient Data

**Cerner Sandbox Patient:**
- ID: `12724066`
- Name: SMARTS SR., NANCYS II
- DOB: 1990-09-15

More test data in [API_REFERENCE.md](docs/development/API_REFERENCE.md#test-data)

## Key Technologies

- **Mobile:** Kotlin, Android 11, Vuzix SDK 2.9.0
- **Backend:** Python 3.11+, FastAPI, ChromaDB, RNNoise
- **AI:** Claude API (Anthropic), AssemblyAI/Deepgram
- **Web:** Next.js 14, TypeScript, Tailwind CSS
- **FHIR:** R4 (Patient, Observation, AllergyIntolerance, etc.)

See [ARCHITECTURE.md](docs/development/ARCHITECTURE.md) for details

## Development Guidelines

### Making Changes
1. **Read existing code first** - Never propose changes to unread code
2. **Use TodoWrite** for multi-step tasks to track progress
3. **Avoid over-engineering** - Only implement what's requested
4. **Security first** - No XSS, SQL injection, or OWASP vulnerabilities
5. **Test coverage** - Update tests when changing functionality

### File Organization
- Android: `mobile/android/app/src/main/java/com/mdxvision/`
- Python: `ehr-proxy/` (main.py, transcription.py, rag_knowledge.py)
- Web: `web/src/app/dashboard/`
- Tests: `*/tests/` or `*/src/test/`

### Testing
```bash
cd ehr-proxy && pytest tests/ -v        # 2,207 Python tests
cd mobile/android && ./gradlew test     # 464 Android unit tests
cd web && npm test                       # 106 web tests
```

See [TESTING.md](docs/development/TESTING.md) for comprehensive testing guide

## Common Issues

| Issue | Solution |
|-------|----------|
| Java not found | `export JAVA_HOME=/opt/homebrew/opt/openjdk@17` |
| ADB not found | `/opt/homebrew/share/android-commandlinetools/platform-tools/adb` |
| Port 8002 in use | `lsof -ti:8002 \| xargs kill -9` |
| Emulator mic not working | Extended Controls → Microphone → Enable host audio |
| WebSocket fails | Use `10.0.2.2` not `localhost` on Android emulator |

**Full troubleshooting:** [SETUP.md](docs/development/SETUP.md#common-issues)

## Getting Help

- **Features:** See [FEATURES.md](docs/development/FEATURES.md) for what's implemented
- **APIs:** See [API_REFERENCE.md](docs/development/API_REFERENCE.md) for all endpoints
- **Setup Issues:** See [SETUP.md](docs/development/SETUP.md)
- **Architecture Questions:** See [ARCHITECTURE.md](docs/development/ARCHITECTURE.md)
- **Session History:** See [CONVERSATIONS.md](docs/planning/CONVERSATIONS.md)

## Important Notes for Claude Code

- **This is a HIPAA-compliant healthcare application** - handle all PHI carefully
- **Voice-first UI** - Vuzix app has minimal buttons, everything is voice-activated
- **98 features already implemented** - check [FEATURES.md](docs/development/FEATURES.md) before building something new
- **Test patient ID 12724066** - use for all Cerner sandbox testing
- **EHR Proxy (port 8002) is the main backend** - Java backend is legacy
- **Documentation is organized in `/docs`** - always link to docs for details, keep this file lean
