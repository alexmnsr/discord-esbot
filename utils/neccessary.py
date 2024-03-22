import datetime
import re

import nextcord
from nextcord.ext.application_checks.core import CheckWrapper

grant_levels = {
    1: ["Модератор"],
    2: ["Ст. Модератор"],
    3: ["Assistant Discord"],
    4: ["Главный Модератор Discord"],
    5: ["Следящий за Discord"]
}


def grant_level(user_roles, member):
    if member.guild_permissions.administrator:
        return max(grant_levels.keys())

    max_level = 0
    for level, roles in grant_levels.items():
        for role in roles:
            if str(role.lower()) in str([role.name.lower() for role in user_roles]):
                max_level = max(max_level, level)
    return max_level


def restricted_command(access_level: int):
    def predicate(interaction: nextcord.Interaction):
        member = interaction.guild.get_member(interaction.user.id)
        if member:
            return grant_level(interaction.user.roles, member) >= access_level
        return False

    def wrapper(func):
        return CheckWrapper(func, predicate)

    wrapper.predicate = predicate
    return wrapper


def is_counting(channel) -> bool:
    if isinstance(channel, nextcord.StageChannel):
        return True

    if "вопрос" in channel.name.lower() or "общение" in channel.name.lower():
        if "close" in channel.name.lower():
            return False
        if channel.user_limit > 2 or not channel.user_limit:
            if channel.overwrites_for(channel.guild.default_role).connect != False:
                return True
    return False


def get_dict_of_time_intervals(start_date, end_date):
    delta = end_date - start_date
    result = {}
    current_date = start_date.date()
    while current_date <= end_date.date():
        if current_date == start_date.date() == end_date.date():
            seconds_in_date = delta.total_seconds()
        elif current_date == start_date.date():
            seconds_in_date = (
                    datetime.datetime.combine(current_date, datetime.datetime.max.time()) - start_date
            ).total_seconds()
        elif current_date == end_date.date():
            seconds_in_date = (
                    end_date - datetime.datetime.combine(current_date, datetime.datetime.min.time())
            ).total_seconds()
        else:
            seconds_in_date = 24 * 3600
        result[current_date.strftime('%d.%m.%Y')] = seconds_in_date
        current_date += datetime.timedelta(days=1)
    return result


def mashup_info(all_online, current_online, date):
    seconds = get_dict_of_time_intervals(current_online['join_time'], datetime.datetime.now()).get(date, 0)
    if seconds == 0:
        return all_online

    for row in all_online:
        if row['channel_id'] == current_online['channel_id']:
            row['seconds'] += seconds
            break
    else:
        all_online.append({
            "user_id": current_online['user_id'],
            "guild_id": current_online['guild_id'],
            "channel_id": current_online['channel_id'],
            "channel_name": current_online['channel_name'],
            "date": date,
            "seconds": seconds,
            "is_counting": current_online['is_counting']
        })
    return all_online


def is_date_valid(date: str):
    try:
        datetime.datetime.strptime(date, '%d.%m.%Y')
        return True
    except ValueError:
        return False


def date_range(start_datetime, end_datetime):
    date_format = "%d.%m.%Y"

    current_datetime = start_datetime
    dates = []

    while current_datetime <= end_datetime:
        dates.append(current_datetime.strftime(date_format))
        current_datetime += datetime.timedelta(days=1)

    return dates


def seconds_to_time(seconds: int) -> str:
    seconds = round(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = (seconds % 60)
    return f"{hours}:{minutes:02d}:{seconds:02d}"


async def date_autocomplete(cog, interaction, string):
    date_list = date_range(datetime.datetime.now() - datetime.timedelta(days=365), datetime.datetime.now())

    if string:
        specified_list = [date for date in date_list if date.startswith(string)]
        if specified_list:
            date_list = specified_list
    date_list.reverse()
    date_list = date_list[:min(7, len(date_list))]

    await interaction.response.send_autocomplete(date_list)


async def remove_role(client, member_id, guild_id, action_id, role_name):
    guild = client.get_guild(guild_id)
    if not guild:
        return False, False

    try:
        member = await guild.fetch_member(member_id)
    except nextcord.NotFound:
        member = None
    if not member:
        return guild, await client.fetch_user(member_id)

    for role in member.roles:
        if role.name == role_name if not isinstance(role_name, list) else role.name in role_name:
            await member.remove_roles(role, reason=f'Action ID: {action_id}.')

    return guild, member


async def add_role(client, member_id, guild_id, action_id, role_name):
    guild = client.get_guild(guild_id)
    if not guild:
        return False, False

    try:
        member = await guild.fetch_member(member_id)
    except nextcord.NotFound:
        member = None
    if not member:
        return guild, await client.fetch_user(member_id)

    for role in guild.roles:
        if role.name == role_name if not isinstance(role_name, list) else role.name in role_name:
            await member.add_roles(role, reason=f'Action ID: {action_id}.')

    return guild, member


async def add_ban(client, member_id, guild_id):
    guild = client.get_guild(guild_id)
    if not guild:
        return False, False

    try:
        member = await guild.fetch_member(member_id)
    except nextcord.NotFound:
        member = None
    if not member:
        return guild, await client.fetch_user(member_id)

    return guild, member


async def send_embed(member, embed):
    try:
        await member.send(embed=embed)
    except:
        pass


async def checking_presence(bot):
    for guild in bot.guilds:
        mute_text_role = nextcord.utils.get(guild.roles, name='Mute » Text')
        mute_voice_role = nextcord.utils.get(guild.roles, name='Mute » Voice')
        if not mute_text_role:
            await create_role_mutes('Mute » Text', guild)
        if not mute_voice_role:
            await create_role_mutes('Mute » Voice', guild)


async def create_role_mutes(role_name, guild: nextcord.Guild):
    permissions_kwargs = {'send_messages' if 'Text' in role_name else 'speak': False}

    role = await guild.create_role(
        name=role_name, permissions=nextcord.Permissions(**permissions_kwargs), color=nextcord.Color.light_grey()
    )
    for channel in guild.channels:
        await channel.set_permissions(role, reason='Создание ролей Mutes', **permissions_kwargs)


time_pattern = re.compile(r'(\d+)([мдmdч])?')


def string_to_seconds(string: str) -> int:
    if not string:
        return None
    time = time_pattern.match(string)
    if not time:
        return None

    time, unit = time.groups()
    time = int(time)
    time_mult = 60 if unit in ('м', 'm') else 24 * 3600 if unit in ('д', 'd') else 3600 if unit in ('ч', 'h') else 60
    return time * time_mult


def print_user(user, newline=True):
    return user.mention + ('\n' if newline else '') + user.name + (
        f'#{user.discriminator}' if user.discriminator and str(user.discriminator) != '0' else '')


def user_visual(user):
    return print_user(user)


def user_text(user):
    return print_user(user, False)


def mute_name(role_name):
    if isinstance(role_name, list):
        return 'Full'
    return role_name.split('» ')[1].capitalize()


def nick_without_tag(nick):
    return nick.split('] ')[1] if ']' in nick else nick
