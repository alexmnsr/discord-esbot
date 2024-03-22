import datetime
from typing import Any

import nextcord
from nextcord.ext import commands

from utils.classes.bot import EsBot
from utils.neccessary import restricted_command, is_date_valid, date_autocomplete


class Stats(commands.Cog):
    def __init__(self, bot: EsBot) -> None:
        self.bot = bot
        self.handler = bot.db.online_handler

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        await self.handler.reload(self.bot.get_all_members())

    @nextcord.slash_command(name='stats', description='Показать онлайн модераторов',
                            dm_permission=False)
    @restricted_command(3)
    async def stats(self, interaction: nextcord.Interaction,
                    date: str = nextcord.SlashOption('дата', description="Дата в формате dd.mm.YYYY", required=False,
                                                     autocomplete_callback=date_autocomplete),
                    is_open: bool = nextcord.SlashOption('открытые-каналы',
                                                         description="Подсчитывать онлайн только в открытых каналах.",
                                                         default=True)) -> Any:
        if not date:
            date = datetime.datetime.now().strftime('%d.%m.%Y')
        elif not is_date_valid(date):
            return await interaction.send('Неверный формат даты. Формат: dd.mm.YYYY.\n'
                                          'Пример: 07.07.2077', ephemeral=True)
        guild = interaction.guild
        if guild:
            moderator_roles = [role for role in guild.roles if 'модератор'.lower() in role.name.lower()]

            if moderator_roles:
                moderator_users = []
                embed = ((nextcord.Embed(title=f'💎 Онлайн модераторов за {date}', color=nextcord.Color.dark_purple())
                          .add_field(name='Каналы', value='Открытые' if is_open else 'Все', inline=True)))
                for member in guild.members:
                    for role in member.roles:
                        if role in moderator_roles:
                            moderator_users.append(member.id)
                            break
                for id_moderator in moderator_users:
                    info = await self.handler.get_info(is_open, user_id=id_moderator, guild_id=interaction.guild.id,
                                                       date=date)
                    member = guild.get_member(id_moderator)
                    embed.add_field(name=f'{member.display_name}',
                                    value=f':small_orange_diamond: Онлайн: {info.total_time}', inline=False)
                await interaction.send(embed=embed)


def setup(bot: EsBot) -> None:
    bot.add_cog(Stats(bot))
