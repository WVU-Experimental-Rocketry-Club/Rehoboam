import asyncio
import aiohttp
import discord
import gspread
import itertools
import json
import pytz
import re
import time
import calendar
import os
import logging

from datetime import datetime, date, timezone, timedelta
from discord.ext import tasks
from oauth2client.service_account import ServiceAccountCredentials
from redbot.core import checks, commands, Config
from redbot.core.utils.chat_formatting import humanize_timedelta
from typing import Union
from .dataIO import dataIO

logger = logging.getLogger("red.rehoboam")

class Rehoboam(commands.Cog):
    """Migrates Rocketry Bot functions to Red cog"""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, 9738629561, force_registration=True)
        self.events = dataIO.load_json("data/scheduled_events/scheduled_events.json")
        self.check_events.start()
        self.check_slcf_stock.start()

        default_guild = {
            "guild_id": None,
            "admin_channel": None,
            "dues_channel": None,
            "dues_log_channel": None,
            "events_channel": None,
            "server_json": None,
            "sh_name": None,
            "wks_name": None,
            "dues_cells_open": None,
            "dues_cells_close": None,
            "emails_cells_open": None,
            "emails_cells_close": None,
            "alum_cells_open": None,
            "alum_cells_close": None,
            "ver_cells_open": None,
            "ver_cells_close": None,
            "joined_column": None,
            "nickname_column": None,
            "username_column": None,
            "sheet_update_count": 0,
            "sheetupdatefreq": 0,
            "time_lastupdate": 0,
            "emailsList": [],
            "emailsListFlat": [],
            "duesListFlat": [],
            "alumListFlat": [],
            "verListFlat": [],
            "rowIndex": None,
            "emailIndex": None,
            "roleMember": None,
            "roleUnpaid": None,
            "roleAlum": None,
            "roleAnnouncements": None
        }

        self.config.register_guild(**default_guild)
        self._ready: asyncio.Event = asyncio.Event()

    @commands.group(autohelp=True)
    @commands.guild_only()
    @checks.admin_or_permissions(manage_guild=True)
    async def serverconfig(self, ctx):
        """
        Config commands for server functions
        """
        pass

    @serverconfig.command(name="adminchannel")
    async def adminset_channel(
            self, ctx, *, channel: Union[discord.TextChannel, discord.VoiceChannel]):
        """
        Changes the channel from which the bot will accept admin commands
        `<channel>` the channel to be used
        """
        await self.config.guild(ctx.guild).admin_channel.set(channel.id)
        await ctx.send(
            ("The admin channel has been set to {channel.mention}").format(channel=channel)
        )

    @serverconfig.command(name="clearadminchannel")
    async def adminset_clear_channel(self, ctx):
        """
        Clears the channel for admin commands
        """
        await self.config.guild(ctx.guild).admin_channel.clear()
        await ctx.send(
            "The admin command channel has been cleared"
        )

    @serverconfig.command(name="dueschannel")
    async def duesset_channel(
            self, ctx, *, channel: Union[discord.TextChannel, discord.VoiceChannel]):
        """
        Changes the channel where the bot will accept dues verification commands
        `<channel>` the channel to be used
        """
        guild = await self.config.guild(ctx.guild).guild_id()
        if guild is None:
            await self.config.guild(ctx.guild).guild_id.set(ctx.guild.id)

        await self.config.guild(ctx.guild).dues_channel.set(channel.id)
        await ctx.send(
            ("The dues verification channel has been set to {channel.mention}").format(channel=channel)
        )

    @serverconfig.command(name="logchannel")
    async def logset_channel(
            self, ctx, *, channel: Union[discord.TextChannel, discord.VoiceChannel]):
        """
        Changes the channel where the bot will send dues log info
        `<channel>` the channel to be used
        """
        await self.config.guild(ctx.guild).dues_log_channel.set(channel.id)
        await ctx.send(
            ("The dues log channel has been set to {channel.mention}").format(channel=channel)
        )

    @serverconfig.command(name="clearlogchannel")
    async def logset_clear_channel(self, ctx):
        """
        Unsets the channel where the bot sends dues log info. This will disable logging
        """
        await self.config.guild(ctx.guild).dues_log_channel.clear()
        await ctx.send(
            "The dues log channel has been cleared. Logging is now disabled."
        )

    @serverconfig.command(name="eventschannel")
    async def eventsset_channel(
            self, ctx, *, channel: Union[discord.TextChannel, discord.VoiceChannel]):
        """
        Changes the channel where the bot posts scheduled events
        `<channel>` the channel to be used
        """
        await self.config.guild(ctx.guild).events_channel.set(channel.id)
        await ctx.send(
            ("The events channel has been set to {channel.mention}").format(channel=channel)
        )

    @serverconfig.command(name="cleareventschannel")
    async def eventsset_clear_channel(self, ctx):
        """
        Unsets the channel where the bot posts scheduled events. This will disable scheduled event messages
        """
        await self.config.guild(ctx.guild).events_channel.clear()
        await ctx.send(
            "The events channel has been cleared. Automated scheduled events posts are now disabled."
        )

    @serverconfig.command(name="duesroles")
    async def duesroles_set(
            self, ctx, member: discord.Role = None, unpaid: discord.Role = None, alum: discord.Role = None):
        """
        Sets the roles which the bot will use for verification
        `<member>` member role
        `<unpaid>` unpaid dues role
        `[alum]` alumnus role
        """
        if type(member) is not discord.Role:
            await ctx.send("Member role must be a valid discord role")
            return
        if type(unpaid) is not discord.Role:
            await ctx.send("Unpaid Dues role must be a valid discord role")
            return
        if alum == None:
            await ctx.send(
                f"Server roles have been set.\n```Member: {member.id}\nUnpaid Dues: {unpaid.id}```"
            )
            await self.config.guild(ctx.guild).roleMember.set(member.id)
            await self.config.guild(ctx.guild).roleUnpaid.set(unpaid.id)
            return
        await ctx.send(
            f"Server roles have been set.\n```Member: {member.id}\nUnpaid Dues: {unpaid.id}\nAlumnus: {alum.id}```"
        )
        await self.config.guild(ctx.guild).roleMember.set(member.id)
        await self.config.guild(ctx.guild).roleUnpaid.set(unpaid.id)
        await self.config.guild(ctx.guild).roleAlum.set(alum.id)

    @serverconfig.command(name="announcerole")
    async def announceroles_set(
            self, ctx, announcements: discord.Role):
        """
        Sets the role which the bot will mention for announcements
        `<announcements>` announcements role
        """
        if type(announcements) is not discord.Role:
            await ctx.send("Role must be a valid discord role")
            return
        await ctx.send(
            f"Announcements role has been set.\n```Announcements: {announcements.id}```"
        )
        await self.config.guild(ctx.guild).roleAnnouncements.set(announcements.id)

    @commands.group(autohelp=True)
    @commands.guild_only()
    @checks.admin_or_permissions(manage_guild=True)
    async def sheetsconfig(self, ctx):
        """
        Config commands for Google Sheets integration
        """
        pass

    @sheetsconfig.command(name="serverjson")
    async def jsonset(self, ctx, path: str):
        """
        Sets the Google Sheets JSON file that contains the service account credentials
        `<path>` the full path to the JSON file
        """
        await self.config.guild(ctx.guild).server_json.set(path)
        await ctx.send(f"The service account json has been set to {path}")

    @sheetsconfig.command(name="clearserverjson")
    async def jsonset_clear(self, ctx):
        """
        Unsets the Google Sheets JSON file. This will disable dues verification
        """
        await self.config.guild(ctx.guild).server_json.clear()
        await ctx.send(
            "The service account json has been cleared. Dues verification is now disabled."
        )

    @sheetsconfig.command(name="duesrange")
    async def duesrangeset(self, ctx, range_open: str, range_close: str):
        """
        Sets the Google Sheets cell range that contains club dues info as TRUE/FALSE
        `<range_open>` the cell of the start of the range in A1 notation
        `<range_close>` the cell of the end of the range in A1 notation
        """
        await self.config.guild(ctx.guild).dues_cells_open.set(range_open)
        await self.config.guild(ctx.guild).dues_cells_close.set(range_close)
        await ctx.send(f"The dues range has been set to {range_open}:{range_close}")

    @sheetsconfig.command(name="clearduesrange")
    async def duesrangeset_clear(self, ctx):
        """
        Unsets the Google Sheets cell range that contains club dues info. This will disable dues verification
        """
        await self.config.guild(ctx.guild).dues_cells_open.clear()
        await self.config.guild(ctx.guild).dues_cells_close.clear()
        await ctx.send(
            "The dues range has been cleared. Dues verification is now disabled."
        )

    @sheetsconfig.command(name="emailsrange")
    async def emailsrangeset(self, ctx, range_open: str, range_close: str):
        """
        Sets the Google Sheets cell range that contains club emails info as TRUE/FALSE
        `<range_open>` the cell of the start of the range in A1 notation
        `<range_close>` the cell of the end of the range in A1 notation
        """
        await self.config.guild(ctx.guild).emails_cells_open.set(range_open)
        await self.config.guild(ctx.guild).emails_cells_close.set(range_close)
        await ctx.send(f"The emails range has been set to {range_open}:{range_close}")

    @sheetsconfig.command(name="clearemailsrange")
    async def emailsrangeset_clear(self, ctx):
        """
        Unsets the Google Sheets cell range that contains club emails info. This will disable dues verification
        """
        await self.config.guild(ctx.guild).emails_cells_open.clear()
        await self.config.guild(ctx.guild).emails_cells_close.clear()
        await ctx.send(
            "The emails range has been cleared. Dues verification is now disabled."
        )

    @sheetsconfig.command(name="alumrange")
    async def alumrangeset(self, ctx, range_open: str, range_close: str):
        """
        Sets the Google Sheets cell range that contains club alum info as TRUE/FALSE
        `<range_open>` the cell of the start of the range in A1 notation
        `<range_close>` the cell of the end of the range in A1 notation
        """
        await self.config.guild(ctx.guild).alum_cells_open.set(range_open)
        await self.config.guild(ctx.guild).alum_cells_close.set(range_close)
        await ctx.send(f"The alum range has been set to {range_open}:{range_close}")

    @sheetsconfig.command(name="clearalumrange")
    async def alumrangeset_clear(self, ctx):
        """
        Unsets the Google Sheets cell range that contains club alum info. This will disable dues verification
        """
        await self.config.guild(ctx.guild).alum_cells_open.clear()
        await self.config.guild(ctx.guild).alum_cells_close.clear()
        await ctx.send(
            "The alum range has been cleared. Dues verification is now disabled."
        )

    @sheetsconfig.command(name="verrange")
    async def verrangeset(self, ctx, range_open: str, range_close: str):
        """
        Sets the Google Sheets cell range that contains member verified info as TRUE/FALSE
        `<range_open>` the cell of the start of the range in A1 notation
        `<range_close>` the cell of the end of the range in A1 notation
        """
        await self.config.guild(ctx.guild).ver_cells_open.set(range_open)
        await self.config.guild(ctx.guild).ver_cells_close.set(range_close)
        await ctx.send(f"The verified range has been set to {range_open}:{range_close}")

    @sheetsconfig.command(name="clearverrange")
    async def verrangeset_clear(self, ctx):
        """
        Unsets the Google Sheets cell range that contains member verified info. This will disable dues verification
        """
        await self.config.guild(ctx.guild).ver_cells_open.clear()
        await self.config.guild(ctx.guild).ver_cells_close.clear()
        await ctx.send(
            "The verified range has been cleared. Dues verification is now disabled."
        )

    @sheetsconfig.command(name="joinedcolumn")
    async def joincolset(self, ctx, column: str):
        """
        Sets the Google Sheets column that contains user joined Discord info as TRUE/FALSE
        `<column>` the letter of the column
        """
        await self.config.guild(ctx.guild).joined_column.set(column)
        await ctx.send(f"The user joined Discord column has been set to {column}")

    @sheetsconfig.command(name="clearjoinedcolumn")
    async def joincolset_clear(self, ctx):
        """
        Unsets the Google Sheets column that contains user joined Discord info as TRUE/FALSE
        """
        await self.config.guild(ctx.guild).joined_column.clear()
        await ctx.send(
            "The user joined Discord column has been cleared."
        )

    @sheetsconfig.command(name="nicknamecolumn")
    async def nickcolset(self, ctx, column: str):
        """
        Sets the Google Sheets column that contains server nicknames
        `<column>` the letter of the column
        """
        await self.config.guild(ctx.guild).nickname_column.set(column)
        await ctx.send(f"The nickname column has been set to {column}")

    @sheetsconfig.command(name="clearnicknamecolumn")
    async def nickcolset_clear(self, ctx):
        """
        Unsets the Google Sheets column that contains server nicknames
        """
        await self.config.guild(ctx.guild).nickname_column.clear()
        await ctx.send(
            "The nickname column has been cleared."
        )

    @sheetsconfig.command(name="usernamecolumn")
    async def namecolset(self, ctx, column: str):
        """
        Sets the Google Sheets column that contains usernames
        `<column>` the letter of the column
        """
        await self.config.guild(ctx.guild).username_column.set(column)
        await ctx.send(f"The username column has been set to {column}")

    @sheetsconfig.command(name="clearusernamecolumn")
    async def namecolset_clear(self, ctx):
        """
        Unsets the Google Sheets column that contains usernames
        """
        await self.config.guild(ctx.guild).username_column.clear()
        await ctx.send(
            "The username column has been cleared."
        )

    @sheetsconfig.command(name="sh")
    async def sheetset(self, ctx, sheet: str):
        """
        Sets the Google Sheets sheet name.
        `<sheet>` the name of the sheet. "[Your Sheet Name]"
        """
        await self.config.guild(ctx.guild).sh_name.set(sheet)
        await ctx.send(f"The sheet name has been set to {sheet}")

    @sheetsconfig.command(name="clearsh")
    async def sheet_clear(self, ctx):
        """
        Unsets the Google Sheets sheet name. This will disable dues verification.
        """
        await self.config.guild(ctx.guild).sh_name.clear()
        await ctx.send(
            "The sheet name has been cleared. Dues verification is now disabled."
        )

    @sheetsconfig.command(name="wks")
    async def worksheetset(self, ctx, worksheet: str):
        """
        Sets the Google Sheets worksheet name.
        `<worksheet>` the name of the worksheet. "[Your Worksheet Name]"
        """
        await self.config.guild(ctx.guild).wks_name.set(worksheet)
        await ctx.send(f"The worksheet name has been set to {worksheet}")

    @sheetsconfig.command(name="clearwks")
    async def worksheet_clear(self, ctx):
        """
        Unsets the Google Sheets worksheet name. This will disable dues verification.
        """
        await self.config.guild(ctx.guild).wks_name.clear()
        await ctx.send(
            "The worksheet name has been cleared. Dues verification is now disabled."
        )

    @sheetsconfig.command(name="updatefreq")
    async def freqset(self, ctx, seconds: int):
        """
        Sets the Google Sheets data retrieval frequency.
        `<seconds>` the interval at which new sheets data will be retrieved in seconds
        """
        await self.config.guild(ctx.guild).sheetupdatefreq.set(seconds)
        await ctx.send(f"The data retrieval frequency has been set to {seconds} seconds")

    @sheetsconfig.command(name="clearupdatefreq")
    async def freq_clear(self, ctx):
        """
        Resets the Google Sheets data retrieval frequency. Default is 0 seconds. New data will be retrieved on every use of [p]verify.
        """
        await self.config.guild(ctx.guild).sheetupdatefreq.clear()
        await ctx.send(
            "The data retrieval frequency has been reset."
        )

    @checks.mod_or_permissions(administrator=True)
    @commands.command()
    @commands.guild_only()
    async def reply(
            self, ctx, target_channelID: discord.TextChannel, target_messageID: int, content: str):
        """
        Admin manual replies to user messages
        `<channel>` Channel containing target message
        `<message>` ID of target message
        `<content>` Content of message to send as a reply
        """
        # Check for Valid Channel
        admin_channel = await self.config.guild(ctx.guild).admin_channel()
        if admin_channel is not None:
            if admin_channel != ctx.channel.id:
                return
            else:
                try:
                    # Error if Reply Content Empty
                    if content == '':
                        await ctx.send(
                            'Reply content cannot be empty.'
                        )
                    # Send Reply
                    else:
                        reply_message = await target_channelID.fetch_message(target_messageID)
                        await reply_message.reply(content)

                # Catch-All Error Message
                except:
                    await ctx.send(
                        'Error in command.'
                    )
        elif admin_channel is None:
            try:
                # Error if Reply Content Empty
                if content == '':
                    await ctx.send(
                        'Reply content cannot be empty.'
                    )
                # Send Reply
                else:
                    reply_message = await target_channelID.fetch_message(target_messageID)
                    await reply_message.reply(content)

            # Catch-All Error Message
            except:
                await ctx.send(
                    'Error in command.'
                )

    # noinspection NonAsciiCharacters
    @commands.command()
    @commands.guild_only()
    async def verify(
            self, ctx, mix_email: str, alum: str = None
    ):
        """
        Verify club dues or alumni status for access to members-only channels.
        `<mix email>` Your full WVU mix email.
        `<alum>` If verifying alum status, write "alum". Otherwise, leave blank
        """
        # Declare vars as global
        global emailsListFlat
        global duesListFlat
        global alumListFlat
        global verListFlat
        global rowIndex
        global emailIndex
        global time_lastupdate

        # Get channel IDs
        dues_id = await self.config.guild(ctx.guild).dues_channel()
        dues_channel = ctx.guild.get_channel(dues_id)

        admin_id = await self.config.guild(ctx.guild).admin_channel()
        adminchannel = ctx.guild.get_channel(admin_id)

        log_id = await self.config.guild(ctx.guild).dues_log_channel()
        log_channel = ctx.guild.get_channel(log_id)

        # Check channels
        if admin_id is None:
            await ctx.reply("""
                        `The channel for admin commands is not set. Use '[p]serverconfig adminchannel' command to set the channel. Disregard this message if you are not a server admin`
                        """)
            return

        if dues_channel is None:
            await adminchannel.send("""
            `The channel for dues verification is not set. Use '[p]serverconfig dueschannel' command to set the channel`
            """)
            return

        if ctx.channel != dues_channel:
            return

        # Check alum str
        if alum is not None:
            alum = alum.lower()
            if alum != "alum":
                await ctx.send("Invalid argument in command. Please use `[p]help verify` to view command information. ")
                return

        if '@' in mix_email:
            # Create Flat List from User Message
            mixEmailInit = [mix_email]
            mixEmail = [x.lower() for x in mixEmailInit]

            await googlesheetsfetch(self, ctx, mixEmail)

            # Get vars from self
            emailsListFlat = await self.config.guild(ctx.guild).emailsListFlat()
            duesListFlat = await self.config.guild(ctx.guild).duesListFlat()
            alumListFlat = await self.config.guild(ctx.guild).alumListFlat()
            verListFlat = await self.config.guild(ctx.guild).verListFlat()
            rowIndex = await self.config.guild(ctx.guild).rowIndex()
            emailIndex = await self.config.guild(ctx.guild).emailIndex()
            time_lastupdate = await self.config.guild(ctx.guild).time_lastupdate()

            # Send Email Not Found Message to User
            if ctx.channel == dues_channel and (rowIndex == None or emailIndex == None):
                async with ctx.channel.typing():
                    await asyncio.sleep(.25)
                await ctx.send(
                    'This email does not appear in our records. Please check your message for formatting/spelling errors. Contact an admin for assistance if the problem persists.'
                )
                await clearindex(self, ctx)
                return

        # Get role vars from self
        roleMember = await self.config.guild(ctx.guild).roleMember()
        roleUnpaid = await self.config.guild(ctx.guild).roleUnpaid()
        roleAlum = await self.config.guild(ctx.guild).roleAlum()

        # Get Nickname and Username
        nickname = ctx.message.author.display_name
        if type(nickname) is not str:
            nickname = ""
        username = ctx.message.author.name
        discriminator = ctx.message.author.discriminator
        if type(username) is not str or type(discriminator) is not str:
            username_discriminator = ""
        else:
            username_discriminator = f"{username}#{discriminator}"

        # Check if User is Alumnus. Code 1
        if alum == "alum":
            if alumListFlat[rowIndex].lower() == 'true' and verListFlat[rowIndex].lower() == 'false':
                # Write to sheet
                code = 1
                await googlesheetswrite(self, ctx, code, nickname, username_discriminator)

                # Updates roles
                roleA = discord.utils.get(ctx.guild.roles, id=roleAlum)
                await ctx.author.add_roles(roleA)

                roleM = discord.utils.get(ctx.guild.roles, id=roleMember)
                roleU = discord.utils.get(ctx.guild.roles, id=roleUnpaid)
                await ctx.author.remove_roles(roleM, roleU)

                # DM Verified User
                await ctx.author.send(
                    f'Thank you for verifying in the {ctx.guild.name} server!'
                )

                # Log to Verification Log
                await log_channel.send(
                    f'{ctx.author.mention} has verified alumni status with the email `{mix_email.lower()}`.'
                )

                if time_lastupdate != 0:
                    await self.config.guild(ctx.guild).time_lastupdate.set(1)
                await clearindex(self, ctx)
                return

            elif alumListFlat[rowIndex].lower() == 'true' and verListFlat[rowIndex].lower() == 'true':
                async with ctx.channel.typing():
                    await asyncio.sleep(.25)
                await ctx.send(
                    'Our records show this email has already been used to verify. Please contact an admin to resolve the issue.'
                )

                await clearindex(self, ctx)
                return

            elif alumListFlat[rowIndex].lower() == 'false' and verListFlat[rowIndex].lower() == 'true':
                async with ctx.channel.typing():
                    await asyncio.sleep(.25)
                await ctx.send(
                    'Our records show this email does not belong to an alumnus. If this is incorrect, please contact an admin to resolve the issue.'
                )

                await clearindex(self, ctx)
                return

            elif alumListFlat[rowIndex].lower() == 'false' and verListFlat[rowIndex].lower() == 'false':
                async with ctx.channel.typing():
                    await asyncio.sleep(.25)
                await ctx.send(
                    'Our records show this email does not belong to an alumnus. If this is incorrect, please contact an admin to resolve the issue.'
                )

                await clearindex(self, ctx)
                return

        # Paid Dues Not Verified. Code 2
        if duesListFlat[rowIndex].lower() == 'true' and verListFlat[rowIndex].lower() == 'false':
            # Write to sheet
            code = 2
            await googlesheetswrite(self, ctx, code, nickname, username_discriminator)

            # Updates roles
            roleM = discord.utils.get(ctx.guild.roles, id=roleMember)
            await ctx.author.add_roles(roleM)

            roleU = discord.utils.get(ctx.guild.roles, id=roleUnpaid)
            await ctx.author.remove_roles(roleU)

            # DM Verified User
            今天 = date.today().replace(year=1)
            今年 = date.today().year
            元旦 = date(year=1, month=1, day=1)
            年中 = date(year=1, month=8, day=1)
            除夕 = date(year=1, month=12, day=31)

            if 元旦<=今天<年中:
                學年 = f"{今年-1}-{今年} "
            elif 年中<=今天<=除夕:
                學年 = f"{今年}-{今年+1} "
            else:
                學年 = f"\u2060"

            await ctx.author.send(
                f'Thank you for verifying your {學年}dues in the {ctx.guild.name} server!'
            )

            # Log to Verification Log
            await log_channel.send(
                f'{ctx.author.mention} has verified dues with the email `{mix_email.lower()}`.'
            )

            if time_lastupdate != 0:
                await self.config.guild(ctx.guild).time_lastupdate.set(1)
            await clearindex(self, ctx)
            return

        # Paid Dues Already Verified
        elif duesListFlat[rowIndex].lower() == 'true' and verListFlat[rowIndex].lower() == 'true':
            async with ctx.channel.typing():
                await asyncio.sleep(.25)
            await ctx.send(
                'Our records show this email has already been used to verify dues. If this was not done by you, please contact an admin to resolve the issue.'
            )

            await clearindex(self, ctx)
            return

        # Unpaid Dues but Somehow Verified. Code 3
        elif duesListFlat[rowIndex].lower() == 'false' and verListFlat[rowIndex].lower() == 'true':
            # Write to sheet
            code = 3
            await googlesheetswrite(self, ctx, code, None, None)

            # Check if User Has 'Member' Role
            for role in ctx.author.roles:
                if str(role) == 'Member':
                    # Remove 'Member' Role
                    roleM = discord.utils.get(ctx.guild.roles, id=roleMember)
                    await ctx.author.remove_roles(roleM)

                    # Add 'Unpaid Dues' Role
                    roleU = discord.utils.get(ctx.guild.roles, id=roleUnpaid)
                    await ctx.author.add_roles(roleU)

            # Send Unpaid Dues Message to User
            async with ctx.channel.typing():
                await asyncio.sleep(.25)
            await ctx.send(
                'Unable to verify dues. Our records show you have not paid dues. Contact an admin for assistance if you believe this is a mistake.'
            )

            await clearindex(self, ctx)
            return

        # Send Unpaid Dues Message to User
        else:
            async with ctx.channel.typing():
                await asyncio.sleep(.25)
            await ctx.send(
                'Unable to verify dues. Our records show you have not paid dues. Contact an admin for assistance if you believe this is a mistake.'
            )

            await clearindex(self, ctx)
            return

    @commands.guild_only()
    @checks.admin_or_permissions(manage_events=True)
    @commands.command(name="eventalert")
    async def event_alert(self, ctx, eventid: int, true_false: str, hours: int = 1):
        """
        Sets the alert details for a scheduled event
        `<ID>` event ID
        `<toggle>` alert status. true or false
        `[hours]` number of hours before start to alert. default is 1
        """
        if type(eventid) is not int:
            await ctx.send("Event ID must be an integer")
            return
        if type(true_false) is not str:
            await ctx.send("Event toggle must be either `true` or `false`")
            return
        if true_false.lower() != "true" and true_false.lower() != "false":
            await ctx.send("Event toggle must be either `true` or `false`")
            return
        if type(hours) is not int:
            await ctx.send("Hours must be an integer")
            return

        if eventid not in [event["ID"] for event in self.events]:
            await ctx.send(f"Could not find event with ID `{eventid}`")

        if true_false.lower() == "false":
            for event in self.events:
                if event["ID"] == eventid:
                    try:
                        event["ALERT"] = "FALSE"
                        getevent = ctx.guild.get_scheduled_event(eventid)
                        try:
                            dataIO.save_json("data/scheduled_events/scheduled_events.json", self.events)
                            await ctx.send(f"Alert disabled for event `{getevent.name}` with ID `{eventid}`")
                        except:
                            logger.info("Could not save events JSON")
                            await ctx.send("`Error. Check your console or logs for details`")
                    except:
                        await ctx.send(f"Could not find event with ID `{eventid}`")

        if true_false.lower() == "true":
            for event in self.events:
                if event["ID"] == eventid:
                    try:
                        event["ALERT"] = "TRUE"
                        event["BEFORE"] = hours
                        delta = timedelta(hours=hours)
                        time_str = humanize_timedelta(timedelta=delta)
                        getevent = ctx.guild.get_scheduled_event(eventid)
                        try:
                            dataIO.save_json("data/scheduled_events/scheduled_events.json", self.events)
                            await ctx.send(f"Alert enabled for event `{getevent.name}` with ID `{eventid}`.\nSet to {time_str} before start.")
                        except:
                            logger.info("Could not save events JSON")
                            await ctx.send("`Error. Check your console or logs for details`")
                    except:
                        await ctx.send(f"Could not find event with ID `{eventid}`")

    @commands.Cog.listener()
    async def on_scheduled_event_create(self, ctx):
        events_id = await self.config.guild(ctx.guild).events_channel()
        if events_id is not None:
            eventschannel = ctx.guild.get_channel(events_id)
            event_url = ctx.url
            event_start = ctx.start_time.isoformat()

            self.events.append({"GUILD": ctx.guild.id,"ID": ctx.id,"START": event_start,"ALERT": "TRUE","BEFORE": 1})

            logger.info("New scheduled event ({}) created in {}.".format(ctx.id, ctx.guild.name))
            dataIO.save_json("data/scheduled_events/scheduled_events.json", self.events)

            await eventschannel.send(event_url)
        else:
            return

    @commands.Cog.listener()
    async def on_scheduled_event_update(self, before, after):
        events_id = await self.config.guild(after.guild).events_channel()
        if events_id is None:
            return
        if after.id not in [event["ID"] for event in self.events]:
            try:
                self.events.append({"GUILD": after.guild.id, "ID": after.id, "START": after.start_time.isoformat()})
                try:
                    logger.info("New scheduled event ({}) created in {}.".format(after.id, after.guild.name))
                    dataIO.save_json("data/scheduled_events/scheduled_events.json", self.events)
                except:
                    logger.info("Could not save events JSON")
            except:
                logger.info(f"Could not add event {after.id}")
        elif before.start_time == after.start_time:
            return
        else:
            for event in self.events:
                if event["ID"] == after.id and event["START"] != after.start_time.isoformat():
                    try:
                        event["START"] = after.start_time.isoformat()
                        try:
                            dataIO.save_json("data/scheduled_events/scheduled_events.json", self.events)
                        except:
                            logger.info("Could not save events JSON")
                    except:
                        logger.info(f"Could not modify start time for event {after.id}")

    @tasks.loop(seconds=5)
    async def check_events(self):
        global to_remove
        global to_alert
        to_remove = []
        to_alert = []

        for event in self.events:
            try:
                event_alert = event["ALERT"]
            except:
                event_alert = "TRUE"
            try:
                event_before = event["BEFORE"]
            except:
                event_before = 1
            event_start = event["START"]
            if event_alert == "TRUE":
                if (datetime.now(timezone.utc) - timedelta(seconds=10)) <= (datetime.fromisoformat(event_start) - timedelta(hours=event_before)) <= (datetime.now(timezone.utc) + timedelta(seconds=10)):
                    to_alert.append(event)
            if (datetime.fromisoformat(event_start) - timedelta(hours=event_before)) <= (datetime.now(timezone.utc) - timedelta(seconds=10)):
                to_remove.append(event)

        for event in to_alert:
            guild = self.bot.get_guild(event["GUILD"])
            scheduled_event_id = event["ID"]
            before_alert = event["BEFORE"]
            events_id = await self.config.guild(guild).events_channel()
            eventschannel = guild.get_channel(events_id)
            scheduled_event = guild.get_scheduled_event(scheduled_event_id)

            delta = timedelta(hours=before_alert)
            time_str = humanize_timedelta(timedelta=delta)

            try:
                await eventschannel.send(f"Event starts in {time_str}.\n{scheduled_event.url}")
            except (discord.errors.Forbidden, discord.errors.NotFound):
                to_remove.append(event)
            except discord.errors.HTTPException:
                pass
            else:
                to_remove.append(event)

        for event in to_remove:
            try:
                self.events.remove(event)
            except:
                logger.info(f"Could not remove event {event['ID']}")

        if to_remove:
            try:
                dataIO.save_json("data/scheduled_events/scheduled_events.json", self.events)
            except:
                logger.info("Could not save events JSON")

    @tasks.loop(seconds=15)
    async def check_slcf_stock(self):
        """Task to check if SLCF is in stock.  Active while SLCF is OUT of stock, sending a message once it becomes IN
        stock """

        url = 'https://www.perfectflitedirect.com/stratologgercf-altimeter/'
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as slcf_obj:
                response = await slcf_obj.text()
                if 'Out of Stock' not in response and '<div class="Label QuantityInput" style="display: ">Quantity:</div>' in response:
                    rocketry_id = 972627157513797643
                    rocketry_guild = await self.bot.get_guild(rocketry_id)
                    channel = await self.config.guild(rocketry_guild).events_channel()
                    announce_id = await self.bot.guild(rocketry_guild).roleAnnouncements()

                    if announce_id is not None:
                        announce_role = await self.bot.guild(rocketry_guild).get_role(announce_id)
                        message = f"{announce_role.mention}\nStratoLogger CF is back in stock!\nhttps://www.perfectflitedirect.com/stratologgercf-altimeter/"

                        # Send message, start the out of stock task, cancel this task
                        await channel.send(message)
                        self.check_slcf_oostock.start()
                        self.check_slcf_stock.cancel()

                    else:
                        message = f"StratoLogger CF is back in stock!\nhttps://www.perfectflitedirect.com/stratologgercf-altimeter/"

                        # Send message, start the out of stock task, cancel this task
                        await channel.send(message)
                        self.check_slcf_oostock.start()
                        self.check_slcf_stock.cancel()

    @tasks.loop(seconds=15)
    async def check_slcf_oostock(self):
        """Task to check if SLCF is out of stock.  Active while SLCF is IN stock, sending a message once it becomes OUT
        of stock """
        url = 'https://www.perfectflitedirect.com/stratologgercf-altimeter/'
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as slcf_obj:
                response = await slcf_obj.text()
                if 'Out of Stock' in response:
                    rocketry_id = 972627157513797643
                    rocketry_guild = await self.bot.get_guild(rocketry_id)
                    channel = await self.config.guild(rocketry_guild).events_channel()

                    message = "\nStratoLogger CF is out of stock.\nI will notify when it is back in stock."

                    # Send message, start the out of stock task, cancel this task
                    await channel.send(message)
                    self.check_slcf_stock.cancel()
                    self.check_slcf_oostock.start()

    @check_events.before_loop
    async def before_task(self):
        await self.bot.wait_until_ready()

    @check_slcf_stock.before_loop
    async def before_task2(self):
        await self.bot.wait_until_ready()

def check_folders():
    if not os.path.exists("data/scheduled_events"):
        print("Creating data/scheduled_events folder...")
        os.makedirs("data/scheduled_events")

def check_files():
    f = "data/scheduled_events/scheduled_events.json"
    if not dataIO.is_valid_json(f):
        print("Creating empty scheduled_events.json...")
        dataIO.save_json(f, [])

async def googlesheetsfetch(self, ctx, mixEmail):
    global counter
    global time_lastupdate
    global emailsListFlat
    global duesListFlat
    global emailsList
    time_diff = await self.config.guild(ctx.guild).sheetupdatefreq()
    time_lastupdate = await self.config.guild(ctx.guild).time_lastupdate()
    time_now = time.time()

    if (time_now - time_diff) < time_lastupdate:
        code = 1
    else:
        code = 2

    if code == 1:
        # Get vars from self
        emailsList = await self.config.guild(ctx.guild).emailsList()
        emailsListFlat = await self.config.guild(ctx.guild).emailsListFlat()
        duesListFlat = await self.config.guild(ctx.guild).duesListFlat()

        # Check if User Message is in Sheets Email List
        if [email for email in emailsListFlat if email in mixEmail]:
            # Get Sheets Dues Cell and Verified Cell from Emails List Index
            rowIndex = emailsListFlat.index(mixEmail[0])
            emailIndexInit = emailsList.index(mixEmail)
            emailIndex = emailIndexInit + 2

            # Write vars to self
            await self.config.guild(ctx.guild).rowIndex.set(rowIndex)
            await self.config.guild(ctx.guild).emailIndex.set(emailIndex)

    elif code == 2:
        # Google
        scope = ["https://spreadsheets.google.com/feeds",
                 "https://www.googleapis.com/auth/spreadsheets",
                 "https://www.googleapis.com/auth/drive.file",
                 "https://www.googleapis.com/auth/drive"]

        dues_json = await self.config.guild(ctx.guild).server_json()
        app_json = open(f'{dues_json}')
        app_creds_dictionary = json.load(app_json)

        # Ranges and whatnot
        dues_range_open = await self.config.guild(ctx.guild).dues_cells_open()
        dues_range_close = await self.config.guild(ctx.guild).dues_cells_close()
        emails_range_open = await self.config.guild(ctx.guild).emails_cells_open()
        emails_range_close = await self.config.guild(ctx.guild).emails_cells_close()
        alum_range_open = await self.config.guild(ctx.guild).alum_cells_open()
        alum_range_close = await self.config.guild(ctx.guild).alum_cells_close()
        ver_range_open = await self.config.guild(ctx.guild).ver_cells_open()
        ver_range_close = await self.config.guild(ctx.guild).ver_cells_close()

        # Connection to specific worksheet
        sheet_name = await self.config.guild(ctx.guild).sh_name()
        worksheet_name = await self.config.guild(ctx.guild).wks_name()
        credentials = ServiceAccountCredentials.from_json_keyfile_dict(app_creds_dictionary, scope)
        sa = gspread.authorize(credentials)
        sh = sa.open(f"{sheet_name}")
        wks = sh.worksheet(f"{worksheet_name}")

        # Check for all vars
        g_id = await self.config.guild(ctx.guild).guild_id()
        if g_id is None:
            await self.config.guild(ctx.guild).guild_id.set(ctx.guild.id)

        admin_id = await self.config.guild(ctx.guild).admin_channel()
        adminchannel = ctx.guild.get_channel(admin_id)

        if dues_json is None:
            await adminchannel.send("""
            `Google Sheets JSON is not set. Use '[p]sheetsconfig serverjson' command to set the file location.`
            """)
            return
        if sheet_name is None:
            await adminchannel.send("""
            `Google Sheets sheet name is not set. Use '[p]sheetsconfig sh' to set the sheet name.`
            """)
            return
        if worksheet_name is None:
            await adminchannel.send("""
            `Google Sheets worksheet name is not set. Use '[p]sheetsconfig wks' to set the sheet name`
            """)
            return
        if dues_range_open is None:
            await adminchannel.send("""
            `Google Sheets dues cell range has no left bound. Use '[p]sheetsconfig duesrange' to set the bounds.`
            """)
            return
        if dues_range_close is None:
            await adminchannel.send("""
            `Google Sheets dues cell range has no right bound. Use '[p]sheetsconfig duessrange' to set the bounds.`
            """)
            return
        if emails_range_open is None:
            await adminchannel.send("""
            `Google Sheets emails cell range has no left bound. Use '[p]sheetsconfig emailsrange' to set the bounds.`
            """)
            return
        if emails_range_close is None:
            await adminchannel.send("""
            `Google Sheets emails cell range has no right bound. Use '[p]sheetsconfig emailsrange' to set the bounds.`
            """)
            return
        if alum_range_open is None:
            await adminchannel.send("""
            `Google Sheets alum cell range has no left bound. Use '[p]sheetsconfig alumrange' to set the bounds.`
            """)
            return
        if alum_range_close is None:
            await adminchannel.send("""
            `Google Sheets alum cell range has no right bound. Use '[p]sheetsconfig alumrange' to set the bounds.`
            """)
            return
        if ver_range_open is None:
            await adminchannel.send("""
            `Google Sheets verified cell range has no left bound. Use '[p]sheetsconfig verrange' to set the bounds.`
            """)
            return
        if ver_range_close is None:
            await adminchannel.send("""
            `Google Sheets verified cell range has no right bound. Use '[p]sheetsconfig verrange' to set the bounds.`
            """)
            return

        counter = await self.config.guild(ctx.guild).sheet_update_count()
        time_lastupdate = None
        if counter is not None:
            # Create Flat List from Sheets Emails
            emailsList = wks.get(f'{emails_range_open}:{emails_range_close}')
            emailsListFlatInit = list(itertools.chain(*emailsList))
            emailsListFlat = [x.lower() for x in emailsListFlatInit]

            # Create Flat List from Sheets Dues
            duesList = wks.get(f'{dues_range_open}:{dues_range_close}')
            duesListFlatInit = list(itertools.chain(*duesList))
            duesListFlat = [x.lower() for x in duesListFlatInit]

            # Create Flat List from Sheet Alums
            alumList = wks.get(f'{alum_range_open}:{alum_range_close}')
            alumListFlatInit = list(itertools.chain(*alumList))
            alumListFlat = [x.lower() for x in alumListFlatInit]

            # Create Flat List from Sheet Verified
            verList = wks.get(f'{ver_range_open}:{ver_range_close}')
            verListFlatInit = list(itertools.chain(*verList))
            verListFlat = [x.lower() for x in verListFlatInit]

            # Write vars to self
            await self.config.guild(ctx.guild).emailsList.set(emailsList)
            await self.config.guild(ctx.guild).emailsListFlat.set(emailsListFlat)
            await self.config.guild(ctx.guild).duesListFlat.set(duesListFlat)
            await self.config.guild(ctx.guild).alumListFlat.set(alumListFlat)
            await self.config.guild(ctx.guild).verListFlat.set(verListFlat)

            # Check if User Message is in Sheets Email List
            if [email for email in emailsListFlat if email in mixEmail]:
                # Get Sheets Dues Cell and Verified Cell from Emails List Index
                rowIndex = emailsListFlat.index(mixEmail[0])
                emailIndexInit = emailsList.index(mixEmail)
                emailIndex = emailIndexInit + 2

                # Write vars to self
                await self.config.guild(ctx.guild).rowIndex.set(rowIndex)
                await self.config.guild(ctx.guild).emailIndex.set(emailIndex)
            else:
                await self.config.guild(ctx.guild).rowIndex.set(None)
                await self.config.guild(ctx.guild).emailIndex.set(None)

            # Print Sheets Data Retrieval Info to Channel
            counter = counter + 1
            try:
                # If OS is MacOS
                await adminchannel.send(
                    time.strftime(f"""
                    `Sheets data successfully retrieved at %-I:%M:%S %p.\nFetch {counter}\n`
                    """)
                )
            except ValueError:
                # If OS is Windows
                await adminchannel.send(
                    time.strftime(f"""
                    `Sheets data successfully retrieved at %#I:%M:%S %p.\nFetch {counter}\n`
                    """)
                )
            await self.config.guild(ctx.guild).sheet_update_count.set(counter)
            await self.config.guild(ctx.guild).time_lastupdate.set(time.time())

async def googlesheetswrite(self, ctx, code: int, nickname = None, username_discriminator = None):
    if type(code) is not int:
        await ctx.send(f'Error in function `googlesheetswrite`\nCode is type `{type(code)}`')
    # Google
    scope = ["https://spreadsheets.google.com/feeds",
             "https://www.googleapis.com/auth/spreadsheets",
             "https://www.googleapis.com/auth/drive.file",
             "https://www.googleapis.com/auth/drive"]

    dues_json = await self.config.guild(ctx.guild).server_json()
    app_json = open(f'{dues_json}')
    app_creds_dictionary = json.load(app_json)

    # Ranges and whatnot
    join_col = await self.config.guild(ctx.guild).joined_column()
    username_col = await self.config.guild(ctx.guild).username_column()
    emailIndex = await self.config.guild(ctx.guild).emailIndex()

    # Connection to specific worksheet
    sheet_name = await self.config.guild(ctx.guild).sh_name()
    worksheet_name = await self.config.guild(ctx.guild).wks_name()
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(app_creds_dictionary, scope)
    sa = gspread.authorize(credentials)
    sh = sa.open(f"{sheet_name}")
    wks = sh.worksheet(f"{worksheet_name}")

    if code == 1 or code == 2:
        # Update 'Joined Discord' and 'Bot Verified' Columns
        wks.batch_update([{
            'range': f'{join_col}{emailIndex}:{username_col}{emailIndex}',
            'values': [['TRUE', 'TRUE', f'{nickname}', f'{username_discriminator}']],
        }],
            value_input_option='USER_ENTERED')
    elif code == 3:
        wks.batch_update([{
            'range': f'{join_col}{emailIndex}',
            'values': [['FALSE']],
        }],
            value_input_option='USER_ENTERED')
    else:
        ctx.send(f'Error in function `googlesheetswrite`\nInvalid code. Code is `code`')
        return

async def clearindex(self,ctx):
    await self.config.guild(ctx.guild).rowIndex.set(None)
    await self.config.guild(ctx.guild).emailIndex.set(None)