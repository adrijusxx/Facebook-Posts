# Facebook Token Renewal System

This system automatically manages Facebook access token renewal to ensure uninterrupted posting capabilities. Long-lived Facebook tokens typically last 60 days, and this system renews them automatically when they have 50 days or less remaining.

## Features

- **Automatic Token Renewal**: Checks token status every 6 hours and renews when needed
- **Manual Token Management**: API endpoints for manual token operations
- **Token Validation**: Comprehensive token validation and status checking
- **Error Handling**: Robust error handling with detailed logging
- **Database Integration**: Tracks token expiry dates and renewal history

## Quick Setup

1. **Run the setup script with your credentials**:
   ```bash
   python setup_token_system.py
   ```

2. **Or manually set up using the migration script**:
   ```bash
   # Run database migration
   python migrate_token_fields.py
   
   # Set up initial token data
   python migrate_token_fields.py "PAGE_ID" "ACCESS_TOKEN" "APP_ID" "APP_SECRET"
   ```

## Your Current Configuration

- **Page ID**: `534295833110036`
- **App ID**: `1173190721520267`
- **Token Renewal Interval**: Every 50 days (configurable)
- **Status Check Frequency**: Every 6 hours

## API Endpoints

### Check Token Status
```bash
GET /api/token/status
```
Returns current token status, expiry information, and renewal history.

### Manual Token Renewal
```bash
POST /api/token/renew
```
Manually trigger token renewal process.

### Set Up New Token
```bash
POST /api/token/setup
Content-Type: application/json

{
    "page_id": "534295833110036",
    "access_token": "YOUR_TOKEN",
    "app_id": "1173190721520267",
    "app_secret": "YOUR_APP_SECRET"
}
```

### Validate Token
```bash
POST /api/token/validate
Content-Type: application/json

{
    "access_token": "TOKEN_TO_VALIDATE"
}
```

## How It Works

### Automatic Renewal Process

1. **Scheduled Checks**: Every 6 hours, the system checks if token renewal is needed
2. **Renewal Trigger**: When a token has ≤50 days remaining, renewal is triggered
3. **Token Exchange**: Uses Facebook's token exchange API to get a fresh 60-day token
4. **Database Update**: Updates the database with the new token and expiry date
5. **Logging**: All activities are logged for monitoring

### Token Renewal Logic

```python
# Check if renewal is needed
if days_until_expiry <= 50:
    # Exchange current token for a new long-lived token
    new_token = exchange_token(app_id, app_secret, current_token)
    
    # Update database with new token
    update_database(new_token, new_expiry_date)
    
    # Log the renewal
    log_renewal_activity()
```

## Database Schema

New fields added to the `settings` table:

- `facebook_app_id` - Facebook App ID for token renewal
- `facebook_app_secret` - Facebook App Secret (encrypted)
- `facebook_token_expires_at` - Token expiration timestamp
- `facebook_token_last_renewed` - Last renewal timestamp
- `facebook_token_auto_renew` - Enable/disable auto-renewal

## Configuration Options

### Renewal Timing
You can modify the renewal threshold in `facebook_token_manager.py`:
```python
self.token_renewal_days = 50  # Renew when 50 days or less remain
```

### Check Frequency
Modify the scheduler frequency in `app.py`:
```python
schedule.every(6).hours.do(token_renewal_job)  # Check every 6 hours
```

### Enable/Disable Auto-Renewal
```python
# Disable auto-renewal
settings.facebook_token_auto_renew = False

# Enable auto-renewal
settings.facebook_token_auto_renew = True
```

## Monitoring and Logs

### Log Messages
- **Info**: Successful renewals and status checks
- **Warning**: Failed renewals or validation issues
- **Error**: System errors or connection problems

### Status Monitoring
Use the `/api/token/status` endpoint to monitor:
- Token validity
- Days until expiry
- Last renewal date
- Auto-renewal status

## Troubleshooting

### Common Issues

1. **Token Renewal Fails**
   - Check app credentials are correct
   - Ensure the current token is still valid
   - Verify app permissions include necessary scopes

2. **Auto-Renewal Not Working**
   - Check `facebook_token_auto_renew` is enabled
   - Verify scheduler is running
   - Check logs for error messages

3. **Token Validation Errors**
   - Ensure token hasn't expired manually
   - Check Facebook app is still active
   - Verify page permissions

### Manual Recovery

If automatic renewal fails, you can:

1. **Get a new token from Facebook**
2. **Update via API**:
   ```bash
   curl -X POST http://localhost:5000/api/token/setup \
     -H "Content-Type: application/json" \
     -d '{
       "page_id": "534295833110036",
       "access_token": "NEW_TOKEN",
       "app_id": "1173190721520267", 
       "app_secret": "YOUR_APP_SECRET"
     }'
   ```

## Security Notes

- App secrets are stored in the database (consider encryption for production)
- Tokens are validated before use
- Failed renewal attempts are logged for security monitoring
- All API endpoints should be secured in production environments

## File Structure

```
├── facebook_token_manager.py     # Main token management class
├── migrate_token_fields.py       # Database migration script
├── setup_token_system.py         # Quick setup script
├── models.py                     # Updated database models
├── app.py                        # Updated with token renewal scheduler
└── TOKEN_RENEWAL_SYSTEM.md       # This documentation
```

## Next Steps

1. **Run the setup script** to initialize the system
2. **Monitor the logs** for the first few renewal cycles
3. **Test the API endpoints** to ensure everything works
4. **Set up monitoring alerts** for renewal failures (optional)

The system is now ready to automatically manage your Facebook tokens for the next several years!