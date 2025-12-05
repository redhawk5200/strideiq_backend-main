# Pydantic Schema Update for All Tools

## What Changed

All coaching agent tools now use **Pydantic models** for input validation following LangChain best practices.

---

## Benefits of Pydantic Schemas

### ✅ **1. Clear Type Validation**
- Automatic validation of input types
- Range constraints (e.g., `gt=0`, `le=90`)
- Literal types for enums (e.g., `Literal["run", "walk", "cycling"]`)

### ✅ **2. Better Documentation**
- Each field has a clear description
- Agent understands exactly what each parameter means
- Auto-generated OpenAPI-style schemas

### ✅ **3. Default Values**
- Explicit default values in one place
- Clear what's required vs optional

### ✅ **4. Validation Rules**
- `gt=0`: Greater than 0
- `le=90`: Less than or equal to 90
- Prevents invalid inputs automatically

---

## Tool-by-Tool Changes

### 1. **create_coaching_plan**

**Pydantic Schema:**
```python
class CreatePlanInput(BaseModel):
    """Input schema for creating a coaching plan."""
    todays_training: str = Field(
        description="Detailed workout description for the user to read"
    )
    workout_type: Literal["run", "walk", "cycling", "rest", "interval"] = Field(
        description="Type of workout activity"
    )
    duration_minutes: int = Field(
        description="Workout duration in minutes",
        gt=0
    )
    intensity_zone: Optional[str] = Field(
        default=None,
        description="Training intensity zone like 'zone_1', 'zone_2', 'zone_3', 'zone_4', 'zone_5'"
    )
    heart_rate_range: Optional[str] = Field(
        default=None,
        description="Target heart rate range like '80-90' or '100-110' BPM"
    )
    nutrition_fueling: Optional[str] = Field(
        default=None,
        description="Nutrition recommendations and fueling guidance"
    )
    recovery_protocol: Optional[str] = Field(
        default=None,
        description="Recovery guidelines including stretching, rest, sleep"
    )
    reasoning: Optional[str] = Field(
        default=None,
        description="Explanation of why this plan was prescribed based on user data and feedback"
    )
```

**Key Features:**
- `workout_type` is **Literal** - only accepts specific values
- `duration_minutes` must be **greater than 0**
- Clear descriptions for each field guide the agent

---

### 2. **update_coaching_plan**

**Pydantic Schema:**
```python
class UpdatePlanInput(BaseModel):
    """Input schema for updating a coaching plan."""
    plan_id: str = Field(
        description="ID of the plan to update"
    )
    todays_training: Optional[str] = Field(
        default=None,
        description="Modified workout description for the user"
    )
    workout_type: Optional[Literal["run", "walk", "cycling", "rest", "interval"]] = Field(
        default=None,
        description="Type of workout activity"
    )
    duration_minutes: Optional[int] = Field(
        default=None,
        description="Workout duration in minutes",
        gt=0
    )
    intensity_zone: Optional[str] = Field(
        default=None,
        description="Training intensity zone like 'zone_1', 'zone_2', etc."
    )
    heart_rate_range: Optional[str] = Field(
        default=None,
        description="Target heart rate range like '80-90' or '100-110' BPM"
    )
    nutrition_fueling: Optional[str] = Field(
        default=None,
        description="Updated nutrition recommendations"
    )
    recovery_protocol: Optional[str] = Field(
        default=None,
        description="Updated recovery guidelines"
    )
    reasoning: Optional[str] = Field(
        default=None,
        description="Updated explanation for the plan"
    )
    status: Optional[Literal["pending", "completed", "skipped", "partial"]] = Field(
        default=None,
        description="Completion status of the workout"
    )
```

**Key Features:**
- `status` is **Literal** - only valid statuses accepted
- All fields optional except `plan_id`

---

### 3. **get_previous_plans**

**Pydantic Schema:**
```python
class PreviousPlansInput(BaseModel):
    """Input schema for retrieving previous plans."""
    days: int = Field(
        default=7,
        description="How many days of training history to retrieve",
        gt=0,
        le=90
    )
```

**Key Features:**
- `days` must be between 1 and 90
- Default is 7 days

---

### 4. **get_workout_details**

**Pydantic Schema:**
```python
class WorkoutDetailsInput(BaseModel):
    """Input schema for retrieving workout details."""
    days_back: int = Field(
        default=7,
        description="How many days of workout history to retrieve",
        gt=0,
        le=90
    )
```

**Key Features:**
- `days_back` must be between 1 and 90
- Default is 7 days

---

### 5. **get_vo2_trends**

**Pydantic Schema:**
```python
class VO2TrendsInput(BaseModel):
    """Input schema for retrieving VO2 trends."""
    days_back: int = Field(
        default=90,
        description="How many days of VO2 history to analyze for trends",
        gt=0,
        le=365
    )
```

**Key Features:**
- `days_back` must be between 1 and 365 (1 year)
- Default is 90 days

---

### 6. **get_user_profile**

**Pydantic Schema:**
```python
class UserProfileInput(BaseModel):
    """Input schema for retrieving user profile (no parameters needed)."""
    pass
```

**Key Features:**
- No parameters needed
- Schema still defined for consistency

---

### 7. **get_user_health_data**

**Pydantic Schema:**
```python
class HealthDataInput(BaseModel):
    """Input schema for retrieving health data (no parameters needed)."""
    pass
```

**Key Features:**
- No parameters needed
- Schema still defined for consistency

---

## Usage Example

### Before (No Schema)
```python
@tool
async def create_coaching_plan(
    config: RunnableConfig,
    todays_training: str,
    workout_type: str,
    duration_minutes: int,
    # ... more params
) -> Dict:
    """Create a plan."""
    pass
```

**Problems:**
- No validation
- No clear documentation
- Agent might pass invalid values

---

### After (With Pydantic Schema)
```python
class CreatePlanInput(BaseModel):
    """Input schema for creating a coaching plan."""
    todays_training: str = Field(
        description="Detailed workout description for the user to read"
    )
    workout_type: Literal["run", "walk", "cycling", "rest", "interval"] = Field(
        description="Type of workout activity"
    )
    duration_minutes: int = Field(
        description="Workout duration in minutes",
        gt=0
    )

@tool(args_schema=CreatePlanInput)
async def create_coaching_plan(
    todays_training: str,
    workout_type: str,
    duration_minutes: int,
    config: RunnableConfig = None
) -> Dict:
    """Create and save a new daily training plan for the user."""
    pass
```

**Benefits:**
- ✅ Automatic validation
- ✅ Clear descriptions
- ✅ Type safety
- ✅ Constrained values

---

## How Agent Uses These Schemas

### Example: Agent Creates a Plan

**What Agent Sees (Schema):**
```json
{
  "name": "create_coaching_plan",
  "description": "Create and save a new daily training plan for the user...",
  "parameters": {
    "type": "object",
    "properties": {
      "todays_training": {
        "type": "string",
        "description": "Detailed workout description for the user to read"
      },
      "workout_type": {
        "type": "string",
        "enum": ["run", "walk", "cycling", "rest", "interval"],
        "description": "Type of workout activity"
      },
      "duration_minutes": {
        "type": "integer",
        "minimum": 1,
        "description": "Workout duration in minutes"
      }
    },
    "required": ["todays_training", "workout_type", "duration_minutes"]
  }
}
```

**Agent's Tool Call:**
```python
create_coaching_plan(
    todays_training="30-minute Zone 1 run",
    workout_type="run",              # ✅ Valid enum value
    duration_minutes=30,             # ✅ Greater than 0
    intensity_zone="zone_1",
    heart_rate_range="80-90"
)
```

**If Agent Tries Invalid Value:**
```python
create_coaching_plan(
    todays_training="30-minute swim",
    workout_type="swimming",         # ❌ Not in Literal options
    duration_minutes=-5,             # ❌ Not greater than 0
)
```
**Result:** Pydantic validation error - agent must fix and retry

---

## Validation Examples

### 1. Duration Must Be Positive
```python
duration_minutes: int = Field(
    description="Workout duration in minutes",
    gt=0  # Greater than 0
)
```

**Valid:** `30`, `45`, `60`
**Invalid:** `0`, `-10`, `-30`

---

### 2. Days Must Be In Range
```python
days: int = Field(
    default=7,
    description="How many days of training history to retrieve",
    gt=0,
    le=90  # Less than or equal to 90
)
```

**Valid:** `1`, `7`, `30`, `90`
**Invalid:** `0`, `-5`, `100`, `365`

---

### 3. Workout Type Must Be Valid
```python
workout_type: Literal["run", "walk", "cycling", "rest", "interval"] = Field(
    description="Type of workout activity"
)
```

**Valid:** `"run"`, `"walk"`, `"cycling"`, `"rest"`, `"interval"`
**Invalid:** `"swimming"`, `"yoga"`, `"strength"`

---

### 4. Status Must Be Valid
```python
status: Optional[Literal["pending", "completed", "skipped", "partial"]] = Field(
    default=None,
    description="Completion status of the workout"
)
```

**Valid:** `"pending"`, `"completed"`, `"skipped"`, `"partial"`, `None`
**Invalid:** `"done"`, `"finished"`, `"cancelled"`

---

## Migration Notes

**No breaking changes** - All existing functionality preserved. The schemas provide additional validation on top of existing code.

**Testing:** The agent will now receive better error messages if it tries to use invalid parameters, making debugging easier.

---

## Files Changed

1. ✅ [app/agent_tools/create_plan_tool.py](app/agent_tools/create_plan_tool.py)
2. ✅ [app/agent_tools/update_plan_tool.py](app/agent_tools/update_plan_tool.py)
3. ✅ [app/agent_tools/previous_plans_tool.py](app/agent_tools/previous_plans_tool.py)
4. ✅ [app/agent_tools/workout_details_tool.py](app/agent_tools/workout_details_tool.py)
5. ✅ [app/agent_tools/vo2_trends_tool.py](app/agent_tools/vo2_trends_tool.py)
6. ✅ [app/agent_tools/user_profile_tool.py](app/agent_tools/user_profile_tool.py)
7. ✅ [app/agent_tools/health_data_tool.py](app/agent_tools/health_data_tool.py)

---

## Summary

All tools now follow the **LangChain + Pydantic best practice** pattern:

```python
class ToolInput(BaseModel):
    """Input schema with clear descriptions."""
    param: Type = Field(description="...", constraints...)

@tool(args_schema=ToolInput)
async def tool_function(param: Type, config: RunnableConfig = None) -> Dict:
    """Tool description."""
    pass
```

This provides:
- ✅ Type safety
- ✅ Automatic validation
- ✅ Better agent guidance
- ✅ Clearer documentation
- ✅ Fewer errors
