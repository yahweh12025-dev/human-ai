"""
Social Media Topic-Switch Module
Manages dynamic switching between social media content topics based on market conditions, 
trading signals, and predefined schedules
"""

import logging
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import time
from enum import Enum

logger = logging.getLogger(__name__)

class TopicCategory(Enum):
    """Categories of social media content topics"""
    MARKET_ANALYSIS = "market_analysis"
    TRADING_SIGNALS = "trading_signals"
    EDUCATIONAL = "educational"
    NEWS_COMMENTARY = "news_commentary"
    TECHNICAL_ANALYSIS = "technical_analysis"
    PORTFOLIO_UPDATES = "portfolio_updates"
    MOTIVATIONAL = "motivational"
    COMMUNITY_ENGAGEMENT = "community_engagement"

class TopicManager:
    """
    Manages dynamic topic switching for social media content
    Adjusts content focus based on market conditions, trading performance, and schedules
    """
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize Topic Manager
        
        Args:
            config_file: Path to topic configuration file
        """
        self.topics = self._load_default_topics()
        self.schedule = {}
        self.topic_weights = {category: 1.0 for category in TopicCategory}
        self.recent_topics = []  # Track recently used topics to avoid repetition
        self.max_recent_history = 5
        
        # Load custom configuration if provided
        if config_file:
            self.load_config(config_file)
        
        logger.info("TopicManager initialized")
    
    def _load_default_topics(self) -> Dict[TopicCategory, List[Dict[str, Any]]]:
        """Load default topic definitions"""
        return {
            TopicCategory.MARKET_ANALYSIS: [
                {
                    'id': 'ma_001',
                    'title': 'Daily Market Overview',
                    'templates': [
                        "📊 Market Update: {symbol} is trading at ${price} ({change_pct}%) with {volume} volume.",
                        "📈 Today's market highlights: {symbol} showing {trend} momentum.",
                        "💰 Market snapshot: {symbol} {action} {amount}% on {timeframe} chart."
                    ],
                    'priority': 'medium',
                    'frequency': 'daily'
                },
                {
                    'id': 'ma_002',
                    'title': 'Sector Performance',
                    'templates': [
                        "🔍 Sector Spotlight: {sector} up/down {change_pct}% today.",
                        "📊 {sector} leading/lagging the market with {performance}.",
                        "🎯 Sector rotation: Money flowing into {sector} as {reason}."
                    ],
                    'priority': 'medium',
                    'frequency': 'daily'
                }
            ],
            TopicCategory.TRADING_SIGNALS: [
                {
                    'id': 'ts_001',
                    'title': 'Signal Alert',
                    'templates': [
                        "🚨 {signal_type} Signal: {symbol} at ${price} - {reason}",
                        "💡 Trading Alert: {action} {symbol} based on {indicator}",
                        "⚡ {signal_strength} {signal_type} signal detected for {symbol}"
                    ],
                    'priority': 'high',
                    'frequency': 'realtime'
                },
                {
                    'id': 'ts_002',
                    'title': 'Signal Performance',
                    'templates': [
                        "📈 Signal Review: {win_rate}% win rate on {signal_type} signals this week.",
                        "📊 {signal_type} signals avg {avg_return}% return over {period}.",
                        "🎯 Best performing signal: {best_signal} with {return}% gain."
                    ],
                    'priority': 'low',
                    'frequency': 'weekly'
                }
            ],
            TopicCategory.EDUCATIONAL: [
                {
                    'id': 'ed_001',
                    'title': 'Trading Concepts',
                    'templates': [
                        "📚 Learn: What is {concept} and how traders use it?",
                        "💡 Quick Tip: {tip} for better {trading_aspect}.",
                        "🎓 Trading School: Understanding {topic} in {time_to_learn} minutes."
                    ],
                    'priority': 'medium',
                    'frequency': 'weekly'
                },
                {
                    'id': 'ed_002',
                    'title': 'Risk Management',
                    'templates': [
                        "� Risk Rule: Never risk more than {percent}% on a single trade.",
                        "🛡️ Protection: Using {technique} to limit downside risk.",
                        "⚖️ Balance: Risk/reward ratio of {ratio} is key to long-term success."
                    ],
                    'priority': 'high',
                    'frequency': 'weekly'
                }
            ],
            TopicCategory.NEWS_COMMENTARY: [
                {
                    'id': 'nc_001',
                    'title': 'Breaking News Reaction',
                    'templates': [
                        "📰 Breaking: {news_headline} - Impact on {symbol}: {impact}",
                        "🗞️ News Flash: {event} causing {effect} in {market}.",
                        "💭 Market Reaction: How traders are responding to {news}."
                    ],
                    'priority': 'high',
                    'frequency': 'realtime'
                },
                {
                    'id': 'nc_002',
                    'title': 'Weekly Recap',
                    'templates': [
                        "📰 This Week in Crypto: Top stories were {story1}, {story2}, {story3}.",
                        "📊 Biggest movers: {gainer} up {gain}%, {loser} down {loss}%.",
                        "🔮 Looking ahead: Watch for {event} next week."
                    ],
                    'priority': 'medium',
                    'frequency': 'weekly'
                }
            ],
            TopicCategory.TECHNICAL_ANALYSIS: [
                {
                    'id': 'ta_001',
                    'title': 'Chart Patterns',
                    'templates': [
                        "📐 Pattern Watch: {symbol} forming {pattern} on {timeframe}.",
                        "📊 Technical View: {indicator} suggests {outcome} for {symbol}.",
                        "🎯 Chart Setup: {setup} developing, watch for {breakout_level}."
                    ],
                    'priority': 'medium',
                    'frequency': 'daily'
                },
                {
                    'id': 'ta_002',
                    'title': 'Indicator Analysis',
                    'templates': [
                        "📈 {indicator} at {value} for {symbol} - indicating {signal}.",
                        "📊 {indicator1} and {indicator2} showing {relationship}.",
                        "⚡ Momentum: {symbol} showing {strength} momentum on {timeframe}."
                    ],
                    'priority': 'medium',
                    'frequency': 'daily'
                }
            ],
            TopicCategory.PORTFOLIO_UPDATES: [
                {
                    'id': 'pu_001',
                    'title': 'Portfolio Performance',
                    'templates': [
                        "💼 Portfolio Update: {performance}% this week ({pnl} P&L).",
                        "📊 Holdings: {top_holding} ({percentage}%), {second_holding} ({percentage2}%).",
                        "🎯 Allocation: {allocation}% cash, {allocation2}% crypto, {allocation3}% stocks."
                    ],
                    'priority': 'medium',
                    'frequency': 'weekly'
                },
                {
                    'id': 'pu_002',
                    'title': 'Trade Journal',
                    'templates': [
                        "📝 Trade Review: {symbol} trade resulted in {outcome} ({pnl}%).",
                        "📊 Win Rate: {rate}% on {trade_type} trades this month.",
                        "🎯 Lesson Learned: {lesson} from recent trading activity."
                    ],
                    'priority': 'low',
                    'frequency': 'weekly'
                }
            ],
            TopicCategory.MOTIVATIONAL: [
                {
                    'id': 'mo_001',
                    'title': 'Mindset & Psychology',
                    'templates': [
                        "💪 Remember: {truth} about trading psychology.",
                        "🧠 Mindset Tip: {tip} for maintaining discipline.",
                        "⚖️ Balance: Trading is {percentage}% psychology, {percentage}% strategy."
                    ],
                    'priority': 'low',
                    'frequency': 'daily'
                },
                {
                    'id': 'mo_002',
                    'title': 'Quotes & Wisdom',
                    'templates': [
                        "💎 Quote: \"{quote}\" - {author}",
                        "🌟 Wisdom: {wisdom} from experienced traders.",
                        "📜 Proverb: {proverb} applies perfectly to today's market."
                    ],
                    'priority': 'low',
                    'frequency': 'daily'
                }
            ],
            TopicCategory.COMMUNITY_ENGAGEMENT: [
                {
                    'id': 'ce_001',
                    'title': 'Polls & Questions',
                    'templates': [
                        "📊 Community Poll: Do you think {symbol} will {direction} this week?",
                        "❓ Question: What's your {timeframe} outlook on {symbol}?",
                        "👥 Discussion: {topic} - What are your thoughts?"
                    ],
                    'priority': 'medium',
                    'frequency': 'daily'
                },
                {
                    'id': 'ce_002',
                    'title': 'User Generated Content',
                    'templates': [
                        "🙌 Shoutout: {username} shared great insight on {topic}.",
                        "🎨 Featured: Community chart analysis of {symbol} by {creator}.",
                        "💬 Community Saying: \"{saying}\" - captures today's sentiment well."
                    ],
                    'priority': 'low',
                    'frequency': 'weekly'
                }
            ]
        }
    
    def load_config(self, config_file: str):
        """
        Load topic configuration from file
        
        Args:
            config_file: Path to JSON configuration file
        """
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            # Update topics if provided
            if 'topics' in config:
                # Merge with existing topics
                for category_str, topic_list in config['topics'].items():
                    try:
                        category = TopicCategory(category_str)
                        if category in self.topics:
                            # Extend existing category
                            self.topics[category].extend(topic_list)
                        else:
                            # Add new category
                            self.topics[category] = topic_list
                    except ValueError:
                        logger.warning(f"Unknown topic category in config: {category_str}")
            
            # Update schedule if provided
            if 'schedule' in config:
                self.schedule = config['schedule']
            
            # Update topic weights if provided
            if 'topic_weights' in config:
                for category_str, weight in config['topic_weights'].items():
                    try:
                        category = TopicCategory(category_str)
                        self.topic_weights[category] = float(weight)
                    except ValueError:
                        logger.warning(f"Unknown topic category in weights: {category_str}")
            
            logger.info(f"Loaded topic configuration from {config_file}")
            
        except FileNotFoundError:
            logger.error(f"Configuration file not found: {config_file}")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in configuration file: {e}")
        except Exception as e:
            logger.error(f"Error loading topic configuration: {e}")
    
    def get_current_market_conditions(self) -> Dict[str, Any]:
        """
        Get current market conditions to inform topic selection
        In a real implementation, this would connect to market data sources
        
        Returns:
            Dictionary with current market condition indicators
        """
        # This would normally fetch real market data
        # For demonstration, we'll return simulated conditions
        import random
        
        # Simulate various market conditions
        volatility = random.choice(['low', 'medium', 'high'])
        trend = random.choice(['strong_up', 'moderate_up', 'neutral', 'moderate_down', 'strong_down'])
        volume = random.choice(['low', 'normal', 'high'])
        
        # Determine market regime
        if trend in ['strong_up', 'moderate_up'] and volume == 'high':
            regime = 'bullish_momentum'
        elif trend in ['strong_down', 'moderate_down'] and volume == 'high':
            regime = 'bearish_momentum'
        elif trend == 'neutral' and volume in ['low', 'normal']:
            regime = 'consolidation'
        elif volatility == 'high':
            regime = 'volatile'
        else:
            regime = 'normal'
        
        return {
            'volatility': volatility,
            'trend': trend,
            'volume': volume,
            'regime': regime,
            'timestamp': datetime.now().isoformat()
        }
    
    def calculate_topic_weights(self, market_conditions: Dict[str, Any], 
                              trading_performance: Optional[Dict[str, Any]] = None,
                              recent_signals: Optional[List[Dict[str, Any]]] = None) -> Dict[TopicCategory, float]:
        """
        Calculate dynamic weights for topic selection based on current conditions
        
        Args:
            market_conditions: Current market conditions from get_current_market_conditions
            trading_performance: Recent trading performance metrics
            recent_signals: Recent trading signals generated
            
        Returns:
            Dictionary mapping topic categories to weights
        """
        # Start with base weights
        weights = self.topic_weights.copy()
        
        volatility = market_conditions.get('volatility', 'medium')
        trend = market_conditions.get('trend', 'neutral')
        regime = market_conditions.get('regime', 'normal')
        
        # Adjust weights based on market regime
        if regime == 'bullish_momentum':
            # In bullish markets, emphasize signal sharing and educational content
            weights[TopicCategory.TRADING_SIGNALS] *= 1.5
            weights[TopicCategory.TECHNICAL_ANALYSIS] *= 1.3
            weights[TopicCategory.EDUCATIONAL] *= 1.2
            
        elif regime == 'bearish_momentum':
            # In bearish markets, focus on risk management and defensive content
            weights[TopicCategory.TRADING_SIGNALS] *= 1.3  # Still important for exit signals
            weights[TopicCategory.EDUCATIONAL] *= 1.4  # More education needed
            weights[TopicCategory.MOTIVATIONAL] *= 1.3  # Need to keep spirits up
            weights[TopicCategory.NEWS_COMMENTARY] *= 1.5  # News drives bearish moves
            
        elif regime == 'consolidation':
            # In ranging markets, focus on technical analysis and education
            weights[TopicCategory.TECHNICAL_ANALYSIS] *= 1.6
            weights[TopicCategory.EDUCATIONAL] *= 1.4
            weights[TopicCategory.COMMUNITY_ENGAGEMENT] *= 1.2  # Good time for discussion
            
        elif regime == 'volatile':
            # In volatile markets, focus on news and risk management
            weights[TopicCategory.NEWS_COMMENTARY] *= 1.8
            weights[TopicCategory.EDUCATIONAL] *= 1.5  # Risk management education
            weights[TopicCategory.MOTIVATIONAL] *= 1.2  # Emotional support
            
        # Adjust based on trading performance
        if trading_performance:
            win_rate = trading_performance.get('win_rate', 0.5)
            if win_rate > 0.6:
                # Performing well, can share more confident signals
                weights[TopicCategory.TRADING_SIGNALS] *= 1.2
                weights[TopicCategory.PORTFOLIO_UPDATES] *= 1.3  # Share success
            elif win_rate < 0.4:
                # Struggling, focus on education and improvement
                weights[TopicCategory.EDUCATIONAL] *= 1.6
                weights[TopicCategory.MOTIVATIONAL] *= 1.4
                weights[TopicCategory.PORTFOLIO_UPDATES] *= 0.7  # Less focus on current P&L
        
        # Adjust based on recent signals
        if recent_signals:
            signal_count = len(recent_signals)
            if signal_count > 5:
                # Lots of signals, maybe focus on education about what they mean
                weights[TopicCategory.TECHNICAL_ANALYSIS] *= 1.3
                weights[TopicCategory.EDUCATIONAL] *= 1.2
            elif signal_count == 0:
                # No signals, maybe market is unclear - focus on analysis
                weights[TopicCategory.MARKET_ANALYSIS] *= 1.4
                weights[TopicCategory.TECHNICAL_ANALYSIS] *= 1.3
        
        # Normalize weights to prevent extreme values
        max_weight = max(weights.values())
        min_weight = min(weights.values())
        if max_weight - min_weight > 0:
            # Apply normalization to keep weights in reasonable range
            for category in weights:
                # Keep weights between 0.3 and 3.0 times base weight
                base_weight = self.topic_weights[category]
                weights[category] = max(0.3 * base_weight, 
                                       min(3.0 * base_weight, weights[category]))
        
        return weights
    
    def select_topic(self, market_conditions: Optional[Dict[str, Any]] = None,
                   trading_performance: Optional[Dict[str, Any]] = None,
                   recent_signals: Optional[List[Dict[str, Any]]] = None,
                   preferred_category: Optional[TopicCategory] = None) -> Dict[str, Any]:
        """
        Select a topic for social media content based on current conditions
        
        Args:
            market_conditions: Current market conditions
            trading_performance: Recent trading performance
            recent_signals: Recent trading signals
            preferred_category: If specified, try to select from this category
            
        Returns:
            Selected topic dictionary with content ready for posting
        """
        # Get market conditions if not provided
        if market_conditions is None:
            market_conditions = self.get_current_market_conditions()
        
        # Calculate dynamic weights
        weights = self.calculate_topic_weights(market_conditions, trading_performance, recent_signals)
        
        # If preferred category is specified, boost its weight significantly
        if preferred_category:
            weights[preferred_category] *= 2.0
        
        # Flatten all topics with their weights and categories
        weighted_topics = []
        for category, topic_list in self.topics.items():
            category_weight = weights.get(category, 1.0)
            for topic in topic_list:
                # Create a copy to avoid modifying the original
                topic_copy = topic.copy()
                topic_copy['category'] = category
                topic_copy['effective_weight'] = category_weight * topic.get('priority_weight', 1.0)
                weighted_topics.append(topic_copy)
        
        # Filter out recently used topics to avoid repetition
        if self.recent_topics:
            recent_ids = [t.get('id') for t in self.recent_topics if t.get('id')]
            weighted_topics = [t for t in weighted_topics if t.get('id') not in recent_ids]
            
            # If we filtered out everything, fall back to allowing repeats
            if not weighted_topics:
                logger.warning("All topics filtered due to recent history, allowing repeats")
                weighted_topics = []
                for category, topic_list in self.topics.items():
                    category_weight = weights.get(category, 1.0)
                    for topic in topic_list:
                        topic_copy = topic.copy()
                        topic_copy['category'] = category
                        topic_copy['effective_weight'] = category_weight * topic.get('priority_weight', 1.0)
                        weighted_topics.append(topic_copy)
        
        # If still no topics (shouldn't happen), return a default
        if not weighted_topics:
            logger.error("No topics available, returning default")
            return {
                'id': 'default',
                'title': 'Market Update',
                'content': '📊 Stay tuned for market updates.',
                'category': TopicCategory.MARKET_ANALYSIS,
                'priority': 'medium'
            }
        
        # Weighted random selection
        import random
        total_weight = sum(topic['effective_weight'] for topic in weighted_topics)
        if total_weight <= 0:
            # Fallback to uniform selection
            selected_topic = random.choice(weighted_topics)
        else:
            # Perform weighted selection
            r = random.uniform(0, total_weight)
            current_weight = 0
            selected_topic = None
            
            for topic in weighted_topics:
                current_weight += topic['effective_weight']
                if current_weight >= r:
                    selected_topic = topic
                    break
            
            # Fallback in case of rounding errors
            if selected_topic is None:
                selected_topic = weighted_topics[-1]
        
        # Add to recent topics history
        topic_entry = {
            'id': selected_topic.get('id'),
            'title': selected_topic.get('title'),
            'category': selected_topic.get('category'),
            'timestamp': datetime.now().isoformat()
        }
        self.recent_topics.append(topic_entry)
        
        # Keep recent history at maximum length
        if len(self.recent_topics) > self.max_recent_history:
            self.recent_topics.pop(0)
        
        # Generate actual content from templates
        content = self._generate_content_from_topic(selected_topic, market_conditions)
        selected_topic['content'] = content
        selected_topic['market_conditions'] = market_conditions
        selected_topic['selection_time'] = datetime.now().isoformat()
        
        logger.info(f"Selected topic: {selected_topic.get('title')} "
                   f"(Category: {selected_topic.get('category').value if hasattr(selected_topic.get('category'), 'value') else selected_topic.get('category')})")
        
        return selected_topic
    
    def _generate_content_from_topic(self, topic: Dict[str, Any], 
                                   market_conditions: Dict[str, Any]) -> str:
        """
        Generate actual content string from topic template and market data
        
        Args:
            topic: Topic dictionary with templates
            market_conditions: Current market conditions
            
        Returns:
            Generated content string ready for posting
        """
        templates = topic.get('templates', [])
        if not templates:
            return f"Topic: {topic.get('title', 'Unknown')}"
        
        # Select a random template
        import random
        template = random.choice(templates)
        
        # Prepare template variables
        # In a real implementation, these would come from actual market data, signals, etc.
        template_vars = {
            'symbol': 'BTC',
            'price': '$67,420',
            'change_pct': '+2.3%',
            'volume': '1.2B',
            'trend': 'bullish',
            'action': 'gained',
            'amount': '1.8',
            'timeframe': '4H',
            'sector': 'DeFi',
            'performance': 'outperforming',
            'reason': 'increased institutional adoption',
            'signal_type': 'BUY',
            'signal_strength': 'Strong',
            'action': 'BUY',
            'indicator': 'RSI divergence',
            'win_rate': '68',
            'avg_return': '15.5%',
            'period': '30 days',
            'best_signal': 'MACD crossover',
            'return': '22.4%',
            'concept': 'moving averages',
            'tip': 'use multiple time frame analysis',
            'topic': 'support and resistance',
            'time_to_learn': '10',
            'technique': 'stop-loss orders',
            'percent': '2',
            'ratio': '1:2',
            'news_headline': 'Major bank announces crypto custody services',
            'impact': 'positive long-term',
            'event': 'Fed interest rate decision',
            'effect': 'increased volatility',
            'story1': 'Bitcoin ETF approval',
            'story2': 'Ethereum upgrade success',
            'story3': 'Regulatory clarity in major markets',
            'gainer': 'SOL',
            'gain': '15.2%',
            'loser': 'DOGE',
            'loss': '8.7%',
            'event': 'Bitcoin halving',
            'top_holding': 'Bitcoin',
            'percentage': '45',
            'second_holding': 'Ethereum',
            'percentage2': '30',
            'allocation': '20',
            'allocation2': '60',
            'allocation3': '20',
            'pnl': '+12.4%',
            'performance': '+12.4%',
            'outcome': 'profitable',
            'rate': '65',
            'trade_type': 'swing',
            'lesson': 'patience pays off in trending markets',
            'truth': 'emotions are your worst enemy in trading',
            'tip': 'stick to your plan regardless of short-term results',
            'percentage': '80',
            'percentage2': '20',
            'quote': 'The trend is your friend until it ends',
            'author': 'Ed Seykota',
            'wisdom': 'Cut your losses short and let your profits run',
            'proverb': 'Plan the trade and trade the plan',
            'username': 'CryptoAnalystPro',
            'topic': 'chart pattern recognition',
            'creator': 'ChartMaster69',
            'saying': 'Buy the rumor, sell the news',
            'direction': 'go up',
            'timeframe': 'week',
            'topic': 'risk management strategies'
        }
        
        # Add market condition specific variables
        template_vars.update({
            'volatility': market_conditions.get('volatility', 'medium'),
            'trend': market_conditions.get('trend', 'neutral'),
            'regime': market_conditions.get('regime', 'normal'),
            'volume': market_conditions.get('volume', 'normal')
        })
        
        # Replace template variables
        try:
            content = template.format(**template_vars)
        except KeyError as e:
            # If a variable is missing, provide a default and log warning
            logger.warning(f"Missing template variable: {e}")
            # Provide a simple fallback
            content = f"{topic.get('title', 'Update')}: Market conditions are {market_conditions.get('regime', 'normal')}."
        
        return content
    
    def get_content_calendar(self, days_ahead: int = 7) -> List[Dict[str, Any]]:
        """
        Generate a content calendar for the specified number of days ahead
        
        Args:
            days_ahead: Number of days to generate content for
            
        Returns:
            List of scheduled content items
        """
        calendar = []
        start_date = datetime.now()
        
        for day_offset in range(days_ahead):
            current_date = start_date + timedelta(days=day_offset)
            date_str = current_date.strftime('%Y-%m-%d')
            
            # Determine how many posts for this day based on schedule
            day_of_week = current_date.weekday()  # 0 = Monday, 6 = Sunday
            
            # Default posting frequency
            posts_per_day = 3
            
            # Adjust based on day of week (example schedule)
            if day_of_week in [5, 6]:  # Weekend
                posts_per_day = 2  # Fewer posts on weekends
            elif day_of_week == 0:  # Monday
                posts_per_day = 4  # More posts to start the week
            
            # Generate topics for each post
            for post_num in range(posts_per_day):
                # Vary market conditions slightly for variety
                market_conditions = self.get_current_market_conditions()
                
                # Add some time-based variation
                hour_offset = post_num * (24 // max(posts_per_day, 1))
                scheduled_time = current_date.replace(
                    hour=min(hour_offset, 23),
                    minute=0,
                    second=0,
                    microsecond=0
                )
                
                # Skip if time is in the past (for today)
                if day_offset == 0 and scheduled_time < datetime.now():
                    continue
                
                topic = self.select_topic(market_conditions=market_conditions)
                
                calendar_item = {
                    'date': date_str,
                    'scheduled_time': scheduled_time.isoformat(),
                    'topic_id': topic.get('id'),
                    'topic_title': topic.get('title'),
                    'content': topic.get('content'),
                    'category': topic.get('category').value if hasattr(topic.get('category'), 'value') else topic.get('category'),
                    'priority': topic.get('priority'),
                    'market_conditions': topic.get('market_conditions')
                }
                
                calendar.append(calendar_item)
        
        # Sort by scheduled time
        calendar.sort(key=lambda x: x['scheduled_time'])
        
        logger.info(f"Generated content calendar with {len(calendar)} items for {days_ahead} days")
        return calendar

# Example usage
if __name__ == "__main__":
    # Initialize topic manager
    topic_manager = TopicManager()
    
    # Get current market conditions
    market_conditions = topic_manager.get_current_market_conditions()
    print(f"Current Market Conditions: {market_conditions}")
    
    # Select a topic based on current conditions
    selected_topic = topic_manager.select_topic(market_conditions=market_conditions)
    print(f"\nSelected Topic:")
    print(f"  ID: {selected_topic.get('id')}")
    print(f"  Title: {selected_topic.get('title')}")
    print(f"  Category: {selected_topic.get('category').value if hasattr(selected_topic.get('category'), 'value') else selected_topic.get('category')}")
    print(f"  Content: {selected_topic.get('content')}")
    
    # Generate a content calendar
    print(f"\nGenerating 3-day content calendar...")
    calendar = topic_manager.get_content_calendar(days_ahead=3)
    
    # Group by date for display
    from collections import defaultdict
    calendar_by_date = defaultdict(list)
    for item in calendar:
        calendar_by_date[item['date']].append(item)
    
    for date, items in sorted(calendar_by_date.items()):
        print(f"\n{date}:")
        for item in items:
            time_str = datetime.fromisoformat(item['scheduled_time']).strftime('%H:%M')
            print(f"  {time_str} - [{item['category']}] {item['topic_title']}")