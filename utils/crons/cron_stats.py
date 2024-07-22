import datetime
import nextcord
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
from dateutil.relativedelta import relativedelta

from cogs.stats import embed_to_string
from utils.classes.actions import moder_actions
from utils.neccessary import user_text, send_embed


class CRON_Stats:
    def __init__(self, bot):
        self.bot = bot
        self.handler = bot.db.online_handler
        self.acts_handler = bot.db.actions
        self.scheduler = AsyncIOScheduler()
        self.scheduler.start()
        self.schedule_reports()

    def schedule_reports(self):
        msk_tz = pytz.timezone('Europe/Moscow')
        now = datetime.datetime.now(msk_tz)
        reports = [
            ('день', 20, 56, '*', '*', None),
            ('неделя', 23, 59, 'sun', '*', None),
            ('месяц', 23, 59, '*', f'{(now.replace(day=1) + relativedelta(months=1, days=-1)).day}',
             datetime.datetime.now().month)
        ]
        for period, hour, minute, day_of_week, day, month in reports:
            trigger = CronTrigger(hour=hour, minute=minute, day_of_week=day_of_week, day=day, month=month,
                                  timezone=msk_tz)
            self.scheduler.add_job(self.send_report, trigger, args=[period])
            self.scheduler.add_job(self.send_stats_bond, trigger, args=[period])

    async def send_report(self, period):
        for guild in self.bot.guilds:
            await self.send_stats_to_guild(guild, period=period)

    async def send_stats_bond(self, period):
        for guild in self.bot.guilds:
            await self.send_stats_to_bond_vk(guild, period=period)

    async def send_stats_to_guild(self, guild, period='день'):
        date = datetime.datetime.now(pytz.timezone('Europe/Moscow')).strftime('%d.%m.%Y')
        start_date = datetime.datetime.strptime(date, '%d.%m.%Y')

        if period == "день":
            end_date = start_date
        elif period == "неделя":
            start_date = start_date - datetime.timedelta(days=start_date.weekday() + 1)
            end_date = start_date + datetime.timedelta(days=6)
        elif period == "месяц":
            start_date = start_date.replace(day=1)
            next_month = start_date.replace(day=28) + datetime.timedelta(days=4)
            end_date = next_month - datetime.timedelta(days=next_month.day)

        date_str = f"{start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}"

        moderator_roles = [role for role in guild.roles if 'модератор'.lower() in role.name.lower()]
        if moderator_roles:
            moderator_users = []
            embed = nextcord.Embed(title=f'💎 Действия модераторов за {date_str}',
                                   color=nextcord.Color.dark_purple())
            for member in guild.members:
                for role in member.roles:
                    if role in moderator_roles:
                        moderator_users.append(member.id)
                        break

            for id_moderator in moderator_users:
                total_online = datetime.timedelta()
                acts_summary = {}

                current_date = start_date
                while current_date <= end_date:
                    info = await self.handler.get_info(True, user_id=id_moderator, guild_id=guild.id,
                                                       date=current_date.strftime('%d.%m.%Y'))
                    total_online += datetime.timedelta(hours=int(info.total_time.split(':')[0]),
                                                       minutes=int(info.total_time.split(':')[1]),
                                                       seconds=int(info.total_time.split(':')[2]))

                    punishments = await self.acts_handler.moderator_actions(current_date, id_moderator)
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

            # channel = [channel_name for channel_name in guild.channels if 'чат-руководства' in channel_name.name][0]
            # if channel:
            #     await channel.send(embed=embed)

    async def send_stats_to_bond_vk(self, guild, period):
        date = datetime.datetime.now(pytz.timezone('Europe/Moscow')).strftime('%d.%m.%Y')
        start_date = datetime.datetime.strptime(date, '%d.%m.%Y')

        if period == "день":
            end_date = start_date
        elif period == "неделя":
            start_date = start_date - datetime.timedelta(days=start_date.weekday() + 1)
            end_date = start_date + datetime.timedelta(days=6)
        elif period == "месяц":
            start_date = start_date.replace(day=1)
            next_month = start_date.replace(day=28) + datetime.timedelta(days=4)
            end_date = next_month - datetime.timedelta(days=next_month.day)

        date_str = f"{start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}" if period != "день" else date

        roles_to_track = ['следящий за discord', 'главный модератор']
        tracked_roles = [role for role in guild.roles if any(r in role.name.lower() for r in roles_to_track)]

        if tracked_roles:
            embed = nextcord.Embed(title=f'💎 Действия ст. модерации за {date_str}',
                                   color=nextcord.Color.dark_purple())
            embed.add_field(name=f'{guild.name}', value='')
            for role in tracked_roles:
                for member in guild.members:
                    if role in member.roles:
                        total_online = datetime.timedelta()
                        acts_summary = {}

                        current_date = start_date
                        while current_date <= end_date:
                            info = await self.handler.get_info(True, user_id=member.id, guild_id=guild.id,
                                                               date=current_date.strftime('%d.%m.%Y'))
                            total_online += datetime.timedelta(hours=int(info.total_time.split(':')[0]),
                                                               minutes=int(info.total_time.split(':')[1]),
                                                               seconds=int(info.total_time.split(':')[2]))

                            punishments = await self.acts_handler.moderator_actions(current_date, member.id)
                            for p in punishments:
                                acts_summary[p['action_type']] = acts_summary.get(p['action_type'], 0) + 1

                            current_date += datetime.timedelta(days=1)

                        embed.add_field(name=f'{member.display_name}',
                                        value=(f'▫️ Онлайн: {str(total_online)}\n' +
                                               (f'▫️ Действия:\n' +
                                                '\n'.join([
                                                    f'⠀⠀⠀ {moder_actions.get(k.split(".")[-1].lower() if k.startswith("ActionType.") else k, "Неизвестное событие")}: {v}'
                                                    for k, v in
                                                    acts_summary.items()]) if acts_summary else '▫️ Никаких действий')),
                                        inline=False)
            embed.set_author(name=guild.name, icon_url=guild.icon.url)
            user_ids = [479244541858152449, 523968589695418378]
            for user_id in user_ids:
                user = await guild.fetch_member(user_id)
                await send_embed(user, embed)
