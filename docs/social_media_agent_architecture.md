# Social Media Agent Architecture
**Date**: 2026-05-10  
**Version**: 1.0  
**Status**: Design Complete

## Overview

The Social Media Agent is an autonomous content creation and posting system for YouTube and TikTok. It integrates with the human-ai swarm to leverage research capabilities, LLM routing, and stealth browser automation.

## Architecture Components

### 1. Content Creation Pipeline

```
Research Agent → Content Planner → Script Generator → Media Processor → Metadata Generator
```

#### 1.1 Research & Topic Discovery
- **Input Sources**:
  - Trending topics from Twitter/X API
  - YouTube trending analysis
  - TikTok discover page scraping
  - Crypto news feeds (existing sentiment system)
  - Reddit /r/cryptocurrency, /r/wallstreetbets

- **Agent**: Researcher agent (existing)
- **Output**: Topic briefs with keywords, context, and engagement potential

#### 1.2 Content Planner
- **Function**: Determines content calendar and posting schedule
- **Integration**: `config/social_cron.yaml` for scheduling
- **Strategy**:
  - Balance evergreen vs trending content
  - Optimize posting times by platform
  - Content series planning
  - Cross-platform repurposing

- **Output**: Content plan with assigned topics and deadlines

#### 1.3 Script Generator
- **LLM Integration**: OpenRouter / DeepSeek for volume generation
- **Prompting Strategy**:
  - Platform-specific tone (YouTube: educational, TikTok: punchy)
  - Hook generation (first 3 seconds critical)
  - Story structure (problem → solution → CTA)
  - SEO keyword integration

- **Templates**:
  - Educational explainer
  - Market analysis
  - Trading strategy breakdown
  - "Day in the life" of trading bot
  - Swarm architecture showcase

- **Output**: Video script with timestamps, visual cues, B-roll suggestions

#### 1.4 Media Processor
- **Video Generation**:
  - Text-to-speech (Azure/ElevenLabs for narration)
  - Stock footage integration (Pexels API)
  - Screen recording (trading charts, code)
  - Animated overlays (statistics, callouts)
  - Subtitle generation (accessibility + engagement)

- **Audio**:
  - Background music (royalty-free library)
  - Sound effects for emphasis
  - Audio normalization

- **Tools**:
  - FFmpeg for video processing
  - OpenCV for frame manipulation
  - Pillow for thumbnail generation

- **Output**: Rendered video file (.mp4), thumbnail (.jpg)

#### 1.5 Metadata Generator
- **YouTube**:
  - Title optimization (50-60 chars, keyword-rich)
  - Description with timestamps and links
  - Tags (trending + niche)
  - Thumbnail text overlay
  - Playlist assignment

- **TikTok**:
  - Caption with hashtags (3-5 trending + niche)
  - Sound selection (trending audio)
  - Category tagging

- **SEO**: Keyword research via Google Trends, VidIQ integration

- **Output**: Metadata JSON for upload

### 2. Posting Automation

```
Content Queue → Upload Scheduler → Camoufox Browser → Platform Upload → Verification
```

#### 2.1 Content Queue Manager
- **Storage**: `data/social/content_queue.json`
- **Fields**:
  - content_id
  - platform (youtube, tiktok)
  - status (queued, uploading, published, failed)
  - scheduled_time
  - video_path
  - metadata
  - retry_count

- **Priority System**: Trending content prioritized

#### 2.2 Upload Scheduler
- **Cron Integration**: Reads from `config/social_cron.yaml`
- **Timezone Handling**: Converts to platform-optimal times
- **Rate Limiting**: Respects platform quotas (YouTube: 10/day, TikTok: varies)
- **Retry Logic**: Exponential backoff for failures

#### 2.3 Camoufox Stealth Browser
- **Anti-Detection**:
  - Randomized user agents
  - Canvas fingerprint randomization
  - WebGL noise injection
  - Timezone/locale matching
  - Human-like mouse movements

- **Session Management**:
  - Persistent cookies in `browser_profiles/social_media/`
  - 2FA handling (TOTP integration)
  - Login state verification

#### 2.4 Platform Upload Workflows

**YouTube**:
1. Navigate to youtube.com/upload
2. Upload video file
3. Fill metadata (title, description, tags)
4. Upload thumbnail
5. Set visibility (public/scheduled)
6. Add to playlist
7. Verify publication

**TikTok**:
1. Navigate to tiktok.com/upload
2. Upload video file
3. Add caption and hashtags
4. Set privacy (public)
5. Enable duet/stitch options
6. Schedule or publish
7. Verify publication

#### 2.5 Verification System
- **Post-Upload Checks**:
  - Video ID extraction
  - URL validation
  - Thumbnail verification
  - Metadata accuracy check
  - Engagement tracking setup

- **Error Handling**:
  - Copyright claims detection
  - Upload failures
  - Account restrictions
  - Video processing errors

### 3. Engagement Tracking

```
Published Content → Analytics API → Metrics Aggregation → Performance Analysis
```

#### 3.1 Metrics Collection
- **YouTube Data API v3**:
  - Views, likes, comments
  - Watch time, average view duration
  - Subscriber growth
  - Traffic sources

- **TikTok API** (unofficial/scraping):
  - Views, likes, shares, comments
  - Follower growth
  - For You Page appearances

#### 3.2 Performance Dashboard
- **Location**: `apps/dashboard/social_media_dashboard.py`
- **Metrics**:
  - Real-time view counts
  - Engagement rate trends
  - Best performing content
  - Growth projections
  - Revenue analytics (YouTube monetization)

#### 3.3 Feedback Loop
- **A/B Testing**:
  - Thumbnail variants
  - Title variations
  - Posting time experiments

- **Content Optimization**:
  - Analyze high-performing videos
  - Extract successful patterns
  - Refine script templates
  - Adjust content calendar

### 4. Swarm Integration

#### 4.1 Research Agent Integration
- **Task**: Topic discovery and script research
- **Input**: Research query from content planner
- **Output**: Comprehensive topic brief with sources

#### 4.2 OpenClaw Gateway
- **Commands**:
  - `/social create <topic>` - Generate new content
  - `/social schedule` - View content calendar
  - `/social publish <id>` - Force publish content
  - `/social analytics` - View performance report

#### 4.3 Knowledge Graph
- **Content Mapping**:
  - Link videos to trading strategies discussed
  - Connect to backtest results
  - Map to market events
  - Track content series relationships

#### 4.4 Memory System
- **Content Memory**:
  - Track successful topics/formats
  - Remember audience preferences
  - Store brand voice guidelines
  - Log content performance patterns

## Implementation Phases

### Phase 1: Core Pipeline (Week 1-2)
- [ ] Script generator with LLM integration
- [ ] Basic video rendering (text-to-speech + stock footage)
- [ ] Thumbnail generation
- [ ] Metadata template system

### Phase 2: Automation (Week 3-4)
- [ ] Camoufox upload workflow for YouTube
- [ ] Camoufox upload workflow for TikTok
- [ ] Content queue manager
- [ ] Scheduling system

### Phase 3: Analytics & Optimization (Week 5-6)
- [ ] YouTube API integration
- [ ] TikTok metrics scraping
- [ ] Performance dashboard
- [ ] A/B testing framework

### Phase 4: Swarm Integration (Week 7-8)
- [ ] OpenClaw command interface
- [ ] Research agent coordination
- [ ] Knowledge graph integration
- [ ] Autonomous content loop

## Technology Stack

### Content Generation
- **LLMs**: OpenRouter (GPT-4, Claude), DeepSeek
- **TTS**: Azure Speech, ElevenLabs
- **Video**: FFmpeg, OpenCV
- **Images**: Pillow, Stable Diffusion API (optional)

### Automation
- **Browser**: Camoufox (stealth automation)
- **Scheduling**: Python APScheduler + cron
- **Storage**: SQLite for content queue

### APIs
- **YouTube**: YouTube Data API v3
- **TikTok**: Unofficial API (pyktok) + scraping
- **Twitter**: Twitter API v2 (trends)
- **Stock Media**: Pexels API, Pixabay API

### Infrastructure
- **Orchestration**: Existing swarm infrastructure
- **Logging**: Centralized logging to `logs/social_media/`
- **Monitoring**: Integration with Mission Control dashboard

## Security & Compliance

### Account Safety
- **Rate Limiting**: Respect platform quotas
- **Human-like Behavior**: Randomized timing, mouse movements
- **Session Management**: Persistent authenticated sessions
- **IP Rotation**: Proxy support if needed

### Content Policy
- **Copyright**: Use only royalty-free media
- **Accuracy**: Fact-check trading advice
- **Disclaimers**: Include trading risk warnings
- **Transparency**: Disclose AI-generated content if required

### Data Privacy
- **Analytics**: Aggregate public metrics only
- **Cookies**: Stored securely in vault/
- **API Keys**: Environment variables, not committed

## Success Metrics

### Growth Targets (6 months)
- **YouTube**:
  - 1,000 subscribers (monetization threshold)
  - 100+ videos published
  - 4,000 watch hours

- **TikTok**:
  - 10,000 followers
  - 200+ videos published
  - 1M+ total views

### Engagement Targets
- YouTube: 5%+ engagement rate (likes/views)
- TikTok: 10%+ engagement rate
- Cross-platform traffic: 20% click-through to website

### Automation Targets
- 95%+ successful upload rate
- <1 hour average processing time per video
- 0 manual interventions per week

## Future Enhancements

### Advanced Features
- Live streaming automation
- Community post scheduling (YouTube)
- Shorts/Reels cross-posting
- Podcast audio repurposing
- Multi-language dubbing

### AI Enhancements
- Voice cloning for consistent narration
- AI avatar/presenter (D-ID, HeyGen)
- Real-time trend prediction
- Automatic thumbnail A/B testing

### Platform Expansion
- Instagram Reels
- Twitter/X video posts
- LinkedIn video articles
- Twitch clips

## File Structure

```
agents/social-media/
├── __init__.py
├── content_pipeline.py          # Core pipeline orchestration
├── script_generator.py          # LLM-based script creation
├── video_renderer.py            # FFmpeg video processing
├── thumbnail_generator.py       # Thumbnail creation
├── metadata_optimizer.py        # SEO optimization
├── upload_automation.py         # Browser automation
├── youtube_uploader.py          # YouTube-specific logic
├── tiktok_uploader.py           # TikTok-specific logic
├── analytics_collector.py       # Metrics gathering
├── content_queue_manager.py     # Queue management
└── scheduler.py                 # Cron integration

data/social/
├── content_queue.json           # Upload queue
├── published_content.json       # Historical log
├── analytics.json               # Metrics data
└── templates/                   # Script templates

config/
└── social_cron.yaml            # Scheduling config (existing)
```

## Conclusion

This architecture provides a comprehensive, autonomous social media content engine that integrates seamlessly with the existing human-ai swarm. The modular design allows for incremental implementation and easy extension to new platforms.

**Status**: Ready for implementation (Tasks #2, #3)
