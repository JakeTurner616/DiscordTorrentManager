# DiscordTorrentManager 🎬

Connect your seedbox to your discord server.

![magnet link demo](https://github.com/JakeTurner616/DiscordTorrentManager/blob/main/docs/moviebotdemo.gif)

This program enhances a Discord server by integrating torrent searching and downloading functionalities through the qBittorrent API. 🤯


# 🌟 Installation

## Docker Installation ***(Recommended)***

1. **Clone the repository:**

    ```bash
    git clone https://github.com/JakeTurner616/DiscordTorrentManager
    cd DiscordTorrentManager
    ```

2. **Build the Docker image:**

    ```bash
    docker build -t discordtorrentmanager .
    ```

3. **Run the Docker container:**


    ### Linux/macOS (Bash or Zsh)
    ```bash
    docker run -d --name discordtorrentmanager -v $(pwd)/config.ini:/app/config.ini -p 5000:5000 discordtorrentmanager
    ```

    ### Windows (PowerShell)
    ```powershell
    docker run -d --name discordtorrentmanager -v ${PWD}/config.ini:/app/config.ini -p 5000:5000 discordtorrentmanager
    ```


---

## Bare-Metal Installation (Not Recommended)

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

5. **Running the bot:**

    The Bot can be started by running the start script, Make sure to setup qBittorrent and the values in `config.ini`.

    ```bash
    bash ./start.sh
    ```
    If you encounter the following error: `ImportError: cannot import name 'Option' from 'discord'`, resolve it by running these commands:
    
    ```bash
    pip uninstall discord -y
    pip uninstall py-cord -y
    pip install discord
    pip install py-cord
    pip uninstall discord -y
    ```

---

## ⚙️ qBittorrent Setup

1. Open qBittorrent and go to `Tools` -> `Options`.

2. Navigate to the `Web UI` section under the `Web UI` tab.

3. Check the `Enable the Web User Interface (Remote control)` box.
   
5. Set a network interface to bind the Web UI in the `IP Address` text box.

6. Set a username and password for the Web UI.

7. Create torrent categories in qBittorrent to associate the downloaded content with the folders they should be saved to (for example: movies --> Z://some/location/movies, and tv --> Z://some/location/tv). These are to be used with `/magnet <magnet_link> <category>` The category save paths could be set somwhere that has access to a media player like plex, jellyfin, a game folder, or anything really.

## ⚙️ Discord Bot Setup

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications) and create a new bot application.

2. Create and copy the bot token.

3. Invite the bot to your Discord server using the OAuth2 URL Generator under the `OAuth2` tab. Make sure to give the bot the necessary permissions for slash commands, reactions, and text.

## ⚙️ Configuration

Edit the `config.ini` file to include your specific environment settings for connecting to your discord bot and qBittorrent instance:

```ini
[Bot]
# change to your bot token
token = YOUR_DISCORD_BOT_TOKEN
# change to your server id
guild_id = YOUR_DISCORD_GUILD_ID

[qbit]
# change to your qBittorrent host and port:  http://host_ip:port 
host = http://host_ip:port
# qBittorrent WebUI login credentials
user = YOUR_QBITTORRENT_USERNAME
pass = YOUR_QBITTORRENT_PASSWORD
```

The bot can then be started by running the `./start.sh` script.

## 🤖 Command Usage

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
