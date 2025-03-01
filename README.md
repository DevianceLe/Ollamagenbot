# Ollama Chat Bot Suite

A versatile chat bot suite that integrates Ollama's language models with multiple platforms: Discord, IRC, and a Bridge server. This suite allows you to deploy AI-powered chat bots across different communication platforms while using Ollama's local language models.

## Components

### 1. Bridge Server (bridge.py)
- Acts as an intermediary between chat platforms and Ollama API
- Manages request queuing and rate limiting
- Runs on port 11435 by default
- Provides a FastAPI-based HTTP interface

### 2. Discord Bot (discordbot.py)
- Full-featured Discord bot integration
- Supports multiple channels and commands
- Message history tracking and user profiling
- URL title fetching and YouTube link handling
- SQLite database for persistent storage

### 3. IRC Bot (ircbot.py)
- Feature-rich IRC bot implementation
- Multiple personality modes
- Channel management and user privilege tracking
- URL title fetching
- Message history and user profiling
- Flood protection and user ignore system

## Prerequisites

- Python 3.8+
- Ollama installed and running locally (default port: 11434)
- Discord Developer Account (for Discord bot)
- Required Python packages:
  ```
  fastapi
  uvicorn
  aiohttp
  discord.py
  beautifulsoup4
  colorama
  sqlite3
  pydantic
  ```

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/ollamagenbot.git
cd ollamagenbot
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

3. Configure the bots:
   - Set up Discord bot token in `discordbot.py`
   - Configure IRC server settings in `ircbot.py`
   - Adjust bridge server settings in `bridge.py` if needed

## Usage

### Bridge Server
```bash
python bridge.py
```
The bridge server will start on port 11435 by default.

### Discord Bot
```bash
python discordbot.py
```
Default command prefix: `!`

#### Discord Commands
- `!clearall` - Clear channel message history (admin only)
- `!clearme` - Clear user's message history
- `!setmodel` - Change the Ollama model
- `!coffee` - Fun coffee-related interaction
- `!weed` - Fun weed-related interaction
- `!personality` - Change bot personality
- `!urltitles` - Toggle URL title fetching
- `!youtube` - Toggle YouTube title fetching
- `!debug` - Toggle debug mode (admin only)

### IRC Bot
```bash
python ircbot.py
```
Default command prefix: `&`

#### IRC Commands
- `&coffee` - Fun coffee-related interaction
- `&weed` - Fun weed-related interaction
- `&join` - Join a channel (admin only)
- `&model` - Change the Ollama model
- `&clearall` - Clear message history (admin only)
- `&chance` - Set response probability
- `&personality` - Change bot personality
- `&prefix` - Change command prefix
- `&urltitles` - Toggle URL title fetching
- `&ignore` - Ignore/unignore users
- `&debug` - Toggle debug mode (admin only)

## Configuration

### Bridge Server (bridge.py)
```python
MAX_CONCURRENT_REQUESTS = 1
OLLAMA_API_URL = "http://localhost:11434/api/chat"
BRIDGE_HOST = "0.0.0.0"
BRIDGE_PORT = 11435
```

### Discord Bot (discordbot.py)
```python
TOKEN = 'YOUR_DISCORD_BOT_TOKEN'
DB_NAME = 'message_history.db'
API_URL = "http://localhost:11435/api/chat"
MODEL = "mistral"  # Default model
```

### IRC Bot (ircbot.py)
```python
IRC_CONFIG = {
    'SERVER': 'IRC SERVER HERE',
    'PORT': 6667,
    'CHANNELS': ['#channel1', '#channel2'],
    'NICKNAME': 'BotName',
    'PASSWORD': '',
    'RESPONSE_CHANCE': 0.005
}
```

## Features

### Common Features
- Message history tracking
- User profiling
- Multiple personality modes
- URL title fetching
- Command system
- Debug logging

### Discord-Specific Features
- Channel-based conversations
- Role-based permissions
- Message chunking for long responses
- Embed support

### IRC-Specific Features
- Flood protection
- User privilege tracking
- Multiple channel support
- Nickname tracking
- Connection resilience

## Security Considerations

- API keys and tokens should be stored securely
- Rate limiting is implemented to prevent abuse
- User privileges are checked for sensitive commands
- Flood protection prevents spam
- Input sanitization for all user inputs

## Troubleshooting

1. **Connection Issues**
   - Verify Ollama is running on port 11434
   - Check network connectivity
   - Verify bot tokens and credentials

2. **Permission Errors**
   - Ensure proper bot permissions in Discord
   - Verify IRC channel operator status

3. **Database Issues**
   - Check write permissions for SQLite files
   - Verify database integrity

## Contributing

Contributions are welcome! Please feel free to submit pull requests or create issues for bugs and feature requests.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Credits

Created by @DevianceLe
Special thanks to @WWelna @TexSantos @acidvegas @SuperNETS

## Version History

- 0.9 - Initial public release
  - Multi-platform support
  - Advanced message handling
  - User profiling
  - Multiple personality modes
``` 