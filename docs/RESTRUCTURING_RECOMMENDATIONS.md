# Documentation Restructuring Recommendations

**Date:** January 22, 2026
**Status:** Completed initial reorganization

## Changes Made

### ✅ Completed Actions

1. **Created organized directory structure**
   - `/business` - Strategic and commercial documentation
   - `/clinical` - Clinical research and health equity
   - `/development` - Technical documentation
   - `/ehr` - EHR integration guides
   - `/planning` - Product planning and session logs
   - `/archived` - Deprecated/completed materials

2. **Removed obsolete files**
   - ❌ `findings.md` - Minerva Phase 3 research notes (project completed)
   - ❌ `progress.md` - Minerva Phase 3 progress log (project completed)
   - ❌ `task_plan.md` - Minerva Phase 3 task plan (project completed)
   - ❌ `FINANCIAL-MODEL-R6-FULL-EXPORT.md` - 1.8MB file that should be a spreadsheet

3. **Created navigation**
   - ✅ Added `docs/README.md` with directory structure guide

---

## Recommended Consolidations

### Priority 1: Merge Redundant Feature Documentation

**Problem:** Multiple overlapping feature checklists
- `development/FEATURES.md` (98 features, 39KB)
- `planning/MDX_V2_FEATURES.md` (v2.0 checklist, 26KB)
- `planning/JARVIS_FEATURES_PLAN.md` (AI features roadmap, 9.5KB)

**Recommendation:**
```
MERGE → development/FEATURES.md (keep as single source of truth)
  - Already has 98 features with implementation status
  - Most comprehensive and up-to-date

ARCHIVE → planning/MDX_V2_FEATURES.md
  - Mostly redundant with FEATURES.md
  - Historical value only

KEEP SEPARATE → planning/JARVIS_FEATURES_PLAN.md
  - Future roadmap, not current features
  - Rename to FUTURE_AI_FEATURES.md for clarity
```

### Priority 2: Consolidate EHR Documentation

**Problem:** EHR information spread across 5 files
- `ehr/EHR_ACCESS_GUIDE.md` (17KB) - Registration instructions
- `ehr/EHR_IMPLEMENTATIONS.md` (8.6KB) - Current status
- `ehr/EHR_AGGREGATOR_PLATFORMS.md` (16KB) - Aggregator research
- `ehr/EHR_AMBULATORY_RESEARCH.md` (15KB) - Ambulatory research
- `ehr/INTERNATIONAL_EHR_EXPANSION.md` (12KB) - International markets

**Recommendation:**
```
CREATE → ehr/README.md
  - Overview of EHR integration strategy
  - Links to specific guides

MERGE:
  - EHR_IMPLEMENTATIONS.md → EHR_ACCESS_GUIDE.md (Section 2: Current Status)
  - Creates single "how to connect" guide

KEEP SEPARATE (research/reference):
  - EHR_AGGREGATOR_PLATFORMS.md (future opportunities)
  - EHR_AMBULATORY_RESEARCH.md (market analysis)
  - INTERNATIONAL_EHR_EXPANSION.md (international strategy)
```

### Priority 3: Streamline Testing Documentation

**Problem:** Testing docs split across 3 files
- `development/TESTING.md` (11KB) - Testing strategy
- `development/TEST_COVERAGE_PLAN.md` (8.1KB) - Coverage analysis
- `development/MANUAL_TESTING_CHECKLIST.md` (8.5KB) - Manual tests

**Recommendation:**
```
MERGE → development/TESTING.md
  - Section 1: Overview (from TESTING.md)
  - Section 2: Automated Testing (from TEST_COVERAGE_PLAN.md)
  - Section 3: Manual Testing (from MANUAL_TESTING_CHECKLIST.md)

DELETE:
  - TEST_COVERAGE_PLAN.md (content merged)
  - Keep MANUAL_TESTING_CHECKLIST.md if used as active checklist
```

---

## Files to Keep As-Is

### Critical - Do Not Modify
- ✅ `development/CLAUDE.md` - Primary AI context file
- ✅ `development/FEATURES.md` - Authoritative feature list
- ✅ `development/MINERVA.md` - Active implementation plan
- ✅ `development/VOICE_COMMANDS.md` - Complete command reference
- ✅ `planning/CONVERSATIONS.md` - Session history log

### Business Critical
- ✅ `business/PRICING.md` - Commercial strategy
- ✅ `business/INVESTOR.md` - Fundraising materials
- ✅ `business/STRATEGIC_ROADMAP.md` - Product direction

### Research Reference
- ✅ `clinical/RACIAL_MEDICINE_DISPARITIES.md` - Unique research
- ✅ `clinical/CULTURAL_CARE_PREFERENCES.md` - Implementation guide

---

## Content Cleanup Recommendations

### Remove from CONVERSATIONS.md
**Issue:** Growing indefinitely (24KB, 2,000+ lines)

**Recommendation:**
```
1. Archive sessions older than 6 months
   - Create planning/archive/CONVERSATIONS_2025_H1.md
   - Keep only last 3-6 months in main file

2. Extract permanent decisions to separate file
   - Create planning/ARCHITECTURE_DECISIONS.md
   - Move key technical decisions out of session logs
```

### Simplify VOICE_COMMANDS.md
**Issue:** May have redundant patterns

**Recommendation:**
```
Audit for:
- Duplicate command patterns
- Deprecated commands (if UI changed)
- Commands for removed features

Current size: 22KB - Review if >25KB
```

### Update CLAUDE.md Regularly
**Issue:** References docs in old locations

**Recommendation:**
```
Update "Key Documents" section:
- Change flat file references to new paths
- Example: FEATURES.md → docs/development/FEATURES.md

Run this periodically to keep in sync
```

---

## Archive Candidates for Review

### Question: Still Needed?
- `archived/DEMO_CSUITE.md` (19KB)
  - **If used for demos:** Move to `/business/DEMOS.md`
  - **If obsolete:** Delete

- `archived/INTERNAL_COMPETITIVE_ANALYSIS.md` (12KB)
  - **If still relevant:** Update and move to `/business/COMPETITIVE_ANALYSIS.md`
  - **If outdated:** Delete (competitive landscape changes quickly)

- `planning/MDX_GLASSES_PRD.md` (11KB)
  - **If active PRD:** Rename to `PRODUCT_REQUIREMENTS.md`
  - **If historical:** Move to archived

---

## New Files to Create

### Recommended Additions

1. **`development/ARCHITECTURE.md`**
   - System architecture diagrams
   - Data flow documentation
   - Technology stack decisions
   - Extract from CLAUDE.md

2. **`development/API_REFERENCE.md`**
   - Complete API endpoint documentation
   - Request/response examples
   - Authentication details
   - Extract from CLAUDE.md

3. **`development/CONTRIBUTING.md`**
   - Development setup guide
   - Code style guidelines
   - PR process
   - Testing requirements

4. **`business/CUSTOMER_PERSONAS.md`**
   - Target user profiles
   - Use cases by specialty
   - Pain points addressed

5. **`ehr/TROUBLESHOOTING.md`**
   - Common EHR connection issues
   - Error codes and solutions
   - FHIR debugging tips

---

## Implementation Plan

### Phase 1: High-Priority Consolidations (1-2 hours)
1. Merge testing documentation
2. Update CLAUDE.md with new doc paths
3. Create ehr/README.md overview

### Phase 2: Archive Old Sessions (30 minutes)
1. Archive CONVERSATIONS.md sessions >6 months old
2. Extract architecture decisions

### Phase 3: Content Audit (2-3 hours)
1. Review archived files for deletion
2. Identify outdated sections in active docs
3. Update references and links

### Phase 4: Create New Documentation (ongoing)
1. Split CLAUDE.md into focused docs
2. Create API reference
3. Add troubleshooting guides

---

## Maintenance Guidelines

### Keep Documentation Fresh
- Review quarterly for outdated content
- Archive old session logs (keep 6 months in CONVERSATIONS.md)
- Update FEATURES.md as features ship
- Keep CLAUDE.md as "quick start" (< 500 lines)

### When to Archive
- Planning documents after feature ships
- Competitive analysis after 6 months
- Demo scripts when outdated
- Session logs after 6 months

### When to Delete
- Duplicate content (always keep newest)
- Features that were removed
- Research for abandoned features
- Obsolete integration guides

---

## Summary

**Immediate Actions Taken:**
- ✅ Organized 33 files into 6 directories
- ✅ Deleted 4 obsolete files
- ✅ Created README.md navigation

**Recommended Next Steps:**
1. Merge MDX_V2_FEATURES.md into FEATURES.md
2. Consolidate testing documentation
3. Update CLAUDE.md with new paths
4. Archive old CONVERSATIONS.md sessions
5. Review archived files for deletion

**Outcome:**
- More navigable documentation structure
- Reduced redundancy
- Easier for new developers and Claude Code
- Clearer separation of business vs technical docs
