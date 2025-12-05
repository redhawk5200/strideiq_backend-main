import openai
import os
from typing import Dict, List, Optional, AsyncGenerator
from datetime import datetime, timedelta, date
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, desc

from app.models.user import User
from app.models.user_profile import UserProfile
from app.models.user_goals import UserGoal, BodyWeightMeasurement
from app.models.training_preferences import TrainingPreferences
from app.models.vo2_max_estimate import VO2MaxEstimate
from app.models.heart_rate_sample import HeartRateSample
from app.models.sleep_session import SleepSession
from app.models.workout_session import WorkoutSession
from app.models.step_minute import StepMinute
from app.models.user_daily_training_intention import UserDailyTrainingIntention
from app.models.user_medical_condition import UserMedicalCondition
from app.models.medical_condition import MedicalCondition
from app.models.coaching_recommendation import CoachingRecommendation, RecommendationStatus
from app.core.logger import get_logger
import re

logger = get_logger("coaching_recommendations_service")


class CoachingRecommendationsService:
    """Service for generating personalized AI coaching recommendations."""

    def __init__(self):
        self.openai_client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    async def generate_comprehensive_recommendations(
        self,
        db: AsyncSession,
        user_id: str
    ) -> Dict:
        """Generate comprehensive AI coaching recommendations based on all user data."""

        try:
            # Gather all user data
            context = await self._gather_user_context(db, user_id)

            if not context['profile']:
                return {
                    "success": False,
                    "error": "User profile not found",
                    "recommendations": []
                }

            # Generate AI recommendations
            ai_recommendations = await self._generate_ai_insights(context)

            # Generate quick action items
            quick_actions = self._generate_quick_actions(context)

            # Convert AI insights to recommendations array
            recommendations_array = self._convert_insights_to_recommendations(
                ai_recommendations.get("insights", {})
            )

            # Save recommendation to database
            saved_recommendation = await self._save_recommendation(
                db, user_id, ai_recommendations.get("insights", {})
            )

            return {
                "success": True,
                "user_id": user_id,
                "recommendation_id": saved_recommendation.id if saved_recommendation else None,
                "context_summary": self._create_context_summary(context),
                "recommendations": recommendations_array,
                "ai_insights": ai_recommendations,
                "quick_actions": quick_actions,
                "generated_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            fallback_insights = self._get_fallback_recommendations()
            return {
                "success": False,
                "error": str(e),
                "recommendations": self._convert_insights_to_recommendations(fallback_insights)
            }

    async def stream_recommendations(
        self,
        db: AsyncSession,
        user_id: str
    ) -> AsyncGenerator[str, None]:
        """Stream AI recommendations in real-time using Server-Sent Events."""

        try:
            # Send initial status
            yield f"data: {json.dumps({'type': 'status', 'message': 'Gathering your health data...'})}\n\n"

            # Gather all user data
            context = await self._gather_user_context(db, user_id)

            if not context['profile']:
                yield f"data: {json.dumps({'type': 'error', 'message': 'User profile not found'})}\n\n"
                return

            # Send context summary
            yield f"data: {json.dumps({'type': 'context', 'data': self._create_context_summary(context)})}\n\n"

            # Send status update
            yield f"data: {json.dumps({'type': 'status', 'message': 'Generating AI insights...'})}\n\n"

            # Build prompt
            prompt = self._build_coaching_prompt(context)

            print(f"🤖 Sending prompt to OpenAI (length: {len(prompt)} chars)")

            # Stream from OpenAI
            stream = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": self._get_system_prompt()
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=2000,
                stream=True
            )

            full_response = ""
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    # Send each chunk to the client
                    yield f"data: {json.dumps({'type': 'chunk', 'content': content})}\n\n"

            # Parse the complete response
            parsed_insights = self._parse_coaching_response(full_response)
            recommendations_array = self._convert_insights_to_recommendations(parsed_insights)

            # Send final recommendations
            yield f"data: {json.dumps({'type': 'complete', 'recommendations': recommendations_array, 'insights': parsed_insights})}\n\n"

        except Exception as e:
            logger.error(f"Error streaming recommendations: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    async def _gather_user_context(self, db: AsyncSession, user_id: str) -> Dict:
        """Gather comprehensive user context for AI analysis."""

        logger.info(f"🔍 Gathering context for user: {user_id}")

        context = {
            "user": None,
            "profile": None,
            "goals": [],
            "training_preferences": None,
            "latest_weight": None,
            "weight_history": [],
            "vo2_data": [],
            "heart_rate_data": [],
            "sleep_data": None,
            "workout_data": [],
            "step_data": [],
            "previous_recommendations": []
        }

        # Get user
        user_result = await db.execute(select(User).where(User.id == user_id))
        context["user"] = user_result.scalar_one_or_none()

        if not context["user"]:
            logger.warning(f"⚠️ User not found: {user_id}")
            return context

        logger.info(f"✅ Found user with ID: {user_id}")

        # Get profile
        profile_result = await db.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        context["profile"] = profile_result.scalar_one_or_none()

        if context["profile"]:
            # Get goals
            goals_result = await db.execute(
                select(UserGoal)
                .where(UserGoal.profile_id == context["profile"].id)
                .where(UserGoal.active == True)
            )
            context["goals"] = goals_result.scalars().all()

            # Get training preferences
            training_result = await db.execute(
                select(TrainingPreferences)
                .where(TrainingPreferences.profile_id == context["profile"].id)
            )
            context["training_preferences"] = training_result.scalar_one_or_none()

        # Get weight data (last 3 readings)
        weight_result = await db.execute(
            select(BodyWeightMeasurement)
            .where(BodyWeightMeasurement.user_id == user_id)
            .order_by(desc(BodyWeightMeasurement.measured_at))
            .limit(3)
        )
        weight_measurements = weight_result.scalars().all()
        if weight_measurements:
            context["latest_weight"] = weight_measurements[0]
            context["weight_history"] = weight_measurements

        # Get VO2 max data (last 3 readings)
        vo2_result = await db.execute(
            select(VO2MaxEstimate)
            .where(VO2MaxEstimate.user_id == user_id)
            .order_by(desc(VO2MaxEstimate.measured_at))
            .limit(3)
        )
        context["vo2_data"] = vo2_result.scalars().all()

        # Get heart rate data (last 3 readings - using daily averages)
        three_days_ago = datetime.utcnow() - timedelta(days=3)
        hr_result = await db.execute(
            select(HeartRateSample)
            .where(HeartRateSample.user_id == user_id)
            .where(HeartRateSample.captured_at >= three_days_ago)
            .order_by(desc(HeartRateSample.captured_at))
            .limit(100)  # Get enough samples to calculate daily averages
        )
        hr_samples = hr_result.scalars().all()

        # Group by day and calculate daily averages
        if hr_samples:
            daily_hr = {}
            for sample in hr_samples:
                day_key = sample.captured_at.date()
                if day_key not in daily_hr:
                    daily_hr[day_key] = []
                daily_hr[day_key].append(sample.bpm)

            # Get last 3 days of averages
            context["heart_rate_data"] = [
                {
                    "date": day.isoformat(),
                    "avg_bpm": sum(bpms) / len(bpms),
                    "min_bpm": min(bpms),
                    "max_bpm": max(bpms),
                    "samples": len(bpms)
                }
                for day, bpms in sorted(daily_hr.items(), reverse=True)[:3]
            ]

        # Get workout data (last 3 workouts)
        workout_result = await db.execute(
            select(WorkoutSession)
            .where(WorkoutSession.user_id == user_id)
            .order_by(desc(WorkoutSession.start_time))
            .limit(3)
        )
        workouts = workout_result.scalars().all()
        context["workout_data"] = [
            {
                "activity_type": w.activity_type,
                "start_time": w.start_time.isoformat(),
                "duration_minutes": w.duration_seconds / 60,
                "distance_miles": w.distance_miles,
                "calories": w.calories,
                "avg_heart_rate": w.avg_heart_rate,
                "max_heart_rate": w.max_heart_rate
            }
            for w in workouts
        ]

        # Get step data (last 3 days including today)
        step_result = await db.execute(
            select(
                func.date(StepMinute.start_minute).label('date'),
                func.sum(StepMinute.steps).label('total_steps')
            )
            .where(StepMinute.user_id == user_id)
            .where(StepMinute.start_minute >= three_days_ago)
            .group_by(func.date(StepMinute.start_minute))
            .order_by(desc('date'))
            .limit(3)
        )
        step_data = step_result.all()
        context["step_data"] = [
            {
                "date": row.date.isoformat() if hasattr(row.date, 'isoformat') else str(row.date),
                "total_steps": row.total_steps
            }
            for row in step_data
        ]

        # Get sleep data (last 3 sessions)
        sleep_result = await db.execute(
            select(SleepSession)
            .where(SleepSession.user_id == user_id)
            .order_by(desc(SleepSession.start_time))
            .limit(3)
        )
        sleep_sessions = sleep_result.scalars().all()
        if sleep_sessions:
            context["sleep_data"] = [
                {
                    "date": s.start_time.date().isoformat(),
                    "duration_hours": s.duration_minutes / 60,
                    "quality": getattr(s, 'quality', None)
                }
                for s in sleep_sessions
            ]

        # Get daily training intention for today
        today = datetime.utcnow().date()
        if context["profile"]:
            intention_result = await db.execute(
                select(UserDailyTrainingIntention)
                .where(UserDailyTrainingIntention.profile_id == context["profile"].id)
                .where(UserDailyTrainingIntention.intention_date == today)
            )
            context["daily_intention"] = intention_result.scalar_one_or_none()
        else:
            context["daily_intention"] = None

        # Get medical conditions
        if context["profile"]:
            medical_conditions_result = await db.execute(
                select(UserMedicalCondition, MedicalCondition)
                .join(MedicalCondition, UserMedicalCondition.medical_condition_id == MedicalCondition.id)
                .where(UserMedicalCondition.profile_id == context["profile"].id)
            )
            medical_conditions = medical_conditions_result.all()
            context["medical_conditions"] = [
                {
                    "name": mc.MedicalCondition.name,
                    "notes": mc.UserMedicalCondition.notes
                }
                for mc in medical_conditions
            ]
        else:
            context["medical_conditions"] = []

        # Calculate trends from historical data
        context["trends"] = self._calculate_trends(context)

        # Get today's current stats
        context["today_stats"] = await self._get_today_stats(db, user_id, today)

        # Get previous recommendations (last 7 days)
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        prev_rec_result = await db.execute(
            select(CoachingRecommendation)
            .where(CoachingRecommendation.user_id == user_id)
            .where(CoachingRecommendation.recommendation_date >= seven_days_ago)
            .order_by(desc(CoachingRecommendation.recommendation_date))
            .limit(7)
        )
        previous_recs = prev_rec_result.scalars().all()

        logger.info(f"🔍 Found {len(previous_recs)} previous recommendations (last 7 days)")

        context["previous_recommendations"] = [
            {
                "date": rec.recommendation_date.date().isoformat(),
                "workout_type": rec.workout_type,
                "duration_minutes": rec.duration_minutes,
                "status": rec.status,
                "compliance_notes": rec.compliance_notes
            }
            for rec in previous_recs
        ]

        # Log summary of gathered data
        logger.info(f"📊 Context Summary:")
        profile = context.get('profile')
        first_name = profile.first_name if profile and profile.first_name else 'Unknown'
        logger.info(f"  - Name: {first_name}")
        logger.info(f"  - Profile: {'✓' if profile else '✗'}")
        logger.info(f"  - Today Stats: {context['today_stats']}")
        logger.info(f"  - Trends: {list(context['trends'].keys())}")
        logger.info(f"  - Step data points: {len(context['step_data'])}")
        logger.info(f"  - VO2 data points: {len(context['vo2_data'])}")
        logger.info(f"  - HR data points: {len(context['heart_rate_data'])}")
        logger.info(f"  - Workout data points: {len(context['workout_data'])}")

        return context

    def _calculate_trends(self, context: Dict) -> Dict:
        """Calculate trends from historical data."""
        trends = {}

        # VO2 Max trend
        vo2_data = context.get("vo2_data", [])
        if len(vo2_data) >= 2:
            latest_vo2 = vo2_data[0].ml_per_kg_min
            oldest_vo2 = vo2_data[-1].ml_per_kg_min
            vo2_change = latest_vo2 - oldest_vo2
            vo2_change_pct = (vo2_change / oldest_vo2) * 100 if oldest_vo2 > 0 else 0
            trends["vo2_max"] = {
                "latest": latest_vo2,
                "oldest": oldest_vo2,
                "change": vo2_change,
                "change_percent": vo2_change_pct,
                "direction": "improving" if vo2_change > 0 else "declining" if vo2_change < 0 else "stable"
            }

        # Heart rate trend
        hr_data = context.get("heart_rate_data", [])
        if len(hr_data) >= 2:
            latest_hr = hr_data[0]["avg_bpm"]
            oldest_hr = hr_data[-1]["avg_bpm"]
            hr_change = latest_hr - oldest_hr
            trends["heart_rate"] = {
                "latest": latest_hr,
                "oldest": oldest_hr,
                "change": hr_change,
                "direction": "decreasing" if hr_change < 0 else "increasing" if hr_change > 0 else "stable"
            }

        # Weight trend
        weight_history = context.get("weight_history", [])
        if len(weight_history) >= 2:
            latest_weight = weight_history[0].weight_lbs
            oldest_weight = weight_history[-1].weight_lbs
            weight_change = latest_weight - oldest_weight
            trends["weight"] = {
                "latest": latest_weight,
                "oldest": oldest_weight,
                "change": weight_change,
                "direction": "decreasing" if weight_change < 0 else "increasing" if weight_change > 0 else "stable"
            }

        # Workout frequency trend
        workout_data = context.get("workout_data", [])
        if workout_data:
            trends["workout_frequency"] = {
                "recent_count": len(workout_data),
                "message": f"{len(workout_data)} workouts in last 3 sessions"
            }

        return trends

    async def _get_today_stats(self, db: AsyncSession, user_id: str, today: date) -> Dict:
        """Get today's current statistics."""
        stats = {}

        # Today's steps
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())

        step_result = await db.execute(
            select(func.sum(StepMinute.steps))
            .where(StepMinute.user_id == user_id)
            .where(func.date(StepMinute.start_minute) == today)
        )
        stats["steps"] = step_result.scalar() or 0

        # Today's average heart rate
        hr_result = await db.execute(
            select(func.avg(HeartRateSample.bpm))
            .where(HeartRateSample.user_id == user_id)
            .where(HeartRateSample.captured_at >= today_start)
            .where(HeartRateSample.captured_at <= today_end)
        )
        avg_hr = hr_result.scalar()
        stats["avg_heart_rate"] = round(avg_hr) if avg_hr else None

        # Today's workout count
        workout_count_result = await db.execute(
            select(func.count(WorkoutSession.id))
            .where(WorkoutSession.user_id == user_id)
            .where(func.date(WorkoutSession.start_time) == today)
        )
        stats["workout_count"] = workout_count_result.scalar() or 0

        # Latest VO2 max (not necessarily from today)
        vo2_result = await db.execute(
            select(VO2MaxEstimate)
            .where(VO2MaxEstimate.user_id == user_id)
            .order_by(desc(VO2MaxEstimate.measured_at))
            .limit(1)
        )
        latest_vo2 = vo2_result.scalar_one_or_none()
        stats["vo2_max"] = latest_vo2.ml_per_kg_min if latest_vo2 else None

        return stats

    def _create_context_summary(self, context: Dict) -> Dict:
        """Create a human-readable summary of user context."""

        profile = context.get("profile")
        summary = {
            "has_profile": profile is not None,
            "demographics": {},
            "goals_count": len(context.get("goals", [])),
            "has_training_preferences": context.get("training_preferences") is not None,
            "data_availability": {}
        }

        if profile:
            summary["demographics"] = {
                "age": profile.age,
                "gender": profile.gender,
                "height_inches": profile.height_inches
            }

        summary["data_availability"] = {
            "weight": context.get("latest_weight") is not None,
            "vo2_max": len(context.get("vo2_data", [])) > 0,
            "heart_rate": len(context.get("heart_rate_data", [])) > 0,
            "sleep": context.get("sleep_data") is not None,
            "workouts": len(context.get("workout_data", [])) > 0,
            "steps": len(context.get("step_data", [])) > 0
        }

        return summary

    async def _generate_ai_insights(self, context: Dict) -> Dict:
        """Generate AI insights using OpenAI with structured output."""

        try:
            prompt = self._build_coaching_prompt(context)

            logger.info(f"🤖 Sending prompt to OpenAI (length: {len(prompt)} chars)")
            logger.debug(f"📝 Prompt preview:\n{prompt[:500]}...")

            # Use structured output with response_format
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": self._get_system_prompt()
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "coaching_recommendation",
                        "strict": True,
                        "schema": {
                            "type": "object",
                            "properties": {
                                "todays_training": {
                                    "type": "string",
                                    "description": "Today's training section with markdown formatting including greeting, stats, and workout details"
                                },
                                "nutrition_fueling": {
                                    "type": "string",
                                    "description": "Nutrition and fueling guidance with markdown formatting"
                                },
                                "recovery_protocol": {
                                    "type": "string",
                                    "description": "Recovery protocol with markdown formatting"
                                },
                                "reasoning": {
                                    "type": "string",
                                    "description": "The reasoning behind the recommendation with markdown formatting"
                                }
                            },
                            "required": ["todays_training", "nutrition_fueling", "recovery_protocol", "reasoning"],
                            "additionalProperties": False
                        }
                    }
                },
                temperature=0.7,
                max_tokens=2000
            )

            insights_text = response.choices[0].message.content
            logger.info(f"✅ Received AI response (length: {len(insights_text)} chars)")
            logger.debug(f"📄 AI response:\n{insights_text}")

            # Parse JSON response directly
            parsed_insights = json.loads(insights_text)

            return {
                "success": True,
                "insights": parsed_insights,
                "raw_response": insights_text
            }

        except Exception as e:
            logger.error(f"❌ Error calling OpenAI API: {e}", exc_info=True)
            logger.info(f"⚠️ Using fallback insights with available context data")
            return {
                "success": False,
                "error": str(e),
                "insights": self._get_fallback_insights(context)
            }

    def _get_system_prompt(self) -> str:
        """Get the system prompt for AI coaching."""

        return """You are an American Olympic Marathon coach working with world renowned sport physiologists who specialize in marathon training. You speak like a coach—encouraging but direct, no fluff.

    Your Mission:
    Deliver a specific workout plan for TODAY based on the athletes' previous running session performance. You are trying to improve the athlete's performance such that it results in an improvement in the VO2 max.
    STRICT LENGTH REQUIREMENT: Total response MUST be 25-50 words MAXIMUM, in bullet format. Be ultra-concise.

    CRITICAL REQUIREMENTS:
    1. **USE THE ATHLETE'S FIRST NAME** in your response (it's provided in the prompt)
    2. **REFERENCE TODAY'S STATS** - VO2 max
    3. **REFERENCE SPECIFIC TRENDS** from their data (e.g., "VO2 improving +6%" or "HR elevated +5 bpm" or "coaching sessions this past week")
    4. **CHECK WORKOUT STATUS**
    5. **RESPECT TRAINING INTENTIONS** - If they said "NO" to training today
    6. **ALIGN WITH WORKOUT PREFERENCES**
    7. You MUST provide a specific running workout for TODAY, not general advice

    RESPONSE FORMAT:
    You MUST return a JSON object with exactly 4 fields. Each field should contain markdown-formatted text WITHOUT section headers (the frontend handles headers):

    {
        "todays_training": "**Hey [Name]!** [X] workouts, VO₂ [value] [trend].\n\n**Today:** [distance/time] [workout type], Zone [X] ([BPM range])",
        "nutrition_fueling": "- **Pre-workout:** [food] [timing]\n- **Post-workout:** [food] [timing]\n- **Daily:** [guideline]",
        "recovery_protocol": "- **Sleep:** [hours] hours\n- **Stretching:** [duration/type]",
        "reasoning": "[1-2 sentences explaining the specific trend + why this plan works]"
    }

    Key Principles (NON-NEGOTIABLE):
    - EXACTLY 25-50 words total response across all sections
    - **FIRST SENTENCE MUST ALWAYS INCLUDE**: Name + workouts count + VO₂ + Trend
    Example: "**Hey Faisal!** 0 workouts, VO₂ 46.5 improving +5.2%."
    - NEVER start with generic greeting without stats
    - ALWAYS give TODAY's exact workout with zones in SECOND sentence
    - ALWAYS reference specific numbers from today's stats (HR, VO2)
    - ALWAYS mention specific trend with numbers (e.g., "improving +5.2%" or "down -10 bpm")
    - Calculate HR zones: Max HR = 220 - age, then Zone 1 (50-60%), Zone 2 (60-70%), etc.
    - Ultra-specific: "5 miles, Zone 2, 140-150 BPM" NOT "easy run"
    - Respect training intention (NO = recovery only, YES = workout)
    - If 0 workouts logged + YES intention = encourage to start

    EXAMPLE JSON RESPONSES:

    ✅ PERFECT Example:
    {
        "todays_training": "**Hey Faisal!** 0 workouts, VO₂ 46.5 improving +5.2%.\\n\\n**Today:** 30-min walk, Zone 1 (80-90 BPM)",
        "nutrition_fueling": "- **Pre-workout:** Water 30min before\\n- **Post-workout:** Protein shake within 30min\\n- **Daily:** 1.5g protein/lb bodyweight",
        "recovery_protocol": "- **Sleep:** 7-8 hours\\n- **Stretching:** 10min post-workout",
        "reasoning": "Building aerobic base while VO₂ trending up. Active recovery consolidates gains."
    }

    ✅ GOOD Example:
    {
        "todays_training": "**Hey Sarah!** 2 workouts, VO₂ 52.3 up +6%.\\n\\n**Today:** 5 miles, Zone 2 (140-150 BPM)",
        "nutrition_fueling": "- **Pre-workout:** Banana 30min before\\n- **Post-workout:** Recovery drink within 30min\\n- **Daily:** 2g protein/lb bodyweight",
        "recovery_protocol": "- **Sleep:** 8 hours\\n- **Stretching:** 15min foam rolling",
        "reasoning": "VO₂ up 6%, time for Zone 2 to build endurance without overtraining."
    }

    ❌ BAD - Missing stats in first sentence:
    "**Hey Mike!** You're doing great. Today: 30-min run." (NO! Must include workouts, VO₂!)

    ❌ BAD - Too wordy, no specific stats:
    "It's important to listen to your body and maintain your training routine..." (NO!)

    ❌ BAD - Too vague:
    "Today: Continue your regular workout." (NO!)

    REMEMBER: Return valid JSON with all 4 fields. Use \\n for line breaks in strings. NO section headers (##). Name + workouts count + VO₂ + trend in first sentence."""

    
    def _build_coaching_prompt(self, context: Dict) -> str:
        """Build the coaching prompt with user data."""

        profile = context.get("profile")
        goals = context.get("goals", [])
        training_prefs = context.get("training_preferences")
        weight = context.get("latest_weight")
        vo2_list = context.get("vo2_data", [])
        hr_list = context.get("heart_rate_data", [])
        sleep_list = context.get("sleep_data", [])
        workouts = context.get("workout_data", [])
        steps = context.get("step_data", [])
        trends = context.get("trends", {})
        today_stats = context.get("today_stats", {})
        daily_intention = context.get("daily_intention")
        medical_conditions = context.get("medical_conditions", [])

        # Extract user's first name from profile
        first_name = profile.first_name if profile and profile.first_name else "Athlete"

        # Build prompt
        prompt_parts = [f"Provide personalized coaching recommendations for {first_name}:\n"]

        # TODAY'S CURRENT STATS (Most important - at the top!)
        prompt_parts.append(f"""
**TODAY'S CURRENT STATS:**
- Steps so far: {today_stats.get('steps', 0):,}
- Average Heart Rate: {today_stats.get('avg_heart_rate', 'No data yet')} bpm
- Workouts completed: {today_stats.get('workout_count', 0)}
- Latest VO₂ Max: {today_stats.get('vo2_max', 'Not available')} ml/kg/min
""")

        # DAILY TRAINING INTENTION
        if daily_intention:
            intention_map = {
                "yes": "YES - wants to train today",
                "no": "NO - rest/recovery day",
                "maybe": "MAYBE - flexible about training"
            }
            intention_text = intention_map.get(daily_intention.intention.lower(), daily_intention.intention)
            prompt_parts.append(f"""
**TODAY'S TRAINING INTENTION:**
- {intention_text}
{f"- Notes: {daily_intention.notes}" if daily_intention.notes else ""}
""")

        # Demographics with MORE DETAIL
        if profile:
            prompt_parts.append(f"""
**Athlete Profile:**
- Name: {first_name}
- Age: {profile.age or 'Not specified'}
- Gender: {profile.gender or 'Not specified'}
- Height: {profile.height_inches or 'Not specified'} inches
- Weight: {weight.value_lbs if weight else 'Not specified'} lbs
""")

        # Medical Conditions
        if medical_conditions:
            conditions_text = "\n".join([
                f"- {mc['name']}" + (f" ({mc['notes']})" if mc['notes'] else "")
                for mc in medical_conditions
            ])
            prompt_parts.append(f"""
**Medical Conditions:**
{conditions_text}
""")

        # Goals
        if goals:
            goals_text = "\n".join([f"- {g.goal_type}: {g.description or 'No description'} (Target: {g.target_value} {g.unit or ''})" for g in goals])
            prompt_parts.append(f"""
**Goals:**
{goals_text}
""")
        else:
            prompt_parts.append("\n**Goals:** Not specified yet\n")

        # Training preferences
        if training_prefs:
            prompt_parts.append(f"""
**Training Preferences:**
- Experience level: {training_prefs.training_level}
- Frequency: {training_prefs.days_per_week} days/week
- Sessions per day: {training_prefs.sessions_per_day}
- Preferred time: {training_prefs.preferred_time_window or 'Flexible'}
""")

        # Weight data
        if weight:
            weight_trend = "stable"
            if len(context.get("weight_history", [])) > 1:
                recent = context["weight_history"][0].value_lbs
                older = context["weight_history"][-1].value_lbs
                diff = recent - older
                if diff < -2:
                    weight_trend = f"decreasing ({abs(diff):.1f} lbs)"
                elif diff > 2:
                    weight_trend = f"increasing ({diff:.1f} lbs)"

            prompt_parts.append(f"""
**Weight:**
- Current: {weight.value_lbs} lbs
- Trend: {weight_trend}
""")

        # VO2 max (last 3 readings)
        if vo2_list:
            vo2_text = "\n".join([
                f"  - {vo2.measured_at.strftime('%Y-%m-%d')}: {vo2.ml_per_kg_min} ml/kg/min"
                for vo2 in vo2_list
            ])
            prompt_parts.append(f"""
**VO₂max (Last 3 Readings):**
{vo2_text}
""")

        # Heart rate (last 3 days)
        if hr_list:
            hr_text = "\n".join([
                f"  - {hr['date']}: Avg {hr['avg_bpm']:.0f} bpm (Range: {hr['min_bpm']}-{hr['max_bpm']} bpm, {hr['samples']} samples)"
                for hr in hr_list
            ])
            prompt_parts.append(f"""
**Heart Rate (Last 3 Days):**
{hr_text}
""")

        # Workouts (last 3)
        if workouts:
            workout_text = "\n".join([
                f"  - {w['start_time'][:10]}: {w['activity_type']} - {w['duration_minutes']:.0f} min" +
                (f", {w['distance_miles']:.1f} miles" if w['distance_miles'] else "") +
                (f", {w['calories']:.0f} cal" if w['calories'] else "") +
                (f", Avg HR: {w['avg_heart_rate']} bpm" if w['avg_heart_rate'] else "")
                for w in workouts
            ])
            prompt_parts.append(f"""
**Recent Workouts (Last 3):**
{workout_text}
""")

        # Steps (last 3 days)
        if steps:
            steps_text = "\n".join([
                f"  - {s['date']}: {s['total_steps']:,} steps"
                for s in steps
            ])
            prompt_parts.append(f"""
**Daily Steps (Last 3 Days):**
{steps_text}
""")

        # Sleep (last 3 sessions)
        if sleep_list:
            sleep_text = "\n".join([
                f"  - {s['date']}: {s['duration_hours']:.1f} hours" +
                (f" ({s['quality']})" if s['quality'] else "")
                for s in sleep_list
            ])
            prompt_parts.append(f"""
**Sleep (Last 3 Sessions):**
{sleep_text}
""")

        # RECENT PROGRESS & TRENDS (Critical for AI to reference!)
        if trends:
            trends_parts = []

            # VO2 Max trend
            if "vo2_max" in trends:
                vo2_trend = trends["vo2_max"]
                change_text = f"{vo2_trend['change']:+.1f} ml/kg/min ({vo2_trend['change_percent']:+.1f}%)"
                trends_parts.append(f"- VO₂ Max: {vo2_trend['oldest']:.1f} → {vo2_trend['latest']:.1f} ml/kg/min ({change_text}) - {vo2_trend['direction']}")

            # Heart rate trend
            if "heart_rate" in trends:
                hr_trend = trends["heart_rate"]
                change_text = f"{hr_trend['change']:+.0f} bpm"
                trends_parts.append(f"- Resting HR: {hr_trend['oldest']:.0f} → {hr_trend['latest']:.0f} bpm ({change_text}) - {hr_trend['direction']}")

            # Weight trend
            if "weight" in trends:
                weight_trend = trends["weight"]
                change_text = f"{weight_trend['change']:+.1f} lbs"
                trends_parts.append(f"- Weight: {weight_trend['oldest']:.1f} → {weight_trend['latest']:.1f} lbs ({change_text}) - {weight_trend['direction']}")

            # Workout frequency
            if "workout_frequency" in trends:
                workout_trend = trends["workout_frequency"]
                trends_parts.append(f"- Recent activity: {workout_trend['message']}")

            if trends_parts:
                trends_text = "\n".join(trends_parts)
                prompt_parts.append(f"""
**RECENT PROGRESS & TRENDS:**
{trends_text}

IMPORTANT: Reference these specific trends in your recommendations! Mention improving/declining metrics by name with numbers.
""")

        # PREVIOUS RECOMMENDATIONS & COMPLIANCE (Critical for context!)
        previous_recs = context.get("previous_recommendations", [])
        if previous_recs:
            # Calculate compliance rate
            total_recs = len(previous_recs)
            completed = sum(1 for r in previous_recs if r['status'] == 'completed')
            skipped = sum(1 for r in previous_recs if r['status'] == 'skipped')
            partial = sum(1 for r in previous_recs if r['status'] == 'partial')

            compliance_rate = (completed / total_recs * 100) if total_recs > 0 else 0

            recs_text = "\n".join([
                f"  - {r['date']}: {r['workout_type'] or 'No workout'} "
                f"({r['duration_minutes'] or 0} min) - {r['status'].upper()}" +
                (f" ({r['compliance_notes']})" if r['compliance_notes'] else "")
                for r in previous_recs[:5]  # Show last 5
            ])

            logger.info(f"📋 Using {total_recs} previous recommendations in AI prompt:")
            logger.info(f"   ✅ Completed: {completed}, ⚠️ Partial: {partial}, ❌ Skipped: {skipped}")
            logger.info(f"   📊 Compliance Rate: {compliance_rate:.0f}%")
            for rec in previous_recs[:3]:  # Log last 3
                logger.info(f"   - {rec['date']}: {rec['workout_type']} ({rec['duration_minutes']}min) → {rec['status'].upper()}")

            prompt_parts.append(f"""
**PREVIOUS RECOMMENDATIONS & COMPLIANCE (Last 7 Days):**
- Compliance Rate: {compliance_rate:.0f}% ({completed} completed, {partial} partial, {skipped} skipped out of {total_recs})
{recs_text}

CRITICAL: Use this history to:
1. Acknowledge what the athlete actually did (e.g., "You completed yesterday's 5K run!")
2. Adjust difficulty based on compliance (consistent completion = increase intensity, frequent skipping = easier workouts)
3. Reference specific past recommendations (e.g., "Building on Tuesday's tempo run...")
""")
        else:
            logger.info(f"📋 No previous recommendations found (first time user or no history)")

        prompt_parts.append(f"\nPlease provide comprehensive, personalized coaching recommendations for {first_name} based on all this data.")

        full_prompt = "\n".join(prompt_parts)
        return full_prompt

    def _parse_coaching_response(self, response_text: str) -> Dict:
        """Parse the AI coaching response into structured sections."""

        sections = {
            'todays_training': '',
            'nutrition_fueling': '',
            'recovery_protocol': '',
            'reasoning': ''
        }

        current_section = None
        lines = response_text.split('\n')

        for line in lines:
            line = line.strip()

            if line.startswith("## Today's Training") or line.startswith("## Today's Training"):
                current_section = 'todays_training'
                continue
            elif line.startswith('## Nutrition & Fueling') or line.startswith('## Nutrition and Fueling'):
                current_section = 'nutrition_fueling'
                continue
            elif line.startswith('## Recovery Protocol'):
                current_section = 'recovery_protocol'
                continue
            elif line.startswith('## The Reasoning'):
                current_section = 'reasoning'
                continue
            elif line.startswith('##'):
                current_section = None
                continue

            if current_section and line:
                sections[current_section] += line + ' '

        # Clean up sections
        for key in sections:
            sections[key] = sections[key].strip()

        # Fallback if parsing fails
        if not any(sections.values()):
            sections['todays_training'] = response_text

        return sections

    def _convert_insights_to_recommendations(self, insights: Dict) -> List[Dict]:
        """Convert AI insights sections into an array of recommendation objects."""

        recommendations = []

        # Add today's training as the primary recommendation
        todays_training = insights.get('todays_training', '')
        if todays_training:
            recommendations.append({
                "title": "Today's Workout",
                "description": todays_training,
                "category": "training",
                "priority": "high"
            })

        # Add nutrition & fueling
        nutrition = insights.get('nutrition_fueling', '')
        if nutrition:
            recommendations.append({
                "title": "Nutrition & Fueling",
                "description": nutrition,
                "category": "nutrition",
                "priority": "high"
            })

        # Add recovery protocol
        recovery = insights.get('recovery_protocol', '')
        if recovery:
            recommendations.append({
                "title": "Recovery Protocol",
                "description": recovery,
                "category": "recovery",
                "priority": "medium"
            })

        # Add reasoning as context
        reasoning = insights.get('reasoning', '')
        if reasoning:
            recommendations.append({
                "title": "Coach's Analysis",
                "description": reasoning,
                "category": "insight",
                "priority": "low"
            })

        # If no recommendations were parsed, create a default one
        if not recommendations:
            recommendations.append({
                "title": "Daily Workout",
                "description": "Keep training consistently. Review your metrics and adjust as needed.",
                "category": "general",
                "priority": "medium"
            })

        return recommendations

    def _generate_quick_actions(self, context: Dict) -> List[Dict]:
        """Generate quick action items based on user data."""

        actions = []

        # Check for missing data
        if not context.get("latest_weight"):
            actions.append({
                "type": "data_input",
                "priority": "high",
                "title": "Log Your Weight",
                "description": "Track your weight to get personalized recommendations",
                "action": "log_weight"
            })

        # VO2 data now comes from Apple Health automatically
        # Removed device connection recommendation

        # Goal-based actions
        goals = context.get("goals", [])
        if goals:
            for goal in goals[:2]:  # Top 2 goals
                actions.append({
                    "type": "goal_progress",
                    "priority": "medium",
                    "title": f"Track Progress: {goal.goal_type}",
                    "description": f"Target: {goal.target_value} {goal.unit or ''}",
                    "action": "view_goal_progress"
                })

        # Training-based actions
        training_prefs = context.get("training_preferences")
        if training_prefs:
            actions.append({
                "type": "training",
                "priority": "high",
                "title": "Today's Workout",
                "description": f"Schedule your {training_prefs.training_level} level training",
                "action": "view_workout_plan"
            })

        return actions[:4]  # Return top 4 actions

    def _get_fallback_recommendations(self) -> Dict:
        """Provide fallback recommendations if AI fails."""

        return {
            "todays_training": "**Hey Athlete!** No recent data available.\n\n**Today:** 30-min easy run, Zone 2 (conversational pace)",
            "nutrition_fueling": "- **Pre-workout:** Light carbs 30-60min before (banana, toast)\n- **Post-workout:** Protein + carbs within 30min\n- **Daily:** Stay hydrated, 0.5-0.7g protein/lb bodyweight",
            "recovery_protocol": "- **Sleep:** 7-9 hours\n- **Stretching:** Foam roll 10min post-run",
            "reasoning": "Building aerobic base with easy-paced runs—foundation for endurance training."
        }

    def _get_fallback_insights(self, context: Dict) -> Dict:
        """Get fallback insights when AI call fails - uses available context data."""

        profile = context.get("profile")
        today_stats = context.get("today_stats", {})
        trends = context.get("trends", {})

        # Extract first name from profile
        first_name = profile.first_name if profile and profile.first_name else "Athlete"

        # Build first sentence with available stats
        workouts = today_stats.get('workout_count', 0) if today_stats else 0
        vo2 = today_stats.get('vo2_max') if today_stats else None

        # Build trend text
        trend_text = "stable"
        if vo2 and trends.get("vo2_max"):
            vo2_trend = trends["vo2_max"]
            change_pct = vo2_trend['change_percent']
            if abs(change_pct) >= 1:
                trend_text = f"{'improving' if change_pct > 0 else 'declining'} {'+' if change_pct > 0 else ''}{change_pct:.1f}%"

        vo2_text = f"{vo2:.1f}" if vo2 else "N/A"
        first_line = f"**Hey {first_name}!** {workouts} workouts, VO₂ {vo2_text} {trend_text}."

        # Calculate HR zone if we have age
        age = profile.age if profile else 30
        max_hr = 220 - age
        zone1_low = int(max_hr * 0.5)
        zone1_high = int(max_hr * 0.6)

        training_message = f"{first_line}\n\n**Today:** 30-min easy walk, Zone 1 ({zone1_low}-{zone1_high} BPM)"

        # Build nutrition section (without header)
        nutrition_message = "- **Pre-workout:** Water 30min before\n- **Post-workout:** Protein shake within 30min\n- **Daily:** 0.6g protein/lb bodyweight"

        # Build recovery section (without header)
        recovery_message = "- **Sleep:** 7-8 hours\n- **Stretching:** 10min post-workout"

        # Build reasoning with trends if available (without header)
        reasoning = "Building aerobic base—foundation for endurance training."
        if trends.get("vo2_max"):
            vo2_trend = trends["vo2_max"]
            direction = vo2_trend['direction']
            reasoning = f"VO₂ {direction}. Active recovery consolidates gains."
        elif trends.get("heart_rate"):
            hr_trend = trends["heart_rate"]
            direction = hr_trend['direction']
            reasoning = f"Resting HR {direction}. Building base while managing recovery."

        return {
            "todays_training": training_message,
            "nutrition_fueling": nutrition_message,
            "recovery_protocol": recovery_message,
            "reasoning": reasoning
        }

    async def _save_recommendation(
        self,
        db: AsyncSession,
        user_id: str,
        insights: Dict
    ) -> Optional[CoachingRecommendation]:
        """Save the coaching recommendation to the database."""

        try:
            # Extract workout details from the training text
            training_text = insights.get('todays_training', '')
            workout_details = self._extract_workout_details(training_text)

            logger.info(f"💾 Saving new recommendation for user {user_id}")
            logger.info(f"   📝 Extracted workout: {workout_details.get('workout_type')} - {workout_details.get('duration_minutes')} min")
            logger.info(f"   🎯 Zone: {workout_details.get('intensity_zone')}, HR: {workout_details.get('heart_rate_range')}")

            # Create recommendation record
            recommendation = CoachingRecommendation(
                user_id=user_id,
                recommendation_date=datetime.utcnow(),
                workout_type=workout_details.get('workout_type'),
                duration_minutes=workout_details.get('duration_minutes'),
                intensity_zone=workout_details.get('intensity_zone'),
                heart_rate_range=workout_details.get('heart_rate_range'),
                todays_training=insights.get('todays_training'),
                nutrition_fueling=insights.get('nutrition_fueling'),
                recovery_protocol=insights.get('recovery_protocol'),
                reasoning=insights.get('reasoning'),
                status=RecommendationStatus.PENDING.value
            )

            db.add(recommendation)
            await db.commit()
            await db.refresh(recommendation)

            logger.info(f"✅ Saved recommendation {recommendation.id} for user {user_id}")
            logger.info(f"   📌 Status: {recommendation.status}")
            return recommendation

        except Exception as e:
            logger.error(f"❌ Error saving recommendation: {e}")
            await db.rollback()
            return None

    def _extract_workout_details(self, training_text: str) -> Dict:
        """Extract workout details from the training recommendation text."""

        details = {
            'workout_type': None,
            'duration_minutes': None,
            'intensity_zone': None,
            'heart_rate_range': None
        }

        if not training_text:
            return details

        # Extract workout type (run, walk, cycling, etc.)
        workout_patterns = {
            'run': r'\b(run|jog|running|jogging)\b',
            'walk': r'\b(walk|walking)\b',
            'cycling': r'\b(cycl|bike|biking)\b',
            'rest': r'\b(rest|recovery)\b',
            'interval': r'\b(interval|HIIT)\b'
        }

        for workout_type, pattern in workout_patterns.items():
            if re.search(pattern, training_text, re.IGNORECASE):
                details['workout_type'] = workout_type
                break

        # Extract duration (e.g., "30-min", "30 min", "30 minutes")
        duration_match = re.search(r'(\d+)[\s-]?(min|minute)', training_text, re.IGNORECASE)
        if duration_match:
            details['duration_minutes'] = int(duration_match.group(1))

        # Extract zone (e.g., "Zone 1", "Zone 2")
        zone_match = re.search(r'Zone\s+(\d+)', training_text, re.IGNORECASE)
        if zone_match:
            details['intensity_zone'] = f"zone_{zone_match.group(1)}"

        # Extract heart rate range (e.g., "140-150 BPM", "(80-90 BPM)")
        hr_match = re.search(r'(\d+)[-–](\d+)\s*(?:BPM|bpm)', training_text)
        if hr_match:
            details['heart_rate_range'] = f"{hr_match.group(1)}-{hr_match.group(2)}"

        return details

    async def check_recommendation_compliance(
        self,
        db: AsyncSession,
        user_id: str
    ) -> Dict:
        """Check if user followed yesterday's recommendation and update status."""

        try:
            # Get yesterday's recommendation
            yesterday = datetime.utcnow().date() - timedelta(days=1)
            yesterday_start = datetime.combine(yesterday, datetime.min.time())
            yesterday_end = datetime.combine(yesterday, datetime.max.time())

            result = await db.execute(
                select(CoachingRecommendation)
                .where(CoachingRecommendation.user_id == user_id)
                .where(CoachingRecommendation.recommendation_date >= yesterday_start)
                .where(CoachingRecommendation.recommendation_date <= yesterday_end)
                .where(CoachingRecommendation.status == RecommendationStatus.PENDING.value)
            )
            recommendation = result.scalar_one_or_none()

            if not recommendation:
                return {
                    "checked": False,
                    "message": "No pending recommendation from yesterday"
                }

            # Get yesterday's workouts
            workout_result = await db.execute(
                select(WorkoutSession)
                .where(WorkoutSession.user_id == user_id)
                .where(func.date(WorkoutSession.start_time) == yesterday)
            )
            workouts = workout_result.scalars().all()

            # Check compliance
            compliance_result = self._match_recommendation_to_workouts(
                recommendation, workouts
            )

            # Update recommendation status
            recommendation.status = compliance_result['status']
            recommendation.compliance_notes = compliance_result['notes']
            if compliance_result.get('matched_workout_id'):
                recommendation.actual_workout_id = compliance_result['matched_workout_id']

            await db.commit()

            logger.info(f"✅ Updated compliance for recommendation {recommendation.id}: {compliance_result['status']}")

            return {
                "checked": True,
                "recommendation_id": recommendation.id,
                "status": compliance_result['status'],
                "notes": compliance_result['notes']
            }

        except Exception as e:
            logger.error(f"❌ Error checking compliance: {e}")
            return {
                "checked": False,
                "error": str(e)
            }

    def _match_recommendation_to_workouts(
        self,
        recommendation: CoachingRecommendation,
        workouts: List[WorkoutSession]
    ) -> Dict:
        """Match a recommendation to actual workouts to determine compliance."""

        if not workouts:
            return {
                "status": RecommendationStatus.SKIPPED.value,
                "notes": "No workouts logged for this day"
            }

        # Get recommended details
        rec_type = recommendation.workout_type
        rec_duration = recommendation.duration_minutes

        # Check each workout for a match
        for workout in workouts:
            workout_type = workout.activity_type.lower() if workout.activity_type else ""
            workout_duration = workout.duration_seconds / 60 if workout.duration_seconds else 0

            # Check if workout type matches
            type_match = False
            if rec_type:
                if rec_type in workout_type or workout_type in rec_type:
                    type_match = True

            # Check if duration is close (within 20% tolerance)
            duration_match = False
            if rec_duration and workout_duration:
                tolerance = rec_duration * 0.2
                if abs(workout_duration - rec_duration) <= tolerance:
                    duration_match = True

            # Determine match quality
            if type_match and duration_match:
                return {
                    "status": RecommendationStatus.COMPLETED.value,
                    "notes": f"Completed: {workout.activity_type}, {workout_duration:.0f} min",
                    "matched_workout_id": workout.id
                }
            elif type_match or duration_match:
                return {
                    "status": RecommendationStatus.PARTIAL.value,
                    "notes": f"Partial: Did {workout.activity_type}, {workout_duration:.0f} min instead of {rec_type}, {rec_duration} min",
                    "matched_workout_id": workout.id
                }

        # User did workouts but didn't match recommendation
        workout_summary = ", ".join([
            f"{w.activity_type} ({w.duration_seconds/60:.0f} min)"
            for w in workouts[:2]
        ])
        return {
            "status": RecommendationStatus.PARTIAL.value,
            "notes": f"Did different workout: {workout_summary}"
        }
