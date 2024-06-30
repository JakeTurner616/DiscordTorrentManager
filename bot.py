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

# Initialize logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Load the configuration file
config = configparser.ConfigParser()

try:
    config.read('config.ini')

    # Load Discord bot token
    bot_token = config.get('Bot', 'token')
    if bot_token.lower() == 'xxx':
        raise ValueError("Bot token in 'config.ini' is not set. Replace 'xxx' with a valid token.")

    # Load guild IDs
    raw_guild_ids = config.get('Bot', 'guild_id')
    if raw_guild_ids.lower() == 'xxx':
        raise ValueError("Guild ID in 'config.ini' is not set. Replace 'xxx' with valid guild IDs.")

    # Parse guild IDs into a list of integers
    try:
        guild_ids = [int(gid.strip()) for gid in raw_guild_ids.split(',')]
    except ValueError as e:
        raise ValueError(f"Invalid guild IDs in 'config.ini': {raw_guild_ids}. Ensure they are valid integers.") from e

    # Load qBittorrent details
    qb_host = config.get('qbit', 'host')
    qb_user = config.get('qbit', 'user')
    qb_pass = config.get('qbit', 'pass')
    if qb_host.lower() == 'http://host_ip:port':
        raise ValueError("qBittorrent host in 'config.ini' is not set. Replace 'http://host_ip:port' with a valid host.")

except configparser.NoSectionError as e:
    logger.error("Configuration error: Missing section in 'config.ini': %s", e)
    sys.exit(1)
except configparser.NoOptionError as e:
    logger.error("Configuration error: Missing option in 'config.ini': %s", e)
    sys.exit(1)
except ValueError as e:
    logger.error("Configuration error: %s", e)
    sys.exit(1)

# -------- QBITTORRENT CLIENT SETUP -------- #

try:
    qb = Client(qb_host)
    qb.login(qb_user, qb_pass)
    logger.info("qBittorrent client initialized successfully.")
except ConnectionError:
    logger.error("Unable to connect to qBittorrent Web API at %s. Check the connection.", qb_host)
    qb = None
except LoginRequired:
    logger.error("Failed to authenticate with the qBittorrent Web API. Verify your credentials.")
    qb = None
except Exception as e:
    logger.error("Unexpected error during qBittorrent client initialization: %s", e)
    qb = None

# -------- DISCORD BOT SETUP -------- #

intents = discord.Intents.default()
intents.reactions = True
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

bot.remove_command('help')

download_in_progress = False
emoji_list = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣']
API_URL = 'http://127.0.0.1:5000'

# -------- COMMANDS -------- #

@bot.slash_command(name="search", description="Search for torrents.", guild_ids=guild_ids)
async def search(ctx: ApplicationContext, query: Option(str, "Specify the search query.", required=True)):
    """
    Search for torrents and display results with reactions.
    """
    logger.info("Received search request with query: %s", query)
    embed = discord.Embed(
        title="Search Initiated",
        description="Bot is searching for your request...",
        color=discord.Color.blue()
    )
    await ctx.respond(embed=embed, ephemeral=True)

    try:
        search_url = f"{API_URL}/torrents?q={query}"
        response = requests.get(search_url)
        results = response.json()

        if 'error' in results:
            logger.error("Error from search API: %s", results['error'])
            await ctx.send(f"Error: {results['error']}")
            return

        if not results:
            embed = discord.Embed(
                title="No Results Found",
                description="The search did not return any results. Please try a different query.",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)
            return

        for i, result in enumerate(results[:len(emoji_list)]):
            embed = discord.Embed(title=result['title'], color=discord.Color.blue())
            embed.add_field(name="Category", value=result['category'], inline=False)
            embed.add_field(name="Size", value=result['size'], inline=False)
            embed.add_field(name="Seeders", value=result['seeders'], inline=False)
            embed.add_field(name="Leechers", value=result['leechers'], inline=False)
            embed.add_field(name="Date", value=result['date'], inline=False)
            embed.add_field(name="Magnet Link", value=f"```{result['magnet_link']}```", inline=False)
            msg = await ctx.send(embed=embed)
            await msg.add_reaction(emoji_list[i])
        logger.info("Search results displayed successfully.")

    except Exception as e:
        logger.error("Unexpected error during search command: %s", e)
        error_embed = discord.Embed(
            title="An error occurred",
            description=str(e),
            color=discord.Color.red()
        )
        await ctx.send(embed=error_embed)


@bot.slash_command(name="magnet", description="Download a torrent from a magnet link.", guild_ids=guild_ids)
async def magnet(ctx: ApplicationContext,
                 magnet_link: Option(str, "Specify the magnet link.", required=True),
                 category: Option(str, "Specify the download category.", required=True, choices=["TV", "Movie", "FitGirl Repack"])):
    """
    Add a torrent download via magnet link.
    """
    global download_in_progress
    if not qb:
        logger.error("Seedbox unavailable. Cannot process magnet command.")
        await ctx.respond(embed=discord.Embed(
            title="Error",
            description="Seedbox is unavailable. Please check the connection.",
            color=discord.Color.red()
        ))
        return

    if download_in_progress:
        await ctx.respond(embed=discord.Embed(
            title="Download in Progress",
            description="Another download is currently in progress. Please wait for it to complete.",
            color=discord.Color.orange()
        ))
        return

    if not magnet_link.startswith("magnet:?"):
        await ctx.respond(embed=discord.Embed(
            title="Invalid Magnet Link",
            description="Please provide a valid magnet link.",
            color=discord.Color.red()
        ))
        return

    download_in_progress = True
    logger.info("Processing magnet command. Magnet link: %s, Category: %s", magnet_link, category)

    try:
        qb.login(qb_user, qb_pass)
        qb.download_from_link(magnet_link, category=category.lower())

        await ctx.respond(embed=discord.Embed(
            title="The torrent file is being sent to qBittorrent.",
            color=discord.Color.green()
        ))
        logger.info("Magnet link sent to qBittorrent successfully.")

    except Exception as e:
        logger.error("Unexpected error during magnet command: %s", e)
        error_embed = discord.Embed(
            title="An error occurred",
            description=str(e),
            color=discord.Color.red()
        )
        await ctx.send(embed=error_embed)

@bot.event
async def on_reaction_add(reaction, user):
    """
    Handle reactions added to search result messages.
    """
    if user.bot:
        return  # Ignore bot reactions

    message = reaction.message

    # Ensure the message contains an embed and was sent by the bot
    if message.embeds and message.author == bot.user:
        embed = message.embeds[0]
        # Match the reaction with the corresponding search result
        if reaction.emoji in emoji_list:
            # Extract the magnet link from the embed
            magnet_field = next((field for field in embed.fields if field.name == "Magnet Link"), None)
            if magnet_field:
                magnet_link = magnet_field.value.strip("```")  # Remove code block formatting
                logger.info("User %s selected magnet link: %s", user.name, magnet_link)
                # Use a default category for now (e.g., "Movie")
                await handle_magnet_download(message.channel, magnet_link, "Movie")
async def handle_magnet_download(channel, magnet_link, category):
    """
    Process the magnet link and send it to qBittorrent, displaying the download UI using the infoglobal endpoint.
    """
    global download_in_progress
    download_in_progress = True
    empty_response_counter = 0
    movie_title = None

    try:
        qb.login(qb_user, qb_pass)
        qb.download_from_link(magnet_link, category=category.lower())

        # Initial embed to confirm download initiation
        init_embed = discord.Embed(
            title="The torrent file is being sent to qBittorrent.",
            color=discord.Color.green()
        )
        await channel.send(embed=init_embed)

        # Embed to display torrent download progress
        progress_embed = discord.Embed(
            title="Torrent download initiated",
            color=discord.Color.green()
        )
        progress_message = await channel.send(embed=progress_embed)

        while True:
            # Fetch data from the infoglobal endpoint
            info_global_url = f'{API_URL}/infoglobal'
            try:
                info_response = requests.get(info_global_url, timeout=10).json()
            except Exception as e:
                logger.error("Error fetching data from infoglobal: %s", e)
                break

            if info_response:
                movie_title = info_response[0].get('name', 'Unknown Name')
                category = info_response[0].get('category', '')
                state = info_response[0].get('state', 'Unknown State')
                size = info_response[0].get('size', 0)
                downloaded = info_response[0].get('downloaded', 0)
                eta_seconds = info_response[0].get('eta', 0)
                eta_humanized = humanize.naturaldelta(eta_seconds)
                num_seeds = info_response[0].get('num_seeds', 0)
                num_leeches = info_response[0].get('num_leechs', 0)
                dlspeed = info_response[0].get('dlspeed', 0)
                dlspeed_humanized = humanize.naturalsize(dlspeed, binary=True) + "/s"

                # Generate the progress bar
                if size > 0:
                    downloaded_percentage = (downloaded / size) * 100
                    loading_bar = "▓" * int(downloaded_percentage // 5) + "░" * int(20 - (downloaded_percentage // 5))
                else:
                    downloaded_percentage = 0
                    loading_bar = "░" * 20

                # Update the embed
                embed_description = (
                    f"Name: **{movie_title}**\n"
                    f"Category: **{category}**\n"
                    f"State: **{state}**\n"
                    f"Size: **{humanize.naturalsize(size, binary=True)}**\n"
                    f"Downloaded: {humanize.naturalsize(downloaded, binary=True)} "
                    f"(**{downloaded_percentage:.2f}%**)\n"
                    f"ETA: **{eta_humanized}**\n\n"
                    f"Progress: **{loading_bar}** ~{dlspeed_humanized}"
                )
                footer_text = f"Seeds: {num_seeds} • Peers: {num_leeches}"
                progress_embed.description = embed_description
                progress_embed.set_footer(text=footer_text)

                await progress_message.edit(embed=progress_embed)

            else:
                empty_response_counter += 1

                if empty_response_counter >= 10:
                    download_complete_embed = discord.Embed(
                        title=f'Download completed for {movie_title}!',
                        color=discord.Color.green()
                    )
                    await progress_message.delete()
                    await channel.send(embed=download_complete_embed)
                    download_in_progress = False
                    break

            await asyncio.sleep(5)

    except Exception as e:
        error_embed = discord.Embed(
            title="An error occurred",
            description=str(e),
            color=discord.Color.red()
        )
        await channel.send(embed=error_embed)
    finally:
        download_in_progress = False


# -------- MAIN -------- #

@bot.event
async def on_ready():
    logger.info(f"{bot.user} is now online and ready.")
    activity = discord.Game(name="Torrent Management")
    await bot.change_presence(status=discord.Status.online, activity=activity)

if __name__ == "__main__":
    try:
        logger.info("Bot client is now online and ready for commands.")
        bot.run(bot_token)
    except Exception as e:
        logger.error("Discord bot encountered an error: %s", e)
        sys.exit(1)
