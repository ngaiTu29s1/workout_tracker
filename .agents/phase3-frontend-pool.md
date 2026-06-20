# 🎨 Phase 3: Frontend — Pool Catalog UX

> **Role**: Frontend Developer
> **Scope**: Catalog view overhaul, pool search UI, exercise cards with images
> **Trước khi bắt đầu**: Đọc `docs/AGENTS.md` → `.handoffs/phase2-done.md` → đọc file này.

---

## 🎯 Mục tiêu

Redesign Catalog view để support Pool/Personal architecture:
- **My Exercises**: Grid cards với images/gifs từ pool
- **Add from Pool**: Search modal tìm trong 1324 bài → 1-click add
- **Manual Create**: Fallback khi pool không có

---

## 🏗️ API Endpoints (từ Phase 2)

```
GET  /api/pool/search?q=bench+press&limit=20
     → { data: [{ id, pool_id, name, category, equipment, target, muscle_group, image_path, gif_path }] }

GET  /api/pool/{id}
     → { data: { ...full detail incl. instructions_en, instructions_vi, secondary_muscles } }

POST /api/exercises/add-from-pool
     Body: { pool_id: 123, tags: ["push", "chest"] }
     → { data: { ...created personal exercise } }

GET  /api/exercises                    ← existing, returns personal only
POST /api/exercises                    ← existing, manual create
```

### Media URLs
```
/pool/images/0001-xxx.jpg     → JPG thumbnail
/pool/videos/0001-xxx.gif     → GIF demo animation
```

---

## 📋 Tasks

### 1. New Store: `pool-store.js`

**File**: `frontend/js/stores/pool-store.js`

```javascript
Alpine.store('pool', {
    searchQuery: '',
    searchResults: [],
    searching: false,
    selectedExercise: null,   // pool exercise detail for preview
    modalOpen: false,
    
    async search(query) {
        if (query.length < 2) { this.searchResults = []; return; }
        this.searching = true;
        const res = await api.get(`/pool/search?q=${encodeURIComponent(query)}&limit=20`);
        this.searchResults = res.data || [];
        this.searching = false;
    },
    
    async getDetail(id) {
        const res = await api.get(`/pool/${id}`);
        this.selectedExercise = res.data;
    },
    
    async addToPersonal(poolId, tags = []) {
        const res = await api.post('/exercises/add-from-pool', { pool_id: poolId, tags });
        // Refresh personal exercises
        Alpine.store('exercises').fetchAll();
        this.modalOpen = false;
        // Toast
        window.dispatchEvent(new CustomEvent('toast', {
            detail: { message: 'Exercise added!', type: 'success' }
        }));
    },
    
    getImageUrl(exercise) {
        // For pool search results: use image_path
        if (exercise.image_path) return `/pool/${exercise.image_path}`;
        // For personal exercises: use image_url (already formatted)
        if (exercise.image_url) return exercise.image_url;
        return null;
    },
    
    getGifUrl(exercise) {
        if (exercise.gif_path) return `/pool/${exercise.gif_path}`;
        if (exercise.video_url) return exercise.video_url;
        return null;
    }
});
```

### 2. Modify Catalog View — `index.html`

#### My Exercises Section

```html
<!-- Exercise cards with images -->
<div class="exercise-grid">
  <template x-for="ex in $store.exercises.filteredItems" :key="ex.id">
    <div class="exercise-card" @click="$store.exercises.openEditModal(ex)">
      <!-- Thumbnail -->
      <div class="exercise-card__image">
        <img :src="ex.image_url || '/pool/' + (ex.pool_image || '')" 
             :alt="ex.name_eng"
             loading="lazy"
             onerror="this.style.display='none'">
        <!-- Fallback: muscle icon or initial -->
        <div class="exercise-card__placeholder" x-show="!ex.image_url && !ex.pool_image">
          <span x-text="ex.name_eng?.charAt(0)?.toUpperCase()"></span>
        </div>
      </div>
      
      <!-- Info -->
      <div class="exercise-card__info">
        <h4 class="exercise-card__name" x-text="ex.name_eng"></h4>
        <p class="exercise-card__muscle" x-text="ex.primary_muscle || 'Unset'"></p>
        <div class="exercise-card__tags">
          <template x-for="tag in (ex.tags || []).slice(0, 3)">
            <span class="chip chip--sm" :class="'chip--' + tag" x-text="tag"></span>
          </template>
        </div>
      </div>
    </div>
  </template>
</div>
```

#### Add Button → Opens Pool Search Modal

```html
<button class="btn btn--primary" @click="$store.pool.modalOpen = true">
  + Add Exercise
</button>
```

### 3. Pool Search Modal

```html
<div class="modal-overlay" x-show="$store.pool.modalOpen" x-transition>
  <div class="modal pool-search-modal">
    <div class="modal__header">
      <h3>Browse Exercise Pool</h3>
      <button @click="$store.pool.modalOpen = false">✕</button>
    </div>
    
    <!-- Search Input -->
    <div class="modal__search">
      <input type="search" 
             placeholder="Search 1,300+ exercises..." 
             x-model="$store.pool.searchQuery"
             @input.debounce.300ms="$store.pool.search($store.pool.searchQuery)"
             autofocus>
    </div>
    
    <!-- Results -->
    <div class="pool-results">
      <template x-for="ex in $store.pool.searchResults" :key="ex.id">
        <div class="pool-result-card">
          <img class="pool-result-card__thumb" 
               :src="'/pool/' + ex.image_path" 
               :alt="ex.name"
               loading="lazy">
          <div class="pool-result-card__info">
            <strong x-text="ex.name"></strong>
            <span class="text-muted" x-text="ex.muscle_group + ' · ' + ex.equipment"></span>
          </div>
          <button class="btn btn--sm btn--accent" 
                  @click="$store.pool.addToPersonal(ex.id, [])">
            + Add
          </button>
        </div>
      </template>
      
      <!-- Empty state -->
      <div x-show="$store.pool.searchQuery.length >= 2 && $store.pool.searchResults.length === 0 && !$store.pool.searching"
           class="pool-empty">
        <p>No results found.</p>
        <button class="btn btn--outline" @click="$store.exercises.openCreateModal(); $store.pool.modalOpen = false">
          Create manually instead
        </button>
      </div>
    </div>
  </div>
</div>
```

### 4. Exercise Detail — Show GIF

Khi user tap vào exercise card (trong Catalog hoặc Session), hiển thị GIF demo:

```html
<!-- In edit modal / detail view -->
<div class="exercise-detail__media" x-show="editingExercise?.video_url">
  <img :src="editingExercise?.video_url" 
       class="exercise-gif"
       alt="Exercise demonstration">
</div>
```

### 5. CSS Updates

#### `frontend/css/views.css` — Exercise Grid

```css
.exercise-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: var(--space-3);
}

.exercise-card {
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  overflow: hidden;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}

.exercise-card:active {
  transform: scale(0.97);
}

.exercise-card__image {
  aspect-ratio: 1;
  overflow: hidden;
  background: var(--bg-glass);
}

.exercise-card__image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.exercise-card__info {
  padding: var(--space-2) var(--space-3);
}
```

#### `frontend/css/components.css` — Pool Search Modal

```css
.pool-search-modal {
  max-height: 80vh;
  display: flex;
  flex-direction: column;
}

.pool-results {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-3);
}

.pool-result-card {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3);
  border-radius: var(--radius-md);
  background: var(--bg-glass);
  margin-bottom: var(--space-2);
}

.pool-result-card__thumb {
  width: 56px;
  height: 56px;
  border-radius: var(--radius-sm);
  object-fit: cover;
}
```

### 6. Load Pool Store

**File**: `frontend/index.html` — thêm script tag:

```html
<script type="module" src="js/stores/pool-store.js"></script>
```

---

## 🎨 Design Guidelines

1. **Exercise cards**: Nổi bật hình ảnh, tên ở dưới, tag chips nhỏ
2. **Pool search modal**: Full-screen trên mobile, centered dialog trên desktop
3. **GIF demo**: Hiển thị khi tap vào card — giống xem preview
4. **Empty state**: Khi chưa có personal exercises → "Browse the exercise pool to get started"
5. **Loading states**: Skeleton cards khi loading, spinner khi searching
6. **Responsive**: 2 cột mobile, 3-4 cột tablet, 5+ cột desktop

---

## ⚠️ Lưu ý quan trọng

1. **KHÔNG sửa BE code** — chỉ FE
2. **Alpine.js patterns**: Dùng `x-model`, `x-for`, `@click`, `$store`
3. **Vanilla CSS only** — không Tailwind
4. **Dark mode**: Tất cả UI phải theo dark theme hiện tại
5. **Touch targets**: Min 48px cho buttons/interactive elements
6. **Image fallback**: Nếu image load fail → hiển thị chữ cái đầu hoặc icon placeholder
7. **Debounce search**: 300ms debounce trên search input

---

## 🔄 Handoff

Viết `.handoffs/phase3-done.md` với:
- Screenshots/mô tả UI mới
- Components đã tạo/sửa
- Store methods available
- Known issues
- Suggestions cho cải tiến sau
