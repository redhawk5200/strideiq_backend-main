# Injury Tracking System - Design Plan

## Overview

A comprehensive injury tracking system that allows the AI coach to:
- Track injuries reported by users
- Monitor injury recovery progress over time
- Adjust training recommendations based on active injuries
- Prevent overtraining and re-injury
- Analyze injury patterns to prevent future issues

---

## Database Schema Design

### `user_injuries` Table

```sql
CREATE TABLE user_injuries (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL,

    -- Injury Details
    injury_type VARCHAR(100) NOT NULL,  -- e.g., "knee_pain", "shin_splints", "plantar_fasciitis"
    affected_area VARCHAR(100) NOT NULL,  -- e.g., "left_knee", "right_ankle", "lower_back"
    severity_level VARCHAR(20) NOT NULL,  -- "mild", "moderate", "severe"

    -- Pain and Recovery
    initial_pain_level INTEGER,  -- 1-10 scale
    current_pain_level INTEGER,  -- 1-10 scale (updated over time)

    -- Timeline
    injury_date TIMESTAMP NOT NULL,
    reported_date TIMESTAMP NOT NULL,
    expected_recovery_date TIMESTAMP,
    actual_recovery_date TIMESTAMP,

    -- Status
    status VARCHAR(20) NOT NULL,  -- "active", "recovering", "recovered", "chronic"

    -- Description and Notes
    description TEXT,
    symptoms TEXT,  -- JSON or text: pain during running, swelling, stiffness, etc.
    treatment_plan TEXT,  -- rest, ice, physical therapy, etc.

    -- Restrictions
    activity_restrictions JSON,  -- {"no_running": true, "max_distance_miles": 2, "avoid_hills": true}

    -- Tracking
    recovery_notes TEXT,  -- Coach's notes on progress
    last_update_date TIMESTAMP,

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    FOREIGN KEY (user_id) REFERENCES user_profiles(user_id) ON DELETE CASCADE
);

CREATE INDEX idx_user_injuries_user_id ON user_injuries(user_id);
CREATE INDEX idx_user_injuries_status ON user_injuries(status);
CREATE INDEX idx_user_injuries_injury_date ON user_injuries(injury_date DESC);
```

---

### `injury_updates` Table (History/Timeline)

Track progress over time with discrete updates:

```sql
CREATE TABLE injury_updates (
    id VARCHAR PRIMARY KEY,
    injury_id VARCHAR NOT NULL,
    user_id VARCHAR NOT NULL,

    -- Update Details
    update_date TIMESTAMP NOT NULL,
    pain_level INTEGER,  -- 1-10 scale at time of update
    status VARCHAR(20),  -- Status at time of update

    -- Progress Notes
    notes TEXT,  -- "Feeling better today", "Pain increased after run", etc.
    improvement_level VARCHAR(20),  -- "improving", "same", "worse"

    -- Activities Since Last Update
    activities_performed JSON,  -- What they did since last check-in
    pain_triggers JSON,  -- What caused pain

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),

    FOREIGN KEY (injury_id) REFERENCES user_injuries(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES user_profiles(user_id) ON DELETE CASCADE
);

CREATE INDEX idx_injury_updates_injury_id ON injury_updates(injury_id);
CREATE INDEX idx_injury_updates_date ON injury_updates(update_date DESC);
```

---

## Injury Types and Categories

### Common Running Injuries

```python
INJURY_TYPES = {
    # Knee Injuries
    "runners_knee": "Runner's Knee (Patellofemoral Pain)",
    "it_band_syndrome": "IT Band Syndrome",
    "patellar_tendonitis": "Patellar Tendonitis",

    # Shin and Calf
    "shin_splints": "Shin Splints",
    "calf_strain": "Calf Strain",
    "achilles_tendonitis": "Achilles Tendonitis",

    # Foot and Ankle
    "plantar_fasciitis": "Plantar Fasciitis",
    "ankle_sprain": "Ankle Sprain",
    "stress_fracture": "Stress Fracture",

    # Hip and Glutes
    "hip_flexor_strain": "Hip Flexor Strain",
    "piriformis_syndrome": "Piriformis Syndrome",

    # Back
    "lower_back_pain": "Lower Back Pain",

    # Other
    "muscle_soreness": "General Muscle Soreness",
    "other": "Other"
}

AFFECTED_AREAS = [
    "left_knee", "right_knee",
    "left_shin", "right_shin",
    "left_calf", "right_calf",
    "left_ankle", "right_ankle",
    "left_foot", "right_foot",
    "left_hip", "right_hip",
    "lower_back", "upper_back",
    "other"
]

SEVERITY_LEVELS = ["mild", "moderate", "severe"]

INJURY_STATUS = ["active", "recovering", "recovered", "chronic"]
```

---

## Agent Tools Design

### 1. **report_injury** Tool

**When to use:** User mentions pain, injury, or discomfort

```python
class ReportInjuryInput(BaseModel):
    """Input for reporting a new injury."""
    injury_type: str = Field(
        description="Type of injury (e.g., 'shin_splints', 'runners_knee', 'plantar_fasciitis')"
    )
    affected_area: str = Field(
        description="Body part affected (e.g., 'left_knee', 'right_ankle', 'lower_back')"
    )
    severity_level: Literal["mild", "moderate", "severe"] = Field(
        description="How severe the injury is"
    )
    pain_level: int = Field(
        description="Pain level on scale 1-10",
        ge=1,
        le=10
    )
    description: str = Field(
        description="Detailed description of the injury and symptoms"
    )
    injury_date: Optional[str] = Field(
        default=None,
        description="When the injury occurred (ISO date format). If not specified, uses today."
    )
    activity_restrictions: Optional[Dict] = Field(
        default=None,
        description="Activity restrictions like {'no_running': true, 'max_distance_miles': 2}"
    )

@tool(args_schema=ReportInjuryInput)
async def report_injury(...) -> Dict:
    """
    Report a new injury or pain that the user is experiencing.

    Use this when a user mentions pain, injury, discomfort, or any physical issue
    that might affect their training.
    """
```

---

### 2. **update_injury_status** Tool

**When to use:** User provides feedback on existing injury

```python
class UpdateInjuryInput(BaseModel):
    """Input for updating injury status."""
    injury_id: str = Field(
        description="ID of the injury to update"
    )
    pain_level: Optional[int] = Field(
        default=None,
        description="Current pain level on scale 1-10",
        ge=1,
        le=10
    )
    improvement_level: Optional[Literal["improving", "same", "worse"]] = Field(
        default=None,
        description="Whether the injury is getting better, staying the same, or getting worse"
    )
    status: Optional[Literal["active", "recovering", "recovered", "chronic"]] = Field(
        default=None,
        description="Current status of the injury"
    )
    notes: Optional[str] = Field(
        default=None,
        description="Update notes about how the injury feels"
    )

@tool(args_schema=UpdateInjuryInput)
async def update_injury_status(...) -> Dict:
    """
    Update the status and progress of an existing injury.

    Use this when a user provides feedback about how their injury is feeling,
    whether it's getting better or worse, or to mark it as recovered.
    """
```

---

### 3. **get_active_injuries** Tool

**When to use:** Before creating workout plans

```python
class GetActiveInjuriesInput(BaseModel):
    """Input for getting active injuries."""
    include_recovering: bool = Field(
        default=True,
        description="Whether to include injuries marked as 'recovering'"
    )

@tool(args_schema=GetActiveInjuriesInput)
async def get_active_injuries(include_recovering: bool = True, config: RunnableConfig = None) -> Dict:
    """
    Get all active and recovering injuries for the user.

    Use this BEFORE creating any workout plan to check if the user has any injuries
    that might affect training recommendations.

    Returns injury details, pain levels, affected areas, and activity restrictions.
    """
```

---

### 4. **get_injury_history** Tool

**When to use:** Analyzing patterns or long-term trends

```python
class InjuryHistoryInput(BaseModel):
    """Input for getting injury history."""
    days_back: int = Field(
        default=180,
        description="How many days of injury history to retrieve",
        gt=0,
        le=365
    )
    include_recovered: bool = Field(
        default=True,
        description="Whether to include recovered injuries"
    )

@tool(args_schema=InjuryHistoryInput)
async def get_injury_history(days_back: int = 180, include_recovered: bool = True, config: RunnableConfig = None) -> Dict:
    """
    Get user's injury history and patterns over time.

    Use this to identify recurring injuries, chronic issues, or patterns that might
    inform training adjustments (e.g., recurring knee pain suggests need for strength work).
    """
```

---

### 5. **analyze_injury_risk** Tool

**When to use:** Proactive injury prevention

```python
class AnalyzeInjuryRiskInput(BaseModel):
    """Input for analyzing injury risk."""
    pass

@tool(args_schema=AnalyzeInjuryRiskInput)
async def analyze_injury_risk(config: RunnableConfig = None) -> Dict:
    """
    Analyze the user's injury risk based on training load, injury history, and patterns.

    Use this to proactively identify when a user might be at risk for injury based on:
    - Recent training volume increases
    - Past injury patterns
    - Current recovery status
    - Weekly training load

    Returns risk level and recommendations for prevention.
    """
```

---

## System Prompt Updates

### New Section: Injury Awareness

```markdown
## Injury Management and Prevention

### 1. Always Check for Injuries
Before creating any workout plan:
- Use get_active_injuries to check for current injuries
- Consider pain levels, affected areas, and activity restrictions
- NEVER prescribe workouts that conflict with injury restrictions

### 2. When User Reports Pain
If a user mentions pain, discomfort, or injury:
- Ask detailed questions: Where? When did it start? Pain level?
- Use report_injury to document it
- Immediately adjust training recommendations
- Suggest appropriate rest or cross-training

### 3. Monitor Recovery Progress
When discussing injuries:
- Ask how the injury feels compared to last time
- Use update_injury_status to track progress
- Adjust training intensity based on recovery
- Celebrate improvements

### 4. Injury-Adapted Training
For users with active injuries:
- Prescribe alternative exercises that avoid the injured area
- Reduce intensity and volume appropriately
- Focus on activities that aid recovery
- Never push through pain

### 5. Prevent Re-Injury
- Use get_injury_history to check for recurring issues
- Gradually return to normal training after recovery
- Include preventive strength work for chronic issues
- Monitor for early warning signs

### 6. Proactive Prevention
- Use analyze_injury_risk when training load increases rapidly
- Recommend rest days when risk is high
- Include recovery and strength work proactively
```

---

## Agent Behavior Examples

### Example 1: User Reports Knee Pain

```
User: "My left knee has been hurting during runs"

Agent's Process:
1. ✅ Ask clarifying questions
2. ✅ Use report_injury to document
3. ✅ Use get_active_injuries to see full picture
4. ✅ Adjust today's workout plan

Agent: "I'm sorry to hear about your knee pain. Let me ask a few questions:
       - On a scale of 1-10, how bad is the pain?
       - When did you first notice it?
       - Does it hurt during the run or after?"

User: "It's about a 6/10, started 3 days ago, hurts during the run especially going downhill"

Agent: [Uses report_injury]:
       injury_type="runners_knee"
       affected_area="left_knee"
       severity_level="moderate"
       pain_level=6
       description="Pain during runs, worse on downhill"

Agent: "Thanks for letting me know. I've documented this as moderate runner's knee.

       For today, let's skip running and do a 30-minute bike ride or swim instead
       to maintain cardio without stressing your knee.

       Also recommend:
       - Ice after activity (15 minutes)
       - Consider seeing a physical therapist
       - We'll reassess in 2-3 days

       How does that sound?"
```

---

### Example 2: Checking Injury Before Workout

```
User: "What's my workout today?"

Agent's Process:
1. ✅ Use get_active_injuries FIRST
2. ✅ Check training history
3. ✅ Create appropriate plan

Agent: [Uses get_active_injuries]
Result: {
  "active_injuries": [
    {
      "injury_type": "shin_splints",
      "affected_area": "right_shin",
      "pain_level": 3,
      "status": "recovering",
      "restrictions": {"no_running": false, "max_distance_miles": 3}
    }
  ]
}

Agent: "Hey Mohammed! Before we plan today's workout, I see your shin splints
       are still recovering (pain level 3/10).

       How is your shin feeling today? Any pain when walking?"

User: "It's feeling better, just a little tender"

Agent: [Uses update_injury_status with improvement_level="improving"]

Agent: "Great to hear it's improving! Since your shin is still tender,
       let's do a gentle 2-mile walk today instead of running.
       This keeps you active while giving your shin more recovery time.

       We'll reassess in 2 days and potentially return to easy running."
```

---

### Example 3: Injury Pattern Analysis

```
User: "My knees keep hurting after long runs"

Agent: [Uses get_injury_history]
Result: {
  "total_injuries": 4,
  "recurring_patterns": [
    {
      "injury_type": "runners_knee",
      "occurrences": 3,
      "affected_area": "both_knees",
      "common_trigger": "runs over 5 miles"
    }
  ]
}

Agent: "I notice a pattern - you've had knee pain 3 times in the past 6 months,
       all after runs longer than 5 miles.

       This suggests we need to:
       1. Build up long run distance more gradually
       2. Add strength work for quads and hips
       3. Consider a gait analysis

       For now, let's cap long runs at 4 miles and add 2 strength sessions
       per week focusing on knee stability. Sound good?"
```

---

## Implementation Steps

### Phase 1: Database and Models
1. Create migration for `user_injuries` table
2. Create migration for `injury_updates` table
3. Create `UserInjury` SQLAlchemy model
4. Create `InjuryUpdate` SQLAlchemy model

### Phase 2: Agent Tools
1. Implement `report_injury` tool
2. Implement `update_injury_status` tool
3. Implement `get_active_injuries` tool
4. Implement `get_injury_history` tool
5. Implement `analyze_injury_risk` tool

### Phase 3: System Prompt
1. Update system prompt with injury awareness section
2. Add injury check to workout creation flow

### Phase 4: Testing
1. Test reporting injuries
2. Test injury status updates
3. Test workout adjustments based on injuries
4. Test injury pattern analysis

---

## Data Flow

```
User Reports Pain
       ↓
Agent asks clarifying questions
       ↓
report_injury tool creates record
       ↓
get_active_injuries shows all current issues
       ↓
Agent adjusts workout plan
       ↓
User provides feedback
       ↓
update_injury_status tracks progress
       ↓
Injury recovers
       ↓
get_injury_history analyzes patterns
```

---

## Benefits

### For Users
- ✅ Safer training adapted to injuries
- ✅ Systematic recovery tracking
- ✅ Pattern identification prevents re-injury
- ✅ Personalized rehabilitation guidance

### For Agent
- ✅ Complete injury context for decisions
- ✅ Historical data for pattern analysis
- ✅ Proactive injury prevention
- ✅ Better long-term athlete development

### For System
- ✅ Comprehensive injury data
- ✅ Analytics on common injury types
- ✅ Evidence-based training adjustments
- ✅ Improved user safety and outcomes

---

## Next Steps

1. Review this plan
2. Create database migrations
3. Implement models
4. Build agent tools
5. Update system prompt
6. Test with real scenarios
