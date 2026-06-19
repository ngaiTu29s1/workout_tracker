import logging
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.config import settings
from backend.app.models.exercise import ExerciseMaster

logger = logging.getLogger(__name__)

class EnrichmentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def enrich_exercise(self, exercise_id: int) -> ExerciseMaster:
        """
        Trigger AI enrichment via n8n webhook.
        If n8n is unconfigured or returns an error, falls back to a smart mock.
        """
        # Fetch exercise
        query = select(ExerciseMaster).where(ExerciseMaster.id == exercise_id)
        result = await self.db.execute(query)
        exercise = result.scalar_one_or_none()
        
        if not exercise:
            raise ValueError(f"Exercise with ID {exercise_id} not found.")

        payload = {
            "exercise_id": exercise.id,
            "name_eng": exercise.name_eng
        }

        enriched_data = None

        # Try to contact n8n
        if settings.N8N_WEBHOOK_URL and "change_me" not in settings.N8N_WEBHOOK_URL and "local" not in settings.N8N_WEBHOOK_URL:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        settings.N8N_WEBHOOK_URL,
                        json=payload,
                        timeout=10.0
                    )
                    if response.status_code == 200:
                        res_json = response.json()
                        if isinstance(res_json, list) and len(res_json) > 0:
                            enriched_data = res_json[0]
                        elif isinstance(res_json, dict):
                            enriched_data = res_json
                        else:
                            enriched_data = {}
                        logger.info("Successfully received enriched metadata from n8n.")
                    else:
                        logger.warning(f"n8n returned status code {response.status_code}. Using mock fallback.")
            except Exception as e:
                logger.warning(f"Failed to connect to n8n webhook at {settings.N8N_WEBHOOK_URL}: {e}. Using mock fallback.")

        # Fallback to Mock Data if no response from n8n
        if not enriched_data:
            enriched_data = self._generate_mock_metadata(exercise.name_eng)

        # Update exercise fields
        # Note: we update fields only if they are not already set, or we overwrite them
        # Let's overwrite them as this is the purpose of the enrichment trigger!
        if "name_vie" in enriched_data:
            exercise.name_vie = enriched_data["name_vie"]
        if "instructions" in enriched_data:
            exercise.instructions = enriched_data["instructions"]
        if "video_url" in enriched_data:
            exercise.video_url = enriched_data["video_url"]
        if "image_url" in enriched_data:
            exercise.image_url = enriched_data["image_url"]
        if "pro_tips" in enriched_data:
            exercise.pro_tips = enriched_data["pro_tips"]
        if "tracking_type" in enriched_data:
            exercise.tracking_type = enriched_data["tracking_type"]
        if "primary_muscle" in enriched_data:
            exercise.primary_muscle = enriched_data["primary_muscle"]
        if "secondary_muscle" in enriched_data:
            exercise.secondary_muscle = enriched_data["secondary_muscle"]
        if "tags" in enriched_data:
            exercise.tags = enriched_data["tags"]

        await self.db.commit()
        await self.db.refresh(exercise)
        return exercise

    def _generate_mock_metadata(self, name_eng: str) -> dict:
        """
        Generate smart mock metadata based on the English name of the exercise.
        """
        name_lower = name_eng.lower()
        
        # Default mock template
        mock = {
            "name_vie": f"{name_eng} (Bản dịch AI)",
            "instructions": f"Hướng dẫn cho bài tập {name_eng}: Thực hiện đúng tư thế, giữ lưng thẳng, hít vào khi hạ tạ và thở ra khi đẩy tạ.",
            "video_url": None,
            "image_url": None,
            "pro_tips": "Khởi động kỹ cơ khớp trước khi thực hiện. Không tập quá sức.",
            "tracking_type": "WEIGHT_REPS",
            "primary_muscle": "Full Body",
            "secondary_muscle": [],
            "tags": ["strength", "gym"]
        }

        # Specific exercises mapping for more realistic demo
        if "bench press" in name_lower:
            mock.update({
                "name_vie": "Đẩy ngực trên ghế bằng",
                "instructions": "Nằm trên ghế phẳng, nắm thanh đòn rộng hơn vai. Hạ thanh đòn xuống ngực và đẩy mạnh lên.",
                "video_url": None,
                "image_url": None,
                "pro_tips": "Giữ bả vai co lại và chạm vào ghế để bảo vệ khớp vai.",
                "tracking_type": "WEIGHT_REPS",
                "primary_muscle": "Chest",
                "secondary_muscle": ["Triceps", "Shoulders"],
                "tags": ["push", "chest", "upper_body", "barbell"]
            })
        elif "squat" in name_lower:
            mock.update({
                "name_vie": "Gánh đùi sau/trước (Squat)",
                "instructions": "Đặt thanh đòn trên cơ cầu vai. Hạ hông xuống như tư thế ngồi ghế cho đến khi đùi song song với sàn, rồi đứng thẳng dậy.",
                "video_url": None,
                "image_url": None,
                "pro_tips": "Đẩy gối ra ngoài và giữ cho lưng thẳng suốt quá trình chuyển động.",
                "tracking_type": "WEIGHT_REPS",
                "primary_muscle": "Quads",
                "secondary_muscle": ["Glutes", "Hamstrings", "Core"],
                "tags": ["legs", "lower_body", "compound", "barbell"]
            })
        elif "deadlift" in name_lower:
            mock.update({
                "name_vie": "Kéo tạ đòn (Deadlift)",
                "instructions": "Đứng sát thanh đòn, gập người nắm thanh đòn. Kéo thanh đòn thẳng lên sát chân bằng lực đùi sau và lưng dưới.",
                "video_url": None,
                "image_url": None,
                "pro_tips": "Không bao giờ để lưng cong khi nhấc tạ khỏi mặt đất.",
                "tracking_type": "WEIGHT_REPS",
                "primary_muscle": "Back",
                "secondary_muscle": ["Hamstrings", "Glutes", "Forearms"],
                "tags": ["pull", "lower_body", "back", "compound", "barbell"]
            })
        elif "pull-up" in name_lower or "pull up" in name_lower:
            mock.update({
                "name_vie": "Hít xà đơn",
                "instructions": "Nắm xà đơn rộng hơn vai. Kéo cơ thể lên cho đến khi cằm vượt qua xà, sau đó hạ từ từ xuống.",
                "video_url": None,
                "image_url": None,
                "pro_tips": "Tập trung co thắt cơ xô (lats) thay vì kéo bằng lực bắp tay trước.",
                "tracking_type": "BODYWEIGHT_REPS",
                "primary_muscle": "Lats",
                "secondary_muscle": ["Biceps", "Upper Back"],
                "tags": ["pull", "back", "upper_body", "calisthenics"]
            })
        elif "plank" in name_lower:
            mock.update({
                "name_vie": "Tập bụng Plank",
                "instructions": "Nằm sấp, chống khuỷu tay vuông góc với vai. Giữ cơ thể thẳng từ đầu đến gót chân.",
                "video_url": None,
                "image_url": None,
                "pro_tips": "Siết chặt cơ bụng và mông để giữ hông không bị võng xuống.",
                "tracking_type": "TIME",
                "primary_muscle": "Core",
                "secondary_muscle": ["Shoulders"],
                "tags": ["core", "bodyweight", "isometric"]
            })
            
        return mock

