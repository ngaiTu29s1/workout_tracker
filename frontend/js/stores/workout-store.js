import { api } from '../api.js';
import { formatDateLocal } from './calendar-store.js';

document.addEventListener('alpine:init', () => {
  Alpine.store('workout', {
    selectedDate: formatDateLocal(new Date()),
    routineTag: 'rest', // routine tag for the selected date
    logs: [], // actual saved logs from API
    sessionExercises: [], // combined logs + recommended exercises
    loading: false,
    activeExerciseId: null, // ID of expanded exercise card
    
    // Quick search list for adding custom exercise to today's workout
    exerciseSearchQuery: '',
    exerciseSearchOpen: false,

    async refreshTodaySession() {
      // Safely called to refresh the current list
      await this.fetchSession();
    },

    async fetchSession() {
      this.loading = true;
      try {
        // 1. Get logs for selected date
        const logsRes = await api.get(`/workouts?date=${this.selectedDate}`);
        this.logs = logsRes.data || [];

        // 2. Fetch the calendar event for this specific date to get today's routine tag
        const calRes = await api.get(`/calendar?start=${this.selectedDate}&end=${this.selectedDate}`);
        const todayEvent = calRes.data && calRes.data[0];
        const routineTag = todayEvent ? todayEvent.routine_tag : 'rest';
        this.routineTag = routineTag;

        // 3. Make sure exercise master items are loaded
        const exerciseStore = Alpine.store('exercises');
        if (exerciseStore.items.length === 0) {
          await exerciseStore.fetchAll();
        }
        const masterExercises = exerciseStore.items;

        // 4. Combine logs and recommendations
        const combined = [];
        
        // Add all exercises that already have logs
        this.logs.forEach(log => {
          if (!log.exercise) return;
          combined.push({
            exercise: log.exercise,
            logId: log.id,
            is_completed: log.is_completed,
            tracking_data: JSON.parse(JSON.stringify(log.tracking_data)), // clone
            isLogged: true,
            isRecommended: this.matchesRoutine(log.exercise, routineTag)
          });
        });

        // Add recommended exercises for this routine tag, if not already logged
        if (routineTag && routineTag.toLowerCase() !== 'rest') {
          const routineLower = routineTag.toLowerCase();
          masterExercises.forEach(ex => {
            const isAlreadyAdded = combined.some(item => item.exercise.id === ex.id);
            if (!isAlreadyAdded && this.matchesRoutine(ex, routineLower)) {
              combined.push({
                exercise: ex,
                logId: null,
                is_completed: false,
                tracking_data: [this.getDefaultSet(ex.tracking_type)],
                isLogged: false,
                isRecommended: true
              });
            }
          });
        }

        this.sessionExercises = combined;
        
        // Auto-expand the first uncompleted or logged exercise if none is active
        if (this.sessionExercises.length > 0 && !this.activeExerciseId) {
          const firstUncompleted = this.sessionExercises.find(item => !item.is_completed);
          if (firstUncompleted) {
            this.activeExerciseId = firstUncompleted.exercise.id;
          } else {
            this.activeExerciseId = this.sessionExercises[0].exercise.id;
          }
        }
      } catch (err) {
        window.dispatchEvent(new CustomEvent('toast', {
          detail: { message: err.message || 'Failed to load workout session', type: 'error' }
        }));
      } finally {
        this.loading = false;
      }
    },

    matchesRoutine(ex, tag) {
      if (!tag || tag === 'rest') return false;
      const lowerTag = tag.toLowerCase();
      
      const inTags = ex.tags && ex.tags.some(t => t.toLowerCase() === lowerTag);
      const isPrimary = ex.primary_muscle && ex.primary_muscle.toLowerCase() === lowerTag;
      const isSecondary = ex.secondary_muscle && ex.secondary_muscle.some(sm => sm.toLowerCase() === lowerTag);
      
      // Special mapping for common presets: pull -> back/biceps, push -> chest/shoulders/triceps, leg -> quads/hamstrings/calves/glutes
      if (lowerTag === 'push') {
        const chestShoulderTricep = ['chest', 'shoulders', 'triceps', 'push'];
        return inTags || 
          (ex.primary_muscle && chestShoulderTricep.includes(ex.primary_muscle.toLowerCase()));
      }
      
      if (lowerTag === 'pull') {
        const backBicepForearm = ['back', 'biceps', 'forearms', 'pull'];
        return inTags || 
          (ex.primary_muscle && backBicepForearm.includes(ex.primary_muscle.toLowerCase()));
      }

      if (lowerTag === 'leg' || lowerTag === 'legs') {
        const legsMuscles = ['quads', 'hamstrings', 'calves', 'glutes', 'leg', 'legs'];
        return inTags || 
          (ex.primary_muscle && legsMuscles.includes(ex.primary_muscle.toLowerCase()));
      }

      return inTags || isPrimary || isSecondary;
    },

    getDefaultSet(trackingType) {
      return {
        set: 1,
        kg: trackingType === 'TIME' ? null : 0,
        rep: trackingType === 'TIME' ? null : 0,
        time_seconds: trackingType === 'TIME' ? 0 : null
      };
    },

    changeDate(offset) {
      const date = new Date(this.selectedDate);
      date.setDate(date.getDate() + offset);
      this.selectedDate = formatDateLocal(date);
      this.activeExerciseId = null;
      this.fetchSession();
    },

    addSet(sessionItem) {
      const tracking = sessionItem.tracking_data;
      const nextSetNum = tracking.length + 1;
      const lastSet = tracking[tracking.length - 1] || {};
      
      tracking.push({
        set: nextSetNum,
        kg: lastSet.kg !== undefined ? lastSet.kg : 0,
        rep: lastSet.rep !== undefined ? lastSet.rep : 0,
        time_seconds: lastSet.time_seconds !== undefined ? lastSet.time_seconds : 0
      });
    },

    removeSet(sessionItem, index) {
      const tracking = sessionItem.tracking_data;
      if (tracking.length <= 1) return; // Keep at least one set
      tracking.splice(index, 1);
      // Re-index sets
      tracking.forEach((s, idx) => s.set = idx + 1);
    },

    async saveLog(sessionItem) {
      // Sanitize inputs
      const tracking_data = sessionItem.tracking_data.map(s => {
        const cleanSet = { set: parseInt(s.set) };
        if (s.kg !== null && s.kg !== undefined) cleanSet.kg = parseFloat(s.kg) || 0;
        if (s.rep !== null && s.rep !== undefined) cleanSet.rep = parseInt(s.rep) || 0;
        if (s.time_seconds !== null && s.time_seconds !== undefined) cleanSet.time_seconds = parseInt(s.time_seconds) || 0;
        return cleanSet;
      });

      const payload = {
        workout_date: this.selectedDate,
        exercise_id: sessionItem.exercise.id,
        tracking_data,
        is_completed: sessionItem.is_completed
      };

      try {
        const res = await api.post('/workouts', payload);
        const log = res.data;
        
        sessionItem.logId = log.id;
        sessionItem.isLogged = true;
        sessionItem.is_completed = log.is_completed;
        sessionItem.tracking_data = JSON.parse(JSON.stringify(log.tracking_data));

        window.dispatchEvent(new CustomEvent('toast', {
          detail: { message: 'Workout log saved!', type: 'success' }
        }));
        
        // Refresh calendar view if in background
        Alpine.store('calendar').fetchCalendar();
        // Refresh overview stats if in background
        Alpine.store('stats').fetchOverview();
      } catch (err) {
        window.dispatchEvent(new CustomEvent('toast', {
          detail: { message: err.message || 'Failed to save log', type: 'error' }
        }));
      }
    },

    async toggleComplete(sessionItem) {
      if (!sessionItem.isLogged) {
        // Save first if not logged yet
        sessionItem.is_completed = !sessionItem.is_completed;
        await this.saveLog(sessionItem);
        return;
      }

      const nextState = !sessionItem.is_completed;
      try {
        const res = await api.post(`/workouts/${sessionItem.logId}/complete?completed=${nextState}`);
        sessionItem.is_completed = res.data.is_completed;
        
        window.dispatchEvent(new CustomEvent('toast', {
          detail: { 
            message: `Exercise marked as ${sessionItem.is_completed ? 'completed' : 'incomplete'}!`, 
            type: 'success' 
          }
        }));
        
        // Refresh calendar view if in background
        Alpine.store('calendar').fetchCalendar();
        // Refresh overview stats if in background
        Alpine.store('stats').fetchOverview();
      } catch (err) {
        window.dispatchEvent(new CustomEvent('toast', {
          detail: { message: err.message || 'Failed to toggle status', type: 'error' }
        }));
      }
    },

    async deleteLog(sessionItem) {
      if (!sessionItem.logId) return;
      if (!confirm('Are you sure you want to clear this log?')) return;
      
      try {
        await api.delete(`/workouts/${sessionItem.logId}`);
        
        sessionItem.logId = null;
        sessionItem.isLogged = false;
        sessionItem.is_completed = false;
        sessionItem.tracking_data = [this.getDefaultSet(sessionItem.exercise.tracking_type)];
        
        // If not recommended for today, remove it from list
        if (!sessionItem.isRecommended) {
          this.sessionExercises = this.sessionExercises.filter(item => item.exercise.id !== sessionItem.exercise.id);
        }

        window.dispatchEvent(new CustomEvent('toast', {
          detail: { message: 'Workout log deleted', type: 'success' }
        }));
        
        // Refresh calendar view if in background
        Alpine.store('calendar').fetchCalendar();
        // Refresh overview stats if in background
        Alpine.store('stats').fetchOverview();
      } catch (err) {
        window.dispatchEvent(new CustomEvent('toast', {
          detail: { message: err.message || 'Failed to delete log', type: 'error' }
        }));
      }
    },

    get searchFilteredExercises() {
      const exerciseStore = Alpine.store('exercises');
      if (!this.exerciseSearchQuery) return [];
      
      const q = this.exerciseSearchQuery.toLowerCase();
      // Filter out exercises already in today's list
      return exerciseStore.items.filter(ex => {
        const alreadyAdded = this.sessionExercises.some(item => item.exercise.id === ex.id);
        if (alreadyAdded) return false;
        
        return ex.name_eng.toLowerCase().includes(q) || 
          (ex.name_vie && ex.name_vie.toLowerCase().includes(q)) ||
          (ex.primary_muscle && ex.primary_muscle.toLowerCase().includes(q));
      }).slice(0, 5);
    },

    addCustomExercise(ex) {
      this.sessionExercises.push({
        exercise: ex,
        logId: null,
        is_completed: false,
        tracking_data: [this.getDefaultSet(ex.tracking_type)],
        isLogged: false,
        isRecommended: false
      });
      this.activeExerciseId = ex.id;
      this.exerciseSearchQuery = '';
      this.exerciseSearchOpen = false;
    },

    get progressPercentage() {
      if (this.sessionExercises.length === 0) return 0;
      const completed = this.sessionExercises.filter(item => item.is_completed).length;
      return Math.round((completed / this.sessionExercises.length) * 100);
    }
  });
});
