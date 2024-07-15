import datetime

import nextcord
from nextcord.ext import commands

from cogs.vk_bot.vk import Vkontakte
from utils.classes.actions import human_actions, moder_actions
from utils.classes.bot import EsBot
from utils.neccessary import restricted_command, is_date_valid, date_autocomplete


def embed_to_string(embed: nextcord.Embed) -> str:
    result = [f"{embed.title}\n"]
    for field in embed.fields:
        result.append(f"{field.name}\n{field.value}\n")
    return "\n".join(result)


class Stats(commands.Cog):
    def __init__(self, bot: EsBot) -> None:
        self.bot = bot
        self.handler = bot.db.online_handler
        self.acts_handler = bot.db.actions
        self.vk = Vkontakte(bot)

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        await self.handler.reload(self.bot.get_all_members())

    @nextcord.slash_command(name='stats', description='Показать онлайн модераторов',
                            dm_permission=False)
    @restricted_command(3)
    async def stats(self, interaction: nextcord.Interaction,
                    date: str = nextcord.SlashOption('дата', description="Дата в формате dd.mm.YYYY", required=False,
                                                     autocomplete_callback=date_autocomplete)):
        if not date:
            date = datetime.datetime.now().strftime('%d.%m.%Y')
        elif not is_date_valid(date):
            return await interaction.send('Неверный формат даты. Формат: dd.mm.YYYY.\n'
                                          'Пример: 07.07.2077', ephemeral=True)
        guild = interaction.guild
        date_obj = datetime.datetime.strptime(date, '%d.%m.%Y')
        if guild:
            moderator_roles = [role for role in guild.roles if 'модератор'.lower() in role.name.lower()]

            if moderator_roles:
                moderator_users = []
                embed = nextcord.Embed(title=f'💎 Действия модераторов за {date}', color=nextcord.Color.dark_purple())
                for member in guild.members:
                    for role in member.roles:
                        if role in moderator_roles:
                            moderator_users.append(member.id)
                            break
                for id_moderator in moderator_users:
                    info = await self.handler.get_info(True, user_id=id_moderator, guild_id=interaction.guild.id,
                                                       date=date)
                    punishments = await self.acts_handler.moderator_actions(date_obj, id_moderator)
                    acts = {}
                    for p in punishments:
                        acts[p['action_type']] = acts.get(p['action_type'], 0) + 1

                    member = guild.get_member(id_moderator)
                    embed.add_field(name=f'{member.display_name}',
                                    value=(f'▫️ Онлайн: {info.total_time}\n' +
                                           (f'▫️ Действия:\n' +
                                            '\n'.join([
                                                f'⠀⠀⠀ {moder_actions.get(k.split(".")[-1].lower() if k.startswith("ActionType.") else k, "Неизвестное событие")}: {v}'
                                                for k, v in
                                                acts.items()]) if acts else '▫️ Никаких действий')),
                                    inline=False)
                # await self.vk.send_message(id=239759093, message=embed_to_string(embed))
                await interaction.send(embed=embed)

    @nextcord.slash_command(name='activity', description='Показать активность модераторов',
                            dm_permission=False)
    @restricted_command(3)
    async def activity(self, interaction: nextcord.Interaction,
                       moderator: nextcord.Member = nextcord.SlashOption('модератор',
                                                                         description="Модератор, чью активность хотите посмотреть."),
                       date: str = nextcord.SlashOption('дата', description="Дата в формате dd.mm.YYYY", required=False,
                                                        autocomplete_callback=date_autocomplete)):
        if not date:
            date = datetime.datetime.now().strftime('%d.%m.%Y')
        elif not is_date_valid(date):
            return await interaction.send('Неверный формат даты. Формат: dd.mm.YYYY.\n'
                                          'Пример: 07.07.2077', ephemeral=True)
        date = datetime.datetime.strptime(date, '%d.%m.%Y')
        guild = interaction.guild
        embed = nextcord.Embed(title=f'💎 Активность {moderator.display_name} за {date.strftime("%d.%m.%Y")}',
                               color=nextcord.Color.dark_purple())

        punishments = await self.acts_handler.moderator_actions(date, moderator.id)
        acts = {}
        for p in punishments:
            acts[p['action_type']] = acts.get(p['action_type'], 0) + 1

        info = await self.handler.get_info(True, user_id=moderator.id, guild_id=interaction.guild.id,
                                           date=date)

        embed.add_field(name=f'Онлайн',
                        value=info.total_time, inline=False)

        embed.add_field(name=f'Наказания',
                        value='\n'.join([
                            f'{human_actions.get(k.split(".")[-1].lower() if k.startswith("ActionType.") else k, "Неизвестное событие")}: {v}'
                            for k, v in acts.items()]), inline=False)

        await interaction.send(embed=embed)


def setup(bot: EsBot) -> None:
    bot.add_cog(Stats(bot))
