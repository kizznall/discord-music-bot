# Discord Music Bot

A simple and efficient Discord music bot that plays audio from YouTube links.

## Features

- Play audio from YouTube URLs or video IDs
- Queue system with admin controls
- Auto-disconnect after inactivity
- Admin commands for queue management
- High-quality audio playback

## Commands

- `!play <url/id>` - Play audio from a YouTube URL or video ID
- `!skip` - Skip the current track
- `!queue` - Show the current queue
- `!clear` - Clear the queue (admin only)
- `!deleteall` - Delete all tracks and disconnect (admin only)
- `!stop` - Stop playback and disconnect (admin only)

## Setup

1. Clone the repository
```bash
git clone https://github.com/yourusername/discord-music-bot.git
cd discord-music-bot
```

2. Install dependencies
```bash
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
pip install -r requirements.txt
```

3. Create config file
Create `config/config.json` with your bot settings:
```json
{
    "token": "YOUR_BOT_TOKEN",
    "voice_channel_id": "YOUR_VOICE_CHANNEL_ID",
    "admin_users": ["YOUR_USER_ID"],
    "admin_roles": ["Admin"],
    "public_access": true
}
```

4. Run the bot
```bash
python bot.py
```

## Requirements

- Python 3.8+
- FFmpeg
- Discord Bot Token
- Required Python packages (see requirements.txt)

## Contributing

Feel free to open issues or submit pull requests!

## License

MIT License - feel free to use and modify as you wish.
