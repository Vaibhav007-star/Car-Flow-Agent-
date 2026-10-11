# Google Flow Video Automation System

An automated, reliable video generation and archiving pipeline for **Google Flow** (labs.google / flow.google.com). Built with Python 3.12, Playwright persistent browser automation, and a Streamlit management dashboard.

---

## 📑 Table of Contents
- [Architecture Overview](#architecture-overview)
- [Automated vs Manual Boundaries](#automated-vs-manual-boundaries)
- [Prerequisites](#prerequisites)
- [Quick Start Guide (Windows PowerShell)](#quick-start-guide-windows-powershell)
- [Running the Automation](#running-the-automation)
  - [Option A: Web Dashboard (Streamlit)](#option-a-web-dashboard-streamlit)
  - [Option B: Command Line Interface (CLI)](#option-b-command-line-interface-cli)
- [Project Structure](#project-structure)
- [Prompt Management](#prompt-management)
- [MCP Integration](#mcp-integration)
- [Safety, Privacy, and Error Handling](#safety-privacy-and-error-handling)
- [Troubleshooting](#troubleshooting)

---

## 🏗️ Architecture Overview

The system is designed with modularity, reliability, and security in mind:

```
flow_agent/
├── app.py                # Streamlit Web UI (Queue controls, Video Gallery, Logs)
├── main.py               # CLI runner with arguments (--run, --login, --status, etc.)
├── browser_manager.py    # Playwright browser controller with persistent profile (.browser_data)
├── flow_automation.py    # Google Flow UI interaction, adaptive selectors, generation watcher
├── prompt_manager.py     # Prompt queue state management, JSON persistence, sync from prompts.txt
├── downloader.py         # Video download handler, blob exporter, file integrity verification
├── config.py             # Environment configuration & path resolution
├── prompts.txt           # Plain-text queue of creative prompts
├── requirements.txt      # Dependency specifications
├── .env.example          # Sample environment variables
├── .gitignore            # Git exclusion rules protecting cookies and session data
├── output_videos/        # Destination folder for completed, verified .mp4 videos
├── logs/                 # Persistent runtime execution logs (automation.log)
└── .vscode/
    └── mcp.json          # Model Context Protocol filesystem configuration
```

---

## ⚖️ Automated vs Manual Boundaries

Google Flow is an AI creative studio hosted by Google Labs that requires Google account authentication and respects human safety policies.

| Component / Task | Automated or Manual | Rationale |
| :--- | :---: | :--- |
| **Google Sign-In** | **Manual (One-Time)** | Google blocks automated login scripts and requires 2FA/CAPTCHA. You log in once manually; the session is preserved locally in `.browser_data`. |
| **Navigating to Studio** | **Automated** | The automation automatically opens `flow.google.com` using the saved session. |
| **Prompt Injection** | **Automated** | Reads the next pending prompt from the queue and types it into the generation input field. |
| **Initiating Generation** | **Automated** | Locates and clicks the Generate/Create button or submits via keyboard shortcut. |
| **Progress Monitoring** | **Automated** | Polls generation progress, monitors for timeouts, and detects completion or error messages. |
| **Error & Policy Detection** | **Automated** | Detects policy rejections, quota limits, and server errors; tags the prompt as Failed with details. |
| **Video Archiving** | **Automated** | Detects completed video elements/download buttons, downloads to `output_videos/`, and verifies non-zero byte size. |
| **Handling CAPTCHAs / Blocks** | **Manual (Safety)** | The system pauses and waits safely without attempting to circumvent Google security checks. |

---

## ⚙️ Prerequisites

- **Windows 10 or 11**
- **Python 3.11+** (Python 3.12 installed and configured in `.venv`)
- Active Google account with access to **Google Flow** (`flow.google.com`)

---

## 🚀 Quick Start Guide (Windows PowerShell)

All commands should be executed from the project root (`c:\Projects\Flow_agent`):

### 1. Activate the Virtual Environment
```powershell
.\.venv\Scripts\Activate.ps1
```
*(If PowerShell restricts scripts, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` first).*

### 2. Verify Installed Dependencies
Dependencies (`playwright`, `streamlit`, `python-dotenv`, `requests`) and Playwright Chromium are already installed in `.venv`. To verify or reinstall:
```powershell
pip install -r requirements.txt
playwright install chromium
```

### 3. Log In to Google (One-Time Setup)
Run the login helper to open the persistent browser window:
```powershell
python main.py --login
```
1. A browser window will open displaying Google Flow.
2. Sign in to your Google Account.
3. Once you see the Google Flow studio interface, close the browser window.
4. Your authenticated session is now securely stored in `.browser_data/`.

---

## 🖥️ Running the Automation

### Option A: Web Dashboard (Streamlit)
Launch the interactive web UI:
```powershell
streamlit run app.py
```
Open your browser to `http://localhost:8501`. From the dashboard you can:
- **View Queue Status**: Real-time counter of Total, Pending, Processing, Completed, and Failed prompts.
- **Start / Stop**: One-click automation start and graceful stop controls.
- **Manage Prompts**: Add new prompts on the fly, edit existing ones, or delete unwanted prompts.
- **Watch Completed Videos**: Embedded video player for all files in `output_videos/`.
- **Live Logs**: Inspect real-time browser actions and diagnostic messages.

---

### Option B: Command Line Interface (CLI)

- **Check Current Queue Status**:
  ```powershell
  python main.py --status
  ```

- **Run Batch Generation**:
  ```powershell
  python main.py --run
  ```

- **Run Next N Prompts (e.g. 1 prompt for testing)**:
  ```powershell
  python main.py --run --limit 1
  ```

- **Hunt and Queue Viral Cars (e.g. top 3 trends)**:
  ```powershell
  python main.py --hunt 3
  ```

- **Add a Prompt via Terminal**:
  ```powershell
  python main.py --add "A miniature Racing Red Porsche 911 GT3 RS..."
  ```

- **Retry Failed Prompts**:
  ```powershell
  python main.py --retry --run
  ```

---

## 🔥 Viral Car Trend Hunter

The system includes an automated **Trend Hunter** (`trend_hunter.py`) that detects trending car models and automatically converts them into the 10-shot prompt format specified in `Car Promot.pdf`:
- **Data Sources**: YouTube Shorts (via YouTube Data API v3), Google Trends RSS, and a high-velocity viral supercar & JDM catalogue.
- **Color Matching**: Automatically pairs discovered cars with one of the 10 locked colors from `Car Promot.pdf` (or lets you pick via the UI).
- **Streamlit Tab**: Navigate to the **"🔥 Viral Trend Hunter"** tab in the dashboard to scan, preview, and queue trending cars with one click!
- **CLI Command**: Run `python main.py --hunt [N]` to scan and queue the top `N` viral cars from terminal.

---

## 📺 YouTube Shorts Auto-Uploader & Autopilot

Complete end-to-end hands-free automation from trend discovery to Google Flow generation to live YouTube Shorts publishing:

### 1. YouTube Data API Setup (One-Time)
1. Download OAuth 2.0 Client credentials (`client_secrets.json` Desktop app) from [Google Cloud Console](https://console.cloud.google.com/apis/credentials).
2. Place `client_secrets.json` in the project root directory.
3. Run one-time authorization:
   ```powershell
   python yt_uploader.py --auth
   ```
4. Sign in and grant permission. Permanent credentials are saved to `token.json` (protected in `.gitignore`).

### 2. Autopilot Mode (100% Hands-Free Autonomous Loop)
Run the continuous background autopilot loop:
```powershell
python autopilot.py --interval 60 --hunt-count 3 --upload --privacy public
```
- Automatically hunts top viral cars every cycle.
- Synthesizes 10-shot ASMR prompts formatted to `Car Promot.pdf`.
- Generates videos via Google Flow.
- Downloads and verifies completed `.mp4` videos.
- Automatically uploads to YouTube Shorts with `#Shorts`, ASMR tags, and category Autos & Vehicles (`categoryId: 2`).

### 3. Direct Scheduling & 2 Daily Peak Slots
The system automatically optimizes for global viewer engagement by targeting the **2 daily peak traffic windows**:
- **Slot 1**: `1:30 PM IST` (`08:00 UTC` / `4:00 AM EST` - European lunch & US morning feed)
- **Slot 2**: `8:00 PM IST` (`14:30 UTC` / `10:30 AM EST` - India/Asia prime evening & US midday peak)

#### Commands:
- **Autopilot with Daily Peak Slots (Hands-free 2 Shorts/day)**:
  ```powershell
  python autopilot.py --count 2 --upload --daily-slots
  ```
- **Batch Upload all completed videos to Daily Peak Slots**:
  ```powershell
  python yt_uploader.py --all --daily-slots
  ```
- **Schedule video to publish in N hours**:
  ```powershell
  python yt_uploader.py --upload output_videos/video_001_porsche_gt3_rs.mp4 --schedule-in-hours 3
  ```
- **Via Streamlit Dashboard**: Open `http://localhost:8501`, go to **"🎥 Video Gallery"**, select **"Daily Peak Slot (1:30 PM / 8:00 PM IST)"**, and click **"📅 Schedule Peak Slot"**.

### 4. Viral SEO Title & Tag Engine
`YouTubeSEO` automatically writes high-converting metadata for every Short:
- **Rotating Viral Hooks**:
  - `Satisfying {Car} Assembly ASMR 🎧 #Shorts`
  - `Rate this {Car} build 1-10? 🔥 #Shorts`
  - `Wait for the exhaust sound... {Car} 🔊 #Shorts`
  - `Building the Ultimate {Color} {Car} in 8s ⚡ #Shorts`
- **Descriptions**: Headphone prompts, engagement question ("Which car should we customize next?"), and targeted hashtags.
- **Tags**: 20+ search volume tags including ASMR car clicks, diecast restoration, model assembly, and specific vehicle keywords.


## 📝 Prompt Management

Prompts are managed with dual synchronization:
1. **`prompts.txt`**: Place individual prompts on separate lines. Lines starting with `#` are treated as comments.
2. **`prompts_state.json`**: Tracks the persistent status (`Pending`, `Processing`, `Completed`, `Failed`), output filenames, timestamps, and error descriptions.

When you add lines to `prompts.txt`, the system automatically syncs new items without resetting already completed videos.

---

## 🔌 MCP Integration

The system includes native Model Context Protocol (MCP) servers:

### 1. `google-flow` (Native Automation Server)
- **File**: `mcp_server.py`
- **Configured In**:
  - Global Antigravity: `~/.gemini/config/mcp_config.json`
  - Workspace: `.vscode/mcp.json`
- **Available MCP Tools**:
  - `add_video_prompt(prompt)`: Queues a new video prompt.
  - `get_queue_status()`: Checks pending, completed, and failed counts.
  - `trigger_video_generation(limit)`: Runs automation to generate videos on Google Flow.
  - `list_generated_videos()`: Inspects files in `output_videos/`.
  - `retry_failed_prompts()`: Resets failed items to Pending.

### 2. `filesystem` (Official Filesystem Server)
- **Configured In**: `.vscode/mcp.json`
- **Scope**: Scoped strictly to `c:/Projects/Flow_agent` for safe media and workspace file operations.

---

## 🔒 Safety, Privacy, and Error Handling

1. **Credentials**: Passwords and session cookies are never hardcoded or logged. All persistent session tokens remain strictly inside `.browser_data/` (which is excluded in `.gitignore`).
2. **Rate Limits & Terms**: Playwright automation includes deliberate pacing delays between actions to respect Google Flow usage policies.
3. **Integrity Verification**: The system checks that any saved video exists on disk, has a valid file size (minimum 1KB), and matches expected media headers before marking a prompt as `Completed`.
4. **Crash Resilience**: If network interruption occurs, the current item is flagged as `Failed` with the exact error message, leaving subsequent items intact in the queue.

