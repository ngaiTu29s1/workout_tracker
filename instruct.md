📜 FITNESS OS - SYSTEM ARCHITECTURE & REQUIREMENTS COMPASS
📜 FITNESS OS - SYSTEM ARCHITECTURE & REQUIREMENTS COMPASS

Bản đặc tả dành cho AI Agent trong IDE để tạo cấu trúc thư mục, khởi tạo cơ sở dữ liệu và triển khai mã nguồn cho dự án Fitness OS (Workout Tracker & Planner).

🏛️ 1. OVERVIEW & UX/UI PHILOSOPHY
Product Goal

Xây dựng một hệ thống Mobile-first Web App quản lý:

Lịch tập luyện
Kho bài tập độc lập
Nhật ký tập luyện
Thống kê tiến độ

Kết hợp AI để tự động làm giàu dữ liệu bài tập (Exercise Metadata Enrichment).

Design System
Visual Style
Minimalist
Dark Mode
Mobile-first
UX Principles
Nút bấm lớn
Thao tác bằng ngón tay cái
Tối ưu cho môi trường phòng gym
Hiển thị nhanh (Glance & Quick)
Cross Platform
Mobile

Ưu tiên Mobile Web/PWA.

Desktop

Hỗ trợ màn hình lớn để:

Lập kế hoạch tập
Theo dõi thống kê
Xem biểu đồ tiến độ
💾 2. DATABASE SCHEMA (POSTGRESQL)
Table 1: exercise_master

Kho dữ liệu bài tập gốc (Master Data)

CREATE TABLE exercise_master (
    id SERIAL PRIMARY KEY,

    name_eng VARCHAR(255) NOT NULL UNIQUE,
    name_vie VARCHAR(255),

    instructions TEXT,

    video_url VARCHAR(512),
    image_url VARCHAR(512),

    pro_tips TEXT,

    tracking_type VARCHAR(50) NOT NULL,

    primary_muscle VARCHAR(100),

    secondary_muscle JSONB DEFAULT '[]'::jsonb,

    tags JSONB DEFAULT '[]'::jsonb,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
tracking_type values
WEIGHT_REPS
BODYWEIGHT_REPS
TIME
Table 2: weekly_presets

Lịch tập cố định hằng tuần.

CREATE TABLE weekly_presets (
    day_of_week INT PRIMARY KEY,
    routine_tag VARCHAR(50)
);
day_of_week
1 = Sunday
2 = Monday
3 = Tuesday
4 = Wednesday
5 = Thursday
6 = Friday
7 = Saturday
routine_tag examples
push
pull
leg
upper_body
cardio
rest
Table 3: daily_workout_log

Nhật ký tập thực tế.

CREATE TABLE daily_workout_log (
    id SERIAL PRIMARY KEY,

    workout_date DATE DEFAULT CURRENT_DATE,

    exercise_id INT REFERENCES exercise_master(id)
        ON DELETE CASCADE,

    tracking_data JSONB DEFAULT '[]'::jsonb,

    is_completed BOOLEAN DEFAULT FALSE
);
tracking_data example
[
  {
    "set": 1,
    "kg": 60,
    "rep": 12
  },
  {
    "set": 2,
    "kg": 60,
    "rep": 10
  }
]
Table 4: workout_aggregated_stats

Bảng dữ liệu thống kê phục vụ Chart.js.

CREATE TABLE workout_aggregated_stats (
    id SERIAL PRIMARY KEY,

    exercise_id INT REFERENCES exercise_master(id)
        ON DELETE CASCADE,

    log_id INT REFERENCES daily_workout_log(id)
        ON DELETE CASCADE,

    date DATE NOT NULL,

    metric_type VARCHAR(50) NOT NULL,

    metric_value NUMERIC NOT NULL,

    unit VARCHAR(20) NOT NULL,

    CONSTRAINT unique_daily_exercise_metric
    UNIQUE(date, exercise_id, metric_type)
);
metric_type values
VOLUME
MAX_WEIGHT
TOTAL_REPS
TOTAL_TIME
unit values
kg
rep
sec
🌐 3. SYSTEM BOUNDARIES & INTERACTION FLOW
[ FRONTEND (Web PWA) ]
            │
            │ REST API
            ▼
[ BACKEND (API Server) ]
            │
            │ Direct SQL
            ▼
[ POSTGRESQL DATABASE ]

            ▲
            │ JSON Payload
            │
[ n8n Runtime Flow ]
            │
            │ POST /webhooks/enrich
            ▼
[ LLM Gateway ]
A. FRONTEND (GUI & DRAG-AND-DROP)
View 1: Exercise Catalog
Features
Danh sách bài tập dạng Card
Hiển thị hình ảnh thumbnail
Tìm kiếm nhanh
Chỉnh sửa metadata trực tiếp
Actions
Create Exercise
Update Exercise
Delete Exercise
AI Enrich Exercise
AI Enrichment Flow
User enters name_eng
        ↓
Click "Fill AI"
        ↓
POST /webhooks/enrich
        ↓
n8n
        ↓
LLM
        ↓
Database Update
View 2: Workout Calendar
Supported Views
Week View
Month Viewhomelab
Year View
Features
Calendar based on weekly_presets
Drag-and-drop scheduling
Override a specific date
Preserve future preset schedules
Drag & Drop Library

Recommended:

SortableJS
View 3: Workout Session
Purpose

Màn hình sử dụng trực tiếp trong phòng tập.

Features
Danh sách bài tập hôm nay
Hướng dẫn tập
Video hướng dẫn ngắn
Nhập Set/Kg/Rep nhanh
Nút bấm lớn
Example UI
Bench Press

[Video]

Set 1
KG: 60
REP: 12

[ Save ]
B. BACKEND (THE GATEKEEPER)
Responsibilities
CRUD APIs
Exercise Master
Weekly Presets
Workout Logshomelab
Statistics
Smart Calendar Engine

Kết hợp:

weekly_presets
+
daily overrides
+
workout logs

để trả về lịch tập thực tế.

Workout Processing

Khi nhận dữ liệu tập luyện:

Frontend
    ↓
Backend
    ↓
daily_workout_log
    ↓
Calculate Metrics
    ↓
UPSERT
workout_aggregated_stats
Metrics Calculation
Volume
Volume
=
Weight × Reps
Max Weight
Highest Weight Used
Total Reps
Sum(All Reps)
Total Time
Sum(All Seconds)
C. N8N AUTOMATION FLOW (THE AI AGENT)
Trigger
POST /webhooks/enrich
Request Payload
{
  "exercise_id": 1,
  "name_eng": "Leg Extension"
}
Execution Flow
Webhook
   ↓
n8n
   ↓
LLM Gateway
   ↓
JSON Output
   ↓
PostgreSQL Update
Expected LLM Output
{
  "name_vie": "Đá đùi trước",
  "instructions": "Ngồi vào máy, lưng thẳng, dùng cơ đùi trước đá thanh đệm chân lên cao...",
  "video_url": "https://cdn.homelab/videos/leg_ext.mp4",
  "image_url": "https://cdn.homelab/images/leg_ext.png",
  "pro_tips": "Tránh để tạ rơi tự do, kiểm soát lực khi hạ chân để bảo vệ khớp gối.",
  "tracking_type": "WEIGHT_REPS",
  "primary_muscle": "Quads",
  "secondary_muscle": [],
  "tags": [
    "leg",
    "lower_body",
    "quads"
  ]
}
Database Update

n8n thực hiện:

UPDATE exercise_master
SET ...
WHERE id = ?;
🚀 4. INSTRUCTIONS FOR THE IDE AI AGENT
Database Setup
Tasks
Create PostgreSQL database
Execute schema
Create indexes
Validate constraints
Required Constraints
PRIMARY KEY
FOREIGN KEY
UNIQUE
ON DELETE CASCADE
Backend Setup
Recommended Stack
Option A
Node.js
Express
PostgreSQL
Option B
Python
FastAPI
PostgreSQL
Required Features
REST API
Validation
Statistics Engine
Calendar Logic
CRUD Operations
Frontend Setup
Recommended Stack
HTML5
Tailwind CSS
Alpine.js
SortableJS
Chart.js
Requirements
Mobile First
Responsive Layout
Large Buttons
Dark Theme
Calendar
Week View
Month View
Year View
Drag & Drop
Workout Session
Fast Input
Minimal Taps
Glanceable Information
Charts

Use Chart.js for:

Progress Tracking
Volume Trends
Max Weight Trends
Total Reps Trends
🎯 FINAL PRODUCT GOAL

Fitness OS phải hoạt động như một hệ thống quản lý tập luyện hoàn chỉnh:

Exercise Catalog
        +
AI Metadata Enrichment
        +
Weekly Planning
        +
Workout Tracking
        +
Statistics Dashboard
        +
Mobile-first UX