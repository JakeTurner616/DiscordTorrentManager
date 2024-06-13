import sys
import discord
from discord import Option, ApplicationContext
from discord.ext import commands
import requests
import configparser
from qbittorrent import Client
import asyncio
import humanize
import subprocess
import platform
import time
import os

# Read config
config = configparser.ConfigParser()
config.read('config.ini')

bot_token = config.get('Bot', 'token')
guild_id = config.getint('Bot', 'guild_id')

qb_host = config.get('qbit', 'host')
qb_user = config.get('qbit', 'user')
qb_pass = config.get('qbit', 'pass')
qb = Client(qb_host)

# Initialize bot
intents = discord.Intents.default()
intents.reactions = True
intents.messages = True
bot = commands.Bot(command_prefix='!', intents=intents)
bot.remove_command('help')

# Global variable to track download progress
download_in_progress = False

emoji_list = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣']  # List of emojis for reactions

def is_server_running(url):
    try:
        response = requests.get(url)
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        return False

API_URL = 'http://127.0.0.1:5000'
if not is_server_running(API_URL):
    print("Server is not running. Starting app.py...")
    current_directory = os.path.dirname(os.path.abspath(__file__))
    python_executable = sys.executable
    script_path = os.path.join(os.path.dirname(__file__), "app.py")

    # Check if the server is running and start it if not
    if not is_server_running('http://127.0.0.1:5000'):
        print("Server is not running. Starting app.py...")
        subprocess.Popen(['venv/scripts/python', 'app.py'])
        time.sleep(5)
    else:
        print("Server is already running.")
    
else:
    print("Server is already running.")

@bot.slash_command(name="magnet", description="Download a torrent from a magnet link.", guild_ids=[guild_id])
async def magnet(ctx: ApplicationContext,
                 magnet_link: Option(str, "Specify the magnet link.", required=True), # type: ignore
                 category: Option(str, "Specify the download category.", required=True, choices=["TV", "Movie", "FitGirl Repack"])): # type: ignore

    global download_in_progress
    download_in_progress = True
    empty_response_counter = 0
    movie_title = None

    try:
        qb.login(qb_user, qb_pass)
        qb.download_from_link(magnet_link, category=category.lower())

        init_embed = discord.Embed(
            title="The torrent file is being sent to qBittorrent.",
            color=discord.Color.green()
        )
        await ctx.respond(embed=init_embed)

        progress_embed = discord.Embed(
            title="Torrent download initiated",
            color=discord.Color.green()
        )
        progress_message = await ctx.send(embed=progress_embed)

        while True:
            info_global_url = 'http://127.0.0.1:5000/infoglobal'
            info_response = requests.get(info_global_url).json()

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

                if size > 0:
                    downloaded_percentage = (downloaded / size) * 100
                    loading_bar = "▓" * int(downloaded_percentage // 5) + "░" * int(20 - (downloaded_percentage // 5))
                else:
                    downloaded_percentage = 0
                    loading_bar = "░" * 20

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
                    await ctx.send(embed=download_complete_embed)
                    await bot.change_presence(status=discord.Status.online, activity=None)
                    download_in_progress = False
                    break

            await asyncio.sleep(5)

    except Exception as e:
        error_embed = discord.Embed(
            title="An error occurred",
            description=str(e),
            color=discord.Color.red()
        )
        await ctx.send(embed=error_embed)
        download_in_progress = False

@bot.slash_command(name="search", description="Search for torrents.", guild_ids=[guild_id])
async def search(ctx: ApplicationContext, query: Option(str, "Specify the search query.", required=True)): # type: ignore
    embed = discord.Embed(
        title="Search Initiated",
        description="Bot is searching for your request...",
        color=discord.Color.blue()
    )
    await ctx.respond(embed=embed, ephemeral=True)

    try:
        search_url = f'http://127.0.0.1:5000/torrents?q={query}'
        response = requests.get(search_url)
        results = response.json()

        if 'error' in results:
            await ctx.send(f"Error: {results['error']}")
            return

        for i, result in enumerate(results):
            embed = discord.Embed(title=result['title'], color=discord.Color.blue())
            embed.add_field(name="Category", value=result['category'], inline=False)
            embed.add_field(name="Size", value=result['size'], inline=False)
            embed.add_field(name="Seeders", value=result['seeders'], inline=False)
            embed.add_field(name="Leechers", value=result['leechers'], inline=False)
            embed.add_field(name="Date", value=result['date'], inline=False)
            embed.add_field(name="Magnet Link", value=f"```{result['magnet_link']}```", inline=False)
            
            msg = await ctx.send(embed=embed)
            await msg.add_reaction(emoji_list[i])

    except Exception as e:
        error_embed = discord.Embed(
            title="An error occurred",
            description=str(e),
            color=discord.Color.red()
        )
        await ctx.send(embed=error_embed)

@bot.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return

    msg = reaction.message
    if msg.author == bot.user and msg.embeds:
        embed = msg.embeds[0]
        magnet_link = embed.fields[5].value.strip("```")
        channel = msg.channel

        await handle_magnet_download(channel, magnet_link, 'Movie')

async def handle_magnet_download(channel, magnet_link, category):
    global download_in_progress
    download_in_progress = True
    empty_response_counter = 0
    movie_title = None
    metadata_failure_count = 0
    max_metadata_failure_count = 100

    try:
        qb.login(qb_user, qb_pass)
        qb.download_from_link(magnet_link, category=category.lower())

        init_embed = discord.Embed(
            title="The torrent file is being sent to qBittorrent.",
            color=discord.Color.green()
        )
        await channel.send(embed=init_embed)

        progress_embed = discord.Embed(
            title="Torrent download initiated",
            color=discord.Color.green()
        )
        progress_message = await channel.send(embed=progress_embed)

        while True:
            info_global_url = 'http://127.0.0.1:5000/infoglobal'
            info_response = requests.get(info_global_url).json()

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

                if size > 0:
                    downloaded_percentage = (downloaded / size) * 100
                    loading_bar = "▓" * int(downloaded_percentage // 5) + "░" * int(20 - (downloaded_percentage // 5))
                else:
                    downloaded_percentage = 0
                    loading_bar = "░" * 20

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
        download_in_progress = False

@bot.command(name='login', help='Log into the qb session')
async def login_command(ctx): 
    try:
        qb.login(qb_user, qb_pass) 
        print('qb session refreshed!')
    except Exception as e:
        error_embed = discord.Embed(
            title="An error occurred during qb login",
            description=str(e),
            color=discord.Color.red()
        )
        await ctx.send(embed=error_embed)

@bot.command(name='logout', help='Log out of the qb session')
async def logout_command(ctx):
    try:
        qb.logout()
        await ctx.send('Logged out and disconnected qb session')
    except Exception as e:
        error_embed = discord.Embed(
            title="An error occurred during qb logout",
            description=str(e),
            color=discord.Color.red()
        )
        await ctx.send(embed=error_embed)

bot.run(bot_token)
