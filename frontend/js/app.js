// Import stores to execute and register them with Alpine
import './stores/exercise-store.js';
import './stores/calendar-store.js';
import './stores/workout-store.js';
import './stores/stats-store.js';
import './stores/pool-store.js';

document.addEventListener('alpine:init', () => {
  // Main app controller
  Alpine.data('app', () => ({
    activeView: 'session',
    toasts: [],
    lang: 'vi',
    
    toggleLang() {
      this.lang = this.lang === 'vi' ? 'en' : 'vi';
      this.addToast(`Switched language to ${this.lang.toUpperCase()}`, 'success');
    },
    
    getRoutineTagClass(tag) {
      const t = (tag || '').toLowerCase().replace(' ', '_');
      if (t === 'push') return 'badge--push';
      if (t === 'pull') return 'badge--pull';
      if (t === 'legs' || t === 'leg') return 'badge--legs';
      if (t === 'upper_body') return 'badge--upper-body';
      if (t === 'lower_body') return 'badge--lower-body';
      if (t === 'core') return 'badge--core';
      if (t === 'cardio') return 'badge--cardio';
      return 'badge--rest';
    },
    
    init() {
      // 1. Setup hash routing
      const handleRoute = () => {
        const hash = window.location.hash.replace('#', '') || 'session';
        const allowedViews = ['catalog', 'calendar', 'session', 'stats'];
        const view = allowedViews.includes(hash) ? hash : 'session';
        
        this.activeView = view;
        
        // Push hash to URL if it's empty
        if (!window.location.hash) {
          window.history.replaceState(null, null, `#${view}`);
        }
        
        // Trigger data fetch for the active view
        this.fetchDataForView(view);
      };
      
      window.addEventListener('hashchange', handleRoute);
      
      // 2. Global Toast notification listener
      window.addEventListener('toast', (e) => {
        this.addToast(e.detail.message, e.detail.type || 'info');
      });
      
      // 3. Run routing on page load
      handleRoute();
    },
    
    fetchDataForView(view) {
      if (view === 'catalog') {
        Alpine.store('exercises').fetchAll();
      } else if (view === 'calendar') {
        Alpine.store('calendar').fetchCalendar();
        Alpine.store('calendar').fetchPresets();
      } else if (view === 'session') {
        // Workout session depends on catalog data for adding custom exercise
        Alpine.store('exercises').fetchAll().then(() => {
          Alpine.store('workout').fetchSession();
        });
      } else if (view === 'stats') {
        // Fetch stats overview dashboard data
        Alpine.store('stats').fetchOverview();
        
        // Load exercise stats for trend chart
        const exStore = Alpine.store('exercises');
        const statsStore = Alpine.store('stats');
        
        const loadTrend = () => {
          if (exStore.items.length > 0) {
            // Pick first exercise if none is selected
            const activeId = statsStore.selectedExerciseId || exStore.items[0].id;
            statsStore.fetchExerciseStats(activeId);
          }
        };

        if (exStore.items.length === 0) {
          exStore.fetchAll().then(loadTrend);
        } else {
          loadTrend();
        }
      }
    },
    
    addToast(message, type) {
      const id = Date.now() + Math.random();
      this.toasts.push({ id, message, type });
      
      // Remove toast after animation completes
      setTimeout(() => {
        this.toasts = this.toasts.filter(t => t.id !== id);
      }, 3000);
    }
  }));
});

// Dynamically load Alpine plugins and Alpine itself to avoid race conditions with ESM imports
const loadScript = (src) => {
  return new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = src;
    script.defer = true;
    script.onload = resolve;
    script.onerror = reject;
    document.head.appendChild(script);
  });
};

// Load collapse plugin first, then Alpine
loadScript('https://unpkg.com/@alpinejs/collapse@3.x.x/dist/cdn.min.js')
  .then(() => loadScript('https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js'))
  .catch(err => console.error('Failed to load Alpine.js', err));
