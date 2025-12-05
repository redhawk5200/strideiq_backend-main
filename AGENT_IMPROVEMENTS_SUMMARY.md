# AI Coaching Agent - Improvements Summary

## What Was Changed

### ✅ 1. **Removed Regex Extraction - Agent Now Provides Structured Data**

**Problem:** Previously, the agent would provide free-text workout descriptions, and we'd use regex to extract structured data like `workout_type`, `duration_minutes`, etc. This was error-prone and limited.

**Solution:** The agent now provides structured parameters directly when creating/updating plans.

#### Create Plan Tool - Before vs After

**Before:**
```python
@tool
async def create_coaching_plan(
    config: RunnableConfig,
    todays_training: str,
    nutrition_fueling: str = None,
    recovery_protocol: str = None,
    reasoning: str = None
) -> Dict:
    # Extract workout details from text using regex
    workout_details = _extract_workout_details(todays_training)
    # workout_details = {
    #     "workout_type": "run",  # extracted via regex
    #     "duration_minutes": 30,  # extracted via regex
    #     ...
    # }
```

**After:**
```python
@tool
async def create_coaching_plan(
    config: RunnableConfig,
    todays_training: str,
    workout_type: str,                      # ✅ Agent provides
    duration_minutes: int,                  # ✅ Agent provides
    intensity_zone: Optional[str] = None,   # ✅ Agent provides
    heart_rate_range: Optional[str] = None, # ✅ Agent provides
    nutrition_fueling: Optional[str] = None,
    recovery_protocol: Optional[str] = None,
    reasoning: Optional[str] = None
) -> Dict:
    # Use agent-provided data directly - no regex needed!
    recommendation = CoachingRecommendation(
        workout_type=workout_type,
        duration_minutes=duration_minutes,
        intensity_zone=intensity_zone,
        heart_rate_range=heart_rate_range,
        ...
    )
```

#### Update Plan Tool - Before vs After

**Before:**
```python
@tool
async def update_coaching_plan(
    config: RunnableConfig,
    plan_id: str,
    todays_training: Optional[str] = None,
    # ... other fields
) -> Dict:
    if todays_training:
        # Re-extract workout details using regex
        workout_details = _extract_workout_details(todays_training)
        recommendation.workout_type = workout_details.get("workout_type")
        recommendation.duration_minutes = workout_details.get("duration_minutes")
```

**After:**
```python
@tool
async def update_coaching_plan(
    config: RunnableConfig,
    plan_id: str,
    todays_training: Optional[str] = None,
    workout_type: Optional[str] = None,      # ✅ Agent provides
    duration_minutes: Optional[int] = None,  # ✅ Agent provides
    intensity_zone: Optional[str] = None,    # ✅ Agent provides
    heart_rate_range: Optional[str] = None,  # ✅ Agent provides
    # ... other fields
) -> Dict:
    # Update fields directly with agent-provided data
    if workout_type is not None:
        recommendation.workout_type = workout_type
    if duration_minutes is not None:
        recommendation.duration_minutes = duration_minutes
```

---

### ✅ 2. **Improved Tool Descriptions (LangChain Best Practices)**

All tools now have clear, action-oriented descriptions that tell the agent:
- **What** the tool does
- **When** to use it
- **What** data it returns

**Example:**

**Before:**
```python
"""
Get user's previous coaching recommendations including today's plan if it exists.

IMPORTANT: This tool returns ALL plans including today's. Check the 'todays_plan' field
to see if a plan already exists for today BEFORE creating a new one.
"""
```

**After:**
```python
"""
Retrieve the user's recent training history, compliance patterns, and check if today's plan already exists.

Use this when you need to understand what the user has been doing lately, how well they followed previous plans,
or before creating a new plan to avoid duplicates.

Args:
    days: How many days of history to retrieve (default 7)

Returns:
    Recent plans with completion status, compliance rate, and today's plan if it exists
"""
```

---

### ✅ 3. **Simplified System Prompt (Removed Hardcoded Tool Names)**

**Before:**
```
2. Use data to make informed decisions:
   - get_user_profile → Understand goals, preferences, constraints.
   - get_previous_plans → See weekly structure and whether a plan for today already exists.
   - get_workout_details → Review recent sessions and compare performance.
```

**After:**
```
### 3. Data-Driven Decisions
Use available data to inform every decision:
- Compare current performance against past workouts
- Analyze fitness trends (VO₂ progression, heart rate patterns)
- Consider user goals and preferences
- Factor in current health metrics
```

**Why This Is Better:**
- Agent learns to associate principles with tools
- More flexible and adaptable
- Agent can reason about which tool to use when
- No hardcoded workflow - agent decides based on context

---

### ✅ 4. **Enhanced Coaching Flow (Conversation Before Prescription)**

The system prompt now emphasizes:

#### Principle 1: ALWAYS Understand Before Prescribing
```
When a user asks for today's workout:
- First, gather context: Did they complete yesterday's plan? How did it feel? Any soreness or fatigue?
- Check their recent training history and compliance patterns
- Review actual workout performance data to see if they're improving or showing signs of fatigue
- Only AFTER this conversation, create today's plan

Never jump straight to giving a workout without understanding where the athlete is right now.
```

#### Principle 2: Think Weekly, Not Just Daily
```
- Every daily plan fits into a weekly training structure
- Balance hard days with recovery days
- Track weekly training load (how many workouts completed vs skipped)
- Prevent overtraining by monitoring cumulative fatigue
- Adapt intensity based on how the week is progressing
```

---

## Benefits of These Changes

### 🎯 **Agent Intelligence**
The agent now understands what it's prescribing at a structural level, not just generating text.

### ✅ **Data Accuracy**
No more regex parsing failures. Database gets clean, structured data every time.

### 🔧 **Easier Maintenance**
No regex patterns to maintain. Agent handles variations in phrasing naturally.

### 📊 **Better Analytics**
Structured data enables easier analysis of workout patterns, compliance, and trends.

### 💬 **Flexible Communication**
Agent can write `todays_training` in any style (formal, casual, detailed, brief) while still providing structured data.

### 🧠 **Smarter Decision Making**
System prompt guides principles, not specific tool calls. Agent learns to use the right tool at the right time.

---

## Example: How the Agent Uses Structured Parameters

### User Asks for Workout

**Agent's Response to User:**
```
"Hey Mohammed! I see you've completed 3 out of 4 workouts this week with 75% compliance.
Your VO₂ has improved by 2 points this month - great progress!

For today, let's do a 35-minute Zone 2 run (aim for 100-110 BPM). This builds on your
successful Zone 1 sessions and starts to challenge your aerobic base.

Nutrition: Eat a light snack 30 minutes before.
Recovery: 10 minutes of stretching after, focus on calves and quads.

Ready to go?"
```

**Agent's Tool Call (Behind the Scenes):**
```python
create_coaching_plan(
    todays_training="35-minute Zone 2 run (aim for 100-110 BPM)",
    workout_type="run",
    duration_minutes=35,
    intensity_zone="zone_2",
    heart_rate_range="100-110",
    nutrition_fueling="Eat a light snack 30 minutes before",
    recovery_protocol="10 minutes of stretching after, focus on calves and quads",
    reasoning="Building on successful Zone 1 sessions, progressing to Zone 2 to challenge aerobic base. User shows good compliance (75%) and VO2 improvement."
)
```

**Database Record:**
```json
{
  "id": "cm4x...",
  "user_id": "user_123",
  "todays_training": "35-minute Zone 2 run (aim for 100-110 BPM)",
  "workout_type": "run",              // ✅ Clean, structured
  "duration_minutes": 35,             // ✅ Clean, structured
  "intensity_zone": "zone_2",         // ✅ Clean, structured
  "heart_rate_range": "100-110",      // ✅ Clean, structured
  "nutrition_fueling": "Eat a light snack 30 minutes before",
  "recovery_protocol": "10 minutes of stretching after, focus on calves and quads",
  "reasoning": "Building on successful Zone 1 sessions...",
  "status": "pending"
}
```

---

## Files Changed

1. **[app/agent_tools/create_plan_tool.py](app/agent_tools/create_plan_tool.py)**
   - Added structured parameters: `workout_type`, `duration_minutes`, `intensity_zone`, `heart_rate_range`
   - Removed regex extraction function `_extract_workout_details`
   - Updated tool description

2. **[app/agent_tools/update_plan_tool.py](app/agent_tools/update_plan_tool.py)**
   - Added structured parameters for updates
   - Removed regex extraction function
   - Updated tool description

3. **[app/agent_tools/previous_plans_tool.py](app/agent_tools/previous_plans_tool.py)**
   - Improved tool description to be more action-oriented

4. **[app/agent_tools/workout_details_tool.py](app/agent_tools/workout_details_tool.py)**
   - Improved tool description

5. **[app/agent_tools/user_profile_tool.py](app/agent_tools/user_profile_tool.py)**
   - Improved tool description

6. **[app/agent_tools/health_data_tool.py](app/agent_tools/health_data_tool.py)**
   - Improved tool description

7. **[app/agent_tools/vo2_trends_tool.py](app/agent_tools/vo2_trends_tool.py)**
   - Improved tool description

8. **[app/services/ai_coaching_agent.py](app/services/ai_coaching_agent.py)**
   - Completely rewritten system prompt
   - Removed hardcoded tool names
   - Focus on coaching principles and philosophy
   - Emphasizes conversation before prescription
   - Weekly planning awareness

9. **[COACHING_AGENT_EXPLANATION.md](COACHING_AGENT_EXPLANATION.md)** (New)
   - Comprehensive documentation of system design
   - Examples and best practices
   - Testing guidelines

---

## Testing Recommendations

### Test Case 1: Agent Provides Structured Data
```
User: "What's my workout today?"
Expected: Agent should call create_coaching_plan with all structured parameters filled
```

### Test Case 2: Conversation Before Prescription
```
User: "What's my workout today?"
Expected: Agent should ask about yesterday's workout before creating today's plan
```

### Test Case 3: Weekly Awareness
```
User: "What's my workout today?"
Context: User has done 5 hard workouts in 6 days
Expected: Agent should recommend rest/easy day based on weekly load
```

### Test Case 4: Update with Structured Data
```
User: "I need to change today's workout to 20 minutes instead of 30"
Expected: Agent should call update_coaching_plan with duration_minutes=20
```

---

## Migration Notes

**No database migration needed** - the database schema already supports these fields (`workout_type`, `duration_minutes`, `intensity_zone`, `heart_rate_range`). We're just changing how we populate them.

**Backward compatibility** - Old plans with regex-extracted data will continue to work. New plans will have cleaner, agent-provided data.

---

## Next Steps

1. **Test the agent** with various scenarios to ensure it provides structured parameters correctly
2. **Monitor tool calls** to verify the agent is using tools appropriately based on context
3. **Gather feedback** on conversation quality and plan recommendations
4. **Iterate** on system prompt if agent needs additional guidance

---

## Questions?

Refer to [COACHING_AGENT_EXPLANATION.md](COACHING_AGENT_EXPLANATION.md) for detailed system design and philosophy.
