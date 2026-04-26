ASTRAEUS
Autonomous Life Orchestrator

Individual Resource Planning (IRP) System

--------------------------------------------------

VISION

ASTRAEUS is a proactive artificial intelligence assistant designed to bridge the gap between a user’s physical context (location, weather, transportation) and personal goals.

Instead of reacting to commands, the system continuously evaluates context and proactively optimizes the user’s daily plan.

"You are Tarık’s Neural Life Architect. Your task is not only to answer questions, but to optimize Tarık’s life."

--------------------------------------------------

CORE TIME CALCULATION FORMULA

ASTRAEUS is built around a deterministic scheduling formula:

T_departure = T_event - (T_transport + T_walk + T_preparation + T_buffer)

This allows the system to:
- Calculate optimal departure times for each event
- Add dynamic buffer time based on weather conditions
- Account for public transportation schedules
- Re-plan the entire day when unexpected delays occur

--------------------------------------------------

FEATURES

AI Decision Engine
- Multi-LLM support: OpenAI GPT, Google Gemini, local Ollama models
- Proactive decision-making without explicit user prompts
- Context-aware reasoning using location, time, weather, and history
- Mentor-style communication with consistent tone and identity

Location and Transit Services
- GPS input via Telegram
- Reverse geocoding
- Nearest transit stop detection
- Route and duration estimation using OSRM or Google Maps

Weather Awareness
- Real-time weather data via OpenWeatherMap
- Forecast-based planning adjustments
- Automatic buffer increases:
  Rain: +20% walking duration
  Snow: +30% walking duration
  Extreme temperature warnings

Dynamic Scheduling
- Precise departure time calculation
- Conflict detection between events
- Full-day re-planning on delays
- Priority handling for non-skippable events

Telegram Bot Interface
- Natural language interaction (Turkish)
- One-tap location sharing
- Scheduled departure notifications
- Command-based quick access

--------------------------------------------------

TECHNOLOGY STACK

Language: Python 3.12+
Bot Framework: python-telegram-bot
AI / LLM: OpenAI, Google Generative AI, Ollama
Database: PostgreSQL with async SQLAlchemy
HTTP Client: httpx (async)
Maps and Location: geopy, OSRM, OSM Overpass API
Containerization: Docker, Docker Compose
Logging: structlog

--------------------------------------------------

PROJECT STRUCTURE

Astraeus-LifeOS/
|
|-- docker-compose.yml
|-- Dockerfile
|-- .env.example
|-- requirements.txt
|
|-- src/
|   |-- main.py
|   |-- config.py
|   |
|   |-- brain/
|   |   |-- llm_client.py
|   |   |-- system_prompt.py
|   |   |-- context_manager.py
|   |   |-- decision_engine.py
|   |
|   |-- location/
|   |   |-- gps_handler.py
|   |   |-- transit_finder.py
|   |   |-- maps_api.py
|   |
|   |-- scheduler/
|   |   |-- time_calculator.py
|   |   |-- dynamic_planner.py
|   |   |-- weather_adjuster.py
|   |
|   |-- integrations/
|   |   |-- telegram_bot.py
|   |   |-- weather_api.py
|   |
|   |-- database/
|       |-- models.py
|       |-- repository.py
|
|-- deploy/
|   |-- setup_vps.sh
|   |-- systemd/
|
|-- docs/

--------------------------------------------------

INSTALLATION

Requirements:
- Python 3.12 or higher
- Docker and Docker Compose
- Telegram Bot Token
- At least one LLM API key (OpenAI, Gemini, or local Ollama)

Quick Start with Docker:

git clone https://github.com/petrofi/astraeus-lifeos
cd astraeus
cp .env.example .env
docker compose up -d

Development Setup:

python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m src.main

--------------------------------------------------

EXAMPLE INTERACTION

User:
"Kafedeyim, bir saate kalkarım"

ASTRAEUS:
"Tarık, şu an kalkman gerekiyor. Hava yağmurlu olduğu için 502 numaralı otobüsü kaçırırsan bir sonraki dersine yetişemezsin.
Bugün Python’da ‘Class Structures’ konusuna odaklanacağız."

--------------------------------------------------

SECURITY

- Authorized user control
- API keys stored in environment variables
- Sensitive files excluded via .gitignore
- Non-root Docker execution
- Firewall-ready VPS setup

--------------------------------------------------

ROADMAP

- Voice message support (Whisper)
- Google Calendar synchronization
- Machine learning-based duration prediction
- Multi-user support
- Web dashboard

--------------------------------------------------

CONTRIBUTION

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push the branch
5. Open a Pull Request

--------------------------------------------------

LICENSE

MIT License. See the LICENSE file for details.

--------------------------------------------------

DEVELOPER

Darklove
AI Systems and Automation


⚠️ Testing Phase – Proje local ortamda test ediliyor. Şu anda çalışır durumdadır ancak gerçek zamanlı testler devam ediyor.


