import { api } from '../api.js';

document.addEventListener('alpine:init', () => {
    Alpine.store('pool', {
        searchQuery: '',
        searchResults: [],
        searching: false,
        selectedExercise: null,   // pool exercise detail for preview
        open() {
            this.modalOpen = true;
            this.searchQuery = '';
            this.search('');
        },
        
        async search(query) {
            const cleanQuery = (query || '').trim();
            this.searching = true;
            try {
                const res = await api.get(`/pool/search?q=${encodeURIComponent(cleanQuery)}&limit=20`);
                this.searchResults = res.data || [];
            } catch (err) {
                window.dispatchEvent(new CustomEvent('toast', {
                    detail: { message: err.message || 'Failed to search pool', type: 'error' }
                }));
            } finally {
                this.searching = false;
            }
        },
        
        async getDetail(id) {
            try {
                const res = await api.get(`/pool/${id}`);
                this.selectedExercise = res.data;
            } catch (err) {
                window.dispatchEvent(new CustomEvent('toast', {
                    detail: { message: err.message || 'Failed to fetch details', type: 'error' }
                }));
            }
        },
        
        async addToPersonal(poolId, tags = []) {
            try {
                const res = await api.post('/exercises/add-from-pool', { pool_id: poolId, tags });
                // Refresh personal exercises
                await Alpine.store('exercises').fetchAll();
                this.modalOpen = false;
                // Toast
                window.dispatchEvent(new CustomEvent('toast', {
                    detail: { message: 'Exercise added!', type: 'success' }
                }));
            } catch (err) {
                window.dispatchEvent(new CustomEvent('toast', {
                    detail: { message: err.message || 'Failed to add exercise', type: 'error' }
                }));
            }
        },
        
        getImageUrl(exercise) {
            if (!exercise) return null;
            // For pool search results: use image_path
            if (exercise.image_path) return `/pool/${exercise.image_path}`;
            // For personal exercises: use image_url (already formatted)
            if (exercise.image_url) return exercise.image_url;
            // Or if it's personal exercise response, it might have pool_image
            if (exercise.pool_image) return `/pool/${exercise.pool_image}`;
            return null;
        },
        
        getGifUrl(exercise) {
            if (!exercise) return null;
            if (exercise.gif_path) return `/pool/${exercise.gif_path}`;
            if (exercise.video_url) return exercise.video_url;
            if (exercise.pool_gif) return `/pool/${exercise.pool_gif}`;
            return null;
        }
    });
});
