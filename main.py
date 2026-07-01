import discord
import datetime
import time
import dotenv
import sqlite3
import os

dotenv.load_dotenv()
token = str(os.getenv("TOKEN"))
bot = discord.Bot(intents=discord.Intents.all())
conn = sqlite3.connect("data.db")
cursor = conn.cursor()


cursor.execute(
    "CREATE TABLE IF NOT EXISTS voice_stats (user_id INTEGER, guild_id INTEGER, total_time INTEGER DEFAULT 0, current_streak INTEGER DEFAULT 0, highest_streak INTEGER DEFAULT 0, last_active_date TEXT, PRIMARY KEY (user_id, guild_id))"
)
cursor.execute(
    "CREATE TABLE IF NOT EXISTS active_sessions (user_id INTEGER, guild_id INTEGER, join_timestamp INTEGER, PRIMARY KEY (user_id, guild_id))"
)


@bot.slash_command(
    name="run_sql",
    description="Run SQL command to the database",
    guild_ids=[182534117173362702],
)
async def runsql(ctx: discord.ApplicationContext, query: str):
    if ctx.author.id != 292661827932782592:
        await ctx.respond("sorry, you cant run this command. try neighing 3 times and running this command again")
        return

    try:
        cursor.execute(query)
        if query.strip().upper().startswith("SELECT"):
            results = cursor.fetchall()
            await ctx.respond(f"Results: \n```python\n{results}\n```", ephemeral=True)
        else:
            conn.commit()
            await ctx.respond(f"Successfully executed: `{query}`", ephemeral=True)

    except Exception as e:
        await ctx.respond(f"SQL Error: `{e}`", ephemeral=True)


@bot.slash_command(name="stats", description="All-time voice chat stats")
async def stats(ctx: discord.ApplicationContext):
    cursor.execute(
        "SELECT * FROM voice_stats WHERE user_id = ? AND guild_id = ?",
        (ctx.author.id, ctx.guild_id),
    )
    result = cursor.fetchone()
    if result:
        await ctx.respond(result)
    else:
        await ctx.respond("Failed to fetch stats")


@bot.event
async def on_voice_state_update(member, before, after):
    # joining vc
    if before.channel is None and after.channel is not None:
        guild_id = after.channel.guild.id
        today = datetime.date.today()
        today_str = today.isoformat()

        cursor.execute(
            "INSERT OR IGNORE INTO voice_stats (user_id, guild_id) VALUES (?, ?)",
            (member.id, guild_id),
        )

        cursor.execute(
            "REPLACE INTO active_sessions (user_id, guild_id, join_timestamp) VALUES (?, ?, ?)",
            (member.id, guild_id, int(time.time())),
        )
        conn.commit()

        # check streak
        cursor.execute(
            "SELECT last_active_date FROM voice_stats WHERE user_id = ? AND guild_id = ?",
            (member.id, guild_id),
        )
        result = cursor.fetchone()

        if result and result[0] is not None:
            last_active = datetime.date.fromisoformat(result[0])
            days_since_active = (today - last_active).days

            if days_since_active == 1:
                cursor.execute(
                    "UPDATE voice_stats SET current_streak = current_streak + 1 WHERE user_id = ? AND guild_id = ?",
                    (member.id, guild_id),
                )
            elif days_since_active > 1:
                cursor.execute(
                    "UPDATE voice_stats SET current_streak = 1 WHERE user_id = ? AND guild_id = ?",
                    (member.id, guild_id),
                )
        else:
            cursor.execute(
                "UPDATE voice_stats SET current_streak = 1 WHERE user_id = ? AND guild_id = ?",
                (member.id, guild_id),
            )

        cursor.execute(
            "UPDATE voice_stats SET last_active_date = ? WHERE user_id = ? AND guild_id = ?",
            (today_str, member.id, guild_id),
        )
        conn.commit()

    # leaving vc
    if before.channel is not None and after.channel is None:
        guild_id = before.channel.guild.id

        cursor.execute(
            "SELECT * FROM active_sessions WHERE user_id = ? AND guild_id = ?",
            (member.id, guild_id),
        )
        result = cursor.fetchone()

        if result:
            cursor.execute(
                "UPDATE voice_stats SET total_time = total_time + ? WHERE user_id = ? AND guild_id = ?",
                (int(time.time()) - result[2], member.id, guild_id),
            )

            cursor.execute(
                "DELETE FROM active_sessions WHERE user_id = ? AND guild_id = ?",
                (member.id, guild_id),
            )
            conn.commit()

    # switching channel
    if before.channel is not None and after.channel is not None:
        print(
            f"test: {member.name} switched channel or did some other dumbfuck shit to update state"
        )

# TODO : reset streaks if midnight passes and someone hasnt joined vc in that day
# TODO : on_voice_channel_status_update : track how long each status is being used
# TODO : track each user's vc timer, total stats, etc
# TODO : "frontend" commands

bot.run(token)
