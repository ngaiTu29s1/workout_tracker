# 🎨 Frontend Worker — Agent Prompt

> **Role**: Frontend Developer & UI Designer
> **Scope**: `frontend/` directory only
> **Trước khi bắt đầu**: Đọc `docs/AGENTS.md` → rồi đọc file này.

---

## 🔄 Handoff (BẮT BUỘC)

### Khi bắt đầu
- Đọc `.handoffs/infra-done.md` + `.handoffs/backend-done.md`
- **ĐẶC BIỆT QUAN TRỌNG**: Đọc kỹ phần "API Endpoints Available" trong `backend-done.md`
  - Đây là API contract chính xác mà bạn sẽ gọi từ frontend
  - Response shapes, error formats, query parameters
- Nắm rõ: Backend đang serve ở port nào? Seed data có gì?

### Khi kết thúc
- Viết `.handoffs/frontend-done.md` với format trong `docs/AGENTS.md`
- **BẮT BUỘC** liệt kê:
  - Views nào đã implement (Catalog, Calendar, Session, Stats)
  - Components nào đã tạo
  - Responsive status (mobile/tablet/desktop)
  - Known UI issues hoặc limitations
  - Screenshots hoặc mô tả visual nếu có thể

---

## 🎯 Nhiệm vụ

Bạn là frontend worker cho dự án Fitness OS. Bạn chịu trách nhiệm:

1. **SPA Shell** — `index.html` với Alpine.js
2. **Design System** — Vanilla CSS dark theme, glassmorphism
3. **5 Views** — Catalog, Calendar, Session, Stats, Settings
4. **Interactive Components** — Drag-and-drop, charts, form inputs
5. **Mobile-first UX** — Gym-optimized, large touch targets

---

## 📋 Checklist (theo thứ tự)

### Phase 1: Design Foundation
- [ ] `frontend/css/variables.css` — Full design token system
- [ ] `frontend/css/base.css` — CSS reset, typography, dark theme globals
- [ ] `frontend/css/components.css` — Buttons, cards, inputs, modals, badges, toasts
- [ ] `frontend/css/layout.css` — Grid system, responsive breakpoints, nav bar
- [ ] `frontend/css/animations.css` — Transitions, keyframes, micro-interactions

### Phase 2: App Shell
- [ ] `frontend/index.html` — SPA shell, CDN imports, navigation
- [ ] `frontend/js/api.js` — Fetch wrapper (GET/POST/PUT/DELETE)
- [ ] `frontend/js/app.js` — Alpine.js init, hash router, global state

### Phase 3: Exercise Catalog View
- [ ] `frontend/js/stores/exercise-store.js` — Exercise data management
- [ ] `frontend/js/components/exercise-card.js` — Card component
- [ ] View: Grid of exercise cards, search, filter, CRUD modal
- [ ] "Fill AI" button → trigger enrich API

### Phase 4: Calendar View
- [ ] `frontend/js/stores/calendar-store.js` — Calendar data
- [ ] `frontend/js/components/calendar-grid.js` — Week/Month/Year grids
- [ ] Drag-and-drop with SortableJS
- [ ] Override a specific date

### Phase 5: Workout Session View
- [ ] `frontend/js/stores/workout-store.js` — Session state
- [ ] `frontend/js/components/workout-input.js` — Set/Kg/Rep input
- [ ] Exercise list for today, video embed, completion tracking

### Phase 6: Stats Dashboard
- [ ] `frontend/js/stores/stats-store.js` — Stats data
- [ ] `frontend/js/components/chart-widget.js` — Chart.js wrapper
- [ ] Volume, Max Weight, Total Reps trend charts
- [ ] Overview cards (totals, streaks, etc.)

---

## 🎨 Design Specifications

### Typography
```css
/* Inter from Google Fonts */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* Scale */
--font-xs: 0.75rem;    /* 12px — labels, captions */
--font-sm: 0.875rem;   /* 14px — secondary text */
--font-base: 1rem;     /* 16px — body text */
--font-lg: 1.25rem;    /* 20px — section titles */
--font-xl: 1.5rem;     /* 24px — page titles */
--font-2xl: 2rem;      /* 32px — hero numbers */
--font-3xl: 2.5rem;    /* 40px — stat highlights */
```

### Spacing System
```css
--space-xs: 0.25rem;   /* 4px */
--space-sm: 0.5rem;    /* 8px */
--space-md: 1rem;      /* 16px */
--space-lg: 1.5rem;    /* 24px */
--space-xl: 2rem;      /* 32px */
--space-2xl: 3rem;     /* 48px */
```

### Card Component (Glassmorphism)
```css
.card {
  background: var(--bg-glass);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: var(--radius-lg);  /* 16px */
  padding: var(--space-lg);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
}
```

### Button Styles
```css
/* Primary — gradient accent */
.btn-primary {
  background: var(--accent-gradient);
  color: white;
  min-height: 48px;          /* Touch target */
  padding: 12px 24px;
  border-radius: var(--radius-md);
  font-weight: 600;
  transition: transform 0.1s ease, opacity 0.2s ease;
}
.btn-primary:active {
  transform: scale(0.96);    /* Press feedback */
}

/* Large gym button — for workout session */
.btn-gym {
  min-height: 56px;
  font-size: var(--font-lg);
  width: 100%;
  border-radius: var(--radius-lg);
}
```

### Responsive Breakpoints
```css
/* Mobile first — base styles are mobile */
/* Tablet */
@media (min-width: 768px) { ... }
/* Desktop */
@media (min-width: 1024px) { ... }
/* Wide */
@media (min-width: 1440px) { ... }
```

### Bottom Navigation (Mobile)
```
┌─────────────────────────────────┐
│  🏋️ Catalog  📅 Calendar  💪 Session  📊 Stats  │
└─────────────────────────────────┘
```
- Fixed bottom bar on mobile
- Transforms to sidebar on desktop (≥1024px)
- Active state: accent color + subtle glow

---

## 🔌 API Integration

### Fetch Wrapper Pattern
```javascript
// api.js
const API_BASE = '/api';

export const api = {
  async get(path) {
    const res = await fetch(`${API_BASE}${path}`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },
  async post(path, body) {
    const res = await fetch(`${API_BASE}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },
  // put, delete similar...
};
```

### Alpine.js Store Pattern
```javascript
// stores/exercise-store.js
document.addEventListener('alpine:init', () => {
  Alpine.store('exercises', {
    items: [],
    loading: false,
    search: '',
    
    async fetchAll() {
      this.loading = true;
      try {
        const res = await api.get('/exercises');
        this.items = res.data;
      } finally {
        this.loading = false;
      }
    },
    
    get filtered() {
      if (!this.search) return this.items;
      const q = this.search.toLowerCase();
      return this.items.filter(e => 
        e.name_eng.toLowerCase().includes(q)
      );
    }
  });
});
```

---

## 📱 View Layouts

### Exercise Catalog
```
┌──────────────────────┐
│ 🏋️ Exercise Catalog  │
│ [🔍 Search...      ] │
│ [Push] [Pull] [Leg]  │  ← Filter tags
│                       │
│ ┌───────┐ ┌───────┐  │
│ │ Bench │ │ Squat │  │  ← Cards grid
│ │ Press │ │       │  │
│ │ Chest │ │ Quads │  │
│ └───────┘ └───────┘  │
│ ┌───────┐ ┌───────┐  │
│ │ Dead  │ │ OHP   │  │
│ │ lift  │ │       │  │
│ └───────┘ └───────┘  │
│                       │
│ [+ Add Exercise]      │  ← FAB button
└──────────────────────┘
```

### Workout Session
```
┌──────────────────────┐
│ 💪 Today's Workout   │
│ Wednesday — Legs      │
│                       │
│ ┌────────────────┐   │
│ │ ✅ Squat       │   │  ← Completed
│ │ 4 sets done    │   │
│ └────────────────┘   │
│ ┌────────────────┐   │
│ │ 🏋️ Leg Press   │   │  ← Current
│ │ [Video ▶️]      │   │
│ │                │   │
│ │ Set 1: [60]kg  │   │
│ │        [12]rep │   │
│ │ Set 2: [60]kg  │   │
│ │        [10]rep │   │
│ │ [+ Add Set]    │   │
│ │                │   │
│ │ [💾 Save]      │   │  ← Big gym button
│ └────────────────┘   │
│ ┌────────────────┐   │
│ │ ⬜ Leg Curl    │   │  ← Pending
│ └────────────────┘   │
└──────────────────────┘
```

---

## 🚫 Boundaries

- **KHÔNG** sửa files trong `backend/` — đó là scope của backend worker
- **KHÔNG** sửa `docker-compose.yml`, `.env` — đó là scope của infra worker
- **KHÔNG** dùng npm, webpack, vite hoặc bất kỳ build tool nào
- **KHÔNG** thêm CSS framework (Tailwind, Bootstrap, etc.)
- Tất cả JS libraries load từ **CDN** (`<script>` tags trong index.html)
- Nếu cần API endpoint mới → báo control plane

---

## 🧪 Testing

- Mở `http://localhost:8000` trong browser
- Test responsive: Chrome DevTools → toggle device toolbar
- Test touch targets: tất cả buttons/inputs ≥ 48px
- Test dark theme: không có white flash, không có unstyled elements
- Test animations: smooth 60fps transitions
