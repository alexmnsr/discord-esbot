from dateutil.relativedelta import relativedelta

from utils.button_state.views.Online import PointsAdd_View
from utils.classes.actions import moder_actions
from utils.classes.bot import EsBot
from utils.neccessary import send_embed
import datetime
import pytz
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from nextcord import Embed, Color, Guild, Member, TextChannel
from typing import Dict, List, Optional, Tuple


class CRON_Stats:
    def __init__(self, bot: EsBot):
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
            ('день', 23, 59, '*', '*', None),
            ('неделя', 23, 59, 'sun', '*', None),
            ('месяц', 23, 59, '*', f'{(now.replace(day=1) + relativedelta(months=1, days=-1)).day}', None)
        ]
        for period, hour, minute, day_of_week, day, month in reports:
            trigger = CronTrigger(hour=hour, minute=minute, day_of_week=day_of_week, day=day, month=month, timezone=msk_tz)
            self.scheduler.add_job(self.send_report, trigger, args=[period])
            self.scheduler.add_job(self.send_stats_bond, trigger, args=[period])

    async def send_report(self, period: str):
        await asyncio.gather(*(self.send_stats_to_guild(guild, period=period) for guild in self.bot.guilds))

    async def send_stats_bond(self, period: str):
        await asyncio.gather(*(self.send_stats_to_bond_vk(guild, period=period) for guild in self.bot.guilds))

    def calculate_date_range(self, period: str) -> (datetime.datetime, datetime.datetime):
        start_date = datetime.datetime.now(pytz.timezone('Europe/Moscow')).replace(hour=0, minute=0, second=0, microsecond=0)

        if period == "день":
            end_date = start_date
        elif period == "неделя":
            start_date -= datetime.timedelta(days=start_date.weekday() + 1)
            end_date = start_date + datetime.timedelta(days=6)
        elif period == "месяц":
            start_date = start_date.replace(day=1)
            next_month = start_date.replace(day=28) + datetime.timedelta(days=4)
            end_date = next_month - datetime.timedelta(days=next_month.day)
        else:
            raise ValueError(f"Unknown period: {period}")

        return start_date, end_date

    async def fetch_moderator_stats(self, guild: Guild, start_date: datetime.datetime, end_date: datetime.datetime, moderator_roles: List[str]) -> Dict[int, Dict]:
        moderator_stats = {}
        for member in guild.members:
            if any(role.name.lower() in moderator_roles for role in (name_role for name_role in member.roles)):
                total_online = datetime.timedelta()
                acts_summary = {}

                current_date = start_date
                while current_date <= end_date:
                    info = await self.handler.get_info(True,
                                                       user_id=member.id,
                                                       guild_id=guild.id,
                                                       date=current_date.strftime('%d.%m.%Y'))
                    total_online += datetime.timedelta(hours=int(info.total_time.split(':')[0]),
                                                       minutes=int(info.total_time.split(':')[1]),
                                                       seconds=int(info.total_time.split(':')[2]))

                    punishments = await self.acts_handler.moderator_actions(current_date, member.id, guild.id)
                    for p in punishments:
                        acts_summary[p['action_type']] = acts_summary.get(p['action_type'], 0) + 1

                    current_date += datetime.timedelta(days=1)

                moderator_stats[member.id] = {
                    'total_online': total_online,
                    'member': member,
                    'guild': guild,
                    'actions': acts_summary
                }

        return moderator_stats

    async def send_stats_to_guild(self, guild: Guild, period: str = 'день'):
        start_date, end_date = self.calculate_date_range(period)
        date_str = f"{start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}"
        moderator_roles = ['модератор', 'ст. модератор']

        moderator_stats = await self.fetch_moderator_stats(guild, start_date, end_date, moderator_roles)
        embed = Embed(title=f'💎 Действия модераторов за {date_str}', color=Color.dark_purple())

        for stats in moderator_stats.values():
            embed.add_field(
                name=f'{stats["member"].display_name}',
                value=f'▫️ Онлайн: {str(stats["total_online"])}\n' +
                      (f'▫️ Действия:\n' +
                       '\n'.join([
                           f'⠀⠀⠀ {moder_actions.get(k.split(".")[-1].lower() if k.startswith("ActionType.") else k, "Неизвестное событие")}: {v}'
                           for k, v in stats["actions"].items()]) if stats["actions"] else '▫️ Никаких действий'),
                inline=False
            )

        channel = next((channel for channel in guild.channels if 'test' in channel.name), None)
        if channel:
            await channel.send(embed=embed)
            await self.send_points(moderator_stats, channel)

    async def send_stats_to_bond_vk(self, guild: Guild, period: str):
        start_date, end_date = self.calculate_date_range(period)
        date_str = f"{start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}" if period != "день" else start_date.strftime('%d.%m.%Y')
        tracked_roles = ['следящий за discord', 'главный модератор']

        moderator_stats = await self.fetch_moderator_stats(guild, start_date, end_date, tracked_roles)
        embed = Embed(title=f'💎 Действия ст. модерации за {date_str}', color=Color.dark_purple())
        embed.set_author(name=guild.name, icon_url=guild.icon.url)
        embed.add_field(name=f'{guild.name}', value='')

        for stats in moderator_stats.values():
            embed.add_field(
                name=f'{stats["member"].display_name}',
                value=f'▫️ Онлайн: {str(stats["total_online"])}\n' +
                      (f'▫️ Действия:\n' +
                       '\n'.join([
                           f'⠀⠀⠀ {moder_actions.get(k.split(".")[-1].lower() if k.startswith("ActionType.") else k, "Неизвестное событие")}: {v}'
                           for k, v in stats["actions"].items()]) if stats["actions"] else '▫️ Никаких действий'),
                inline=False
            )

        user_ids = [479244541858152449, 523968589695418378]
        for user_id in user_ids:
            user = await guild.fetch_member(user_id)
            await send_embed(user, embed)

    async def send_points(self, moderator_stats: Dict[int, Dict], channel: TextChannel):
        max_online_st_moderator_id, max_online_moderator_id, max_role_moderator_id = self.calculate_points(moderator_stats)

        embed = Embed(title='💎 Поинты', color=Color.gold())
        send_messages_points = {}

        for moderator_id, stats in moderator_stats.items():
            points, reasons = self.calculate_individual_points(moderator_id, stats, max_online_st_moderator_id, max_online_moderator_id, max_role_moderator_id)

            if points > 0:
                send_messages_points[moderator_id] = {
                    'points': points,
                    'reasons': reasons
                }

                embed.add_field(
                    name=f"Модератор - {channel.guild.get_member(moderator_id).display_name}",
                    value=f"Online: {stats['total_online']}\nПоинты: {points} поинтов\nПричины: {', '.join(reasons)}",
                    inline=False
                )

        embed.set_footer(text=f"{datetime.datetime.now().strftime('%d.%m.%Y')}")
        message = await channel.send(embed=embed, view=PointsAdd_View(moderator_ids=str(send_messages_points), date=datetime.datetime.now().strftime("%d.%m.%Y")))

        params = {
            'moderator_ids': str(send_messages_points),
            'date': datetime.datetime.now().strftime("%d.%m.%Y"),
        }
        await self.bot.buttons.add_button("Online", message_id=message.id, channel_id=channel.id, class_method='PointsAdd_View', params=params)

    def calculate_points(self, moderator_stats: Dict[int, Dict[str, int]]) -> Tuple[
        Optional[int], Optional[int], Optional[int]]:
        max_online_st_moderator_id = None
        max_online_moderator_id = None
        max_role_moderator_id = None

        max_online_st_moderator = datetime.timedelta()
        max_online = datetime.timedelta()
        max_role = 0

        for moderator_id, stats in moderator_stats.items():
            total_online_td = stats['total_online']
            roles = [r.name.lower() for r in stats['member'].roles]

            if any('ст. модератор' in role for role in roles) or any('ассистент discord' in role for role in roles):
                if total_online_td > max_online_st_moderator:
                    max_online_st_moderator = total_online_td
                    max_online_st_moderator_id = moderator_id

            if any('модератор' in role for role in roles) and 'главный модератор' not in roles:
                if total_online_td > max_online:
                    max_online = total_online_td
                    max_online_moderator_id = moderator_id

            role_approve = stats['actions'].get('role_approve', 0)
            role_reject = stats['actions'].get('role_remove', 0)
            total_roles = role_approve + (role_reject / 2)

            if total_roles > max_role:
                max_role = total_roles
                max_role_moderator_id = moderator_id
            elif total_roles == max_role:
                current_online_td = stats['total_online']
                if max_role_moderator_id is None or current_online_td > moderator_stats[max_role_moderator_id][
                    'total_online']:
                    max_role_moderator_id = moderator_id

        return max_online_st_moderator_id, max_online_moderator_id, max_role_moderator_id

    def calculate_individual_points(self, moderator_id: int, stats: Dict, max_online_st_moderator_id: int, max_online_moderator_id: int, max_role_moderator_id: int) -> (int, List[str]):
        points = 0
        reasons = []

        total_online_td = stats['total_online']
        if total_online_td >= datetime.timedelta(hours=19, minutes=50):
            points += 4
            reasons.append(f"Онлайн {total_online_td.days * 24 + total_online_td.seconds // 3600}ч")
        elif total_online_td >= datetime.timedelta(hours=14, minutes=50):
            points += 3
            reasons.append(f"Онлайн {total_online_td.days * 24 + total_online_td.seconds // 3600}ч")
        elif total_online_td >= datetime.timedelta(hours=9, minutes=50):
            points += 2
            reasons.append(f"Онлайн {total_online_td.days * 24 + total_online_td.seconds // 3600}ч")
        elif total_online_td >= datetime.timedelta(hours=4, minutes=50):
            points += 1
            reasons.append(f"Онлайн {total_online_td.days * 24 + total_online_td.seconds // 3600}ч")

        if moderator_id == max_online_st_moderator_id:
            points += 1
            reasons.append("Лучший по онлайну [SMD]")

        if moderator_id == max_online_moderator_id:
            points += 1
            reasons.append("Лучший по онлайну [MD]")

        if moderator_id == max_role_moderator_id:
            points += 1
            reasons.append("Лучший по ролям")

        return points, reasons