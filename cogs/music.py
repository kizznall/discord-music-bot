import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta
import re
import asyncio
import yt_dlp

class Track:
    def __init__(self, info, requester=None):
        self.info = info
        self.requester = requester
        self.title = info.get('title', 'Unknown')
        self.url = info.get('webpage_url', info.get('url'))
        self.stream_url = None

class MusicCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queue = []
        self.current_track = None
        self.voice_client = None
        self.last_activity = datetime.now()
        self.check_inactivity.start()

    def cog_unload(self):
        self.check_inactivity.cancel()

    @tasks.loop(seconds=60)
    async def check_inactivity(self):
        if self.voice_client and (datetime.now() - self.last_activity).seconds > 300:  # 5 minutes
            await self.voice_client.disconnect()
            self.voice_client = None

    def update_activity(self):
        self.last_activity = datetime.now()

    async def ensure_voice_client(self, ctx):
        try:
            channel = self.bot.get_channel(int(self.bot.config['voice_channel_id']))
            if not channel:
                await ctx.send("❌ Voice channel not found!")
                return False

            # If already connected to the right channel
            if self.voice_client and self.voice_client.is_connected():
                if self.voice_client.channel.id == channel.id:
                    return True
                # If connected to wrong channel, disconnect first
                await self.voice_client.disconnect()
                self.voice_client = None

            # Connect to voice channel
            self.voice_client = await channel.connect(timeout=20.0)
            return True

        except discord.ClientException as e:
            await ctx.send(f"❌ Failed to connect: {str(e)}")
            return False
        except Exception as e:
            print(f"Voice connection error: {str(e)}")
            await ctx.send("❌ Could not connect to voice channel!")
            return False

    async def get_track_info(self, url):
        try:
            info = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.bot.yt_dlp.extract_info(url, download=False)
            )
            if info and info.get('url'):
                info['stream_url'] = info['url']
            elif info and info.get('formats'):
                # Get the best audio format
                formats = info['formats']
                audio_formats = [f for f in formats if f.get('acodec') != 'none']
                if audio_formats:
                    info['stream_url'] = audio_formats[0]['url']
            return info
        except Exception as e:
            print(f"Error getting track info: {str(e)}")
            return None

    @commands.command(name='play')
    async def play(self, ctx, *, query: str):
        if not self.bot.config.get('public_access', False) and not self.bot.is_admin(ctx.author):
            await ctx.send("❌ Only admins can use this bot!")
            return

        await ctx.send("🔍 Searching...")

        # Connect to voice first
        if not await self.ensure_voice_client(ctx):
            return

        try:
            # Handle YouTube video ID format
            if re.match(r'^[a-zA-Z0-9_-]{11}$', query):
                query = f'https://youtube.com/watch?v={query}'

            # Get track info
            info = await self.get_track_info(query)
            if not info:
                await ctx.send("❌ Could not find track!")
                return

            if not info.get('stream_url'):
                await ctx.send("❌ Could not get audio stream!")
                return

            # Create track and add to queue
            track = Track(info, ctx.author)
            track.stream_url = info['stream_url']
            self.queue.append(track)
            await ctx.send(f"✅ Added track: {track.title}")

            # Start playing if not already playing
            if not self.voice_client.is_playing():
                await self.play_next()

        except Exception as e:
            print(f"Error in play command: {str(e)}")
            await ctx.send(f"❌ An error occurred: {str(e)}")

    async def play_next(self):
        if not self.queue or not self.voice_client:
            self.current_track = None
            return

        try:
            self.current_track = self.queue.pop(0)
            
            # If we don't have a stream URL, get fresh track info
            if not self.current_track.stream_url:
                info = await self.get_track_info(self.current_track.url)
                if not info or not info.get('stream_url'):
                    print("Could not get track stream URL")
                    await self.play_next()
                    return
                self.current_track.stream_url = info['stream_url']

            # Create FFmpeg audio source
            try:
                audio = discord.FFmpegPCMAudio(
                    self.current_track.stream_url,
                    **self.bot.ffmpeg_options
                )
                audio = discord.PCMVolumeTransformer(audio, volume=1.0)
            except Exception as e:
                print(f"Error creating audio source: {str(e)}")
                await self.play_next()
                return

            def after_playing(error):
                if error:
                    print(f"Error after playing: {str(error)}")
                asyncio.run_coroutine_threadsafe(self.play_next(), self.bot.loop)

            # Play the audio
            self.voice_client.play(audio, after=after_playing)
            self.update_activity()

        except Exception as e:
            print(f"Error in play_next: {str(e)}")
            await self.play_next()

    @commands.command(name='skip')
    async def skip(self, ctx):
        if not self.voice_client or not self.voice_client.is_playing():
            await ctx.send("❌ Nothing is playing!")
            return

        self.voice_client.stop()
        await ctx.send("⏭️ Skipped!")

    @commands.command(name='queue')
    async def show_queue(self, ctx):
        if not self.queue and not self.current_track:
            await ctx.send("Queue is empty!")
            return

        embed = discord.Embed(title="Music Queue", color=discord.Color.blue())
        
        if self.current_track:
            requester = self.current_track.requester.name if self.current_track.requester else "Unknown"
            embed.add_field(
                name="Now Playing",
                value=f"{self.current_track.title}\nRequested by: {requester}",
                inline=False
            )

        queue_text = ""
        for i, track in enumerate(self.queue[:10], 1):
            requester = track.requester.name if track.requester else "Unknown"
            queue_text += f"{i}. {track.title} (by {requester})\n"

        if queue_text:
            embed.add_field(name="Up Next", value=queue_text, inline=False)
            if len(self.queue) > 10:
                embed.add_field(name="", value=f"...and {len(self.queue) - 10} more tracks", inline=False)

        await ctx.send(embed=embed)

    @commands.command(name='clear')
    async def clear_queue(self, ctx):
        if not self.bot.is_admin(ctx.author):
            await ctx.send("❌ Only admins can clear the queue!")
            return

        self.queue.clear()
        if self.voice_client and self.voice_client.is_playing():
            self.voice_client.stop()
        self.current_track = None
        await ctx.send("🧹 Queue cleared and playback stopped!")

    @commands.command(name='deleteall', aliases=['da'])
    async def delete_all(self, ctx):
        if not self.bot.is_admin(ctx.author):
            await ctx.send("❌ Only admins can delete all!")
            return

        self.queue.clear()
        if self.voice_client:
            if self.voice_client.is_playing():
                self.voice_client.stop()
            await self.voice_client.disconnect()
            self.voice_client = None
        self.current_track = None
        await ctx.send("💥 Deleted all tracks, stopped playback, and disconnected!")

    @commands.command(name='stop')
    async def stop(self, ctx):
        if not self.bot.is_admin(ctx.author):
            await ctx.send("❌ Only admins can stop the bot!")
            return

        if self.voice_client:
            await self.voice_client.disconnect()
            self.voice_client = None
            self.queue.clear()
            self.current_track = None
            await ctx.send("⏹️ Stopped and disconnected!")

async def setup(bot):
    await bot.add_cog(MusicCog(bot))
