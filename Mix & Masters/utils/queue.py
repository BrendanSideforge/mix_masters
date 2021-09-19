
import discord

from .priority import Priority

async def send_queue_embed(bot, server, db):

    tickets = await db.fetch("SELECT * FROM tickets")
    priorities = []

    for ticket in tickets:
        previous_transactions = len(await db.fetch("SELECT id FROM customers WHERE user_id=$1", ticket['user_id']))
        referrals = len(await db.fetch("SELECT id FROM referrals WHERE referred_id=$1", ticket['user_id']))
        addons = ticket['extra_packages']

        priorities.append(Priority(
            bot,
            ticket,
            referrals,
            previous_transactions,
            ticket['price'],
            addons if addons else []
        ))

    sorted_priorities = sorted(priorities, key=lambda priority: priority.total_points, reverse=True)
    embed_format = []

    if sorted_priorities:

        for priority in sorted_priorities:
            # print(priority.ticket_information['user_id'], priority.total_points, priority.referrals, priority.previous_transactions)
            chat_channels = [channel for channel in server.text_channels if channel.category.id  == priority.ticket_information['category_id'] and channel.name == "control-panel"]
            ticket_channel = chat_channels[0]

            embed_format.append(
                f"**{sorted_priorities.index(priority)+1}.** `${priority.price}` {ticket_channel.mention} for <@{priority.ticket_information['user_id']}>"
            )

        embed = discord.Embed(color=discord.Color.blue())
        embed.title = "Ranked Orders"
        embed.description = "\n".join(embed_format)

        for priority in sorted_priorities:
            queue_channels = [channel for channel in server.text_channels if channel.category.id  == priority.ticket_information['category_id'] and channel.name == "control-panel"]
            try:
                channel_message_to_delete = await queue_channels[0].fetch_message(queue_channels[0].last_message_id)
                if channel_message_to_delete.embeds[0].title == "Ranked Orders":
                    await channel_message_to_delete.delete()
            except:
                pass
            await queue_channels[0].send(embed=embed)
