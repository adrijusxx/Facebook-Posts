# Facebook Trucking News Automation 🚛

An intelligent automation system that fetches the latest USA trucking industry news and posts engaging content to Facebook using AI enhancement.

## Features

### 🤖 AI-Powered Content Enhancement
- **OpenAI Integration**: Uses GPT-3.5-turbo to make posts more engaging
- **Multiple Styles**: Informative, motivational, questions, tips, and industry insights
- **Smart Hashtags**: Automatically adds relevant hashtags based on content
- **Professional Tone**: Maintains industry-appropriate language

### 📰 Smart News Fetching
- **Multiple Sources**: RSS feeds and website scraping
- **Trucking-Focused**: Filters content relevant to USA trucking industry
- **Duplicate Detection**: Prevents posting the same content twice
- **Source Management**: Easy-to-use interface for managing news sources

### 📅 Intelligent Scheduling
- **Flexible Timing**: Configure posting hours (default: 9 AM, 2 PM, 7 PM)
- **Daily Limits**: Set posts per day (1-10)
- **Auto-posting**: Fully automated or manual control
- **Smart Distribution**: Evenly distributes posts throughout the day

### 🎯 Facebook Integration
- **Graph API**: Direct posting to Facebook pages
- **Link Previews**: Automatic link and image attachment
- **Post Tracking**: Monitor post status and engagement
- **Error Handling**: Robust error handling and retry logic

### 🖥️ User-Friendly Interface
- **Modern Dashboard**: Clean, responsive web interface
- **Real-time Stats**: Live statistics and post monitoring
- **Quick Actions**: One-click news fetching and posting
- **Settings Management**: Easy configuration of all features

## Quick Start

### 1. Installation

```bash
git clone https://github.com/yourusername/facebook-trucking-automation.git
cd facebook-trucking-automation
pip install -r requirements.txt
```

### 2. Configuration

Copy the environment template:
```bash
cp .env.example .env
```

Edit `.env` with your configuration:
```env
SECRET_KEY=your-unique-secret-key
FACEBOOK_PAGE_ID=your-facebook-page-id
FACEBOOK_ACCESS_TOKEN=your-facebook-access-token
OPENAI_API_KEY=your-openai-api-key
```

### 3. Run the Application

```bash
python app.py
```

Visit `http://localhost:5000` to access the web interface.

## Setup Guide

### Facebook Setup

1. **Create a Facebook App**:
   - Go to [Facebook Developers](https://developers.facebook.com/)
   - Create a new app with "Business" type
   - Add "Pages" product to your app

2. **Get Page Access Token**:
   - Use the [Graph API Explorer](https://developers.facebook.com/tools/explorer/)
   - Select your app and page
   - Generate a token with `pages_manage_posts` permission
   - Exchange for a long-lived token

3. **Configure Permissions**:
   - Ensure your app has `pages_manage_posts` permission
   - Submit for review if publishing publicly

### OpenAI Setup

1. **Get API Key**:
   - Visit [OpenAI Platform](https://platform.openai.com/)
   - Go to API Keys section
   - Create a new secret key

2. **Configure Usage**:
   - Set up billing (pay-per-use)
   - Monitor usage in OpenAI dashboard
   - Adjust AI settings in the app interface

### News Sources

The application comes with default trucking news sources:
- Transport Topics
- Trucking Info
- Fleet Owner

You can add more sources through the web interface.

## Usage

### Dashboard
- **Statistics**: View total posts, daily posts, and success rates
- **Recent Posts**: Monitor latest posts and their status
- **Quick Actions**: Fetch news, post immediately, or generate AI content

### Settings
- **General**: Configure posting frequency and schedule
- **Facebook**: Set up page credentials and test connection
- **AI Enhancement**: Configure OpenAI and content style
- **News Sources**: Manage RSS feeds and news websites

### AI Features
- **Auto Enhancement**: Automatically improve all news posts
- **Custom Posts**: Generate posts on specific topics
- **Content Suggestions**: Get AI-powered content ideas
- **Style Control**: Choose from different post styles

## API Endpoints

### News Management
- `POST /api/fetch_news` - Fetch latest news
- `GET /api/posts` - Get all posts
- `POST /api/post_now` - Post immediately

### AI Features
- `POST /api/test_openai` - Test OpenAI connection
- `POST /api/generate_custom_post` - Generate AI content
- `POST /api/content_suggestions` - Get content ideas
- `POST /api/enhance_content` - Enhance existing content

## Configuration Options

### Posting Schedule
```python
# Set posting hours (24-hour format)
POSTING_HOURS = "9,14,19"  # 9 AM, 2 PM, 7 PM

# Set posts per day
POSTS_PER_DAY = 3
```

### AI Enhancement
```python
# AI styles available
AI_STYLES = [
    "informative",      # Professional, factual posts
    "motivational",     # Inspiring, encouraging posts
    "question",         # Discussion-starting questions
    "tip",             # Helpful advice and tips
    "industry_insight"  # Expert insights and analysis
]
```

### News Filtering
The system automatically filters content for trucking relevance using keywords:
- Transportation terms
- Trucking-specific vocabulary
- USA location indicators
- Industry regulations (DOT, FMCSA, etc.)

## Architecture

```
├── app.py                 # Main Flask application
├── models.py             # Database models
├── news_fetcher.py       # News fetching logic
├── facebook_poster.py    # Facebook API integration
├── ai_content_enhancer.py # OpenAI integration
├── templates/           # HTML templates
├── static/             # CSS, JS, images
└── requirements.txt    # Python dependencies
```

## Database Schema

- **Posts**: Store fetched articles and posting status
- **Settings**: Application configuration
- **NewsSource**: News source management
- **PostingLog**: Activity logging and debugging

## Security Features

- **Environment Variables**: Sensitive data in .env files
- **Token Validation**: Facebook and OpenAI token verification
- **Input Sanitization**: Protection against malicious input
- **Error Handling**: Graceful handling of API failures

## Monitoring and Logging

- **Dashboard Stats**: Real-time success rates and post counts
- **Activity Logs**: Detailed logging of all operations
- **Error Tracking**: Comprehensive error logging
- **Performance Metrics**: API response times and success rates

## Troubleshooting

### Common Issues

1. **Facebook API Errors**:
   - Check token permissions and expiration
   - Verify page ID is correct
   - Ensure app is not rate-limited

2. **OpenAI Errors**:
   - Verify API key is valid
   - Check account billing status
   - Monitor usage limits

3. **News Fetching Issues**:
   - Verify RSS feed URLs are accessible
   - Check internet connectivity
   - Review news source configurations

### Debug Mode

Run with debug enabled:
```bash
export FLASK_DEBUG=1
python app.py
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Create an issue on GitHub
- Check the troubleshooting section
- Review Facebook and OpenAI documentation

## Roadmap

- [ ] Instagram integration
- [ ] LinkedIn posting
- [ ] Advanced analytics
- [ ] Custom AI training
- [ ] Multi-language support
- [ ] Mobile app
- [ ] Webhook integrations

---

**Note**: This tool is designed for legitimate business use. Please comply with Facebook's terms of service and posting guidelines.