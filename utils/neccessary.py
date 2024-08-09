import asyncio
import datetime
import importlib
import re

import nextcord
from nextcord.ext.application_checks.core import CheckWrapper

grant_levels = {
    1: ["Модератор"],
    2: ["Ст. Модератор"],
    3: ["Ассистент Discord"],
    4: ["Главный Модератор"],
    5: ["Следящий за Discord"]
}


async def get_class_from_file(module_name: str, class_name: str):
    module = importlib.import_module(module_name)
    cls = getattr(module, class_name, None)

    if isinstance(cls, type):
        return cls
    return None


async def load_buttons(client, buttons, type_buttons):
    loaded_buttons = await buttons.load_all_buttons()

    for button_data in loaded_buttons[f'{type_buttons}']:
        module_name = f'utils.button_state.views.{type_buttons}'
        message_id = button_data.get('message_id')
        channel_id = button_data.get('channel_id')
        class_name = button_data.get('class_method')
        selected_class = await get_class_from_file(module_name, class_name)
        if selected_class:
            print(f"Класс {selected_class.__name__} найден.")
        else:
            print(f"Класс {selected_class.__name__} не найден.")
        params = button_data.get('params', {})
        view = selected_class(**params)

        channel = client.get_channel(channel_id)
        if channel:
            try:
                message = await channel.fetch_message(message_id)
                await message.edit(view=view)
            except nextcord.NotFound:
                print("Сообщение не найдено.")
            except nextcord.Forbidden:
                print("Нет прав на редактирование этого сообщения.")
            except Exception as e:
                print(f"Произошла ошибка: {e}")


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


async def copy_message(message: nextcord.Message,
                       channel: nextcord.TextChannel, thread: nextcord.Thread, mess: nextcord.Message,
                       message_len: int):
    webhooks = await channel.webhooks()
    if webhooks:
        webhook = webhooks[0]
    else:
        webhook = await channel.create_webhook(name="Saved messages")

    messages = await message.channel.history(around=message, limit=message_len).flatten()

    async def message_copied(message_to_copy):
        files = []

        if message_to_copy.attachments:
            for attachment in message_to_copy.attachments:
                files.append(await attachment.to_file())
        return dict(
            target=message_to_copy.id == message.id,
            content=message_to_copy.content,
            files=files,
            username=('📸 ' if message_to_copy.id == message.id else '') + message_to_copy.author.display_name,
            avatar_url=message_to_copy.author.display_avatar.url,
            allowed_mentions=nextcord.AllowedMentions.none(),
            embeds=message_to_copy.embeds
        )

    tasks = [message_copied(to_message) for to_message in messages]
    messages = await asyncio.gather(*tasks)
    for copied_message in messages:
        target = copied_message['target']
        del copied_message['target']
        c_mess = await webhook.send(**copied_message, thread=thread, wait=target)
        if target:
            embed = mess.embeds[0]
            field = embed.fields[1]
            await mess.edit(embed=mess.embeds[0].set_field_at(1, name=field.name,
                                                              value=f'[{field.value}]({thread.jump_url + "/" + str(c_mess.id)})',
                                                              inline=False))
    await message.delete()


def beautify_seconds(seconds: int) -> str:
    if seconds == -1:
        return "Навсегда"
    if seconds < 60:
        return f"{seconds} сек."
    if seconds < 3600:
        return f"{seconds // 60} мин."
    if seconds < 86400:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours} ч. {minutes} мин."
    return f"{seconds // 86400} дн."


def is_counting(channel: nextcord
                .VoiceChannel) -> bool:
    if "вопрос" in channel.name.lower() or "общение" in channel.name.lower():
        if channel.user_limit > 2 or not channel.user_limit:
            if (
                    channel.overwrites_for(channel.guild.default_role).connect is not False and
                    channel.overwrites_for(channel.guild.default_role).view_channel is not False
            ):
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


async def remove_temp_role(member: nextcord.Member = None, role_name='Temp_Mute » Full'):
    member = await member.guild.fetch_member(member.id)
    for role in member.roles:
        if role.name == role_name if not isinstance(role_name, list) else role.name in role_name:
            await member.remove_roles(role, reason=f'Снятие временного наказания (Temp_Mute).')


async def remove_role(member_id, guild, action_id, role_name):
    if not guild:
        return False, False

    try:
        member = await guild.fetch_member(member_id)
    except nextcord.NotFound:
        return

    roles_to_remove = []
    for role in member.roles:
        if (isinstance(role_name, list) and role.name in role_name) or (role.name == role_name):
            roles_to_remove.append(role)

    if not roles_to_remove:
        return guild, member

    try:
        await member.remove_roles(*roles_to_remove, reason=f'Action ID: {action_id}.')
    except nextcord.Forbidden:
        print(f'Bot does not have permission to remove roles from {member.display_name}.')
    except nextcord.HTTPException as e:
        print(f'Failed to remove roles from {member.display_name}: {e}')

    return guild, member


async def add_role(client, member_id, guild_id, role_name, action_id='Temp_Mute'):
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
            await member.add_roles(role,
                                   reason=f'Action ID: {action_id}.' if action_id == 'Temp_Mute' else 'Временная блокировка (до выяснений)')

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


async def create_role_mutes(role_name, guild: nextcord.Guild):
    permissions_kwargs = get_role_permissions(role_name)

    role = await guild.create_role(
        name=role_name, permissions=nextcord.Permissions(**permissions_kwargs), color=nextcord.Color.light_grey()
    )

    await set_channel_permissions(role, guild, permissions_kwargs)


async def update_role_permissions(role: nextcord.Role, role_name: str, guild: nextcord.Guild):
    desired_permissions = get_role_permissions(role_name)
    current_permissions = role.permissions

    print(f'Current permissions for {role.name}: {current_permissions}')  # Логирование
    print(f'Desired permissions for {role_name}: {desired_permissions}')  # Логирование
    await role.edit(permissions=nextcord.Permissions(**desired_permissions), reason='Обновление разрешений роли Mutes')
    await set_channel_permissions(role, guild, desired_permissions)


async def set_channel_permissions(role: nextcord.Role, guild: nextcord.Guild, permissions_kwargs):
    for channel in guild.channels:
        current_channel_permissions = channel.permissions_for(role)

        # Проверка, нужно ли обновлять разрешения для 'Temp_Mute » Full'
        if role.name == 'Temp_Mute » Full':
            if 'правила' in channel.name and '-' not in channel.name:
                if current_channel_permissions.read_messages != True or current_channel_permissions.send_messages != False:
                    await channel.set_permissions(role, reason='Редактирование ролей Mutes', read_messages=True,
                                                  send_messages=False)
            else:
                if current_channel_permissions.read_messages != False or current_channel_permissions.speak != False or current_channel_permissions.connect != False:
                    await channel.set_permissions(role, reason='Редактирование ролей Mutes', read_messages=False,
                                                  speak=False, connect=False)
        else:
            if current_channel_permissions.read_messages != False:
                await channel.set_permissions(role, reason='Редактирование ролей Mutes', read_messages=False,
                                              **permissions_kwargs)


def get_role_permissions(role_name: str):
    if role_name == 'Temp_Mute » Full':
        return {'send_messages': False, 'speak': False, 'connect': False}
    elif 'Mute » Text' in role_name:
        return {'send_messages': False}
    elif 'Mute » Voice' in role_name:
        return {'connect': False}
    else:
        return {}


async def checking_presence(bot):
    for guild in bot.guilds:
        mute_text_role = nextcord.utils.get(guild.roles, name='Mute » Text')
        mute_voice_role = nextcord.utils.get(guild.roles, name='Mute » Voice')
        mute_temp_role = nextcord.utils.get(guild.roles, name='Temp_Mute » Full')

        if not mute_temp_role:
            await create_role_mutes('Temp_Mute » Full', guild)
        else:
            await update_role_permissions(mute_temp_role, 'Temp_Mute » Full', guild)

        if not mute_text_role:
            await create_role_mutes('Mute » Text', guild)
        else:
            await update_role_permissions(mute_text_role, 'Mute » Text', guild)

        if not mute_voice_role:
            await create_role_mutes('Mute » Voice', guild)
        else:
            await update_role_permissions(mute_voice_role, 'Mute » Voice', guild)


time_pattern = re.compile(r'(\d+)([мдmdч])?')


def string_to_seconds(string: str, default_unit='m') -> int | None | str:
    if not string:
        return None

    if string == '-1':
        return '-1'

    time = time_pattern.match(string)
    if not time:
        return None

    time, unit = time.groups()
    if not unit:
        unit = default_unit
    time = int(time)
    time_mult = 60 if unit in ('м', 'm') else 24 * 3600 if unit in ('д', 'd') else 3600 if unit in ('ч', 'h') else 60
    return time * time_mult


def print_user(user, newline=True):
    return user.mention + ('\n' if newline else ' ') + user.name + (
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
