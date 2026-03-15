import asyncio
import datetime
import os
from gtts import gTTS
import discord
from discord.ext import commands
import aiohttp


class Facts(commands.Cog):
    def __init__(self, bot, voice_channel_id: int, exec_hour: str):
        self.bot = bot
        self.voice_channel_id = voice_channel_id
        self.exec_hour = exec_hour
        self.bot.loop.create_task(self.fact_loop())

    async def get_fact(self):
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:6000/fact") as resp:
                if resp.status != 200:
                    print("❌ Erro ao buscar facto.")
                    return None
                # Devolvemos tudo o que a API manda (fact, day, use_date, use_time)
                return await resp.json()

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
        print(f"⏳ Próximo facto em {hours}h {minutes}m {seconds}s ({next_time.strftime('%H:%M')})")
        await asyncio.sleep(delta)

    # Substituímos o tasks.loop por uma task assíncrona simples
    async def fact_loop(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            await self.wait_till_exec_time()
            await self.tell_fact()

    async def speak_text(self, channel, text):
        tts = gTTS(text, lang='pt')
        tts.save("temp.mp3")
        try:
            vc = await channel.connect()
            vc.play(discord.FFmpegPCMAudio("temp.mp3"), after=lambda e: print(f'Reprodução concluída: {e}'))
            while vc.is_playing():
                await asyncio.sleep(1)
            await vc.disconnect()
        except Exception as e:
            print(f"❌ Erro no TTS: {e}")
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
        fact_text = data.get("fact")
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
    exec_hour = os.getenv("EXEC_HOUR")
    await bot.add_cog(Facts(bot, int(voice_channel_id), exec_hour))