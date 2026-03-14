import discord
from discord.app_commands import describe
from discord.ext import commands
from dotenv import load_dotenv
import os

load_dotenv()
TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.voice_states = True

client = commands.Bot(command_prefix='?', intents=intents, help_command=None)

green = 0x00FF00
red = 0xFF0000

@client.event
async def on_ready():
    activity = discord.Activity(type=discord.ActivityType.listening, name='?facts')
    await client.change_presence(activity=activity)
    print(f'{client.user} has connected to the following servers:\n')
    for server in client.guilds:
        print(f'- {server.name} (id: {server.id})')

        client.tree.copy_global_to(guild=server) # Copy global commands to the server
        await client.tree.sync(guild=server) # Sync the commands to the server
    print(f'\nCogs loaded:')
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py'):
            await client.load_extension(f'cogs.{filename[:-3]}')
            try:
                print(f'- {filename[:-3]}')
            except Exception as e:
                print(f'Failed to load {filename[:-3]}')
                print(e)

@client.command()
async def help(ctx):
    embed = discord.Embed(
        title="Sherlock Help",
        description="Available Commands",
        color=green
    )
    embed.add_field(name="?fact_now", value="Tells the current fact immediately.", inline=False)
    embed.add_field(name="?prev_fact", value="Tells the previous fact.", inline=False)
    embed.add_field(name="?fact_day <day_or_date>", value="Retrieves the fact for a specific day or date.", inline=False)
    embed.add_field(name="?insult opt[member] opt[custom_insult]", value="Sends an insult to a member or a random member in your voice channel.(opt = optional)", inline=False)
    embed.add_field(name="?add_insult <insult_text>", value="Adds a new insult to the insult list.", inline=False)
    embed.add_field(name="?help", value="Shows this help message.", inline=False)
    embed.set_footer(text="More commands will be added soon!")
    await ctx.send(embed=embed)

client.run(TOKEN)