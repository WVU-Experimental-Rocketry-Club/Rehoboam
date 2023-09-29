import asyncio
import discord
import itertools
import re

from discord.ext import tasks
from oauth2client.service_account import ServiceAccountCredentials
from redbot.core import checks, commands, Config
from redbot.core.utils.chat_formatting import text_to_file
from typing import Union

class Sandpaper(commands.Cog):
    """Sandpaper bot stuff idk"""

    async def red_delete_data_for_user(self, **kwargs):
        """ Nothing to delete """
        return

    def __init__(self, bot):
        self.bot = bot
        self.replychannel = None
        self.config = Config.get_conf(self, 6887658234, force_registration=True)

        default_guild = {
            "guild_id": None,
            "news_disc_channel": None,
            "news_links_channel": None,
            "whitelist": [],
            "blacklist": [],
        }

        self.config.register_guild(**default_guild)
        self._ready: asyncio.Event = asyncio.Event()

    @commands.Cog.listener()
    async def on_message(self, ctx):
        if ctx.guild:
            whitelist = await self.config.guild(ctx.guild).whitelist()
            blacklist = await self.config.guild(ctx.guild).blacklist()
            news_disc_channel = await self.config.guild(ctx.guild).news_disc_channel()
            news_links_channel_ID = await self.config.guild(ctx.guild).news_links_channel()
            news_links_channel = ctx.guild.get_channel(news_links_channel_ID)

            await asyncio.sleep(3)

            if ctx.author.bot:
                return
            elif not ctx.channel.id == news_disc_channel:
                return
            elif ctx.embeds:
            # elif ctx:
                # await news_links_channel.send(ctx.embeds)
                for embed in ctx.embeds:
                    # await news_links_channel.send(embed.url)
                    if any(re.search(fr'^(https://)?([a-z]+\.)*({re.escape(site)})', embed.url, re.IGNORECASE) is not None for site in whitelist):
                        if any(re.search(fr'^(https://)?([a-z]+\.)*({re.escape(site)})', embed.url, re.IGNORECASE) is not None for site in blacklist):
                            return
                        else:
                            await news_links_channel.send(embed.url)
                    else:
                        return
                else:
                    return
        else:
            pass

    @checks.mod_or_permissions(administrator=True)
    @commands.command(name="discussionchannel")
    @commands.guild_only()
    async def news_disc_channel(
            self, ctx, *, channel: Union[discord.TextChannel, discord.VoiceChannel]):
        """Changes the channel where the bot searches for news links."""
        await self.config.guild(ctx.guild).news_disc_channel.set(channel.id)
        await ctx.send(
            ("The news discussion channel has been set to {channel.mention}").format(channel=channel)
        )

    @checks.mod_or_permissions(administrator=True)
    @commands.command(name="linkschannel")
    @commands.guild_only()
    async def news_links_channel(
            self, ctx, *, channel: Union[discord.TextChannel, discord.VoiceChannel]):
        """Changes the channel where the bot posts news links."""
        await self.config.guild(ctx.guild).news_links_channel.set(channel.id)
        await ctx.send(
            ("The news links channel has been set to {channel.mention}").format(channel=channel)
        )

    # @commands.command(name="archive")
    # @commands.guild_only()
    # async def archive(
    #         self, ctx, link: str):
    #     """Archives webpages with archive.is"""
    #     async with ctx.channel.typing():
    #         await asyncio.sleep(.25)
    #     await ctx.send(
    #         'Archiving url...'
    #     )
    #     await ctx.send(
    #         ("")
    #     )

    @commands.group(autohelp=True)
    @commands.guild_only()
    async def wlist(self, ctx):
        """Commands for interacting with the whitelist"""
        pass

    @wlist.command(name="add")
    async def wlink_add(
            self, ctx, *names: str):
        """Adds a news site to the bot's whitelist."""
        whitelist = await self.config.guild(ctx.guild).whitelist()
        if not whitelist:
            await self.config.guild(ctx.guild).whitelist.set([])
        to_add = [name for name in names if name not in whitelist]
        cant_add = [name for name in names if name in whitelist]
        add_string = ""
        cant_string = ""
        if to_add is not []:
            to_add.sort()
            add_string = '\n'.join(map(str, to_add))
        if cant_add is not []:
            cant_add.sort()
            cant_string = '\n'.join(map(str, cant_add))
        for name in to_add:
            whitelist.append(name)
        whitelist.sort()
        await self.config.guild(ctx.guild).whitelist.set(whitelist)
        if cant_string and add_string != "":
            statement = f"Added to whitelist:\n{add_string}\n\nAlready whitelisted:\n{cant_string}"
        elif add_string != "" and cant_string == "":
            statement = f"Added to whitelist:\n{add_string}"
        else:
            statement = f"Already whitelisted:\n{cant_string}"

        await ctx.send(
            f"```{statement}```"
        )

    @wlist.command(name="remove", aliases=["delete"])
    async def wlink_remove(
            self, ctx, *names: str):
        """Remove a news site from the bot's whitelist."""
        whitelist = await self.config.guild(ctx.guild).whitelist()
        if not whitelist:
            await self.config.guild(ctx.guild).whitelist.set([])
        to_remove = [name for name in names if name in whitelist]
        cant_remove = [name for name in names if name not in whitelist]
        remove_string = ""
        cant_string = ""
        if to_remove is not []:
            to_remove.sort()
            remove_string = ', '.join(map(str, to_remove))
        if cant_remove is not []:
            cant_remove.sort()
            cant_string = ', '.join(map(str, cant_remove))
        for name in to_remove:
            whitelist.remove(name)
        whitelist.sort()
        await self.config.guild(ctx.guild).whitelist.set(whitelist)
        if remove_string and cant_string != "":
            statement = f"Removed from whitelist:\n{remove_string}\n\nNot whitelisted:\n{cant_string}"
        elif remove_string != "" and cant_string == "":
            statement = f"Removed from whitelist:\n{remove_string}"
        else:
            statement = f"Not whitelisted:\n{cant_string}"

        await ctx.send(
            f"```{statement}```"
        )

    @wlist.command(name="show", aliases=["view", "display"])
    async def wlist_show(
            self, ctx):
        """Displays the bot's whitelist."""
        whitelist = await self.config.guild(ctx.guild).whitelist()
        list_formatted = ""
        if whitelist is not []:
            list_formatted = '\n'.join(map(str, whitelist))
        try:
            await ctx.send(
            f"```Whitelist:\n{list_formatted}```"
        )
        except:
            wlistfile = text_to_file(list_formatted, filename='whitelist.txt')
            await ctx.send(file=wlistfile)


    @commands.group(autohelp=True)
    @commands.guild_only()
    async def blist(self, ctx):
        """Commands for interacting with the blacklist"""
        pass

    @blist.command(name="add")
    async def blink_add(
            self, ctx, *names: str):
        """Adds a news site to the bot's blacklist."""
        blacklist = await self.config.guild(ctx.guild).blacklist()
        if not blacklist:
            await self.config.guild(ctx.guild).blacklist.set([])
        to_add = [name for name in names if name not in blacklist]
        cant_add = [name for name in names if name in blacklist]
        add_string = ""
        cant_string = ""
        if to_add is not []:
            to_add.sort()
            add_string = ', '.join(map(str, to_add))
        if cant_add is not []:
            cant_add.sort()
            cant_string = ', '.join(map(str, cant_add))
        for name in to_add:
            blacklist.append(name)
        blacklist.sort()
        await self.config.guild(ctx.guild).blacklist.set(blacklist)
        if cant_string and add_string != "":
            statement = f"Added to blacklist:\n{add_string}\n\nAlready blacklisted:\n{cant_string}"
        elif add_string != "" and cant_string == "":
            statement = f"Added to blacklist:\n{add_string}"
        else:
            statement = f"Already blacklisted:\n{cant_string}"

        await ctx.send(
            f"```{statement}```"
        )

    @blist.command(name="remove", aliases=["delete"])
    async def blink_remove(
            self, ctx, *names: str):
        """Remove a news site from the bot's blacklist."""
        blacklist = await self.config.guild(ctx.guild).blacklist()
        if not blacklist:
            await self.config.guild(ctx.guild).blacklist.set([])
        to_remove = [name for name in names if name in blacklist]
        cant_remove = [name for name in names if name not in blacklist]
        remove_string = ""
        cant_string = ""
        if to_remove is not []:
            to_remove.sort()
            remove_string = ', '.join(map(str, to_remove))
        if cant_remove is not []:
            cant_remove.sort()
            cant_string = ', '.join(map(str, cant_remove))
        for name in to_remove:
            blacklist.remove(name)
        blacklist.sort()
        await self.config.guild(ctx.guild).blacklist.set(blacklist)
        if remove_string and cant_string != "":
            statement = f"Removed from blacklist:\n{remove_string}\n\nNot blacklisted:\n{cant_string}"
        elif remove_string != "" and cant_string == "":
            statement = f"Removed from blacklist:\n{remove_string}"
        else:
            statement = f"Not blacklisted:\n{cant_string}"

        await ctx.send(
            f"```{statement}```"
        )

    @blist.command(name="show", aliases=["view", "display"])
    async def blist_show(
            self, ctx):
        """Displays the bot's blacklist."""
        blacklist = await self.config.guild(ctx.guild).blacklist()
        list_formatted = ""
        if blacklist is not []:
            list_formatted = '\n'.join(map(str, blacklist))
        try:
            await ctx.send(
            f"```Blacklist:\n{list_formatted}```"
        )
        except:
            blistfile = text_to_file(list_formatted, filename='blacklist.txt')
            await ctx.send(file=blistfile)