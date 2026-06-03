# VAB Content Pipeline Specification
# Topic-Agnostic autonomous content generation for YouTube and TikTok.

## 1. Pipeline Flow
Input (Topic) -> Research (DeepSeek Headless) -> Scripting (Hermes) -> Visual Prompting (VAB-Visuals) -> Final Render (SiliconFlow/Local SD) -> Distribution (Postiz)

## 2. Topic-Agnostic Modules
- **Research Module**: Uses DeepSeek to find 3 viral hooks and 1 core value proposition for the given topic.
- **Scripting Module**: Converts research into a 60-second high-retention script.
- **Visual Module**: Generates image prompts based on the script's key scenes.

## 3. Production Tiers
- Tier 1 (Draft): Pollinations.ai for rapid concepting.
- Tier 2 (Production): SiliconFlow (Flux.1 [schnell]) for high-fidelity visuals.
- Tier 3 (Fallback): Local Stable Diffusion (CPU/Headless) for 100% uptime.

## 4. Postiz Integration
- Use Postiz API to queue posts with specific tags and schedules.
- Format: [Topic] | [Visual_ID] | [Caption] | [Schedule_Time]

## 5. Quality Control
- Automatic hook retention analysis
- Visual consistency checking
- Audio synchronization verification
- Platform-specific format adaptation (9:16 for TikTok/Shorts, 16:9 for YouTube)

## 6. Error Handling
- Retry mechanisms for API failures
- Fallback content generation when primary services unavailable
- Manual review queue for flagged content
