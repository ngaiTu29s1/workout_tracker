import os
import json
import logging
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.pool import ExercisePool
from backend.app.models.exercise import ExerciseMaster
from backend.app.models.preset import WeeklyPreset
from backend.app.services.exercise_service import title_case_name
from backend.app.services.pool_service import infer_tracking_type

logger = logging.getLogger(__name__)

# Original 33 exercises metadata for Vietnamese name and pro-tip preservation
EXERCISES_SEED = [
    # === PUSH (Upper Body) ===
    {
        "name_eng": "Barbell Bench Press",
        "name_vie": "Đẩy ngực ngang tạ đòn",
        "pro_tips": "Siết bả vai ra sau và gồng cơ bụng để tạo bệ đỡ vững chắc. Giữ khuỷu tay hơi khép, tránh mở rộng 90 độ để bảo vệ khớp vai.",
    },
    {
        "name_eng": "Incline Dumbbell Press",
        "name_vie": "Đẩy ngực trên với tạ đơn",
        "pro_tips": "Không để ghế quá dốc vì lực sẽ ăn vào vai trước quá nhiều thay vì ngực trên. Tập trung kiểm soát tạ khi hạ xuống.",
    },
    {
        "name_eng": "Overhead Press (OHP)",
        "name_vie": "Đẩy vai qua đầu tạ đòn",
        "pro_tips": "Tránh ưỡn lưng dưới quá đà khi đẩy tạ lên bằng cách siết chặt cơ mông và cơ bụng suốt động tác.",
    },
    {
        "name_eng": "Parallel Bar Dips",
        "name_vie": "Chống xà kép (Dips)",
        "pro_tips": "Hơi nghiêng thân người về phía trước để kích hoạt cơ ngực dưới nhiều hơn. Nếu muốn tập trung vào tay sau, hãy giữ thân người thẳng đứng.",
    },
    {
        "name_eng": "Tricep Pushdown",
        "name_vie": "Kéo cáp cơ tay sau",
        "pro_tips": "Không di chuyển cùi chỏ ra trước hay ra sau để tập trung cô lập hoàn toàn vào cơ tay sau.",
    },
    {
        "name_eng": "Cable Fly",
        "name_vie": "Ép ngực với cáp",
        "pro_tips": "Tưởng tượng như bạn đang ôm một thân cây lớn để giữ khớp khuỷu cố định, tránh biến bài tập thành bài đẩy ngực.",
    },
    {
        "name_eng": "Dumbbell Lateral Raise",
        "name_vie": "Dang tay vai bên tạ đơn",
        "pro_tips": "Không nhún vai khi nâng tạ. Hãy tưởng tượng như bạn đang đẩy tạ ra xa hai bên thay vì kéo lên trên.",
    },
    {
        "name_eng": "Close-Grip Barbell Bench Press",
        "name_vie": "Đẩy ngực hẹp tay tạ đòn",
        "pro_tips": "Giữ cùi chỏ khép sát thân người trong suốt quá trình đẩy để tối ưu hóa việc kích hoạt cơ tay sau.",
    },
    {
        "name_eng": "Push-up",
        "name_vie": "Hít đất (Chống đẩy)",
        "pro_tips": "Giữ cơ thể thẳng từ đầu đến gót chân bằng cách siết chặt cơ bụng và cơ mông. Không để hông bị võng.",
    },

    # === PULL (Upper Body & Back) ===
    {
        "name_eng": "Barbell Deadlift",
        "name_vie": "Nhấc tạ đòn (Deadlift)",
        "pro_tips": "Gồng chặt cơ bụng và cơ xô để bảo vệ cột sống lưng dưới. Giữ thanh đòn di chuyển sát sát chân trong suốt hành trình.",
    },
    {
        "name_eng": "Barbell Row",
        "name_vie": "Gập người chèo tạ đòn",
        "pro_tips": "Kéo bằng khuỷu tay ra sau sát cơ thể để cảm nhận cơ xô tốt nhất. Tránh nhún nhảy hay dùng đà của thân trên.",
    },
    {
        "name_eng": "Pull-up",
        "name_vie": "Hít xà đơn (Pull-up)",
        "pro_tips": "Tránh đung đưa người. Hãy tưởng tượng bạn đang kéo thanh xà xuống phía ngực mình thay vì kéo người lên.",
    },
    {
        "name_eng": "Lat Pulldown",
        "name_vie": "Kéo cáp rộng tay (Lat Pulldown)",
        "pro_tips": "Tập trung kéo bằng cùi chỏ và siết cơ xô ở điểm cuối. Không ngả người ra sau quá nhiều.",
    },
    {
        "name_eng": "Face Pull",
        "name_vie": "Kéo cáp ngang mặt (Face Pull)",
        "pro_tips": "Tập trung xoay ngoài khớp vai ở cuối biên độ động tác để kích hoạt tối đa cơ vai sau và các cơ xoay vai.",
    },
    {
        "name_eng": "Dumbbell Bicep Curl",
        "name_vie": "Cuộn tay trước tạ đơn",
        "pro_tips": "Tránh đưa khuỷu tay ra trước khi cuộn tạ lên để giữ áp lực liên tục lên cơ tay trước.",
    },
    {
        "name_eng": "Incline Dumbbell Row",
        "name_vie": "Gập người chèo tạ đơn ghế dốc",
        "pro_tips": "Tư thế này giúp loại bỏ đà từ cơ thể và giảm áp lực lên lưng dưới, tối ưu hóa kích hoạt nhóm cơ lưng.",
    },
    {
        "name_eng": "Hammer Curl",
        "name_vie": "Cuộn tay trước kiểu búa",
        "pro_tips": "Bài tập này cực kỳ tốt cho cơ cánh tay quay (brachioradialis) và giúp tăng độ dày của bắp tay trước.",
    },
    {
        "name_eng": "Cable Seated Row",
        "name_vie": "Kéo cáp ngồi chèo thuyền",
        "pro_tips": "Ưỡn ngực khi kéo tạ về và tránh để lưng bị gù khi nhả tạ về phía trước.",
    },

    # === LEGS (Lower Body) ===
    {
        "name_eng": "Barbell Back Squat",
        "name_vie": "Gánh tạ đòn sau (Squat)",
        "pro_tips": "Luôn giữ bàn chân bám chặt trên sàn, không nhấc gót. Hướng đầu gối theo hướng mũi chân khi xuống.",
    },
    {
        "name_eng": "Leg Press",
        "name_vie": "Đạp đùi trên máy (Leg Press)",
        "pro_tips": "Tuyệt đối không khóa thẳng khớp gối ở điểm cao nhất để tránh chấn thương nghiêm trọng. Giữ mông áp sát vào ghế đệm.",
    },
    {
        "name_eng": "Leg Extension",
        "name_vie": "Đá đùi trước trên máy",
        "pro_tips": "Bám chặt tay vịn hai bên để giữ mông cố định trên ghế, tránh để hông nâng lên khi đá tạ.",
    },
    {
        "name_eng": "Seated Leg Curl",
        "name_vie": "Móc đùi sau ngồi trên máy",
        "pro_tips": "Kiểm soát tốc độ lúc thả tạ lên để cơ đùi sau được chịu áp lực liên tục.",
    },
    {
        "name_eng": "Standing Calf Raise",
        "name_vie": "Nhón bắp chuối đứng",
        "pro_tips": "Giữ ở điểm cao nhất và thấp nhất khoảng 1-2 giây để loại bỏ lực quán tính của gân Achilles.",
    },
    {
        "name_eng": "Romanian Deadlift",
        "name_vie": "Kéo đùi sau tạ đòn (RDL)",
        "pro_tips": "Tập trung đẩy hông ra sau để cảm nhận cơ đùi sau và mông căng tối đa, tránh dùng lưng dưới để cúi gập người.",
    },
    {
        "name_eng": "Dumbbell Lunges",
        "name_vie": "Bước chùng chân với tạ đơn",
        "pro_tips": "Giữ lưng thẳng đứng và không để đầu gối chân trước vượt quá mũi chân quá xa.",
    },
    {
        "name_eng": "Hip Thrust",
        "name_vie": "Đẩy hông với tạ đòn trên ghế",
        "pro_tips": "Siết chặt cơ mông ở điểm cao nhất trong 1-2 giây và giữ cằm hướng về phía ngực thay vì ngửa đầu ra sau.",
    },

    # === CORE & STABILIZATION ===
    {
        "name_eng": "Forearm Plank",
        "name_vie": "Gồng bụng Plank cẳng tay",
        "pro_tips": "Tránh để hông bị võng xuống hay đẩy lên cao. Thực hiện xoay nhẹ xương chậu ra sau để kích hoạt cơ bụng tối đa.",
    },
    {
        "name_eng": "Cable Crunch",
        "name_vie": "Quỳ gập bụng với cáp",
        "pro_tips": "Tránh gập hông để kéo tạ. Hãy tập trung cuộn tròn cột sống để cơ bụng chịu hoàn toàn lực kéo.",
    },
    {
        "name_eng": "Hanging Leg Raise",
        "name_vie": "Treo người nâng chân tập bụng",
        "pro_tips": "Kiểm soát tốc độ lúc hạ xuống để tránh đung đưa người. Tập trung cuộn xương chậu lên để ăn vào cơ bụng dưới.",
    },
    {
        "name_eng": "Russian Twist",
        "name_vie": "Xoay người kiểu Nga",
        "pro_tips": "Di chuyển bằng cách xoay lồng ngực từ bên này sang bên kia, không chỉ di chuyển cánh tay.",
    },

    # === CARDIO / ENDURANCE ===
    {
        "name_eng": "Treadmill Run",
        "name_vie": "Chạy bộ trên máy",
        "pro_tips": "Giữ cơ thể thẳng đứng, đánh tay tự nhiên bên hông. Bắt đầu bằng chạy chậm khởi động trước khi tăng tốc.",
    },
    {
        "name_eng": "Rowing Machine",
        "name_vie": "Tập chèo thuyền trên máy",
        "pro_tips": "Lực chèo chia làm 60% từ chân, 20% từ việc giữ cơ bụng/lưng, và 20% từ lực kéo của tay.",
    },
    {
        "name_eng": "Stationary Bicycle",
        "name_vie": "Đạp xe đạp cơ học",
        "pro_tips": "Yên xe nên ở độ cao sao cho khi chân ở điểm thấp nhất đầu gối vẫn hơi cong nhẹ khoảng 10-15 độ.",
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

def get_preset_seed_info(name_eng: str):
    name_eng_lower = name_eng.lower()
    for ex in EXERCISES_SEED:
        ex_lower = ex["name_eng"].lower()
        # Clean special characters/helpers
        ex_clean = ex_lower.replace("(ohp)", "").strip()
        if ex_clean in name_eng_lower or name_eng_lower in ex_clean:
            return ex
    return None

async def seed_pool(db: AsyncSession) -> None:
    """Seed exercise_pool from exercises.json (1324 rows)."""
    pool_count = await db.scalar(select(func.count(ExercisePool.id)))
    
    if pool_count >= 1324:
        logger.info(f"Pool already seeded ({pool_count}). Skipping.")
        return
        
    if pool_count > 0:
        logger.info(f"Partial pool data found ({pool_count}). Clearing and re-seeding...")
        await db.execute(ExercisePool.__table__.delete())
        await db.flush()

    # Find the json dataset path robustly
    paths_to_try = [
        os.getenv("POOL_DATA_PATH", "/app/static/pool") + "/exercises.json",
        "data/exercise-pool/exercises.json",
        "../data/exercise-pool/exercises.json",
        "/app/static/pool/exercises.json"
    ]
    json_path = None
    for p in paths_to_try:
        if os.path.exists(p):
            json_path = p
            break

    if not json_path:
        raise FileNotFoundError("Could not locate exercises.json dataset in any path.")

    logger.info(f"Loading pool exercises from {json_path}...")
    with open(json_path) as f:
        exercises = json.load(f)

    for ex in exercises:
        pool_ex = ExercisePool(
            pool_id=ex["id"],
            name=ex["name"],
            category=ex.get("category"),
            body_part=ex.get("body_part"),
            equipment=ex.get("equipment"),
            target=ex.get("target"),
            instructions_en=ex.get("instructions", {}).get("en"),
            instructions_vi=ex.get("instructions", {}).get("vi"), # map vi if preset
            muscle_group=ex.get("muscle_group"),
            secondary_muscles=ex.get("secondary_muscles", []),
            image_path=ex.get("image"),
            gif_path=ex.get("gif_url"),
        )
        db.add(pool_ex)
    
    await db.commit()
    logger.info(f"Successfully seeded {len(exercises)} exercises into pool.")

async def seed_personal_defaults(db: AsyncSession) -> None:
    """Seed 33 default personal exercises by searching the newly seeded pool."""
    personal_count = await db.scalar(select(func.count(ExerciseMaster.id)))
    if personal_count > 0:
        logger.info(f"Personal exercises exist ({personal_count}). Skipping.")
        return

    DEFAULT_EXERCISES = [
        # === PUSH ===
        {"search": "barbell bench press", "tags": ["push", "upper_body", "compound"]},
        {"search": "dumbbell incline bench press", "tags": ["push", "upper_body", "compound"]},
        {"search": "barbell seated overhead press", "tags": ["push", "upper_body", "compound"]},
        {"search": "assisted chest dip (kneeling)", "tags": ["push", "upper_body", "compound"]},
        {"search": "cable pushdown", "tags": ["push", "upper_body", "isolation"]},
        {"search": "cable incline fly", "tags": ["push", "upper_body", "isolation"]},
        {"search": "dumbbell lateral raise", "tags": ["push", "upper_body", "isolation"]},
        {"search": "barbell incline close grip bench press", "tags": ["push", "upper_body", "compound"]},
        {"search": "push-up", "tags": ["push", "upper_body", "compound"]},
        
        # === PULL ===
        {"search": "barbell deadlift", "tags": ["pull", "legs", "lower_body", "compound"]},
        {"search": "barbell bent over row", "tags": ["pull", "upper_body", "compound"]},
        {"search": "pull-up", "tags": ["pull", "upper_body", "compound"]},
        {"search": "alternate lateral pulldown", "tags": ["pull", "upper_body", "compound"]},
        {"search": "cable standing rear delt row (with rope)", "tags": ["pull", "upper_body", "isolation"]},
        {"search": "dumbbell biceps curl", "tags": ["pull", "upper_body", "isolation"]},
        {"search": "dumbbell incline row", "tags": ["pull", "upper_body", "compound"]},
        {"search": "dumbbell alternate seated hammer curl", "tags": ["pull", "upper_body", "isolation"]},
        {"search": "cable low seated row", "tags": ["pull", "upper_body", "compound"]},
        
        # === LEGS ===
        {"search": "barbell squat", "tags": ["legs", "lower_body", "compound"]},
        {"search": "lever alternate leg press", "tags": ["legs", "lower_body", "compound"]},
        {"search": "lever leg extension", "tags": ["legs", "lower_body", "isolation"]},
        {"search": "lever seated leg curl", "tags": ["legs", "lower_body", "isolation"]},
        {"search": "barbell standing calf raise", "tags": ["legs", "lower_body", "isolation"]},
        {"search": "barbell romanian deadlift", "tags": ["legs", "pull", "lower_body", "compound"]},
        {"search": "dumbbell lunge", "tags": ["legs", "lower_body", "compound"]},
        {"search": "resistance band hip thrusts on knees (female)", "tags": ["legs", "lower_body", "compound"]},
        
        # === CORE ===
        {"search": "weighted front plank", "tags": ["push", "pull", "legs", "bodyweight"]},
        {"search": "cable kneeling crunch", "tags": ["pull", "upper_body", "isolation"]},
        {"search": "hanging leg raise", "tags": ["legs", "pull", "upper_body", "isolation"]},
        {"search": "assisted motion russian twist", "tags": ["pull", "bodyweight", "isolation"]},
        
        # === CARDIO ===
        {"search": "walking on incline treadmill", "tags": ["legs", "lower_body", "bodyweight"]},
        {"search": "bodyweight standing row", "tags": ["pull", "legs", "lower_body", "upper_body", "compound"]},
        {"search": "stationary bike run v. 3", "tags": ["legs", "lower_body"]}
    ]

    logger.info("Seeding default personal exercises...")
    for entry in DEFAULT_EXERCISES:
        # Try exact case-insensitive match first
        pool_ex = await db.scalar(
            select(ExercisePool).where(
                ExercisePool.name.ilike(entry["search"])
            ).limit(1)
        )
        if not pool_ex:
            # Fallback to fuzzy match
            pool_ex = await db.scalar(
                select(ExercisePool).where(
                    ExercisePool.name.ilike(f"%{entry['search']}%")
                ).limit(1)
            )

        if pool_ex:
            # Look up handcrafted Vietnamese names & pro-tips
            seed_info = get_preset_seed_info(pool_ex.name)
            name_vie = seed_info["name_vie"] if seed_info else None
            pro_tips = seed_info["pro_tips"] if seed_info else None

            personal = ExerciseMaster(
                pool_id=pool_ex.id,
                name_eng=title_case_name(pool_ex.name),
                name_vie=name_vie,
                instructions=pool_ex.instructions_vi or pool_ex.instructions_en,
                image_url=f"/pool/{pool_ex.image_path}" if pool_ex.image_path else None,
                video_url=f"/pool/{pool_ex.gif_path}" if pool_ex.gif_path else None,
                pro_tips=pro_tips,
                primary_muscle=pool_ex.muscle_group,
                secondary_muscle=pool_ex.secondary_muscles or [],
                tags=entry["tags"],
                tracking_type=infer_tracking_type(pool_ex.equipment, pool_ex.category),
            )
            db.add(personal)
        else:
            logger.warning(f"Failed to find pool match for: {entry['search']}")
            
    await db.commit()
    logger.info("Successfully seeded personal defaults.")

async def seed_weekly_presets(db: AsyncSession) -> None:
    """Seed weekly presets if table is empty."""
    preset_count = await db.scalar(select(func.count(WeeklyPreset.day_of_week)))
    if preset_count == 0:
        logger.info("Weekly presets table is empty. Seeding presets...")
        for p in WEEKLY_PRESETS_SEED:
            db_p = WeeklyPreset(**p)
            db.add(db_p)
        await db.commit()
        logger.info(f"Successfully seeded {len(WEEKLY_PRESETS_SEED)} weekly presets.")
    else:
        logger.info("Weekly presets already exist. Skipping preset seeding.")

async def seed_db(db: AsyncSession) -> None:
    """Main seed entry point."""
    await seed_pool(db)
    await seed_personal_defaults(db)
    await seed_weekly_presets(db)
