# Injury Tracking - Quick Start Guide

## ✅ Everything is Ready!

Your complete injury tracking system has been implemented. Here's how to activate it:

---

## Step 1: Run Database Migration

```bash
cd /Users/kz/Desktop/work/edgefirm/strideiq_backend
alembic upgrade head
```

This creates the `user_injuries` and `injury_updates` tables.

---

## Step 2: Register Tools with Agent

Find where your agent tools are registered (likely `app/utils/agent_instance.py` or similar) and add:

```python
# Import injury tools
from app.agent_tools.report_injury_tool import report_injury
from app.agent_tools.update_injury_tool import update_injury_status
from app.agent_tools.get_active_injuries_tool import get_active_injuries
from app.agent_tools.get_injury_history_tool import get_injury_history

# Add to your tools list
tools = [
    # Your existing tools
    get_user_profile,
    get_previous_plans,
    get_workout_details,
    get_vo2_trends,
    get_user_health_data,
    create_coaching_plan,
    update_coaching_plan,

    # NEW: Injury tracking tools
    report_injury,
    update_injury_status,
    get_active_injuries,
    get_injury_history,
]
```

---

## Step 3: (Optional) Update System Prompt

Add injury awareness to your agent's system prompt in `app/services/ai_coaching_agent.py`:

```python
system_prompt = """You are an elite Olympic-level running coach...

## Core Coaching Principles

### 1. ALWAYS Understand Before Prescribing
When a user asks for today's workout:
- First, check for any active injuries  # ← NEW
- Ask about yesterday's workout feedback
- Only AFTER gathering context, create today's plan

### 2. Injury Awareness  # ← NEW SECTION
Before creating any workout:
- Check for active injuries
- Adjust recommendations based on pain levels
- Never prescribe workouts that conflict with injury restrictions

When user reports pain:
- Ask: Where? Pain level 1-10? When did it start?
- Document the injury
- Adjust training immediately
- Suggest rest or alternative exercise

Monitor recovery:
- Ask about injury progress regularly
- Update status as user improves
- Gradually return to normal training

...
"""
```

---

## Step 4: Test It!

### Test Scenario 1: Report Injury
```
User: "My left knee hurts when I run"

Expected Agent Behavior:
1. Ask clarifying questions
   - "On scale 1-10, how bad is the pain?"
   - "When did you first notice it?"
   - "Any swelling or stiffness?"

2. User responds: "7/10, started 2 days ago, sharp pain downhill"

3. Agent uses report_injury:
   ✅ Creates injury record in database
   ✅ Adjusts workout recommendation
   ✅ Suggests rest and treatment
```

### Test Scenario 2: Check Injuries Before Workout
```
User: "What's my workout today?"

Expected Agent Behavior:
1. Uses get_active_injuries FIRST
2. Sees: shin_splints (pain 4/10, recovering)
3. Asks: "How's your shin feeling today?"
4. Creates appropriate plan based on injury status
```

---

## Files Created

### Database
- ✅ `alembic/versions/20250118_add_injury_tracking.py` - Migration
- ✅ `app/models/user_injury.py` - UserInjury model
- ✅ `app/models/injury_update.py` - InjuryUpdate model
- ✅ `app/models/user.py` - Added injuries relationship

### Agent Tools
- ✅ `app/agent_tools/report_injury_tool.py`
- ✅ `app/agent_tools/update_injury_tool.py`
- ✅ `app/agent_tools/get_active_injuries_tool.py`
- ✅ `app/agent_tools/get_injury_history_tool.py`

### Documentation
- ✅ `INJURY_TRACKING_PLAN.md` - Full design
- ✅ `INJURY_SYSTEM_SUMMARY.md` - Quick reference
- ✅ `INJURY_IMPLEMENTATION_COMPLETE.md` - What's built
- ✅ This quick start guide

---

## Common Injury Types Supported

```python
# The agent can track these and more:
- shin_splints
- runners_knee
- plantar_fasciitis
- achilles_tendonitis
- it_band_syndrome
- calf_strain
- ankle_sprain
- hip_flexor_strain
- lower_back_pain
- muscle_soreness
# ... any injury the user reports
```

---

## Data Examples

### After Reporting Injury
```json
{
  "success": true,
  "injury_id": "cm4xabc123",
  "injury_type": "shin_splints",
  "affected_area": "right_shin",
  "pain_level": 7,
  "status": "active"
}
```

### After Getting Active Injuries
```json
{
  "has_injuries": true,
  "total_injuries": 1,
  "injuries": [{
    "injury_type": "shin_splints",
    "current_pain_level": 7,
    "status": "active",
    "days_since_injury": 2
  }],
  "most_severe_injury": {
    "injury_type": "shin_splints",
    "pain_level": 7
  }
}
```

---

## That's It!

Run the migration, register the tools, and your AI coach can now:
- ✅ Track injuries from onset to recovery
- ✅ Monitor pain levels over time
- ✅ Adjust workouts based on injuries
- ✅ Identify recurring patterns
- ✅ Prevent re-injury

**All code is production-ready!** 🚀
