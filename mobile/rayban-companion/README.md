# MDx Vision - Ray-Ban Meta Companion App

This is the phone-side companion app that connects to Ray-Ban Meta glasses using the Meta Wearables Device Access Toolkit.

## Architecture

```
┌─────────────────────────┐
│   Ray-Ban Meta Glasses  │
│   ├── Microphone        │──────┐
│   ├── Camera            │      │ Bluetooth
│   └── Display           │◄─────┤
└─────────────────────────┘      │
                                 │
┌─────────────────────────┐      │
│   Phone Companion App   │◄─────┘
│   ├── Audio Processing  │
│   ├── Voice Recognition │
│   └── Display Renderer  │
└───────────┬─────────────┘
            │ HTTP/WebSocket
            ▼
┌─────────────────────────┐
│   EHR Proxy Backend     │
│   ├── Transcription     │
│   ├── FHIR Integration  │
│   └── AI Note Gen       │
└─────────────────────────┘
```

## Setup

### Prerequisites

1. Ray-Ban Meta glasses (Gen 1 or Gen 2)
2. Meta AI app installed on phone
3. Glasses paired with Meta AI app
4. Developer Mode enabled on glasses

### Enable Developer Mode

1. Open Meta AI app
2. Go to Settings → Glasses → Developer Mode
3. Toggle ON

### Build & Run

```bash
# Android
cd android
./gradlew assembleDebug
adb install -r app/build/outputs/apk/debug/app-debug.apk

# iOS
cd ios
pod install
open RayBanCompanion.xcworkspace
# Build and run from Xcode
```

## Features

- Voice command recognition via glasses microphone
- Real-time transcription display on glasses
- Patient data HUD overlay
- Voice-activated EHR queries
- Hands-free clinical documentation

## SDK Reference

- [Meta Wearables Device Access Toolkit](https://developers.meta.com/wearables)
- [Getting Started Guide](https://wearables.developer.meta.com/docs/getting-started-toolkit)
