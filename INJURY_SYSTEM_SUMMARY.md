# Injury Tracking System - Implementation Summary

## ✅ What's Been Created

I've designed a comprehensive injury tracking system for your AI coaching agent. Here's what's ready:

---

## 📋 Complete Plan

**[INJURY_TRACKING_PLAN.md](INJURY_TRACKING_PLAN.md)** contains the full design including:

### 1. **Database Schema**
- `user_injuries` table - Main injury tracking
- `injury_updates` table - Timeline of recovery progress

### 2. **Five Agent Tools**
All designed with Pydantic schemas following best practices:

1. **report_injury** - Document new injuries/pain
2. **update_injury_status** - Track recovery progress
3. **get_active_injuries** - Check current injuries before workouts
4. **get_injury_history** - Analyze patterns over time
5. **analyze_injury_risk** - Proactive injury prevention

### 3. **System Prompt Updates**
Complete injury awareness section teaching the agent to:
- Always check for injuries before creating plans
- Ask questions when users report pain
- Monitor recovery progress
- Prevent re-injury
- Provide injury-adapted training

---

## 🗄️ Database Models Created

### ✅ `UserInjury` Model
**File:** [app/models/user_injury.py](app/models/user_injury.py)

**Key Features:**
```python
class UserInjury(Base):
    # Injury Details
    injury_type: str        # "shin_splints", "runners_knee"
    affected_area: str      # "left_knee", "right_ankle"
    severity_level: str     # "mild", "moderate", "severe"

    # Pain Tracking (1-10 scale)
    initial_pain_level: int
    current_pain_level: int

    # Timeline
    injury_date: datetime
    expected_recovery_date: datetime
    actual_recovery_date: datetime

    # Status
    status: str  # "active", "recovering", "recovered", "chronic"

    # Activity Restrictions
    activity_restrictions: JSON  # {"no_running": true, "max_distance": 2}

    # Relationships
    updates: relationship -> InjuryUpdate[]
```

---

### ✅ `InjuryUpdate` Model
**File:** [app/models/injury_update.py](app/models/injury_update.py)

**Key Features:**
```python
class InjuryUpdate(Base):
    injury_id: str
    update_date: datetime
    pain_level: int  # 1-10 scale at time of update
    improvement_level: str  # "improving", "same", "worse"
    notes: str  # Progress notes
    activities_performed: JSON  # What they did
    pain_triggers: JSON  # What caused pain
```

---

## 🎯 How It Works

### Example 1: User Reports Knee Pain

```
User: "My left knee hurts when I run"

Agent Process:
1. Ask clarifying questions (pain level, when it started)
2. Use report_injury tool:
   {
     "injury_type": "runners_knee",
     "affected_area": "left_knee",
     "severity_level": "moderate",
     "pain_level": 6,
     "description": "Pain during runs, worse on downhill"
   }
3. Adjust workout → recommend cycling instead of running
4. Suggest treatment → ice, rest, PT
```

---

### Example 2: Check Injuries Before Workout

```
User: "What's my workout today?"

Agent Process:
1. Use get_active_injuries FIRST
2. See: shin_splints (recovering, pain level 3/10)
3. Ask: "How's your shin feeling today?"
4. Create appropriate plan:
   - If better → gentle 2-mile walk
   - If worse → complete rest or swimming
```

---

### Example 3: Track Recovery Progress

```
User: "My shin is feeling much better!"

Agent Process:
1. Use update_injury_status:
   {
     "injury_id": "cm4x...",
     "pain_level": 2,  # down from 6
     "improvement_level": "improving",
     "notes": "User reports significant improvement"
   }
2. Creates InjuryUpdate record in database
3. Updates current_pain_level on UserInjury
4. Gradually increases training intensity
```

---

### Example 4: Pattern Analysis

```
Agent uses get_injury_history:

Result: {
  "recurring_injuries": [
    {
      "injury_type": "runners_knee",
      "occurrences": 3,
      "common_trigger": "runs over 5 miles"
    }
  ]
}

Agent Recommendation:
"I notice your knees hurt after long runs. Let's:
- Cap long runs at 4 miles for now
- Add strength work 2x/week
- Gradually build distance tolerance"
```

---

## 🛠️ Implementation Checklist

### ✅ Completed
- [x] Design complete database schema
- [x] Create `UserInjury` model
- [x] Create `InjuryUpdate` model
- [x] Design all 5 agent tools with Pydantic schemas
- [x] Design system prompt updates
- [x] Document complete plan

### 🔄 Next Steps (To Implement)

#### 1. Database Migration
```bash
# Create Alembic migration
alembic revision --autogenerate -m "add_injury_tracking_tables"
alembic upgrade head
```

#### 2. Update User Model
Add relationship to [app/models/user.py](app/models/user.py):
```python
class User(Base):
    ...
    # Add this relationship
    injuries = relationship("UserInjury", back_populates="user")
```

#### 3. Create Agent Tools
Implement the 5 tools in `app/agent_tools/`:
- `report_injury_tool.py`
- `update_injury_tool.py`
- `get_active_injuries_tool.py`
- `get_injury_history_tool.py`
- `analyze_injury_risk_tool.py`

#### 4. Update System Prompt
Add injury awareness section to [app/services/ai_coaching_agent.py](app/services/ai_coaching_agent.py)

#### 5. Register Tools
Add injury tools to agent initialization

---

## 📊 Data Examples

### UserInjury Record
```json
{
  "id": "cm4xabc123",
  "user_id": "user_123",
  "injury_type": "shin_splints",
  "affected_area": "right_shin",
  "severity_level": "moderate",
  "initial_pain_level": 7,
  "current_pain_level": 3,
  "injury_date": "2025-11-10T00:00:00Z",
  "status": "recovering",
  "activity_restrictions": {
    "no_running": false,
    "max_distance_miles": 3,
    "avoid_hills": true
  },
  "treatment_plan": "Rest, ice 15min after activity, calf stretches"
}
```

### InjuryUpdate Record
```json
{
  "id": "cm4xupd456",
  "injury_id": "cm4xabc123",
  "update_date": "2025-11-15T00:00:00Z",
  "pain_level": 3,
  "improvement_level": "improving",
  "notes": "Pain reduced significantly, can walk without discomfort",
  "activities_performed": ["2-mile walk", "swimming"],
  "pain_triggers": []
}
```

---

## 🎓 Agent Behavior

### Always Check Injuries
```python
# Before EVERY workout plan creation:
injuries = get_active_injuries()

if injuries:
    # Adjust plan based on restrictions
    # Ask about pain levels
    # Provide modified workout
```

### Smart Questions
```
Agent asks when user reports pain:
- "Where exactly does it hurt?"
- "On a scale 1-10, how bad is the pain?"
- "When did you first notice it?"
- "Does it hurt during activity or after?"
- "Any swelling or stiffness?"
```

### Adaptive Training
```
Based on injury status:
- active (pain 7-10) → Complete rest or alternative exercise
- recovering (pain 3-6) → Modified training, reduced intensity
- chronic → Long-term adaptations, preventive work
- recovered → Gradual return to normal training
```

---

## 🔑 Key Features

### 1. **Complete History**
- Every injury tracked from onset to recovery
- Timeline of progress with pain levels
- Identify recurring issues

### 2. **Activity Restrictions**
```json
{
  "no_running": true,
  "max_distance_miles": 2,
  "avoid_hills": true,
  "max_heart_rate": 140
}
```

### 3. **Pattern Analysis**
- Recurring injury detection
- Common triggers identification
- Preventive recommendations

### 4. **Proactive Prevention**
- Training load monitoring
- Risk assessment based on history
- Early warning signs

---

## 💡 Benefits

### For Users
- ✅ Safer training adapted to injuries
- ✅ Systematic recovery tracking
- ✅ Injury patterns identified
- ✅ Prevents re-injury

### For Agent
- ✅ Complete injury context
- ✅ Historical pattern data
- ✅ Proactive prevention capability
- ✅ Better long-term athlete care

### For System
- ✅ Comprehensive injury analytics
- ✅ Evidence-based training adjustments
- ✅ User safety prioritized
- ✅ Improved outcomes

---

## 📚 Documentation

1. **[INJURY_TRACKING_PLAN.md](INJURY_TRACKING_PLAN.md)** - Complete design plan
2. **[app/models/user_injury.py](app/models/user_injury.py)** - UserInjury model
3. **[app/models/injury_update.py](app/models/injury_update.py)** - InjuryUpdate model
4. This summary document

---

## 🚀 Ready to Implement

All design work is complete. The system is fully planned and ready for implementation:

1. **Models**: ✅ Created
2. **Database Schema**: ✅ Designed
3. **Agent Tools**: ✅ Designed (need implementation)
4. **System Prompt**: ✅ Designed (need integration)
5. **Documentation**: ✅ Complete

Next step: Create the database migration and implement the agent tools!
