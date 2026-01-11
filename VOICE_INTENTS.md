# Voice Intent Chaining

This update adds support for chaining multiple voice intents in a single utterance
so users can perform several actions in sequence (load a patient, show sections,
and read a summary) without repeating the wake word.

## How it works

When a transcript is processed, the app now parses multi-intent phrases and
executes them in order before the existing single-command `lower.contains(...)`
chain runs. The parser looks for common conjunctions (e.g., "and", "then") and
extracts intent keywords in each clause.

## Supported intent keywords

The parser currently recognizes these intents:

- **LoadPatient**: "open", "load", or "show" a patient's chart/record
- **ShowVitals**: "vital" or "vitals"
- **ShowLabs**: "lab" or "labs"
- **SpeakSummary**: "read it back", "read summary", "speak summary", "brief"

## Example commands

Try commands like:

- "Open John Doe's chart and show last vitals and labs and read it back"
- "Load patient Jane Smith then show vitals and read summary"
- "Show labs and speak summary"

## Execution behavior

Intents run in the order they appear. The executor inserts a short delay between
actions, with a slightly longer delay after a patient load to give the UI and
data time to update before subsequent fetches.
