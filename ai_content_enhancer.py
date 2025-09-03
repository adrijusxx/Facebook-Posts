"""
AI Content Enhancer using OpenAI to create engaging Facebook posts
"""

import openai
import logging
import re
from datetime import datetime
from models import db, Settings, PostingLog
import os
import tiktoken
import json

logger = logging.getLogger(__name__)

class AIContentEnhancer:
    """Uses OpenAI to enhance news content for engaging Facebook posts"""
    
    def __init__(self):
        self.client = None
        self.model = "gpt-3.5-turbo"
        self.max_tokens = 300
        self.encoding = tiktoken.encoding_for_model(self.model)
        
    def initialize_openai(self, api_key):
        """Initialize OpenAI client with API key"""
        try:
            openai.api_key = api_key
            self.client = openai.OpenAI(api_key=api_key)
            return True
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI: {e}")
            return False
    
    def enhance_post_content(self, title, original_content, url, source):
        """Enhance news content to create an engaging Facebook post"""
        if not self.client:
            settings = Settings.query.first()
            if not settings or not settings.openai_api_key:
                logger.warning("OpenAI not configured, using basic formatting")
                return self._create_basic_post(title, original_content, url, source)
            
            if not self.initialize_openai(settings.openai_api_key):
                return self._create_basic_post(title, original_content, url, source)
        
        try:
            # Create the prompt for engaging content
            prompt = self._create_enhancement_prompt(title, original_content, source)
            
            # Make the API call
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a social media expert specializing in the trucking and logistics industry. Create highly engaging, shareable Facebook posts that will resonate with truckers, fleet owners, and logistics professionals. Write like you're talking to a friend who's a trucker - be informative but also make it interesting and worth sharing."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=self.max_tokens,
                temperature=0.7,
                presence_penalty=0.1,
                frequency_penalty=0.1
            )
            
            enhanced_content = response.choices[0].message.content.strip()
            
            # Add URL and hashtags if not included
            final_content = self._finalize_post(enhanced_content, url, source)
            
            logger.info(f"Successfully enhanced post content using OpenAI")
            self._log_action('ai_enhance', f"Enhanced post: {title[:50]}...")
            
            return final_content
            
        except Exception as e:
            logger.error(f"Error enhancing content with OpenAI: {e}")
            self._log_action('ai_error', f"OpenAI enhancement failed: {str(e)}")
            # Fallback to basic formatting
            return self._create_basic_post(title, original_content, url, source)
    
    def _create_enhancement_prompt(self, title, content, source):
        """Create a prompt for OpenAI to enhance the content"""
        # Truncate content if too long to fit in prompt
        max_content_length = 1000
        if len(content) > max_content_length:
            content = content[:max_content_length] + "..."
        
        prompt = f"""
Create an engaging Facebook post for the trucking industry based on this news article:

Title: {title}
Content: {content}
Source: {source}

Requirements:
1. Make it highly engaging and relevant to truckers, fleet owners, and logistics professionals
2. Use appropriate emojis strategically (but don't overdo it)
3. Include a compelling hook in the first line that grabs attention
4. Keep it under 300 characters for the main text
5. Make it professional but conversational and relatable
6. Highlight the key impact or takeaway for the trucking community
7. Use industry-relevant language that resonates with trucking professionals
8. Don't include hashtags, URLs, or source - I'll add those separately
9. Make it shareable and encourage engagement
10. Focus on why this matters to the trucking community and make them want to engage

Style: Write like you're talking to a friend who's a trucker. Be informative but also make it interesting and worth sharing.
"""
        return prompt
    
    def _finalize_post(self, enhanced_content, url, source):
        """Add hashtags to the enhanced content (no URLs or source)"""
        # Remove any URLs or hashtags that AI might have added
        enhanced_content = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', enhanced_content)
        enhanced_content = re.sub(r'#\w+', '', enhanced_content)
        enhanced_content = enhanced_content.strip()
        
        # Build final post with just content and hashtags
        final_post = enhanced_content + "\n\n"
        
        # Add relevant hashtags (no URLs or source)
        hashtags = self._get_relevant_hashtags(enhanced_content)
        final_post += hashtags
        
        return final_post
    
    def _get_relevant_hashtags(self, content):
        """Generate relevant hashtags based on content"""
        base_hashtags = ["#TruckingNews", "#Logistics", "#Transportation", "#FreightNews"]
        
        content_lower = content.lower()
        
        # Add specific hashtags based on content
        if any(word in content_lower for word in ['driver', 'drivers']):
            base_hashtags.append("#TruckDrivers")
        
        if any(word in content_lower for word in ['fleet', 'fleets']):
            base_hashtags.append("#FleetManagement")
        
        if any(word in content_lower for word in ['safety', 'accident', 'regulation']):
            base_hashtags.append("#TruckingSafety")
        
        if any(word in content_lower for word in ['fuel', 'diesel', 'gas']):
            base_hashtags.append("#FuelPrices")
        
        if any(word in content_lower for word in ['technology', 'tech', 'digital', 'app']):
            base_hashtags.append("#TruckingTech")
        
        if any(word in content_lower for word in ['supply chain', 'shipping', 'cargo']):
            base_hashtags.append("#SupplyChain")
        
        if any(word in content_lower for word in ['electric', 'ev', 'green', 'sustainable']):
            base_hashtags.append("#ElectricTrucks")
        
        # Limit to 8 hashtags to avoid spam
        return " ".join(base_hashtags[:8])
    
    def _create_basic_post(self, title, content, url, source):
        """Create a basic post without AI enhancement (fallback) - Enhanced and engaging"""
        # Create engaging opening
        opening_phrases = [
            "🚛 Breaking in trucking:",
            "📰 Industry Update:",
            "🔥 Hot off the press:",
            "⚡ Trucking Alert:",
            "📢 Important news for truckers:",
            "🛣️ Latest from the road:",
            "💼 Business update:",
            "🎯 What's new in trucking:",
            "🚚 Industry insights:",
            "📊 Market update:",
            "💡 Industry spotlight:",
            "🌟 Trending in trucking:"
        ]
        
        import random
        opening = random.choice(opening_phrases)
        
        # Clean and truncate content
        if content and len(content) > 250:
            content = content[:250].rsplit(' ', 1)[0] + "..."
        
        post = f"{opening} {title}\n\n"
        
        if content and content != title:
            post += f"{content}\n\n"
        
        # Add engaging hashtags without links or source
        hashtags = "#TruckingNews #Logistics #Transportation #FreightNews #USATrucking"
        
        # Add context-specific hashtags
        content_lower = content.lower() if content else ""
        if any(word in content_lower for word in ['driver', 'drivers']):
            hashtags += " #TruckDrivers"
        if any(word in content_lower for word in ['fleet', 'fleets']):
            hashtags += " #FleetManagement"
        if any(word in content_lower for word in ['safety', 'accident', 'regulation']):
            hashtags += " #TruckingSafety"
        if any(word in content_lower for word in ['fuel', 'diesel', 'gas']):
            hashtags += " #FuelPrices"
        if any(word in content_lower for word in ['technology', 'tech', 'digital', 'app']):
            hashtags += " #TruckingTech"
        if any(word in content_lower for word in ['electric', 'ev', 'green', 'sustainable']):
            hashtags += " #ElectricTrucks"
        if any(word in content_lower for word in ['supply chain', 'shipping', 'cargo']):
            hashtags += " #SupplyChain"
        
        post += hashtags
        
        return post
    
    def generate_custom_post(self, topic, style="informative"):
        """Generate a custom post about a specific topic"""
        if not self.client:
            settings = Settings.query.first()
            if not settings or not settings.openai_api_key:
                return None
            
            if not self.initialize_openai(settings.openai_api_key):
                return None
        
        try:
            style_prompts = {
                "informative": "Create an informative and educational post",
                "motivational": "Create a motivational and inspiring post",
                "question": "Create an engaging post that asks a question to encourage discussion",
                "tip": "Create a helpful tip or advice post",
                "industry_insight": "Create a post sharing industry insights or trends"
            }
            
            style_instruction = style_prompts.get(style, style_prompts["informative"])
            
            prompt = f"""
{style_instruction} about {topic} for the trucking and logistics industry.

Requirements:
1. Make it highly engaging and relevant to truckers, fleet owners, and logistics professionals
2. Use appropriate emojis strategically (but don't overdo it)
3. Keep it under 280 characters
4. Make it professional but conversational and relatable
5. Encourage engagement and make it shareable
6. Don't include hashtags - I'll add those separately
7. Write like you're talking to a friend who's a trucker
8. Make it interesting and worth sharing

Topic: {topic}
"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a social media expert for the trucking industry. Create highly engaging, shareable content that resonates with trucking professionals. Write like you're talking to a friend who's a trucker - be informative but also make it interesting and worth sharing."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=150,
                temperature=0.8
            )
            
            content = response.choices[0].message.content.strip()
            
            # Add hashtags
            hashtags = self._get_relevant_hashtags(content + " " + topic)
            final_post = content + "\n\n" + hashtags
            
            return final_post
            
        except Exception as e:
            logger.error(f"Error generating custom post: {e}")
            return None
    
    def test_openai_connection(self, api_key):
        """Test OpenAI API connection"""
        try:
            test_client = openai.OpenAI(api_key=api_key)
            
            response = test_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "user", "content": "Say 'OpenAI connection successful' if you can read this."}
                ],
                max_tokens=10
            )
            
            return {
                'success': True,
                'message': response.choices[0].message.content.strip()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _log_action(self, action, message, post_id=None):
        """Log an action to the database"""
        log = PostingLog(
            post_id=post_id,
            action=action,
            message=message
        )
        db.session.add(log)
    
    def get_content_suggestions(self, keywords):
        """Get content suggestions based on keywords"""
        if not self.client:
            return []
        
        try:
            prompt = f"""
Generate 5 engaging Facebook post ideas for the trucking industry based on these keywords: {', '.join(keywords)}

For each idea, provide:
1. A catchy title
2. Brief description of the post content
3. Suggested style (question, tip, news, motivational, etc.)

Format as a JSON list of objects with keys: title, description, style
"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a content strategist for the trucking industry. Provide practical, engaging post ideas."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=400,
                temperature=0.8
            )
            
            content = response.choices[0].message.content.strip()
            
            # Try to parse JSON, fallback to simple list if it fails
            try:
                suggestions = json.loads(content)
                return suggestions
            except:
                # If JSON parsing fails, return basic suggestions
                return [
                    {"title": "Trucking Industry Update", "description": "Share latest industry news", "style": "informative"},
                    {"title": "Driver Safety Tips", "description": "Share safety advice", "style": "tip"},
                    {"title": "Fleet Management Question", "description": "Ask about fleet challenges", "style": "question"}
                ]
                
        except Exception as e:
            logger.error(f"Error getting content suggestions: {e}")
            return []