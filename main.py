import os
import asyncio
from datetime import datetime, timezone, timedelta
import discord
from discord.ext import commands

WAITING_ROOM_VOICE = 1472654310696419349
JOKEZ_VOICE = 1339052615832567811
CROWS_VOICE = 1474894816088162365
PVP1_VOICE = 1339057971803586590
PVP2_VOICE = 1339058001818157207
VIP_VOICE = 1459658590347460782

CROW_ALERTS_CHANNEL = 1517316662641033236
JOIN_VOICE_CHANNEL = 1512195785633042644
CONTROL_PANEL_CHANNEL = 1512208972436869280
LOGS_CHANNEL = 1339060870197678231

AUDIENCE_ROLE = 1339057300098252820
JOKERZ_ROLE = 1339053887616712787
KAWKAW_ROLE = 1356415745285689344
BOUNCER_ROLE = 1339058493520478240
PINK_ROLE = 1339053520934146058

PANEL_COLOR = discord.Color.from_rgb(255, 165, 0)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True       
intents.moderation = True    
intents.voice_states = True  
intents.emojis = False
intents.typing = False
intents.presences = False

member_cache = discord.MemberCacheFlags.all()
member_cache.voice = True

ignored_mass_moves = set()

bot = commands.Bot(
    command_prefix="!", 
    intents=intents,
    member_cache_flags=member_cache,
    max_messages=0  
)

async def mass_move_users(interaction: discord.Interaction, source_ids: list, target_id: int) -> list:
    guild = interaction.guild
    author = interaction.user

    if not author.voice or not author.voice.channel:
        await interaction.response.send_message("You must be connected to a voice channel.", ephemeral=True)
        return []

    target_channel = guild.get_channel(target_id)
    if not target_channel:
        await interaction.response.send_message("Error: Target voice channel not found.", ephemeral=True)
        return []

    channels_to_sweep = [ch for cid in source_ids if (ch := guild.get_channel(cid))]
    if not channels_to_sweep:
        await interaction.response.send_message("Error: No valid source channels found.", ephemeral=True)
        return []

    await interaction.response.defer(ephemeral=True)

    moved_users = []
    for channel in channels_to_sweep:
        for member in list(channel.members):
            try:
                ignored_mass_moves.add(member.id)
                await member.move_to(target_channel)
                moved_users.append(member)
            except discord.DiscordException:
                ignored_mass_moves.discard(member.id)
                continue

    await interaction.followup.send(f"Moved **{len(moved_users)}** member(s) to {target_channel.mention}.", ephemeral=True)
    return moved_users

async def log_mass_move(guild, action_title, moved_users, author=None):
    if not moved_users:
        return
        
    log_channel = guild.get_channel(LOGS_CHANNEL)
    if not log_channel:
        return

    mentions_str = ", ".join([m.mention for m in moved_users])

    embed = discord.Embed(
        title=action_title,
        description=f"**Users:**\n{mentions_str}",
        color=PANEL_COLOR,
    )
    
    if author:
        icon_url = author.display_avatar.url if author.display_avatar else None
        embed.set_author(name=author.display_name, icon_url=icon_url)
    
    try:
        await log_channel.send(embed=embed)
    except discord.DiscordException:
        pass

class DynamicApproveJoinView(discord.ui.View):
    def __init__(self, target_user_id: int = None):
        super().__init__(timeout=None)
        if target_user_id:
            self.approve_button.custom_id = f"app_uj:{target_user_id}"

    @discord.ui.button(label="Approve", style=discord.ButtonStyle.green, custom_id="app_uj:0")
    async def approve_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            target_user_id = int(interaction.data['custom_id'].split(":")[1])
        except (IndexError, ValueError, KeyError):
            await interaction.response.send_message("Error: Request error.", ephemeral=True)
            return

        guild = interaction.guild
        target_user = guild.get_member(target_user_id) or await guild.fetch_member(target_user_id)
        start_channel = guild.get_channel(WAITING_ROOM_VOICE)
        jokez_channel = guild.get_channel(JOKEZ_VOICE)
        crows_channel = guild.get_channel(CROWS_VOICE)

        if not start_channel or not jokez_channel or not crows_channel:
            await interaction.response.send_message("Error: Voice channels not found.", ephemeral=True)
            return

        if not target_user or target_user not in start_channel.members:
            user_mention = target_user.mention if target_user else f"<@{target_user_id}>"
            await interaction.response.send_message(f"{user_mention} is no longer in the waiting voice channel.", ephemeral=True)
            return

        target_channel = crows_channel if len(crows_channel.members) > len(jokez_channel.members) else jokez_channel

        try:
            await target_user.move_to(target_channel)
            button.disabled = True
            button.label = f"Moved to {target_channel.name}"
            button.style = discord.ButtonStyle.secondary
            await interaction.response.edit_message(view=self)
        except discord.Forbidden:
            await interaction.response.send_message("You don't have permission to move members.", ephemeral=True)
        except discord.DiscordException as e:
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)

class JoinVoiceChannelsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def handle_join(self, interaction: discord.Interaction, target_channel_id: int):
        guild = interaction.guild
        user = interaction.user

        if not user.voice or not user.voice.channel:
            await interaction.response.send_message("You must be connected to a voice channel first.", ephemeral=True)
            return

        target_channel = guild.get_channel(target_channel_id)
        if not target_channel:
            await interaction.response.send_message("Error: Target voice channel not found.", ephemeral=True)
            return

        try:
            await user.move_to(target_channel)
            await interaction.response.send_message(f"You joined {target_channel.mention}.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("The bot doesn't have permission to move you.", ephemeral=True)
        except discord.DiscordException as e:
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)

    @discord.ui.button(label="Join 🤣┃jokez", style=discord.ButtonStyle.success, custom_id="join_jokez_vc")
    async def join_jokez(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_join(interaction, JOKEZ_VOICE)

    @discord.ui.button(label="Join 🐔┃crows", style=discord.ButtonStyle.danger, custom_id="join_crows_vc")
    async def join_crows(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_join(interaction, CROWS_VOICE)

    @discord.ui.button(label="Join 🗡️┃pvp 1", style=discord.ButtonStyle.blurple, custom_id="join_pvp1_vc")
    async def join_pvp1(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_join(interaction, PVP1_VOICE)

    @discord.ui.button(label="Join ⚔️┃pvp 2", style=discord.ButtonStyle.blurple, custom_id="join_pvp2_vc")
    async def join_pvp2(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_join(interaction, PVP2_VOICE)

class ControlPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Move all users to 🤣┃jokez", style=discord.ButtonStyle.success, custom_id="move_to_jokez")
    async def move_to_jokez_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        target_channel = interaction.guild.get_channel(JOKEZ_VOICE)
        moved_users = await mass_move_users(interaction, [CROWS_VOICE, WAITING_ROOM_VOICE, PVP1_VOICE, PVP2_VOICE, VIP_VOICE], JOKEZ_VOICE)
        if moved_users and target_channel:
            await log_mass_move(interaction.guild, "Mass Move to 🤣┃jokez", moved_users, author=interaction.user)

    @discord.ui.button(label="Move all users to 🐔┃crows", style=discord.ButtonStyle.danger, custom_id="move_to_crows")
    async def move_to_crows_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        target_channel = interaction.guild.get_channel(CROWS_VOICE)
        moved_users = await mass_move_users(interaction, [JOKEZ_VOICE, WAITING_ROOM_VOICE, PVP1_VOICE, PVP2_VOICE, VIP_VOICE], CROWS_VOICE)
        if moved_users and target_channel:
            await log_mass_move(interaction.guild, "Mass Move to 🐔┃crows", moved_users, author=interaction.user)

    @discord.ui.button(label="Officer Meeting 💎┃vip", style=discord.ButtonStyle.blurple, custom_id="move_bouncers_to_vip")
    async def move_bouncers_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        author = interaction.user

        if not author.voice or not author.voice.channel:
            await interaction.response.send_message("You must be connected to a voice channel.", ephemeral=True)
            return

        vip_channel = guild.get_channel(VIP_VOICE)
        if not vip_channel:
            await interaction.response.send_message("Error: VIP voice channel not found.", ephemeral=True)
            return

        channels_to_scan = [ch for cid in [JOKEZ_VOICE, CROWS_VOICE, WAITING_ROOM_VOICE, PVP1_VOICE, PVP2_VOICE] if (ch := guild.get_channel(cid))]
        if not channels_to_scan:
            await interaction.response.send_message("Error: No channels found.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        bouncer_role = guild.get_role(BOUNCER_ROLE)

        moved_users = []
        for ch in channels_to_scan:
            for member in list(ch.members):
                if bouncer_role in member.roles:
                    try:
                        ignored_mass_moves.add(member.id)
                        await member.move_to(vip_channel)
                        moved_users.append(member)
                    except discord.DiscordException:
                        ignored_mass_moves.discard(member.id)
                        continue

        await interaction.followup.send(f"Moved **{len(moved_users)}** Bouncer(s) to {vip_channel.mention}.", ephemeral=True)
        if moved_users:
            await log_mass_move(guild, "Officer Meeting 💎┃vip", moved_users, author=interaction.user)

    @discord.ui.button(label="📢┃Crow Alert", style=discord.ButtonStyle.secondary, custom_id="crow_button", row=1)
    async def crow_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        ping_channel = guild.get_channel(CROW_ALERTS_CHANNEL)

        if not ping_channel:
            await interaction.response.send_message("Error: Crows channel not found.", ephemeral=True)
            return

        now = datetime.now(timezone.utc)
        future_times = [
            t if (t := now.replace(hour=h, minute=30, second=0, microsecond=0)) > now else t + timedelta(days=1)
            for h in [1, 4, 7, 10, 13, 16, 19, 22]
        ]

        unix_timestamp = int(min(future_times).timestamp())

        embed = discord.Embed(
            title="KAWKAW",
            description=f"**Crow's Cache** spawns <t:{unix_timestamp}:R>!",
            color=PANEL_COLOR
        )

        embed.set_author(name=f"{interaction.user.display_name} is requesting reinforcements", icon_url=interaction.user.display_avatar.url)
        embed.set_thumbnail(url="https://i.imgur.com/89JOBF6.png")

        try:
            await ping_channel.send(content=f"<@&{AUDIENCE_ROLE}><@&{JOKERZ_ROLE}><@&{KAWKAW_ROLE}>", embed=embed)
            await interaction.response.send_message(f"Created alert in {ping_channel.mention}.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("Error: Bot does not have permission to post in that channel.", ephemeral=True)
        except discord.DiscordException as e:
            await interaction.response.send_message(f"Error: {e}", ephemeral=True)

class MemberJoinDropdown(discord.ui.Select):
    def __init__(self, user_id: int = 0):
        options = [
            discord.SelectOption(label="Audience", emoji="🟢", value=str(AUDIENCE_ROLE)),
            discord.SelectOption(label="Jokez", emoji="🟠", value=str(JOKERZ_ROLE)),
            discord.SelectOption(label="Kawkaw", emoji="🟡", value=str(KAWKAW_ROLE))
        ]
        super().__init__(
            placeholder="Promote", 
            min_values=1, 
            max_values=1, 
            options=options, 
            custom_id=f"jr_select:{user_id}"
        )

    async def callback(self, interaction: discord.Interaction):
        try:
            target_user_id = int(self.custom_id.split(":")[1])
        except (IndexError, ValueError):
            await interaction.response.send_message("Error processing request.", ephemeral=True)
            return

        role_id = int(self.values[0])
        guild = interaction.guild
        member = guild.get_member(target_user_id) or await guild.fetch_member(target_user_id)
        role = guild.get_role(role_id)

        if not member:
            await interaction.response.send_message("This member is no longer in the server.", ephemeral=True)
            return
        if not role:
            await interaction.response.send_message("Error: Role not found.", ephemeral=True)
            return

        try:
            await member.add_roles(role)
            await interaction.response.send_message(f"Successfully added {role.mention} to {member.mention}.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("The bot does not have permissions to manage roles.", ephemeral=True)
        except discord.DiscordException as e:
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)

class MemberJoinView(discord.ui.View):
    def __init__(self, user_id: int = 0):
        super().__init__(timeout=None)
        self.add_item(MemberJoinDropdown(user_id))

@bot.event
async def on_message(message):
    if message.guild is None and message.author.id == 314300380051668994:
        parts = message.content.split(" ", 1)
        if len(parts) == 2 and parts[0].isdigit():
            if channel := bot.get_channel(int(parts[0])):
                try:
                    await channel.send(parts[1])
                except discord.DiscordException:
                    pass

    await bot.process_commands(message)

@bot.event
async def on_voice_state_update(member, before, after):
    if member.id in ignored_mass_moves:
        ignored_mass_moves.discard(member.id)
        return

    if after.channel and after.channel.id == WAITING_ROOM_VOICE:
        jokez_channel = member.guild.get_channel(JOKEZ_VOICE)
        if jokez_channel:
            try:
                await member.move_to(jokez_channel)
            except discord.HTTPException:
                pass
        return

    if after.channel and (not before.channel or before.channel.id != after.channel.id):
        log_channel = member.guild.get_channel(LOGS_CHANNEL)
        if log_channel:
            embed = discord.Embed(
                description=f"{member.mention} joined **{after.channel.name}**.",
                color=PANEL_COLOR
            )
            if member.avatar:
                embed.set_author(name=member.display_name, icon_url=member.avatar.url)
            
            try:
                await log_channel.send(embed=embed)
            except discord.DiscordException:
                pass

@bot.event
async def on_member_join(member):
    log_channel = member.guild.get_channel(LOGS_CHANNEL)
    if log_channel:
        embed = discord.Embed(
            description=f"{member.mention} joined the server.",
            color=PANEL_COLOR
        )
        if member.avatar:
            embed.set_author(name=member.display_name, icon_url=member.avatar.url)
        else:
            embed.set_author(name=member.display_name)
        
        view = MemberJoinView(user_id=member.id)
        try:
            await log_channel.send(embed=embed, view=view)
        except discord.DiscordException:
            pass

@bot.event
async def on_member_remove(member):
    log_channel = member.guild.get_channel(LOGS_CHANNEL)
    if not log_channel:
        return

    description = f"{member.mention} left the server."
    guild = member.guild

    try:
        async for entry in guild.audit_logs(action=discord.AuditLogAction.kick, limit=1):
            if entry.target.id == member.id and (datetime.now(timezone.utc) - entry.created_at).total_seconds() < 10:
                description = f"{entry.user.mention} kicked {member.mention}"
                if entry.reason:
                    description += f"\n**Reason:** {entry.reason}"
                break
    except discord.Forbidden:
        pass
    except discord.DiscordException:
        pass

    embed = discord.Embed(description=description, color=PANEL_COLOR)
    if member.avatar:
        embed.set_author(name=member.display_name, icon_url=member.avatar.url)
    else:
        embed.set_author(name=member.display_name)

    try:
        await log_channel.send(embed=embed)
    except discord.DiscordException:
        pass

@bot.event
async def on_member_ban_add(guild, user):
    log_channel = guild.get_channel(LOGS_CHANNEL)
    if not log_channel:
        return

    description = f"{user.mention} was banned from the server."

    try:
        async for entry in guild.audit_logs(action=discord.AuditLogAction.ban, limit=1):
            if entry.target.id == user.id:
                description = f"{entry.user.mention} banned {user.mention}"
                if entry.reason:
                    description += f"\n**Reason:** {entry.reason}"
                break
    except discord.Forbidden:
        pass
    except discord.DiscordException:
        pass

    embed = discord.Embed(description=description, color=PANEL_COLOR)
    if user.avatar:
        embed.set_author(name=user.display_name, icon_url=user.avatar.url)
    else:
        embed.set_author(name=user.display_name)

    try:
        await log_channel.send(embed=embed)
    except discord.DiscordException:
        pass

@bot.event
async def on_ready():
    bot.add_view(JoinVoiceChannelsView())
    bot.add_view(ControlPanelView())
    bot.add_view(DynamicApproveJoinView())
    bot.add_view(MemberJoinView())

    async def setup_panel(channel_id, title, desc, view_obj):
        if not (channel := bot.get_channel(channel_id)):
            return
        async for message in channel.history(limit=1):
            if message.author == bot.user and message.embeds and message.embeds[0].title == title:
                return
        await channel.send(embed=discord.Embed(title=title, description=desc, color=PANEL_COLOR), view=view_obj)

    await setup_panel(JOIN_VOICE_CHANNEL, "Join Voice Channels", "You must be in a voice channel before you can click a button.", JoinVoiceChannelsView())
    await setup_panel(CONTROL_PANEL_CHANNEL, "Control Panel", "Click the following buttons for their intended use.", ControlPanelView())
    print(f"Logged in as {bot.user}")
    
bot.run(os.environ['TOKEN'])
