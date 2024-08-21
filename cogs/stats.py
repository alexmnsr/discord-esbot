import datetime

import nextcord
from nextcord.ext import commands

from utils.classes.actions import human_actions, moder_actions
from utils.classes.bot import EsBot
from utils.neccessary import restricted_command, is_date_valid, date_autocomplete, grant_level


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

    @nextcord.slash_command(name='stats', description='Показать онлайн модераторов', dm_permission=False)
    @restricted_command(1)
    async def stats(self, interaction: nextcord.Interaction,
                    date: str = nextcord.SlashOption('дата', description="Дата в формате dd.mm.YYYY", required=False,
                                                     autocomplete_callback=date_autocomplete),
                    period: str = nextcord.SlashOption('период', description="Период (день, неделя, месяц)",
                                                       required=False,
                                                       choices=["день", "неделя", "месяц"]),
                    month: str = nextcord.SlashOption('месяц', description="Месяц", required=False,
                                                      choices=["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
                                                               "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь",
                                                               "Декабрь"])):
        try:
            if not date:
                date = datetime.datetime.now().strftime('%d.%m.%Y')
            elif not is_date_valid(date):
                return await interaction.send('Неверный формат даты. Формат: dd.mm.YYYY.\n'
                                              'Пример: 07.07.2077', ephemeral=True)

            if not period:
                period = "день"

            date_obj = datetime.datetime.strptime(date, '%d.%m.%Y')

            if period == "неделя":
                start_date = date_obj - datetime.timedelta(days=date_obj.weekday())
                end_date = start_date + datetime.timedelta(days=6)
            elif period == "месяц":
                if month:
                    month_names = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
                                   "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]
                    month_index = month_names.index(month) + 1
                    start_date = date_obj.replace(month=month_index, day=1)
                else:
                    start_date = date_obj.replace(day=1)
                end_date = (start_date + datetime.timedelta(days=31)).replace(day=1) - datetime.timedelta(days=1)
            else:
                start_date = date_obj
                end_date = date_obj

            guild = interaction.guild
            if guild:
                moderator_roles = [role for role in guild.roles if 'модератор'.lower() in role.name.lower()]
                if moderator_roles:
                    moderator_users = []
                    if grant_level(interaction.user.roles, interaction.user) < 4:
                        moderator_users.append(interaction.user.id)
                        embed = nextcord.Embed(
                            title=f'💎 Действия за {start_date.strftime("%d.%m.%Y")} - {end_date.strftime("%d.%m.%Y")}',
                            color=nextcord.Color.dark_purple())
                    else:
                        embed = nextcord.Embed(
                            title=f'💎 Действия модераторов за {start_date.strftime("%d.%m.%Y")} - {end_date.strftime("%d.%m.%Y")}',
                            color=nextcord.Color.dark_purple())
                        for member in guild.members:
                            for role in member.roles:
                                if role in moderator_roles:
                                    moderator_users.append(member.id)
                                    break

                    await interaction.response.defer()

                    for id_moderator in moderator_users:
                        total_online = datetime.timedelta()
                        acts_summary = {}

                        current_date = start_date
                        while current_date <= end_date:
                            info = await self.handler.get_info(True, user_id=id_moderator,
                                                               guild_id=interaction.guild.id,
                                                               date=current_date.strftime('%d.%m.%Y'))
                            total_online += datetime.timedelta(hours=int(info.total_time.split(':')[0]),
                                                               minutes=int(info.total_time.split(':')[1]),
                                                               seconds=int(info.total_time.split(':')[2]))

                            punishments = await self.acts_handler.moderator_actions(current_date, id_moderator,
                                                                                    guild.id)
                            for p in punishments:
                                acts_summary[p['action_type']] = acts_summary.get(p['action_type'], 0) + 1

                            current_date += datetime.timedelta(days=1)

                        member = guild.get_member(id_moderator)
                        embed.add_field(name=f'{member.display_name}',
                                        value=(f'▫️ Онлайн: {str(total_online)}\n' +
                                               (f'▫️ Действия:\n' +
                                                '\n'.join([
                                                    f'⠀⠀⠀ {moder_actions.get(k.split(".")[-1].lower() if k.startswith("ActionType.") else k, "Неизвестное событие")}: {v}'
                                                    for k, v in
                                                    acts_summary.items()]) if acts_summary else '▫️ Никаких действий')),
                                        inline=False)
                    await interaction.followup.send(embed=embed)

        except Exception as e:
            print(f"Error in stats command: {e}")
            await interaction.followup.send(f"Произошла ошибка: {str(e)}", ephemeral=True)


def setup(bot: EsBot) -> None:
    bot.add_cog(Stats(bot))
