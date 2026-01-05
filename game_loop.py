import asyncio
import discord
import classes
import random
import math
import menuViews

class WerewolfGame:
    def __init__(self, bot, guild, players):
        self.bot = bot
        self.guild = guild
        self.players = players  # list of discord.Member
        self.lastHangedPlayer = None
        self.running = False
        self.userList = []
        self.dayCount = 1
        ##self.isDay = False
        self.channel = None
        self.timerRunning = False
        self.remainingTime = 0
        self.voteEvent = asyncio.Event()
        self.wolfVictory = False
        self.checkRoleButton = None
        self.checkRoleView = None
        self.nightActionButton = None
        self.nightActionView = None
        self.spectators = set()
        
        

        

    #game setup
    async def start(self, ctx):
        print(f"starting game")

        #Assign users
        self.userList = await classes.AssignRoles(self.players)
        for user in self.userList:
            try:
                embed = discord.Embed(title=f"You are the **{user.role.roleName.upper()}**", description=f"{user.role.roleDescription}")
                await user.user.send(embed=embed)
            except Exception as e:
                print(f"Failed to DM {user.user}: {e}")

        print(f"check")
        #hide channel
        #self.overwrites = {self.guild.default_role: discord.PermissionOverwrite(view_channel=False)  }  #hide from everyone   
        #
        # Set channel permissions  
        self.overwrites = {
            self.guild.default_role: discord.PermissionOverwrite(view_channel=False), #hide channel from users

            # give the bot full control of the channel
            self.guild.me: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                manage_channels=True,
                manage_messages=True,
                create_public_threads=True,
                create_private_threads=True,
                send_messages_in_threads=True
            )
        }

        #create channel
        channelName = f"werewolf-{self.guild.id}"
        existing_channel = discord.utils.get(self.guild.text_channels, name=channelName)
        if existing_channel is not None:
            print(f"{channelName} already exists")
            return
        
        
        self.channel = await self.guild.create_text_channel(channelName, overwrites=self.overwrites)
        await self.lockChannel()

        #ping users
        userNames = "\n".join([user.mention for user in self.players]) or "No players joined."
        await self.channel.send(userNames)

        print("starting...")
        #starting the game
        self.running = True
        
        #night one
        await self.nightOne()
        await self.channel.send("The game will begin in 60 seconds")
        await self.setInterval(60)
        
        
        while self.running:
            await self.day()
            if self.running:
                self.dayCount+=1
                await self.night()
        
        print("day night loop ended")

        #Handle victory logic
        #Figure out if wolves or humans won
        if self.wolfVictory:
            titleTxt = "The **wolf** team won!"
            winners = [user for user in self.userList if user.role.isWolf==True]
            losers = [user for user in self.userList if user.role.isWolf==False]
            imageTxt = "wolfVictory"
            color = 0xFF0000
        else:
            titleTxt = "The **human** team won!"
            winners = [user for user in self.userList if user.role.isWolf==False]
            losers = [user for user in self.userList if user.role.isWolf==True]
            imageTxt = "humanVictory"
            color = 0x00FF00
            
        
        #Create and display the victory text
        #Get the player names
        winnerNames = "\n".join([f"{user.user.mention} - {user.role.roleName}" for user in winners])
        loserNames = "\n".join([f"{user.user.mention} - {user.role.roleName}" for user in losers])
        victoryTxt = "**WINNERS**\n" \
        f"{winnerNames}\n\n" \
        "**LOSERS**\n" \
        f"{loserNames}"

        file1 = discord.File(f"images/{imageTxt}.png", filename=f"{imageTxt}.png")
        file2 = discord.File(f"images/{imageTxt}.png", filename=f"{imageTxt}.png")
        embed = discord.Embed(title=titleTxt, description=victoryTxt, color=color)
        embed.set_thumbnail(url=f"attachment://{imageTxt}.png")

        await self.channel.send(embed=embed, file=file1)
        await ctx.send(embed=embed, file=file2)


    async def nightOne(self):
        #get list of all wolves
        wolves = [user for user in self.userList if user.role.roleName.lower()=="wolf"]
        #DM wolf partner
        for wolf in wolves:
            try:
                partners = [w.user.name for w in wolves if w != wolf]
                if partners:
                    partner_text = ", ".join(partners)
                else:
                    partner_text = "You are the only wolf."
                embed = discord.Embed(title=f"Wolf partners", description=partner_text)
                await wolf.user.send(f"Your partner in crime is **{partner_text}**\nChat with your partner by replying to this message.")
            except Exception as e:
                print(f"Failed to DM {wolf.user}: {e}")
        
        #DM the seer 
        humansAlive = self.getAllHumansAlive()
        for human in humansAlive:
            try:
                if human.role.roleName.lower()=="seer":
                    possible_targets = [h for h in humansAlive if h != human]
                    if possible_targets:
                        target = random.choice(possible_targets)
                        human.selectedUser = target
                        txt = f"{target.user.mention}({target.user.display_name}) is human"
                        embed = discord.Embed(title=f"You are hit with a revelation...", description=txt)
                        #await self.channel.send(embed=embed, ephemeral=True)
                        await human.user.send(f"{target.user.mention}({target.user.display_name}) is human")
            except Exception as e:
                print(f"Failed to DM {wolf.user}: {e}")

        #welcome message.
        file = discord.File("images/narrowCover.png", filename="narrowCover.png")
        embed = discord.Embed(title="Welcome to the game of werewolf!", description=
                              f"Rules: Absolutely NO DMING outside the game's official channels.\n" \
                              "NO AFK\n" \
                              "Player roles will not be exposed on death, so the werewolves can feel free to fake-claim\n" \
                              "Some useful commands:\n" \
                              "w!claim xxx\n" \
                              "w!claims\n" \
                              "w!extend\n" \
                              "w!skip\n" \
                              "w!roles",
                              color=0x000001)
        embed.set_image(url="attachment://narrowCover.png")
        await self.channel.send(embed=embed, file=file)

        await self.checkRoleDisplay()
                
        

    async def day(self): 
        file1 = discord.File("images/sun.png", filename="sun.png")
        file2 = discord.File("images/day.png", filename="day.png")

        embed = discord.Embed(title="**A new day is rising!**", 
                              description="It is time for the discussion phase of the game.\n\n" \
                              "If you are a medium or seer, check the results on the button below.",
                            color=0x00FF00)
        embed.set_image(url="attachment://day.png")
        embed.set_thumbnail(url="attachment://sun.png")

        await self.channel.send(embed=embed, files=[file1,file2])

        await self.setInterval(3)
        await self.unlockChannel()
        #Set the timer
        self.timer_task = asyncio.create_task(self.startTimer(180))
        #wait for timer
        try:
            await self.timer_task
        except asyncio.CancelledError:
            print("Day skipped successfully")

        #Hanging
        #Reset previous checkrole button
        await self.checkRoleDisable()

        # Reset all votes
        self.resetVotes()
        await self.setInterval(4)

        #Display the dropdown
        await self.channel.send("It is now time for the lynch")
        #Create the embed
        fileGallow = discord.File("images/gallow.png", filename="gallow.png")
        embed = discord.Embed(title="Choose who to hang", description="Vote below", color=0xFFA500)
        embed.set_thumbnail(url="attachment://gallow.png")
        #Get players
        print("ALIVEUSERS DEBUG:")
        for t in self.getAllUsersAlive():
            print(" → t:", t, " type:", type(t), " user:", getattr(t, "user", None))
        self.voteEvent = asyncio.Event()
        hangView = menuViews.VoteView(self, None, self.getAllUsersAlive(), "Select a player to hang...")
        print("The view initialized??")

        msg = await self.channel.send(embed=embed, file=fileGallow, view=hangView)
        
        # Wait for 60 seconds OR all votes in, whichever first
        print("before voteevent")
        
        try:
            await asyncio.wait_for(self.voteEvent.wait(), timeout=60)
        except asyncio.TimeoutError:
            pass  # voting time ended
        
        #Disable the view
        for child in hangView.children:
            child.disabled = True
        await msg.edit(view=hangView)

        #Carry out the hanging
        await self.hangPlayer()

        await self.gameEndCondition()
        if not self.running:
            return
        
        await self.setInterval(10)

    async def night(self):
        await self.lockChannel()
        self.resetVotes()

        #Night display
        self.nightActionView = menuViews.NightAction(self, self.userList)
        print("The view initialized??")

        file1 = discord.File("images/moon.png", filename="moon.png")
        file2 = discord.File("images/night.png", filename="night.png")

        embed = discord.Embed(title="**The night has fallen**", 
                              description="Who will get killed tonight?.\n\n" \
                              "If you have a night action, click below.\n",
                            color=0x000001)
        embed.set_image(url="attachment://night.png")
        embed.set_thumbnail(url="attachment://moon.png")
        self.nightActionButton = await self.channel.send(embed=embed, files=[file1,file2], view=self.nightActionView)


        await self.setInterval(60) #Wait for night to end

        #Disable the night action button
        if self.nightActionView:
            await self.nightActionDisable()

        #Select guarded player
        guards = [g for g in self.getAllHumansAlive() if g.role.roleName.lower()=="guard"]
        guardedPlayers = [g.selectedUser for g in guards]

        #select victim
        aliveWolves = [w for w in self.getAllWolves() if w.isAlive]
        picks = {}
        for wolf in aliveWolves:
            if wolf.selectedUser:
                target = wolf.selectedUser
                picks[target] = picks.get(target, 0) + 1

        
        if not picks:
            wolfTarget = random.choice(self.getAllHumansAlive())
        else:
            maxVotes = max(picks.values())
            tied = [target for target, count in picks.items() if count == maxVotes]
            wolfTarget = random.choice(tied)

        for player in guardedPlayers:
            if player == wolfTarget:
                wolfTarget= None

        #Night ends
        await self.channel.send("The night is coming to an end...")
        await self.setInterval(3)

        await self.displayPlayers()

        #Display target
        if wolfTarget:
            #If target got killed
            wolfTarget.isAlive = False
            pfp = wolfTarget.user.display_avatar.url
            embed = discord.Embed(title=f"{wolfTarget.user.display_name} was killed by the wolves.", 
                                  description=f"Today we say our goodbyes to {wolfTarget.user.mention}",
                                  color=0xFF0000)
            embed.set_thumbnail(url=pfp)
            await self.channel.send(embed=embed)
        else:
            #If saved by guard
            fileGuard = discord.File("images/guard.png", filename="guard.png")
            embed = discord.Embed(title=f"Nobody was killed tonight", 
                                  description=f"The guard did her duty and protected town from harm.",
                                  color=0xFFFFFF)
            embed.set_thumbnail(url="attachment://guard.png")
            await self.channel.send(embed=embed, file=fileGuard)

        

        #Check if game has ended
        await self.gameEndCondition()
        if not self.running:
            self.setInterval(10)
            return
        
        #DM medium
        mediums = [s for s in self.getAllHumansAlive() if s.role.roleName.lower()=="medium"]
        if not self.lastHangedPlayer:
            mediumTxt = f"Nobody was hanged last night"
        elif self.lastHangedPlayer.role.isColorWolf:
            mediumTxt = f"{self.lastHangedPlayer.user.display_name} was a **WOLF**"
        else:
            mediumTxt = f"{self.lastHangedPlayer.user.display_name} was a **HUMAN**"
        for medium in mediums:
            try:
                embed = discord.Embed(title=f"You see a vision from last night...", description=mediumTxt)
                #await self.channel.send(embed=embed, ephemeral=True)
                await medium.user.send(mediumTxt)
            except Exception as e:
                print(f"Failed to DM {medium.user}: {e}")
        #DM seer
        seers = [s for s in self.getAllHumansAlive() if s.role.roleName.lower()=="seer"]
        for seer in seers:
            if seer.selectedUser:
                if seer.selectedUser.role.isColorWolf:
                    seerTxt = f"{seer.selectedUser.user.display_name} is a **WOLF**"
                else:
                    seerTxt = f"{seer.selectedUser.user.display_name} is a **HUMAN**"
                try:
                    embed = discord.Embed(title=f"You are hit with a revelation...", description=seerTxt)
                    #await self.channel.send(embed=embed, ephemeral=True)
                    await seer.user.send(seerTxt)
                except Exception as e:
                    print(f"Failed to DM {seer.user}: {e}")

        #Check role button
        await self.checkRoleDisplay()

        await self.setInterval(15)
        print("night() ending")


        

    async def hangPlayer(self):
        #Count votes
        alive = self.getAllUsersAlive()
        votes = {}

        for user in alive:
            if user.selectedUser:
                target = user.selectedUser
                votes[target] = votes.get(target, 0) + 1
        
        #skip if nobody voted
        if not votes:
            await self.channel.send("Nobody voted. No one is lynched.")
            self.lastHangedPlayer = None
            return
        
        #Hang the max voted player
        maxVotes = max(votes.values())
        topCandidates = [user for user, count in votes.items() if count == maxVotes]
        voteSummary = "\n".join(
            f"**{user.user.mention}** — {count} vote{'s' if count != 1 else ''}"
            for user, count in votes.items()
        )
        chosen = random.choice(topCandidates)
        self.lastHangedPlayer = chosen
        chosen.isAlive = False

        #Display the hanging
        pfp = chosen.user.display_avatar.url
        fileHang = discord.File("images/hanging.png", filename="hanging.png")
        embed = discord.Embed(title=f"**{chosen.user.display_name}** has been hanged", 
                              description="Total votes: \n" \
                              f"{voteSummary}",
                              color=0xFFA500)
        embed.set_image(url="attachment://hanging.png")
        embed.set_thumbnail(url=pfp)
        
        await self.channel.send(embed=embed, file=fileHang)
        

    async def displayPlayers(self):
        #Figure out who are alive
        livingNames = "\n".join([user.user.mention for user in self.userList if user.isAlive])
        deadNames = "\n".join([user.user.mention for user in self.userList if not user.isAlive])
        
        #Create and display the player status
        statusTxt = "**ALIVE PLAYERS**\n" \
        f"{livingNames}\n\n" \
        "**DEAD PLAYERS**\n" \
        f"{deadNames}"

        embed = discord.Embed(title="Players", description=statusTxt)
        await self.channel.send(embed=embed)


    #channel lock and unlock
    async def lockChannel(self):
        for user in self.userList:
            await self.channel.set_permissions(
                user.user,
                view_channel=True,
                send_messages=False,
                create_public_threads=False, 
                create_private_threads=False, 
                send_messages_in_threads=False
            )

        """ for user in self.userList:
                self.overwrites[user.user] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=False
        )
        await self.channel.edit(overwrites=self.overwrites) #applies the updated permission """

    async def unlockChannel(self):
        for user in self.userList:
            if user.isAlive:
                await self.channel.set_permissions(
                    user.user,
                    view_channel=True,
                    send_messages=True,
                    create_public_threads=False, 
                    create_private_threads=False, 
                    send_messages_in_threads=False
                )
        """         for user in self.userList:
                if user.isAlive:
                    self.overwrites[user.user] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True
            )
        await self.channel.edit(overwrites=self.overwrites)  """
        
    async def gameEndCondition(self):
        #Get count of alive players
        wolfCount = len([w for w in self.getAllWolves() if w.isAlive])
        humanCount = len(self.getAllHumansAlive())
        print(f"Humans alive:{humanCount} wolves alive: {wolfCount}")

        if wolfCount==0:
            print("Human victory")
            self.running=False
            self.wolfVictory= False
        elif wolfCount >= humanCount:
            print("Wolf victory")
            self.running=False
            self.wolfVictory=True
        else:
            print("gameEndCondition() The game continues...")

    async def checkRoleDisplay(self):
        roleView = menuViews.CheckRole(self.channel, self.userList, self.lastHangedPlayer)
        self.checkRoleView = roleView
        self.checkRoleButton = await self.channel.send(view=roleView)

    async def checkRoleDisable(self):
        #disable the view
        if self.checkRoleView:
            try:
                for child in self.checkRoleView.children:
                    child.disabled = True
                await self.checkRoleButton.edit(view=self.checkRoleView)
            except Exception as e:
                print("Failed to disable CheckRole:", e)
        
    async def nightActionDisplay(self):
        self.nightActionView = menuViews.NightAction(self, self.userList)
        print("The view initialized??")
        embed = discord.Embed(title=f"The night has fallen", description="If you have a night action, click below.\n" \
                              "Seer and medium results will be displayed in the morning")
        self.nightActionButton = await self.channel.send(embed=embed, view=self.nightActionView)
    
    async def nightActionDisable(self):
        if self.nightActionView:
            try:
                for child in self.nightActionView.children:
                    child.disabled = True
                await self.nightActionButton.edit(view=self.nightActionView)
            except Exception as e:
                print("Failed to disable NightAction:", e)


    async def setInterval(self, seconds):
        while True:
            #await self.channel.send(f"The game will proceed in {seconds} seconds...")
            await asyncio.sleep(seconds)
            return

        #Time commands
    
    async def startTimer(self, seconds):
        self.remainingTime=seconds
        self.timerRunning=True
        for user in self.userList:
                user.isExtending = False
        print("⏳ Timer started")
        try:
            while self.remainingTime > 0 and self.timerRunning:
                await self.channel.send(f"⏳ {self.remainingTime} seconds remaining...")
                await asyncio.sleep(30)
                self.remainingTime -= 30
            if self.timerRunning:
                await self.channel.send("⏰ Time's up!")
        except asyncio.CancelledError:
            print("StartTimer asyncio.cancel")
            raise
        except Exception as e:
            print(f"❌ Timer error: {e}")
        finally:
            self.timerRunning = False

    async def extendTimer(self, player):
        print("extendTimer() started")
        if not self.timerRunning:
            print("Timer extension failed because self.timerRunning is false")
            return
        #find user
        user = self.getUserAlive(player)
        if not user:
            return
        #set skipping/extending

        user.isSkipping = False
        msg = ""

        if user.isExtending:
            user.isExtending = False
            msg = f"**{player.display_name}** has cancelled their vote to extend"
        else:
            user.isExtending = True
            msg = f"**{player.display_name}** has voted to extend the timer"

        #get total votes
        usersAlive = self.getAllUsersAlive()
        userVotes = 0
        votesNeeded = math.floor(len(usersAlive)/2)+1
        for u in usersAlive:
            if u.isExtending:
                userVotes+=1

        #Display message
        embed = discord.Embed(title=msg, description=f"{userVotes}/{votesNeeded} votes to extend", color=0xFFFFFF)
        await self.channel.send(embed=embed)
        if userVotes>=votesNeeded:
            self.remainingTime += 60
            embed = discord.Embed(title="Day successfully extended by 60 seconds!", 
                                          description=f"Remaining time is {self.remainingTime} seconds")
            await self.channel.send(embed=embed)
            for user in self.userList:
                user.isExtending = False
                user.isSkipping = False


    async def skipTimer(self, player):
        if not self.timerRunning or not hasattr(self, "timer_task"):
            print("attempt to skip timer failed because no timer running")
            return
        
        #find user
        user = self.getUserAlive(player)
        if not user:
            return
        
        #set skipping/extending
        user.isExtending = False
        msg = ""
        if user.isSkipping:
            user.isSkipping = False
            msg = f"**{player.display_name}** has cancelled their vote to skip"
        else:
            user.isSkipping = True
            msg = f"**{player.display_name}** has voted to skip the timer"

        #get total votes
        usersAlive = self.getAllUsersAlive()
        userVotes = 0
        votesNeeded = math.floor(len(usersAlive)/2)+1
        for u in usersAlive:
            if u.isSkipping:
                userVotes+=1
        
        #Display vote message
        embed = discord.Embed(title=msg, description=f"{userVotes}/{votesNeeded} votes to skip", color=0xFFFF00)
        await self.channel.send(embed=embed)

        #cancel task if sufficient votes
        if userVotes>=votesNeeded:
            self.timer_task.cancel()
            self.timerRunning = False  # stop the loop
            self.remainingTime=0
            await self.channel.send("The day has been skipped! Moving on...")
            #Reset votes
            for user in self.userList:
                user.isSkipping = False
                user.isExtending = False

    async def broadcast_to_wolves(self, sender, message_text):
        print("broadcast_to_wolves started")
        """DM all wolves when one sends a DM."""
        wolves = self.getAllWolves()
        for wolf in wolves:
            # Cross out name if the wolf is dead
            nameDisplay = (
                f"~~{sender.user.display_name}~~" if not sender.isAlive else sender.user.display_name
            )

            # Send DM
            try:
                await wolf.user.send(f"**{nameDisplay}:** {message_text}")
            except discord.Forbidden:
                print(f"Couldn't DM {wolf.user.name}")
        print("broadcast_to_wolves ended")

    

    def resetVotes(self):
        for user in self.userList:
            user.selectedUser = None
    
    def getUserAlive(self, discord_user):
        return next((u for u in self.userList if u.user.id == discord_user.id and u.isAlive), None)
    
    def getUser(self, discord_user):
        return next((u for u in self.userList if u.user.id == discord_user.id), None)


    def getAllUsersAlive(self):
        allUsers = [user for user in self.userList if user.isAlive==True]
        return allUsers
    
    def getAllWolves(self):
        allUsers = [user for user in self.userList if user.role.isColorWolf]
        return allUsers
    
    def getUserById(self, uid: int):
        return next((u for u in self.userList if u.user.id == uid), None)
    
    def getAllHumansAlive(self):
        aliveHumans = [user for user in self.userList if user.isAlive==True and user.role.isColorWolf==False]
        return aliveHumans

