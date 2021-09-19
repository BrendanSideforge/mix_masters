
# installed PyPi packages
import discord
from discord.ext import commands
from discord.ext.commands import Cog
from discord_components import DiscordComponents, Button, ButtonStyle, Select, SelectOption

class About(Cog):
    def __init__(self, bot):
        self.bot = bot

    @Cog.listener()
    async def on_ready(self):
        about_channel = self.bot.get_channel(self.bot.config['about_channel_id'])
        try:
            about_message_to_delete = await about_channel.fetch_message(about_channel.last_message_id)
            await about_message_to_delete.delete()
        except:
            pass

        about_me_image = discord.File("./icons/aboutMeImage1.png", "aboutMeImage.png")

        about_embed = discord.Embed()
        about_embed.title = "ABOUT OUR COMPANY"
        about_embed.description = """
        Mix & Masters is a premium service where YOU can get professional mixing and mastering for your projects at an affordable rate. We offer same day delivery for those who order from our Premium package as well as peer-to-peer consultation for all of our services. We have over 14 years of experience in post-production and audio engineering and over 20 thousand dollars worth of equipment to satisfy even the most demanding projects. Whether you're here to give your single that professional sheen it needs for its debut or you need exceptional engineering for your entire album, we are ready to match your ambitions no matter the challenges they present. 
        """
        about_embed.set_footer(text="We mix for masters of their crafts; don't forgo your project's sonic quality and begin your journey in the industry today!")
        about_embed.set_image(url="attachment://aboutMeImage.png")
        await about_channel.send(file=about_me_image, embed=about_embed)

def setup(bot):
    bot.add_cog(About(bot))
