# ASTRAEUS - Autonomous Life Orchestrator
## System Architecture Documentation

This document provides detailed technical documentation of the ASTRAEUS system architecture.

## Table of Contents

1. [Overview](#overview)
2. [Module Descriptions](#module-descriptions)
3. [Data Flow](#data-flow)
4. [API Contracts](#api-contracts)
5. [Database Schema](#database-schema)

---

## Overview

ASTRAEUS is a proactive life optimization system built on four core principles:

1. **Proactive Intelligence**: Don't wait for user requests; anticipate needs
2. **Context Awareness**: Understand location, weather, time, and history
3. **Dynamic Adaptation**: Replan when conditions change
4. **Personalization**: Learn and adapt to user preferences

## Module Descriptions

### 1. Brain Module (`src/brain/`)

The AI decision-making core.

#### `llm_client.py`
- **Purpose**: Unified interface for multiple LLM providers
- **Supports**: OpenAI, Google Gemini, Ollama
- **Features**: Async generation, streaming support, error handling

#### `system_prompt.py`
- **Purpose**: Master system instructions for the AI
- **Features**: Dynamic context injection, role-specific prompts
- **Includes**: Event reminder templates, replanning templates

#### `context_manager.py`
- **Purpose**: Maintains conversation state and user context
- **Features**: Message history, location tracking, preference learning

#### `decision_engine.py`
- **Purpose**: Proactive decision-making logic
- **Features**: Departure time calculation, conflict detection, weather adjustments

### 2. Location Module (`src/location/`)

Geographic and transit services.

#### `gps_handler.py`
- **Purpose**: Coordinate processing and geocoding
- **Uses**: geopy with OpenStreetMap Nominatim
- **Features**: Caching, reverse geocoding, distance calculations

#### `transit_finder.py`
- **Purpose**: Find nearby public transit stops
- **Uses**: OSM Overpass API
- **Features**: Bus/metro/tram detection, walking time estimation

#### `maps_api.py`
- **Purpose**: Route calculation and travel times
- **Uses**: OSRM (free) or Google Maps
- **Features**: Multiple transport modes, step-by-step directions

### 3. Scheduler Module (`src/scheduler/`)

Time management and planning.

#### `time_calculator.py`
- **Purpose**: Implements the core departure time formula
- **Formula**: `T_kalkış = T_etkinlik - (T_ulaşım + T_yürüme + T_hazırlık + T_tampon)`
- **Features**: Weather-adjusted calculations, countdown formatting

#### `dynamic_planner.py`
- **Purpose**: Day planning and replanning
- **Features**: Event management, conflict detection, delay recovery

#### `weather_adjuster.py`
- **Purpose**: Weather-based time adjustments
- **Features**: Condition-specific buffers, recommendations, warnings

### 4. Integrations Module (`src/integrations/`)

External API connections.

#### `telegram_bot.py`
- **Purpose**: User interface via Telegram
- **Features**: Commands, location sharing, scheduled reminders, AI chat

#### `weather_api.py`
- **Purpose**: Weather data retrieval
- **Uses**: OpenWeatherMap API
- **Features**: Current weather, forecasts, alerts

### 5. Database Module (`src/database/`)

Data persistence layer.

#### `models.py`
- **Purpose**: SQLAlchemy ORM models
- **Tables**: User, Event, SavedLocation, Reminder, TravelLog

#### `repository.py`
- **Purpose**: Data access layer
- **Features**: Async CRUD operations, query helpers

---

## Data Flow

```
User Message (Telegram)
        │
        ▼
┌───────────────────┐
│  telegram_bot.py  │ ──► Authorization Check
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ context_manager   │ ──► Add to history, get context
└────────┬──────────┘
         │
         ├──────────────────┬─────────────────┐
         ▼                  ▼                 ▼
┌─────────────────┐ ┌─────────────────┐ ┌───────────┐
│  weather_api    │ │  gps_handler    │ │ database  │
│  (get weather)  │ │  (get location) │ │ (history) │
└────────┬────────┘ └────────┬────────┘ └─────┬─────┘
         │                   │                │
         └───────────────────┴────────────────┘
                             │
                             ▼
                  ┌───────────────────┐
                  │  system_prompt.py │ ──► Build dynamic prompt
                  └─────────┬─────────┘
                            │
                            ▼
                  ┌───────────────────┐
                  │   llm_client.py   │ ──► Generate response
                  └─────────┬─────────┘
                            │
                            ▼
                  ┌───────────────────┐
                  │ decision_engine   │ ──► Check for reminders
                  └─────────┬─────────┘
                            │
                            ▼
                   Send Response to User
```

---

## API Contracts

### Weather API Response

```python
@dataclass
class WeatherData:
    location: str
    temperature: float  # Celsius
    feels_like: float
    humidity: int  # %
    wind_speed: float  # m/s
    description: str
    main: str  # Weather category
    is_raining: bool
    is_snowing: bool
```

### Decision Engine Output

```python
@dataclass
class Decision:
    decision_type: DecisionType  # Enum
    urgency: Urgency  # LOW, MEDIUM, HIGH, CRITICAL
    title: str
    message: str
    action_required: bool
    deadline: Optional[datetime]
    metadata: Dict[str, Any]
```

### Time Calculation Result

```python
@dataclass
class TimeCalculation:
    event_time: datetime
    departure_time: datetime
    travel_duration: timedelta
    walking_duration: timedelta
    prep_time: timedelta
    buffer_time: timedelta
    total_duration: timedelta
```

---

## Database Schema

### Entity Relationship Diagram

```
┌─────────────────┐
│      User       │
├─────────────────┤
│ id (PK)         │
│ telegram_id     │
│ name            │
│ preferences...  │
└────────┬────────┘
         │
         │ 1:N
         │
         ├──────────────────┬──────────────────┐
         ▼                  ▼                  ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│     Event       │ │ SavedLocation   │ │    Reminder     │
├─────────────────┤ ├─────────────────┤ ├─────────────────┤
│ id (PK)         │ │ id (PK)         │ │ id (PK)         │
│ user_id (FK)    │ │ user_id (FK)    │ │ user_id (FK)    │
│ title           │ │ name            │ │ event_id (FK)   │
│ start_time      │ │ latitude        │ │ message         │
│ location...     │ │ longitude       │ │ trigger_time    │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

---

## Configuration

All configuration is managed through environment variables. See `.env.example` for the complete list.

### Required Variables

| Variable | Description |
|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Telegram Bot API token |
| `TELEGRAM_AUTHORIZED_USER_ID` | Your Telegram user ID |
| `AI_PROVIDER` | `openai`, `gemini`, or `ollama` |
| `DATABASE_URL` | PostgreSQL connection string |

### AI Provider Configuration

Choose one:

```bash
# OpenAI
AI_PROVIDER=openai
OPENAI_API_KEY=sk-...

# Gemini
AI_PROVIDER=gemini
GEMINI_API_KEY=...

# Ollama (local)
AI_PROVIDER=ollama
OLLAMA_HOST=http://localhost:11434
```

---

## Performance Considerations

1. **Caching**: Weather and geocoding results are cached
2. **Async**: All I/O operations are async
3. **Connection Pooling**: SQLAlchemy connection pool for database
4. **Rate Limiting**: Respect API rate limits (built into clients)

---

## Error Handling

All modules implement structured logging with `structlog`:

```python
logger.error("Operation failed", 
    error=str(e),
    user_id=user_id,
    operation="weather_fetch"
)
```

Graceful degradation:
- If weather fails → Continue without weather adjustment
- If LLM fails → Return error message to user
- If database fails → Log warning, continue in memory
