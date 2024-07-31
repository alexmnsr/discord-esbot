import datetime
import nextcord
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
from dateutil.relativedelta import relativedelta

from utils.button_state.views.Online import PointsAdd_View
from utils.classes.actions import moder_actions
from typing import Dict
from utils.neccessary import send_embed


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
            ('день', 1, 35, '*', '*', None),
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
        date = '31.07.2024' # datetime.datetime.now(pytz.timezone('Europe/Moscow')).strftime('%d.%m.%Y')
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
        moderator_stats = {}
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

                    punishments = await self.acts_handler.moderator_actions(current_date, id_moderator, guild.id)
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
                moderator_stats[id_moderator] = {
                    'total_online': total_online,
                    'member': member,
                    'guild': guild,
                    'actions': {key: value for key, value in acts_summary.items()}
                }
            channel = [channel_name for channel_name in guild.channels if 'test' in channel_name.name][0]
            if channel:  # and guild.id == 506143782509740052
                await channel.send(embed=embed)
                await self.send_points(moderator_stats, channel)

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

                            punishments = await self.acts_handler.moderator_actions(current_date, member.id, guild.id)
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

    async def send_points(self, moderator_stats: Dict[int, Dict[str, int]], channel: nextcord.TextChannel):
        max_online_st_moderator = datetime.timedelta()
        max_online_st_moderator_id = None

        max_online = datetime.timedelta()
        max_online_moderator_id = None

        send_messages_points = {}

        max_role = 0
        max_role_moderator_id = None

        for moderator_id, stats in moderator_stats.items():
            total_online_td = stats['total_online']
            roles = [r.name.lower() for r in stats['member'].roles]
            if 'ст. модератор' in roles or 'ассистент discord' in roles:
                if total_online_td > max_online_st_moderator:
                    max_online_st_moderator = total_online_td
                    max_online_st_moderator_id = moderator_id
            elif 'модератор' in roles and 'главный модератор' not in roles:
                if total_online_td > max_online:
                    max_online = total_online_td
                    max_online_moderator_id = moderator_id

            role_approve = stats['actions'].get('role_approve', 0)
            role_reject = stats['actions'].get('role_remove', 0)
            total_roles = role_approve + (role_reject / 2)

            if total_roles > max_role:
                max_role = total_roles
                max_role_moderator_id = moderator_id

        def calculate_online_points(online_time):
            if online_time >= datetime.timedelta(hours=20):
                return 4
            elif online_time >= datetime.timedelta(hours=15):
                return 3
            elif online_time >= datetime.timedelta(hours=10):
                return 2
            elif online_time >= datetime.timedelta(hours=5):
                return 1
            return 0

        embed = nextcord.Embed(title='💎 Поинты', color=nextcord.Color.gold())
        for moderator_id, stats in moderator_stats.items():
            total_online_td = stats['total_online']
            points = calculate_online_points(total_online_td)
            reasons = []

            if moderator_id not in send_messages_points:
                send_messages_points[moderator_id] = {'points': 0, 'reasons': []}

            if points > 0:
                send_messages_points[moderator_id]['points'] += points
                reasons.append(f"Онлайн {total_online_td.days * 24 + total_online_td.seconds // 3600}ч")

            if moderator_id == max_online_st_moderator_id:
                send_messages_points[moderator_id]['points'] += 1
                reasons.append("Лучший по онлайну [SMD]")

            if moderator_id == max_online_moderator_id:
                send_messages_points[moderator_id]['points'] += 1
                reasons.append("Лучший по онлайну [MD]")

            if moderator_id == max_role_moderator_id:
                send_messages_points[moderator_id]['points'] += 1
                reasons.append("Лучший по ролям")

            if reasons:
                send_messages_points[moderator_id]['reasons'].extend(reasons)

                embed.add_field(
                    name=f"Модератор - {channel.guild.get_member(moderator_id).display_name}",
                    value=f"Online: {total_online_td}\nПоинты: {send_messages_points[moderator_id]['points']} поинтов\nПричины: {', '.join(send_messages_points[moderator_id]['reasons'])}",
                    inline=False
                )
        embed.set_footer(text=f"{datetime.datetime.now().strftime('%d.%m.%Y')}")
        message = await channel.send(embed=embed, view=PointsAdd_View(moderator_ids=str(send_messages_points), date=datetime.datetime.now().strftime("%d.%m.%Y")))
        params = {
            'moderator_ids': str(send_messages_points),
            'date': datetime.datetime.now().strftime("%d.%m.%Y")
        }
        await self.bot.buttons.add_button("Online", message_id=message.id,
                                          channel_id=channel.id,
                                          class_method='PointsAdd_View',
                                          params=params)
