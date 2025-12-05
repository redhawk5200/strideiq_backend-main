# AI Coaching Agent - System Design & Philosophy

## Overview

The AI Coaching Agent is designed to act as an **intelligent, context-aware running coach** that:
- Understands weekly training patterns, not just individual workouts
- Always gathers feedback before prescribing new plans
- Makes data-driven decisions using available tools
- Prevents overtraining and respects recovery needs
- Provides personalized, adaptive coaching based on real performance data

---

## Core Design Principles

### 1. **Agent-First Architecture** (No Hardcoded Workflows)

**What This Means:**
- The agent decides WHEN to use tools based on tool descriptions, not hardcoded instructions
- Tool descriptions are clear, action-oriented, and explain WHEN to use each tool
- The system prompt focuses on coaching philosophy, not specific tool names

**Why This Matters:**
- Agent can adapt to new situations intelligently
- More natural conversational flow
- Easier to add new tools without rewriting the entire prompt
- Agent learns to use the right tool at the right time

### 2. **Conversation-First Approach**

**The Flow:**
```
User: "What's my workout today?"

❌ BAD (Old Behavior):
Agent: "Here's your 30-minute run in Zone 1..."

✅ GOOD (New Behavior):
Agent: "Hey Mohammed! Before I recommend today's workout,
       let me ask - did you complete yesterday's plan?
       How did you feel during it?"

User: "Yes, but I felt really tired and my legs were sore"

Agent: [Uses tools to check]:
       - Recent training history (get_previous_plans)
       - Actual workout performance (get_workout_details)
       - Weekly load and compliance

Agent: "I see you've done 5 workouts this week with great
       intensity. Given your fatigue and soreness, let's do
       an easy 20-minute recovery walk today instead..."
```

**Key Points:**
- Always ask about previous workout completion and how it felt
- Check data to compare against previous performance
- Only prescribe after understanding the athlete's current state
- Update previous plan status based on feedback

### 3. **Weekly Planning Awareness**

**The Problem:**
Daily plans in isolation can lead to overtraining or inconsistent progression.

**The Solution:**
The agent considers:
- How many workouts were completed this week
- How many were skipped
- Training load distribution (hard days vs easy days)
- Recovery needs based on weekly volume
- Whether the user is progressing toward weekly/monthly goals

**Example:**
```
Week View:
Mon: 5K run ✅ completed
Tue: Intervals ✅ completed
Wed: Easy run ✅ completed
Thu: Rest ❌ skipped (did a hard run instead)
Fri: Long run ✅ completed
Sat: [Today - asking for plan]

Agent Analysis:
- 4 workouts completed (should be 3-4 per week)
- Skipped a rest day
- High cumulative load
- Decision: Prescribe mandatory recovery today
```

### 4. **Data-Driven Decisions**

The agent uses actual data from tools to make informed recommendations:

| Tool | Purpose | When Agent Uses It |
|------|---------|-------------------|
| `get_user_profile` | Understand goals, preferences, constraints | First conversation or when personalization is needed |
| `get_previous_plans` | See training history, compliance, check if today's plan exists | Before every plan creation |
| `get_workout_details` | Compare actual performance against past workouts | When analyzing progress or making comparisons |
| `get_vo2_trends` | Show fitness progression over time | When celebrating improvements or explaining decisions |
| `get_user_health_data` | Current VO₂, heart rate snapshot | When assessing readiness for training |
| `create_coaching_plan` | Save a new daily plan | Only after gathering feedback and confirming no plan exists |
| `update_coaching_plan` | Modify existing plan or update status | When user provides feedback on completed workout |

---

## Tool Design Philosophy

### Following LangChain Best Practices

Each tool description follows this pattern:
```python
@tool
async def tool_name(config: RunnableConfig, param: Type) -> Dict:
    """
    [One-line summary: What this tool does]

    [When to use it: Clear trigger conditions]

    Args:
        param: Description

    Returns:
        What data is returned
    """
```

**Example - Before (Confusing):**
```python
"""
Get user's previous coaching recommendations including today's plan if it exists.

IMPORTANT: This tool returns ALL plans including today's. Check the 'todays_plan' field
to see if a plan already exists for today BEFORE creating a new one.
"""
```

**Example - After (Clear & Action-Oriented):**
```python
"""
Retrieve the user's recent training history, compliance patterns, and check if today's plan already exists.

Use this when you need to understand what the user has been doing lately, how well they followed previous plans,
or before creating a new plan to avoid duplicates.
"""
```

**Benefits:**
- Agent immediately understands WHEN to use the tool
- No need to hardcode tool names in system prompt
- Tools become self-documenting
- Easy to add new tools

### Agent Provides Structured Data (No Regex Extraction)

**Key Design Decision:** The agent provides structured workout parameters directly instead of relying on regex extraction.

**Before (Regex Extraction):**
```python
@tool
async def create_coaching_plan(
    config: RunnableConfig,
    todays_training: str,  # Free-text description
    ...
) -> Dict:
    # Extract workout type, duration, zone from text using regex
    workout_details = _extract_workout_details(todays_training)
```

**After (Agent-Provided Structure):**
```python
@tool
async def create_coaching_plan(
    config: RunnableConfig,
    todays_training: str,
    workout_type: str,           # Agent provides explicitly
    duration_minutes: int,       # Agent provides explicitly
    intensity_zone: Optional[str] = None,
    heart_rate_range: Optional[str] = None,
    ...
) -> Dict:
    # Use agent-provided structured data directly
```

**Why This Is Better:**
- **Agent Intelligence**: The agent understands what it's prescribing, not just generating text
- **Accuracy**: No regex parsing failures or misinterpretations
- **Flexibility**: Agent can use any phrasing in `todays_training` for the user while still providing structured data
- **Data Quality**: Database gets clean, structured data every time
- **Easier Analytics**: No post-processing needed to analyze workout patterns

---

## System Prompt Philosophy

### What Changed

**Before:** Explicit tool names and forced workflow
```
2. Use data to make informed decisions:
   - get_user_profile → Understand goals, preferences, constraints.
   - get_previous_plans → See weekly structure and whether a plan for today already exists.
   - get_workout_details → Review recent sessions and compare performance.
```

**After:** Principle-based guidance that lets agent choose tools
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
- Reads more naturally
- Agent can reason about which tool to use when

---

## The Coaching Flow in Practice

### Example 1: User Asks for Today's Workout

```
User: "Hi coach, what's my workout for today?"

Agent's Internal Process:
1. ✅ Need to understand context first
2. 🔧 Use get_previous_plans to check history
3. 🔧 Use get_workout_details to see actual performance
4. 💬 Ask user about yesterday's workout feedback
5. ⏸️  Wait for response before creating plan

Agent Response:
"Hey Mohammed! Before I recommend today's workout, I want to check in:
- I see you had a 30-minute Zone 1 walk planned for yesterday. Did you complete it?
- How did you feel during and after the workout?
- Any soreness, fatigue, or concerns?"

User: "Yes, I did it. Felt good, no issues."

Agent's Internal Process:
6. ✅ Good compliance, no issues
7. 🔧 Check if today's plan exists (from get_previous_plans)
8. 🔧 Check weekly load and compliance rate
9. 🔧 Check VO₂ trends for progress
10. 🔧 Use create_coaching_plan to save today's plan

Agent Response:
"Excellent work! I see you've completed 3 out of 4 workouts this week with
75% compliance. Your VO₂ has improved by 2 points this month - great progress!

For today, let's do a **35-minute Zone 2 run** (aim for 100-110 BPM).
This builds on your successful Zone 1 sessions and starts to challenge
your aerobic base.

**Nutrition:** Eat a light snack 30 minutes before.
**Recovery:** 10 minutes of stretching after, focus on calves and quads.

Ready to go?"

Agent's Internal Tool Call:
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

### Example 2: User Shows Signs of Fatigue

```
User: "What's my workout today?"

Agent: [Uses tools to check history]

Agent: "Hey Mohammed! I see you had intervals planned yesterday.
       How did that session go for you?"

User: "I did it, but I was really struggling. My legs felt heavy
       and my heart rate was higher than usual for the same pace."

Agent's Internal Process:
🚨 RED FLAG: Performance declining + high HR + heavy legs
🔧 Use get_workout_details to compare yesterday vs previous intervals
🔧 Check weekly load (5 workouts in 6 days)
🔧 Check compliance (skipped rest day)
💡 DECISION: Prescribe recovery, not intensity

Agent Response:
"Thanks for that feedback - this is important information. Looking at
your data, I notice:

- You've done 5 workouts in the last 6 days (normally 3-4)
- Yesterday's heart rate was 8 BPM higher than your interval session
  from last week at the same pace
- You skipped a rest day mid-week

These are signs your body needs recovery. For today, let's do a
**complete rest day** or a very easy 15-minute walk if you feel
restless.

Recovery is when fitness actually builds. You've been training hard -
now let your body adapt. We'll resume with a light session tomorrow
if you're feeling better."
```

---

## Weekly Planning Logic

### The Algorithm (Conceptual)

```python
def should_prescribe_hard_workout(user):
    weekly_data = get_previous_plans(days=7)

    completed_workouts = count_completed(weekly_data)
    hard_workouts = count_hard_sessions(weekly_data)
    compliance_rate = calculate_compliance(weekly_data)

    # Check if user needs recovery
    if completed_workouts >= 4 and hard_workouts >= 2:
        return False  # Prescribe easy/rest

    # Check if user is under-training
    if completed_workouts < 2:
        return True  # Can handle harder session

    # Check recent performance
    recent_workouts = get_workout_details(days_back=7)
    performance_trend = analyze_hr_and_pace(recent_workouts)

    if performance_trend == "declining":
        return False  # Need recovery

    return True  # Can handle harder session
```

**The agent doesn't run this exact code**, but the system prompt guides it to think this way through:
- Principles about weekly balance
- Instructions to check compliance patterns
- Guidance on comparing performance data
- Emphasis on preventing overtraining

---

## Key Improvements Summary

### ✅ What We Fixed

1. **Tool Descriptions**: Now clear, action-oriented, and explain WHEN to use each tool
2. **System Prompt**: Removed hardcoded tool names; focuses on coaching philosophy and principles
3. **Conversation Flow**: Agent MUST gather feedback before prescribing workouts
4. **Weekly Awareness**: Agent considers weekly training load, not just daily plans
5. **Data Comparison**: Agent compares current performance against historical data
6. **Plan Management**: Agent checks if today's plan exists to avoid duplicates

### 🎯 Expected Behavior

**When user asks "What's my workout today?":**
1. Agent uses `get_previous_plans` to check history
2. Agent asks user about yesterday's workout and how they felt
3. Agent uses `get_workout_details` to compare actual performance
4. Agent uses `get_user_health_data` or `get_vo2_trends` if relevant
5. Agent creates plan ONLY after understanding context
6. Agent explains reasoning with specific data points
7. Agent uses `create_coaching_plan` to save the plan

**When user provides feedback:**
1. Agent uses `update_coaching_plan` to mark status (completed/skipped/partial)
2. Agent acknowledges feedback and adjusts future plans accordingly

---

## Testing the System

### Good Test Cases

**Test 1: First-time user asks for workout**
- ✅ Agent should ask about goals and preferences
- ✅ Agent should use `get_user_profile`
- ✅ Agent should start with conservative plan

**Test 2: User asks for workout after completing yesterday's plan**
- ✅ Agent should ask how yesterday felt
- ✅ Agent should compare performance to previous sessions
- ✅ Agent should acknowledge completion and progress

**Test 3: User shows signs of overtraining**
- ✅ Agent should detect high weekly volume
- ✅ Agent should notice performance decline
- ✅ Agent should prescribe recovery instead of intensity

**Test 4: User has inconsistent compliance**
- ✅ Agent should acknowledge skipped workouts without judgment
- ✅ Agent should adjust expectations
- ✅ Agent should prescribe achievable plan

---

## Future Enhancements

1. **Multi-week planning**: Track monthly and quarterly goals
2. **Injury prevention**: Use biomechanics data if available
3. **Race preparation**: Taper and peak for events
4. **Cross-training**: Incorporate strength, cycling, swimming
5. **Nutrition tracking**: More detailed fueling plans based on workouts

---

## Conclusion

The AI Coaching Agent is now designed to be:
- **Intelligent**: Uses tools based on context, not hardcoded rules
- **Conversational**: Always gathers feedback before prescribing
- **Adaptive**: Considers weekly patterns and individual progress
- **Data-driven**: Makes decisions based on actual performance metrics
- **Sustainable**: Prevents overtraining and respects recovery

The agent acts like a real coach who **listens, analyzes, and adapts** rather than just dispensing generic workouts.
