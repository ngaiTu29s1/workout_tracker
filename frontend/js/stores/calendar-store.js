import { api } from '../api.js';

// Format Date object to local YYYY-MM-DD string
export function formatDateLocal(date) {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}
window.formatDateLocal = formatDateLocal;

document.addEventListener('alpine:init', () => {
  Alpine.store('calendar', {
    days: [],
    loading: false,
    viewType: 'week', // 'week' or 'month'
    currentDate: new Date(),
    presets: {}, // day_of_week -> routine_tag
    refreshCounter: 0, // Used as part of template keys to force DOM clean rebuilds on refreshes
    formatDateLocal(date) {
      return formatDateLocal(date);
    },
    
    // Preset Editing Modal state
    presetsModalOpen: false,
    editingPresets: [], // array of { day_of_week, routine_tag }

    async fetchPresets() {
      try {
        const res = await api.get('/presets');
        // Res.data is list of { day_of_week, routine_tag }
        const map = {};
        res.data.forEach(p => {
          map[p.day_of_week] = p.routine_tag;
        });
        this.presets = map;
        this.editingPresets = JSON.parse(JSON.stringify(res.data)); // clone
      } catch (err) {
        console.error('Failed to fetch presets', err);
      }
    },

    async openPresetsModal() {
      await this.fetchPresets();
      this.presetsModalOpen = true;
    },

    async savePresets() {
      try {
        await api.put('/presets', { presets: this.editingPresets });
        window.dispatchEvent(new CustomEvent('toast', {
          detail: { message: 'Presets updated successfully', type: 'success' }
        }));
        this.presetsModalOpen = false;
        await this.fetchCalendar();
        
        // Refresh workout session if routine changed
        Alpine.store('workout').refreshTodaySession();
      } catch (err) {
        window.dispatchEvent(new CustomEvent('toast', {
          detail: { message: err.message || 'Failed to save presets', type: 'error' }
        }));
      }
    },

    async fetchCalendar() {
      this.loading = true;
      try {
        let start, end;
        const baseDate = new Date(this.currentDate);

        if (this.viewType === 'week') {
          // Align to start on Monday
          const day = baseDate.getDay();
          const diff = baseDate.getDate() - day + (day === 0 ? -6 : 1);
          const monday = new Date(baseDate.setDate(diff));
          const sunday = new Date(monday);
          sunday.setDate(monday.getDate() + 6);
          
          start = formatDateLocal(monday);
          end = formatDateLocal(sunday);
        } else {
          // Month view: Fetch 1st of month to last of month
          const firstDay = new Date(baseDate.getFullYear(), baseDate.getMonth(), 1);
          const lastDay = new Date(baseDate.getFullYear(), baseDate.getMonth() + 1, 0);
          
          // Pad to start of week (Monday) and end of week (Sunday)
          const startDayOfWeek = firstDay.getDay(); // 0 is Sunday
          const paddingStart = startDayOfWeek === 0 ? 6 : startDayOfWeek - 1;
          const startDate = new Date(firstDay);
          startDate.setDate(firstDay.getDate() - paddingStart);

          const endDayOfWeek = lastDay.getDay();
          const paddingEnd = endDayOfWeek === 0 ? 0 : 7 - endDayOfWeek;
          const endDate = new Date(lastDay);
          endDate.setDate(lastDay.getDate() + paddingEnd);

          start = formatDateLocal(startDate);
          end = formatDateLocal(endDate);
        }

        const res = await api.get(`/calendar?start=${start}&end=${end}`);
        this.days = res.data || [];
        this.refreshCounter++;
      } catch (err) {
        window.dispatchEvent(new CustomEvent('toast', {
          detail: { message: err.message || 'Failed to fetch calendar', type: 'error' }
        }));
      } finally {
        this.loading = false;
      }
    },

    next() {
      const nextDate = new Date(this.currentDate);
      if (this.viewType === 'week') {
        nextDate.setDate(nextDate.getDate() + 7);
      } else {
        nextDate.setMonth(nextDate.getMonth() + 1);
      }
      this.currentDate = nextDate;
      this.fetchCalendar();
    },

    prev() {
      const prevDate = new Date(this.currentDate);
      if (this.viewType === 'week') {
        prevDate.setDate(prevDate.getDate() - 7);
      } else {
        prevDate.setMonth(prevDate.getMonth() - 1);
      }
      this.currentDate = prevDate;
      this.fetchCalendar();
    },

    today() {
      this.currentDate = new Date();
      this.fetchCalendar();
    },

    async setOverride(dateStr, routineTag, skipRefresh = false) {
      try {
        if (!skipRefresh) {
          // Optimistic UI update for single-day drops
          this.days = this.days.map(d => {
            if (d.date === dateStr) {
              const targetTag = routineTag || d.preset_tag;
              return { ...d, routine_tag: targetTag, is_override: routineTag !== null };
            }
            return d;
          });
          this.refreshCounter++;
        }

        await api.post('/calendar/override', {
          workout_date: dateStr,
          routine_tag: routineTag || null // null reverts to preset
        });
        
        if (!skipRefresh) {
          // Refresh calendar list
          await this.fetchCalendar();
          
          // If this date is today or currently loaded session date, refresh workout session
          const workoutStore = Alpine.store('workout');
          if (workoutStore.selectedDate === dateStr) {
            await workoutStore.fetchSession();
          }

          window.dispatchEvent(new CustomEvent('toast', {
            detail: { message: 'Routine updated successfully', type: 'success' }
          }));
        }
      } catch (err) {
        window.dispatchEvent(new CustomEvent('toast', {
          detail: { message: err.message || 'Failed to override routine', type: 'error' }
        }));
      }
    },

    async moveOverride(sourceDate, targetDate, routineTag) {
      try {
        // Optimistic UI update for both source and target days
        this.days = this.days.map(d => {
          if (d.date === sourceDate) {
            return { ...d, routine_tag: d.preset_tag, is_override: false };
          }
          if (d.date === targetDate) {
            return { ...d, routine_tag: routineTag, is_override: true };
          }
          return d;
        });
        this.refreshCounter++;

        // Remove override from source date (skip refresh)
        await this.setOverride(sourceDate, null, true);
        // Set override on target date (do refresh)
        await this.setOverride(targetDate, routineTag, false);
      } catch (err) {
        console.error('Failed to move override', err);
      }
    },

    get monthYearLabel() {
      const months = [
        'January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December'
      ];
      return `${months[this.currentDate.getMonth()]} ${this.currentDate.getFullYear()}`;
    },

    get weekRangeLabel() {
      if (this.days.length === 0) return '';
      const start = new Date(this.days[0].date);
      const end = new Date(this.days[this.days.length - 1].date);
      
      const formatOption = { month: 'short', day: 'numeric' };
      return `${start.toLocaleDateString('en-US', formatOption)} - ${end.toLocaleDateString('en-US', formatOption)}`;
    }
  });
});
