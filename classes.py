import random
import menuViews
import discord



class Role:
    def __init__(self, roleName, isWolf, isColorWolf, roleDescription):
        self.roleName = roleName
        self.isWolf = isWolf
        self.isColorWolf = isColorWolf
        if isWolf:
            self.winCondition = "The number of humans alive is equal to or less than the number of wolves alive." 
        else:
            self.winCondition = "All wolves have been eradicated."

        self.roleDescription = roleDescription+"\n**Win condition:** "+self.winCondition
        self.choseToHang = None
        self.choseToAttack = None


    """ async def nightAction(self, user, dropDown, txt, channel):
        try:
            view = menuViews.VoteView(self, user, dropDown, txt)
            embed = discord.Embed(title=f"Perform your night action", description=txt)
            await channel.send(embed=embed, view=view, ephemeral=True)
            #await user.user.send(
            #    txt,
            #    view=view
            #)
        except Exception as e:
            print(f"Failed to DM {user.user}: {e}") """




class User:
    def __init__(self, user, role, isAlive):
        self.user = user
        self.role = role
        self.isAlive = isAlive
        self.claim = ""
        self.selectedUser = None
        self.isSkipping = False
        self.isExtending = False





#define the roles
wolf = Role("Wolf", True, True, 
            f"Every night, select a player to attack.\n" \
            "If you and your partner picks a different target, the target will be chosen by random between the two.\n" \
            "If neither of you choose a target, the attacked player will be chosen by random")
heretic = Role("Heretic", True, False, 
               "You are a human who adores wolves.\n" \
               "You are on the wolves side, but you don't have any powers of your own.\n" \
               "You don't know who the wolves are, and the wolves don't know who you are.\n" \
               "If the seer or medium selects you, they will see you as human.")
villager = Role("Villager", False, False, 
                "You are a plain villager. You don't have any powers")
seer = Role("Seer", False, False, 
                     "Every night, select a player to see if they are a wolf or human.\n" \
                     "On the first night, you will be shown a random human player.")
medium = Role("Medium", False, False, 
              "Every night, you will be shown if the previously hanged player was wolf or human.")
guard = Role("Guard", False, False, 
             "Every night, select a player to protect.\n" \
             "If the wolves attacks the player you selected, nobody will be killed that night.\n" \
             "You can select the same player as many times as you want.")


def returnRolesText():
    allRoles = [wolf,villager,seer,medium,guard,heretic]
    txt = "\n".join([f"**{role.roleName}**\n{role.roleDescription}\n\n" for role in allRoles])
    return txt

#assign roles to the users in game
async def AssignRoles(players):
    """ playerCount = len(players)

    #base guaranteed roles
    roles = [wolf]

    #add guaranteed roles based on player count
    if playerCount>=5:
        roles.append(heretic)
    if playerCount>=7:
        roles.append(wolf)
    
    #Fill out the last roles and add to the pool
    optionalRoles = [villager, villager, villager, seer, medium, guard]

    while len(roles) < playerCount:
        choice = random.choice(optionalRoles)
        roles.append(choice)
        optionalRoles.remove(choice)

    #assign the roles
    random.shuffle(roles) """
    assignedUsers = []

    roles = [wolf, seer, guard, villager, heretic, villager, wolf, medium, villager]
    random.shuffle(players)
    for i, user in enumerate(players):
        newUser = User(user=user, role=roles[i], isAlive=True)
        assignedUsers.append(newUser)
        
    return assignedUsers