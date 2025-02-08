import discord
from discord.ext import commands
import json
import asyncio
import os
from datetime import datetime, timedelta
import yt_dlp

class MusicBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.voice_states = True
        super().__init__(command_prefix='!', intents=intents)
        
        # Load config
        with open('config/config.json') as f:
            self.config = json.load(f)
        
        self.last_activity = datetime.now()
        self.yt_dlp_format_options = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'nocheckcertificate': True,
            'ignoreerrors': False,
            'quiet': True,
            'no_warnings': True,
            'default_search': 'auto',
            'source_address': '0.0.0.0',
            'extract_flat': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'opus',
            }],
        }
        self.ffmpeg_options = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-acodec pcm_s16le -f s16le -ar 48000 -ac 2'
        }
        self.yt_dlp = yt_dlp.YoutubeDL(self.yt_dlp_format_options)
    
    async def setup_hook(self):
        await self.load_extension('cogs.music')
    
    async def on_ready(self):
        print(f'Logged in as {self.user}')
        print('------')

    def is_admin(self, member):
        if str(member.id) in self.config.get('admin_users', []):
            return True
        return any(role.name in self.config.get('admin_roles', []) for role in member.roles)

if __name__ == '__main__':
    bot = MusicBot()
    bot.run(bot.config['token'])
