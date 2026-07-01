import discord
import dotenv
import os

dotenv.load_dotenv()
token = str(os.getenv("TOKEN"))
client = discord.Bot()


@client.slash_command(name="stats", description="venten all-time stats")
async def stats(ctx: discord.ApplicationContext):
    await ctx.respond("ibra: 1 second atleast...")


client.run(token)
