import os
import time
import asyncio
from datetime import datetime, timezone, timedelta
import discord
from discord.ext import commands

JOKEZ_VOICE = 1339052615832567811
CROWS_VOICE = 1474894816088162365
PVP1_VOICE = 1339057971803586590
PVP2_VOICE = 1339058001818157207
WAITING_ROOM_VOICE = 1472654310696419349
VIP_VOICE = 1459658590347460782

JOIN_VOICE_CHANNEL = 1512195785633042644
CONTROL_PANEL_CHANNEL = 1512208972436869280
REQUESTS_CHANNEL = 1512205620751765515
CROWS_CHANNEL = 1356415359367778498

PINK_ROLE = 1339053520934146058
AUDIENCE_ROLE = 1339057300098252820
BOUNCER_ROLE = 1339058493520478240
KAWKAW_ROLE = 1356415745285689344

PANEL_COLOR = discord.Color.from_rgb(255, 165, 0)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

request_cooldowns = {}

class ApproveJoinView(discord.ui.View):
    def __init__(self, target_user: discord.Member = None):
        super().__init__(timeout=None)
        self.target_user = target_user

    @discord.ui.button(label="Approve", style=discord.ButtonStyle.green, custom_id="approve_button_fixed")
    async def approve_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.target_user:
            await interaction.response.send_message("Error: Session expired for this request.", ephemeral=True)
            return

        guild = interaction.guild
        start_channel = guild.get_channel(WAITING_ROOM_VOICE)
        target_channel = guild.get_channel(JOKEZ_VOICE)

        if not start_channel or not target_channel:
            await interaction.response.send_message("Error: Voice channels not found.", ephemeral=True)
            return

        if self.target_user not in start_channel.members:
            await interaction.response.send_message(
                f"{self.target_user.mention} is no longer in the waiting voice channel.", 
                ephemeral=True
            )
            return

        try:
            await self.target_user.move_to(target_channel)

            button.disabled = True
            button.label = "Joined"
            button.style = discord.ButtonStyle.secondary

            await interaction.response.edit_message(view=self)

        except discord.Forbidden:
            await interaction.response.send_message(
                "You don't have permission to move members.", 
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"An error occurred: {e}", 
                ephemeral=True
            )

class RequestJoinView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Request", style=discord.ButtonStyle.blurple, custom_id="request_join_fixed")
    async def request_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user_id = interaction.user.id
        current_time = time.time()

        if user_id in request_cooldowns:
            remaining_time = request_cooldowns[user_id] - current_time
            if remaining_time > 0:
                await interaction.response.send_message(
                    f"You can request again in **{int(remaining_time)}** seconds.", 
                    ephemeral=True
                )
                return

        log_channel = guild.get_channel(REQUESTS_CHANNEL)
        waiting_room = guild.get_channel(WAITING_ROOM_VOICE)

        if not waiting_room or interaction.user not in waiting_room.members:
            await interaction.response.send_message(
                f"You must be in the <#{WAITING_ROOM_VOICE}> voice channel to make this request!", 
                ephemeral=True
            )
            return

        if not log_channel:
            await interaction.response.send_message(
                "Error: Request channel not found.", 
                ephemeral=True
            )
            return

        request_cooldowns[user_id] = current_time + 60

        embed = discord.Embed(
            description=f"{interaction.user.mention} has requested to join <#{JOKEZ_VOICE}>",
            color=PANEL_COLOR
        )

        if interaction.user.avatar:
            embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url)

        approval_view = ApproveJoinView(target_user=interaction.user)
        mention_text = f"<@&{BOUNCER_ROLE}>"

        await log_channel.send(content=mention_text, embed=embed, view=approval_view)

        await interaction.response.send_message(
            f"Your request has been sent to <@&{BOUNCER_ROLE}>", 
            ephemeral=True
        )

class ControlPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Move all users to 🤣┃jokez", style=discord.ButtonStyle.success, custom_id="move_to_jokez_fixed")
    async def move_to_jokez_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        author = interaction.user

        if not author.voice or not author.voice.channel:
            await interaction.response.send_message(
                "You must be connected to a voice channel.", 
                ephemeral=True
            )
            return

        jokez_channel = guild.get_channel(JOKEZ_VOICE)

        if not jokez_channel:
            await interaction.response.send_message("Error: Jokez voice channel not found.", ephemeral=True)
            return

        channels_to_sweep = []
        for channel_id in [CROWS_VOICE, WAITING_ROOM_VOICE, PVP1_VOICE, PVP2_VOICE, VIP_VOICE]:
            ch = guild.get_channel(channel_id)
            if ch:
                channels_to_sweep.append(ch)

        if not channels_to_sweep:
            await interaction.response.send_message("Error: No channels found.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        async def safe_move(member):
            try:
                await member.move_to(jokez_channel)
                return True
            except Exception:
                return False

        moved_count = 0

        for channel in channels_to_sweep:
            if not channel.members:
                continue

            results = await asyncio.gather(*[safe_move(m) for m in channel.members])
            moved_count += sum(1 for r in results if r)

        await interaction.followup.send(
            f"Moved **{moved_count}** member(s) to {jokez_channel.mention}.", 
            ephemeral=True
        )

    @discord.ui.button(label="Move all users to 🐔┃crows", style=discord.ButtonStyle.danger, custom_id="move_to_crows_fixed")
    async def move_to_crows_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        author = interaction.user

        if not author.voice or not author.voice.channel:
            await interaction.response.send_message(
                "You must be connected to a voice channel.", 
                ephemeral=True
            )
            return

        crows_channel = guild.get_channel(CROWS_VOICE)

        if not crows_channel:
            await interaction.response.send_message("Error: Crows voice channel not found.", ephemeral=True)
            return

        channels_to_sweep = []
        for channel_id in [JOKEZ_VOICE, WAITING_ROOM_VOICE, PVP1_VOICE, PVP2_VOICE, VIP_VOICE]:
            ch = guild.get_channel(channel_id)
            if ch:
                channels_to_sweep.append(ch)

        if not channels_to_sweep:
            await interaction.response.send_message("Error: No channels found.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        async def safe_move(member):
            try:
                await member.move_to(crows_channel)
                return True
            except Exception:
                return False

        moved_count = 0

        for channel in channels_to_sweep:
            if not channel.members:
                continue

            results = await asyncio.gather(*[safe_move(m) for m in channel.members])
            moved_count += sum(1 for r in results if r)

        await interaction.followup.send(
            f"Moved **{moved_count}** member(s) to {crows_channel.mention}.", 
            ephemeral=True
        )

    @discord.ui.button(label="Officer Meeting 💎┃vip", style=discord.ButtonStyle.blurple, custom_id="move_bouncers_to_vip_fixed")
    async def move_bouncers_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        author = interaction.user

        if not author.voice or not author.voice.channel:
            await interaction.response.send_message(
                "You must be connected to a voice channel.", 
                ephemeral=True
            )
            return

        vip_channel = guild.get_channel(VIP_VOICE)
        if not vip_channel:
            await interaction.response.send_message("Error: VIP voice channel not found.", ephemeral=True)
            return

        channels_to_scan = []
        for channel_id in [JOKEZ_VOICE, CROWS_VOICE, WAITING_ROOM_VOICE, PVP1_VOICE, PVP2_VOICE]:
            channel = guild.get_channel(channel_id)
            if channel:
                channels_to_scan.append(channel)

        if not channels_to_scan:
            await interaction.response.send_message("Error: No channels found.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        bouncer_role = guild.get_role(BOUNCER_ROLE)

        async def safe_move_bouncer(member):
            if bouncer_role in member.roles:
                try:
                    await member.move_to(vip_channel)
                    return True
                except Exception:
                    return False
            return False

        moved_count = 0

        for channel in channels_to_scan:
            if not channel.members:
                continue

            results = await asyncio.gather(*[safe_move_bouncer(m) for m in channel.members])
            moved_count += sum(1 for r in results if r)

        await interaction.followup.send(
            f"Moved **{moved_count}** Bouncer(s) to {vip_channel.mention}.", 
            ephemeral=True
        )

    @discord.ui.button(label="📢┃Crow Alert", style=discord.ButtonStyle.secondary, custom_id="kawkaw_button_fixed", row=1)
    async def kawkaw_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        ping_channel = guild.get_channel(CROWS_CHANNEL)

        if not ping_channel:
            await interaction.response.send_message("Error: Kawkaw channel not found.", ephemeral=True)
            return

        now = datetime.now(timezone.utc)
        target_hours = [1, 4, 7, 10, 13, 16, 19, 22]
        future_times = []

        for hour in target_hours:
            t = now.replace(hour=hour, minute=30, second=0, microsecond=0)
            if t < now:
                t += timedelta(days=1)
            future_times.append(t)

        closest_target = min(future_times)
        delta = closest_target - now

        # Convert remaining time to total minutes (rounded down)
        total_minutes = int(delta.total_seconds()) // 60
        hours, minutes = divmod(total_minutes, 60)

        # Apply custom time format
        if hours > 0:
            time_str = f"{hours} hours, {minutes} minutes"
        else:
            time_str = f"{minutes} minutes"

        try:
            await ping_channel.send(f"<@&{KAWKAW_ROLE}> - An officer ({interaction.user.mention}) is requesting your attention! (Time until next: **{time_str}**)")
            await interaction.response.send_message(f"Successfully pinged <@&{KAWKAW_ROLE}> in {ping_channel.mention}.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("Error: Bot does not have permission to post in that channel.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Error: {e}", ephemeral=True)

@bot.event
async def on_ready():
    bot.add_view(ApproveJoinView())
    bot.add_view(RequestJoinView())
    bot.add_view(ControlPanelView())

    req_channel = bot.get_channel(JOIN_VOICE_CHANNEL)
    if req_channel:
        req_exists = False
        async for message in req_channel.history(limit=20):
            if message.author == bot.user and len(message.embeds) > 0:
                if message.embeds[0].title == "Request to Join":
                    req_exists = True
                    break

        if not req_exists:
            embed = discord.Embed(
                title="Request to Join",
                description="Click the button to request to join the 🤣┃jokez voice channel.",
                color=PANEL_COLOR
            )
            await req_channel.send(embed=embed, view=RequestJoinView())

    ctrl_channel = bot.get_channel(CONTROL_PANEL_CHANNEL)
    if ctrl_channel:
        ctrl_exists = False
        async for message in ctrl_channel.history(limit=20):
            if message.author == bot.user and len(message.embeds) > 0:
                if message.embeds[0].title == "Control Panel":
                    ctrl_exists = True
                    break

        if not ctrl_exists:
            embed = discord.Embed(
                title="Control Panel",
                description="Welcome to the Control Panel. Click the respective buttons for their intended use.",
                color=PANEL_COLOR
            )
            await ctrl_channel.send(embed=embed, view=ControlPanelView())

bot.run(os.environ['TOKEN'])
