# 🏋️‍♂️ Fitness OS — The Ultimate Gym Companion

> **Reclaim your workout rhythm.** A premium, mobile-first web console designed to bring structure, speed, and sleek aesthetics to your training. Beautifully responsive, reactively bilingual, and built for lifters who value both style and substance.

---

## 💎 Premium Design Aesthetics

Fitness OS is engineered with a high-fidelity visual system designed to feel premium, immersive, and dark-mode-first:
*   **Glassmorphic Console**: Cards and panels utilize frosted-glass backdrops (`backdrop-filter`) with semi-transparent borders for a modern, futuristic vibe.
*   **Micro-Animations**: Experience smooth, responsive feedback with scale-down button presses, kinetic hover lifts, and fluid view transitions.
*   **Mobile-First Touch Grid**: High-contrast labels and generous **48px+ finger-friendly touch targets** ensure seamless logging mid-set with sweaty hands.
*   **Inter Typography**: Clean, high-readability fonts imported directly from Google Fonts for a professional dashboard experience.

---

## ✨ Elite Features

### 📅 Smart Weekly Planner
Plan your splits on a drag-and-drop interactive calendar. Effortlessly schedule your weekly routines (`Push`, `Pull`, `Legs`, etc.) or drag new templates into your calendar to dynamically override specific days.

### 🪄 Exercise Pool Catalog
Access a massive database of **1,324 exercises** complete with target muscle groups, required equipment, step-by-step instructions, and professional pro-tips. Quick-search the database with instant debouncing.

### ⚙️ Automated Progression & overloading
*   **Local Auto-fill**: Let the system automatically recommend exercises based on your active routine tag and historic performance, scheduling your progression path.
*   **AI Suggestions**: Leverage intelligent, automated routing to autofill and translate guidelines, pro-tips, and muscle group tagging.

### 🇻🇳 🇬🇧 Reactively Bilingual
Switch the entire user interface, instructions, pro-tips, and analytical metrics between **Vietnamese** and **English** reactively. Zero page reloads required.

### 💾 Local Cache Optimizer
Your custom exercises and personalized edits are secured in a persistent local cache. Rebuild and reset container data at will without ever losing your custom modifications.

### 📊 Rich Analytical Insights
Visualize your progression trends over time with elegant, gradient-filled area charts tracking workout volumes, maximum weights, and repetition counts.

---

## 📱 The Console Layout

*   **Catalog**: Manage, create, and browse your personal exercises and reference pool.
*   **Calendar**: Map out your training week with a modular drag-and-drop palette.
*   **Workout Session**: Input sets, repetitions, and weights reactively. Highlights recommended exercises matching your active split.
*   **Analytics**: Review volume history and performance metrics with detailed interactive charts.

---

## 🛠️ Developer Tooling

| Tool | Purpose | Config |
|---|---|---|
| **Ruff** | Linter + formatter (Python) | `pyproject.toml` → `[tool.ruff]` |
| **pre-commit** | Git hooks: Ruff + hygiene checks | `.pre-commit-config.yaml` |
| **pytest** | Backend test suite | `backend/pytest.ini` (asyncio) |

```sh
# One-time: install dev deps + hooks locally
pip install -r backend/requirements-dev.txt
pre-commit install

# Run Ruff without a local install (uses the Docker image)
docker compose run --rm --no-deps --entrypoint sh fitness-backend -c \
  'pip install -q ruff && ruff check backend && ruff format --check backend'

# Run the test suite (needs a live DB)
docker compose run --rm -e TESTING=True --entrypoint sh fitness-backend -c \
  'env PYTHONPATH=. pytest backend/tests/ -v'
```

> Vietnamese search helpers (`remove_vietnamese_tones`, query expansion) live in `backend/app/services/search_config.py`, covered by `backend/tests/test_pool_search.py`. See `docs/tooling-setup.md` for details.
