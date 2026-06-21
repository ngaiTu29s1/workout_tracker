import logging
import httpx
import os
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from backend.app.config import settings
from backend.app.models.exercise import ExerciseMaster

logger = logging.getLogger(__name__)

CACHE_PATH = os.path.join(os.getenv("POOL_DATA_PATH", "/app/static/pool"), "enrichment_cache.json")

class EnrichmentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _load_cache(self) -> dict:
        try:
            if os.path.exists(CACHE_PATH):
                with open(CACHE_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load enrichment cache: {e}")
        return {}

    def _save_cache(self, cache_data: dict) -> None:
        try:
            os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
            with open(CACHE_PATH, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save enrichment cache: {e}")

    def _resolve_bilingual_field(
        self,
        exercise: ExerciseMaster,
        base_field: str,
        enriched_data: dict,
        default: str
    ) -> tuple:
        """
        Resolve fallback logic for bilingual fields (instructions, pro_tips).
        """
        val = getattr(exercise, base_field, None)
        val_en = getattr(exercise, f"{base_field}_en", None)
        val_vi = getattr(exercise, f"{base_field}_vi", None)

        # 1. Inherit from pool if it exists
        if exercise.pool:
            if not val_en:
                val_en = getattr(exercise.pool, f"{base_field}_en", None)
            if not val_vi:
                val_vi = getattr(exercise.pool, f"{base_field}_vi", None)

        # 2. Inherit from enriched_data
        if not val_en and enriched_data:
            val_en = enriched_data.get(f"{base_field}_en")
        if not val_vi and enriched_data:
            val_vi = enriched_data.get(f"{base_field}_vi") or enriched_data.get(base_field)

        # 3. Apply general fallback rules
        base_val = val_vi or val or val_en
        en_val = val_en or base_val or default
        vi_val = val_vi or base_val

        return base_val, en_val, vi_val

    async def enrich_exercise(self, exercise_id: int) -> ExerciseMaster:
        """
        Trigger AI enrichment via n8n webhook.
        Uses a local JSON cache to store translation metadata to optimize token usage.
        If n8n is unconfigured or returns an error, falls back to a smart mock.
        """
        # Fetch exercise with eager loaded pool relation to prevent MissingGreenlet errors during Pydantic validation
        query = select(ExerciseMaster).where(ExerciseMaster.id == exercise_id).options(joinedload(ExerciseMaster.pool))
        result = await self.db.execute(query)
        exercise = result.scalar_one_or_none()
        
        if not exercise:
            raise ValueError(f"Exercise with ID {exercise_id} not found.")

        # Check in persistent cache first using lowercased English name
        cache_key = exercise.name_eng.strip().lower()
        cache = self._load_cache()
        enriched_data = None

        if cache_key in cache:
            enriched_data = cache[cache_key]
            logger.info(f"Using cached AI enrichment for: {exercise.name_eng}")
        else:
            # Send exercise ID and English name directly to the n8n webhook.
            payload = {
                "exercise_id": exercise.id,
                "name_eng": exercise.name_eng
            }

            # Try to contact n8n
            if settings.N8N_WEBHOOK_URL and "change_me" not in settings.N8N_WEBHOOK_URL and "local" not in settings.N8N_WEBHOOK_URL:
                try:
                    async with httpx.AsyncClient() as client:
                        response = await client.post(
                            settings.N8N_WEBHOOK_URL,
                            json=payload,
                            timeout=60.0
                        )
                        if response.status_code == 200:
                            res_json = response.json()
                            if isinstance(res_json, list) and len(res_json) > 0:
                                enriched_data = res_json[0]
                            elif isinstance(res_json, dict):
                                enriched_data = res_json
                            else:
                                enriched_data = {}
                            
                            # Cache successful translation metadata
                            if enriched_data and "name_vie" in enriched_data:
                                cache[cache_key] = enriched_data
                                self._save_cache(cache)
                                logger.info(f"Successfully cached enriched metadata from n8n for: {exercise.name_eng}")
                        else:
                            logger.warning(f"n8n returned status code {response.status_code}. Using mock fallback.")
                except Exception as e:
                    logger.warning(f"Failed to connect to n8n webhook at {settings.N8N_WEBHOOK_URL}: {e}. Using mock fallback.")

        # Fallback to Mock Data if no response from cache/n8n or response is incomplete (missing translation fields)
        if not enriched_data or "name_vie" not in enriched_data or ("instructions" not in enriched_data and "instructions_vi" not in enriched_data):
            enriched_data = self._generate_mock_metadata(exercise.name_eng)

        # 1. Inherit from pool first if this is a pool-linked exercise (non-bilingual fields)
        if exercise.pool:
            pool = exercise.pool
            if not exercise.image_url and pool.image_path:
                exercise.image_url = f"/pool/{pool.image_path}"
            if not exercise.video_url and pool.gif_path:
                exercise.video_url = f"/pool/{pool.gif_path}"
            if not exercise.primary_muscle and pool.muscle_group:
                exercise.primary_muscle = pool.muscle_group
            if not exercise.secondary_muscle and pool.secondary_muscles:
                exercise.secondary_muscle = pool.secondary_muscles
            if not exercise.tracking_type:
                from backend.app.services.pool_service import infer_tracking_type
                exercise.tracking_type = infer_tracking_type(pool.equipment, pool.category)

        # 2. Update empty exercise fields with AI enriched data
        if not exercise.name_vie and enriched_data and "name_vie" in enriched_data:
            exercise.name_vie = enriched_data["name_vie"]
            
        # Resolve bilingual fields
        exercise.instructions, exercise.instructions_en, exercise.instructions_vi = self._resolve_bilingual_field(
            exercise, "instructions", enriched_data, "Perform the exercise with correct form."
        )

        exercise.pro_tips, exercise.pro_tips_en, exercise.pro_tips_vi = self._resolve_bilingual_field(
            exercise, "pro_tips", enriched_data, "Focus on form and safety."
        )

        if not exercise.video_url and enriched_data and "video_url" in enriched_data:
            exercise.video_url = enriched_data["video_url"]
        if not exercise.image_url and enriched_data and "image_url" in enriched_data:
            exercise.image_url = enriched_data["image_url"]

        if not exercise.tracking_type and enriched_data and "tracking_type" in enriched_data:
            exercise.tracking_type = enriched_data["tracking_type"]
        if not exercise.primary_muscle and enriched_data and "primary_muscle" in enriched_data:
            exercise.primary_muscle = enriched_data["primary_muscle"]
        if (not exercise.secondary_muscle) and enriched_data and "secondary_muscle" in enriched_data:
            exercise.secondary_muscle = enriched_data["secondary_muscle"]
        if (not exercise.tags) and enriched_data and "tags" in enriched_data:
            exercise.tags = enriched_data["tags"]

        # 3. Write back instructions_vi to the pool table if it is linked, to enrich the pool itself
        if exercise.pool and exercise.instructions_vi:
            exercise.pool.instructions_vi = exercise.pool.instructions_vi or exercise.instructions_vi

        await self.db.commit()
        from backend.app.services.exercise_service import ExerciseService
        ex_service = ExerciseService(self.db)
        return await ex_service.get_exercise(exercise.id)

    def _generate_mock_metadata(self, name_eng: str) -> dict:
        """
        Generate smart mock metadata based on the English name of the exercise.
        Returns bilingual fields.
        """
        name_lower = name_eng.lower()
        
        # Default mock template
        mock = {
            "name_vie": f"{name_eng} (Bản dịch AI)",
            "instructions_en": f"Instructions for {name_eng}: Execute with proper form, keep your back straight, inhale on descent and exhale on push/pull.",
            "instructions_vi": f"Hướng dẫn cho bài tập {name_eng}: Thực hiện đúng tư thế, giữ lưng thẳng, hít vào khi hạ tạ và thở ra khi đẩy/kéo tạ.",
            "video_url": None,
            "image_url": None,
            "pro_tips_en": "Warm up properly before training. Do not overexert yourself.",
            "pro_tips_vi": "Khởi động kỹ cơ khớp trước khi thực hiện. Không tập quá sức.",
            "tracking_type": "WEIGHT_REPS",
            "primary_muscle": "Full Body",
            "secondary_muscle": [],
            "tags": ["strength", "gym"]
        }

        # Specific exercises mapping for more realistic demo
        if "bench press" in name_lower:
            mock.update({
                "name_vie": "Đẩy ngực trên ghế bằng",
                "instructions_en": "Lie flat on a bench, grip the barbell wider than shoulder width. Lower the bar slowly to your chest, then press it back up.",
                "instructions_vi": "Nằm trên ghế phẳng, nắm thanh đòn rộng hơn vai. Hạ thanh đòn xuống ngực và đẩy mạnh lên.",
                "pro_tips_en": "Keep your shoulder blades retracted and flat on the bench to protect shoulders.",
                "pro_tips_vi": "Giữ bả vai co lại và chạm vào ghế để bảo vệ khớp vai.",
                "primary_muscle": "Chest",
                "secondary_muscle": ["Triceps", "Shoulders"],
                "tags": ["push", "chest", "upper_body", "barbell"]
            })
        elif "squat" in name_lower:
            mock.update({
                "name_vie": "Gánh đùi sau/trước (Squat)",
                "instructions_en": "Rest bar on upper traps. Lower your hips as if sitting back in a chair until thighs are parallel to the floor, then stand straight.",
                "instructions_vi": "Đặt thanh đòn trên cơ cầu vai. Hạ hông xuống như tư thế ngồi ghế cho đến khi đùi song song với sàn, rồi đứng thẳng dậy.",
                "pro_tips_en": "Keep knees tracking over toes and maintain a neutral/straight spine throughout.",
                "pro_tips_vi": "Đẩy gối ra ngoài và giữ cho lưng thẳng suốt quá trình chuyển động.",
                "primary_muscle": "Quads",
                "secondary_muscle": ["Glutes", "Hamstrings", "Core"],
                "tags": ["legs", "lower_body", "compound", "barbell"]
            })
        elif "deadlift" in name_lower:
            mock.update({
                "name_vie": "Kéo tạ đòn (Deadlift)",
                "instructions_en": "Stand close to bar, bend hips and knees to grip it. Pull the bar straight up by driving your legs and keeping back straight.",
                "instructions_vi": "Đứng sát thanh đòn, gập người nắm thanh đòn. Kéo thanh đòn thẳng lên sát chân bằng lực đùi sau và lưng dưới.",
                "pro_tips_en": "Never round your spine. Engage core and lats before lifting.",
                "pro_tips_vi": "Không bao giờ để lưng cong khi nhấc tạ khỏi mặt đất.",
                "primary_muscle": "Back",
                "secondary_muscle": ["Hamstrings", "Glutes", "Forearms"],
                "tags": ["pull", "lower_body", "back", "compound", "barbell"]
            })
        elif "pull-up" in name_lower or "pull up" in name_lower:
            mock.update({
                "name_vie": "Hít xà đơn",
                "instructions_en": "Grip bar wider than shoulders. Pull your body up until chin clears the bar, then lower with control.",
                "instructions_vi": "Nắm xà đơn rộng hơn vai. Kéo cơ thể lên cho đến khi cằm vượt qua xà, sau đó hạ từ từ xuống.",
                "pro_tips_en": "Focus on driving your elbows down and squeezing your lats, not pull with biceps.",
                "pro_tips_vi": "Tập trung co thắt cơ xô (lats) thay vì kéo bằng lực bắp tay trước.",
                "tracking_type": "BODYWEIGHT_REPS",
                "primary_muscle": "Lats",
                "secondary_muscle": ["Biceps", "Upper Back"],
                "tags": ["pull", "back", "upper_body", "calisthenics"]
            })
        elif "plank" in name_lower:
            mock.update({
                "name_vie": "Tập bụng Plank",
                "instructions_en": "Place elbows directly under shoulders. Hold your body in a straight line from head to heels.",
                "instructions_vi": "Nằm sấp, chống khuỷu tay vuông góc với vai. Giữ cơ thể thẳng từ đầu đến gót chân.",
                "pro_tips_en": "Squeeze glutes and brace your core to prevent hips from sagging.",
                "pro_tips_vi": "Siết chặt cơ bụng và mông để giữ hông không bị võng xuống.",
                "tracking_type": "TIME",
                "primary_muscle": "Core",
                "secondary_muscle": ["Shoulders"],
                "tags": ["core", "bodyweight", "isometric"]
            })
            
        return mock
