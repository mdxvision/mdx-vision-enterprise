# MDx Vision - Development Setup

## Prerequisites

### Required Software

- **Java 17** (OpenJDK)
- **Python 3.11+**
- **Node.js 18+** (for web dashboard)
- **Android Studio** (for mobile development)
- **Android SDK** (API Level 30+)
- **Git**

### Optional Tools

- **Android Command Line Tools** (for ADB without Android Studio)
- **Docker** (for containerized deployment)
- **PostgreSQL** (for future backend database)

## Installation

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/mdx-vision-enterprise.git
cd mdx-vision-enterprise
```

### 2. Java Setup

**macOS (Homebrew):**
```bash
brew install openjdk@17
export JAVA_HOME=/opt/homebrew/opt/openjdk@17
echo 'export JAVA_HOME=/opt/homebrew/opt/openjdk@17' >> ~/.zshrc
```

**Linux (apt):**
```bash
sudo apt update
sudo apt install openjdk-17-jdk
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
```

**Verify:**
```bash
java -version  # Should show 17.x.x
```

### 3. Python Setup

**Create Virtual Environment:**
```bash
cd ehr-proxy
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

**Install Dependencies:**
```bash
pip install -r requirements.txt
```

**Key Packages:**
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `anthropic` - Claude API
- `assemblyai` - Transcription
- `chromadb` - Vector database
- `sentence-transformers` - Embeddings
- `pyrnnoise` - Noise reduction

### 4. Node.js Setup (Web Dashboard)

```bash
cd web
npm install
```

### 5. Android Setup

**Option A: Android Studio**
1. Download and install [Android Studio](https://developer.android.com/studio)
2. Open project: `mobile/android`
3. Let Gradle sync
4. Install SDK Platform 30 (Android 11)
5. Install Vuzix SDK (if using Vuzix hardware)

**Option B: Command Line Tools**
```bash
# macOS Homebrew
brew install --cask android-commandlinetools
export ANDROID_HOME=/opt/homebrew/share/android-commandlinetools
export PATH=$PATH:$ANDROID_HOME/platform-tools
```

**Verify ADB:**
```bash
adb version  # Should work
```

## Environment Variables

### EHR Proxy (.env file)

Create `ehr-proxy/.env`:

```bash
# Transcription (Required)
TRANSCRIPTION_PROVIDER=assemblyai           # or "deepgram"
ASSEMBLYAI_API_KEY=your_key_here
DEEPGRAM_API_KEY=your_key_here             # If using Deepgram
ENABLE_MEDICAL_VOCAB=true

# AI Notes (Required)
CLAUDE_API_KEY=your_anthropic_key_here

# EHR Integration (Optional)
CERNER_CLIENT_ID=0fab9b20-adc8-4940-bbf6-82034d1d39ab
CERNER_CLIENT_SECRET=your_secret
EPIC_CLIENT_ID=your_epic_client_id
EPIC_CLIENT_SECRET=your_epic_secret

# RAG Knowledge Base (Optional)
ENABLE_RAG=true
CHROMA_PERSIST_DIRECTORY=./data/chroma_db

# PubMed Integration (Optional)
NCBI_API_KEY=your_ncbi_key                 # Not required for <3 req/sec

# Security (Optional)
JWT_SECRET=your_random_secret_key
SESSION_TIMEOUT_MINUTES=5

# Server Configuration
HOST=0.0.0.0
PORT=8002
DEBUG=true
LOG_LEVEL=INFO

# CORS (Development)
ALLOWED_ORIGINS=http://localhost:5173,http://10.0.2.2:5173
```

### Web Dashboard (.env.local)

Create `web/.env.local`:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8002
NEXT_PUBLIC_EHR_PROXY_URL=http://localhost:8002
```

### Android App (gradle.properties)

Create `mobile/android/gradle.properties`:

```bash
# EHR Proxy URL (for emulator)
ehr.proxy.url=http://10.0.2.2:8002

# Or for physical device on same network
# ehr.proxy.url=http://192.168.1.100:8002

# API Keys (for debug builds only)
assemblyai.api.key=your_key_here
```

**Security Note:** Never commit API keys to version control. Use environment variables or gradle.properties (gitignored).

## Running the Application

### Start EHR Proxy

```bash
cd ehr-proxy
source venv/bin/activate
python main.py
```

Server will start on `http://localhost:8002`

**Check Status:**
```bash
curl http://localhost:8002/health
```

### Start Web Dashboard

```bash
cd web
npm run dev
```

Dashboard will open at `http://localhost:5173`

### Build Android App

**Debug Build:**
```bash
cd mobile/android
export JAVA_HOME=/opt/homebrew/opt/openjdk@17
./gradlew assembleDebug
```

APK location: `mobile/android/app/build/outputs/apk/debug/app-debug.apk`

**Install to Device/Emulator:**
```bash
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

**Launch App:**
```bash
adb shell am start -n com.mdxvision.glasses/com.mdxvision.MainActivity
```

### Run Android Emulator

**From Android Studio:**
1. Tools → Device Manager
2. Create Virtual Device (API Level 30)
3. Enable mic: Extended Controls → Microphone → "Virtual microphone uses host audio input"

**From Command Line:**
```bash
emulator -avd Pixel_5_API_30 -feature -Vulkan
```

## Testing

### Python Tests (EHR Proxy)

```bash
cd ehr-proxy
pytest tests/ -v                    # Run all tests
pytest tests/test_main.py -v       # Run specific file
pytest tests/ -k "test_patient"    # Run tests matching pattern
pytest --cov=. tests/              # With coverage report
```

**2,207 tests** covering:
- API endpoints
- Transcription
- RAG knowledge base
- Health equity features
- Billing/DNFB
- Authentication

### Android Unit Tests

```bash
cd mobile/android
./gradlew test                     # All unit tests
./gradlew testDebugUnitTest       # Debug variant only
```

**464 tests** covering:
- Voice command parsing
- Gesture detection
- Data models
- Utility functions

### Android E2E Tests

**Requires connected device or emulator:**

```bash
cd mobile/android
./gradlew connectedAndroidTest
```

**54 tests** covering:
- API integration
- Voice command workflows
- Ambient Clinical Intelligence

### Web Dashboard Tests

```bash
cd web
npm test                           # Run all tests
npm test -- --watch                # Watch mode
npm run test:coverage              # With coverage
```

**106 tests** covering:
- Components
- API clients
- Utilities

### Manual Testing

See `docs/development/MANUAL_TESTING_CHECKLIST.md` for 55+ tests requiring human interaction (voice commands, TTS, gestures).

## Common Issues

### Java Not Found

**Symptom:** `JAVA_HOME not set` or `java: command not found`

**Solution:**
```bash
# macOS
export JAVA_HOME=/opt/homebrew/opt/openjdk@17
echo 'export JAVA_HOME=/opt/homebrew/opt/openjdk@17' >> ~/.zshrc

# Linux
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
echo 'export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64' >> ~/.bashrc
```

### ADB Not Found

**Symptom:** `adb: command not found`

**Solution:**
```bash
# macOS - Homebrew installation
/opt/homebrew/share/android-commandlinetools/platform-tools/adb

# Add to PATH
export PATH=$PATH:/opt/homebrew/share/android-commandlinetools/platform-tools
echo 'export PATH=$PATH:/opt/homebrew/share/android-commandlinetools/platform-tools' >> ~/.zshrc

# Or use Android Studio's ADB
export PATH=$PATH:~/Library/Android/sdk/platform-tools
```

### Port Already in Use

**Symptom:** `Address already in use: bind()`

**Solution:**
```bash
# Find process using port 8002
lsof -ti:8002

# Kill the process
lsof -ti:8002 | xargs kill -9

# Or use different port
PORT=8003 python main.py
```

### Emulator Mic Not Working

**Symptom:** No audio input in transcription

**Solution:**
1. Open emulator Extended Controls (... button)
2. Go to Microphone section
3. Enable "Virtual microphone uses host audio input"
4. Select your host microphone
5. Restart the app

### WebSocket Connection Failed

**Symptom:** `WebSocket connection to 'ws://localhost:8002/ws/transcribe' failed`

**Solution:**
```bash
# Android emulator uses 10.0.2.2 for localhost
# Update app configuration
EHR_PROXY_URL=http://10.0.2.2:8002

# For physical device, use your machine's IP
EHR_PROXY_URL=http://192.168.1.100:8002
```

### Gradle Build Failed - Lombok Incompatibility

**Symptom:** `Lombok annotation processing error with Java 17.0.17`

**Solution:**
```bash
# Downgrade to Java 17.0.13 or upgrade to 17.0.18+
brew install openjdk@17

# Or disable Lombok in Gradle
# Edit build.gradle:
# configurations.all {
#     exclude group: 'org.projectlombok', module: 'lombok'
# }
```

### Python Dependencies Installation Fails

**Symptom:** `error: could not build wheels for pyrnnoise`

**Solution:**
```bash
# Install system dependencies first
# macOS
brew install portaudio

# Linux
sudo apt-get install portaudio19-dev python3-dev

# Then reinstall
pip install --upgrade pip
pip install -r requirements.txt
```

### ChromaDB Initialization Error

**Symptom:** `ChromaDB could not initialize`

**Solution:**
```bash
# Create data directory
mkdir -p ehr-proxy/data/chroma_db

# Set permissions
chmod 755 ehr-proxy/data/chroma_db

# Or disable RAG temporarily
ENABLE_RAG=false python main.py
```

### AssemblyAI/Deepgram API Errors

**Symptom:** `401 Unauthorized` or `Invalid API key`

**Solution:**
1. Verify API key in `.env` file
2. Check for extra spaces or quotes
3. Test API key with curl:

```bash
# AssemblyAI
curl -H "Authorization: YOUR_KEY" https://api.assemblyai.com/v2/

# Deepgram
curl -H "Authorization: Token YOUR_KEY" https://api.deepgram.com/v1/projects
```

### Vuzix SDK Not Found

**Symptom:** Build error: `Could not resolve: com.vuzix:hud-actionmenu:2.9.0`

**Solution:**
```bash
# Add Vuzix Maven repository to build.gradle
repositories {
    maven {
        url "https://vuzix.jfrog.io/artifactory/vuzix-public"
    }
}

# Or disable Vuzix SDK for testing
# Comment out in build.gradle dependencies
```

### Network Timeout on EHR Requests

**Symptom:** `ReadTimeout: HTTPSConnectionPool`

**Solution:**
1. Check internet connection
2. Verify EHR sandbox is accessible
3. Increase timeout in code:

```python
# In ehr-proxy/main.py
import httpx

async with httpx.AsyncClient(timeout=30.0) as client:
    response = await client.get(url)
```

### websockets Library Compatibility

**Symptom:** `websockets.connect() got an unexpected keyword argument 'extra_headers'`

**Solution:**
```python
# Use 'additional_headers' instead of 'extra_headers'
async with websockets.connect(
    uri,
    additional_headers={"Authorization": "Bearer token"}
) as ws:
    ...
```

### Android Emulator Slow Performance

**Solution:**
1. Enable hardware acceleration (HAXM on Intel, Hypervisor.Framework on Apple Silicon)
2. Allocate more RAM in AVD settings (4GB recommended)
3. Use x86_64 system image (not ARM)
4. Close other resource-heavy applications

### CORS Errors in Web Dashboard

**Symptom:** `Access-Control-Allow-Origin header missing`

**Solution:**
```python
# In ehr-proxy/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://10.0.2.2:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Development Workflow

### Typical Development Session

```bash
# Terminal 1: Start EHR Proxy
cd ehr-proxy && source venv/bin/activate && python main.py

# Terminal 2: Start Web Dashboard
cd web && npm run dev

# Terminal 3: Android development
cd mobile/android && ./gradlew installDebug && adb logcat | grep MDx
```

### Hot Reload

- **EHR Proxy:** Restart server after code changes
- **Web Dashboard:** Auto-reload on save (Vite HMR)
- **Android:** Rebuild and reinstall APK

### Debugging

**Python:**
```bash
# Add breakpoints with pdb
import pdb; pdb.set_trace()

# Or use VS Code debugger
# Launch configuration in .vscode/launch.json
```

**Android:**
```bash
# View logs
adb logcat | grep -E "MDx|MainActivity|AudioStreaming"

# Debug with Android Studio
# Run → Debug 'app' (Shift+F9)
```

**Web:**
```bash
# Browser DevTools (F12)
# React DevTools extension recommended
```

## Performance Optimization

### Android App

- Use ProGuard for release builds (shrinks APK)
- Enable R8 code shrinking
- Optimize images and resources
- Use RecyclerView for long lists

### EHR Proxy

- Use async/await for I/O operations
- Cache frequently accessed data (Redis in production)
- Batch database operations
- Profile with `cProfile`:

```bash
python -m cProfile -o profile.stats main.py
python -m pstats profile.stats
```

### Web Dashboard

- Use Next.js Image component
- Implement code splitting
- Enable production mode:

```bash
npm run build
npm start  # Production server
```

## Deployment

### EHR Proxy Production

**Docker:**
```bash
cd ehr-proxy
docker build -t mdx-ehr-proxy .
docker run -p 8002:8002 --env-file .env mdx-ehr-proxy
```

**Kubernetes (future):**
```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ehr-proxy
spec:
  replicas: 3
  ...
```

### Web Dashboard Production

**Vercel (recommended):**
```bash
cd web
vercel deploy --prod
```

**Self-hosted:**
```bash
npm run build
npm start
```

### Android App Release

```bash
cd mobile/android

# Generate release key (first time)
keytool -genkey -v -keystore mdx-release.keystore -alias mdx -keyalg RSA -keysize 2048 -validity 10000

# Build release APK
./gradlew assembleRelease

# Sign APK
jarsigner -verbose -sigalg SHA1withRSA -digestalg SHA1 \
  -keystore mdx-release.keystore \
  app/build/outputs/apk/release/app-release-unsigned.apk mdx

# Align APK
zipalign -v 4 app-release-unsigned.apk app-release.apk
```

## Next Steps

- Review [ARCHITECTURE.md](./ARCHITECTURE.md) for system design
- Check [API_REFERENCE.md](./API_REFERENCE.md) for endpoint documentation
- See [TESTING.md](./TESTING.md) for testing guidelines
- Read [FEATURES.md](./FEATURES.md) for feature checklist
- Explore [VOICE_COMMANDS.md](./VOICE_COMMANDS.md) for command reference
