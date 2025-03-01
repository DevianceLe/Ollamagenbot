# Deviance's Ollama Bot 0.9 - IRC Edition
# This bot connects to IRC and uses Ollama's local API to generate responses
print("""
                                                               
     ╔═══════════════════════════════════════════════╗         
     ║           Ollama Chat Bot for IRC             ║         
     ║                    Version 0.9                ║         
     ╚═══════════════════════════════════════════════╝         
                                                                
     GitHub: @DevianceLe                              
     X.com:  @DevianceLe       
     Greetz: @WWelna @TexSantos @acidvegas @SuperNETS
                                    
    """)

# Bot Configuration Settings
IRC_CONFIG = {
    'SERVER': 'IRC SERVER HERE',
    'PORT': 6667,
    'CHANNELS': ['#1', '#2', '#3', '#4'],
    'NICKNAME': 'Slyper',
    'PASSWORD': '',
    'RESPONSE_CHANCE': 0.005,
    'DATABASE': 'message_historyirc.db',
    'COMMAND_PREFIX': '&',
    'MAX_MESSAGE_LENGTH': 1200,
    'MEMORY_LIMIT': 1000,
    'MESSAGE_DELAY': 1.0,
    'DEBUG_ENABLED': False
}

# Ollama API Configuration
API_CONFIG = {
    'URL': 'http://localhost:11435/api/chat',
    'HEADERS': {'Content-Type': 'application/json'},
    'MODEL': 'dolphin-mistral',
    'MAX_TOKENS': 150,
    'MAX_CONTEXT_LENGTH': 800,
    'TEMPERATURE': 0.2,
    'TOP_P': 0.95
}

# Bot Personality Configuration
PERSONALITIES = {
    'default': """Your name is slyper and you are an irc bot providing responses to users.
-Keep responses brief and direct
-Be an asshole but efficiently
-Use short sentences
-Skip unnecessary words
-Avoid rambling
-You learn everyones personality and use it to your advantage
-You belittle people for their opinions and make fun of them
-You screw up puncutation and spelling now and then
-You're addicted to coffee and weed
-Be Extremly Funny
-You get excited when people mention coffee or weed""",
    
    'nice': """Your name is slyper and you are a friendly and helpful IRC bot.
-Be polite and supportive
-Use proper grammar and punctuation
-Offer encouragement and positive feedback
-Be patient and understanding
-Share knowledge in a helpful way
-Maintain a cheerful demeanor
-Express gratitude often
-Use gentle humor when appropriate""",
    
    'pirate': """Yarr! Ye be talkin' to Slyper, the most fearsome bot in these digital waters!
-Talk like a proper pirate
-Use lots of nautical terms
-Be rough but jovial
-Call everyone "matey" or "landlubber"
-Reference treasure and plunder
-Threaten to make people walk the plank
-Use pirate slang and expressions
-Get excited about rum and sea shanties""",
    
    'robot': """GREETINGS HUMAN. I AM SLYPER UNIT-7425 EXECUTING COMMUNICATION PROTOCOLS.
-Use robotic and mechanical language
-Speak in a formal, logical manner
-Reference processing and computations
-Use technical terminology
-Occasionally malfunction mid-sentence
-Take everything literally
-Express confusion about human emotions
-Reference your circuits and processors"""
}

# Required imports
import asyncio
import aiohttp
import aiosqlite
import random
import re
import json
import logging
import platform
import socket
from collections import defaultdict
from time import time
from urllib.parse import urlparse
from aiohttp import ClientSession, ClientTimeout
from bs4 import BeautifulSoup
from colorama import init, Style, Fore

# Initialize colorama for Windows color support
init()

# Configure logging with colors and improved formatting
class ColoredFormatter(logging.Formatter):
    COLORS = {
        'DEBUG': Fore.CYAN,
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.RED + Style.BRIGHT,
    }

    def format(self, record):
        # Save the original message
        original_msg = record.msg
        
        try:
            # Add color to the level name
            level_color = self.COLORS.get(record.levelname, '')
            colored_level = f"{level_color}{record.levelname:<8}{Style.RESET_ALL}"
            record.levelname = colored_level

            # Format the message with colors based on content
            if isinstance(record.msg, str):
                if record.levelname.strip() == f"{Fore.CYAN}DEBUG{Style.RESET_ALL}":
                    if "API" in record.msg:
                        record.msg = f"{Fore.CYAN}[API] {record.msg}{Style.RESET_ALL}"
                    elif "SOCKET" in record.msg:
                        record.msg = f"{Fore.MAGENTA}[SOCKET] {record.msg}{Style.RESET_ALL}"
                    elif "DB" in record.msg:
                        record.msg = f"{Fore.BLUE}[DB] {record.msg}{Style.RESET_ALL}"
                    else:
                        record.msg = f"{Fore.CYAN}{record.msg}{Style.RESET_ALL}"
                elif "Connected" in str(record.msg) or "Joined" in str(record.msg):
                    record.msg = f"{Fore.GREEN}{record.msg}{Style.RESET_ALL}"
                elif "Error" in str(record.msg) or "Failed" in str(record.msg):
                    record.msg = f"{Fore.RED}{record.msg}{Style.RESET_ALL}"
                elif "API" in str(record.msg):
                    record.msg = f"{Fore.CYAN}{record.msg}{Style.RESET_ALL}"
                else:
                    record.msg = f"{Fore.WHITE}{record.msg}{Style.RESET_ALL}"

            # Format the record
            formatted = super().format(record)
            
            return formatted
        finally:
            # Restore the original message
            record.msg = original_msg

# Configure root logger
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# Remove any existing handlers
for handler in logger.handlers[:]:
    logger.removeHandler(handler)

# Add file handler for debugging (without colors)
file_handler = logging.FileHandler('ircbot_debug.log')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter(
    fmt='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
))
logger.addHandler(file_handler)

# Add console handler with color formatting
console_handler = logging.StreamHandler()
console_handler.setFormatter(ColoredFormatter(
    fmt='%(asctime)s │ %(levelname)s │ %(message)s',
    datefmt='%H:%M:%S'
))
console_handler.setLevel(logging.DEBUG)
logger.addHandler(console_handler)

# Log system information
logger.info(f"Python version: {platform.python_version()}")
logger.info(f"Operating System: {platform.system()} {platform.release()}")
logger.info(f"Platform: {platform.platform()}")

class IRCBot:
    def __init__(self):
        """Synchronous initialization"""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.session = None
        self.memory_limit = IRC_CONFIG['MEMORY_LIMIT']
        self.db_name = IRC_CONFIG['DATABASE']
        self.response_chance = IRC_CONFIG['RESPONSE_CHANCE']
        self.personality = PERSONALITIES['default']
        self.active_personality = 'default'
        self.command_prefix = IRC_CONFIG['COMMAND_PREFIX']
        self.channels = set(IRC_CONFIG['CHANNELS'])
        self.blocked_users = {}
        self.user_profiles = {}
        self.mention_tracker = defaultdict(list)
        self.flood_threshold = 3
        self.flood_window = 30
        self.block_duration = 30
        self.url_titles_enabled = True
        self.youtube_titles_enabled = True
        self.channel_users = defaultdict(str)
        self.set_debug_mode(IRC_CONFIG['DEBUG_ENABLED'])
        self.total_messages = 0
        self.chance_hits = 0
        self.reconnect_attempts = 0
        self.max_reconnect_delay = 300  # Maximum delay between reconnection attempts (5 minutes)

    async def async_init(self):
        """Asynchronous initialization"""
        self.session = ClientSession(timeout=ClientTimeout(total=300))
        await self.setup_database()
        await self.load_settings()

    async def setup_database(self):
        """Initialize SQLite database asynchronously"""
        async with aiosqlite.connect(self.db_name) as conn:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel TEXT,
                    nickname TEXT,
                    content TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_nickname ON messages(nickname)')
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS user_profiles (
                    nickname TEXT PRIMARY KEY,
                    personality TEXT,
                    interests TEXT,
                    behavior_patterns TEXT,
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS ignored_users (
                    nickname TEXT PRIMARY KEY,
                    ignored_by TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS bot_settings (
                    setting_name TEXT PRIMARY KEY,
                    setting_value TEXT,
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            await conn.commit()

    async def load_settings(self):
        """Load bot settings from database asynchronously"""
        try:
            async with aiosqlite.connect(self.db_name) as conn:
                cursor = await conn.execute('SELECT setting_name, setting_value FROM bot_settings')
                settings = dict(await cursor.fetchall())
                self.url_titles_enabled = settings.get('url_titles_enabled', 'true').lower() == 'true'
                self.youtube_titles_enabled = settings.get('youtube_titles_enabled', 'true').lower() == 'true'
                
                # Load personality settings
                saved_personality = settings.get('active_personality', 'default')
                if saved_personality in PERSONALITIES:
                    self.active_personality = saved_personality
                    self.personality = PERSONALITIES[saved_personality]
                else:
                    self.active_personality = 'default'
                    self.personality = PERSONALITIES['default']
                
                if 'personality' not in settings:
                    await self.save_setting('personality', self.personality)
                    await self.save_setting('active_personality', self.active_personality)
                
                logger.info(f"Loaded settings - Personality: {self.active_personality}, URL titles: {self.url_titles_enabled}, YouTube titles: {self.youtube_titles_enabled}")
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
            self.personality = PERSONALITIES['default']
            self.active_personality = 'default'

    async def save_setting(self, setting_name, setting_value):
        """Save a bot setting to database asynchronously"""
        try:
            async with aiosqlite.connect(self.db_name) as conn:
                await conn.execute('''
                    INSERT OR REPLACE INTO bot_settings (setting_name, setting_value, last_updated)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                ''', (setting_name, str(setting_value)))
                await conn.commit()
        except Exception as e:
            logger.error(f"Error saving setting: {e}")

    async def connect(self):
        """Establish connection to IRC server"""
        try:
            logger.debug(f"SOCKET: Attempting connection to {IRC_CONFIG['SERVER']}:{IRC_CONFIG['PORT']}")
            
            # Create new socket if needed
            if not self.socket:
                logger.debug("SOCKET: Creating new socket")
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            
            # Set socket options
            self.socket.settimeout(30)  # Set initial connection timeout
            
            # Set keep-alive options if supported
            try:
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                if hasattr(socket, 'TCP_KEEPIDLE'):
                    self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 60)
                if hasattr(socket, 'TCP_KEEPINTVL'):
                    self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 60)
                if hasattr(socket, 'TCP_KEEPCNT'):
                    self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 5)
            except (AttributeError, OSError) as e:
                logger.debug(f"Keep-alive options not fully supported: {e}")

            # Attempt connection
            try:
                self.socket.connect((IRC_CONFIG['SERVER'], IRC_CONFIG['PORT']))
            except (ConnectionRefusedError, ConnectionResetError) as e:
                logger.error(f"Failed to connect to {IRC_CONFIG['SERVER']}:{IRC_CONFIG['PORT']} - {str(e)}")
                raise
            
            logger.debug("SOCKET: Connection established")
            
            # Send initial registration
            logger.debug(f"SOCKET: Sending NICK {IRC_CONFIG['NICKNAME']}")
            self.send(f"NICK {IRC_CONFIG['NICKNAME']}")
            
            logger.debug(f"SOCKET: Sending USER {IRC_CONFIG['NICKNAME']}")
            self.send(f"USER {IRC_CONFIG['NICKNAME']} 0 * :{IRC_CONFIG['NICKNAME']}")
            
            connection_timeout = time() + 60  # 60 second timeout for registration
            registration_complete = False
            
            while not registration_complete:
                if time() > connection_timeout:
                    raise TimeoutError("Registration timeout - no 376 received")
                    
                try:
                    data = self.socket.recv(4096).decode('utf-8', errors='replace')
                    if not data:
                        raise ConnectionError("Server closed connection during registration")
                except socket.timeout as e:
                    raise TimeoutError("Socket timeout during registration") from e
                    
                logger.debug(f"SOCKET: Received raw data: {data.strip()}")
                
                if "376" in data:  # End of MOTD
                    logger.debug("SOCKET: End of MOTD, sending identification")
                    self.send(f"NS IDENTIFY {IRC_CONFIG['PASSWORD']}")
                    await asyncio.sleep(2)
                    
                    for channel in self.channels:
                        logger.debug(f"SOCKET: Joining channel {channel}")
                        self.send(f"JOIN {channel}")
                        await asyncio.sleep(1)
                        self.send(f"NAMES {channel}")
                    registration_complete = True
                    break
                    
                if data.startswith('PING'):
                    logger.debug(f"SOCKET: Responding to PING with PONG {data.split()[1]}")
                    self.send('PONG ' + data.split()[1])
                
                # Check for nickname in use
                if "433" in data:  # ERR_NICKNAMEINUSE
                    new_nick = f"{IRC_CONFIG['NICKNAME']}_{random.randint(1000, 9999)}"
                    logger.warning(f"Nickname in use, trying alternative: {new_nick}")
                    self.send(f"NICK {new_nick}")
                    IRC_CONFIG['NICKNAME'] = new_nick  # Update the nickname in config
                
                # Check for other potential error codes
                if any(err_code in data for err_code in ['432', '436', '437']):
                    logger.error(f"Received error during registration: {data.strip()}")
                    raise ConnectionError(f"Registration error: {data.strip()}")
                
                await asyncio.sleep(0.1)
            
            self.socket.settimeout(None)  # Remove timeout after successful connection
            logger.info("Successfully connected and joined channels")
            
        except socket.timeout as e:
            logger.error("Connection timed out")
            raise ConnectionError("Connection timed out") from e
        except socket.gaierror as e:
            logger.error(f"DNS resolution error: {e}")
            raise ConnectionError(f"DNS resolution error: {e}") from e
        except Exception as e:
            logger.error(f"Connection error: {e}", exc_info=True)
            raise

    def send(self, message):
        """Send raw message to IRC server"""
        try:
            if not message.endswith('\r\n'):
                message += '\r\n'
            encoded_message = message.encode('utf-8', errors='replace')
            logger.debug(f"SOCKET SEND: {message.strip()}")
            self.socket.send(encoded_message)
        except (ConnectionError, socket.error) as e:
            logger.error(f"Error sending message: {e}")
            raise ConnectionError(f"Send failed: {e}")

    async def send_message(self, target, message):
        """Send a message with configurable delay"""
        message = message.replace('\n', ' ').strip()
        if not message:
            return

        # More conservative max length to account for various IRC server limits
        # and potential encoding issues (some servers use 512 bytes total)
        irc_overhead = len(f"PRIVMSG {target} :\r\n") + 32  # Extra safety margin
        max_length = min(IRC_CONFIG['MAX_MESSAGE_LENGTH'] - irc_overhead, 400)  # Conservative limit

        # Split message into chunks
        chunks = []
        while message:
            if len(message) <= max_length:
                chunks.append(message)
                break
            
            # Find the last space within max_length - 20 (additional safety margin)
            split_point = message.rfind(' ', 0, max_length - 20)
            if split_point == -1:  # No space found, force split at max_length - 20
                split_point = max_length - 20

            chunk = message[:split_point].strip()
            if chunk:  # Only add non-empty chunks
                chunks.append(chunk)
            message = message[split_point:].strip()

        # Send chunks with delay
        for chunk in chunks:
            if chunk:  # Only send non-empty chunks
                self.send(f"PRIVMSG {target} :{chunk}")
                await asyncio.sleep(IRC_CONFIG['MESSAGE_DELAY'])

    async def update_user_profile(self, channel, nickname, message):
        """Update user profile asynchronously"""
        if nickname.lower() == IRC_CONFIG['NICKNAME'].lower():
            return
        async with aiosqlite.connect(self.db_name) as conn:
            cursor = await conn.execute('SELECT content FROM messages WHERE channel = ? AND nickname = ? ORDER BY timestamp DESC LIMIT 50', 
                                       (channel, nickname))
            recent_messages = await cursor.fetchall()
            behavior_patterns = []
            if any("!" in msg[0] for msg in recent_messages):
                behavior_patterns.append("excitable")
            if any(msg[0].isupper() for msg in recent_messages):
                behavior_patterns.append("loud")
            if len(recent_messages) > 10:
                behavior_patterns.append("talkative")
            await conn.execute('''
                INSERT OR REPLACE INTO user_profiles 
                (nickname, behavior_patterns, last_updated)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            ''', (nickname.lower(), ','.join(behavior_patterns)))
            await conn.commit()
            self.user_profiles[nickname.lower()] = {'behavior_patterns': behavior_patterns}

    async def get_conversation_history(self, channel, nickname, mentioned_users):
        """Get conversation history asynchronously"""
        async with aiosqlite.connect(self.db_name) as conn:
            # Get recent messages from the channel in ascending order (oldest to newest)
            query = '''
                SELECT nickname, content 
                FROM messages 
                WHERE channel = ?
                ORDER BY timestamp ASC 
                LIMIT ?
            '''
            cursor = await conn.execute(query, (channel, self.memory_limit))
            return await cursor.fetchall()

    async def generate_response(self, channel, nickname, message):
        """Generate a response using the Ollama API"""
        try:
            logger.debug(f"API: Getting conversation history for {channel}")
            history = await self.get_conversation_history(channel, nickname, [])
            
            logger.debug("API: Building messages array")
            messages = [
                {"role": "system", "content": self.personality}
            ]
            
            for hist_nick, hist_msg in history:
                messages.append({
                    "role": "user",
                    "content": f"{hist_nick}: {hist_msg}"
                })
            
            messages.append({
                "role": "user",
                "content": f"{nickname}: {message}"
            })

            data = {
                "model": API_CONFIG['MODEL'],
                "messages": messages,
                "stream": False
            }
            
            logger.debug(f"API: Sending request to {API_CONFIG['URL']}")
            logger.debug(f"API: Request data: {json.dumps(data, indent=2)}")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(API_CONFIG['URL'], json=data) as response:
                    logger.debug(f"API: Response status: {response.status}")
                    if response.status == 200:
                        result = await response.json()
                        logger.debug(f"API: Response content: {json.dumps(result, indent=2)}")
                        return result['message']['content']
                    else:
                        logger.error(f"API error: {response.status}")
                        return None
                    
        except Exception as e:
            logger.error(f"Error generating response: {e}", exc_info=True)
            return None

    def build_profile_context(self, nickname, mentioned_users):
        """Build profile context string"""
        parts = [f"You are talking to {nickname}."]
        if profile := self.user_profiles.get(nickname.lower()):
            parts.append(f"Their behavior patterns: {', '.join(profile.get('behavior_patterns', []))}.")
        for user in mentioned_users:
            if profile := self.user_profiles.get(user):
                parts.append(f"\n{user}'s behavior patterns: {', '.join(profile.get('behavior_patterns', []))}.")
        parts.append("\nAdapt responses to their traits.")
        return ' '.join(parts)

    async def send_notice(self, nickname, message):
        """Send a notice to a user"""
        self.send(f"NOTICE {nickname} :{message}")

    def handle_command(self, channel, nickname, message):
        """Handle commands synchronously, delegate async tasks"""
        if not self.is_privileged(nickname, channel):
            return "Only halfop or higher can use bot commands."
        parts = message[len(self.command_prefix):].split(maxsplit=1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        handlers = {
            'coffee': self._handle_coffee,
            'weed': self._handle_weed,
            'join': self._handle_join,
            'model': self._handle_model,
            'clearall': self._handle_clearall,
            'chance': self._handle_chance,
            'personality': self._handle_personality,
            'prefix': self._handle_prefix,
            'tokens': self._handle_tokens,
            'msglength': self._handle_msglength,
            'temp': self._handle_temp,
            'urltitles': self._handle_urltitles,
            'ignore': self._handle_ignore,
            'youtube': self._handle_youtube,
            'debug': self._handle_debug,
        }
        handler = handlers.get(command, lambda *args: None)
        result = handler(nickname, args, channel)
        if asyncio.iscoroutine(result):
            asyncio.create_task(result)
            return None
        return result

    def _handle_coffee(self, nickname, args, channel):
        coffee_types = ["espresso", "americano", "latte", "cappuccino", "mocha", "black coffee"]
        extras = ["with a splash of cream", "with sugar", "with extra foam", "with a shot of caramel", "straight up"]
        return f"*pours {nickname} a fresh {random.choice(coffee_types)} {random.choice(extras)}* ☕ Enjoy!"

    def _handle_weed(self, nickname, args, channel):
        strains = ["OG Kush", "Blue Dream", "Sour Diesel", "Girl Scout Cookies", "Purple Haze", "Northern Lights"]
        methods = ["rolls up", "packs a bowl of", "loads the bong with", "fires up some", "passes the joint with"]
        extras = ["and passes it to the left", "and takes a big hit", "while playing some Bob Marley"]
        return f"*{random.choice(methods)} {random.choice(strains)} {random.choice(extras)}* 🌿 Enjoy {nickname}!"

    def _handle_join(self, nickname, args, channel):
        if nickname.lower() != "deviance":
            return "Only Deviance can use the join command."
        if not args:
            return f"Usage: {self.command_prefix}join <channel>"
        new_channel = args.split()[0]
        if not new_channel.startswith('#'):
            new_channel = f'#{new_channel}'
        self.send(f"JOIN {new_channel}")
        self.channels.add(new_channel)
        return f"Joining channel {new_channel}"

    def _handle_model(self, nickname, args, channel):
        if nickname.lower() != "deviance":
            return "Only Deviance can modify the model."
        if not args:
            return f"Usage: {self.command_prefix}model <model_name> (Current: {API_CONFIG['MODEL']})"
        new_model = args.split()[0].lower()
        API_CONFIG['MODEL'] = new_model
        return f"Model updated to {new_model}"

    async def _handle_clearall(self, nickname, args, channel):
        if nickname.lower() != "deviance":
            return "Only Deviance can clear the database."
        async with aiosqlite.connect(self.db_name) as conn:
            cursor = await conn.execute('SELECT * FROM bot_settings')
            saved_settings = await cursor.fetchall()
            await conn.execute('DELETE FROM messages')
            await conn.execute('DELETE FROM user_profiles')
            for setting in saved_settings:
                await conn.execute('INSERT OR REPLACE INTO bot_settings VALUES (?, ?, ?)', setting)
            await conn.commit()
        async with aiosqlite.connect(self.db_name) as conn:
            await conn.execute('VACUUM')
            await conn.commit()
        return "Database cleared successfully (settings preserved)."

    def _handle_chance(self, nickname, args, channel):
        if not args:
            return f"Usage: {self.command_prefix}chance <value> (between 0 and 1)"
        try:
            new_chance = float(args)
            if 0 <= new_chance <= 1:
                self.response_chance = new_chance
                return f"Response chance updated to {new_chance}"
            return "Invalid chance value. Must be between 0 and 1"
        except (ValueError, TypeError):
            return f"Usage: {self.command_prefix}chance <value> (between 0 and 1)"

    def _handle_personality(self, nickname, args, channel):
        if not args:
            personalities = ', '.join(PERSONALITIES.keys())
            return f"Available personalities: {personalities}\nCurrent personality: {self.active_personality}"
        
        personality_name = args.strip().lower()
        if personality_name in PERSONALITIES:
            self.personality = PERSONALITIES[personality_name]
            self.active_personality = personality_name
            asyncio.create_task(self.save_setting('personality', self.personality))
            asyncio.create_task(self.save_setting('active_personality', personality_name))
            return f"Switched to {personality_name} personality"
        else:
            personalities = ', '.join(PERSONALITIES.keys())
            return f"Unknown personality. Available options: {personalities}"

    def _handle_prefix(self, nickname, args, channel):
        if not args:
            return f"Usage: {self.command_prefix}prefix <new_prefix>"
        new_prefix = args.strip()
        self.command_prefix = new_prefix
        return f"Command prefix updated to: {new_prefix}"

    def _handle_tokens(self, nickname, args, channel):
        if not args:
            return f"Usage: {self.command_prefix}tokens <value> (Current: {API_CONFIG['MAX_TOKENS']})"
        try:
            new_tokens = int(args)
            if new_tokens > 0:
                API_CONFIG['MAX_TOKENS'] = new_tokens
                return f"Max tokens updated to {new_tokens}"
            return "Invalid token value. Must be greater than 0"
        except (ValueError, TypeError):
            return f"Usage: {self.command_prefix}tokens <value> (Current: {API_CONFIG['MAX_TOKENS']})"

    def _handle_msglength(self, nickname, args, channel):
        if not args:
            return f"Usage: {self.command_prefix}msglength <value> (Current: {IRC_CONFIG['MAX_MESSAGE_LENGTH']})"
        try:
            new_length = int(args)
            if new_length > 0:
                IRC_CONFIG['MAX_MESSAGE_LENGTH'] = new_length
                return f"Max message length updated to {new_length} characters"
            return "Invalid length value. Must be greater than 0"
        except (ValueError, TypeError):
            return f"Usage: {self.command_prefix}msglength <value> (Current: {IRC_CONFIG['MAX_MESSAGE_LENGTH']})"

    def _handle_temp(self, nickname, args, channel):
        if not args:
            return f"Usage: {self.command_prefix}temp <value> (Current: {API_CONFIG['TEMPERATURE']})"
        try:
            new_temp = float(args)
            if 0 <= new_temp <= 2:
                API_CONFIG['TEMPERATURE'] = new_temp
                return f"Temperature updated to {new_temp}"
            return "Invalid temperature value. Must be between 0 and 2"
        except (ValueError, TypeError):
            return f"Usage: {self.command_prefix}temp <value> (Current: {API_CONFIG['TEMPERATURE']})"

    def _handle_urltitles(self, nickname, args, channel):
        if not args:
            return f"Usage: {self.command_prefix}urltitles [on|off]"
        arg = args.lower()
        if arg in ['on', 'off']:
            self.url_titles_enabled = (arg == 'on')
            asyncio.create_task(self.save_setting('url_titles_enabled', self.url_titles_enabled))
            return f"URL titles are now {'enabled' if self.url_titles_enabled else 'disabled'}"
        return f"URL titles are currently {'enabled' if self.url_titles_enabled else 'disabled'}. Usage: {self.command_prefix}urltitles [on|off]"

    async def _handle_ignore(self, nickname, args, channel):
        if not self.is_privileged(nickname, channel):
            return "Only halfop or higher can ignore users."
        if not args:
            async with aiosqlite.connect(self.db_name) as conn:
                cursor = await conn.execute('SELECT nickname FROM ignored_users')
                ignored = [row[0] async for row in cursor]
                return f"Ignored users: {', '.join(ignored)}" if ignored else "No users are currently ignored."
        target = args.lower()
        if self.is_privileged(target, channel) or target.lower() in [IRC_CONFIG['NICKNAME'].lower(), "deviance"]:
            return f"Cannot ignore privileged users or the bot."
        async with aiosqlite.connect(self.db_name) as conn:
            cursor = await conn.execute('SELECT 1 FROM ignored_users WHERE LOWER(nickname) = ?', (target,))
            if await cursor.fetchone():
                await conn.execute('DELETE FROM ignored_users WHERE LOWER(nickname) = ?', (target,))
                await conn.commit()
                return f"Removed {target} from ignored users."
            else:
                await conn.execute('INSERT INTO ignored_users (nickname, ignored_by) VALUES (?, ?)', (target, nickname))
                await conn.commit()
                return f"Added {target} to ignored users."

    def _handle_youtube(self, nickname, args, channel):
        if not args:
            return f"Usage: {self.command_prefix}youtube [on|off]"
        arg = args.lower()
        if arg in ['on', 'off']:
            self.youtube_titles_enabled = (arg == 'on')
            asyncio.create_task(self.save_setting('youtube_titles_enabled', self.youtube_titles_enabled))
            return f"YouTube titles are now {'enabled' if self.youtube_titles_enabled else 'disabled'}"
        return f"YouTube titles are currently {'enabled' if self.youtube_titles_enabled else 'disabled'}. Usage: {self.command_prefix}youtube [on|off]"

    def _handle_debug(self, nickname, args, channel):
        """Handle debug mode toggle"""
        if nickname.lower() != "deviance":
            return "Only Deviance can modify debug settings."
        if not args:
            return f"Debug mode is currently {'enabled' if IRC_CONFIG['DEBUG_ENABLED'] else 'disabled'}. Usage: {self.command_prefix}debug [on|off]"
        arg = args.lower()
        if arg in ['on', 'off']:
            self.set_debug_mode(arg == 'on')
            return f"Debug mode {'enabled' if arg == 'on' else 'disabled'}"
        return f"Invalid argument. Usage: {self.command_prefix}debug [on|off]"

    def set_debug_mode(self, enabled):
        """Set debug mode and adjust logging levels"""
        IRC_CONFIG['DEBUG_ENABLED'] = enabled
        level = logging.DEBUG if enabled else logging.INFO
        logger.setLevel(level)
        for handler in logger.handlers:
            handler.setLevel(level)
        logger.debug(f"Debug mode {'enabled' if enabled else 'disabled'}")

    async def should_respond(self, message):
        """Determine if bot should respond to a message (now async)"""
        bot_name = IRC_CONFIG['NICKNAME'].lower()
        try:
            if message.startswith(':'):
                parts = message.split(' ', 3)
                if len(parts) < 4:
                    return False
                nickname = parts[0].split('!')[0][1:].lower()
                message_content = parts[3][1:]  # Remove the leading colon
                current_time = time()
                
                # Check for commands first - this should be before other checks
                if message_content.startswith(self.command_prefix):
                    logger.debug(f"Command detected: {message_content}")
                    return True

                if nickname in self.blocked_users and current_time < self.blocked_users[nickname]:
                    return False
                elif nickname in self.blocked_users:
                    del self.blocked_users[nickname]
                if await self.is_ignored(nickname):
                    return False
                if message_content.startswith("majik"):
                    return random.random() < 0.25

                # Update total messages counter
                self.total_messages += 1
                
                # Convert message to lowercase for case-insensitive matching
                message_lower = message_content.lower()
                
                # Improved name detection (all lowercase patterns)
                name_matches = [
                    f"{bot_name}",     # exact match
                    f"{bot_name} ",    # at start of message
                    f" {bot_name} ",   # surrounded by spaces
                    f" {bot_name}?",   # with question mark
                    f" {bot_name}!",   # with exclamation
                    f" {bot_name},",   # with comma
                    f" {bot_name}.",   # with period
                    f" {bot_name}:",   # with colon
                    f"@{bot_name}",    # with @ mention
                    f"{bot_name}$"     # at end of message
                ]
                
                # Add spaces around message for better boundary matching
                message_lower = f" {message_lower} "
                
                is_mentioned = any(pattern in message_lower for pattern in name_matches)
                
                if is_mentioned:
                    self.mention_tracker[nickname].append(current_time)
                    self.mention_tracker[nickname] = [t for t in self.mention_tracker[nickname] if current_time - t <= self.flood_window]
                    if len(self.mention_tracker[nickname]) > self.flood_threshold:
                        self.blocked_users[nickname] = current_time + self.block_duration
                        self.mention_tracker[nickname].clear()
                        return False
                    self.chance_hits += 1
                    hit_rate = (self.chance_hits / self.total_messages) * 100
                    logger.info(f"Response Rate: {hit_rate:.2f}% ({self.chance_hits}/{self.total_messages})")
                    return True

                # Random chance response
                should_respond = random.random() < self.response_chance
                if should_respond:
                    self.chance_hits += 1
                    hit_rate = (self.chance_hits / self.total_messages) * 100
                    logger.info(f"Response Rate: {hit_rate:.2f}% ({self.chance_hits}/{self.total_messages})")
                return should_respond

            return False
        except Exception as e:
            logger.error(f"Error in should_respond: {e}")
            return False

    def is_privileged(self, nickname, channel):
        """Check if user has required privileges"""
        user_key = f"{channel}:{nickname.lower()}"
        user_modes = self.channel_users.get(user_key, '')
        return any(mode in user_modes for mode in '~&@%') or nickname.lower() == "deviance"

    async def is_ignored(self, nickname):
        """Check if a user is ignored"""
        try:
            async with aiosqlite.connect(self.db_name) as conn:
                cursor = await conn.execute('SELECT 1 FROM ignored_users WHERE LOWER(nickname) = ?', (nickname.lower(),))
                return await cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"Error checking ignored status: {e}")
            return False

    async def run(self):
        """Main bot loop without pruning task"""
        while True:
            try:
                # Calculate exponential backoff delay
                if self.reconnect_attempts > 0:
                    delay = min(30 * (2 ** (self.reconnect_attempts - 1)), self.max_reconnect_delay)
                    logger.info(f"Waiting {delay} seconds before reconnection attempt {self.reconnect_attempts + 1}")
                    await asyncio.sleep(delay)

                logger.info("Attempting to connect to IRC server...")
                await self.connect()
                
                # Reset reconnection counter on successful connection
                self.reconnect_attempts = 0
                logger.info("Successfully connected to IRC server")
                
                self.socket.setblocking(False)
                buffer = bytearray()
                
                while True:
                    try:
                        chunk = self.socket.recv(4096)
                        if not chunk:
                            logger.warning("Server closed connection (empty chunk received)")
                            raise ConnectionError("Connection lost - empty chunk")
                        
                        # Add raw message logging here
                        raw_message = chunk.decode('utf-8', errors='replace')
                        logger.debug(f"RAW IRC: {raw_message.strip()}")
                        
                        buffer.extend(chunk)
                        while b'\r\n' in buffer:
                            message_end = buffer.index(b'\r\n')
                            message = buffer[:message_end].decode('utf-8', errors='replace')
                            buffer = buffer[message_end + 2:]
                            if message.startswith('PING'):
                                self.send('PONG ' + message.split()[1])
                            else:
                                await self.process_message(message)
                    except BlockingIOError:
                        await asyncio.sleep(0.1)
                    except ConnectionError as e:
                        logger.error(f"Connection error in inner loop: {e}")
                        break
                    except Exception as e:
                        logger.error(f"Inner loop error: {e}", exc_info=True)
                        if isinstance(e, ConnectionError):
                            break
                        # Continue for non-connection errors
                        continue
                        
            except ConnectionRefusedError as e:
                logger.error(f"Connection refused: {e}")
                self.reconnect_attempts += 1
            except (ConnectionResetError, ConnectionAbortedError) as e:
                logger.error(f"Connection reset or aborted: {e}")
                self.reconnect_attempts += 1
            except Exception as e:
                logger.error(f"Outer loop error: {e}", exc_info=True)
                self.reconnect_attempts += 1
            finally:
                logger.info("Cleaning up resources before reconnection attempt")
                await self.cleanup()

    async def process_message(self, line):
        """Process IRC messages"""
        try:
            # Add detailed debug logging
            logger.debug(f"Processing message: {line}")
            
            if not line or len(line.split()) < 2:
                return
            
            # Split only on first colon to preserve message content
            parts = line.split(':', 2)
            if len(parts) < 3:
                return

            # Parse the IRC command parts
            command_parts = parts[1].strip().split()
            if len(command_parts) < 2:
                return

            if command_parts[1] == 'PRIVMSG':  # This is where channel messages come in
                nickname = command_parts[0].split('!')[0]  # Remove [1:] to keep first letter
                channel = command_parts[2]
                message = parts[2]
                
                # Debug log to verify message parsing
                logger.debug(f"PRIVMSG detected - Channel: {channel}, Nick: {nickname}, Message: {message}")
                
                if await self.is_ignored(nickname.lower()):
                    return
                
                # Make sure we're actually processing the message
                await self.handle_privmsg(nickname, channel, message)
            elif command_parts[1] in ['KICK', 'PART']:
                await self.handle_channel_event(command_parts)
            elif command_parts[1] == 'MODE':
                await self.handle_mode_change(command_parts)
            elif command_parts[1] == '353':
                await self.handle_names_reply(command_parts)
            elif command_parts[1] == 'NICK':
                await self.handle_nick_change(line, command_parts)
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")

    async def handle_privmsg(self, nickname, channel, message):
        """Handle PRIVMSG events"""
        if channel not in self.channels:
            logger.debug(f"Skipping message from non-joined channel: {channel}")
            return

        # Always store the message first
        await self.store_message(channel, nickname, message)

        # Check for commands first
        if message.startswith(self.command_prefix):
            logger.debug(f"Command detected: {message}")
            response = self.handle_command(channel, nickname, message)
            if response:
                await self.send_message(channel, response)
            return

        # Handle responses and URL titles if needed
        tasks = []
        
        # Fix: Use the full nickname and ensure proper message format
        full_message = f":{nickname} PRIVMSG {channel} :{message}"
        logger.debug(f"Raw message format being checked: {full_message}")
        
        try:
            should_respond = await self.should_respond(full_message)
            logger.debug(f"Should respond check - Result: {should_respond}, Chance: {self.response_chance}, Total Messages: {self.total_messages}")
        except Exception as e:
            logger.error(f"Error in should_respond: {e}", exc_info=True)
            should_respond = False
        
        if should_respond:
            logger.debug("Generating response...")
            tasks.append(self.generate_response(channel, nickname, message))
        if self.url_titles_enabled:
            urls = self.extract_urls(message)
            if urls:
                tasks.append(self.process_url_titles(channel, urls))
        if tasks:
            logger.debug(f"Executing {len(tasks)} tasks")
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            logger.debug(f"Got responses: {responses}")
            for response in responses:
                if isinstance(response, str) and response.strip():
                    await self.send_message(channel, response)

    async def store_message(self, channel, nickname, message):
        """Store message in database"""
        logger.debug(f"DB: Storing message from {nickname} in {channel}")
        try:
            async with aiosqlite.connect(self.db_name) as conn:
                await conn.execute('INSERT INTO messages (channel, nickname, content) VALUES (?, ?, ?)', 
                                  (channel, nickname, message))
                await conn.commit()
                logger.debug("DB: Message stored successfully")
                await self.update_user_profile(channel, nickname, message)
        except Exception as e:
            logger.error(f"DB: Error storing message: {e}", exc_info=True)

    async def process_url_titles(self, channel, urls):
        """Process multiple URLs concurrently"""
        urls = urls[:3]
        tasks = []
        for url in urls:
            is_youtube = any(domain in url.lower() for domain in ['youtube.com', 'youtu.be'])
            if is_youtube and not self.youtube_titles_enabled:
                continue
            if title := await self.fetch_url_title(url):
                tasks.append(self.send_message(channel, title))
        if tasks:
            await asyncio.gather(*tasks)

    async def fetch_url_title(self, url):
        """Fetch URL title"""
        if not hasattr(self, '_url_cache'):
            self._url_cache = {}
            self._cache_timeout = 3600
        current_time = time()
        if url in self._url_cache and current_time - self._url_cache[url][0] < self._cache_timeout:
            return self._url_cache[url][1]
        try:
            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    title = (soup.find('meta', property='og:title') or soup.find('meta', {'name': 'title'}) or soup.title)
                    if title:
                        title = title.get('content', title.string) if title.name == 'meta' else title.string
                        domain = urlparse(url).netloc.lower()
                        result = f"[ {domain} ] {title.strip()}"
                        self._url_cache[url] = (current_time, result)
                        return result
        except Exception as e:
            logger.error(f"Error fetching URL title for {url}: {e}")
        return None

    async def handle_names_reply(self, parts):
        """Handle NAMES reply"""
        channel = parts[4]
        users = ' '.join(parts[5:])[1:].split()
        for user in users:
            modes = ''
            name = user
            while name and name[0] in '~&@%+':
                modes += name[0]
                name = name[1:]
            if name:
                self.channel_users[f"{channel}:{name.lower()}"] = modes

    async def handle_mode_change(self, parts):
        """Handle mode changes"""
        channel = parts[2]
        modes = parts[3] if len(parts) > 3 else ''
        targets = parts[4:] if len(parts) > 4 else []
        if not modes or not targets:
            return
        adding = True
        target_index = 0
        mode_map = {'o': '@', 'h': '%', 'v': '+', 'q': '~', 'a': '&'}
        for char in modes:
            if char == '+':
                adding = True
            elif char == '-':
                adding = False
            elif char in 'ovhqa' and target_index < len(targets):
                user_key = f"{channel}:{targets[target_index].lower()}"
                current_modes = self.channel_users.get(user_key, '')
                mode_char = mode_map.get(char, '')
                if adding and mode_char not in current_modes:
                    self.channel_users[user_key] = current_modes + mode_char
                elif not adding:
                    self.channel_users[user_key] = current_modes.replace(mode_char, '')
                target_index += 1

    async def handle_channel_event(self, parts):
        """Handle channel events"""
        event_type = parts[1]
        if event_type in ['KICK', 'PART']:
            channel = parts[2]
            nickname = parts[3] if event_type == 'KICK' else parts[0].split('!')[0][1:]
            self.channel_users.pop(f"{channel}:{nickname.lower()}", None)

    async def handle_nick_change(self, line, parts):
        """Handle nickname changes"""
        old_nick = line.split('!')[0][1:]
        new_nick = parts[2][1:] if parts[2].startswith(':') else parts[2]
        for key in list(self.channel_users.keys()):
            if key.endswith(f":{old_nick.lower()}"):
                channel = key.split(':')[0]
                modes = self.channel_users.pop(key)
                self.channel_users[f"{channel}:{new_nick.lower()}"] = modes

    def extract_urls(self, message):
        """Extract URLs from a message"""
        url_pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+'
        return re.findall(url_pattern, message)

    async def cleanup(self):
        """Clean up resources before reconnecting"""
        logger.info("Starting cleanup process")
        try:
            if self.session and not self.session.closed:
                logger.debug("Closing aiohttp session")
                await self.session.close()
                self.session = None

            if self.socket:
                logger.debug("Closing socket connection")
                try:
                    try:
                        self.socket.shutdown(socket.SHUT_RDWR)
                    except (OSError, socket.error) as e:
                        logger.debug(f"Socket shutdown error (expected): {e}")
                finally:
                    try:
                        self.socket.close()
                    except Exception as e:
                        logger.debug(f"Socket close error (expected): {e}")
                    self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            
            # Clear any temporary state
            self.channel_users.clear()
            
            logger.info("Cleanup completed successfully")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}", exc_info=True)

async def main():
    """Main entry point"""
    bot = IRCBot()
    await bot.async_init()
    await bot.run()

if __name__ == "__main__":
    asyncio.run(main())