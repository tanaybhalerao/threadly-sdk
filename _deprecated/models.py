from sqlalchemy import Column, String, Integer, DateTime, Text, Float, Boolean
from db_setup import Base
from datetime import datetime

class MemoryEvent(Base):
    __tablename__ = "memory_events"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    message_text = Column(Text)
    response_text = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)

    sentiment = Column(String, default="unknown")
    topic = Column(String, default="unknown")
    topic_nuance = Column(Text, default="")
    subtopics = Column(Text, default="")  # 🧠 NEW: comma-separated subtopics
    thread_id = Column(String, index=True)

    resolved = Column(Boolean, default=False)
    summary = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

    tags = Column(String, default="")
    importance_score = Column(Float, default=0.5)
    role = Column(String, default="user")
    message_hash = Column(String, index=True, default="")

    # 🧠 Structured memory insights
    current_state_summary = Column(Text, nullable=True)
    next_step_prediction = Column(Text, nullable=True)
    breakthrough_flag = Column(Boolean, default=False)
    breakthrough_description = Column(Text, nullable=True)

    # 🎯 Optional goal label
    goal_label = Column(String, default="")

class UserProfile(Base):
    __tablename__ = "user_profiles"

    user_id = Column(String, primary_key=True)
    total_messages = Column(Integer, default=0)
    total_threads = Column(Integer, default=0)
    unresolved_threads = Column(Integer, default=0)
    most_common_topic = Column(String, default="")

    dominant_emotion = Column(String, default="neutral")
    active_topic_streak = Column(String, default="")
    repetition_count = Column(Integer, default=0)
