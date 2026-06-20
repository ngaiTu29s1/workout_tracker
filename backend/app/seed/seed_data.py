import logging
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.exercise import ExerciseMaster
from backend.app.models.preset import WeeklyPreset

logger = logging.getLogger(__name__)

# ~33 classic exercises categorized with Push, Pull, Legs routine tags + anatomically correct muscles
EXERCISES_SEED = [
    # === PUSH (Upper Body) ===
    {
        "name_eng": "Barbell Bench Press",
        "name_vie": "Đẩy ngực ngang tạ đòn",
        "instructions": "Nằm ngửa trên ghế phẳng. Nắm thanh đòn rộng hơn vai. Hạ thanh đòn xuống chạm nhẹ ngực (khoảng ngang núm vú) rồi đẩy mạnh lên về vị trí ban đầu.",
        "video_url": None,
        "image_url": None,
        "pro_tips": "Siết bả vai ra sau và gồng cơ bụng để tạo bệ đỡ vững chắc. Giữ khuỷu tay hơi khép, tránh mở rộng 90 độ để bảo vệ khớp vai.",
        "tracking_type": "WEIGHT_REPS",
        "primary_muscle": "Chest",
        "secondary_muscle": ["Triceps", "Shoulders"],
        "tags": ["push", "upper_body", "compound", "barbell"]
    },
    {
        "name_eng": "Incline Dumbbell Press",
        "name_vie": "Đẩy ngực trên với tạ đơn",
        "instructions": "Điều chỉnh ghế dốc lên khoảng 30-45 độ. Cầm tạ đơn ở hai bên ngực, lòng bàn tay hướng ra trước. Đẩy tạ lên cao thẳng tay theo đường vòng cung nhẹ rồi hạ xuống có kiểm soát.",
        "video_url": None,
        "image_url": None,
        "pro_tips": "Không để ghế quá dốc vì lực sẽ ăn vào vai trước quá nhiều thay vì ngực trên. Tập trung kiểm soát tạ khi hạ xuống.",
        "tracking_type": "WEIGHT_REPS",
        "primary_muscle": "Chest",
        "secondary_muscle": ["Shoulders", "Triceps"],
        "tags": ["push", "upper_body", "compound", "dumbbell"]
    },
    {
        "name_eng": "Overhead Press (OHP)",
        "name_vie": "Đẩy vai qua đầu tạ đòn",
        "instructions": "Đứng thẳng gồng bụng và mông. Cầm tạ đòn ngang ngực trên. Đẩy thẳng tạ lên trên qua đầu đến khi khóa tay, hơi đưa đầu về phía trước để tạ thẳng hàng với thân người, sau đó hạ về vị trí cũ.",
        "video_url": None,
        "image_url": None,
        "pro_tips": "Tránh ưỡn lưng dưới quá đà khi đẩy tạ lên bằng cách siết chặt cơ mông và cơ bụng suốt động tác.",
        "tracking_type": "WEIGHT_REPS",
        "primary_muscle": "Shoulders",
        "secondary_muscle": ["Triceps", "Core"],
        "tags": ["push", "upper_body", "compound", "barbell"]
    },
    {
        "name_eng": "Parallel Bar Dips",
        "name_vie": "Chống xà kép (Dips)",
        "instructions": "Bám hai tay vào xà kép, nâng cơ thể lên thẳng tay. Gập cùi chỏ hạ cơ thể xuống cho đến khi cánh tay trên song song với sàn (hoặc cùi chỏ vuông góc), sau đó đẩy mạnh người lên.",
        "video_url": None,
        "image_url": None,
        "pro_tips": "Hơi nghiêng thân người về phía trước để kích hoạt cơ ngực dưới nhiều hơn. Nếu muốn tập trung vào tay sau, hãy giữ thân người thẳng đứng.",
        "tracking_type": "BODYWEIGHT_REPS",
        "primary_muscle": "Chest",
        "secondary_muscle": ["Triceps", "Shoulders"],
        "tags": ["push", "upper_body", "compound", "bodyweight"]
    },
    {
        "name_eng": "Tricep Pushdown",
        "name_vie": "Kéo cáp cơ tay sau",
        "instructions": "Đứng đối diện máy cáp, cầm tay cầm dây thừng hoặc thanh thẳng. Ghim chặt cùi chỏ sát sườn, dùng lực tay sau kéo cáp xuống cho đến khi cánh tay thẳng hoàn toàn, siết mạnh rồi từ từ đưa về.",
        "video_url": None,
        "image_url": None,
        "pro_tips": "Không di chuyển cùi chỏ ra trước hay ra sau để tập trung cô lập hoàn toàn vào cơ tay sau.",
        "tracking_type": "WEIGHT_REPS",
        "primary_muscle": "Triceps",
        "secondary_muscle": [],
        "tags": ["push", "upper_body", "isolation", "cable"]
    },
    {
        "name_eng": "Cable Fly",
        "name_vie": "Ép ngực với cáp",
        "instructions": "Đứng giữa hai cột cáp cao, bước một chân lên trước để vững tư thế. Cầm tay cầm cáp kéo ép vào nhau phía trước ngực với cùi chỏ hơi cong, siết chặt cơ ngực ở điểm chạm.",
        "video_url": None,
        "image_url": None,
        "pro_tips": "Tưởng tượng như bạn đang ôm một thân cây lớn để giữ khớp khuỷu cố định, tránh biến bài tập thành bài đẩy ngực.",
        "tracking_type": "WEIGHT_REPS",
        "primary_muscle": "Chest",
        "secondary_muscle": ["Shoulders"],
        "tags": ["push", "upper_body", "isolation", "cable"]
    },
    {
        "name_eng": "Dumbbell Lateral Raise",
        "name_vie": "Dang tay vai bên tạ đơn",
        "instructions": "Đứng thẳng, mỗi tay cầm một quả tạ đơn đặt ở hai bên đùi. Hơi cong cùi chỏ, nâng tạ sang hai bên cho đến khi cánh tay song song với sàn, sau đó hạ từ từ xuống.",
        "video_url": None,
        "image_url": None,
        "pro_tips": "Không nhún vai khi nâng tạ. Hãy tưởng tượng như bạn đang đẩy tạ ra xa hai bên thay vì kéo lên trên.",
        "tracking_type": "WEIGHT_REPS",
        "primary_muscle": "Shoulders",
        "secondary_muscle": [],
        "tags": ["push", "upper_body", "isolation", "dumbbell"]
    },
    {
        "name_eng": "Close-Grip Barbell Bench Press",
        "name_vie": "Đẩy ngực hẹp tay tạ đòn",
        "instructions": "Nằm ngửa trên ghế phẳng. Nắm thanh đòn với khoảng cách hai tay hẹp hơn vai (khoảng 20-30cm). Hạ tạ xuống sát ngực dưới rồi đẩy mạnh lên.",
        "video_url": None,
        "image_url": None,
        "pro_tips": "Giữ cùi chỏ khép sát thân người trong suốt quá trình đẩy để tối ưu hóa việc kích hoạt cơ tay sau.",
        "tracking_type": "WEIGHT_REPS",
        "primary_muscle": "Triceps",
        "secondary_muscle": ["Chest", "Shoulders"],
        "tags": ["push", "upper_body", "compound", "barbell"]
    },
    {
        "name_eng": "Push-up",
        "name_vie": "Hít đất (Chống đẩy)",
        "instructions": "Bắt đầu ở tư thế plank cao tay, hai tay rộng hơn vai một chút, thân người thẳng. Hạ ngực xuống sát sàn bằng cách gập cùi chỏ, sau đó đẩy mạnh người lên vị trí ban đầu.",
        "video_url": None,
        "image_url": None,
        "pro_tips": "Giữ cơ thể thẳng từ đầu đến gót chân bằng cách siết chặt cơ bụng và cơ mông. Không để hông bị võng.",
        "tracking_type": "BODYWEIGHT_REPS",
        "primary_muscle": "Chest",
        "secondary_muscle": ["Triceps", "Shoulders", "Core"],
        "tags": ["push", "upper_body", "compound", "bodyweight"]
    },

    # === PULL (Upper Body & Back) ===
    {
        "name_eng": "Barbell Deadlift",
        "name_vie": "Nhấc tạ đòn (Deadlift)",
        "instructions": "Đứng sát thanh đòn sao cho đòn tạ ở giữa bàn chân. Cúi gập người nắm thanh đòn, giữ lưng thẳng, đẩy ngực lên. Đạp mạnh chân xuống sàn và đẩy hông về phía trước để đứng dậy kéo tạ lên sát người.",
        "video_url": None,
        "image_url": None,
        "pro_tips": "Gồng chặt cơ bụng và cơ xô để bảo vệ cột sống lưng dưới. Giữ thanh đòn di chuyển sát sát chân trong suốt hành trình.",
        "tracking_type": "WEIGHT_REPS",
        "primary_muscle": "Hamstrings",
        "secondary_muscle": ["Glutes", "Back", "Core"],
        "tags": ["pull", "legs", "lower_body", "compound", "barbell"]
    },
    {
        "name_eng": "Barbell Row",
        "name_vie": "Gập người chèo tạ đòn",
        "instructions": "Đứng cúi gập người góc 45 độ, giữ lưng thẳng tự nhiên. Nắm thanh đòn rộng bằng vai, kéo thanh đòn về phía bụng dưới, co cùi chỏ ra sau rồi hạ xuống có kiểm soát.",
        "video_url": None,
        "image_url": None,
        "pro_tips": "Kéo bằng khuỷu tay ra sau sát cơ thể để cảm nhận cơ xô tốt nhất. Tránh nhún nhảy hay dùng đà của thân trên.",
        "tracking_type": "WEIGHT_REPS",
        "primary_muscle": "Back",
        "secondary_muscle": ["Biceps", "Shoulders"],
        "tags": ["pull", "upper_body", "compound", "barbell"]
    },
    {
        "name_eng": "Pull-up",
        "name_vie": "Hít xà đơn (Pull-up)",
        "instructions": "Bám hai tay rộng hơn vai trên xà đơn, lòng bàn tay hướng ra trước. Kéo cơ thể lên bằng cách hướng khuỷu tay xuống sàn cho đến khi cằm vượt qua thanh xà, từ từ hạ xuống hết tay.",
        "video_url": None,
        "image_url": None,
        "pro_tips": "Tránh đung đưa người. Hãy tưởng tượng bạn đang kéo thanh xà xuống phía ngực mình thay vì kéo người lên.",
        "tracking_type": "BODYWEIGHT_REPS",
        "primary_muscle": "Lats",
        "secondary_muscle": ["Biceps", "Back"],
        "tags": ["pull", "upper_body", "compound", "bodyweight"]
    },
    {
        "name_eng": "Lat Pulldown",
        "name_vie": "Kéo cáp rộng tay (Lat Pulldown)",
        "instructions": "Ngồi vào máy kéo cáp, điều chỉnh đệm đùi. Cầm thanh kéo rộng hơn vai. Ưỡn nhẹ ngực, kéo thanh cáp xuống sát ngực trên rồi từ từ nhả tạ lên.",
        "video_url": None,
        "image_url": None,
        "pro_tips": "Tập trung kéo bằng cùi chỏ và siết cơ xô ở điểm cuối. Không ngả người ra sau quá nhiều.",
        "tracking_type": "WEIGHT_REPS",
        "primary_muscle": "Lats",
        "secondary_muscle": ["Biceps", "Back"],
        "tags": ["pull", "upper_body", "compound", "cable"]
    },
    {
        "name_eng": "Face Pull",
        "name_vie": "Kéo cáp ngang mặt (Face Pull)",
        "instructions": "Cầm dây thừng trên máy cáp ngang tầm mắt. Kéo dây về hướng trán/mũi, đồng thời mở rộng khuỷu tay sang hai bên và xoay ngoài khớp vai để siết vai sau.",
        "video_url": None,
        "image_url": None,
        "pro_tips": "Tập trung xoay ngoài khớp vai ở cuối biên độ động tác để kích hoạt tối đa cơ vai sau và các cơ xoay vai.",
        "tracking_type": "WEIGHT_REPS",
        "primary_muscle": "Shoulders",
        "secondary_muscle": ["Back"],
        "tags": ["pull", "upper_body", "isolation", "cable"]
    },
    {
        "name_eng": "Dumbbell Bicep Curl",
        "name_vie": "Cuộn tay trước tạ đơn",
        "instructions": "Đứng thẳng, hai tay cầm hai quả tạ đơn. Giữ cùi chỏ cố định sát thân người, cuộn tạ lên đồng thời xoay lòng bàn tay hướng lên trên, siết chặt bắp tay trước rồi hạ xuống chậm rãi.",
        "video_url": None,
        "image_url": None,
        "pro_tips": "Tránh đưa khuỷu tay ra trước khi cuộn tạ lên để giữ áp lực liên tục lên cơ tay trước.",
        "tracking_type": "WEIGHT_REPS",
        "primary_muscle": "Biceps",
        "secondary_muscle": ["Forearms"],
        "tags": ["pull", "upper_body", "isolation", "dumbbell"]
    },
    {
        "name_eng": "Incline Dumbbell Row",
        "name_vie": "Gập người chèo tạ đơn ghế dốc",
        "instructions": "Nằm sấp trên ghế dốc lên khoảng 30-45 độ. Mỗi tay cầm một quả tạ đơn buông thõng xuôi xuống. Kéo tạ lên sát hông bằng cách gập cùi chỏ ra sau, siết chặt cơ lưng rồi hạ xuống.",
        "video_url": None,
        "image_url": None,
        "pro_tips": "Tư thế này giúp loại bỏ đà từ cơ thể và giảm áp lực lên lưng dưới, tối ưu hóa kích hoạt nhóm cơ lưng.",
        "tracking_type": "WEIGHT_REPS",
        "primary_muscle": "Back",
        "secondary_muscle": ["Biceps", "Shoulders"],
        "tags": ["pull", "upper_body", "compound", "dumbbell"]
    },
    {
        "name_eng": "Hammer Curl",
        "name_vie": "Cuộn tay trước kiểu búa",
        "instructions": "Đứng thẳng cầm tạ đơn hai bên tay với lòng bàn tay hướng vào nhau. Giữ cùi chỏ cố định, cuộn tạ lên mà không xoay bàn tay, giữ nguyên hướng song song rồi hạ xuống.",
        "video_url": None,
        "image_url": None,
        "pro_tips": "Bài tập này cực kỳ tốt cho cơ cánh tay quay (brachioradialis) và giúp tăng độ dày của bắp tay trước.",
        "tracking_type": "WEIGHT_REPS",
        "primary_muscle": "Biceps",
        "secondary_muscle": ["Forearms"],
        "tags": ["pull", "upper_body", "isolation", "dumbbell"]
    },
    {
        "name_eng": "Cable Seated Row",
        "name_vie": "Kéo cáp ngồi chèo thuyền",
        "instructions": "Ngồi vào máy cáp, đặt chân lên bệ đỡ, hơi chùng gối. Cầm tay cầm chữ V, giữ lưng thẳng. Kéo tay cầm về phía bụng dưới bằng cách kéo bả vai và gập khuỷu tay ra sau.",
        "video_url": None,
        "image_url": None,
        "pro_tips": "Ưỡn ngực khi kéo tạ về và tránh để lưng bị gù khi nhả tạ về phía trước.",
        "tracking_type": "WEIGHT_REPS",
        "primary_muscle": "Back",
        "secondary_muscle": ["Biceps", "Shoulders"],
        "tags": ["pull", "upper_body", "compound", "cable"]
    },

    # === LEGS (Lower Body) ===
    {
        "name_eng": "Barbell Back Squat",
        "name_vie": "Gánh tạ đòn sau (Squat)",
        "instructions": "Đặt tạ đòn trên cơ cầu vai. Đứng chân rộng bằng vai, mũi chân hơi mở. Siết bụng, đẩy hông ra sau và hạ thấp người xuống cho đến khi đùi song song với mặt đất hoặc sâu hơn, sau đó đạp mạnh chân đứng lên.",
        "video_url": None,
        "image_url": None,
        "pro_tips": "Luôn giữ bàn chân bám chặt trên sàn, không nhấc gót. Hướng đầu gối theo hướng mũi chân khi xuống.",
        "tracking_type": "WEIGHT_REPS",
        "primary_muscle": "Quads",
        "secondary_muscle": ["Glutes", "Hamstrings", "Core"],
        "tags": ["legs", "lower_body", "compound", "barbell"]
    },
    {
        "name_eng": "Leg Press",
        "name_vie": "Đạp đùi trên máy (Leg Press)",
        "instructions": "Ngồi vào máy đạp đùi, đặt hai chân lên bàn đạp rộng bằng vai. Mở chốt an toàn, co gối hạ bàn đạp xuống có kiểm soát cho đến khi đùi vuông góc với cẳng chân, sau đó đạp mạnh lên.",
        "video_url": None,
        "image_url": None,
        "pro_tips": "Tuyệt đối không khóa thẳng khớp gối ở điểm cao nhất để tránh chấn thương nghiêm trọng. Giữ mông áp sát vào ghế đệm.",
        "tracking_type": "WEIGHT_REPS",
        "primary_muscle": "Quads",
        "secondary_muscle": ["Glutes", "Hamstrings"],
        "tags": ["legs", "lower_body", "compound", "machine"]
    },
    {
        "name_eng": "Leg Extension",
        "name_vie": "Đá đùi trước trên máy",
        "instructions": "Ngồi vào máy đá đùi, đặt cổ chân dưới đệm mút. Đá chân thẳng lên cao, siết chặt cơ đùi trước trong 1 giây ở điểm cao nhất, rồi hạ xuống từ từ.",
        "video_url": None,
        "image_url": None,
        "pro_tips": "Bám chặt tay vịn hai bên để giữ mông cố định trên ghế, tránh để hông nâng lên khi đá tạ.",
        "tracking_type": "WEIGHT_REPS",
        "primary_muscle": "Quads",
        "secondary_muscle": [],
        "tags": ["legs", "lower_body", "isolation", "machine"]
    },
    {
        "name_eng": "Seated Leg Curl",
        "name_vie": "Móc đùi sau ngồi trên máy",
        "instructions": "Ngồi vào vị trí máy, đệm đùi ép chặt. Co chân gập cẳng chân ra sau hướng xuống dưới hết cỡ, siết chặt cơ đùi sau rồi từ từ thả lên.",
        "video_url": None,
        "image_url": None,
        "pro_tips": "Kiểm soát tốc độ lúc thả tạ lên để cơ đùi sau được chịu áp lực liên tục.",
        "tracking_type": "WEIGHT_REPS",
        "primary_muscle": "Hamstrings",
        "secondary_muscle": ["Calves", "Glutes"],
        "tags": ["legs", "lower_body", "isolation", "machine"]
    },
    {
        "name_eng": "Standing Calf Raise",
        "name_vie": "Nhón bắp chuối đứng",
        "instructions": "Đứng trên bục nhón bắp chân (bằng máy hoặc tạ đơn). Hạ gót chân xuống sâu dưới bục để kéo giãn cơ, sau đó nhón cao gót chân hết mức nâng toàn bộ cơ thể lên.",
        "video_url": None,
        "image_url": None,
        "pro_tips": "Giữ ở điểm cao nhất và thấp nhất khoảng 1-2 giây để loại bỏ lực quán tính của gân Achilles.",
        "tracking_type": "WEIGHT_REPS",
        "primary_muscle": "Calves",
        "secondary_muscle": [],
        "tags": ["legs", "lower_body", "isolation", "dumbbell"]
    },
    {
        "name_eng": "Romanian Deadlift",
        "name_vie": "Kéo đùi sau tạ đòn (RDL)",
        "instructions": "Đứng thẳng giữ tạ đòn trước đùi. Hơi chùng nhẹ đầu gối (giữ góc cố định), đẩy hông tối đa ra sau để cúi người xuống, hạ thanh đòn chạy dọc theo chân cho tới dưới đầu gối một chút rồi siết đùi sau mông kéo người lên đứng thẳng.",
        "video_url": None,
        "image_url": None,
        "pro_tips": "Tập trung đẩy hông ra sau để cảm nhận cơ đùi sau và mông căng tối đa, tránh dùng lưng dưới để cúi gập người.",
        "tracking_type": "WEIGHT_REPS",
        "primary_muscle": "Hamstrings",
        "secondary_muscle": ["Glutes", "Back"],
        "tags": ["legs", "pull", "lower_body", "compound", "barbell"]
    },
    {
        "name_eng": "Dumbbell Lunges",
        "name_vie": "Bước chùng chân với tạ đơn",
        "instructions": "Đứng thẳng, mỗi tay cầm một quả tạ đơn buông dọc thân người. Bước một chân rộng lên phía trước, hạ thấp hông cho đến khi đầu gối chân sau gần chạm sàn và đùi chân trước song song với sàn, sau đó đạp chân trước đứng dậy bước về.",
        "video_url": None,
        "image_url": None,
        "pro_tips": "Giữ lưng thẳng đứng và không để đầu gối chân trước vượt quá mũi chân quá xa.",
        "tracking_type": "WEIGHT_REPS",
        "primary_muscle": "Quads",
        "secondary_muscle": ["Glutes", "Hamstrings"],
        "tags": ["legs", "lower_body", "compound", "dumbbell"]
    },
    {
        "name_eng": "Hip Thrust",
        "name_vie": "Đẩy hông với tạ đòn trên ghế",
        "instructions": "Tựa lưng trên lên ghế băng ngang, đặt tạ đòn trên khớp hông (sử dụng đệm lót). Co gối, bàn chân đặt trên sàn. Hạ hông xuống rồi dùng lực cơ mông đẩy hông lên cao cho đến khi đùi và thân người song song với sàn.",
        "video_url": None,
        "image_url": None,
        "pro_tips": "Siết chặt cơ mông ở điểm cao nhất trong 1-2 giây và giữ cằm hướng về phía ngực thay vì ngửa đầu ra sau.",
        "tracking_type": "WEIGHT_REPS",
        "primary_muscle": "Glutes",
        "secondary_muscle": ["Hamstrings", "Core"],
        "tags": ["legs", "lower_body", "compound", "barbell"]
    },

    # === CORE & STABILIZATION ===
    {
        "name_eng": "Forearm Plank",
        "name_vie": "Gồng bụng Plank cẳng tay",
        "instructions": "Tì khuỷu tay trực tiếp dưới vai và chống mũi chân trên sàn. Siết chặt cơ bụng, cơ mông và cơ đùi để giữ toàn bộ cơ thể thẳng tắp từ đầu đến gót chân.",
        "video_url": None,
        "image_url": None,
        "pro_tips": "Tránh để hông bị võng xuống hay đẩy lên cao. Thực hiện xoay nhẹ xương chậu ra sau để kích hoạt cơ bụng tối đa.",
        "tracking_type": "TIME",
        "primary_muscle": "Core",
        "secondary_muscle": ["Shoulders", "Glutes"],
        "tags": ["push", "pull", "legs", "bodyweight"]
    },
    {
        "name_eng": "Cable Crunch",
        "name_vie": "Quỳ gập bụng với cáp",
        "instructions": "Quỳ trước máy cáp, cầm dây thừng ghim sát tai. Khóa cố định hông, cuộn tròn lưng cúi xuống hướng khuỷu tay về phía đùi bằng cách siết cơ bụng, rồi từ từ nhả về.",
        "video_url": None,
        "image_url": None,
        "pro_tips": "Tránh gập hông để kéo tạ. Hãy tập trung cuộn tròn cột sống để cơ bụng chịu hoàn toàn lực kéo.",
        "tracking_type": "WEIGHT_REPS",
        "primary_muscle": "Core",
        "secondary_muscle": [],
        "tags": ["pull", "upper_body", "isolation", "cable"]
    },
    {
        "name_eng": "Hanging Leg Raise",
        "name_vie": "Treo người nâng chân tập bụng",
        "instructions": "Treo người thẳng trên xà đơn. Giữ chân thẳng (hoặc hơi chùng), dùng cơ bụng nâng chân lên cao cho tới khi vuông góc với thân người, sau đó hạ chân xuống chậm rãi.",
        "video_url": None,
        "image_url": None,
        "pro_tips": "Kiểm soát tốc độ lúc hạ xuống để tránh đung đưa người. Tập trung cuộn xương chậu lên để ăn vào cơ bụng dưới.",
        "tracking_type": "BODYWEIGHT_REPS",
        "primary_muscle": "Core",
        "secondary_muscle": ["Hip Flexors"],
        "tags": ["legs", "pull", "upper_body", "isolation", "bodyweight"]
    },
    {
        "name_eng": "Russian Twist",
        "name_vie": "Xoay người kiểu Nga",
        "instructions": "Ngồi trên sàn, co gối, hơi nhấc chân khỏi sàn và ngả lưng ra sau góc 45 độ. Đan hai tay trước ngực và xoay thân người sang trái rồi sang phải nhịp nhàng.",
        "video_url": None,
        "image_url": None,
        "pro_tips": "Di chuyển bằng cách xoay lồng ngực từ bên này sang bên kia, không chỉ di chuyển cánh tay.",
        "tracking_type": "BODYWEIGHT_REPS",
        "primary_muscle": "Obliques",
        "secondary_muscle": ["Core"],
        "tags": ["pull", "bodyweight", "isolation"]
    },

    # === CARDIO / ENDURANCE ===
    {
        "name_eng": "Treadmill Run",
        "name_vie": "Chạy bộ trên máy",
        "instructions": "Bật máy chạy bộ, chọn tốc độ và độ dốc phù hợp. Chạy bộ đều đặn, đáp chân nhẹ nhàng bằng nửa bàn chân trước hoặc giữa bàn chân.",
        "video_url": None,
        "image_url": None,
        "pro_tips": "Giữ cơ thể thẳng đứng, đánh tay tự nhiên bên hông. Bắt đầu bằng chạy chậm khởi động trước khi tăng tốc.",
        "tracking_type": "TIME",
        "primary_muscle": "Quads",
        "secondary_muscle": ["Hamstrings", "Calves", "Glutes"],
        "tags": ["legs", "lower_body", "bodyweight"]
    },
    {
        "name_eng": "Rowing Machine",
        "name_vie": "Tập chèo thuyền trên máy",
        "instructions": "Ngồi trên máy chèo thuyền, siết chặt bàn chân. Cầm tay cầm, đạp chân thẳng ra trước để đẩy người, sau đó ngả nhẹ lưng và kéo cáp sát về phía bụng dưới.",
        "video_url": None,
        "image_url": None,
        "pro_tips": "Lực chèo chia làm 60% từ chân, 20% từ việc giữ cơ bụng/lưng, và 20% từ lực kéo của tay.",
        "tracking_type": "TIME",
        "primary_muscle": "Back",
        "secondary_muscle": ["Quads", "Hamstrings", "Biceps"],
        "tags": ["pull", "legs", "lower_body", "upper_body", "compound", "machine"]
    },
    {
        "name_eng": "Stationary Bicycle",
        "name_vie": "Đạp xe đạp cơ học",
        "instructions": "Điều chỉnh chiều cao yên xe phù hợp. Ngồi thẳng lưng, đặt chân lên bàn đạp và bắt đầu đạp xe với tốc độ/lực cản mong muốn.",
        "video_url": None,
        "image_url": None,
        "pro_tips": "Yên xe nên ở độ cao sao cho khi chân ở điểm thấp nhất đầu gối vẫn hơi cong nhẹ khoảng 10-15 độ.",
        "tracking_type": "TIME",
        "primary_muscle": "Quads",
        "secondary_muscle": ["Hamstrings", "Calves", "Glutes"],
        "tags": ["legs", "lower_body", "machine"]
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
    # 1. Seed Exercises — seed if fewer than expected (handles partial data from testing)
    exercise_count_query = select(func.count(ExerciseMaster.id))
    result = await db.execute(exercise_count_query)
    count = result.scalar()

    if count < len(EXERCISES_SEED):
        if count > 0:
            logger.info(f"Found {count} exercises (expected {len(EXERCISES_SEED)}). Re-seeding...")
            # Delete existing to avoid duplicates, then reseed
            await db.execute(ExerciseMaster.__table__.delete())
            await db.flush()
        else:
            logger.info("Database is empty. Seeding exercises...")
        for ex in EXERCISES_SEED:
            db_ex = ExerciseMaster(**ex)
            db.add(db_ex)
        await db.commit()
        logger.info(f"Successfully seeded {len(EXERCISES_SEED)} exercises.")
    else:
        logger.info(f"Exercises already seeded ({count}). Skipping.")

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
