
import enum
import json
import datetime

import discord
from discord.ext.commands import Cog, command, Context
import asyncio
from io import BytesIO

from utils import time
from utils import queue

class ReactionEmojis(enum.Enum):
    Cancel = "❌"
    Completed = "✅"
    PriorityAddon = "📈"
    GoProMixingSessionAddon = "📸"

class ControlPanel(Cog):
    def __init__(self, bot):
        self.bot = bot

    async def track_user(self, server, user):

        invites = await self.bot.db.fetch("""
        SELECT guild_id, code, inviter, uses, users FROM invites WHERE guild_id=$1
        """, server.id)
        user_invites = [invite for invite in invites if str(user.id) in json.loads(invite['users'])]
        sorted_invites = sorted([(json.loads(invite['users']).get(str(user.id)), invite['code'], invite['inviter'], invite['uses']) for invite in user_invites], reverse=True)

        if len(sorted_invites) == 0:

            return False

        else:

            invite = sorted_invites[0]
            return invite

    @staticmethod
    def _get_matching_enum_values(enum, value):

        matched = []
        for item in (enum):
            if value == item.value:
                matched.append(value)

        return matched

    @Cog.listener(name="on_raw_reaction_add")
    async def raw_reaction_add(self, payload):
        
        # see if the payload emoji matches one of the ReactionEmojis
        matching_reactions = self._get_matching_enum_values(ReactionEmojis, payload.emoji.name)

        if not matching_reactions:
            return
        if not payload.member.id != self.bot.user.id:
            return

        reaction_channel = payload.member.guild.get_channel(payload.channel_id)
        reaction_message = None

        try:
            reaction_message = await reaction_channel.fetch_message(payload.message_id)
        except:
            return

        confirmation_messages = [
            'yep',
            'yes',
            'ye',
            'yea',
            'yuh',
            'yah'
            'nah',
            'no',
        ]
        if ReactionEmojis.Cancel.value == matching_reactions[0] and reaction_message and reaction_channel.name == "control-panel":
            question_message = await reaction_channel.send(f":warning: Are you sure you want to close this ticket? Enter **yes** or **no**")

            confirmation_message = await self.bot.wait_for("message", check= lambda message: message.author.id == payload.user_id and message.channel.id == reaction_channel.id and message.content.lower() in confirmation_messages)
            if confirmation_message.content.startswith("n"):
                await confirmation_message.delete()
                await question_message.delete()
                await reaction_channel.send(":thumbsup: Cancelled, deleting in 5 seconds.", delete_after=5)
            elif confirmation_message.content.startswith("y"):
                await confirmation_message.delete()
                await question_message.delete()
                await reaction_channel.send(":thumbsup: Closing ticket, starting process in 10 seconds.", delete_after=9)

                # wait 10 seconds
                await asyncio.sleep(10)

                parent_channel = reaction_channel.category
                matching_text_channels_to_category = [channel for channel in payload.member.guild.text_channels if channel.category and channel.category.id == parent_channel.id]
                matching_voice_channels_to_category = [channel for channel in payload.member.guild.voice_channels if channel.category and channel.category.id == parent_channel.id]

                for text_channel in matching_text_channels_to_category:
                    await text_channel.delete(
                        reason="Closed ticket."
                    )
                for voice_channel in matching_voice_channels_to_category:
                    await voice_channel.delete(
                        reason="Closed ticket."
                    )
                await parent_channel.delete(
                    reason="Closed ticket."
                )

                ticket_information = await self.bot.db.fetchrow("SELECT * FROM tickets WHERE category_id=$1", parent_channel.id)
                await self.bot.db.execute("DELETE FROM tickets WHERE category_id=$1", parent_channel.id)

                ticket_user = await self.bot.fetch_user(ticket_information['user_id'])
                transaction_logs = payload.member.guild.get_channel(self.bot.config['transactions_logs_channel_id'])
                transaction_embed = discord.Embed(color=discord.Color.orange(), timestamp=ticket_information['created_at'])
                transaction_embed.set_author(name=f"{ticket_user.name} Ticket Closed", icon_url=ticket_user.avatar_url)
                transaction_embed.description = f"""
                **__CANCELLED__**

                :moneybag: **Price:** {ticket_information['price']}
                :package: **Extra Packages:** {", ".join(ticket_information['extra_packages']) if ticket_information['extra_packages'] else "No extra packages"}
                """

                transcripts = await self.bot.db.fetch("SELECT * FROM transcripts WHERE category_id=$1", parent_channel.id)
                archives_list = [
                    f"Ticket ID: #{ticket_information['id']:,}",
                    f"Intiated By: {ticket_user} ({ticket_user.id})",
                    ""
                ]

                for transcript in transcripts:
                    user = await self.bot.fetch_user(transcript['author_id'])
                    content = transcript['message_content']

                    archives_list.append(f"[{transcript['created_at']}] {user} (ID: {user.id}) - {content}\n")

                archivesBytes = BytesIO()
                archivesData = "\n".join(archives_list)
                archivesBytes.write(archivesData.encode())
                archivesBytes.seek(0)
                archives = discord.File(archivesBytes, f"{ticket_information['id']}_{ticket_information['category_id']}_archives.txt")

                await transaction_logs.send(
                    embed=transaction_embed,
                    file=archives
                )

                await queue.send_queue_embed(
                    self.bot,
                    payload.member.guild,
                    self.bot.db
                )

        elif ReactionEmojis.Completed.value == matching_reactions[0] and reaction_message and reaction_channel.name == "control-panel":
            
            question_message = await reaction_channel.send(f":warning: Are you sure you want to complete this ticket? Enter **yes** or **no**")

            confirmation_message = await self.bot.wait_for("message", check= lambda message: message.author.id == payload.user_id and message.channel.id == reaction_channel.id and message.content.lower() in confirmation_messages)
            if confirmation_message.content.startswith("n"):
                await confirmation_message.delete()
                await question_message.delete()
                await reaction_channel.send(":thumbsup: Cancelled, deleting in 5 seconds.", delete_after=5)
            elif confirmation_message.content.startswith("y"):
                await confirmation_message.delete()
                await question_message.delete()
                await reaction_channel.send(":thumbsup: Processing transaction information, deleting in 10 seconds.", delete_after=9)

                parent_channel = reaction_channel.category
                ticket_information = await self.bot.db.fetchrow("SELECT * FROM tickets WHERE category_id=$1", parent_channel.id)
                invite_used = await self.track_user(payload.member.guild, await self.bot.fetch_user(ticket_information['user_id']))
                customer_role = payload.member.guild.get_role(self.bot.config['customers_role_id'])
                user = payload.member.guild.get_member(ticket_information['user_id'])

                await user.add_roles(customer_role)

                await self.bot.db.execute("""
                INSERT INTO customers (
                    user_id,
                    ticket_id,
                    created_at
                ) VALUES (
                    $1, $2, $3
                )
                """, ticket_information['user_id'], ticket_information['id'], datetime.datetime.now())

                if invite_used:
                    referral_logs = payload.member.guild.get_channel(self.bot.config['referral_logs_channel_id'])
                    invite_timestamp, invite_code, inviter_id, invite_uses = invite_used
                    referral_query = """
                    INSERT INTO referrals (
                        user_id,
                        referred_id,
                        reffered_at
                    ) VALUES (
                        $1, $2, $3
                    )
                    """
                    await self.bot.db.execute(referral_query, ticket_information['user_id'], inviter_id, datetime.datetime.now())

                    referrals = await self.bot.db.fetch("SELECT * FROM referrals WHERE referred_id=$1", inviter_id)
                
                    if len(referrals) >= 3:
                        await referral_logs.send(
                            "\n".join([
                                f":tada: <@{inviter_id}> has just hit **{len(referrals)}** referrals! They have referred <@{ticket_information['user_id']}> most recently."
                            ])
                        )
                    else:
                        await referral_logs.send(
                            "\n".join([
                                f":inbox_tray: <@{inviter_id}> has just referred <@{ticket_information['user_id']}>, they now have **{len(referrals)}** referral(s)."
                            ])
                        )

                matching_text_channels_to_category = [channel for channel in payload.member.guild.text_channels if channel.category and channel.category.id == parent_channel.id]
                matching_voice_channels_to_category = [channel for channel in payload.member.guild.voice_channels if channel.category and channel.category.id == parent_channel.id]

                for text_channel in matching_text_channels_to_category:
                    await text_channel.delete(
                        reason="Closed ticket."
                    )
                for voice_channel in matching_voice_channels_to_category:
                    await voice_channel.delete(
                        reason="Closed ticket."
                    )
                await parent_channel.delete(
                    reason="Closed ticket."
                )

                ticket_information = await self.bot.db.fetchrow("SELECT * FROM tickets WHERE category_id=$1", parent_channel.id)
                await self.bot.db.execute("DELETE FROM tickets WHERE category_id=$1", parent_channel.id)

                ticket_user = await self.bot.fetch_user(ticket_information['user_id'])
                transaction_logs = payload.member.guild.get_channel(self.bot.config['transactions_logs_channel_id'])
                transaction_embed = discord.Embed(color=discord.Color.green(), timestamp=ticket_information['created_at'])
                transaction_embed.set_author(name=f"{ticket_user.name} Ticket Closed", icon_url=ticket_user.avatar_url)
                transaction_embed.description = f"""
                **__COMPLETED__**

                :moneybag: **Price:** {ticket_information['price']}
                :package: **Extra Packages:** {", ".join(ticket_information['extra_packages']) if ticket_information['extra_packages'] else "No extra packages"}
                """

                transcripts = await self.bot.db.fetch("SELECT * FROM transcripts WHERE category_id=$1", parent_channel.id)
                archives_list = [
                    f"Ticket ID: #{ticket_information['id']:,}",
                    f"Intiated By: {ticket_user} ({ticket_user.id})",
                    ""
                ]

                for transcript in transcripts:
                    user = await self.bot.fetch_user(transcript['author_id'])
                    content = transcript['message_content']

                    archives_list.append(f"[{transcript['created_at']}] {user} (ID: {user.id}) - {content}\n")

                archivesBytes = BytesIO()
                archivesData = "\n".join(archives_list)
                archivesBytes.write(archivesData.encode())
                archivesBytes.seek(0)
                archives = discord.File(archivesBytes, f"{ticket_information['id']}_{ticket_information['category_id']}_archives.txt")

                await transaction_logs.send(
                    embed=transaction_embed,
                    file=archives
                )

                await queue.send_queue_embed(
                    self.bot,
                    payload.member.guild,
                    self.bot.db
                )

                try:

                    await user.send(f":tada: Thank you for choosing Mix & Masters! Your order has been completed, would you like to rate or review Mix & Masters?")

                    confirmation_message = await self.bot.wait_for("message", check= lambda message: message.author.id == user.id and message.channel.id == reaction_channel.id and message.content.lower() in confirmation_messages)
                    if confirmation_message.startswith("n"):
                        await user.send("Okay, blah blah")
                        return 
                    if confirmation_message.startswith("y"):
                        await user.send("What review would you like to leave?")
                        review_message = await self.bot.wait_for("message", check = lambda message: message.author.id == user.id and message.channel.id == reaction_channel.id)

                        if review_message.content.lower() == "cancel":
                            return await user.send("Okay, thank you for your time!")

                        await user.send("What rating would you give Mix & Masters?")
                        rating_message = await self.bot.wait_for("message", check = lambda message: message.author.id == user.id and message.channel.id == reaction_channel.id)

                        if rating_message.content.lower() == "cancel":
                            return await user.send("Okay, thank you for your time!")
                        if type(rating_message.content) == int and int(rating_message.content) > 0 and int(rating_message.content) < 6:
                            rating_found = False
                            while not rating_found:
                                await user.send("A rating must be greater than 0 and less than 6, please try again!")
                                rating_message = await self.bot.wait_for("message", check = lambda message: message.author.id == user.id and message.channel.id == reaction_channel.id)

                                if rating_message.content.lower() == "cancel":
                                    return await user.send("Okay, thank you for your time!")
                                
                                if type(rating_message.content) == int and int(rating_message.content > 0) and int(rating_message.content) > 6:
                                    continue
                                else:
                                    rating_found = True

                        review_channel = payload.member.guild.get_channel(self.bot.config['review_channel_id'])

                        review_embed = discord.Embed(color=discord.Color.green(), timestamp=datetime.datetime.now())
                        review_embed.title = f"{user}'s Review!"
                        review_embed.description = "\n".join([
                            review_message.content,
                            "",
                            f"**Rating:** {rating_message.content}"
                        ])
                        await review_channel.send(embed=review_embed)

                except:
                    pass

        elif ReactionEmojis.PriorityAddon.value == matching_reactions[0] and reaction_message and reaction_channel.name == "addons":

            question_message = await reaction_channel.send(f":warning: Are you sure you want to add this addon? **yes** or **no**")

            confirmation_message = await self.bot.wait_for("message", check= lambda message: message.author.id == payload.user_id and message.channel.id == reaction_channel.id and message.content.lower() in confirmation_messages)
            if confirmation_message.content.startswith("n"):
                await confirmation_message.delete()
                await question_message.delete()
                await reaction_channel.send(":thumbsup: Cancelled, not adding that addon.", delete_after=5)
            elif confirmation_message.content.startswith("y"):
                await confirmation_message.delete()
                await question_message.delete()
                await reaction_channel.send(":thumbsup: Added the `$100 Tier Priority` addon to the list!", delete_after=5)
        
                parent_channel = reaction_channel.category
                ticket_information = await self.bot.db.fetchrow("SELECT * FROM tickets WHERE category_id=$1", parent_channel.id)
                addons = ticket_information['extra_packages'] if ticket_information['extra_packages'] else []
                if not "$100 Tier Priority" in addons:
                    addons.append("$100 Tier Priority")

                await self.bot.db.execute(
                    """
                    UPDATE tickets
                    SET extra_packages=$2
                    WHERE id=$1
                    """,
                    ticket_information['id'],
                    addons
                )
                await queue.send_queue_embed(
                    self.bot,
                    payload.member.guild,
                    self.bot.db
                )

                plans = {
                    100: 'Basic',
                    200: 'Standard',
                    300: 'Premium'
                }

                try:

                    text_channel = [channel for channel in payload.member.guild.text_channels if channel.category and channel.category.id == parent_channel.id and channel.name == "chat"]
                    message = await text_channel[0].fetch_message(ticket_information['information_embed_id'])
                    user = await self.bot.fetch_user(ticket_information['user_id'])

                    previous_referrals_query = """
                        SELECT id FROM referrals
                        WHERE user_id=$1
                    """
                    previous_referrals = await self.bot.db.fetch(previous_referrals_query, user.id)

                    previous_buys_query = """
                        SELECT id FROM customers
                        WHERE user_id=$1
                    """
                    previous_buys = await self.bot.db.fetch(previous_buys_query, user.id)

                    ticket_embed = discord.Embed()
                    ticket_embed.set_author(name=f"{user} {plans[ticket_information['price']]} (${ticket_information['price']})", icon_url=user.avatar_url)
                    ticket_embed.description = f"""
                    **{user}** has made created a new ticket!
                    They are wanting the **{plans[ticket_information['price']]} (${ticket_information['price']})** package.
                    They have made **{len(previous_referrals)}** referrals and **{len(previous_buys)}** transactions.
                    Extra Packages: {", ".join(addons)}
                    """
                    await message.edit(
                        embed=ticket_embed,
                        content=f"{payload.member.mention}"
                    )
                    
                except Exception as e:
                    print(e)
                    
        elif ReactionEmojis.GoProMixingSessionAddon.value == matching_reactions[0] and reaction_message and reaction_channel.name == "addons":

            question_message = await reaction_channel.send(f":warning: Are you sure you want to add this addon? **yes** or **no**")

            confirmation_message = await self.bot.wait_for("message", check= lambda message: message.author.id == payload.user_id and message.channel.id == reaction_channel.id and message.content.lower() in confirmation_messages)
            if confirmation_message.content.startswith("n"):
                await confirmation_message.delete()
                await question_message.delete()
                await reaction_channel.send(":thumbsup: Cancelled, not adding that addon.", delete_after=5)
            elif confirmation_message.content.startswith("y"):
                await confirmation_message.delete()
                await question_message.delete()
                await reaction_channel.send(":thumbsup: Added the `$75 for 4k GoPro Mixing Session` addon to the list!", delete_after=5)
        
                parent_channel = reaction_channel.category
                ticket_information = await self.bot.db.fetchrow("SELECT * FROM tickets WHERE category_id=$1", parent_channel.id)
                addons = ticket_information['extra_packages'] if ticket_information['extra_packages'] else []

                if not "$75 for 4k GoPro Mixing Session" in addons:
                    addons.append("$75 for 4k GoPro Mixing Session")

                await self.bot.db.execute(
                    """
                    UPDATE tickets
                    SET extra_packages=$2
                    WHERE id=$1
                    """,
                    ticket_information['id'],
                    addons
                )
                await queue.send_queue_embed(
                    self.bot,
                    payload.member.guild,
                    self.bot.db
                )

                plans = {
                    100: 'Basic',
                    200: 'Standard',
                    300: 'Premium'
                }

                try:

                    text_channel = [channel for channel in payload.member.guild.text_channels if channel.category and channel.category.id == parent_channel.id and channel.name == "chat"]
                    message = await text_channel[0].fetch_message(ticket_information['information_embed_id'])
                    user = await self.bot.fetch_user(ticket_information['user_id'])

                    previous_referrals_query = """
                        SELECT id FROM referrals
                        WHERE user_id=$1
                    """
                    previous_referrals = await self.bot.db.fetch(previous_referrals_query, user.id)

                    previous_buys_query = """
                        SELECT id FROM customers
                        WHERE user_id=$1
                    """
                    previous_buys = await self.bot.db.fetch(previous_buys_query, user.id)

                    ticket_embed = discord.Embed()
                    ticket_embed.set_author(name=f"{user} {plans[ticket_information['price']]} (${ticket_information['price']})", icon_url=user.avatar_url)
                    ticket_embed.description = f"""
                    **{user}** has made created a new ticket!
                    They are wanting the **{plans[ticket_information['price']]} (${ticket_information['price']})** package.
                    They have made **{len(previous_referrals)}** referrals and **{len(previous_buys)}** transactions.
                    Extra Packages: {", ".join(addons)}
                    """
                    await message.edit(
                        embed=ticket_embed,
                        content=f"{payload.member.mention}"
                    )
                    
                except Exception as e:
                    print(e)

def setup(bot):
    bot.add_cog(ControlPanel(bot))