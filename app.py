"""Streamlit Dashboard for Google Flow Video Automation System.
Provides queue management, live execution controls, status monitoring,
downloaded video gallery, and activity logs.
"""

import os
import sys
import time
import subprocess
import threading
from pathlib import Path
import streamlit as st

# Configure page
st.set_page_config(
    page_title="Google Flow Video Automation",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

from config import FLOW_URL, OUTPUT_DIR, LOGS_DIR, USER_DATA_DIR, YOUTUBE_API_KEY
from prompt_manager import PromptManager
from downloader import VideoDownloader
from trend_hunter import TrendHunter, LOCKED_COLORS, format_short_video_prompt

# Initialize managers
pm = PromptManager()
downloader = VideoDownloader()

# Session state initialization
if "running_process" not in st.session_state:
    st.session_state.running_process = None
if "active_worker" not in st.session_state:
    st.session_state.active_worker = None

# Custom CSS for modern visual polish
st.markdown("""
<style>
    .metric-card {
        background-color: #1e222b;
        border-radius: 8px;
        padding: 16px;
        border: 1px solid #2e3440;
        text-align: center;
    }
    .status-badge {
        display: inline-block;
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .badge-completed { background-color: #0e4429; color: #3fb950; }
    .badge-processing { background-color: #3b2300; color: #d29922; }
    .badge-pending { background-color: #161b22; color: #8b949e; }
    .badge-failed { background-color: #490202; color: #f85149; }
</style>
""", unsafe_allow_html=True)


# --- Background Worker Function ---
def run_automation_worker(limit=None):
    from browser_manager import BrowserManager
    from flow_automation import GoogleFlowAutomation

    bm = BrowserManager(headless=False)
    automation = GoogleFlowAutomation(browser_manager=bm, prompt_manager=pm, downloader=downloader)
    try:
        automation.run_queue(max_items=limit)
    except Exception as e:
        st.session_state["last_error"] = str(e)
    finally:
        bm.close()
        st.session_state.active_worker = None


# --- Top Header & Metrics ---
st.title("🎬 Google Flow Video Automation")
st.caption("Automated video generation, prompt scheduling, and local media archiving for Google Flow (Veo).")

summary = pm.get_summary()

col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)
col_m1.metric("Total Prompts", summary["Total"])
col_m2.metric("⏳ Pending", summary["Pending"])
col_m3.metric("⚙️ Processing", summary["Processing"])
col_m4.metric("✅ Completed", summary["Completed"])
col_m5.metric("❌ Failed", summary["Failed"])

st.divider()

# --- Sidebar Controls ---
st.sidebar.header("🕹️ Automation Controls")

# Session Status
is_active = st.session_state.active_worker is not None and st.session_state.active_worker.is_alive()
if is_active:
    st.sidebar.warning("⚡ Automation is currently running...")
else:
    st.sidebar.info("💤 Automation is idle.")

# Run controls
col_btn1, col_btn2 = st.sidebar.columns(2)
with col_btn1:
    if st.button("▶️ Start Run", disabled=is_active, use_container_width=True, type="primary"):
        worker = threading.Thread(target=run_automation_worker, daemon=True)
        worker.start()
        st.session_state.active_worker = worker
        st.rerun()

with col_btn2:
    if st.button("⏹️ Stop Run", disabled=not is_active, use_container_width=True):
        st.session_state.active_worker = None
        st.sidebar.info("Stop requested. Will halt after current prompt.")
        st.rerun()

st.sidebar.subheader("🔑 Authentication")
st.sidebar.caption("Google Flow requires an authenticated Google Account. Click below to sign in once:")

if st.sidebar.button("🌐 Open Browser for Login", use_container_width=True):
    # Launch detached login process
    python_exe = sys.executable
    cmd = [python_exe, "main.py", "--login"]
    subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == "nt" else 0)
    st.sidebar.success("Browser opened! Please log in, then close the browser window.")

st.sidebar.subheader("🔄 Queue Operations")
if st.sidebar.button("🔁 Retry Failed Prompts", use_container_width=True):
    retried = pm.retry_failed()
    st.sidebar.success(f"Reset {retried} failed prompts to Pending.")
    st.rerun()

if st.sidebar.button("🗑️ Reset All to Pending", use_container_width=True):
    pm.reset_all()
    st.sidebar.success("All prompts reset to Pending.")
    st.rerun()

st.sidebar.subheader("➕ Add New Prompt")
with st.sidebar.form("add_prompt_form", clear_on_submit=True):
    new_prompt_text = st.text_area("Prompt Text", placeholder="Describe the scene in detail...")
    submitted = st.form_submit_button("Add to Queue")
    if submitted and new_prompt_text.strip():
        pm.add_prompt(new_prompt_text.strip())
        st.success("Prompt added to queue!")
        st.rerun()


# --- Main Tabs ---
tab_queue, tab_hunter, tab_gallery, tab_logs, tab_docs = st.tabs([
    "📋 Prompt Queue",
    "🔥 Viral Trend Hunter",
    "🎥 Video Gallery",
    "📜 Live Logs",
    "📖 Documentation & Setup"
])

with tab_hunter:
    st.subheader("🔥 Viral Car Trend Hunter")
    st.caption("Discover high-velocity trending cars across YouTube Shorts, Google Trends, and automotive communities, then automatically generate ready-to-run 10-shot video prompts.")

    col_h1, col_h2, col_h3 = st.columns([2, 1, 1])
    with col_h1:
        yt_api_input = st.text_input(
            "YouTube Data API Key (Optional)",
            value=YOUTUBE_API_KEY,
            type="password",
            help="Enables real-time queries for top-viewed YouTube Shorts. If left blank, Google Trends and the viral database are used automatically."
        )
    with col_h2:
        num_cars = st.slider("Number of cars to hunt", min_value=1, max_value=8, value=4)
    with col_h3:
        st.write("")
        st.write("")
        scan_btn = st.button("🔍 Scan Trends Now", type="primary", use_container_width=True)

    if "discovered_trends" not in st.session_state:
        st.session_state.discovered_trends = []

    if scan_btn:
        hunter = TrendHunter(youtube_api_key=yt_api_input.strip() or None)
        with st.spinner("Scanning YouTube Shorts, Google Trends, and viral automotive niches..."):
            st.session_state.discovered_trends = hunter.get_trending_cars(max_results=num_cars)
        st.success(f"Discovered {len(st.session_state.discovered_trends)} viral car trends!")

    if st.session_state.discovered_trends:
        col_act1, col_act2 = st.columns([3, 1])
        with col_act1:
            st.info("Review discovered trends below. You can change their color or add them directly to your generation queue.")
        with col_act2:
            if st.button("➕ Queue All Discovered Cars", use_container_width=True):
                hunter = TrendHunter()
                added = hunter.queue_trending_cars(st.session_state.discovered_trends, pm)
                st.success(f"Added {added} trending car prompts to the queue!")
                st.rerun()

        for idx, t in enumerate(st.session_state.discovered_trends):
            with st.container(border=True):
                col_c1, col_c2, col_c3, col_c4 = st.columns([3, 2, 2, 1])
                with col_c1:
                    st.markdown(f"### {t['car']}")
                    st.caption(f"Source: **{t['source']}** · Virality Score: **{t['score']}/100**")
                    st.write(t.get("details", ""))
                with col_c2:
                    current_color = t.get("color", LOCKED_COLORS[0])
                    col_idx = LOCKED_COLORS.index(current_color) if current_color in LOCKED_COLORS else 0
                    selected_color = st.selectbox(
                        "Chosen Color",
                        options=LOCKED_COLORS,
                        index=col_idx,
                        key=f"color_select_{idx}"
                    )
                    t["color"] = selected_color
                    t["prompt"] = format_short_video_prompt(t["car"], selected_color)
                with col_c3:
                    with st.expander("👁️ View Generated Prompt"):
                        st.caption(t["prompt"])
                with col_c4:
                    if st.button("➕ Queue", key=f"queue_btn_{idx}", use_container_width=True):
                        hunter = TrendHunter()
                        added = hunter.queue_trending_cars([t], pm)
                        if added:
                            st.success(f"Queued {t['car']}!")
                        else:
                            st.warning("Already in queue!")
                        st.rerun()

with tab_queue:
    st.subheader("Manage Prompts")
    if not pm.items:
        st.info("No prompts currently loaded. Add prompts in the sidebar or edit prompts.txt.")
    else:
        for idx, item in enumerate(pm.items):
            with st.container(border=True):
                col1, col2, col3, col4 = st.columns([5, 2, 2, 1])

                with col1:
                    st.markdown(f"**#{idx+1}** · `{item['id']}`")
                    st.write(item["prompt"])
                    if item.get("error"):
                        st.error(f"Error: {item['error']}")
                    if item.get("output_file"):
                        st.caption(f"📁 Output: `{item['output_file']}`")

                with col2:
                    status = item.get("status", "Pending")
                    if status == "Completed":
                        st.markdown('<span class="status-badge badge-completed">Completed</span>', unsafe_allow_html=True)
                    elif status == "Processing":
                        st.markdown('<span class="status-badge badge-processing">Processing...</span>', unsafe_allow_html=True)
                    elif status == "Failed":
                        st.markdown('<span class="status-badge badge-failed">Failed</span>', unsafe_allow_html=True)
                    else:
                        st.markdown('<span class="status-badge badge-pending">Pending</span>', unsafe_allow_html=True)

                with col3:
                    st.caption(f"Created: {item['created_at'][:19].replace('T', ' ')}")

                with col4:
                    if st.button("🗑️", key=f"del_{item['id']}", help="Delete prompt"):
                        pm.remove_prompt(item["id"])
                        st.rerun()

with tab_gallery:
    st.subheader("Downloaded Videos (output_videos/)")
    video_files = list(OUTPUT_DIR.glob("*.mp4")) + list(OUTPUT_DIR.glob("*.webm"))
    
    if not video_files:
        st.info("No completed videos downloaded yet. Completed videos will appear here automatically.")
    else:
        # Match videos to prompts
        video_to_prompt = {item.get("output_file"): item for item in pm.items if item.get("output_file")}

        cols = st.columns(2)
        for i, v_path in enumerate(reversed(video_files)):
            col = cols[i % 2]
            with col:
                with st.container(border=True):
                    st.markdown(f"**{v_path.name}**")
                    size_mb = v_path.stat().st_size / (1024 * 1024)
                    st.caption(f"Size: {size_mb:.2f} MB · Path: `{v_path}`")
                    st.video(str(v_path))
                    matched_item = video_to_prompt.get(v_path.name)
                    if matched_item:
                        st.caption(f"Prompt: *{matched_item['prompt']}*")

with tab_logs:
    st.subheader("Automation Activity Logs")
    col_l1, col_l2 = st.columns([1, 4])
    with col_l1:
        auto_refresh = st.checkbox("Auto-refresh (5s)", value=True)
    with col_l2:
        if st.button("🔄 Refresh Logs Now"):
            st.rerun()

    log_path = LOGS_DIR / "automation.log"
    if log_path.exists():
        with open(log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()[-150:]  # Last 150 lines
            log_content = "".join(lines)
            st.code(log_content or "No logs recorded yet.", language="log")
    else:
        st.info("No log file found yet. Logs will be recorded once automation starts.")

    if auto_refresh and is_active:
        time.sleep(5)
        st.rerun()

with tab_docs:
    st.subheader("System Architecture & User Guide")
    st.markdown(f"""
    ### Overview
    This automation coordinates Google Flow (`{FLOW_URL}`) using **Playwright with persistent browser profiling**.
    
    - **Session Persistence**: User profile & Google authentication are safely maintained in `{USER_DATA_DIR}` so you only log in once.
    - **Prompt Queue**: Loaded from `prompts.txt` and preserved with state in `prompts_state.json`.
    - **Safe Downloading**: Generated videos are captured directly and verified in `{OUTPUT_DIR}`.
    - **Resilience**: Adaptive selector fallback handles UI variations smoothly without crashing.

    ### Quick Start
    1. Click **'🌐 Open Browser for Login'** in the sidebar to sign into your Google account.
    2. Once logged in and viewing Google Flow, close the browser.
    3. Click **'▶️ Start Run'** to begin automated batch video generation!
    """)

