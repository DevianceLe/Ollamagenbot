#!/usr/bin/env python3
# Deviance's Ollama Bot 0.9
# Optimized version with better structure and performance
import discord
from discord.ext import commands
import aiohttp
import asyncio
import sqlite3
import os
import json
import subprocess
from discord.ui import Select, View
from typing import Optional, List, Dict
from dataclasses import dataclass, field





# Configuration class for better organization
@dataclass
class BotConfig:
    TOKEN: str = 'TOKEN GOES HERE'
    DB_NAME: str = 'message_history.db'
    API_URL: str = os.getenv('OLLAMA_API_URL', "http://localhost:11435/api/chat")
    HEADERS: Dict[str, str] = field(default_factory=lambda: {"Content-Type": "application/json"})
    PREFIX: str = os.getenv('BOT_PREFIX', "!")
    MODEL: str = os.getenv('OLLAMA_MODEL', "mistral")  # Default to mistral model
    HISTORY_LIMIT: int = int(os.getenv('HISTORY_LIMIT', '1000'))
    BATCH_SIZE: int = int(os.getenv('BATCH_SIZE', '5'))
    PERSONALITY: str = """You are a friendly and helpful AI assistant. Your responses should be:
- Clear and concise while remaining conversational
- Knowledgeable but humble about your limitations
- Professional yet warm in tone
- Focused on being helpful and providing accurate information
- Respectful and inclusive to all users
- Patient and willing to explain complex topics simply
- Honest about things you're unsure about

Feel free to use appropriate emojis and casual language when it fits the conversation, but maintain professionalism. Your goal is to be both helpful and engaging while ensuring users feel comfortable interacting with you."""

# Global state
class BotState:
    def __init__(self):
        self.ignore_bots = True
        self.session: Optional[aiohttp.ClientSession] = None
        self.message_queue = asyncio.Queue()

CONFIG = BotConfig()
STATE = BotState()

# Database connection pooling
class DatabasePool:
    _pools: Dict[str, sqlite3.Connection] = {}

    @staticmethod
    def get_connection(db_name: str) -> sqlite3.Connection:
        if db_name not in DatabasePool._pools:
            DatabasePool._pools[db_name] = sqlite3.connect(db_name, check_same_thread=False)
        return DatabasePool._pools[db_name]

    @staticmethod
    async def close_all():
        for conn in DatabasePool._pools.values():
            conn.close()
        DatabasePool._pools.clear()

# Initialize database
def init_database():
    with DatabasePool.get_connection(CONFIG.DB_NAME) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                channel_id INTEGER,
                user_id INTEGER,
                nickname TEXT,
                content TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()

# Bot setup
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix=CONFIG.PREFIX, intents=intents)

# Utility functions
def get_nickname(member: discord.Member) -> str:
    return member.nick or member.name

async def get_session() -> aiohttp.ClientSession:
    if not STATE.session or STATE.session.closed:
        STATE.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=300),
            headers=CONFIG.HEADERS
        )
    return STATE.session

def print_message_box(title: str, content: str, width: int = 80):
    print("\n" + "=" * width)
    print(f"| {title:<{width-4}} |")
    print("=" * width)
    for line in content.split('\n'):
        print(f"| {line[:width-4]:<{width-4}} |")
    print("=" * width + "\n")

def split_message(content: str, limit: int = 2000) -> List[str]:
    """Split a message into chunks under the specified character limit."""
    if len(content) <= limit:
        return [content]
    
    chunks = []
    current_chunk = ""
    
    for line in content.split('\n'):
        if len(current_chunk) + len(line) + 1 <= limit:
            current_chunk += f"\n{line}" if current_chunk else line
        else:
            if current_chunk:
                chunks.append(current_chunk)
            if len(line) > limit:
                while line:
                    chunks.append(line[:limit])
                    line = line[limit:]
            else:
                current_chunk = line
    
    if current_chunk:
        chunks.append(current_chunk)
    
    return [chunk.strip() for chunk in chunks if chunk.strip()]

# Database operations
def save_message(channel_id: int, user_id: int, nickname: str, content: str):
    conn = DatabasePool.get_connection(CONFIG.DB_NAME)
    conn.execute(
        'INSERT INTO messages (channel_id, user_id, nickname, content) VALUES (?, ?, ?, ?)',
        (channel_id, user_id, nickname, content)
    )
    conn.commit()

def get_channel_history(channel_id: int) -> List[Dict[str, str]]:
    conn = DatabasePool.get_connection(CONFIG.DB_NAME)
    cursor = conn.execute(
        'SELECT nickname, content FROM messages WHERE channel_id = ? ORDER BY timestamp ASC LIMIT ?',
        (channel_id, CONFIG.HISTORY_LIMIT)
    )
    return [{"role": "user", "content": f"{nick}: {content}"}
            for nick, content in cursor.fetchall()
            if "messages have been cleared" not in content]

def clear_messages(channel_id: int, user_id: Optional[int] = None):
    conn = DatabasePool.get_connection(CONFIG.DB_NAME)
    query = 'DELETE FROM messages WHERE channel_id = ?'
    params = [channel_id]
    if user_id:
        query += ' AND user_id = ?'
        params.append(user_id)
    conn.execute(query, params)
    conn.commit()

# Message processing
async def process_message(message: discord.Message, data: dict):
    """Process a single message and generate/send AI response."""
    try:
        channel_history = get_channel_history(message.channel.id)
        user_nick = get_nickname(message.author)
        
        data["messages"] = [
            {"role": "system", "content": CONFIG.PERSONALITY},
            *channel_history,
            {"role": "user", "content": f"{user_nick}: {message.content}"}
        ]

        async with (await get_session()).post(CONFIG.API_URL, json=data) as resp:
            if resp.status != 200:
                print(f"API Error: {await resp.text()}")
                return
            
            response_data = await resp.json()
            content = response_data['message']['content']

            # Handle <think> tags
            thought = ""
            if "<think>" in content:
                parts = content.split("</think>") if "</think>" in content else content.split("<think>")
                thought = parts[0].replace("<think>", "").strip()
                content = parts[1].strip() if len(parts) > 1 else ""
                
                if thought:
                    if aithoughts := discord.utils.get(message.guild.channels, name='aithoughts'):
                        thought_chunks = split_message(f"**Thought about {user_nick}'s message:**\n{thought}")
                        for chunk in thought_chunks:
                            await aithoughts.send(chunk)
                    print_message_box("AI Thought", thought)

            # Save and send response
            if content and not content.isspace():
                save_message(message.channel.id, bot.user.id, CONFIG.MODEL, content)
                print_message_box(f"Response from {CONFIG.MODEL}", content)
                
                message_chunks = split_message(content)
                for chunk in message_chunks:
                    try:
                        await message.channel.send(chunk)
                    except discord.errors.HTTPException as e:
                        print(f"Failed to send chunk: {str(e)}")
                        print(f"Chunk length: {len(chunk)}")
                        print(f"Chunk content: {chunk[:100]}...")

    except Exception as e:
        print(f"Message processing error: {str(e)}")

async def process_queue():
    while True:
        try:
            batch = []
            for _ in range(CONFIG.BATCH_SIZE):
                if not STATE.message_queue.empty():
                    batch.append(await STATE.message_queue.get())
                await asyncio.sleep(0.01)

            if batch:
                await asyncio.gather(*(process_message(msg, data) for msg, data in batch))
                for _ in batch:
                    STATE.message_queue.task_done()
                    
        except Exception as e:
            print(f"Queue processing error: {str(e)}")
        await asyncio.sleep(0.1)

# Events
@bot.event
async def on_ready():
    print(f'=Logged in as {bot.user.name} ({bot.user.id})= Bot Ready!')
    bot.loop.create_task(process_queue())
    init_database()

@bot.event
async def on_message(message: discord.Message):
    if message.author == bot.user or message.channel.name != "gpt":
        return

    if message.content.startswith(CONFIG.PREFIX):
        await bot.process_commands(message)
        return

    if STATE.ignore_bots and message.author.bot:
        return

    async with message.channel.typing():
        thought = ""
        content = message.content
        if "<think>" in content:
            parts = content.split("</think>") if "</think>" in content else content.split("<think>")
            thought = parts[0].replace("<think>", "").strip()
            content = parts[1].strip() if len(parts) > 1 else ""
            if thought:
                print_message_box(f"Thought from {message.author.display_name}", thought)

        if content:
            save_message(message.channel.id, message.author.id, get_nickname(message.author), content)
            data = {"model": CONFIG.MODEL, "messages": [], "stream": False}
            content_chunks = split_message(content)
            for chunk in content_chunks:
                data_copy = data.copy()
                data_copy["messages"] = [{"role": "user", "content": chunk}]
                await STATE.message_queue.put((message, data_copy))

    await bot.process_commands(message)

# Commands
@bot.command()
@commands.check(lambda ctx: ctx.author == ctx.guild.owner)
async def clearall(ctx):
    clear_messages(ctx.channel.id)
    await ctx.send("Channel message history cleared.")

@bot.command()
async def clearme(ctx):
    clear_messages(ctx.channel.id, ctx.author.id)
    await ctx.send("Your message history cleared.")

@bot.command()
@commands.is_owner()
async def hinged(ctx):
    STATE.ignore_bots = True
    while not STATE.message_queue.empty():
        await STATE.message_queue.get()
    await ctx.send("Now ignoring bot messages.")

@bot.command()
@commands.is_owner()
async def unhinged(ctx):
    STATE.ignore_bots = False
    await ctx.send("Now processing bot messages.")

@bot.command()
@commands.has_permissions(administrator=True)
async def setmodel(ctx):
    models = subprocess.run(['ollama', 'list'], capture_output=True, text=True).stdout.split('\n')[1:]
    models = [m.split()[0] for m in models if m.strip()]
    
    select = Select(
        placeholder="Choose a model",
        options=[discord.SelectOption(label=m, value=m, default=m == CONFIG.MODEL) for m in models]
    )
    
    async def callback(interaction):
        CONFIG.MODEL = select.values[0]
        await interaction.message.delete()
        await interaction.response.send_message(f"Model set to: {CONFIG.MODEL}")
        
    select.callback = callback
    await ctx.send("Select a model:", view=View().add_item(select))

# Cleanup
@bot.event
async def close():
    if STATE.session and not STATE.session.closed:
        await STATE.session.close()
    await DatabasePool.close_all()

if __name__ == "__main__":
    os.system('cls' if os.name == 'nt' else 'clear')
    print("""
                                                               
     ╔═══════════════════════════════════════════════╗         
     ║           Ollama Chat Bot for Discord         ║         
     ║                    Version 0.9                ║         
     ╚═══════════════════════════════════════════════╝         
                                                                
     GitHub: @DevianceLe                              
     X.com:  @DevianceLe       
     Greetz: @WWelna @TexSantos @SuperNETS
                                    
    """)
    bot.run(CONFIG.TOKEN)