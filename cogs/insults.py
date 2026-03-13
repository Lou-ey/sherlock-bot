from cogs.facts import Facts
from discord.ext import commands
import random
import os
import json

class Insults(commands.Cog):
    def __init__(self, bot, facts_cog: Facts):
        self.bot = bot
        self.facts_cog = facts_cog
        self.insults_file = "api/insults.json"

    def load_insults(self):
        if os.path.exists(self.insults_file):
            with open(self.insults_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    @commands.command()
    async def insult(self, ctx, *, args=None):
        global name
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send("❌ Tens de estar num canal de voz para usar este comando.")
            return

        insults = self.load_insults()
        print(insults)

        insult = random.choice(insults)

        connected_members = [m for m in ctx.author.voice.channel.members if m != ctx.bot.user]

        member = None
        custom_insult = None

        if args:
            if ctx.message.mentions:
                member = ctx.message.mentions[0]
                custom_insult = args.replace(str(member.mention), "").strip()
                if not custom_insult:
                    custom_insult = insult
            else:
                custom_insult = args
        else:
            if connected_members:
                member = random.choice(connected_members)
                custom_insult = random.choice(insults)
            else:
                await ctx.send("❌ Não há outros membros no canal de voz para insultar.")
                return

        if member and custom_insult:
            formatted_insult = f"{member.display_name}, ||{custom_insult}||"
        elif member:
            formatted_insult = f"{member.display_name}, ||{insult}||"
        else:
            formatted_insult = f"||{custom_insult or insult}||"

        '''if member:
            random_member = member
            name = random_member
        elif member is None and connected_members:
            random_member = random.choice(connected_members)
            name = random_member.name

        if custom_insult:
            insult = custom_insult
        else:
            insult = random.choice(insults)'''

        #formatted_insult = f"{name}, ||{insult}||"
        print(f"💬 {formatted_insult}")

        await ctx.send(f"💢 {formatted_insult}")
        await self.facts_cog.speak_text(ctx.author.voice.channel, formatted_insult)

    @commands.command()
    async def add_insult(self, ctx, *, insult_text: str):
        insults = self.load_insults()

        with open(self.insults_file, "r", encoding="utf-8") as f:
            json.dump(insults, f, ensure_ascii=False, indent=2)

        await ctx.send(f"✅ Insult Added: ||{insult_text}||")

async def setup(bot):
    facts_cog = bot.get_cog("Facts")
    await bot.add_cog(Insults(bot, facts_cog))