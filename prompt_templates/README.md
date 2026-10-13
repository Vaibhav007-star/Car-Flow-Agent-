# 📂 Prompt Templates & Multi-Niche Library

This folder serves as the central repository for creative video prompt systems, styles, and niches used by the Google Flow Video Automation Agent.

---

## 🏎️ Active Niches

| Template | Niche Name | Visual Theme | Palette / Materials | Duration | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| [`diecast_car_assembly.md`](diecast_car_assembly.md) | **Diecast Miniature Assembly** | Spotless white studio desk, macro model kit parts snapping together | 10 Locked Colors (Pearl White, Racing Red, etc.) | 8-10s | Active |
| [`wooden_car_carving.md`](wooden_car_carving.md) | **Artisan Wooden Car Carving** | Warm cozy workshop, flat wooden workbench, hands-only chisel & sanding ASMR | 10 Locked Woods (Rich Walnut, Light Maple, etc.) | 8s (Hard limit) | Active |
| [`model_kit_car_assembly.md`](model_kit_car_assembly.md) | **Model-Kit Car Unboxing & Assembly** | Hobbyist cutting mat, branded box unboxing, tray reveal, rapid tool bolt & display | 10 Locked Colors + Specific Supercars | 8s (Hard limit) | **New** |

---

## 🌲 Adding New Niches in the Future
To add a new niche in the future:
1. Create a new markdown file in this folder (e.g. `cyberpunk_car_wrap.md`, `lego_supercar_speedbuild.md`).
2. Define the **Locked Shot Structure** (timecodes and exact actions).
3. Specify the **Consistency Block** and **Material/Color Options**.
4. Register the template format into `trend_hunter.py` and `history_manager.py` to enable automated generation and anti-repetition tracking.

