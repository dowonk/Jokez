import os
import time
import asyncio
import discord
from discord.ext import commands

START_VOICE_CHANNEL_ID = 1474894816088162365  
TARGET_VOICE_CHANNEL_ID = 1339052615832567811
ALT_SOURCE_VOICE_CHANNEL_ID = 1472654310696419349  

TEXT_CHANNEL_ID = 1512195785633042644
CONTROL_PANEL_CHANNEL_ID = 1512208972436869280  
LOG_CHANNEL_ID = 1512205620751765515

PINK_ROLE_ID = 1339053520934146058  
AUDIENCE_ROLE_ID = 1339057300098252820
BOUNCERS_ROLE_ID = 1339058493520478240

PANEL_COLOR = discord.Color.from_rgb(255, 165, 0)  

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

request_cooldowns = {}

class ApproveJoinView(discord.ui.View):
    def __init__(self, target_user: discord.Member):
        super().__init__(timeout=None)
        self.target_user = target_user

    @discord.ui.button(label="Approve", style=discord.ButtonStyle.green, custom_id="approve_button_fixed")
    async def approve_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        start_channel = guild.get_channel(ALT_SOURCE_VOICE_CHANNEL_ID)
        target_channel = guild.get_channel(TARGET_VOICE_CHANNEL_ID)

        if not start_channel or not target_channel:
            await interaction.response.send_message("Error: Voice channels could not be found.", ephemeral=True)
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
            button.label = "Approved"
            button.style = discord.ButtonStyle.secondary

            await interaction.response.edit_message(view=self)

        except discord.Forbidden:
            await interaction.response.send_message(
                "I don't have permission to move members. Check my server permissions!", 
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

    @discord.ui.button(label="Request to Join", style=discord.ButtonStyle.blurple, custom_id="request_join_fixed")
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

        log_channel = guild.get_channel(LOG_CHANNEL_ID)
        waiting_room = guild.get_channel(ALT_SOURCE_VOICE_CHANNEL_ID)

        if not waiting_room or interaction.user not in waiting_room.members:
            await interaction.response.send_message(
                f"You must be in the <#{ALT_SOURCE_VOICE_CHANNEL_ID}> voice channel to make this request!", 
                ephemeral=True
            )
            return

        if not log_channel:
            await interaction.response.send_message(
                "Error: Request logging channel could not be found.", 
                ephemeral=True
            )
            return

        request_cooldowns[user_id] = current_time + 60

        embed = discord.Embed(
            description=f"{interaction.user.mention} has requested to join 🤣┃jokez",
            color=PANEL_COLOR
        )

        if interaction.user.avatar:
            embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url)

        approval_view = ApproveJoinView(target_user=interaction.user)
        mention_text = f"<@&{BOUNCERS_ROLE_ID}>"

        await log_channel.send(content=mention_text, embed=embed, view=approval_view)

        await interaction.response.send_message(
            f"Your request has been sent to <@&{BOUNCERS_ROLE_ID}>", 
            ephemeral=True
        )


class ControlPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Move all to 🐔┃crows", style=discord.ButtonStyle.danger, custom_id="move_all_to_crows_fixed")
    async def move_all_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        author = interaction.user

        if not author.voice or not author.voice.channel:
            await interaction.response.send_message(
                "You must be connected to a voice channel to run this command.", 
                ephemeral=True
            )
            return

        current_vc = author.voice.channel
        crows_channel = guild.get_channel(START_VOICE_CHANNEL_ID)

        if not crows_channel:
            await interaction.response.send_message("Error: The destination Crows voice channel was not found.", ephemeral=True)
            return

        channels_to_sweep = []

        if current_vc.id == START_VOICE_CHANNEL_ID:
            ch1 = guild.get_channel(TARGET_VOICE_CHANNEL_ID)
            ch2 = guild.get_channel(ALT_SOURCE_VOICE_CHANNEL_ID)
            if ch1: channels_to_sweep.append(ch1)
            if ch2: channels_to_sweep.append(ch2)
        else:
            channels_to_sweep.append(current_vc)

        await interaction.response.defer(ephemeral=True)

        all_members_to_move = []
        for channel in channels_to_sweep:
            all_members_to_move.extend(channel.members)

        async def safe_move(member):
            try:
                await member.move_to(crows_channel)
                return True
            except Exception:
                return False

        results = await asyncio.gather(*[safe_move(m) for m in all_members_to_move])
        moved_count = sum(1 for r in results if r)

        await interaction.followup.send(
            f"Moved **{moved_count}** member(s) to {crows_channel.mention}.", 
            ephemeral=True
        )


@bot.event
async def on_ready():
    print(f'Bot is online as {bot.user}')

    bot.add_view(RequestJoinView())
    bot.add_view(ControlPanelView())

    req_channel = bot.get_channel(TEXT_CHANNEL_ID)
    if req_channel:
        req_exists = False
        async for message in req_channel.history(limit=20):
            if message.author == bot.user and len(message.embeds) > 0:
                if message.embeds[0].title == "Request to Join":
                    req_exists = True
                    print("Request panel already exists. Skipping duplication.")
                    break

        if not req_exists:
            embed = discord.Embed(
                title="Request to Join",
                description="Click the button to request to join the 🤣┃jokez voice channel.",
                color=PANEL_COLOR
            )
            await req_channel.send(embed=embed, view=RequestJoinView())
            print(f"Generated request panel in channel {TEXT_CHANNEL_ID}")
    else:
        print(f"Warning: Channel ID {TEXT_CHANNEL_ID} not accessible.")

    ctrl_channel = bot.get_channel(CONTROL_PANEL_CHANNEL_ID)
    if ctrl_channel:
        ctrl_exists = False
        async for message in ctrl_channel.history(limit=20):
            if message.author == bot.user and len(message.embeds) > 0:
                if message.embeds[0].title == "Control Panel":
                    ctrl_exists = True
                    print("Control Panel already exists. Skipping duplication.")
                    break

        if not ctrl_exists:
            embed = discord.Embed(
                title="Control Panel",
                description="Move all users to 🐔┃crows.",
                color=PANEL_COLOR
            )
            await ctrl_channel.send(embed=embed, view=ControlPanelView())
            print(f"Generated Control Panel in channel {CONTROL_PANEL_CHANNEL_ID}")
    else:
        print(f"Warning: Channel ID {CONTROL_PANEL_CHANNEL_ID} not accessible.")

bot.run(os.environ['TOKEN'])
