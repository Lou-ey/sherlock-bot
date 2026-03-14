import asyncio
import datetime
import os
from gtts import gTTS
import discord
from discord.ext import commands, tasks
import aiohttp
import random

class Facts(commands.Cog):
    def __init__(self, bot, voice_channel_id: int, exec_hour: str):
        self.bot = bot
        self.voice_channel_id = voice_channel_id
        self.exec_hour = exec_hour
        self.count_file = "fact_day_count.txt"
        self.day_count = self.load_day_count()
        self.bot.loop.create_task(self.fact_loop())

    def load_day_count(self):
        if os.path.exists(self.count_file):
            with open(self.count_file, "r") as f:
                try:
                    return int(f.read().strip())
                except ValueError:
                    return 0
        return 0

    def increment_day_count(self):
        self.day_count += 1
        with open(self.count_file, "w") as f:
            f.write(str(self.day_count))
        return self.day_count


    async def get_fact(self):
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:6000/fact") as resp:
                if resp.status != 200:
                    print("❌ Error fetching fact.")
                    return None
                data = await resp.json()
                return data.get("fact")

    def get_next_exec_time(self):
        now = datetime.datetime.now()
        target_time = datetime.datetime.strptime(self.exec_hour, "%H:%M").replace(
            year=now.year, month=now.month, day=now.day, tzinfo=None
        )
        if target_time < now:
            target_time += datetime.timedelta(days=1)
        return target_time

    async def wait_till_exec_time(self):
        next_time = self.get_next_exec_time()
        delta = (next_time - datetime.datetime.now()).total_seconds()
        hours, remainder = divmod(int(delta), 3600)
        minutes, seconds = divmod(remainder, 60)
        print(f"⏳ Next fact in {hours}h {minutes}m {seconds}s ({next_time.strftime('%H:%M UTC')})")
        await asyncio.sleep(delta)

    @tasks.loop(minutes=24)
    async def fact_loop(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            await self.wait_till_exec_time()
            await self.tell_fact()

    @fact_loop.before_loop
    async def before_fact_loop(self):
        await self.bot.wait_until_ready()

    async def speak_text(self, channel, text):
        tts = gTTS(text, lang='pt')
        tts.save("temp.mp3")
        try:
            vc = await channel.connect()
            vc.play(discord.FFmpegPCMAudio("temp.mp3"), after=lambda e: print(f'Finished playing: {e}'))
            while vc.is_playing():
                await asyncio.sleep(1)
            await vc.disconnect()
        except Exception as e:
            print(f"❌ Error during TTS playback: {e}")
        finally:
            if os.path.exists("temp.mp3"):
                os.remove("temp.mp3")

    async def tell_fact(self):
        channel = self.bot.get_channel(self.voice_channel_id)
        if not channel or not isinstance(channel, discord.VoiceChannel):
            print("❌ Voice channel not found or invalid.")
            return

        fact = await self.get_fact()
        day = self.increment_day_count()

        fact =f'Facto interssante, dia {day}. {fact}'

        if not fact:
            return

        print(f"🔊 Telling fact for day {day}: {fact}")
        await self.speak_text(channel, fact)

    @commands.command()
    async def fact_now(self, ctx):
        await self.tell_fact()
        await ctx.send("✅ Fact told!")

    @commands.command()
    async def prev_fact(self, ctx):
        channel = self.bot.get_channel(self.voice_channel_id)
        if not channel or not isinstance(channel, discord.VoiceChannel):
            await ctx.send("❌ Voice channel not found or invalid.")
            return

        day = self.day_count
        if day <= 1:
            await ctx.send("❌ No previous fact available.")
            return

        previous_day = day

        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://localhost:6000/fact/{previous_day}") as resp:
                if resp.status == 404:
                    await ctx.send(f"❌ No fact found for day {previous_day}.")
                    return
                elif resp.status != 200:
                    await ctx.send("❌ Error fetching previous fact.")
                    return
                data = await resp.json()
                fact = data.get("fact")
                date = data.get("use_date")
                time = data.get("use_time")

        fact = f'Facto interssante anterior, do dia {previous_day} contado no dia {date} às {time}. {fact}'
        await self.speak_text(channel, fact)

    @commands.command()
    async def fact_day(self, ctx, arg):
        api_url = "http://localhost:6000"

        if "/" in arg:
            arg = arg.replace("/", "-")

        if arg.isdigit():
            url = f"{api_url}/fact/{arg}"
            description = f"do dia {arg}"
        else:
            try:
                datetime.datetime.strptime(arg, "%d-%m-%Y")
            except ValueError:
                await ctx.send("❌ Invalid argument. Please provide a day number or a date in DD/MM/YYYY format.")
                return
            url = f"{api_url}/fact/{arg}"
            description = ""

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 404:
                    await ctx.send(f"❌ Não existe facto registado para {description}.")
                    return
                elif resp.status != 200:
                    await ctx.send("❌ Erro ao obter o facto da API.")
                    return

                data = await resp.json()
                fact = data.get("fact")
                date = data.get("use_date")
                time = data.get("use_time")
        description = description.replace("-", "/")
        print(description)
        fact = f'Facto interssante {description}, contado no dia {date} às {time}. {fact}'

        channel = self.bot.get_channel(self.voice_channel_id)
        if not channel or not isinstance(channel, discord.VoiceChannel):
            await ctx.send("❌ Canal de voz não encontrado ou inválido.")
            return

        await self.speak_text(channel, fact)

async def setup(bot):
    voice_channel_id = os.getenv("VOICE_CHANNEL_ID")
    exec_hour = os.getenv("EXEC_HOUR")
    await bot.add_cog(Facts(bot, int(voice_channel_id), exec_hour))