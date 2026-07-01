import discord
import dotenv
import os

dotenv.load_dotenv()
token = str(os.getenv("TOKEN"))
bot = discord.Bot(intents=discord.Intents.all())

# TODO : on_voice_channel_status_update : track how long each status is being used
# TODO : track each user's vc timer, total stats, etc


@bot.slash_command(name="stats", description="venten all-time stats")
async def stats(ctx: discord.ApplicationContext):
    await ctx.respond("youve been in vc for... 1 second.. atleast., .")


@bot.event
async def on_voice_state_update(member, before, after):
    await member.send(f"testing! hi {member.mention}")


bot.run(token)
