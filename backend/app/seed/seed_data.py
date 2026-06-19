import logging
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.exercise import ExerciseMaster
from backend.app.models.preset import WeeklyPreset

logger = logging.getLogger(__name__)

# ~30 classic exercises categorized as Push, Pull, Legs, Core, Cardio
EXERCISES_SEED = [
    # === PUSH ===
    {
        "name_eng": "Barbell Bench Press",
        "name_vie": "Đẩy ngực ngang tạ đòn",
        "instructions": "Nằm ngửa trên ghế phẳng. Nắm thanh đòn rộng hơn vai. Hạ tạ xuống chạm nhẹ ngực rồi đẩy mạnh lên.",
        "video_url": "https://www.w3schools.com/html/mov_bbb.mp4",
        "image_url": "https://images.unsplash.com/photo-1571019614242-c5c5dee9f50b?w=500",
        "pro_tips": "Siết bả vai ra sau và gồng cơ bụng để tạo bệ đỡ vững chắc.",
        "tracking_type": "WEIGHT_REPS",
        "primary_muscle": "Chest",
        "secondary_muscle": ["Triceps", "Shoulders"],
        "tags": ["push", "chest", "barbell", "upper_body"]
    },
    {
        "name_eng": "Incline Dumbbell Press",
        "name_vie": "Đẩy ngực trên với tạ đơn",
        "instructions": "Ngồi trên ghế dốc lên 30-45 độ. Cầm tạ đơn ở hai bên ngực. Đẩy tạ lên cao thẳng tay rồi hạ xuống kiểm soát.",
        "video_url": "https://www.w3schools.com/html/mov_bbb.mp4",
        "image_url": "https://images.unsplash.com/photo-1571019614242-c5c5dee9f50b?w=500",
        "pro_tips": "Đừng để ghế quá dốc vì lực sẽ ăn vào vai trước quá nhiều.",
        "tracking_type": "WEIGHT_REPS",
        "primary_muscle": "Chest",
        "secondary_muscle": ["Shoulders", "Triceps"],
        "tags": ["push", "chest", "dumbbell", "upper_body"]
    },
    {
        "name_eng": "Overhead Press (OHP)",
        "name_vie": "Đẩy vai qua đầu tạ đòn",
        "instructions": "Đứng thẳng gồng bụng hông. Cầm tạ đòn ngang ngực. Đẩy thẳng tạ lên trên qua đầu rồi hạ về vị trí cũ.",
        "video_url": "https://www.w3schools.com/html/mov_bbb.mp4",
        "image_url": "https://images.unsplash.com/photo-1571019614242-c5c5dee9f50b?w=500",
        "pro_tips": "Tránh ưỡn lưng dưới quá đà khi đẩy tạ lên.",
        "tracking_type": "WEIGHT_REPS",
        "primary_muscle": "Shoulders",
        "secondary_muscle": ["Triceps", "Core"],
        "tags": ["push", "shoulders", "barbell", "upper_body"]
    },
    {
        "name_eng": "Parallel Bar Dips",
        "name_vie": "Chống xà kép (Dips)",
        "instructions": "Bám hai tay vào xà kép, nâng cơ thể lên. Gập cùi chỏ hạ cơ thể xuống đến khi cánh tay vuông góc rồi đẩy lên.",
        "video_url": "https://www.w3schools.com/html/mov_bbb.mp4",
        "image_url": "https://images.unsplash.com/photo-1571019614242-c5c5dee9f50b?w=500",
        "pro_tips": "Hơi nghiêng người về phía trước để kích hoạt cơ ngực dưới nhiều hơn.",
        "tracking_type": "BODYWEIGHT_REPS",
        "primary_muscle": "Chest",
        "secondary_muscle": ["Triceps", "Shoulders"],
        "tags": ["push", "triceps", "chest", "bodyweight", "upper_body"]
    },
    {
        "name_eng": "Tricep Pushdown",
        "name_vie": "Kéo cáp cơ tay sau",
        "instructions": "Đứng đối diện máy cáp, cầm tay cầm dây thừng hoặc thanh thẳng. Ghim cùi chỏ sát sườn, kéo cáp xuống thẳng tay.",
        "video_url": "https://www.w3schools.com/html/mov_bbb.mp4",
        "image_url": "https://images.unsplash.com/photo-1571019614242-c5c5dee9f50b?w=500",
        "pro_tips": "Không di chuyển cùi chỏ ra trước sau để tập trung hoàn toàn vào tay sau.",
        "tracking_type": "WEIGHT_REPS",
        "primary_muscle": "Triceps",
        "secondary_muscle": [],
        "tags": ["push", "triceps", "cable", "upper_body"]
    },
    {
        "name_eng": "Cable Fly",
        "name_vie": "Ép ngực với cáp",
        "instructions": "Đứng giữa hai cột cáp cao. Cầm tay cầm cáp kéo ép vào nhau phía trước ngực với cùi chỏ hơi cong.",
        "video_url": "https://www.w3schools.com/html/mov_bbb.mp4",
        "image_url": "https://images.unsplash.com/photo-1571019614242-c5c5dee9f50b?w=500",
        "pro_tips": "Tưởng tượng như bạn đang ôm một thân cây lớn để giữ khớp khuỷu cố định.",
        "tracking_type": "WEIGHT_REPS",
        "primary_muscle": "Chest",
        "secondary_muscle": ["Shoulders"],
        "tags": ["push", "chest", "cable", "upper_body"]
    },
    
    # === PULL ===
    {
        "name_eng": "Barbell Deadlift",
        "name_vie": "Nhấc tạ đòn (Deadlift)",
        "instructions": "Đứng sát thanh đòn. Gập người cúi xuống nắm tạ. Giữ lưng thẳng, đạp chân đẩy hông đứng dậy kéo tạ lên sát người.",
        "video_url": "https://www.w3schools.com/html/mov_bbb.mp4",
        "image_url": "https://images.unsplash.com/photo-1517838277536-f5f99be501cd?w=500",
        "pro_tips": "Gồng chặt cơ xô và giữ thẳng lưng suốt buổi tập.",
        "tracking_type": "WEIGHT_REPS",
        "primary_muscle": "Back",
        "secondary_muscle": ["Hamstrings", "Glutes", "Core"],
        "tags": ["pull", "back", "hamstrings", "barbell", "compound", "lower_body"]
    },
    {
        "name_eng": "Barbell Row",
        "name_vie": "Gập người chèo tạ đòn",
        "instructions": "Cúi gập người góc 45 độ, giữ thẳng lưng. Nắm thanh đòn kéo về phía bụng dưới rồi hạ xuống có kiểm soát.",
        "video_url": "https://www.w3schools.com/html/mov_bbb.mp4",
        "image_url": "https://images.unsplash.com/photo-1517838277536-f5f99be501cd?w=500",
        "pro_tips": "Kéo khuỷu tay ra sau sát cơ thể để cảm nhận cơ xô tốt nhất.",
        "tracking_type": "WEIGHT_REPS",
        "primary_muscle": "Back",
        "secondary_muscle": ["Biceps", "Shoulders"],
        "tags": ["pull", "back", "barbell", "upper_body"]
    },
    {
        "name_eng": "Pull-up",
        "name_vie": "Hít xà đơn (Pull-up)",
        "instructions": "Bám tay rộng trên xà. Kéo cơ thể lên sao cho cằm vượt qua xà rồi từ từ hạ xuống hết tay.",
        "video_url": "https://www.w3schools.com/html/mov_bbb.mp4",
        "image_url": "https://images.unsplash.com/photo-1517838277536-f5f99be501cd?w=500",
        "pro_tips": "Tránh đu đưa người quá nhiều, hãy dùng sức mạnh cơ xô cô lập.",
        "tracking_type": "BODYWEIGHT_REPS",
        "primary_muscle": "Lats",
        "secondary_muscle": ["Biceps", "Upper Back"],
        "tags": ["pull", "back", "bodyweight", "upper_body"]
    },
    {
        "name_eng": "Lat Pulldown",
        "name_vie": "Kéo cáp rộng tay (Lat Pulldown)",
        "instructions": "Ngồi vào máy kéo cáp, cầm thanh kéo rộng tay. Kéo thanh cáp xuống sát ngực trên rồi từ từ nhả tạ lên.",
        "video_url": "https://www.w3schools.com/html/mov_bbb.mp4",
        "image_url": "https://images.unsplash.com/photo-1517838277536-f5f99be501cd?w=500",
        "pro_tips": "Ưỡn nhẹ ngực ra trước và hướng khuỷu tay xuống sàn khi kéo.",
        "tracking_type": "WEIGHT_REPS",
        "primary_muscle": "Lats",
        "secondary_muscle": ["Biceps", "Upper Back"],
        "tags": ["pull", "back", "cable", "upper_body"]
    },
    {
        "name_eng": "Face Pull",
        "name_vie": "Kéo cáp ngang mặt (Face Pull)",
        "instructions": "Cầm dây thừng trên máy cáp ngang mặt. Kéo cáp về hướng mặt đồng thời mở rộng khuỷu tay sang hai bên.",
        "video_url": "https://www.w3schools.com/html/mov_bbb.mp4",
        "image_url": "https://images.unsplash.com/photo-1517838277536-f5f99be501cd?w=500",
        "pro_tips": "Đây là bài tuyệt vời để sửa tư thế gù và phục hồi vai sau.",
        "tracking_type": "WEIGHT_REPS",
        "primary_muscle": "Shoulders",
        "secondary_muscle": ["Upper Back"],
        "tags": ["pull", "shoulders", "cable", "upper_body"]
    },
    {
        "name_eng": "Dumbbell Bicep Curl",
        "name_vie": "Cuộn tay trước tạ đơn",
        "instructions": "Đứng thẳng cầm tạ đơn hai bên tay. Cuộn tạ đơn lên xoay lòng bàn tay hướng lên trên rồi hạ xuống.",
        "video_url": "https://www.w3schools.com/html/mov_bbb.mp4",
        "image_url": "https://images.unsplash.com/photo-1517838277536-f5f99be501cd?w=500",
        "pro_tips": "Không khóa khớp khuỷu tay hoàn toàn khi hạ tạ.",
        "tracking_type": "WEIGHT_REPS",
        "primary_muscle": "Biceps",
        "secondary_muscle": ["Forearms"],
        "tags": ["pull", "biceps", "dumbbell", "upper_body"]
    },

    # === LEGS ===
    {
        "name_eng": "Barbell Back Squat",
        "name_vie": "Gánh tạ đòn sau (Squat)",
        "instructions": "Đặt tạ đòn trên vai. Hạ hông ngồi xuống giống như đang ngồi ghế cho đến khi đùi song song mặt đất rồi đứng lên.",
        "video_url": "https://www.w3schools.com/html/mov_bbb.mp4",
        "image_url": "https://images.unsplash.com/photo-1574680096145-d05b474e2155?w=500",
        "pro_tips": "Giữ vững bàn chân và đẩy đầu gối theo hướng mũi chân.",
        "tracking_type": "WEIGHT_REPS",
        "primary_muscle": "Quads",
        "secondary_muscle": ["Glutes", "Hamstrings", "Core"],
        "tags": ["legs", "quads", "barbell", "compound", "lower_body"]
    },
    {
        "name_eng": "Leg Press",
        "name_vie": "Đạp đùi trên máy (Leg Press)",
        "instructions": "Ngồi vào máy ép đùi, đặt hai chân lên bàn đạp rộng bằng vai. Mở chốt an toàn, hạ chân xuống rồi đạp mạnh lên.",
        "video_url": "https://www.w3schools.com/html/mov_bbb.mp4",
        "image_url": "https://images.unsplash.com/photo-1574680096145-d05b474e2155?w=500",
        "pro_tips": "Tuyệt đối không khóa thẳng khớp gối ở điểm cao nhất để tránh chấn thương nghiêm trọng.",
        "tracking_type": "WEIGHT_REPS",
        "primary_muscle": "Quads",
        "secondary_muscle": ["Glutes", "Hamstrings"],
        "tags": ["legs", "quads", "machine", "lower_body"]
    },
    {
        "name_eng": "Leg Extension",
        "name_vie": "Đá đùi trước máy",
        "instructions": "Ngồi vào máy đá đùi, đặt cổ chân dưới đệm. Đá chân thẳng lên cao giữ 1 giây rồi hạ từ từ xuống.",
        "video_url": "https://www.w3schools.com/html/mov_bbb.mp4",
        "image_url": "https://images.unsplash.com/photo-1574680096145-d05b474e2155?w=500",
        "pro_tips": "Giữ mông cố định trên ghế bằng cách bám chặt tay vịn hai bên.",
        "tracking_type": "WEIGHT_REPS",
        "primary_muscle": "Quads",
        "secondary_muscle": [],
        "tags": ["legs", "quads", "machine", "lower_body"]
    },
    {
        "name_eng": "Seated Leg Curl",
        "name_vie": "Móc đùi sau ngồi máy",
        "instructions": "Ngồi vào máy móc đùi sau. Co chân gập cẳng chân ra sau hướng xuống dưới sàn hết cỡ rồi từ từ thả lên.",
        "video_url": "https://www.w3schools.com/html/mov_bbb.mp4",
        "image_url": "https://images.unsplash.com/photo-1574680096145-d05b474e2155?w=500",
        "pro_tips": "Kiểm soát cơ đùi sau siết lại tối đa ở điểm gập chân.",
        "tracking_type": "WEIGHT_REPS",
        "primary_muscle": "Hamstrings",
        "secondary_muscle": ["Calves"],
        "tags": ["legs", "hamstrings", "machine", "lower_body"]
    },
    {
        "name_eng": "Standing Calf Raise",
        "name_vie": "Nhón bắp chuối đứng",
        "instructions": "Đứng nhón chân trên bục. Hạ gót chân xuống sâu nhất có thể rồi nhón cao gót hết cỡ nâng cơ thể lên.",
        "video_url": "https://www.w3schools.com/html/mov_bbb.mp4",
        "image_url": "https://images.unsplash.com/photo-1574680096145-d05b474e2155?w=500",
        "pro_tips": "Giữ ở điểm cao nhất 1 giây để bắp chuối được co cơ tối đa.",
        "tracking_type": "WEIGHT_REPS",
        "primary_muscle": "Calves",
        "secondary_muscle": [],
        "tags": ["legs", "calves", "dumbbell", "bodyweight", "lower_body"]
    },
    {
        "name_eng": "Romanian Deadlift",
        "name_vie": "Kéo đùi sau tạ đòn (RDL)",
        "instructions": "Đứng thẳng giữ tạ đòn sát đùi. Hơi chùng gối nhẹ, đẩy hông hết cỡ ra sau, hạ tạ dọc theo chân cho tới dưới gối rồi kéo lên.",
        "video_url": "https://www.w3schools.com/html/mov_bbb.mp4",
        "image_url": "https://images.unsplash.com/photo-1574680096145-d05b474e2155?w=500",
        "pro_tips": "Hãy nghĩ về việc đẩy hông ra sau hơn là gập người xuống.",
        "tracking_type": "WEIGHT_REPS",
        "primary_muscle": "Hamstrings",
        "secondary_muscle": ["Glutes", "Back"],
        "tags": ["legs", "hamstrings", "glutes", "barbell", "lower_body"]
    },

    # === CORE ===
    {
        "name_eng": "Forearm Plank",
        "name_vie": "Gồng bụng Plank",
        "instructions": "Tì khuỷu tay và mũi chân trên sàn. Giữ cơ thể thẳng tắp như tấm ván, siết bụng hông mông chặt.",
        "video_url": "https://www.w3schools.com/html/mov_bbb.mp4",
        "image_url": "https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=500",
        "pro_tips": "Đừng để hông bị võng hay nhô lên quá cao.",
        "tracking_type": "TIME",
        "primary_muscle": "Core",
        "secondary_muscle": ["Shoulders", "Glutes"],
        "tags": ["core", "bodyweight", "isometric"]
    },
    {
        "name_eng": "Cable Crunch",
        "name_vie": "Quỳ gập bụng kéo cáp",
        "instructions": "Quỳ trước máy cáp, cầm dây thừng ghim sát tai. Gập người kéo cùi chỏ hướng về đùi bằng cơ bụng.",
        "video_url": "https://www.w3schools.com/html/mov_bbb.mp4",
        "image_url": "https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=500",
        "pro_tips": "Cố gắng cuộn cột sống lại chứ không chỉ đơn giản là gập hông xuống.",
        "tracking_type": "WEIGHT_REPS",
        "primary_muscle": "Core",
        "secondary_muscle": [],
        "tags": ["core", "cable"]
    },
    {
        "name_eng": "Hanging Leg Raise",
        "name_vie": "Treo người nâng chân",
        "instructions": "Treo người trên thanh xà. Giữ chân thẳng (hoặc gập gối), dùng cơ bụng nâng chân lên cao vuông góc cơ thể.",
        "video_url": "https://www.w3schools.com/html/mov_bbb.mp4",
        "image_url": "https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=500",
        "pro_tips": "Kiểm soát tốc độ lúc hạ chân xuống để tránh đung đưa cơ thể.",
        "tracking_type": "BODYWEIGHT_REPS",
        "primary_muscle": "Core",
        "secondary_muscle": ["Hip Flexors"],
        "tags": ["core", "bodyweight", "upper_body"]
    },

    # === CARDIO ===
    {
        "name_eng": "Treadmill Run",
        "name_vie": "Chạy bộ máy (Treadmill)",
        "instructions": "Bật máy chạy bộ, chọn độ dốc và tốc độ phù hợp rồi bắt đầu chạy bộ nhịp nhàng.",
        "video_url": "https://www.w3schools.com/html/mov_bbb.mp4",
        "image_url": "https://images.unsplash.com/photo-1597452243004-db7480f2495d?w=500",
        "pro_tips": "Luôn đeo dây an toàn để tránh tai nạn té ngã trên máy.",
        "tracking_type": "TIME",
        "primary_muscle": "Cardio",
        "secondary_muscle": ["Quads", "Calves"],
        "tags": ["cardio", "stamina"]
    },
    {
        "name_eng": "Rowing Machine",
        "name_vie": "Chèo thuyền máy (Rowing)",
        "instructions": "Ngồi trên máy chèo thuyền, buộc chân. Đạp mạnh chân thẳng rồi ngửa lưng kéo tay cầm cáp sát bụng.",
        "video_url": "https://www.w3schools.com/html/mov_bbb.mp4",
        "image_url": "https://images.unsplash.com/photo-1597452243004-db7480f2495d?w=500",
        "pro_tips": "Giai đoạn đẩy xuất phát từ chân (60%), lưng (20%) và tay (20%).",
        "tracking_type": "TIME",
        "primary_muscle": "Cardio",
        "secondary_muscle": ["Back", "Legs", "Arms"],
        "tags": ["cardio", "stamina", "full_body"]
    }
]

WEEKLY_PRESETS_SEED = [
    {"day_of_week": 1, "routine_tag": "rest"},    # Sunday
    {"day_of_week": 2, "routine_tag": "push"},    # Monday
    {"day_of_week": 3, "routine_tag": "pull"},    # Tuesday
    {"day_of_week": 4, "routine_tag": "legs"},    # Wednesday
    {"day_of_week": 5, "routine_tag": "push"},    # Thursday
    {"day_of_week": 6, "routine_tag": "pull"},    # Friday
    {"day_of_week": 7, "routine_tag": "legs"}     # Saturday
]

async def seed_db(db: AsyncSession) -> None:
    """
    Seed the database with default exercises and weekly presets if they don't exist.
    """
    # 1. Seed Exercises
    exercise_count_query = select(func.count(ExerciseMaster.id))
    result = await db.execute(exercise_count_query)
    count = result.scalar()

    if count == 0:
        logger.info("Database is empty. Seeding exercises...")
        for ex in EXERCISES_SEED:
            db_ex = ExerciseMaster(**ex)
            db.add(db_ex)
        await db.commit()
        logger.info(f"Successfully seeded {len(EXERCISES_SEED)} exercises.")
    else:
        logger.info("Exercises already exist. Skipping exercise seeding.")

    # 2. Seed Weekly Presets
    preset_count_query = select(func.count(WeeklyPreset.day_of_week))
    result_preset = await db.execute(preset_count_query)
    preset_count = result_preset.scalar()

    if preset_count == 0:
        logger.info("Weekly presets table is empty. Seeding presets...")
        for p in WEEKLY_PRESETS_SEED:
            db_p = WeeklyPreset(**p)
            db.add(db_p)
        await db.commit()
        logger.info(f"Successfully seeded {len(WEEKLY_PRESETS_SEED)} weekly presets.")
    else:
        logger.info("Weekly presets already exist. Skipping preset seeding.")
