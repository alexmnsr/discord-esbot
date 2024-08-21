import asyncio
from typing import Optional

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

        def has_discord_team_role(roles, role_names=("главный модератор", "следящий за discord")):
            return any(role_name in user_role.name.lower() for user_role in roles for role_name in role_names)

        async def update_roles(user: nextcord.Member, guild: nextcord.Guild, add: bool):
            roles = [r for r in guild.roles if "・discord™" in r.name.lower()]
            if not roles:
                return

            member = guild.get_member(user.id) or await self.fetch_member_safe(guild, user.id)
            if not member:
                return

            try:
                if add:
                    await member.add_roles(*roles)
                else:
                    await member.remove_roles(*roles)
            except Exception as e:
                action = "Выдача" if add else "Удаление"
                user_error = user.name or user.id
                await self.bot.vk.nt_error(f"{action} ролей для {user_error} на сервере '{guild.name}': {e}")

        if has_discord_team_role(added_roles):
            tasks = [update_roles(after, guild, add=True) for guild in self.bot.guilds]
            await asyncio.gather(*tasks)
        elif has_discord_team_role(removed_roles):
            tasks = [update_roles(after, guild, add=False) for guild in self.bot.guilds]
            await asyncio.gather(*tasks)

    async def fetch_member_safe(self, guild: nextcord.Guild, user_id: int) -> Optional[nextcord.Member]:
        try:
            return await guild.fetch_member(user_id)
        except Exception as e:
            await self.bot.vk.nt_error(f"Поиск пользователя {user_id} в гильдии {guild.name}: {e}")
            return None


def setup(bot: EsBot) -> None:
    bot.add_cog(DiscordTeam(bot))
