import asyncio
import datetime
import os
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

        self.daily_fact_loop.start()

    def cog_unload(self):
        self.daily_fact_loop.cancel()
        asyncio.create_task(self.session.close())

    @tasks.loop(time=[datetime.time(hour=22, minute=0, tzinfo=zoneinfo.ZoneInfo("Europe/Lisbon"))])
    async def daily_fact_loop(self):
        print(f"⏰ Hour reached: {self.exec_hour}. Executing...")
        await self.tell_fact()

    @daily_fact_loop.before_loop
    async def before_daily_fact(self):
        await self.bot.wait_until_ready()
        print("✅ Fact loop is active and waiting for the scheduled time...")

        time_until_target = self.target_time.hour * 3600 + self.target_time.minute * 60 - (datetime.datetime.now(self.tz).hour * 3600 + datetime.datetime.now(self.tz).minute * 60)
        if time_until_target < 0:
            time_until_target += 24 * 3600  # add 24 hours in seconds
        print(f"⏳ Time until first execution: {time_until_target // 3600}h {(time_until_target % 3600) // 60}m")

        now = datetime.datetime.now(self.tz)
        if now.hour >= 22:
            today_str = now.strftime("%d-%m-%Y")
            async with self.session.get(f"http://localhost:6000/fact/{today_str}") as resp:
                if resp.status == 404:
                    print("⚠️ The bot started after the scheduled time and today's fact has not been counted. Catching up now...")
                    await self.tell_fact()
                else:
                    print("ℹ️ Today's fact has already been counted. No need to catch up.")

    async def get_fact(self, day_or_date=None):
        url = "http://localhost:6000/fact"
        if day_or_date:
            url = f'{url}/{day_or_date}'

        try:
            async with self.session.get(url) as resp:
                if resp.status == 200:
                    return await resp.json()
        except Exception as e:
            print("❌ Error fetching fact from API.")
        return None

    async def speak_text(self, channel, text):
        tts = gTTS(text, lang='pt', tld='pt')
        tts.save("temp.mp3")
        vc = channel.guild.voice_client
        try:
            #if vc is None:
            vc = await channel.connect()
            if vc.channel.id != channel.id:
                await vc.move_to(channel)
            vc.play(discord.FFmpegPCMAudio("temp.mp3"), after=lambda e: print(f'Reprodução concluída: {e}'))
            while vc.is_playing():
                await asyncio.sleep(1)
            await vc.disconnect()
        except Exception as e:
            print(f"❌ Erro no TTS: {e}")
            if vc and vc.is_connected():
                await vc.disconnect()
        finally:
            if os.path.exists("temp.mp3"):
                os.remove("temp.mp3")

    async def tell_fact(self):
        channel = self.bot.get_channel(self.voice_channel_id)

        if not channel or not isinstance(channel, discord.VoiceChannel):
            print("❌ Canal de voz não encontrado.")
            return

        data = await self.get_fact()
        if not data:
            return

        # A API envia o dia exato
        fact_text = data.get("fact_text") or data.get("fact")
        day = data.get("day")

        frase = f'Facto interessante, dia {day}. {fact_text}'

        print(f"🔊 A contar o facto para o dia {day}: {fact_text}")
        await self.speak_text(channel, frase)

    @commands.command()
    async def fact_now(self, ctx):
        await self.tell_fact()
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


async def setup(bot):
    voice_channel_id = os.getenv("VOICE_CHANNEL_ID")
    exec_hour = os.getenv("EXEC_HOUR") or "22:00"
    await bot.add_cog(Facts(bot, int(voice_channel_id), exec_hour))