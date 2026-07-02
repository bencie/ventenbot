import discord
from discord.commands import Option
import datetime
import time
import schedule
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
        await ctx.respond(
            "sorry, you cant run this command. try neighing 3 times and running this command again"
        )
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


@bot.slash_command(
    name="run_function",
    description="Run python function",
    guild_ids=[182534117173362702],
)
async def runfunction(ctx: discord.ApplicationContext, code: str):
    if ctx.author.id != 292661827932782592:
        await ctx.respond(
            "sorry, you cant run this command. try neighing 3 times and running this command again"
        )
        return
    try:
        result = eval(code, globals(), locals())
        await ctx.respond(
            f"Executed successfully. Result:\n```python\n{result}\n```", ephemeral=True
        )

    except Exception as e:
        await ctx.respond(f"Error:\n```python\n{e}\n```", ephemeral=True)


def getUserStats(user_id: int, guild_id: int | None):
    cursor.execute(
        "SELECT * FROM voice_stats WHERE user_id = ? AND guild_id = ?",
        (user_id, guild_id),
    )
    return cursor.fetchone()


def initUserVoiceStats(user_id: int, guild_id: int):
    cursor.execute(
        "INSERT OR IGNORE INTO voice_stats (user_id, guild_id) VALUES (?, ?)",
        (user_id, guild_id),
    )
    conn.commit()


def addActiveSession(user_id, guild_id):
    cursor.execute(
        "REPLACE INTO active_sessions (user_id, guild_id, join_timestamp) VALUES (?, ?, ?)",
        (user_id, guild_id, int(time.time())),
    )
    conn.commit()


def streakCheckUpdate(user_id: int, guild_id: int):
    today = datetime.date.today()

    cursor.execute(
        "SELECT last_active_date FROM voice_stats WHERE user_id = ? AND guild_id = ?",
        (user_id, guild_id),
    )
    result = cursor.fetchone()

    if result and result[0] is not None:
        last_active = datetime.date.fromisoformat(result[0])
        days_since_active = (today - last_active).days

        if days_since_active == 1:
            cursor.execute(
                "UPDATE voice_stats SET current_streak = current_streak + 1, highest_streak = MAX(highest_streak, current_streak + 1) WHERE user_id = ? AND guild_id = ?",
                (user_id, guild_id),
            )
            conn.commit()

        # TODO: 1 of these from elif/else are dumb as fuck so it should be refactored
        elif days_since_active > 1:
            cursor.execute(
                "UPDATE voice_stats SET current_streak = 1 WHERE user_id = ? AND guild_id = ?",
                (user_id, guild_id),
            )
            conn.commit()

    else:
        cursor.execute(
            "UPDATE voice_stats SET current_streak = 1 WHERE user_id = ? AND guild_id = ?",
            (user_id, guild_id),
        )
        conn.commit()


def forceRecheckHighestStreak(user_id: int, guild_id: int):
    cursor.execute(
        "UPDATE voice_stats SET highest_streak = MAX(highest_streak, current_streak) WHERE user_id = ? AND guild_id = ?",
        (user_id, guild_id),
    )
    conn.commit()


def updateLastActiveDate(user_id: int, guild_id: int):
    today = datetime.date.today()
    today_str = today.isoformat()
    cursor.execute(
        "UPDATE voice_stats SET last_active_date = ? WHERE user_id = ? AND guild_id = ?",
        (today_str, user_id, guild_id),
    )
    conn.commit()


def removeActiveSession(user_id: int, guild_id: int):
    cursor.execute(
        "DELETE FROM active_sessions WHERE user_id = ? AND guild_id = ?",
        (user_id, guild_id),
    )
    conn.commit()


def increaseTotalTime(user_id: int, guild_id: int):
    cursor.execute(
        "SELECT * FROM active_sessions WHERE user_id = ? AND guild_id = ?",
        (user_id, guild_id),
    )
    result = cursor.fetchone()

    if result:
        cursor.execute(
            "UPDATE voice_stats SET total_time = total_time + ? WHERE user_id = ? AND guild_id = ?",
            (int(time.time()) - result[2], user_id, guild_id),
        )


def getUserRank(user_id: int, guild_id: int):
    cursor.execute(
        "SELECT COUNT(*) + 1 FROM voice_stats WHERE guild_id = ? AND total_time > (SELECT total_time FROM voice_stats WHERE user_id = ? AND guild_id = ?)",
        (guild_id, user_id, guild_id),
    )
    return cursor.fetchone()[0]


def getDaysSinceActive(last_active_str: str | None):
    if not last_active_str:
        return 0

    last_active = datetime.date.fromisoformat(last_active_str)
    today = datetime.date.today()
    return (today - last_active).days


@bot.slash_command(name="stats", description="All-time voice chat stats")
async def stats(
    ctx: discord.ApplicationContext,
    target_user: discord.Member | None = Option(
        discord.Member, "Select a user", required=False, default=None
    ),  # type: ignore
):
    if not ctx.guild_id:
        return await ctx.respond("This command can only be used inside a server.")

    user = target_user or ctx.author
    user_stats = getUserStats(user.id, ctx.guild_id)

    if user_stats:
        (
            user_id,
            guild_id,
            total_time,
            current_streak,
            highest_streak,
            last_active_date,
        ) = user_stats
        minutes, seconds = divmod(total_time, 60)
        hours, minutes = divmod(minutes, 60)
        await ctx.respond(f"""```ansi
{user.name}'s stats:
🕑 [2;34m{hours} hours, {minutes} minutes, {seconds} seconds total voice time[0m
🏆 [2;33m{getUserRank(user_id, guild_id)}. highest total time in voice[0m
🗓️ [2;31m{current_streak} day streak[0m
🎖️ [2;35m{highest_streak} day highest streak[0m
⏳ [2;32m{(datetime.date.today() - datetime.date.fromisoformat(last_active_date)).days} days since last in voice[0m
```""")
    else:
        initUserVoiceStats(user.id, ctx.guild_id)
        user_stats = getUserStats(user.id, ctx.guild_id)
        await ctx.respond(user_stats)


@bot.event
async def on_voice_state_update(member, before, after):
    # joining vc
    if before.channel is None and after.channel is not None:
        guild_id = after.channel.guild.id

        initUserVoiceStats(member.id, guild_id)
        addActiveSession(member.id, guild_id)
        streakCheckUpdate(member.id, guild_id)
        updateLastActiveDate(member.id, guild_id)

    # leaving vc
    if before.channel is not None and after.channel is None:
        guild_id = before.channel.guild.id

        increaseTotalTime(member.id, guild_id)
        removeActiveSession(member.id, guild_id)

    # switching channel
    if before.channel is not None and after.channel is not None:
        print(
            f"dbg: {member.name} switched channel or did some other dumbfuck shit to update state"
        )


# TODO : reset streaks if midnight passes and someone hasnt joined vc in that day
# TODO : on_voice_channel_status_update : track how long each status is being used
# TODO : top total_time stats, make it scrollable so you can view 1-5, 6-10, etc
# TODO : "frontend" commands

bot.run(token)
