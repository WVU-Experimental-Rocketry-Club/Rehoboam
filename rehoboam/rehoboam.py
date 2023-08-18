import asyncio
import discord
import gspread
import itertools
import json
import pytz
import re
import requests
import time
import calendar
import os
import logging

from datetime import datetime, date, timezone, timedelta
from discord.ext import tasks
from oauth2client.service_account import ServiceAccountCredentials
from redbot.core import checks, commands, Config
from typing import Union
from .dataIO import dataIO

logger = logging.getLogger("red.rehoboam")

class Rehoboam(commands.Cog):
    """Migrates Rocketry Bot functions to Red cog"""

    async def red_delete_data_for_user(self, **kwargs):
        """ Nothing to delete """
        return

    def __init__(self, bot):
        self.bot = bot
        self.replychannel = None
        self.config = Config.get_conf(self, 9738629561, force_registration=True)
        self.events = dataIO.load_json("data/scheduled_events/scheduled_events.json")
        self.check_events.start()

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
            "verified_column": None,
            "joined_column": None,
            "nickname_column": None,
            "username_column": None,
            "sheet_update_count": 0,
            "sheet_loop_freq": 3600,
            "time_lastupdate": 0
        }

        self.config.register_guild(**default_guild)
        self._ready: asyncio.Event = asyncio.Event()

    @commands.group(autohelp=True)
    @commands.guild_only()
    @checks.admin_or_permissions(manage_guild=True)
    async def serverconfig(self, ctx):
        """Config commands for server functions"""
        pass

    @serverconfig.command(name="adminchannel")
    async def adminset_channel(
            self, ctx, *, channel: Union[discord.TextChannel, discord.VoiceChannel]):
        """Changes the channel where the bot will accept admin commands."""
        await self.config.guild(ctx.guild).admin_channel.set(channel.id)
        await ctx.send(
            ("The admin channel has been set to {channel.mention}").format(channel=channel)
        )

    @serverconfig.command(name="clearadminchannel")
    async def adminset_clear_channel(self, ctx):
        """Unsets the channel for admin commands."""
        await self.config.guild(ctx.guild).admin_channel.clear()
        await ctx.send(
            "The admin command channel has been cleared"
        )

    @serverconfig.command(name="dueschannel")
    async def duesset_channel(
            self, ctx, *, channel: Union[discord.TextChannel, discord.VoiceChannel]):
        """Changes the channel where the bot will accept dues verification commands."""
        guild = await self.config.guild(ctx.guild).guild_id()
        if guild is None:
            await self.config.guild(ctx.guild).guild_id.set(ctx.guild.id)

        await self.config.guild(ctx.guild).dues_channel.set(channel.id)
        await ctx.send(
            ("The dues verification channel has been set to {channel.mention}").format(channel=channel)
        )

    @serverconfig.command(name="cleardueschannel")
    async def duesset_clear_channel(self, ctx):
        """Unsets the channel for dues verification commands. Disables dues verification."""
        await self.config.guild(ctx.guild).dues_channel.clear()
        await ctx.send(
            "The dues verification channel has been cleared. Dues verification is now disabled."
        )

    @serverconfig.command(name="logchannel")
    async def logset_channel(
            self, ctx, *, channel: Union[discord.TextChannel, discord.VoiceChannel]):
        """Changes the channel where the bot will send dues log info."""
        await self.config.guild(ctx.guild).dues_log_channel.set(channel.id)
        await ctx.send(
            ("The dues log channel has been set to {channel.mention}").format(channel=channel)
        )

    @serverconfig.command(name="clearlogchannel")
    async def logset_clear_channel(self, ctx):
        """Unsets the channel where the bot sends dues log info. This will disable logging."""
        await self.config.guild(ctx.guild).dues_log_channel.clear()
        await ctx.send(
            "The dues log channel has been cleared. Logging is now disabled."
        )

    @serverconfig.command(name="eventschannel")
    async def eventsset_channel(
            self, ctx, *, channel: Union[discord.TextChannel, discord.VoiceChannel]):
        """Changes the channel where the bot posts scheduled events."""
        await self.config.guild(ctx.guild).events_channel.set(channel.id)
        await ctx.send(
            ("The events channel has been set to {channel.mention}").format(channel=channel)
        )

    @serverconfig.command(name="cleareventschannel")
    async def eventsset_clear_channel(self, ctx):
        """Unsets the channel where the bot posts scheduled events. This will disable scheduled event messages."""
        await self.config.guild(ctx.guild).events_channel.clear()
        await ctx.send(
            "The events channel has been cleared. Automated scheduled events posts are now disabled."
        )

    @commands.group(autohelp=True)
    @commands.guild_only()
    @checks.admin_or_permissions(manage_guild=True)
    async def sheetsconfig(self, ctx):
        """Config commands for Google Sheets integration."""
        pass

    @sheetsconfig.command(name="serverjson")
    async def jsonset(self, ctx, json: str):
        """Sets the Google Sheets JSON file that contains the service account credentials."""
        await self.config.guild(ctx.guild).server_json.set(json)
        await ctx.send(f"The service account json has been set to {json}")

    @sheetsconfig.command(name="clearserverjson")
    async def jsonset_clear(self, ctx):
        """Unsets the Google Sheets JSON file. This will disable dues verification."""
        await self.config.guild(ctx.guild).server_json.clear()
        await ctx.send(
            "The service account json has been cleared. Dues verification is now disabled."
        )

    @sheetsconfig.command(name="duesrange")
    async def duesrangeset(self, ctx, range_open: str, range_close: str):
        """Sets the Google Sheets cell range that contains club dues info as TRUE/FALSE."""
        await self.config.guild(ctx.guild).dues_cells_open.set(range_open)
        await self.config.guild(ctx.guild).dues_cells_close.set(range_close)
        await ctx.send(f"The dues range has been set to {range_open}:{range_close}")

    @sheetsconfig.command(name="clearduesrange")
    async def duesrangeset_clear(self, ctx):
        """Unsets the Google Sheets cell range that contains club dues info. This will disable dues verification."""
        await self.config.guild(ctx.guild).dues_cells_open.clear()
        await self.config.guild(ctx.guild).dues_cells_close.clear()
        await ctx.send(
            "The dues range has been cleared. Dues verification is now disabled."
        )

    @sheetsconfig.command(name="emailsrange")
    async def emailsrangeset(self, ctx, range_open: str, range_close: str):
        """Sets the Google Sheets cell range that contains club emails info as TRUE/FALSE."""
        await self.config.guild(ctx.guild).emails_cells_open.set(range_open)
        await self.config.guild(ctx.guild).emails_cells_close.set(range_close)
        await ctx.send(f"The emails range has been set to {range_open}:{range_close}")

    @sheetsconfig.command(name="clearemailsrange")
    async def emailsrangeset_clear(self, ctx):
        """Unsets the Google Sheets cell range that contains club emails info. This will disable dues verification."""
        await self.config.guild(ctx.guild).emails_cells_open.clear()
        await self.config.guild(ctx.guild).emails_cells_close.clear()
        await ctx.send(
            "The emails range has been cleared. Dues verification is now disabled."
        )

    @sheetsconfig.command(name="verifiedcolumn")
    async def vercolset(self, ctx, column: str):
        """Sets the Google Sheets column that contains user verified info as TRUE/FALSE."""
        await self.config.guild(ctx.guild).verified_column.set(column)
        await ctx.send(f"The user verified column has been set to {column}")

    @sheetsconfig.command(name="clearverifiedcolumn")
    async def vercolset_clear(self, ctx):
        """Unsets the Google Sheets column that contains user verified info as TRUE/FALSE."""
        await self.config.guild(ctx.guild).verified_column.clear()
        await ctx.send(
            "The user verified column has been cleared."
        )

    @sheetsconfig.command(name="joinedcolumn")
    async def joincolset(self, ctx, column: str):
        """Sets the Google Sheets column that contains user joined Discord info as TRUE/FALSE."""
        await self.config.guild(ctx.guild).joined_column.set(column)
        await ctx.send(f"The user joined Discord column has been set to {column}")

    @sheetsconfig.command(name="clearjoinedcolumn")
    async def joincolset_clear(self, ctx):
        """Unsets the Google Sheets column that contains user joined Discord info as TRUE/FALSE."""
        await self.config.guild(ctx.guild).joined_column.clear()
        await ctx.send(
            "The user joined Discord column has been cleared."
        )

    @sheetsconfig.command(name="nicknamecolumn")
    async def nickcolset(self, ctx, column: str):
        """Sets the Google Sheets column that contains server nicknames."""
        await self.config.guild(ctx.guild).nickname_column.set(column)
        await ctx.send(f"The nickname column has been set to {column}")

    @sheetsconfig.command(name="clearnicknamecolumn")
    async def nickcolset_clear(self, ctx):
        """Unsets the Google Sheets column that contains server nicknames."""
        await self.config.guild(ctx.guild).nickname_column.clear()
        await ctx.send(
            "The nickname column has been cleared."
        )

    @sheetsconfig.command(name="usernamecolumn")
    async def namecolset(self, ctx, column: str):
        """Sets the Google Sheets column that contains usernames."""
        await self.config.guild(ctx.guild).username_column.set(column)
        await ctx.send(f"The username column has been set to {column}")

    @sheetsconfig.command(name="clearusernamecolumn")
    async def namecolset_clear(self, ctx):
        """Unsets the Google Sheets column that contains usernames."""
        await self.config.guild(ctx.guild).username_column.clear()
        await ctx.send(
            "The username column has been cleared."
        )

    @sheetsconfig.command(name="sh")
    async def sheetset(self, ctx, sheet: str):
        """
        Sets the Google Sheets sheet name.
        "[Your Sheet Name]"
        """
        await self.config.guild(ctx.guild).sh_name.set(sheet)
        await ctx.send(f"The sheet name has been set to {sheet}")

    @sheetsconfig.command(name="clearsh")
    async def sheet_clear(self, ctx):
        """Unsets the Google Sheets sheet name. This will disable dues verification."""
        await self.config.guild(ctx.guild).sh_name.clear()
        await ctx.send(
            "The sheet name has been cleared. Dues verification is now disabled."
        )

    @sheetsconfig.command(name="wks")
    async def worksheetset(self, ctx, worksheet: str):
        """
        Sets the Google Sheets worksheet name.
        "[Your Worksheet Name]"
        """
        await self.config.guild(ctx.guild).wks_name.set(worksheet)
        await ctx.send(f"The worksheet name has been set to {worksheet}")

    @sheetsconfig.command(name="clearwks")
    async def worksheet_clear(self, ctx):
        """Unsets the Google Sheets worksheet name. This will disable dues verification."""
        await self.config.guild(ctx.guild).wks_name.clear()
        await ctx.send(
            "The worksheet name has been cleared. Dues verification is now disabled."
        )

    @sheetsconfig.command(name="looptime")
    async def sheet_loop_freq_set(self, ctx, hours: int, minutes: int, seconds: int):
        """
        Set Google Sheets data loop frequency.
        :param hours:
        :param minutes:
        :param seconds:
        """
        hrs_sec = hours * 60 * 60
        mins_sec =  minutes * 60
        frequency = hrs_sec + mins_sec + seconds

        interval_format = datetime.time(hour= hours, minute = minutes, second= seconds).isoformat()

        if frequency < 1:
            await ctx.send(
                "Time interval cannot be less than 1 second."
            )
        else:
            await self.config.guild(ctx.guild).sheet_loop_freq.set(frequency)
            await ctx.send(
                f"Sheets data retrieval time interval set to {interval_format}."
            )

    @sheetsconfig.command(name="clearinterval")
    async def sheet_loop_freq_clear(self, ctx):
        """
        Reset Google Sheets data loop frequency to default of 3600 seconds.
        """
        await self.config.guild(ctx.guild).sheet_loop_freq.clear()
        await ctx.send(
            f"Sheets data retrieval time set to 01:00:00."
        )

    @checks.mod_or_permissions(administrator=True)
    @commands.command()
    @commands.guild_only()
    async def reply(
            self, ctx, target_channelID: discord.TextChannel, target_messageID: int, content: str):
        """
        Admin manual replies to user messages
        :param ctx:
        :param target_channelID:
        :param target_messageID:
        :param content:
        :return:
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

    @commands.command()
    @commands.guild_only()
    async def verify(
            self, ctx, mix_email: str
    ):
        """
        Verify club dues for access to members-only channels.
        :param ctx:
        :param mix_email:
        :return:
        """

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
        ver_col = await self.config.guild(ctx.guild).verified_column()
        join_col = await self.config.guild(ctx.guild).joined_column()
        nickname_col = await self.config.guild(ctx.guild).nickname_column()
        username_col = await self.config.guild(ctx.guild).username_column()

        # Connection to specific worksheet
        sheet_name = await self.config.guild(ctx.guild).sh_name()
        worksheet_name = await self.config.guild(ctx.guild).wks_name()
        credentials = ServiceAccountCredentials.from_json_keyfile_dict(app_creds_dictionary, scope)
        sa = gspread.authorize(credentials)
        sh = sa.open(f"{sheet_name}")
        wks = sh.worksheet(f"{worksheet_name}")

        # Server handling bullshit
        roleMember = 'Member'
        roleUnpaid = 'Unpaid Dues'

        g_id = await self.config.guild(ctx.guild).guild_id()
        if g_id is None:
            await self.config.guild(ctx.guild).guild_id.set(ctx.guild.id)

        admin_id = await self.config.guild(ctx.guild).admin_channel()
        if admin_id is None:
            await ctx.reply("""
                        `The channel for admin commands is not set. Use 'adminchannel' command to set the channel. Disregard this message if you are not a server admin`
                        """)
            return
        adminchannel = ctx.guild.get_channel(admin_id)

        dues_id = await self.config.guild(ctx.guild).dues_channel()
        dues_channel = ctx.guild.get_channel(dues_id)

        log_id = await self.config.guild(ctx.guild).dues_log_channel()
        log_channel = ctx.guild.get_channel(log_id)

        if dues_channel is None:
            await adminchannel.send("""
            `The channel for dues verification is not set. Use 'dueschannel' command to set the channel`
            """)
            return
        if dues_json is None:
            await adminchannel.send("""
            `Google Sheets JSON is not set. Use 'serverjson' command to set the file location.`
            """)
            return
        if sheet_name is None:
            await adminchannel.send("""
            `Google Sheets sheet name is not set. Use 'sh' to set the sheet name.`
            """)
            return
        if worksheet_name is None:
            await adminchannel.send("""
            `Google Sheets worksheet name is not set. Use 'wks' to set the sheet name`
            """)
            return
        if dues_range_open is None:
            await adminchannel.send("""
            `Google Sheets dues cell range is has no left bound. Use 'duesrange' to set the bounds.`
            """)
            return
        if dues_range_close is None:
            await adminchannel.send("""
            `Google Sheets dues cell range is has no right bound. Use 'duesrange' to set the bounds.`
            """)
            return
        if emails_range_open is None:
            await adminchannel.send("""
            `Google Sheets emails cell range is has no left bound. Use 'emailsrange' to set the bounds.`
            """)
            return
        if emails_range_close is None:
            await adminchannel.send("""
            `Google Sheets emails cell range is has no right bound. Use 'emailsrange' to set the bounds.`
            """)
            return
        if dues_channel != ctx.channel:
            return

        if '@' in mix_email:
            # Create Flat List from User Message
            mixEmailInit = [mix_email]
            mixEmail = [x.lower() for x in mixEmailInit]

            global counter
            counter = await self.config.guild(ctx.guild).sheet_update_count()
            global time_lastupdate
            time_lastupdate = None
            if counter is not None:
                global emailsListFlat
                global duesListFlat
                global emailsList

                # Create Flat List from Sheets Emails
                emailsList = wks.get(f'{emails_range_open}:{emails_range_close}')
                emailsListFlatInit = list(itertools.chain(*emailsList))
                emailsListFlat = [x.lower() for x in emailsListFlatInit]

                # Create Flat List from Sheets Dues
                duesList = wks.get(f'{dues_range_open}:{dues_range_close}')
                duesListFlatInit = list(itertools.chain(*duesList))
                duesListFlat = [x.lower() for x in duesListFlatInit]

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

                # Check if User Message is in Sheets Email List
                if [email for email in emailsListFlat if email in mixEmail]:
                    # Get Sheets Dues Cell and Verified Cell from Emails List Index
                    rowIndex = emailsListFlat.index(mixEmail[0])
                    emailIndexInit = emailsList.index(mixEmail)
                    emailIndex = emailIndexInit + 2
                    verifiedCell = wks.get(f'{ver_col}{emailIndex}')
                    verifiedCell = verifiedCell[0][0]

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

                    # Paid Dues Not Verified
                    if duesListFlat[rowIndex] == 'true' and verifiedCell == 'FALSE':
                        # Updates roles
                        roleM = discord.utils.get(ctx.guild.roles, name=roleMember)
                        await ctx.author.add_roles(roleM)

                        roleU = discord.utils.get(ctx.guild.roles, name=roleUnpaid)
                        await ctx.author.remove_roles(roleU)

                        # Update 'Joined Discord' and 'Bot Verified' Columns
                        wks.batch_update([{
                            'range': f'{join_col}{emailIndex}:{username_col}{emailIndex}',
                            'values': [['TRUE', 'TRUE', f'{nickname}', f'{username_discriminator}']],
                        }],
                            value_input_option='USER_ENTERED')

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
                        await log_channel.send(f'{ctx.author.mention} has verified dues.')

                    # Paid Dues Already Verified
                    elif duesListFlat[rowIndex] == 'true' and verifiedCell == 'TRUE':
                        async with ctx.channel.typing():
                            await asyncio.sleep(.25)
                        await ctx.send(
                            'Our records show this email has already been used to verify dues. If this was not done by you, please contact an admin to resolve the issue.'
                        )

                    # Unpaid Dues but Somehow Verified
                    elif duesListFlat[rowIndex] == 'false' and verifiedCell == 'TRUE':
                        wks.batch_update([{
                            'range': f'{join_col}{emailIndex}',
                            'values': [['FALSE']],
                        }],
                            value_input_option='USER_ENTERED')

                        # Check if User Has 'Member' Role
                        for role in ctx.author.roles:
                            if str(role) != 'Member':
                                return
                            elif str(role) == 'Member':
                                # Remove 'Member' Role
                                roleM = discord.utils.get(ctx.guild.roles, name=roleMember)
                                await ctx.author.remove_roles(roleM)

                                # Add 'Unpaid Dues' Role
                                roleU = discord.utils.get(ctx.guild.roles, name=roleUnpaid)
                                await ctx.author.add_roles(roleU)
                            else:
                                return

                        # Send Unpaid Dues Message to User
                        async with ctx.channel.typing():
                            await asyncio.sleep(.25)
                        await ctx.send(
                            'Unable to verify dues. Our records show you have not paid dues. Contact an admin for assistance if you believe this is a mistake.'
                        )

                    # Send Unpaid Dues Message to User
                    else:
                        async with ctx.channel.typing():
                            await asyncio.sleep(.25)
                        await ctx.send(
                            'Unable to verify dues. Our records show you have not paid dues. Contact an admin for assistance if you believe this is a mistake.'
                        )

                # Send Email Not Found Message to User
                elif dues_channel == ctx.channel.id:
                    async with ctx.channel.typing():
                        await asyncio.sleep(.25)
                    await ctx.send(
                        'This email does not appear in our records. Please check your message for formatting/spelling errors. Contact an admin for assistance if the problem persists.'
                    )
        else:
            async with ctx.channel.typing():
                await asyncio.sleep(.25)
            await ctx.send(
                'This does not appear to be a valid email. Please check your message for formatting/spelling errors.'
            )

    @commands.Cog.listener()
    async def on_scheduled_event_create(self, ctx):
        events_id = await self.config.guild(ctx.guild).events_channel()
        if events_id is not None:
            eventschannel = ctx.guild.get_channel(events_id)
            event_url = ctx.url
            event_start = ctx.start_time.isoformat()

            self.events.append({"GUILD": ctx.guild.id,"ID": ctx.id, "START": event_start})

            logger.info("New scheduled event ({}) created in {}.".format(ctx.id, ctx.guild.name))
            dataIO.save_json("data/scheduled_events/scheduled_events.json", self.events)

            await eventschannel.send(event_url)

        else:
            return

    @tasks.loop(seconds=5)
    async def check_events(self):
        to_remove = []
        for event in self.events:
            guild = self.bot.get_guild(event["GUILD"])
            scheduled_event_id = event["ID"]
            event_start = event["START"]
            events_id = await self.config.guild(guild).events_channel()
            eventschannel = guild.get_channel(events_id)
            scheduled_event = guild.get_scheduled_event(scheduled_event_id)

            if (datetime.now(timezone.utc) - timedelta(seconds=10)) <= (datetime.fromisoformat(event_start) - timedelta(hours=1)) <= (datetime.now(timezone.utc) + timedelta(seconds=10)):
                try:
                    await eventschannel.send(f"{scheduled_event.url}\nEvent starts in 1 hour.")
                except (discord.errors.Forbidden, discord.errors.NotFound):
                    to_remove.append(event)
                except discord.errors.HTTPException:
                    pass
                else:
                    to_remove.append(event)
            if (datetime.fromisoformat(event_start) - timedelta(hours=1)) <= (datetime.now(timezone.utc) - timedelta(seconds=10)):
                to_remove.append(event)
        for event in to_remove:
            self.events.remove(event)
        if to_remove:
            dataIO.save_json("data/scheduled_events/scheduled_events.json", self.events)

    @check_events.before_loop
    async def before_task(self):
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