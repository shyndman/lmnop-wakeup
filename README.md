# lmnop:wakeup

**AI-Powered Morning Briefing System**

`lmnop:wakeup` is a sophisticated personal assistant that generates intelligent, personalized morning briefings with natural multi-character dialogue and professional audio production. Using advanced AI orchestration and agent-based architecture, it analyzes your calendar, weather conditions, and locations to create engaging daily briefings that integrate seamlessly with your smart home ecosystem.

```mermaid
graph TD
    subgraph "Main Workflow (workflow.py)"
        A[populate_raw_inputs] --> B{send_location_requests}
        B --> C[process_location]
        A --> D[fork_analysis]
        C --> D

        D --> E[calculate_schedule]
        D --> F[predict_sunset_beauty]
        D --> G{send_locations_to_analysis_tasks}
        G --> H[analyze_weather]

        E --> I[prioritize_events]
        F --> I
        H --> I

        I --> R1[review_prioritized_events]
        R1 --> J[write_content_optimization]
        J --> R2[review_content_optimization]
        R2 --> K[write_briefing_script]
        K --> R3[review_briefing_script]
        R3 --> L[consolidate_dialogue]
        L --> R4[review_final_script]
        R4 --> M[generate_tts]
        M --> N[schedule_automation_calendar_events]

        subgraph "Location Processing Subgraph"
            C1[resolve_location] --> C2[request_weather]
        end

        subgraph "TTS Subgraph (audio/workflow.py)"
            T1[generate_individual_tts] --> T2[master_tts_audio]
            T2 --> T3[add_audio_production]
        end

        M -.-> T1
        T3 -.-> M
    end
```

## Key Features

### 🧠 **Intelligent Briefing Generation**
- **AI-Powered Analysis**: Uses specialized AI agents for event prioritization, weather analysis, and content optimization
- **Location-Aware Planning**: Automatically resolves event locations and fetches location-specific weather forecasts
- **Smart Event Prioritization**: Determines which calendar events deserve attention based on importance, weather impact, and scheduling
- **Sunset Predictions**: Analyzes weather conditions to predict sunset beauty and outdoor activity recommendations

### 🎭 **Multi-Character Audio Production**
- **Natural Dialogue**: Generates conversations between distinct AI personalities with unique voice characteristics
- **Professional Audio**: Creates production-quality briefings with background music and audio effects
- **Script Optimization**: Intelligently consolidates dialogue to create engaging, natural-sounding conversations
- **TTS Integration**: Uses Google Gemini's advanced text-to-speech with character-specific voice mapping

### 🏠 **Smart Home Integration**
- **Music Assistant Integration**: Seamlessly announces briefings through your smart speaker ecosystem
- **Home Assistant Calendars**: Integrates with Home Assistant calendar entities alongside Google Calendar
- **Automated Scheduling**: Creates automation calendar events for optimal wake-up timing

### ⚡ **Advanced Workflow Orchestration**
- **LangGraph Architecture**: State-driven workflow with PostgreSQL checkpointing and workflow resumption
- **Parallel Processing**: Concurrent location resolution and weather analysis for efficiency
- **Multi-Tier Caching**: Redis and SQLite caching for expensive API operations
- **Interactive Mode**: Human-in-the-loop review steps for content approval and refinement


## Usage

### **Generate Daily Briefing**
```bash
# Generate complete briefing with audio
wakeup --briefing-date 2025-06-10 --current-location home

# Interactive mode with review steps
wakeup --briefing-date 2025-06-10 --current-location home --interactive

# Resume incomplete workflow
wakeup --briefing-date 2025-06-10 --thread-id 2025-06-10-123456
```
