import discord
from discord.ext import commands
from dotenv import load_dotenv
import os

load_dotenv()
TOKEN = os.getenv("TOKEN")

intents = discord.Intents.all()
intents.members = True
intents.message_content = True

client = commands.Bot(command_prefix='?', intents=intents)

green = 0x00FF00
red = 0xFF0000

@client.event
async def on_ready():
    activity = discord.Activity(type=discord.ActivityType.listening, name='!facts')
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

# slash command help
@client.tree.command(name="help", description="Shows help information about the bot")
async def help(ctx):
    help_text = """
    **Available Commands:**
    `?fact_now` - Tells the current fact immediately.
    `?prev_fact` - Tells the previous fact.
    `?fact_day <day_number>` - Tells the fact for the specified day.
    More commands will be added soon!
    """
    await ctx.send(help_text)

client.run(TOKEN)