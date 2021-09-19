
# default libraries
import os

# installed packages from PyPi
import discord
from discord.ext import commands
from discord.ext.commands import Bot
import yaml
import asyncpg
from discord_components import DiscordComponents, Button, ButtonStyle, Select, SelectOption

# custom files
from utils.context import Context

# load the config contents from config.yaml and safe load it
with open("config.yaml", "rb") as ConfigFile:
    config = yaml.safe_load(ConfigFile.read())

# this class will hold all of the attributes, events, and custom functions in order to run the bot
class MixMasterBot(Bot):
    def __init__(self):
        super().__init__(
            command_prefix=commands.when_mentioned_or(config['prefix']),
            case_insensitive=True,
            intents=discord.Intents.all()
        )

        self.db: asyncpg.Pool or None = None # postgresql database
        self.config: yaml.SafeLoader = config # yaml config contents

        self.unloaded_cogs: list = [ # cogs, all the commands and events of the bot
            'jishaku',
            "cogs.about",
            "cogs.order",
            "cogs.invites",
            "cogs.control_panel",
            "cogs.transcripts"
        ]

    async def on_ready(self) -> None:
        DiscordComponents(bot) # load the discord components module when the bot is ready
        print(f"Ready to rock and roll.")
        
    async def _create_postgres_session(self) -> None:

        self.db = await asyncpg.create_pool(
            host=config['postgres']['host'],
            port=config['postgres']['port'],
            database=config['postgres']['database'],
            user=config['postgres']['user'],
            password=config['postgres']['password']
        )

        # SQL loader, this will go through each SQL file and execute the contents
        for file in os.listdir("./sql"):
            if file.endswith(".sql"):

                # read the sql file, then execute with the asyncpg library
                path = f"./sql/{file}"
                with open(path, 'r') as SQLFile:
                    try:
                        await self.db.execute(SQLFile.read())
                        print(f"Executed the SQL file: {file}")
                    except Exception as e:
                        print(f"Failed to execute {file}: {e}")

    async def _load_cogs(self) -> None:

        for cog in self.unloaded_cogs:
            try:
                self.load_extension(cog)
                print(f"Loaded the cog: {cog}")
            except Exception as e:
                print(f"Failed to load {cog}: {e}")
    
    async def login(self, *args, **kwargs):
        await self._load_cogs()
        await self._create_postgres_session()

        await super().login(*args, **kwargs)

    async def get_context(self, message, cls=None) -> None or commands.Context:
        if not message.guild or message.author.bot:
            return None

        return await super().get_context(message, cls=cls)

    async def process_commands(self, message) -> None:
        ctx = await self.get_context(message, cls=Context)
        if not ctx or not ctx.command:
            return 
        
        await self.invoke(ctx)

bot = MixMasterBot()

# finally, run the bot
bot.run(config['token'])