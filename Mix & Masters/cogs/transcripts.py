
import enum
import json
import datetime

import discord
from discord.ext.commands import Cog, command, Context
import asyncio

from utils import time

class Transcripts(Cog):
    def __init__(self, bot):
        self.bot = bot

    @Cog.listener(name="on_message")
    async def on_message(self, message):
        if message.author.bot:
            return
        
        if not hasattr(message.channel, 'category'):
            return
        category = message.channel.category
        if not category:
            return

        ticket = await self.bot.db.fetchrow("SELECT * FROM tickets WHERE category_id=$1", category.id)
        if not ticket:
            return

        if not message.channel.name.lower() == "chat":
            return

        content = [message.content, ]
        if message.attachments and message.attachments[0].width:
            content.append(f"[ATTACHMENT] {message.attachments[0].proxy_url}")
        content = "\n".join(content)

        query = """
        INSERT INTO transcripts (
            message_id,
            author_id,
            channel_id,
            category_id,
            message_content,
            created_at
        ) VALUES (
            $1, $2, $3, $4, $5, $6
        )
        """
        await self.bot.db.execute(query, message.id, message.author.id, message.channel.id, category.id, content, message.created_at)

def setup(bot):
    bot.add_cog(Transcripts(bot))
