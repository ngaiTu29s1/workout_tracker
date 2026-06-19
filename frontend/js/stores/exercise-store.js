import { api } from '../api.js';

document.addEventListener('alpine:init', () => {
  Alpine.store('exercises', {
    items: [],
    loading: false,
    enrichingIds: [],
    search: '',
    selectedMuscle: '',
    selectedTag: '',
    routineTags: [
      { value: 'push', label: 'Push' },
      { value: 'pull', label: 'Pull' },
      { value: 'legs', label: 'Legs' },
      { value: 'upper_body', label: 'Upper Body' },
      { value: 'lower_body', label: 'Lower Body' },
      { value: 'core', label: 'Core' },
      { value: 'cardio', label: 'Cardio' }
    ],
    
    // For editing/creating modal form state
    modalOpen: false,
    editingExercise: null, // null means creating new
    form: {
      name_eng: '',
      name_vie: '',
      instructions: '',
      video_url: '',
      image_url: '',
      pro_tips: '',
      tracking_type: 'WEIGHT_REPS',
      primary_muscle: '',
      secondary_muscle: [],
      tags: []
    },

    // UI filters
    musclesList: [],
    tagsList: [],

    async fetchAll() {
      this.loading = true;
      try {
        const res = await api.get('/exercises');
        this.items = res.data || [];
        this.extractFilters();
      } catch (err) {
        window.dispatchEvent(new CustomEvent('toast', {
          detail: { message: err.message || 'Failed to fetch exercises', type: 'error' }
        }));
      } finally {
        this.loading = false;
      }
    },

    extractFilters() {
      const muscles = new Set();
      const tags = new Set();
      this.items.forEach(ex => {
        if (ex.primary_muscle) muscles.add(ex.primary_muscle);
        if (ex.secondary_muscle) {
          ex.secondary_muscle.forEach(m => muscles.add(m));
        }
        if (ex.tags) {
          ex.tags.forEach(t => tags.add(t));
        }
      });
      this.musclesList = Array.from(muscles).sort();
      this.tagsList = Array.from(tags).sort();
    },

    get filteredItems() {
      const filtered = this.items.filter(ex => {
        // Search filter (name, vietnamese name, primary muscle, secondary muscle)
        const matchesSearch = !this.search || 
          ex.name_eng.toLowerCase().includes(this.search.toLowerCase()) ||
          (ex.name_vie && ex.name_vie.toLowerCase().includes(this.search.toLowerCase())) ||
          (ex.primary_muscle && ex.primary_muscle.toLowerCase().includes(this.search.toLowerCase())) ||
          (ex.secondary_muscle && ex.secondary_muscle.some(m => m.toLowerCase().includes(this.search.toLowerCase())));

        // Tag filter (matches against routine_tag)
        const matchesTag = !this.selectedTag || 
          (ex.tags && ex.tags.some(t => t.toLowerCase().replace(' ', '_') === this.selectedTag.toLowerCase().replace(' ', '_')));

        return matchesSearch && matchesTag;
      });

      // Sort by created_at DESC (newest first)
      return filtered.sort((a, b) => {
        const da = a.created_at || '';
        const db = b.created_at || '';
        if (da < db) return 1;
        if (da > db) return -1;
        return 0;
      });
    },

    openCreateModal() {
      this.editingExercise = null;
      this.form = {
        name_eng: '',
        name_vie: '',
        instructions: '',
        video_url: '',
        image_url: '',
        pro_tips: '',
        tracking_type: 'WEIGHT_REPS',
        primary_muscle: '',
        secondary_muscle_str: '', // input helper
        tags_str: '' // input helper
      };
      this.modalOpen = true;
    },

    openEditModal(exercise) {
      this.editingExercise = exercise;
      this.form = {
        name_eng: exercise.name_eng || '',
        name_vie: exercise.name_vie || '',
        instructions: exercise.instructions || '',
        video_url: exercise.video_url || '',
        image_url: exercise.image_url || '',
        pro_tips: exercise.pro_tips || '',
        tracking_type: exercise.tracking_type || 'WEIGHT_REPS',
        primary_muscle: exercise.primary_muscle || '',
        secondary_muscle_str: exercise.secondary_muscle ? exercise.secondary_muscle.join(', ') : '',
        tags_str: exercise.tags ? exercise.tags.join(', ') : ''
      };
      this.modalOpen = true;
    },

    async saveForm() {
      // Parse lists from strings
      const secondary_muscle = this.form.secondary_muscle_str
        ? this.form.secondary_muscle_str.split(',').map(s => s.trim()).filter(Boolean)
        : [];
      const tags = this.form.tags_str
        ? this.form.tags_str.split(',').map(s => s.trim()).filter(Boolean)
        : [];

      const payload = {
        name_eng: this.form.name_eng,
        name_vie: this.form.name_vie || null,
        instructions: this.form.instructions || null,
        video_url: this.form.video_url || null,
        image_url: this.form.image_url || null,
        pro_tips: this.form.pro_tips || null,
        tracking_type: this.form.tracking_type,
        primary_muscle: this.form.primary_muscle || null,
        secondary_muscle,
        tags
      };

      try {
        if (this.editingExercise) {
          const res = await api.put(`/exercises/${this.editingExercise.id}`, payload);
          // Update in local items list
          const index = this.items.findIndex(ex => ex.id === this.editingExercise.id);
          if (index !== -1) {
            this.items.splice(index, 1, res.data);
          }
          window.dispatchEvent(new CustomEvent('toast', {
            detail: { message: 'Exercise updated successfully', type: 'success' }
          }));
        } else {
          const res = await api.post('/exercises', payload);
          this.items.push(res.data);
          window.dispatchEvent(new CustomEvent('toast', {
            detail: { message: 'Exercise created successfully', type: 'success' }
          }));
          // Auto-trigger enrichment
          this.enrichExercise(res.data.id);
        }
        this.extractFilters();
        this.modalOpen = false;
        
        // Refresh session today if needed
        Alpine.store('workout').refreshTodaySession();
      } catch (err) {
        window.dispatchEvent(new CustomEvent('toast', {
          detail: { message: err.message || 'Failed to save exercise', type: 'error' }
        }));
      }
    },

    async deleteExercise(id) {
      if (!confirm('Are you sure you want to delete this exercise? This will delete all logged data for it.')) {
        return;
      }
      try {
        await api.delete(`/exercises/${id}`);
        this.items = this.items.filter(ex => ex.id !== id);
        this.extractFilters();
        window.dispatchEvent(new CustomEvent('toast', {
          detail: { message: 'Exercise deleted successfully', type: 'success' }
        }));
        
        // Refresh active views
        Alpine.store('workout').refreshTodaySession();
      } catch (err) {
        window.dispatchEvent(new CustomEvent('toast', {
          detail: { message: err.message || 'Failed to delete exercise', type: 'error' }
        }));
      }
    },

    async enrichExercise(id) {
      if (this.enrichingIds.includes(id)) return;
      this.enrichingIds.push(id);

      window.dispatchEvent(new CustomEvent('toast', {
        detail: { message: 'Starting AI enrichment...', type: 'info' }
      }));
      try {
        const res = await api.post(`/exercises/${id}/enrich`);
        // Update local item
        const index = this.items.findIndex(ex => ex.id === id);
        if (index !== -1) {
          this.items.splice(index, 1, res.data);
        }
        this.extractFilters();
        window.dispatchEvent(new CustomEvent('toast', {
          detail: { message: 'AI enrichment completed!', type: 'success' }
        }));
        
        // If we are editing this exercise in modal, refresh form field values
        if (this.modalOpen && this.editingExercise && this.editingExercise.id === id) {
          this.openEditModal(res.data);
        }
        
        // Refresh session today if needed
        Alpine.store('workout').refreshTodaySession();
      } catch (err) {
        window.dispatchEvent(new CustomEvent('toast', {
          detail: { message: err.message || 'AI enrichment failed', type: 'error' }
        }));
      } finally {
        this.enrichingIds = this.enrichingIds.filter(x => x !== id);
      }
    }
  });
});
