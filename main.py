import os
import time
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

async def mass_move_users(interaction: discord.Interaction, source_ids: list, target_id: int):
		guild = interaction.guild
		author = interaction.user

		if not author.voice or not author.voice.channel:
				await interaction.response.send_message("You must be connected to a voice channel.", ephemeral=True)
				return

		target_channel = guild.get_channel(target_id)
		if not target_channel:
				await interaction.response.send_message("Error: Target voice channel not found.", ephemeral=True)
				return

		channels_to_sweep = [guild.get_channel(cid) for cid in source_ids if guild.get_channel(cid)]
		if not channels_to_sweep:
				await interaction.response.send_message("Error: No valid source channels found.", ephemeral=True)
				return

		await interaction.response.defer(ephemeral=True)

		moved_count = 0
		for channel in channels_to_sweep:
				for member in channel.members:
						try:
								await member.move_to(target_channel)
								moved_count += 1
						except Exception:
								continue

		await interaction.followup.send(
				f"Moved **{moved_count}** member(s) to {target_channel.mention}.", 
				ephemeral=True
		)

class DynamicApproveJoinView(discord.ui.View):
		def __init__(self, target_user_id: int = None):
				super().__init__(timeout=None)
				if target_user_id:
						self.approve_button.custom_id = f"approve_user_join:{target_user_id}"

		@discord.ui.button(label="Approve", style=discord.ButtonStyle.green, custom_id="approve_user_join:placeholder")
		async def approve_button(self, interaction: discord.Interaction, button: discord.ui.Button):
				try:
						target_user_id = int(interaction.data['custom_id'].split(":")[1])
				except (IndexError, ValueError, KeyError):
						await interaction.response.send_message("Error: Request error.", ephemeral=True)
						return

				guild = interaction.guild
				target_user = guild.get_member(target_user_id)
				start_channel = guild.get_channel(WAITING_ROOM_VOICE)

				jokez_channel = guild.get_channel(JOKEZ_VOICE)
				crows_channel = guild.get_channel(CROWS_VOICE)

				if not start_channel or not jokez_channel or not crows_channel:
						await interaction.response.send_message("Error: Voice channels not found.", ephemeral=True)
						return

				if not target_user or target_user not in start_channel.members:
						user_mention = f"<@{target_user_id}>" if not target_user else target_user.mention
						await interaction.response.send_message(
								f"{user_mention} is no longer in the waiting voice channel.", 
								ephemeral=True
						)
						return

				if len(crows_channel.members) > len(jokez_channel.members):
						target_channel = crows_channel
				else:
						target_channel = jokez_channel

				try:
						await target_user.move_to(target_channel)
						button.disabled = True
						button.label = f"Moved to {target_channel.name}"
						button.style = discord.ButtonStyle.secondary
						await interaction.response.edit_message(view=self)
				except discord.Forbidden:
						await interaction.response.send_message("You don't have permission to move members.", ephemeral=True)
				except Exception as e:
						await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)

class RequestJoinView(discord.ui.View):
		def __init__(self):
				super().__init__(timeout=None)

		@discord.ui.button(label="Request", style=discord.ButtonStyle.blurple, custom_id="request_join")
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
						await interaction.response.send_message("Error: Request channel not found.", ephemeral=True)
						return

				request_cooldowns[user_id] = current_time + 60

				embed = discord.Embed(
						description=f"{interaction.user.mention} has requested to join the voice channel.",
						color=PANEL_COLOR
				)
				if interaction.user.avatar:
						embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url)

				await log_channel.send(
						content=f"<@&{BOUNCER_ROLE}>", 
						embed=embed, 
						view=DynamicApproveJoinView(target_user_id=interaction.user.id)
				)
				await interaction.response.send_message(f"Your request has been sent to <@&{BOUNCER_ROLE}>", ephemeral=True)

class ControlPanelView(discord.ui.View):
		def __init__(self):
				super().__init__(timeout=None)

		@discord.ui.button(label="Move all users to 🤣┃jokez", style=discord.ButtonStyle.success, custom_id="move_to_jokez")
		async def move_to_jokez_button(self, interaction: discord.Interaction, button: discord.ui.Button):
				await mass_move_users(interaction, [CROWS_VOICE, WAITING_ROOM_VOICE, PVP1_VOICE, PVP2_VOICE, VIP_VOICE], JOKEZ_VOICE)

		@discord.ui.button(label="Move all users to 🐔┃crows", style=discord.ButtonStyle.danger, custom_id="move_to_crows")
		async def move_to_crows_button(self, interaction: discord.Interaction, button: discord.ui.Button):
				await mass_move_users(interaction, [JOKEZ_VOICE, WAITING_ROOM_VOICE, PVP1_VOICE, PVP2_VOICE, VIP_VOICE], CROWS_VOICE)

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

				channels_to_scan = [guild.get_channel(cid) for cid in [JOKEZ_VOICE, CROWS_VOICE, WAITING_ROOM_VOICE, PVP1_VOICE, PVP2_VOICE] if guild.get_channel(cid)]
				if not channels_to_scan:
						await interaction.response.send_message("Error: No channels found.", ephemeral=True)
						return

				await interaction.response.defer(ephemeral=True)
				bouncer_role = guild.get_role(BOUNCER_ROLE)

				moved_count = 0
				for ch in channels_to_scan:
						for member in ch.members:
								if bouncer_role in member.roles:
										try:
												await member.move_to(vip_channel)
												moved_count += 1
										except Exception:
												continue

				await interaction.followup.send(f"Moved **{moved_count}** Bouncer(s) to {vip_channel.mention}.", ephemeral=True)

		@discord.ui.button(label="📢┃Crow Alert", style=discord.ButtonStyle.secondary, custom_id="crow_button", row=1)
		async def crow_button(self, interaction: discord.Interaction, button: discord.ui.Button):
				guild = interaction.guild
				ping_channel = guild.get_channel(CROWS_CHANNEL)

				if not ping_channel:
						await interaction.response.send_message("Error: Crows channel not found.", ephemeral=True)
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
				unix_timestamp = int(closest_target.timestamp())

				try:
						await ping_channel.send(
								f"<@&{KAWKAW_ROLE}>{interaction.user.mention} is requesting reinforcements!\n"
								f"KAWKAW! Crow spawns <t:{unix_timestamp}:R>!"
						)
						await interaction.response.send_message(f"Successfully pinged <@&{KAWKAW_ROLE}> in {ping_channel.mention}.", ephemeral=True)
				except discord.Forbidden:
						await interaction.response.send_message("Error: Bot does not have permission to post in that channel.", ephemeral=True)
				except Exception as e:
						await interaction.response.send_message(f"Error: {e}", ephemeral=True)

@bot.event
async def on_ready():
		bot.add_view(RequestJoinView())
		bot.add_view(ControlPanelView())
		bot.add_view(DynamicApproveJoinView())

		async def setup_panel(channel_id, title, desc, view_obj):
				channel = bot.get_channel(channel_id)
				if not channel:
						return
				async for message in channel.history(limit=20):
						if message.author == bot.user and message.embeds and message.embeds[0].title == title:
								return
				embed = discord.Embed(title=title, description=desc, color=PANEL_COLOR)
				await channel.send(embed=embed, view=view_obj)

		await setup_panel(JOIN_VOICE_CHANNEL, "Request to Join", "Click the button to request to join the voice channel.", RequestJoinView())
		await setup_panel(CONTROL_PANEL_CHANNEL, "Control Panel", "Welcome to the Control Panel. Click the respective buttons for their intended use.", ControlPanelView())
		print(f"Logged in as {bot.user}")

bot.run(os.environ['TOKEN'])
