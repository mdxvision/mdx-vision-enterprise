# Planning with Files - MDx Vision

> Manus-style file-based planning for complex development tasks.
> "Context Window = RAM (volatile, limited) | Filesystem = Disk (persistent, unlimited)"

## Overview

This skill implements a three-file planning system for MDx Vision development. Use it for any task requiring 3+ steps, multiple file changes, or research.

## The Three Files

| File | Purpose | Update When |
|------|---------|-------------|
| `task_plan.md` | Phase tracking with checkboxes | Starting task, completing phases, errors |
| `findings.md` | Research discoveries, decisions | After discoveries, every 2 browser ops |
| `progress.md` | Session log, test results | After each phase, on errors |

## When to Use

**Use for:**
- Multi-phase features (like Minerva implementation)
- Bug investigations
- EHR integration work
- Any task with 5+ tool calls
- Research requiring multiple web fetches

**Skip for:**
- Single-file edits
- Quick questions
- Simple bug fixes

## Critical Rules

### 1. Create Plan First
Never start complex work without `task_plan.md`. Create it immediately.

### 2. The 2-Action Rule
After every 2 view/search/browse operations, update `findings.md`. Visual/multimodal info is lost quickly.

### 3. Read Before Deciding
Re-read `task_plan.md` before major decisions to prevent goal drift.

### 4. Log ALL Errors
Every error goes in both `task_plan.md` (Errors table) and `progress.md` (Error Log). This prevents repeating mistakes.

### 5. Never Repeat Failures
Track attempts. If an approach failed, mutate the strategy - don't retry identical actions.

### 6. Update After Acts
Mark phase status after completing work. Log actions in `progress.md`.

## Quick Start

```bash
# Create planning files for a new task
/plan [task description]
```

This will create all three files with appropriate templates.

## File Update Guide

| Event | File(s) | Action |
|-------|---------|--------|
| Starting task | task_plan.md | Create with phases |
| Found information | findings.md | Add to Research Findings |
| After 2 browser ops | findings.md | **MUST update** (2-Action Rule) |
| Made decision | findings.md | Add to Technical Decisions |
| Completed phase | task_plan.md, progress.md | Update status, log details |
| Error occurred | task_plan.md, progress.md | Add to Errors table, Error Log |
| Test results | progress.md | Add to Test Results section |

## MDx Vision Specific

For MDx Vision development, typical phases include:

1. **Research** - Understand existing code, gather requirements
2. **Design** - Plan approach, identify files to modify
3. **Implement** - Write the code
4. **Test** - Verify functionality works
5. **Document** - Update CLAUDE.md, FEATURES.md, etc.
6. **Commit** - Git commit with proper message

## Example Task Plan

```markdown
# Task Plan: Add Minerva Proactive Alerts

## Goal
Implement Phase 3 of Minerva - proactive alerts on patient load

## Phases

### Phase 1: Research [complete]
- [x] Review existing pre-visit prep (Feature #92)
- [x] Understand Minerva endpoint structure
- [x] Identify integration points

### Phase 2: Implementation [in_progress]
- [ ] Add /api/v1/minerva/proactive endpoint
- [ ] Integrate with patient load flow
- [ ] Add TTS announcements

### Phase 3: Testing [pending]
- [ ] Test with Cerner patient
- [ ] Test with Epic patient
- [ ] Verify TTS speaks correctly

## Errors
| Error | Cause | Resolution |
|-------|-------|------------|
| - | - | - |
```

## Integration with TodoWrite

This planning system complements the built-in TodoWrite tool:
- **TodoWrite** - Quick in-session task tracking (volatile)
- **Planning Files** - Persistent cross-session documentation (persistent)

Use both together: TodoWrite for immediate tasks, planning files for complex multi-session work.
