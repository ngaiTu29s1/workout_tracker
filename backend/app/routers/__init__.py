from backend.app.routers.exercises import router as exercises
from backend.app.routers.presets import router as presets
from backend.app.routers.workouts import router as workouts
from backend.app.routers.calendar import router as calendar
from backend.app.routers.stats import router as stats

__all__ = [
    "exercises",
    "presets",
    "workouts",
    "calendar",
    "stats",
]
