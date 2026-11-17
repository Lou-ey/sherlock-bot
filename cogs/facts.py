import asyncio
import datetime
import os
import uuid

from gtts import gTTS
import discord
from discord.ext import commands, tasks
import aiohttp
import zoneinfo

class Facts(commands.Cog):
    def __init__(self, bot, voice_channel_id: int, exec_hour: str):
        self.bot = bot
        self.voice_channel_id = voice_channel_id
        self.exec_hour = exec_hour
        self.tz = zoneinfo.ZoneInfo("Europe/Lisbon")
        self.session = aiohttp.ClientSession()

        h, m = map(int, exec_hour.split(":"))
        self.target_time = datetime.time(hour=h, minute=m, tzinfo=self.tz)

        self.daily_fact_loop.change_interval(time=self.target_time)
        self.daily_fact_loop.start()

    def cog_unload(self):
        self.daily_fact_loop.cancel()
        asyncio.create_task(self.session.close())

    @tasks.loop()
    async def daily_fact_loop(self):
        print(f"Hour reached: {self.exec_hour}. Executing...")
        await self.tell_fact()

    @daily_fact_loop.before_loop
    async def before_daily_fact(self):
        await self.bot.wait_until_ready()
        print("Fact loop is active and waiting for the scheduled time...")

        now = datetime.datetime.now(self.tz)

        if now.time() >= self.target_time:
            today_str = now.strftime("%d-%m-%Y")
            try:
                async with self.session.get(f"http://localhost:6000/fact/{today_str}") as resp:
                    if resp.status == 404:
                        print("⚠️ The bot started after the scheduled time and today's fact has not been counted. Catching up now...")
                        await self.tell_fact()
                    else:
                        print("ℹ️ Today's fact has already been counted. No need to catch up.")
            except Exception as e:
                print(f"Error fetching today's fact: {e}")

    async def get_fact(self, day_or_date=None):
        url = "http://localhost:6000/fact"
        if day_or_date:
            url = f'{url}/{day_or_date}'

        try:
            async with self.session.get(url) as resp:
                if resp.status == 200:
                    return await resp.json()
        except Exception as e:
            print(f"Error fetching fact from API: {e}")
        return None

    async def speak_text(self, channel, text):
        temp_file = f"temp_{uuid.uuid4().hex}.mp3"

        def generate_tts():
            tts = gTTS(text, lang='pt', tld='pt')
            tts.save(temp_file)

        await asyncio.to_thread(generate_tts)

        vc = channel.guild.voice_client
        try:
            if vc is None:
                vc = await channel.connect()
            if vc.channel.id != channel.id:
                await vc.move_to(channel)

            await asyncio.sleep(1.5)

            vc.play(discord.FFmpegPCMAudio(temp_file, options='-vn -b:a 128k'))

            while vc.is_playing():
                await asyncio.sleep(1)

            return True

        except Exception as e:
            print(f"Error in TTS: {e}")
            if vc and vc.is_connected():
                await vc.disconnect()

            return False
        finally:
            if vc and vc.is_connected():
                await vc.disconnect()

            if os.path.exists(temp_file):
                os.remove(temp_file)

    async def tell_fact(self, force=False):
        channel = self.bot.get_channel(self.voice_channel_id)

        if not channel or not isinstance(channel, discord.VoiceChannel):
            print("Canal de voz não encontrado.")
            return

        if not force:
            now = datetime.datetime.now(self.tz)
            today_str = now.strftime("%d-%m-%Y")
            async with self.session.get(f"http://localhost:6000/fact/{today_str}") as resp:
                if resp.status == 200:
                    print("ℹ️ Today's fact has already been counted. Skipping...")
                    return

        data = await self.get_fact()
        if not data:
            return

        fact_text = data.get("fact_text")
        fact_id = data.get("id")
        frase = f"Facto interessante. {fact_text}"

        print(f"Preparing to tell the fact: {fact_text}")

        success = await self.speak_text(channel, frase)

        if success:
            mark_payload = {"id": fact_id, "fact_text": fact_text}
            async with self.session.post("http://localhost:6000/fact/mark", json=mark_payload) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    print(f"Fact marked as used with day {result.get('day')} at {result.get('use_date')} {result.get('use_time')}.")
        else:
            print("Failed to play the fact in the voice channel.")

    @commands.command()
    async def fact_now(self, ctx):
        await self.tell_fact(force=True)
        await ctx.send("✅ Facto contado!")

    @commands.command()
    async def fact_day(self, ctx, arg):
        api_url = "http://localhost:6000"

        if "/" in arg:
            arg = arg.replace("/", "-")

        url = f"{api_url}/fact/{arg}"
        print(url)

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 404:
                    await ctx.send(f"❌ Não existe facto registado para esse dia ou data.")
                    return
                elif resp.status != 200:
                    await ctx.send("❌ Erro ao obter o facto da API.")
                    return

                data = await resp.json()
                fact = data.get("fact_text")
                date = data.get("use_date")
                time = data.get("use_time")
                day = data.get("day")

        frase = f'Facto interessante anterior do dia {day}, contado no dia {date} às {time}. {fact}'

        channel = self.bot.get_channel(self.voice_channel_id)
        if not channel or not isinstance(channel, discord.VoiceChannel):
            await ctx.send("❌ Canal de voz não encontrado.")
            return

        await self.speak_text(channel, frase)

    @commands.command()
    async def prev_fact(self, ctx):
        api_url = "http://localhost:6000/fact/previous"

        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as resp:
                if resp.status == 404:
                    await ctx.send("❌ Não existe facto anterior.")
                    return

                data = await resp.json()

        fact = data["fact_text"]
        date = data["use_date"]
        time = data["use_time"]
        day = data["day"]

        frase = f"Facto interessante anterior do dia {day}, contado no dia {date} às {time}. {fact}"

        channel = self.bot.get_channel(self.voice_channel_id)

        if not channel or not isinstance(channel, discord.VoiceChannel):
            await ctx.send("❌ Canal de voz não encontrado.")
            return

        await self.speak_text(channel, frase)


async def setup(bot):
    voice_channel_id = os.getenv("VOICE_CHANNEL_ID")
    exec_hour = os.getenv("EXEC_HOUR") or "22:00"
    await bot.add_cog(Facts(bot, int(voice_channel_id), exec_hour))