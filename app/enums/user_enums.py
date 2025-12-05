"""
User-related enums for the application.
"""

from enum import Enum


class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    PREFER_NOT_TO_SAY = "prefer_not_to_say"


class UnitPreference(str, Enum):
    IMPERIAL = "imperial"


class TrainingLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class TimeWindow(str, Enum):
    RIGHT_AFTER_WAKING = "right_after_waking"
    AFTER_BREAKFAST = "after_breakfast"
    BEFORE_LUNCH = "before_lunch"
    AFTER_LUNCH = "after_lunch"
    EVENING = "evening"
    AFTER_WORK = "after_work"
    BEFORE_BED = "before_bed"
    NOT_FIXED = "not_fixed"


class WorkoutType(str, Enum):
    RUNNING = "running"
    WALKING = "walking"
    CYCLING = "cycling"
    SWIMMING = "swimming"
    STRENGTH_TRAINING = "strength_training"
    YOGA = "yoga"
    HIIT = "hiit"
    CROSSFIT = "crossfit"
    PILATES = "pilates"
    BOXING = "boxing"
    DANCE = "dance"
    STRETCHING = "stretching"
    HIKE = "hike"
    WEIGHTLIFTING = "weightlifting"
    OTHERS = "others"


class MoodType(str, Enum):
    NORMAL = "normal"
    HAPPY = "happy"
    ENERGETIC = "energetic"
    NERVOUS = "nervous"
    SAD = "sad"
    TIRED = "tired"
    ANGRY = "angry"


class DailyTrainingIntention(str, Enum):
    YES = "yes"
    NO = "no"
    MAYBE = "maybe"


class GoalType(str, Enum):
    WEIGHT_LOSS = "weight_loss"
    WEIGHT_GAIN = "weight_gain"
    MUSCLE_GAIN = "muscle_gain"
    ENDURANCE = "endurance"
    STRENGTH = "strength"
    FLEXIBILITY = "flexibility"
    GENERAL_FITNESS = "general_fitness"


class GoalPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class OnboardingStep(str, Enum):
    BASIC_INFO = "basic_info"
    GOALS = "goals"
    WEIGHT = "weight"
    TRAINING_PREFERENCES = "training_preferences"
    WORKOUT_PREFERENCES = "workout_preferences"
    HEALTH_METRICS = "health_metrics"
    COMPLETED = "completed"


class ConsentType(str, Enum):
    DATA_USAGE = "data_usage"
    HEALTHKIT_READ = "healthkit_read"
    NOTIFICATIONS = "notifications"
    ANALYTICS = "analytics"
