"""Settings for SkillSwap. Secrets come from the .env file, never from the code."""
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "change-this-secret-key")
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", "3306"))
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_NAME = os.getenv("DB_NAME", "skillswap")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"


DEPARTMENTS = [
    "Computer Science", "Information Technology", "Electronics and Communication",
    "Electrical Engineering", "Mechanical Engineering", "Civil Engineering",
    "AI and Machine Learning", "Data Science", "Business Administration", "Other",
]
LEVELS = ["Beginner", "Intermediate", "Advanced"]
