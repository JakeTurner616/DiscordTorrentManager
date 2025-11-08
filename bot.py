#!/usr/bin/env python3
"""
Discord Torrent Manager Bot
---------------------------
A bot for managing torrent downloads via qBittorrent, including searching and downloading torrents.

Requirements:
- Python 3.10+
- Discord bot Token
- qBittorrent + Web API enabled
- Completed config.ini file with bot token, guild ID, and qBittorrent information
"""

import sys
import discord
from discord import Option, ApplicationContext
from discord.ext import commands
import requests
import configparser
import asyncio
import humanize
import logging
from urllib.parse import parse_qsl, urlencode
from requests.exceptions import ConnectionError
from qbittorrent.client import LoginRequired

# -------- CONFIGURATION -------- #

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

config = configparser.ConfigParser()
config.read("config.ini")

try:
    bot_token = config.get("Bot", "token")
    raw_guild_ids = config.get("Bot", "guild_id")
    qb_host = config.get("qbit", "host")
    qb_user = config.get("qbit", "user")
    qb_pass = config.get("qbit", "pass")
    guild_ids = [int(g.strip()) for g in raw_guild_ids.split(",")]
except Exception as e:
    logger.error("Configuration error: %s", e)
    sys.exit(1)

# -------- MAGNET TRIMMER -------- #

def trim_magnet(magnet_link: str, max_trackers: int = 7, max_len: int = 1024) -> str:
    """
    Safely trims magnet links for Discord embeds:
    - Keeps only top `max_trackers` trackers.
    - Ensures final string is <= max_len characters.
    """
    if not magnet_link.startswith("magnet:?"):
        return magnet_link

    try:
        # Parse magnet query params
        base, query = magnet_link.split("?", 1)
        params = parse_qsl(query)

        infohash_part = [p for p in params if p[0] in ("xt", "dn")]
        trackers = [p for p in params if p[0] == "tr"]
        others = [p for p in params if p[0] not in ("xt", "dn", "tr")]

        limited_trackers = trackers[:max_trackers]
        new_params = infohash_part + limited_trackers + others
        trimmed = f"{base}?{urlencode(new_params, doseq=True)}"

        if len(trimmed) > max_len:
            trimmed = trimmed[:max_len - 3] + "..."

        return trimmed
    except Exception as e:
        logger.warning("Failed to trim magnet link: %s", e)
        return magnet_link[:max_len - 3] + "..."

# -------- QBITTORRENT SESSION -------- #

class QbitSession:
    def __init__(self, host, user, password):
        self.host = host.rstrip("/")
        self.user = user
        self.password = password
        self.session = requests.Session()
        self.session.headers.update({
            "Referer": self.host,
            "Origin": self.host,
            "User-Agent": "Mozilla/5.0 (DiscordBot)"
        })

    def login(self):
        try:
            r = self.session.post(
                f"{self.host}/api/v2/auth/login",
                data={"username": self.user, "password": self.password},
                timeout=10
            )
            if r.status_code == 200:
                logger.info("Authenticated with qBittorrent.")
            else:
                logger.error("Login failed: %s %s", r.status_code, r.text)
        except Exception as e:
            logger.error("Login exception: %s", e)

    def ensure(self):
        try:
            r = self.session.get(f"{self.host}/api/v2/app/version", timeout=5)
            if r.status_code != 200:
                self.login()
        except Exception:
            self.login()

    def download(self, magnet, category):
        """Add a torrent via magnet link with proper category."""
        self.ensure()
        try:
            r = self.session.post(
                f"{self.host}/api/v2/torrents/add",
                data={"urls": magnet, "category": category.lower()},
                timeout=10
            )
            if r.status_code == 200:
                logger.info("Torrent added to qBittorrent under %s", category)
            else:
                logger.error("Add failed: %s %s", r.status_code, r.text)
        except Exception as e:
            logger.error("Send error: %s", e)

# -------- INIT -------- #

qbit = QbitSession(qb_host, qb_user, qb_pass)
qbit.login()

# -------- DISCORD BOT -------- #

intents = discord.Intents.default()
intents.reactions = True
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
bot.remove_command("help")

emoji_list = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣']
API_URL = 'http://127.0.0.1:5000'

# -------- PROGRESS HANDLER -------- #

async def handle_magnet_download(channel, magnet_link, category):
    info_url = f"{API_URL}/infoglobal"

    try:
        qbit.download(magnet_link, category)
        start_embed = discord.Embed(
            title="Torrent Added",
            description=f"Category: **{category}**\nFetching progress...",
            color=discord.Color.green()
        )
        await channel.send(embed=start_embed)

        progress_embed = discord.Embed(
            title="Torrent Download in Progress",
            description=f"Magnet: `{trim_magnet(magnet_link)}`",
            color=discord.Color.blurple()
        )
        msg = await channel.send(embed=progress_embed)

        while True:
            try:
                resp = requests.get(info_url, timeout=10)
                torrents = resp.json()
            except Exception as e:
                logger.error("infoglobal fetch failed: %s", e)
                await asyncio.sleep(5)
                continue

            if not torrents:
                await asyncio.sleep(5)
                continue

            t = torrents[0]
            state = t.get("state", "Unknown")
            size = t.get("size", 0)
            downloaded = t.get("downloaded", 0)
            eta = t.get("eta", 0)
            dlspeed = t.get("dlspeed", 0)
            seeds = t.get("num_seeds", 0)
            leeches = t.get("num_leechs", 0)

            pct = (downloaded / size * 100) if size else 0
            eta_str = humanize.naturaldelta(eta)
            spd_str = humanize.naturalsize(dlspeed, binary=True) + "/s"
            bar = "▓" * int(pct // 5) + "░" * (20 - int(pct // 5))

            desc = (
                f"**State:** {state}\n"
                f"**Size:** {humanize.naturalsize(size, binary=True)}\n"
                f"**Downloaded:** {humanize.naturalsize(downloaded, binary=True)} "
                f"({pct:.1f}%)\n"
                f"**ETA:** {eta_str}\n\n"
                f"Progress: **{bar}** ~{spd_str}"
            )
            progress_embed.description = desc
            progress_embed.set_footer(text=f"Seeds: {seeds} • Peers: {leeches}")
            await msg.edit(embed=progress_embed)

            if pct >= 99 or state.lower() in ("seeding", "uploading"):
                done = discord.Embed(
                    title="🎉 Download Complete",
                    description=f"{humanize.naturalsize(size, binary=True)} finished.",
                    color=discord.Color.green()
                )
                await msg.delete()
                await channel.send(embed=done)
                break

            await asyncio.sleep(5)

    except Exception as e:
        logger.error("Progress error: %s", e)
        await channel.send(embed=discord.Embed(
            title="Error",
            description=str(e),
            color=discord.Color.red()
        ))

# -------- COMMANDS -------- #

@bot.slash_command(name="search", description="Search for torrents.", guild_ids=guild_ids)
async def search(ctx: ApplicationContext, query: Option(str, "Specify the search query.", required=True)):
    logger.info("Search query: %s", query)
    await ctx.respond(embed=discord.Embed(title="Searching...", color=discord.Color.blue()), ephemeral=True)

    try:
        r = requests.get(f"{API_URL}/torrents?q={query}", timeout=10)
        results = r.json()

        if not results:
            await ctx.send(embed=discord.Embed(
                title="No Results Found",
                description="Try another search.",
                color=discord.Color.orange()
            ))
            return

        notice = discord.Embed(
            title="⚠️ Provider Notice",
            description="Results come from **1377x.to**; use /magnet for direct control.",
            color=discord.Color.gold()
        )
        await ctx.send(embed=notice)

        for i, res in enumerate(results[:len(emoji_list)]):
            e = discord.Embed(title=res["title"], color=discord.Color.blurple())
            e.add_field(name="Size", value=res["size"], inline=True)
            e.add_field(name="Seeders", value=res["seeders"], inline=True)
            e.add_field(name="Leechers", value=res["leechers"], inline=True)
            e.add_field(name="Date", value=res["date"], inline=True)

            safe_magnet = trim_magnet(res["magnet_link"])
            e.add_field(name="Magnet Link", value=f"```{safe_magnet}```", inline=False)

            m = await ctx.send(embed=e)
            await m.add_reaction(emoji_list[i])

    except Exception as e:
        logger.error("Search error: %s", e)
        await ctx.send(embed=discord.Embed(title="Error", description=str(e), color=discord.Color.red()))


@bot.slash_command(name="magnet", description="Add a magnet link to qBittorrent.", guild_ids=guild_ids)
async def magnet(ctx: ApplicationContext,
                 magnet_link: Option(str, "Specify the magnet link.", required=True),
                 category: Option(str, "Specify the category.", required=True,
                                  choices=["TV", "Movie", "FitGirl Repack"])):
    logger.info("Magnet received for category %s", category)
    await ctx.respond(embed=discord.Embed(
        title="Magnet Accepted",
        description=f"Added to category **{category}**. Monitoring progress...",
        color=discord.Color.green()
    ))
    bot.loop.create_task(handle_magnet_download(ctx.channel, magnet_link, category))

# -------- REACTION HANDLER -------- #

@bot.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return
    msg = reaction.message
    if not msg.embeds or msg.author != bot.user:
        return
    embed = msg.embeds[0]
    if reaction.emoji in emoji_list:
        magnet_field = next((f for f in embed.fields if f.name == "Magnet Link"), None)
        if magnet_field:
            magnet = magnet_field.value.strip("```")
            logger.info("Reaction magnet added by %s", user.name)
            await msg.channel.send(embed=discord.Embed(
                title="Torrent Added via Reaction",
                description="Added to **Movie** category. Fetching progress...",
                color=discord.Color.green()
            ))
            bot.loop.create_task(handle_magnet_download(msg.channel, magnet, "Movie"))

# -------- MAIN -------- #

@bot.event
async def on_ready():
    logger.info("%s is online and ready.", bot.user)
    await bot.change_presence(activity=discord.Game("Torrent Management"))

if __name__ == "__main__":
    try:
        bot.run(bot_token)
    except Exception as e:
        logger.error("Startup error: %s", e)
        sys.exit(1)
else:
    try:
        bot.run(bot_token)
    except Exception as e:
        logger.error("Gunicorn error: %s", e)
        sys.exit(1)
