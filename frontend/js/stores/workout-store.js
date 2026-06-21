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
    
    // AI Suggestion State
    aiSuggestions: [],
    isSuggesting: false,
    previewOpen: false,
    swappingId: null, // Track which card is being swapped
    suggestionSource: null,
    
    // Quick search list for adding custom exercise to today's workout
    exerciseSearchQuery: '',
    exerciseSearchOpen: false,

    // Swap Modal State
    swappingSessionItem: null,
    swapModalOpen: false,
    swapSearchQuery: '',

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

        // 4. Combine logs
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

        // Sort combined list based on saved order in localStorage (if any)
        const savedOrderStr = localStorage.getItem(`workout_order_${this.selectedDate}`);
        if (savedOrderStr) {
          try {
            const savedOrder = JSON.parse(savedOrderStr);
            combined.sort((a, b) => {
              const idxA = savedOrder.indexOf(a.exercise.id);
              const idxB = savedOrder.indexOf(b.exercise.id);
              if (idxA === -1 && idxB === -1) return 0;
              if (idxA === -1) return 1;
              if (idxB === -1) return -1;
              return idxA - idxB;
            });
          } catch (e) {
            console.error('Failed to parse saved workout order', e);
          }
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
      const lowerTag = tag.toLowerCase().replace(' ', '_');

      const inTags = ex.tags && ex.tags.some(t => {
        const lt = t.toLowerCase().replace(' ', '_');
        return lt === lowerTag || (lowerTag === 'legs' && lt === 'leg') || (lowerTag === 'leg' && lt === 'legs');
      });
      const isPrimary = ex.primary_muscle && ex.primary_muscle.toLowerCase() === lowerTag;
      const isSecondary = ex.secondary_muscle && ex.secondary_muscle.some(sm => sm.toLowerCase() === lowerTag);

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

      if (lowerTag === 'upper_body') {
        const upperMuscles = ['chest', 'shoulders', 'triceps', 'back', 'biceps', 'forearms', 'push', 'pull', 'upper_body', 'upper body'];
        return inTags || 
          (ex.primary_muscle && upperMuscles.includes(ex.primary_muscle.toLowerCase()));
      }

      if (lowerTag === 'lower_body') {
        const lowerMuscles = ['quads', 'hamstrings', 'calves', 'glutes', 'leg', 'legs', 'lower_body', 'lower body'];
        return inTags || 
          (ex.primary_muscle && lowerMuscles.includes(ex.primary_muscle.toLowerCase()));
      }

      if (lowerTag === 'core') {
        const coreMuscles = ['core', 'abs', 'obliques', 'lower back'];
        return inTags || 
          (ex.primary_muscle && coreMuscles.includes(ex.primary_muscle.toLowerCase()));
      }

      if (lowerTag === 'cardio') {
        const cardioMuscles = ['cardio', 'conditioning', 'stretching', 'warmup'];
        return inTags || 
          (ex.primary_muscle && cardioMuscles.includes(ex.primary_muscle.toLowerCase()));
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
      if (!(await window.customConfirm('Are you sure you want to clear this log?'))) return;
      
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

    get swapFilteredExercises() {
      const exerciseStore = Alpine.store('exercises');
      if (!this.swappingSessionItem) return [];
      
      const targetMuscle = (this.swappingSessionItem.exercise.primary_muscle || '').toLowerCase();
      
      let list = exerciseStore.items.filter(ex => {
        // Exclude exercises already in the session
        return !this.sessionExercises.some(item => Number(item.exercise.id) === Number(ex.id));
      });

      if (this.swapSearchQuery) {
        const q = this.swapSearchQuery.toLowerCase();
        list = list.filter(ex => {
          const nameMatch = (ex.name_eng || '').toLowerCase().includes(q) || (ex.name_vie || '').toLowerCase().includes(q);
          const muscleMatch = (ex.primary_muscle || '').toLowerCase().includes(q);
          return nameMatch || muscleMatch;
        });
      }

      // Sort: place same primary muscle first
      if (targetMuscle) {
        list.sort((a, b) => {
          const aMatch = (a.primary_muscle || '').toLowerCase() === targetMuscle ? 1 : 0;
          const bMatch = (b.primary_muscle || '').toLowerCase() === targetMuscle ? 1 : 0;
          return bMatch - aMatch;
        });
      }
      return list.slice(0, 10);
    },

    openSwapModal(sessionItem) {
      this.swappingSessionItem = sessionItem;
      this.swapSearchQuery = '';
      this.swapModalOpen = true;
    },

    async swapSessionExerciseManually(ex) {
      if (!this.swappingSessionItem) return;
      
      const appEl = document.querySelector('[x-data="app"]');
      const lang = appEl && window.Alpine ? window.Alpine.evaluate(appEl, 'lang') : 'vi';
      const sessionItem = this.swappingSessionItem;

      if (sessionItem.isLogged) {
        const confirmMsg = lang === 'vi' 
          ? 'Đổi bài tập sẽ xóa dữ liệu đã lưu hôm nay của bài này. Bạn có chắc muốn đổi?' 
          : 'Swapping this exercise will clear today\'s saved logs for it. Are you sure?';
        if (!(await window.customConfirm(confirmMsg))) return;
      }

      this.loading = true;
      try {
        if (sessionItem.logId) {
          await api.delete(`/workouts/${sessionItem.logId}`);
        }
        
        sessionItem.exercise = ex;
        sessionItem.logId = null;
        sessionItem.isLogged = false;
        sessionItem.is_completed = false;
        
        // Fetch suggested sets from single exercise suggestion endpoint
        const res = await api.get(`/workouts/suggest-sets?exercise_id=${ex.id}`);
        const suggestion = res.data;
        
        if (suggestion && suggestion.suggested_sets && suggestion.suggested_sets.length > 0) {
          sessionItem.tracking_data = suggestion.suggested_sets.map((s, idx) => ({
            set: s.set || (idx + 1),
            kg: s.kg,
            rep: s.rep,
            time_seconds: s.time_seconds
          }));
        } else {
          sessionItem.tracking_data = [this.getDefaultSet(ex.tracking_type)];
        }
        
        this.activeExerciseId = ex.id;
        this.sessionExercises = [...this.sessionExercises];
        this.swapModalOpen = false;
        this.swappingSessionItem = null;
        this.swapSearchQuery = '';
        
        window.dispatchEvent(new CustomEvent('toast', {
          detail: {
            message: lang === 'vi' ? 'Đổi bài tập thành công!' : 'Exercise swapped successfully!',
            type: 'success'
          }
        }));
        
        Alpine.store('calendar').fetchCalendar();
        Alpine.store('stats').fetchOverview();
      } catch (err) {
        window.dispatchEvent(new CustomEvent('toast', {
          detail: { message: err.message || 'Failed to swap exercise', type: 'error' }
        }));
      } finally {
        this.loading = false;
      }
    },

    async swapSessionExerciseAuto() {
      if (!this.swappingSessionItem) return;
      const sessionItem = this.swappingSessionItem;
      this.swapModalOpen = false;
      this.swapSearchQuery = '';
      await this.swapSessionExercise(sessionItem);
      this.swappingSessionItem = null;
    },

    async fetchLocalSuggestions() {
      if (this.routineTag === 'rest') {
        window.dispatchEvent(new CustomEvent('toast', {
          detail: { message: 'Hôm nay là ngày nghỉ (Rest), không thể gợi ý bài tập.', type: 'warning' }
        }));
        return;
      }
      this.isSuggesting = true;
      try {
        const res = await api.post('/workouts/local-suggest', {
          date: this.selectedDate,
          routine_tag: this.routineTag
        });
        
        const suggestions = res.data || [];
        const exerciseStore = Alpine.store('exercises');
        if (exerciseStore.items.length === 0) {
          await exerciseStore.fetchAll();
        }
        
        this.aiSuggestions = suggestions.map(s => {
          const sId = s.exercise_id || s.id;
          const ex = exerciseStore.items.find(item => Number(item.id) === Number(sId));
          return {
            exercise: ex,
            suggested_sets: s.suggested_sets || [],
            checked: true
          };
        }).filter(s => s && s.exercise);
        
        this.suggestionSource = 'local';
        this.previewOpen = true;
      } catch (err) {
        window.dispatchEvent(new CustomEvent('toast', {
          detail: { message: err.message || 'Failed to get suggestions', type: 'error' }
        }));
      } finally {
        this.isSuggesting = false;
      }
    },

    async fetchAiSuggestions() {
      if (this.routineTag === 'rest') {
        window.dispatchEvent(new CustomEvent('toast', {
          detail: { message: 'Hôm nay là ngày nghỉ (Rest), không thể gợi ý bài tập.', type: 'warning' }
        }));
        return;
      }
      this.isSuggesting = true;
      try {
        const res = await api.post('/workouts/ai-suggest', {
          date: this.selectedDate,
          routine_tag: this.routineTag
        });
        
        const suggestions = res.data || [];
        const exerciseStore = Alpine.store('exercises');
        if (exerciseStore.items.length === 0) {
          await exerciseStore.fetchAll();
        }
        
        this.aiSuggestions = suggestions.map(s => {
          const sId = s.exercise_id || s.id;
          const ex = exerciseStore.items.find(item => Number(item.id) === Number(sId));
          return {
            exercise: ex,
            suggested_sets: s.suggested_sets || [],
            checked: true
          };
        }).filter(s => s && s.exercise);
        
        this.suggestionSource = 'ai';
        this.previewOpen = true;
      } catch (err) {
        let msg = err.message || 'Failed to get suggestions';
        if (msg.includes('N8N Webhook not configured')) {
          const appEl = document.querySelector('[x-data="app"]');
          const lang = appEl && window.Alpine ? window.Alpine.evaluate(appEl, 'lang') : 'vi';
          msg = lang === 'vi' 
            ? 'N8N Webhook chưa được cấu hình. Vui lòng thiết lập N8N_AUTOFILL_WEBHOOK_URL trong file .env.' 
            : 'N8N Webhook not configured. Please set N8N_AUTOFILL_WEBHOOK_URL in .env file.';
        }
        window.dispatchEvent(new CustomEvent('toast', {
          detail: { message: msg, type: 'error' }
        }));
      } finally {
        this.isSuggesting = false;
      }
    },

    async swapSuggestion(exerciseId) {
      this.swappingId = exerciseId;
      try {
        const currentSuggestions = this.aiSuggestions.map(s => Number(s.exercise.id));
        const endpoint = this.suggestionSource === 'local' ? '/workouts/local-swap' : '/workouts/ai-swap';
        const res = await api.post(endpoint, {
          date: this.selectedDate,
          routine_tag: this.routineTag,
          exercise_id: exerciseId,
          current_suggestions: currentSuggestions
        });
        
        const replacement = res.data;
        if (replacement) {
          const exerciseStore = Alpine.store('exercises');
          const ex = exerciseStore.items.find(item => Number(item.id) === Number(replacement.exercise_id || replacement.id));
          if (ex) {
            const idx = this.aiSuggestions.findIndex(s => s.exercise && Number(s.exercise.id) === Number(exerciseId));
            if (idx !== -1) {
              this.aiSuggestions[idx] = {
                exercise: ex,
                suggested_sets: replacement.suggested_sets || [],
                checked: true
              };
              this.aiSuggestions = [...this.aiSuggestions];
            }
          }
        }
      } catch (err) {
        window.dispatchEvent(new CustomEvent('toast', {
          detail: { message: err.message || 'Failed to swap exercise', type: 'error' }
        }));
      } finally {
        this.swappingId = null;
      }
    },

    async applySuggestions() {
      const checkedSuggestions = this.aiSuggestions.filter(s => s.checked);
      if (checkedSuggestions.length === 0) {
        window.dispatchEvent(new CustomEvent('toast', {
          detail: { message: 'Vui lòng chọn ít nhất một bài tập', type: 'warning' }
        }));
        return;
      }

      this.loading = true;
      try {
        const suggestionsPayload = checkedSuggestions.map(s => ({
          exercise_id: s.exercise.id,
          suggested_sets: s.suggested_sets
        }));

        await api.post('/workouts/apply-suggestions', {
          date: this.selectedDate,
          suggestions: suggestionsPayload
        });

        this.previewOpen = false;
        this.aiSuggestions = [];
        await this.fetchSession();

        window.dispatchEvent(new CustomEvent('toast', {
          detail: { message: 'Đã áp dụng các bài tập gợi ý!', type: 'success' }
        }));
        
        Alpine.store('calendar').fetchCalendar();
        Alpine.store('stats').fetchOverview();
      } catch (err) {
        window.dispatchEvent(new CustomEvent('toast', {
          detail: { message: err.message || 'Failed to apply suggestions', type: 'error' }
        }));
      } finally {
        this.loading = false;
      }
    },

    moveExercise(item, direction) {
      const idx = this.sessionExercises.findIndex(ex => ex.exercise.id === item.exercise.id);
      if (idx === -1) return;
      const targetIdx = idx + direction;
      if (targetIdx < 0 || targetIdx >= this.sessionExercises.length) return;
      
      const temp = this.sessionExercises[idx];
      this.sessionExercises[idx] = this.sessionExercises[targetIdx];
      this.sessionExercises[targetIdx] = temp;
      
      this.sessionExercises = [...this.sessionExercises];
      
      const newOrder = this.sessionExercises.map(ex => ex.exercise.id);
      localStorage.setItem(`workout_order_${this.selectedDate}`, JSON.stringify(newOrder));
    },

    async swapSessionExercise(sessionItem) {
      const appEl = document.querySelector('[x-data="app"]');
      const lang = appEl && window.Alpine ? window.Alpine.evaluate(appEl, 'lang') : 'vi';

      if (sessionItem.isLogged) {
        const confirmMsg = lang === 'vi' 
          ? 'Đổi bài tập sẽ xóa dữ liệu đã lưu hôm nay của bài này. Bạn có chắc muốn đổi?' 
          : 'Swapping this exercise will clear today\'s saved logs for it. Are you sure?';
        if (!(await window.customConfirm(confirmMsg))) return;
      }
      
      this.loading = true;
      try {
        const currentIds = this.sessionExercises.map(item => Number(item.exercise.id));
        const endpoint = this.suggestionSource === 'local' ? '/workouts/local-swap' : '/workouts/ai-swap';
        const res = await api.post(endpoint, {
          date: this.selectedDate,
          routine_tag: this.routineTag,
          exercise_id: sessionItem.exercise.id,
          current_suggestions: currentIds
        });
        
        const replacement = res.data;
        if (replacement) {
          const ex = exerciseStore.items.find(item => Number(item.id) === Number(replacement.exercise_id || replacement.id));
          if (ex) {
            if (sessionItem.logId) {
              await api.delete(`/workouts/${sessionItem.logId}`);
            }
            
            sessionItem.exercise = ex;
            sessionItem.logId = null;
            sessionItem.isLogged = false;
            sessionItem.is_completed = false;
            
            if (replacement.suggested_sets && replacement.suggested_sets.length > 0) {
              sessionItem.tracking_data = replacement.suggested_sets.map((s, idx) => ({
                set: s.set || (idx + 1),
                kg: s.kg,
                rep: s.rep,
                time_seconds: s.time_seconds
              }));
            } else {
              sessionItem.tracking_data = [this.getDefaultSet(ex.tracking_type)];
            }
            
            this.activeExerciseId = ex.id;
            this.sessionExercises = [...this.sessionExercises];
            
            window.dispatchEvent(new CustomEvent('toast', {
              detail: { 
                message: lang === 'vi' ? 'Đổi bài tập thành công!' : 'Exercise swapped successfully!', 
                type: 'success' 
              }
            }));
            
            Alpine.store('calendar').fetchCalendar();
            Alpine.store('stats').fetchOverview();
          }
        }
      } catch (err) {
        window.dispatchEvent(new CustomEvent('toast', {
          detail: { message: err.message || 'Failed to swap exercise', type: 'error' }
        }));
      } finally {
        this.loading = false;
      }
    },

    async removeSessionExercise(sessionItem) {
      const appEl = document.querySelector('[x-data="app"]');
      const lang = appEl && window.Alpine ? window.Alpine.evaluate(appEl, 'lang') : 'vi';

      if (sessionItem.isLogged) {
        const confirmMsg = lang === 'vi' 
          ? 'Bạn có chắc chắn muốn xóa bài tập này khỏi buổi tập hôm nay? Lịch sử hiệp tập đã lưu của bài này sẽ bị xóa.' 
          : 'Are you sure you want to remove this exercise from today\'s session? Its saved logs will be deleted.';
        if (!(await window.customConfirm(confirmMsg))) return;
        
        try {
          await api.delete(`/workouts/${sessionItem.logId}`);
        } catch (err) {
          window.dispatchEvent(new CustomEvent('toast', {
            detail: { message: err.message || 'Failed to delete log', type: 'error' }
          }));
          return;
        }
      }
      
      this.sessionExercises = this.sessionExercises.filter(item => item.exercise.id !== sessionItem.exercise.id);
      
      const newOrder = this.sessionExercises.map(ex => ex.exercise.id);
      localStorage.setItem(`workout_order_${this.selectedDate}`, JSON.stringify(newOrder));
      
      window.dispatchEvent(new CustomEvent('toast', {
        detail: { 
          message: lang === 'vi' ? 'Đã xóa bài tập khỏi buổi tập!' : 'Exercise removed from session!', 
          type: 'success' 
        }
      }));
      
      Alpine.store('calendar').fetchCalendar();
      Alpine.store('stats').fetchOverview();
    },

    get progressPercentage() {
      if (this.sessionExercises.length === 0) return 0;
      const completed = this.sessionExercises.filter(item => item.is_completed).length;
      return Math.round((completed / this.sessionExercises.length) * 100);
    }
  });
});
