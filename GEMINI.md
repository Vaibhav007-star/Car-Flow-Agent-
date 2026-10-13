# 🏎️ FLOW AGENT — AUTONOMOUS YOUTUBE SHORTS RULES & OPERATIONAL SPECIFICATION

These instructions are persistent rules for all video generation, trend hunting, prompt synthesis, and YouTube publishing tasks in this workspace.

---

## 1. ⏱️ HARD DURATION CONSTRAINT: EXACTLY 8.0 SECONDS
- **Every prompt generated MUST strictly target 8.0 seconds** in Google Flow (Veo).
- **Structure**: Always use the locked **4-Beat 2.0-Second Architecture**:
  - `[0.0s - 2.0s]` **Beat 1 (The Hook)**: High-impact action hook (e.g. hobby nippers sprue cut, button trigger, bolt-cutter snip, impact-driver whirr).
  - `[2.0s - 4.0s]` **Beat 2 (Core Assembly/Carving)**: Primary chassis, body sculpting, or transit film peel.
  - `[4.0s - 6.0s]` **Beat 3 (Detail & Interior Fit)**: Fine tools, wheel torque, interior plastic peel, or key turn.
  - `[6.0s - 8.0s]` **Beat 4 (Hero Reveal & LED Ignition)**: Headlights/taillights flare to life, exhaust sound/flame pop, holding steady hero shot.
- **Aspect Ratio**: Always Vertical 9:16 (`720x1280` or `1080x1920`).
- **Audio**: Close-mic diegetic ASMR only (mechanical clicks, ratchets, carving scrapes, vinyl hisses, startup chimes). No background music, no voiceover.
- **Negative Constraints**: Always include: `No face, no visible person, no text, no captions, no logos, no watermark, no extra fingers, no deformed hands, no cartoon look, no morphing or melting shapes, no camera jitter, no background changing.`

---

## 2. 🗄️ MANDATORY USE OF PROMPT DATABASE & NICHES
All prompts MUST be synthesized using the established, tested template specifications in `prompt_templates/`:

| Niche | Template | Setting | Signature Hook |
| :--- | :--- | :--- | :--- |
| **Diecast Assembly** | [`diecast_car_assembly.md`](prompt_templates/diecast_car_assembly.md) | Spotless white cyclorama studio | Grille emblem snap, carbon vents click, LED flare |
| **Wooden Carving** | [`wooden_car_carving.md`](prompt_templates/wooden_car_carving.md) | Cozy workshop oak workbench | Chisel cuts wood curls, sanding glow, taillight hum |
| **Model-Kit Build** | [`model_kit_car_assembly.md`](prompt_templates/model_kit_car_assembly.md) | Dark green grid cutting mat | Precision nippers snip plastic sprue runners, tray build |
| **Factory Film Peel** | [`peel_and_delivery_car_assembly.md`](prompt_templates/peel_and_delivery_car_assembly.md) | Rotating turntable studio | Protective film peel from hood/roof, push-to-start |
| **Styrofoam Craft** | [`foam_car_sculpting.md`](prompt_templates/foam_car_sculpting.md) | Light oak workbench | Razor foam slice, sandpaper friction, brush sweep |
| **4x4 Overlander** | [`offroad_overlander_makeover.md`](prompt_templates/offroad_overlander_makeover.md) | Bright cyclorama garage | Pneumatic impact drivers bolt bull-bar & lift kit |
| **Kinetic Gadget** | [`kinetic_gadget_transformation.md`](prompt_templates/kinetic_gadget_transformation.md) | Living room granite table | Push-button spring burst unfolds 1:18 scale model |
| **Container Unboxing**| [`container_unboxing_peel.md`](prompt_templates/container_unboxing_peel.md) | Dark walnut workbench | Bolt cutters snip seal, tray slide, film peel, exhaust flame |

---

## 3. 🎯 AUDIENCE & MARKET-DRIVEN NICHE SELECTION
- Always use `trend_hunter.py` with channel performance data (`--audience`) and Google Trends to discover the hottest car model and niche.
- **Anti-Repetition Rule**: Never repeat a car model in the same color/material within the same niche. Verify against `generation_history.json`.
- Rotate through top-performing niches according to audience retention velocity.

---

## 4. 📅 SCHEDULING & PUBLISHING DISCIPLINE
- **Daily Peak Slots**: Always schedule to the channel's 2 prime viewer velocity windows:
  - **Slot A**: **1:30 PM IST** (`08:00:00Z`)
  - **Slot B**: **8:00 PM IST** (`14:30:00Z`)
- **Privacy**: Always `private` with ISO 8601 `publishAt` timestamp.
- **Thumbnails**: Always score frames using `thumbnail_generator.py` and upload the highest engagement score hero frame (favoring 6.5s-7.6s hero reveals).
- **SEO**: Clean all hashtags from YouTube Data API tags (API requirement: no `#` symbols in tag array). Always include `#Shorts` in the title.
- **Disk Cleanliness**: Keep local storage lean; once a video is uploaded and scheduled, raw `.mp4` files can be cleaned from `output_videos/` since master records are preserved in `prompts_state.json` and `generation_history.json`.
