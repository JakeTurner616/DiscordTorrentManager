# DiscordTorrentManager

Torrent seeker and manager that you can use with your friends 


> [!NOTE]
> The [initial](https://github.com/JakeTurner616/DiscordMovieBot) version of this project faced significant issues with maintainability and scope. This is the second iteration and aims to have a clearer scope and improved testability so it can be easily maintained and improved.

This program consists of a bot scirpt and a search wrapper. these two parts work together to find torrents and add magnets to qbittorrent.

# Installation

1. **Clone the repository:**

    ```bash
    git clone https://github.com/JakeTurner616/DiscordTorrentManager
    cd DiscordTorrentManager
    ```

2. **Create a virtual environment:**

    ```bash
    python -m venv venv
    ```

3. **Activate the virtual environment:**

    - On Windows:

        ```bash
        venv\Scripts\activate
        ```

    - On MacOS and Linux:

        ```bash
        source venv/bin/activate
        ```

4. **Install the required packages:**

    ```bash
    pip install -r requirements.txt
    ```

5. **Run the bot:**

    ```bash
    python bot.py
    ```

## qBittorrent Setup

1. Open qBittorrent and go to `Tools` -> `Options`.

2. Navigate to the `Web UI` section under the `Web UI` tab.

3. Check the `Enable the Web User Interface (Remote control)` box.

4. Set a username and password for the Web UI or setup whitelist rules.

5. Note the IP address and port number where the Web UI will be accessible (e.g., `http://10.0.0.153:8080`).

6. Create torrent categories in qBittorrent to associate the downloaded content with the folders they should be saved to (for example: movies > Z://some/location/movies, tv > Z://some/location/tv). These are to be used with /magnet. (/magnet <magnet_link> <category>) These could be set somwhere that has access to a media player like plex, jellyfin, or anything really.

## Discord Bot Setup

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications) and create a new bot application.

2. Navigate to the `Bot` section and create a new bot.

3. Create and copy the bot token.

4. Invite the bot to your server using the OAuth2 URL Generator under the `OAuth2` tab. Make sure to give the bot the necessary permissions.

## Configuration

Edit the `config.ini` file to include your specific environment settings for connecting to your discord bot and qBittorrent instance:

```ini
[Bot]
# change to your bot token
token = YOUR_DISCORD_BOT_TOKEN
# change to your server id
guild_id = YOUR_DISCORD_GUILD_ID

[qbit]
# change to your qBittorrent host and port:  http://host_ip:port 
host = http://10.0.0.153:8080
# qBittorrent WebUI login credentials
user = YOUR_QBITTORRENT_USERNAME
pass = YOUR_QBITTORRENT_PASSWORD
```

The bot can then be started by running the `bot.py` script.

## Command Usage

Here are the commands included with the DiscordTorrentManager bot:

- **Add a Magnet Link:**
    ```bash
    /magnet <magnet> <category>
    ```
    This command adds a new torrent to qBittorrent using the provided magnet link and associates it with the specified category.

- **Search for Torrents:**
    ```bash
    /search <title>
    ```
    This command searches for torrents based on the provided title. The bot will list the results, and the user can select a result to automatically download it to the 'movie' category. Assumes the 'movie' category exists.
