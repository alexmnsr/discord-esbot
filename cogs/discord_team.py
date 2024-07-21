import asyncio

import nextcord
from nextcord.ext import commands

from utils.classes.bot import EsBot


class DiscordTeam(commands.Cog):
    def __init__(self, bot: EsBot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_update(self, before: nextcord.Member, after: nextcord.Member):
        if before.roles == after.roles:
            return

        removed_roles = [r for r in before.roles if r not in after.roles]
        added_roles = [r for r in after.roles if r not in before.roles]

        def added_to_discord_team(user_added_roles):
            role_names = ["главный модератор", "следящий за discord"]
            result = any(
                any(role_name in user_role.name.lower() for role_name in role_names) for user_role in user_added_roles)
            return result

        def removed_from_discord_team(user_removed_roles):
            role_names = ["главный модератор", "следящий за discord"]
            result = any(
                any(role_name in user_role.name.lower() for role_name in role_names) for user_role in
                user_removed_roles)
            return result

        async def give_roles(user: nextcord.Member, other_guild: nextcord.Guild):
            add_roles = [r for r in other_guild.roles if "・discord™" in r.name.lower()]
            if not add_roles:
                return
            member = other_guild.get_member(user.id)
            if not member:
                try:
                    member = await other_guild.fetch_member(user.id)
                except Exception as e:
                    print(f"Error fetching member {user.id} in guild {other_guild.name}: {e}")
                    return
            try:
                await member.add_roles(*add_roles)
            except Exception as e:
                print(f"Error adding roles to member {user.id} in guild {other_guild.name}: {e}")

        async def remove_roles(user: nextcord.Member, other_guild: nextcord.Guild):
            remove_roles = [r for r in other_guild.roles if "・discord™" in r.name.lower()]
            print(f"Removing roles in {other_guild.name}: {remove_roles}")
            if not remove_roles:
                return
            member = other_guild.get_member(user.id)
            if not member:
                try:
                    member = await other_guild.fetch_member(user.id)
                except Exception as e:
                    print(f"Error fetching member {user.id} in guild {other_guild.name}: {e}")
                    return
            try:
                await member.remove_roles(*remove_roles)
            except Exception as e:
                print(f"Error removing roles from member {user.id} in guild {other_guild.name}: {e}")

        if added_to_discord_team(added_roles):
            tasks = [give_roles(after, guild) for guild in self.bot.guilds]
            await asyncio.gather(*tasks)
        elif removed_from_discord_team(removed_roles):
            tasks = [remove_roles(after, guild) for guild in self.bot.guilds]
            await asyncio.gather(*tasks)


def setup(bot: EsBot) -> None:
    bot.add_cog(DiscordTeam(bot))
