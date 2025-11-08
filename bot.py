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
from qbittorrent import Client
import asyncio
import humanize
import logging
import os
from requests.exceptions import ConnectionError
from qbittorrent.client import LoginRequired

# -------- CONFIGURATION SETUP -------- #

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

# -------- SESSION-BASED CLIENT WRAPPER -------- #

class QbitSession:
    """Cookie-based qBittorrent session manager to maintain auth persistently."""
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
        """Explicitly log in and store the SID cookie."""
        try:
            resp = self.session.post(
                f"{self.host}/api/v2/auth/login",
                data={"username": self.user, "password": self.password},
                timeout=10
            )
            if resp.status_code == 200:
                logger.info("Authenticated with qBittorrent Web API.")
            else:
                logger.error("Failed qBittorrent login: %s %s", resp.status_code, resp.text)
        except Exception as e:
            logger.error("Login exception: %s", e)

    def ensure(self):
        """Ensure the session is still valid; relog if needed."""
        try:
            test = self.session.get(f"{self.host}/api/v2/app/version", timeout=5)
            if test.status_code != 200:
                self.login()
        except Exception:
            self.login()

    def download(self, magnet, category):
        """Add a torrent via magnet link."""
        self.ensure()
        try:
            resp = self.session.post(
                f"{self.host}/api/v2/torrents/add",
                data={"urls": magnet, "category": category.lower()},
                timeout=10
            )
            if resp.status_code == 200:
                logger.info("Torrent added successfully.")
            else:
                logger.error("Failed to add torrent: %s %s", resp.status_code, resp.text)
        except Exception as e:
            logger.error("Error sending torrent: %s", e)


# -------- INIT SESSION -------- #

qbit = QbitSession(qb_host, qb_user, qb_pass)
qbit.login()

# -------- DISCORD BOT SETUP -------- #

intents = discord.Intents.default()
intents.reactions = True
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
bot.remove_command("help")

download_in_progress = False
emoji_list = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣']
API_URL = 'http://127.0.0.1:5000'

# -------- COMMANDS -------- #

@bot.slash_command(name="search", description="Search for torrents.", guild_ids=guild_ids)
async def search(ctx: ApplicationContext, query: Option(str, "Specify the search query.", required=True)):  # type: ignore
    logger.info("Received search request with query: %s", query)
    embed = discord.Embed(title="Search Initiated", description="Searching...", color=discord.Color.blue())
    await ctx.respond(embed=embed, ephemeral=True)

    try:
        response = requests.get(f"{API_URL}/torrents?q={query}", timeout=10)
        results = response.json()

        if not results:
            await ctx.send(embed=discord.Embed(
                title="No Results Found",
                description="Try another query.",
                color=discord.Color.orange()
            ))
            return

        # ⚠️ Upstream warning message
        warning_embed = discord.Embed(
            title="⚠️ /Search Provider Notice",
            description=(
                "Results are currently fetched from **https://www.1377x.to**.\n"
                "They may not always work very well or could include wack results.\n"
                "Use /magnet for way more control"
            ),
            color=discord.Color.gold()
        )
        await ctx.send(embed=warning_embed)

        for i, r in enumerate(results[:len(emoji_list)]):
            e = discord.Embed(title=r["title"], color=discord.Color.blue())
            e.add_field(name="Size", value=r["size"], inline=False)
            e.add_field(name="Seeders", value=r["seeders"], inline=False)
            e.add_field(name="Leechers", value=r["leechers"], inline=False)
            e.add_field(name="Date", value=r["date"], inline=False)
            e.add_field(name="Magnet Link", value=f"```{r['magnet_link']}```", inline=False)
            msg = await ctx.send(embed=e)
            await msg.add_reaction(emoji_list[i])
        logger.info("Search results displayed successfully.")

    except Exception as e:
        logger.error("Error during search: %s", e)
        await ctx.send(embed=discord.Embed(title="Error", description=str(e), color=discord.Color.red()))


@bot.slash_command(name="magnet", description="Add a magnet link to qBittorrent.", guild_ids=guild_ids)
async def magnet(ctx: ApplicationContext,
                 magnet_link: Option(str, "Specify the magnet link.", required=True),  # type: ignore
                 category: Option(str, "Specify the category.", required=True, choices=["TV", "Movie", "FitGirl Repack"])):  # type: ignore
    logger.info("Processing magnet: %s", magnet_link[:60])
    qbit.download(magnet_link, category)

    await ctx.respond(embed=discord.Embed(
        title="Torrent Added",
        description=f"Magnet link sent to qBittorrent under category **{category}**.",
        color=discord.Color.green()
    ))


@bot.event
async def on_reaction_add(reaction, user):
    """Handle emoji reactions from search results."""
    if user.bot:
        return
    msg = reaction.message
    if msg.embeds and msg.author == bot.user:
        embed = msg.embeds[0]
        if reaction.emoji in emoji_list:
            magnet_field = next((f for f in embed.fields if f.name == "Magnet Link"), None)
            if magnet_field:
                magnet = magnet_field.value.strip("```")
                logger.info("User %s selected magnet link: %s", user.name, magnet[:60])
                qbit.download(magnet, "Movie")
                await msg.channel.send(embed=discord.Embed(
                    title="Torrent Added via Reaction",
                    description="Your selection was added to qBittorrent.",
                    color=discord.Color.green()
                ))


# -------- MAIN -------- #

@bot.event
async def on_ready():
    logger.info("%s is now online and ready.", bot.user)
    await bot.change_presence(activity=discord.Game("Torrent Management"))

if __name__ == "__main__":
    try:
        bot.run(bot_token)
    except Exception as e:
        logger.error("Discord bot encountered an error: %s", e)
        sys.exit(1)
else:
    try:
        bot.run(bot_token)
    except Exception as e:
        logger.error("Discord bot encountered an error under gunicorn: %s", e)
        sys.exit(1)
