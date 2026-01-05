import discord
from discord.ui import View, Select

class VoteSelect(Select):
    def __init__(self, game, voter, targets, placeholder):

        print("VoteSelect targets:", targets)
        for t in targets:
            print(" → target:", t, " type:", type(t), " user:", t.user, " user type:", type(t.user))

        # Build options safely
        options = []
        for t in targets:
            user = t.user
            label = getattr(user, "display_name", None) or getattr(user, "name", None) or str(user)
            desc = getattr(user, "name", None) or str(user)
            value = str(getattr(user, "id", id(user)))  # fallback prevents crash

            options.append(
                discord.SelectOption(
                    label=label[:100],
                    description=f"@{desc}"[:100],
                    value=value
                )
            )

        super().__init__(
            placeholder=placeholder,
            min_values=1,
            max_values=1,
            options=options
        )

        self.game = game
        self.voter = voter
        self.targets = targets


    async def callback(self, interaction):
        print("callback fired")

        voter = self.voter or self.game.getUserAlive(interaction.user)
        print("voter =", voter)

        selected_id = int(self.values[0])
        choice = self.game.getUserById(selected_id)
        
        #Return if user selected themselves
        if(voter==choice):
            await interaction.response.send_message("You can't select yourself")
            return

        voter.selectedUser = choice
        await interaction.response.send_message(
            f"You selected **{choice.user.display_name}**",
            ephemeral=True
        )

        if all(u.selectedUser for u in self.game.getAllUsersAlive()):
            self.game.voteEvent.set()


class VoteView(View):
    def __init__(self, game, voter, aliveUsers, placeholder):
        print("VoteView with aliveUsers:", aliveUsers)
        super().__init__(timeout=60)
        self.add_item(VoteSelect(game, voter, aliveUsers, placeholder))

    async def on_error(self, error, item, interaction):
        print("UI ERROR:", error)
        import traceback
        traceback.print_exc()


class NightAction(discord.ui.View):
    def __init__(self, game, userList):
        super().__init__(timeout=None)
        self.game = game
        self.userList = userList


    @discord.ui.button(label=f"Action", style=discord.ButtonStyle.primary)
    async def nightActionButton(self, interaction: discord.Interaction, button: discord.ui.Button):
        """         
        #Get users
        alivePlayers = [u for u in self.userList if u.isAlive]
        user = next((u for u in alivePlayers if u.user.id == interaction.user.id), None)
        allHumans = [u for u in alivePlayers if not u.role.isColorWolf and u!=user]
        allPlayers = [u for u in alivePlayers if u!=user]

        
        if not user:
            await interaction.response.send_message("You are not in the game", ephemeral=True)
            return

        #Displaythe night action dropdown
        if user.role.roleName.lower()=="wolf":
            await user.role.nightAction(user, allHumans, "Select a player to attack...", self.channel)
            await interaction.response.defer(ephemeral=True)
        elif user.role.roleName.lower()=="guard":
            await user.role.nightAction(user, allPlayers, "Select a player to protect...", self.channel)
            await interaction.response.defer(ephemeral=True)
        elif user.role.roleName.lower()=="seer":
            await user.role.nightAction(user, allPlayers, "Select a player to see if they are wolf or human...", self.channel)
            await interaction.response.defer(ephemeral=True)
        else:
            await interaction.response.send_message("You don't have any night actions available", ephemeral=True)
            return """
        #Get users
        alivePlayers = [u for u in self.userList if u.isAlive]
        user = next((u for u in alivePlayers if u.user.id == interaction.user.id), None)
        #allHumans = [u for u in alivePlayers if not u.role.isColorWolf and u!=user]
        #allPlayers = [u for u in alivePlayers if u!=user]

        
        if not user:
            await interaction.response.send_message("You are not in the game", ephemeral=True)
            return

        #Displaythe night action dropdown
        if user.role.roleName.lower()=="wolf":
            dropdown = [u for u in alivePlayers if not u.role.isColorWolf and u!=user]
            txt = "Select a player to attack..."
        elif user.role.roleName.lower()=="guard":
            dropdown = [u for u in alivePlayers if u!=user]
            txt = "Select a player to protect..."
        elif user.role.roleName.lower()=="seer":
            dropdown = [u for u in alivePlayers if u!=user]
            txt = "Select a player to see if they are wolf or human..."
        else:
            await interaction.response.send_message("You don't have any night actions available", ephemeral=True)
            return

        #hangView = menuViews.VoteView(self, None, self.getAllUsersAlive(), "Select a player to hang...")
        #view = VoteView(self, None, user, dropdown, txt)
        view = VoteView(self.game, user, dropdown, txt)
        embed = discord.Embed(title=f"Perform your night action", description=txt)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class CheckRole(discord.ui.View):
    def __init__(self, channel, userList, lastHangedPlayer):
        super().__init__(timeout=None)
        self.channel = channel
        self.userList = userList
        self.lastHangedPlayer = lastHangedPlayer
    
    @discord.ui.button(label=f"Check your role", style=discord.ButtonStyle.primary)
    async def roleButton(self, interaction: discord.Interaction, button: discord.ui.Button):
        #find the user
        user = next((u for u in self.userList if u.user.id == interaction.user.id and u.isAlive), None)

        if not user:
            await interaction.response.send_message("You are not in the game", ephemeral=True)
            return
        
        if user.role.isColorWolf:
            color=0xFF0000
        else:
            color=0x00FF00
        
        #Display role text
        file = discord.File(f"images/{user.role.roleName.lower()}.png", filename=f"{user.role.roleName.lower()}.png")
        print("after file")
        embed = discord.Embed(title=f"You are the **{user.role.roleName.upper()}**", 
                              description=f"{user.role.roleDescription}",
                            color=color)
        embed.set_thumbnail(url=f"attachment://{user.role.roleName.lower()}.png")
        
        await interaction.response.send_message(embed=embed, file=file, ephemeral=True)

        #Special message for seers
        if user.role.roleName.lower()=="seer" and user.selectedUser:
            if user.selectedUser.role.isColorWolf:
                seerTxt = f"{user.selectedUser.user.mention} is a **WOLF**"
                color = color=0xFF0000
            else:
                seerTxt = f"{user.selectedUser.user.mention} is a **HUMAN**"
                color = color=0x00FF00

            embed = discord.Embed(title=f"You are hit with a revelation...", description=seerTxt, color=color)
            await interaction.followup.send(embed=embed, ephemeral=True)
        #special message for mediums
        elif user.role.roleName.lower()=="medium" and self.lastHangedPlayer:
            if self.lastHangedPlayer.role.isColorWolf:
                mediumTxt = f"{self.lastHangedPlayer.user.display_name} was a **WOLF**"
                color = color=0xFF0000
            else:
                mediumTxt = f"{self.lastHangedPlayer.user.display_name} was a **HUMAN**"
                color = color=0x00FF00

            embed = discord.Embed(title=f"You see a vision from last night...", description=mediumTxt, color=color)
            await interaction.followup.send(embed=embed, ephemeral=True)
        #special message for wolves
        elif user.role.roleName.lower()=="wolf":
            wolves = [u for u in self.userList if u.role.isColorWolf]
            partners = [w.user.mention for w in wolves if w != user]
            if partners:
                partner_text = ", ".join(partners)
            else:
                partner_text = "You are the only wolf."
            embed = discord.Embed(title=f"Wolf partners", description=f"Your partner in crime is **{partner_text}**")
            #await self.channel.send(embed=embed, ephemeral=True)
            await interaction.followup.send(embed=embed, ephemeral=True)


            
            
