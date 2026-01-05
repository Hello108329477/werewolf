#python .\main.py  to start application
import discord
from discord.ext import commands
import logging
from dotenv import load_dotenv
import os
import classes
from game_loop import WerewolfGame


#bot setup
load_dotenv()
token = os.getenv('DISCORD_TOKEN')
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True
intents.dm_messages = True
#intents.members = True

def prefix_callable(bot, message):
    return ["w!", "W!"]
bot = commands.Bot(command_prefix=prefix_callable, intents=intents, case_insensitive=True)

secretRole = "Bot tester"

lobbies = {}
games = {}

class GameView(discord.ui.View):
    def __init__(self, guild_id, ctx):
        super().__init__(timeout=None)
        self.guild_id = guild_id
        self.ctx = ctx
        #if guild_id not in games:
        #    games[guild_id] = []
        self.players = []


    
            

    
    @discord.ui.button(label=f"Join game (0/9)", style=discord.ButtonStyle.green)
    async def joinButton(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user in self.players:
            await interaction.response.send_message("You have already joined, dumbass", ephemeral=True)
        elif len(self.players)>=9:
            await interaction.response.send_message("The lobby is already full", ephemeral=True)
        else:
            self.players.append(interaction.user)
            button.label = f"Join game ({len(self.players)}/9)"
            await interaction.response.edit_message(view=self)
            await interaction.followup.send(f"{interaction.user.mention} has joined!", ephemeral=True)

    @discord.ui.button(label=f"Leave game", style=discord.ButtonStyle.red)
    async def leaveButton(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user not in self.players:
            await interaction.response.send_message("You aren't in the game", ephemeral=True)
        else:
            self.players.remove(interaction.user)
            for child in self.children:
                if isinstance(child, discord.ui.Button) and "Join game" in child.label:
                    child.label = f"Join game ({len(self.players)}/9)"
            await interaction.response.edit_message(view=self)
            await interaction.followup.send(f"You have left the game", ephemeral=True)
    
    @discord.ui.button(label=f"View lobby", style=discord.ButtonStyle.grey)
    async def viewLobbyButton(self, interaction: discord.Interaction, button: discord.ui.Button):
        userNames = "\n".join([user.mention for user in self.players])
        embed = discord.Embed(title="Users in lobby:", description=f"\n{userNames}")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label=f"START GAME", style=discord.ButtonStyle.primary)
    async def startButton(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.guild_permissions.manage_events:
            await interaction.response.send_message("Starting the game...") 
            guild = interaction.guild
            bot = interaction.client
            game = WerewolfGame(bot, guild, self.players)
            games[self.guild_id] = game
            if self.guild_id in lobbies:
                del lobbies[self.guild_id]
            print(f"Game stored for guild {self.guild_id}")
            interaction.client.loop.create_task(game.start(self.ctx))
            
            #Create spectate button
            embed = discord.Embed(
            title="The game of werewolf has begun!",
            description="Click below to **Spectate** the ongoing game. 👀"
            )
            view = SpectateView(game, interaction.user)
            await interaction.followup.send(embed=embed, view=view)
        else:
            await interaction.response.send_message("You don't have permission", ephemeral=True) 

#spectate button
class SpectateView(discord.ui.View):
    def __init__(self, game, user):
        super().__init__(timeout=None)
        self.game = game  # Store the WerewolfGame instance so we can modify permissions if needed

    @discord.ui.button(label="Spectate Game", style=discord.ButtonStyle.blurple)
    async def spectate_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Allow user to view the werewolf channel but not speak."""
        channel = self.game.channel
        user = interaction.user
        
        ##Return if already in the game
        if any(player.user == user for player in self.game.userList):
            await interaction.response.send_message(
                f"You are already in the game, join here: {channel.mention}", ephemeral=True
            )
            return

        self.game.spectators.add(user)

        # Grant read-only access
        await channel.set_permissions(interaction.user, 
                                    view_channel=True, 
                                    send_messages=False,
                                    create_public_threads=False, 
                                    create_private_threads=False, 
                                    send_messages_in_threads=False
                                    )

        await interaction.response.send_message(
            f"You can now spectate {channel.mention}! 👀", ephemeral=True
        )

###commands


#w!start
@bot.command()
@commands.has_permissions(manage_events=True)
async def start(ctx):
    guild_id = ctx.guild.id
    if guild_id in lobbies:
        view = lobbies[guild_id]
    else:
        view = GameView(guild_id, ctx)
        lobbies[guild_id] = view

    file = discord.File("images/narrowCover.png", filename="narrowCover.png")
    print("after file")
    embed = discord.Embed(title="A new game of werewolf is starting", description=
                        "This game is inspired by Jinrou, the Japanese take on the classic Werewolf game.\n\n" \
                        "Click below to join the game.",
                        color=0x000001)
    embed.set_image(url="attachment://narrowCover.png")
    await ctx.send(embed=embed, file=file, view=view) 




#w!exit
@bot.command()
@commands.has_permissions(manage_events=True)
async def exit(ctx):
    guild_id = ctx.guild.id

    #deleting the channel
    channelName = f"werewolf-{guild_id}"
    channel = discord.utils.get(ctx.guild.text_channels, name=channelName)
    if channel:
        await channel.delete()
        await ctx.send(f"🗑 Deleted channel `{channelName}`.")

    #disable buttons
    if guild_id in lobbies:
        view = lobbies[guild_id]
        for child in view.children:
            child.disabled = True
        del lobbies[guild_id]

    #Remove any active game instance
    if guild_id in games:
        del games[guild_id]

    embed = discord.Embed(
        title="Werewolf cancelled",
        description="The game (and any lobby) has been ended and cleaned up."
    )
    await ctx.send(embed=embed)


#w!extend
@bot.command()
async def extend(ctx):
    guild_id = ctx.guild.id
    if guild_id not in games:
        await ctx.send("No active game found.")
        return
    print("w!extend guild has been found")
    game = games[guild_id]
    channel = game.channel
    if ctx.channel==channel:
        if(game.getUserAlive(ctx.author)):
            await game.extendTimer(ctx.author)

#w!skip
@bot.command()
async def skip(ctx):
    """Force the werewolf timer to end immediately."""
    guild_id = ctx.guild.id
    game = games[guild_id]
    channel = game.channel
    if ctx.channel==channel:
        if guild_id not in games:
            await ctx.send("No active game found.")
            return

        game = games[guild_id]
        # If you stored both view + game in a dict, use:
        # game = games[guild_id]["game"]
        await game.skipTimer(ctx.author)


#w!roles
@bot.command()
async def roles(ctx):
    embed =discord.Embed(title="Roles", description=classes.returnRolesText())
    await ctx.send(embed=embed)


#w!claim
@bot.command()
async def claim(ctx, *, msg):
    guild_id = ctx.guild.id
    game = games[guild_id]
    player = game.getUserAlive(ctx.author)
    channel = game.channel
    if player and ctx.channel==channel:
        player.claim = msg[:150]
        file = discord.File("images/claim.png", filename="claim.png")
        embed = discord.Embed(title="CLAIM ALERT", description=f"{ctx.author.mention} has claimed \"{player.claim}\"",color=0xFFFF00)
        embed.set_thumbnail(url="attachment://claim.png")
        await ctx.send(embed=embed, file=file)

#w!claims
@bot.command()
async def claims(ctx):
    guild_id = ctx.guild.id
    game = games[guild_id]
    channel = game.channel
    if ctx.channel==channel:
        claims = "\n".join(
            [f"{user.user.mention}: {user.claim}" for user in game.userList if user.claim]
        ) or "No claims yet."
        embed = discord.Embed(title="Claims", description=f"\n{claims}",color=0xFFFF00)
        await ctx.send(embed=embed)




#wolf dms
@bot.event
async def on_message(message):
    #print("on_message registered")
    # Ignore bot’s own messages
    if message.author == bot.user:
        return
    
    # Handle DMs from wolves
    if isinstance(message.channel, discord.DMChannel):
        print("isInstance = channel")
        print(f"games = {list(games.keys())}")
        for game in games.values():
            print("HI")
            wolf_user = game.getUser(message.author)
            if(wolf_user):
                print(f"{wolf_user.user.name} is {wolf_user.role.isColorWolf}")
            else:
                print("NO WOLF")
            if wolf_user and wolf_user.role.isColorWolf:
                print("before broadcast")
                # Send message to all wolves
                await game.broadcast_to_wolves(wolf_user, message.content)
                break  # stop after finding correct game
    print("on_message almost ending")            
    await bot.process_commands(message)
    print("on_message sent")

    



#testing stuff
@bot.event
async def on_ready():
    print(f"We are ready, {bot.user.name}")

"""
# w.assign
@bot.command()
async def assign(ctx):
    role = discord.utils.get(ctx.guild.roles, name=secretRole)
    if role:
        await ctx.author.add_roles(role)
        await ctx.send(f"{ctx.author.name} is now assigned the {secretRole} role")
    else:
        await ctx.send("Role doesn't exist")

# w.unassign
@bot.command()
async def unassign(ctx):
    role = discord.utils.get(ctx.guild.roles, name=secretRole)
    if role:
        await ctx.author.remove_roles(role)
        await ctx.send(f"{ctx.author.name} is no longer assigned the {secretRole} role")
    else:
        await ctx.send("Role doesn't exist")

# w.secret
@bot.command()
@commands.has_role(secretRole)
async def secret(ctx):
    await ctx.send("welcome to the club")

@secret.error
async def secret_error(ctx, error):
    if isinstance(error, commands.MissingRole):
        await ctx.send("Thou are not worthy")
    #else:
     #   await ctx.send("unspecified error")

# w.dm
@bot.command()
async def dm(ctx, *, msg):
    await ctx.author.send(f"You said: \"{msg}\"")

# w.reply
@bot.command()
async def reply(ctx):
    await ctx.reply("This is a reply to your message")

# w.poll
@bot.command()
async def poll(ctx, *, question):
    embed = discord.Embed(title="New Poll", description=question)
    poll_message = await ctx.send(embed=embed)
    await poll_message.add_reaction("👍")
    await poll_message.add_reaction("👎")

    
"""


bot.run(token, log_handler=handler, log_level=logging.DEBUG)