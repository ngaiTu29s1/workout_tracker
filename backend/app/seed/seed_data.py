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

# Original 33 exercises metadata with bilingual names, instructions, and pro-tips
EXERCISES_SEED = [
    # === PUSH (Upper Body) ===
    {
        "name_eng": "Barbell Bench Press",
        "name_vie": "Đẩy ngực ngang tạ đòn",
        "instructions_vi": "Nằm ngửa trên ghế phẳng, nắm thanh đòn rộng hơn vai một chút. Hạ thanh đòn xuống ngực và đẩy mạnh lên.",
        "pro_tips_vi": "Siết bả vai ra sau và gồng cơ bụng để tạo bệ đỡ vững chắc. Giữ khuỷu tay hơi khép, tránh mở rộng 90 độ để bảo vệ khớp vai.",
        "pro_tips_en": "Retract your shoulder blades and brace your core to create a solid base. Keep elbows slightly tucked to protect shoulders.",
    },
    {
        "name_eng": "Incline Dumbbell Press",
        "name_vie": "Đẩy ngực trên với tạ đơn",
        "instructions_vi": "Nằm trên ghế dốc lên, đẩy tạ đơn từ sát ngực thẳng lên cao rồi hạ xuống có kiểm soát.",
        "pro_tips_vi": "Không để ghế quá dốc vì lực sẽ ăn vào vai trước quá nhiều thay vì ngực trên. Tập trung kiểm soát tạ khi hạ xuống.",
        "pro_tips_en": "Do not make the incline too steep as it will target front delts too much. Control the weight during the descent.",
    },
    {
        "name_eng": "Overhead Press (OHP)",
        "name_vie": "Đẩy vai qua đầu tạ đòn",
        "instructions_vi": "Đứng thẳng lưng, đẩy thanh đòn từ vị trí ngang vai qua đầu cho đến khi thẳng tay.",
        "pro_tips_vi": "Tránh ưỡn lưng dưới quá đà khi đẩy tạ lên bằng cách siết chặt cơ mông và cơ bụng suốt động tác.",
        "pro_tips_en": "Avoid excessive arching of the lower back by squeezing glutes and core throughout the movement.",
    },
    {
        "name_eng": "Parallel Bar Dips",
        "name_vie": "Chống xà kép (Dips)",
        "instructions_vi": "Bám hai tay vào xà kép, hạ cơ thể xuống bằng cách gập khuỷu tay rồi đẩy người lên.",
        "pro_tips_vi": "Hơi nghiêng thân người về phía trước để kích hoạt cơ ngực dưới nhiều hơn. Nếu muốn tập trung vào tay sau, hãy giữ thân người thẳng đứng.",
        "pro_tips_en": "Lean forward slightly to target lower chest, or keep torso upright to focus on triceps.",
    },
    {
        "name_eng": "Tricep Pushdown",
        "name_vie": "Kéo cáp cơ tay sau",
        "instructions_vi": "Đứng trước máy kéo cáp, dùng lực cơ tay sau đẩy thanh cầm xuống cho đến khi tay duỗi thẳng.",
        "pro_tips_vi": "Không di chuyển cùi chỏ ra trước hay ra sau để tập trung cô lập hoàn toàn vào cơ tay sau.",
        "pro_tips_en": "Keep elbows locked at your sides to isolate the triceps completely.",
    },
    {
        "name_eng": "Cable Fly",
        "name_vie": "Ép ngực với cáp",
        "instructions_vi": "Đứng giữa giàn cáp dốc, kéo và ép hai tay lại với nhau trước ngực theo đường vòng cung.",
        "pro_tips_vi": "Tưởng tượng như bạn đang ôm một thân cây lớn để giữ khớp khuỷu cố định, tránh biến bài tập thành bài đẩy ngực.",
        "pro_tips_en": "Imagine hugging a large tree to keep elbows at a fixed angle, avoiding pressing.",
    },
    {
        "name_eng": "Dumbbell Lateral Raise",
        "name_vie": "Dang tay vai bên tạ đơn",
        "instructions_vi": "Đứng thẳng, hai tay cầm tạ đơn dang rộng sang hai bên cho đến khi song song với mặt đất.",
        "pro_tips_vi": "Không nhún vai khi nâng tạ. Hãy tưởng tượng như bạn đang đẩy tạ ra xa hai bên thay vì kéo lên trên.",
        "pro_tips_en": "Lead with your elbows and avoid shrugging. Think about pushing weights outward.",
    },
    {
        "name_eng": "Close-Grip Barbell Bench Press",
        "name_vie": "Đẩy ngực hẹp tay tạ đòn",
        "instructions_vi": "Nằm đẩy ngực với thanh đòn nhưng khoảng cách hai tay nắm hẹp hơn vai (tầm 20-30cm).",
        "pro_tips_vi": "Giữ cùi chỏ khép sát thân người trong suốt quá trình đẩy để tối ưu hóa việc kích hoạt cơ tay sau.",
        "pro_tips_en": "Keep elbows tucked close to your body to maximize triceps recruitment.",
    },
    {
        "name_eng": "Push-up",
        "name_vie": "Hít đất (Chống đẩy)",
        "instructions_vi": "Nằm sấp chống tay, giữ người thẳng rồi hạ ngực sát sàn và đẩy cơ thể lên.",
        "pro_tips_vi": "Giữ cơ thể thẳng từ đầu đến gót chân bằng cách siết chặt cơ bụng và cơ mông. Không để hông bị võng.",
        "pro_tips_en": "Keep body straight from head to heels by bracing core and glutes. Do not let hips sag.",
    },

    # === PULL (Upper Body & Back) ===
    {
        "name_eng": "Barbell Deadlift",
        "name_vie": "Nhấc tạ đòn (Deadlift)",
        "instructions_vi": "Đứng sát thanh đòn, cúi xuống nắm chặt thanh đòn rồi kéo tạ đứng thẳng dậy bằng lực đùi sau và lưng.",
        "pro_tips_vi": "Gồng chặt cơ bụng và cơ xô để bảo vệ cột sống lưng dưới. Giữ thanh đòn di chuyển sát sát chân trong suốt hành trình.",
        "pro_tips_en": "Brace core and lats to protect lower back. Keep the bar close to your shins throughout.",
    },
    {
        "name_eng": "Barbell Row",
        "name_vie": "Gập người chèo tạ đòn",
        "instructions_vi": "Gập người về phía trước, giữ lưng thẳng, kéo thanh đòn hướng về phía bụng dưới.",
        "pro_tips_vi": "Kéo bằng khuỷu tay ra sau sát cơ thể để cảm nhận cơ xô tốt nhất. Tránh nhún nhảy hay dùng đà của thân trên.",
        "pro_tips_en": "Pull with your elbows to feel the lats. Avoid using body momentum.",
    },
    {
        "name_eng": "Pull-up",
        "name_vie": "Hít xà đơn (Pull-up)",
        "instructions_vi": "Treo người trên xà, nắm rộng hơn vai, kéo cơ thể lên cho đến khi cằm vượt qua thanh xà.",
        "pro_tips_vi": "Tránh đung đưa người. Hãy tưởng tượng bạn đang kéo thanh xà xuống phía ngực mình thay vì kéo người lên.",
        "pro_tips_en": "Avoid swinging. Focus on driving elbows down to pull chest to the bar.",
    },
    {
        "name_eng": "Lat Pulldown",
        "name_vie": "Kéo cáp rộng tay (Lat Pulldown)",
        "instructions_vi": "Ngồi vào máy, kéo thanh xà cáp xuống sát vùng ngực trên rồi thả lên có kiểm soát.",
        "pro_tips_vi": "Tập trung kéo bằng cùi chỏ và siết cơ xô ở điểm cuối. Không ngả người ra sau quá nhiều.",
        "pro_tips_en": "Pull with elbows and squeeze lats at the bottom. Do not lean back excessively.",
    },
    {
        "name_eng": "Face Pull",
        "name_vie": "Kéo cáp ngang mặt (Face Pull)",
        "instructions_vi": "Kéo dây cáp ngang tầm mắt về phía mặt, dang rộng cùi chỏ và xoay ngoài bả vai.",
        "pro_tips_vi": "Tập trung xoay ngoài khớp vai ở cuối biên độ động tác để kích hoạt tối đa cơ vai sau và các cơ xoay vai.",
        "pro_tips_en": "Pull rope toward face and rotate shoulders outward at the end to target rear delts.",
    },
    {
        "name_eng": "Dumbbell Bicep Curl",
        "name_vie": "Cuộn tay trước tạ đơn",
        "instructions_vi": "Đứng thẳng, tay cầm tạ đơn cuộn lên sát vai bằng cơ bắp tay trước.",
        "pro_tips_vi": "Tránh đưa khuỷu tay ra trước khi cuộn tạ lên để giữ áp lực liên tục lên cơ tay trước.",
        "pro_tips_en": "Do not swing elbows forward during the lift to keep tension on the biceps.",
    },
    {
        "name_eng": "Incline Dumbbell Row",
        "name_vie": "Gập người chèo tạ đơn ghế dốc",
        "instructions_vi": "Nằm sấp trên ghế dốc hướng lên, tay cầm tạ đơn kéo ngược lên sát sườn.",
        "pro_tips_vi": "Tư thế này giúp loại bỏ đà từ cơ thể và giảm áp lực lên lưng dưới, tối ưu hóa kích hoạt nhóm cơ lưng.",
        "pro_tips_en": "Eliminates body momentum and lower back stress to isolate back muscles.",
    },
    {
        "name_eng": "Hammer Curl",
        "name_vie": "Cuộn tay trước kiểu búa",
        "instructions_vi": "Cuộn tạ đơn lên với lòng bàn tay hướng vào nhau (song song) trong suốt quá trình cuộn.",
        "pro_tips_vi": "Bài tập này cực kỳ tốt cho cơ cánh tay quay (brachioradialis) và giúp tăng độ dày của bắp tay trước.",
        "pro_tips_en": "Great for forearm development (brachioradialis) and biceps thickness.",
    },
    {
        "name_eng": "Cable Seated Row",
        "name_vie": "Kéo cáp ngồi chèo thuyền",
        "instructions_vi": "Ngồi thẳng lưng, kéo tay cầm cáp về sát bụng và khép bả vai lại.",
        "pro_tips_vi": "Ưỡn ngực khi kéo tạ về và tránh để lưng bị gù khi nhả tạ về phía trước.",
        "pro_tips_en": "Keep chest up and avoid rounding your back as you return the weight.",
    },

    # === LEGS (Lower Body) ===
    {
        "name_eng": "Barbell Back Squat",
        "name_vie": "Gánh tạ đòn sau (Squat)",
        "instructions_vi": "Đặt thanh đòn lên vai, hạ hông xuống thấp như đang ngồi ghế cho đến khi đùi song song sàn rồi đứng lên.",
        "pro_tips_vi": "Luôn giữ bàn chân bám chặt trên sàn, không nhấc gót. Hướng đầu gối theo hướng mũi chân khi xuống.",
        "pro_tips_en": "Keep feet flat, knees tracking over toes. Drop hips until thighs are parallel to floor.",
    },
    {
        "name_eng": "Leg Press",
        "name_vie": "Đạp đùi trên máy (Leg Press)",
        "instructions_vi": "Ngồi vào máy, đặt hai chân lên bàn đạp, hạ đùi xuống sát ngực rồi đạp đẩy bàn đạp lên.",
        "pro_tips_vi": "Tuyệt đối không khóa thẳng khớp gối ở điểm cao nhất để tránh chấn thương nghiêm trọng. Giữ mông áp sát vào ghế đệm.",
        "pro_tips_en": "Do not lock knees at the top. Keep your lower back pressed flat against the seat.",
    },
    {
        "name_eng": "Leg Extension",
        "name_vie": "Đá đùi trước trên máy",
        "instructions_vi": "Ngồi vào máy, móc chân dưới thanh đệm rồi đá duỗi chân thẳng ra trước mặt.",
        "pro_tips_vi": "Bám chặt tay vịn hai bên để giữ mông cố định trên ghế, tránh để hông nâng lên khi đá tạ.",
        "pro_tips_en": "Hold handles tightly to anchor hips. Avoid lifting buttocks off the seat.",
    },
    {
        "name_eng": "Seated Leg Curl",
        "name_vie": "Móc đùi sau ngồi trên máy",
        "instructions_vi": "Ngồi vào máy, đặt chân lên thanh đệm rồi dùng lực cơ đùi sau móc chân gập xuống.",
        "pro_tips_vi": "Kiểm soát tốc độ lúc thả tạ lên để cơ đùi sau được chịu áp lực liên tục.",
        "pro_tips_en": "Control the weight on the way up to maintain constant tension on hamstrings.",
    },
    {
        "name_eng": "Standing Calf Raise",
        "name_vie": "Nhón bắp chuối đứng",
        "instructions_vi": "Đứng nhón gót chân lên cao tối đa trên bục và hạ xuống sâu nhất có thể.",
        "pro_tips_vi": "Giữ ở điểm cao nhất và thấp nhất khoảng 1-2 giây để loại bỏ lực quán tính của gân Achilles.",
        "pro_tips_en": "Hold at peak contraction and stretch to eliminate Achilles tendon bounce.",
    },
    {
        "name_eng": "Romanian Deadlift",
        "name_vie": "Kéo đùi sau tạ đòn (RDL)",
        "instructions_vi": "Giữ lưng thẳng, đẩy hông ra sau và cúi người hạ thanh đòn xuống dọc theo cẳng chân.",
        "pro_tips_vi": "Tập trung đẩy hông ra sau để cảm nhận cơ đùi sau và mông căng tối đa, tránh dùng lưng dưới để cúi gập người.",
        "pro_tips_en": "Push hips back to feel maximum stretch in hamstrings, avoid rounding spine.",
    },
    {
        "name_eng": "Dumbbell Lunges",
        "name_vie": "Bước chùng chân với tạ đơn",
        "instructions_vi": "Cầm tạ đơn bước một bước dài về phía trước rồi chùng gối hạ trọng tâm cơ thể xuống.",
        "pro_tips_vi": "Giữ lưng thẳng đứng và không để đầu gối chân trước vượt quá mũi chân quá xa.",
        "pro_tips_en": "Keep torso upright and step far enough to keep front knee behind toes.",
    },
    {
        "name_eng": "Hip Thrust",
        "name_vie": "Đẩy hông với tạ đòn trên ghế",
        "instructions_vi": "Tựa vai trên ghế, đặt tạ đòn ở vùng hông rồi đẩy mông lên cao tối đa.",
        "pro_tips_vi": "Siết chặt cơ mông ở điểm cao nhất trong 1-2 giây và giữ cằm hướng về phía ngực thay vì ngửa đầu ra sau.",
        "pro_tips_en": "Squeeze glutes at top, keep chin tucked to chest instead of tilting head back.",
    },

    # === CORE & STABILIZATION ===
    {
        "name_eng": "Forearm Plank",
        "name_vie": "Gồng bụng Plank cẳng tay",
        "instructions_vi": "Nằm chống khuỷu tay và mũi chân, giữ cơ thể thẳng tắp từ đầu đến chân.",
        "pro_tips_vi": "Tránh để hông bị võng xuống hay đẩy lên cao. Thực hiện xoay nhẹ xương chậu ra sau để kích hoạt cơ bụng tối đa.",
        "pro_tips_en": "Keep straight line. Tilt pelvis posteriorly to maximize abdominal engagement.",
    },
    {
        "name_eng": "Cable Crunch",
        "name_vie": "Quỳ gập bụng với cáp",
        "instructions_vi": "Quỳ gối cầm cáp đặt hai bên đầu, cuộn lưng và gập bụng kéo cáp xuống sát sàn.",
        "pro_tips_vi": "Tránh gập hông để kéo tạ. Hãy tập trung cuộn tròn cột sống để cơ bụng chịu hoàn toàn lực kéo.",
        "pro_tips_en": "Do not flex hips; curl your spine to ensure the abs do the work.",
    },
    {
        "name_eng": "Hanging Leg Raise",
        "name_vie": "Treo người nâng chân tập bụng",
        "instructions_vi": "Treo người trên xà đơn rồi nâng hai chân thẳng hoặc gập gối lên cao.",
        "pro_tips_vi": "Kiểm soát tốc độ lúc hạ xuống để tránh đung đưa người. Tập trung cuộn xương chậu lên để ăn vào cơ bụng dưới.",
        "pro_tips_en": "Control descent to prevent swinging. Curl pelvis up to target lower abs.",
    },
    {
        "name_eng": "Russian Twist",
        "name_vie": "Xoay người kiểu Nga",
        "instructions_vi": "Ngồi hơi ngả lưng ra sau, nhấc nhẹ hai chân rồi xoay vặn thân người liên tục sang hai bên.",
        "pro_tips_vi": "Di chuyển bằng cách xoay lồng ngực từ bên này sang bên kia, không chỉ di chuyển cánh tay.",
        "pro_tips_en": "Rotate your torso, not just your arms, from side to side.",
    },

    # === CARDIO / ENDURANCE ===
    {
        "name_eng": "Treadmill Run",
        "name_vie": "Chạy bộ trên máy",
        "instructions_vi": "Chạy bộ hoặc đi bộ dốc đều đặn trên máy chạy bộ.",
        "pro_tips_vi": "Giữ cơ thể thẳng đứng, đánh tay tự nhiên bên hông. Bắt đầu bằng chạy chậm khởi động trước khi tăng tốc.",
        "pro_tips_en": "Run upright, arm swing relaxed. Warm up before increasing speed.",
    },
    {
        "name_eng": "Rowing Machine",
        "name_vie": "Tập chèo thuyền trên máy",
        "instructions_vi": "Ngồi trên máy đạp đẩy chân lùi ra sau kết hợp dùng tay kéo cáp chèo sát bụng.",
        "pro_tips_vi": "Lực chèo chia làm 60% từ chân, 20% từ việc giữ cơ bụng/lưng, và 20% từ lực kéo của tay.",
        "pro_tips_en": "Power is 60% legs, 20% core, 20% arms pull.",
    },
    {
        "name_eng": "Stationary Bicycle",
        "name_vie": "Đạp xe đạp cơ học",
        "instructions_vi": "Ngồi đạp xe đạp tại chỗ trên máy tập liên tục.",
        "pro_tips_vi": "Yên xe nên ở độ cao sao cho khi chân ở điểm thấp nhất đầu gối vẫn hơi cong nhẹ khoảng 10-15 độ.",
        "pro_tips_en": "Set seat height so knee has a slight 10-15 degree bend at the bottom.",
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
            # Look up handcrafted Vietnamese names, pro-tips and instructions
            seed_info = get_preset_seed_info(pool_ex.name)
            name_vie = seed_info["name_vie"] if seed_info else None
            pro_tips_vi = seed_info["pro_tips_vi"] if seed_info and "pro_tips_vi" in seed_info else (seed_info["pro_tips"] if seed_info and "pro_tips" in seed_info else None)
            pro_tips_en = seed_info.get("pro_tips_en") if seed_info else None
            instructions_vi = seed_info.get("instructions_vi") if seed_info else None
            instructions_en = pool_ex.instructions_en

            personal = ExerciseMaster(
                pool_id=pool_ex.id,
                name_eng=title_case_name(pool_ex.name),
                name_vie=name_vie,
                instructions=instructions_vi or instructions_en,
                instructions_en=instructions_en,
                instructions_vi=instructions_vi,
                image_url=f"/pool/{pool_ex.image_path}" if pool_ex.image_path else None,
                video_url=f"/pool/{pool_ex.gif_path}" if pool_ex.gif_path else None,
                pro_tips=pro_tips_vi or pro_tips_en,
                pro_tips_en=pro_tips_en,
                pro_tips_vi=pro_tips_vi,
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
