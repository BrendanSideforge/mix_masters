
# default libraries
import datetime

# installed PyPi packages
import discord
from discord.ext import commands
from discord.ext.commands import Cog
from discord_components import DiscordComponents, Button, ButtonStyle, Select, SelectOption

from utils import queue

class Order(Cog):
    def __init__(self, bot):
        self.bot = bot

    @Cog.listener()
    async def on_ready(self):

        bot_server = self.bot.get_guild(self.bot.config['bot_server_id'])
        ticket_channel = self.bot.get_channel(self.bot.config['ticket_create_channel_id'])

        try:
            ticket_message_to_delete = await ticket_channel.fetch_message(ticket_channel.last_message_id)
            await ticket_message_to_delete.delete()
        except:
            pass
        
        # await self.bot.db.execute("DELETE FROM tickets")
        await queue.send_queue_embed(
            self.bot,
            bot_server,
            self.bot.db
        )

        order_now_image = discord.File("./icons/orderNowBanner.gif", "orderNow.gif")
        ticket_embed = discord.Embed()
        ticket_embed.set_author(name="Mix & Masters")
        ticket_embed.description = f"""
        **1.** $100 basic mix w/ 1 revision.
        **2.** $200 mix and master w/ 2 revisions.
        **3.** $300 mix and master w/ unlimited revisions and priority queue.

        Want your session filmed for promotional use? $75 for 4k mixing session.

        Beat leases / exclusives on demand, negotiable rates available.
        """
        ticket_embed.set_image(url="attachment://orderNow.gif")
        ticket_embed.set_footer(text="Please click the corresponding button!")

        await ticket_channel.send(
            embed=ticket_embed,
            file=order_now_image,
            components = [
                [
                    Button(
                        style=ButtonStyle.green,
                        label="Basic ($100)"
                    ),
                    Button(
                        style=ButtonStyle.green,
                        label="Standard ($200)"
                    ),
                    Button(
                        style=ButtonStyle.green,
                        label="Premium ($300)"
                    )
                ]
            ]
        )

        # await self.bot.db.execute("DELETE FROM referrals")

        while True:
            interaction = await self.bot.wait_for("button_click")

            active_tickets = await self.bot.db.fetch(
                """SELECT * FROM tickets WHERE user_id=$1 AND active=$2""",
                interaction.user.id,
                True
            )

            if not active_tickets:
                await interaction.respond(content="Ticket has been created, thanks.")
                # the steps to create a category, text channel, and voice channel
                user_overwrites = {
                    bot_server.default_role: discord.PermissionOverwrite(send_messages=False, read_messages=False),
                    interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True)
                }
                parent_category = await bot_server.create_category_channel(
                    name=f"({interaction.component.label.split(' ')[0]}) {interaction.user.name}",
                )
                text_channel = await parent_category.create_text_channel(
                    name="chat",
                    overwrites=user_overwrites
                )
                addons_channel = await parent_category.create_text_channel(
                    name="addons",
                    overwrites=user_overwrites
                )
                control_channel = await parent_category.create_text_channel(
                    name="control-panel",
                    overwrites={
                        bot_server.default_role: discord.PermissionOverwrite(send_messages=False, read_messages=False)
                    }
                )
                # await parent_category.create_text_channel(
                #     name="queue-system",
                #     overwrites={
                #         bot_server.default_role: discord.PermissionOverwrite(send_messages=False, read_messages=False)
                #     }
                # )
                await parent_category.create_voice_channel(
                    name="vc",
                    overwrites={
                        bot_server.default_role: discord.PermissionOverwrite(send_messages=False, read_messages=False),
                        interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True)
                    }
                )

                previous_referrals_query = """
                    SELECT id FROM referrals
                    WHERE user_id=$1
                """
                previous_referrals = await self.bot.db.fetch(previous_referrals_query, interaction.user.id)

                previous_buys_query = """
                    SELECT id FROM customers
                    WHERE user_id=$1
                """
                previous_buys = await self.bot.db.fetch(previous_buys_query, interaction.user.id)

                ticket_embed = discord.Embed()
                ticket_embed.set_author(name=f"{interaction.user} {interaction.component.label}", icon_url=interaction.user.avatar_url)
                ticket_embed.description = f"""
                **{interaction.user}** has made created a new ticket!
                They are wanting the **{interaction.component.label}** package.
                They have made **{len(previous_referrals)}** referrals and **{len(previous_buys)}** transactions.
                """
                ticket_embed_message = await text_channel.send(
                    embed=ticket_embed,
                    content=f"{interaction.user.mention}"
                )


                add_ticket_query = """
                    INSERT INTO tickets (
                        user_id,
                        price,
                        category_id,
                        created_at,
                        active,
                        extra_packages,
                        information_embed_id
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7
                    )
                """
                await self.bot.db.execute(
                    add_ticket_query, 
                    interaction.user.id, 
                    int(interaction.component.label.split(' ')[1].split('$')[1].replace(")", "")),
                    parent_category.id, 
                    datetime.datetime.now(),
                    True,
                    [],
                    ticket_embed_message.id
                )

                
                control_embed = discord.Embed()
                control_embed.set_author(name="Managing Ticket")
                control_embed.description = f"""
                :white_check_mark: - Transaction Complete
                :x: - Cancel Transaction
                """
                control_message = await control_channel.send(
                    embed=control_embed
                )
                await control_message.add_reaction("✅")
                await control_message.add_reaction("❌")

                addon_embed = discord.Embed()
                addon_embed.set_author(name="Picking addons!")
                addon_embed.description = "\n".join([f"**{addon['name']}**" for addon in self.bot.config['order_addons']])
                addon_message = await addons_channel.send(
                    embed=addon_embed
                )
                for addon in self.bot.config['order_addons']:
                    await addon_message.add_reaction(addon['reaction'])

                await queue.send_queue_embed(
                    self.bot,
                    bot_server,
                    self.bot.db
                )
            else:
                await interaction.respond(content="You have hit a limit of concurrent tickets!")

def setup(bot):
    bot.add_cog(Order(bot))
