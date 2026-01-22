# Vuzix Minerva Workflow Checklist

## Setup
- [ ] Vuzix is on the same Wi-Fi as the dev machine.
- [ ] EHR proxy is running and reachable at the configured URL.
- [ ] Microphone, camera, overlay, and notification permissions are granted.

## Build & Install
- [ ] `cd mobile && npm install` (if deps changed).
- [ ] `cd mobile/android && ./gradlew assembleDebug` succeeds.
- [ ] Install the APK on Vuzix and launch the app.

## Pairing (if enabled)
- [ ] Launch pairing flow (“pair device”) and scan dashboard QR.
- [ ] Pairing success confirmed in UI.
- [ ] Session unlock works with “verify me” (if required).

## Wake Word & Command Flow
- [ ] Say “Hey Minerva” and confirm listening state.
- [ ] “Load patient” loads the default test patient.
- [ ] “Show vitals” / “Show labs” / “Show meds” update the HUD.
- [ ] “Start note” → dictation → “Stop note” completes without errors.

## Minerva Proactive Alerts
- [ ] On patient load, Minerva speaks proactive alerts when applicable.
- [ ] “Minerva is speaking…” indicator appears during alert playback.
- [ ] HUD shows Minerva alert banner with severity styling.
- [ ] “Got it, Minerva” stops alert playback and clears the HUD banner.

## Minerva Q&A
- [ ] “Hey Minerva” activates conversational mode.
- [ ] Ask a clinical question and verify a spoken response.
- [ ] “Minerva stop” ends the session cleanly.

## Wrap Up
- [ ] Stop streaming/transcription and confirm no crash.
- [ ] Close the app and relaunch to confirm settings persist.
