import { api } from '../api.js';

document.addEventListener('alpine:init', () => {
  Alpine.store('stats', {
    range: '30d',
    overview: {
      total_workouts: 0,
      total_active_days: 0,
      total_volume_kg: 0.0,
      total_reps: 0,
      recent_activity: []
    },
    loadingOverview: false,
    
    // Exercise specific trends
    selectedExerciseId: null,
    exerciseHistory: [],
    loadingExercise: false,
    
    // Chart instances (Chart.js)
    activityChart: null,
    exerciseChart: null,
    activeMetric: 'volume', // 'volume', 'max_weight', 'total_reps', 'total_time'

    async fetchOverview() {
      this.loadingOverview = true;
      try {
        const res = await api.get(`/stats/overview?range=${this.range}`);
        this.overview = res.data || {
          total_workouts: 0,
          total_active_days: 0,
          total_volume_kg: 0.0,
          total_reps: 0,
          recent_activity: []
        };
        
        // Render or update activity chart
        this.updateActivityChart();
      } catch (err) {
        console.error('Failed to fetch overview stats', err);
      } finally {
        this.loadingOverview = false;
      }
    },

    async changeRange(newRange) {
      this.range = newRange;
      await this.fetchOverview();
      if (this.selectedExerciseId) {
        await this.fetchExerciseStats(this.selectedExerciseId);
      }
    },

    async fetchExerciseStats(id) {
      if (!id) return;
      this.selectedExerciseId = parseInt(id);
      this.loadingExercise = true;
      try {
        const res = await api.get(`/stats/exercise/${id}?range=${this.range}`);
        this.exerciseHistory = res.data && res.data.history ? res.data.history : [];
        
        // Render or update exercise trend chart
        this.updateExerciseChart();
      } catch (err) {
        console.error('Failed to fetch exercise stats', err);
      } finally {
        this.loadingExercise = false;
      }
    },

    setMetric(metric) {
      this.activeMetric = metric;
      this.updateExerciseChart();
    },

    updateActivityChart() {
      const ctx = document.getElementById('activityChartCanvas');
      if (!ctx) return; // view not loaded yet or canvas missing

      // Reverse recent activity to show in chronological order
      const sortedActivity = [...this.overview.recent_activity].reverse();
      const labels = sortedActivity.map(a => {
        const dateObj = new Date(a.date);
        return dateObj.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
      });
      const dataCompleted = sortedActivity.map(a => a.completed);
      const dataTotal = sortedActivity.map(a => a.total);

      if (this.activityChart) {
        this.activityChart.destroy();
      }

      this.activityChart = new Chart(ctx, {
        type: 'bar',
        data: {
          labels: labels,
          datasets: [
            {
              label: 'Completed Exercises',
              data: dataCompleted,
              backgroundColor: '#00d4aa',
              borderRadius: 4,
              maxBarThickness: 12
            },
            {
              label: 'Total Logged',
              data: dataTotal,
              backgroundColor: 'rgba(255, 255, 255, 0.05)',
              borderRadius: 4,
              maxBarThickness: 12
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              display: false
            },
            tooltip: {
              mode: 'index',
              intersect: false,
              backgroundColor: '#12121a',
              titleColor: '#f0f0f5',
              bodyColor: '#8888a0',
              borderColor: 'rgba(255,255,255,0.08)',
              borderWidth: 1
            }
          },
          scales: {
            x: {
              grid: {
                display: false
              },
              ticks: {
                color: '#8888a0',
                font: {
                  size: 10,
                  family: 'Inter'
                }
              }
            },
            y: {
              grid: {
                color: 'rgba(255, 255, 255, 0.04)'
              },
              ticks: {
                color: '#8888a0',
                font: {
                  size: 10,
                  family: 'Inter'
                },
                stepSize: 1
              }
            }
          }
        }
      });
    },

    updateExerciseChart() {
      const ctx = document.getElementById('exerciseChartCanvas');
      if (!ctx) return; // view not loaded yet

      const labels = this.exerciseHistory.map(h => {
        const dateObj = new Date(h.date);
        return dateObj.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
      });

      let labelText = '';
      let data = [];
      let strokeColor = '#7c3aed';
      let fillColor = 'rgba(124, 58, 237, 0.05)';

      if (this.activeMetric === 'volume') {
        labelText = 'Volume (kg)';
        data = this.exerciseHistory.map(h => h.volume || 0);
        strokeColor = '#00d4aa';
        fillColor = 'rgba(0, 212, 170, 0.05)';
      } else if (this.activeMetric === 'max_weight') {
        labelText = 'Max Weight (kg)';
        data = this.exerciseHistory.map(h => h.max_weight || 0);
        strokeColor = '#7c3aed';
        fillColor = 'rgba(124, 58, 237, 0.05)';
      } else if (this.activeMetric === 'total_reps') {
        labelText = 'Total Reps';
        data = this.exerciseHistory.map(h => h.total_reps || 0);
        strokeColor = '#f59e0b';
        fillColor = 'rgba(245, 158, 11, 0.05)';
      } else if (this.activeMetric === 'total_time') {
        labelText = 'Total Time (sec)';
        data = this.exerciseHistory.map(h => h.total_time || 0);
        strokeColor = '#3b82f6';
        fillColor = 'rgba(59, 130, 246, 0.05)';
      }

      if (this.exerciseChart) {
        this.exerciseChart.destroy();
      }

      this.exerciseChart = new Chart(ctx, {
        type: 'line',
        data: {
          labels: labels,
          datasets: [
            {
              label: labelText,
              data: data,
              borderColor: strokeColor,
              backgroundColor: fillColor,
              borderWidth: 3,
              fill: true,
              tension: 0.3,
              pointBackgroundColor: strokeColor,
              pointBorderColor: '#0a0a0f',
              pointHoverRadius: 6
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              display: false
            },
            tooltip: {
              backgroundColor: '#12121a',
              titleColor: '#f0f0f5',
              bodyColor: '#8888a0',
              borderColor: 'rgba(255,255,255,0.08)',
              borderWidth: 1
            }
          },
          scales: {
            x: {
              grid: {
                display: false
              },
              ticks: {
                color: '#8888a0',
                font: {
                  size: 10,
                  family: 'Inter'
                }
              }
            },
            y: {
              grid: {
                color: 'rgba(255, 255, 255, 0.04)'
              },
              ticks: {
                color: '#8888a0',
                font: {
                  size: 10,
                  family: 'Inter'
                }
              }
            }
          }
        }
      });
    }
  });
});
