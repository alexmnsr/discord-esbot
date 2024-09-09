import asyncio
import datetime
from datetime import timedelta
from typing import Any

import nextcord

from utils.classes.actions import ActionType
from utils.neccessary import remove_role, send_embed, add_role, user_visual, user_text, mute_name, beautify_seconds, \
    remove_temp_role, load_buttons
from utils.punishments.punishments_database import PunishmentsDatabase


class MuteHandler:
    def __init__(self, handler) -> None:
        self.handler = handler
        self.client = handler.client
        self.database = handler.database

    def mute_info(self, role_name):
        get, give, remove = (self.database.get_text_mute, self.database.give_text_mute, self.database.remove_text_mute) \
            if role_name == 'Mute » Text' else (
            self.database.get_voice_mute, self.database.give_voice_mute, self.database.remove_voice_mute
        ) \
            if role_name == 'Mute » Voice' else (
            self.database.get_full_mute, self.database.give_full_mute, self.database.remove_full_mute
        )
        return get, give, remove

    async def user_muted(self, user_id: int, guild_id: int):
        return await self.database.get_mutes(user_id, guild_id)

    async def give_temp_mute(self, user: int, guild: int, moderator: int, reason: str, duration: int) -> Any:
        guild, member = await add_role(self.client, user, guild, 'Temp_Mute » Full')

        if not guild:
            return

        embed = nextcord.Embed(
            title=f'Вам выдан временный мут.',
            description=f'Причина: {reason} (До уточнения информации)\nВремя истечения: <t:{int((datetime.datetime.now() + datetime.timedelta(seconds=duration)).timestamp())}:R>\nВыдал модератор: <@{moderator.id}>',
            color=0xFF0000
        )
        embed.set_author(name=guild.name, icon_url=guild.icon.url)
        await send_embed(member, embed)
        self.client.loop.create_task(self.wait_mute(None, duration, 'Temp_Mute » Full', moderator, member))

    async def give_mute(self, role_name, *,
                        user: int,
                        guild: int,
                        moderator: int,
                        reason: str,
                        duration: int,
                        jump_url: str):
        get, give, remove = self.mute_info(role_name)
        action_id = await give(user_id=user, guild_id=guild, moderator_id=moderator, reason=reason,
                               duration=duration, jump_url=jump_url)
        if not action_id:
            return
        if role_name == 'Mute » Full':
            role_name = ['Mute » Text', 'Mute » Voice']
        guild, member = await add_role(self.client, user, guild, role_name, action_id)
        if not guild:
            return

        embed = nextcord.Embed(
            title=f'Вам выдан {mute_name(role_name)} мут.',
            description=f'Причина: {reason}\nВремя истечения: <t:{int((datetime.datetime.now() + datetime.timedelta(seconds=duration)).timestamp())}:R>\nВыдал модератор: <@{moderator}>',
            color=0xFF0000
        )
        embed.set_author(name=guild.name, icon_url=guild.icon.url)
        embed.set_footer(text=f'Action ID: {action_id}')

        await send_embed(member, embed)
        moderator = await guild.fetch_member(moderator)

        log_embed = nextcord.Embed(title=f'Выдача {mute_name(role_name)} мута',
                                   color=0xFF0000)
        log_embed.set_author(name=moderator.display_name, icon_url=moderator.display_avatar.url)
        log_embed.add_field(name='Пользователь', value=user_visual(member))
        log_embed.add_field(name='Причина', value=reason)
        log_embed.add_field(name='Время истечения',
                            value=f'<t:{int((datetime.datetime.now() + datetime.timedelta(seconds=duration)).timestamp())}:R>')
        log_embed.add_field(name='Длительность мута', value=str(int(duration / 60)) + "м")
        log_embed.add_field(name='Ссылка на сообщение', value=jump_url)
        log_embed.set_footer(text=f'ID: {member.id}')
        await self.client.db.actions.send_log(action_id, guild, embed=log_embed)

        action_id = await get(user_id=member.id, guild_id=guild.id)

        self.client.loop.create_task(self.wait_mute(action_id['_id'], duration, role_name, member))

    async def wait_mute(self, action_id, seconds, role_name, moderator, member: nextcord.Member = None):
        if seconds > 0:
            await asyncio.sleep(seconds)

        if action_id is None:
            print("Action ID is None, removing temporary role.")
            await remove_temp_role(member=member)

        get, give, remove = self.mute_info(role_name)
        mute = await get(action_id=action_id)

        if not mute:
            print(f"No mute found for action ID: {action_id}.")
            return

        if role_name == 'Mute » Full':
            role_name = ['Mute » Text', 'Mute » Voice']
        guild = self.client.get_guild(mute['guild_id'])
        guild, member = await remove_role(mute['user_id'], guild, action_id, role_name)
        await remove(member.id, guild.id)

        if not guild:
            print("Guild not found, unable to remove role.")
            return

        embed = nextcord.Embed(
            title=f'Ваш {mute_name(role_name)} мут истек.',
            description=f'Вы снова можете продолжать общение в текстовых чатах на сервере {guild.name}.',
            color=0x00FF00
        )
        embed.set_author(name=guild.name, icon_url=guild.icon.url)

        try:
            await send_embed(member, embed)
        except nextcord.HTTPException as e:
            await self.client.vk.nt_error(f"Не удалось отправить уведомление пользователю {member.display_name}: {e}")

    async def remove_mute(self, user_id: int, guild: nextcord.Guild, role_name, moderator: int, *, cancel=None):
        moderator = await guild.fetch_member(moderator)
        get, give, remove = self.mute_info(role_name)
        if cancel:
            mute = await get(user_id=user_id, guild_id=guild.id)
            await self.database.cancel(user_id=user_id, guild_id=guild.id, moderator_id=moderator.id)
        else:
            if not (mute := await get(user_id=user_id, guild_id=guild.id)) or not await remove(user_id, guild.id,
                                                                                               moderator=moderator.id):
                if role_name == 'Mute » Full':
                    role_name = ['Mute » Text', 'Mute » Voice']
        if mute is None:
            return False
        guild, member = await remove_role(user_id, guild, mute['_id'], role_name)

        if guild:
            embed = nextcord.Embed(
                title=f'Вам был снят мут!',
                description=f'Модератор {user_text(moderator)} снял у вас мут на сервере {guild.name}.',
                color=0x00FF00
            )
            await send_embed(member, embed)

        log_embed = nextcord.Embed(title=f'Снятие {mute_name(role_name)} мута', color=0x00FF00)
        log_embed.add_field(name='Пользователь', value=user_visual(member))
        log_embed.set_author(name=moderator.display_name, icon_url=moderator.display_avatar.url)
        log_embed.set_footer(text=f'ID: {mute["_id"]}')
        await self.client.db.actions.send_log(mute['_id'], guild, log_embed)
        return True

    def get_punishment_channel(self, guild):
        return next(c for c in guild.text_channels if 'выдача-наказаний' in c.name)

    def create_punishment_params(self, moderator_id, user_id, role_name):
        return {'moderator_id': moderator_id, 'user_id': user_id, 'role_name': role_name}

    async def register_punishment_button(self, mess, params, interaction):
        await self.client.buttons.add_button("Punishments", message_id=mess.id,
                                             channel_id=mess.channel.id,
                                             user_request=interaction.user.id,
                                             moderator_id=interaction.user.id,
                                             guild_id=interaction.guild.id,
                                             class_method='CancelPunishments',
                                             params=params)

    async def apply_mute(self, role_name, user: int, guild: int, moderator: int, reason: str, duration: int,
                         jump_url: str):
        await self.give_mute(role_name, user=user, guild=guild, moderator=moderator,
                             reason=reason, duration=duration, jump_url=jump_url)


class BlockChannelHandler:
    def __init__(self, handler) -> None:
        self.handler = handler
        self.client = handler.client
        self.database = handler.database

    async def give_block_channel(self, interaction: nextcord.Interaction, user: nextcord.Member, guild: nextcord.Guild,
                                 duration,
                                 reason, category: nextcord.CategoryChannel):
        moderator = interaction.user
        overwrite = nextcord.PermissionOverwrite()
        overwrite.send_messages = False
        overwrite.connect = False
        await category.set_permissions(user, overwrite=overwrite, reason=reason)
        action_id = await self.database.give_block_channel(user_id=user if isinstance(user, int) else user.id,
                                                           guild_id=guild.id,
                                                           moderator_id=interaction.user.id,
                                                           reason=reason,
                                                           duration=duration,
                                                           category=category.name)
        if not action_id:
            return

        embed = nextcord.Embed(
            title=f'Вам выдана блокировка каналов на категорию "{category.name}" на сервере {guild.name}.',
            description=f'Причина: {reason}\nВремя истечения: <t:{int((datetime.datetime.now() + timedelta(seconds=int(duration))).timestamp())}:R>',
            color=0xFF0000
        )
        embed.set_author(name=guild.name, icon_url=guild.icon.url)

        await send_embed(user, embed)
        await interaction.send(
            f'Пользователь {user.display_name}, получил блокировку каналов.\nКатегория:{category.name}\nВремя истечения: <t:{int((datetime.datetime.now() + timedelta(seconds=int(duration))).timestamp())}:R>',
            ephemeral=True)
        await self.wait_block_channel(user, moderator, category, duration, guild, action_id)

    async def remove_block_channel(self, user: nextcord.Member, moderator, category: nextcord.CategoryChannel,
                                   guild: nextcord.Guild, action_id=None):
        await self.database.remove_block_channel(user_id=user if isinstance(user, int) else user.id,
                                                 guild_id=guild.id,
                                                 moderator_id=moderator.id,
                                                 action_id=action_id)
        await category.set_permissions(user, overwrite=None, reason="Снята блокировка после истечения времени.")

    async def find_categories(self, guild: nextcord.Guild, category_name):
        category_find = None
        for category in guild.categories:
            if category_name in category.name:
                category_find = category
        return category_find

    async def wait_block_channel(self, user: nextcord.Member, moderator, category: nextcord.CategoryChannel, duration,
                                 guild: nextcord.Guild, action_id=None):
        seconds = duration
        if seconds > 0:
            await asyncio.sleep(seconds)

        await self.remove_block_channel(user, moderator, category, guild, action_id)


class WarnHandler:
    def __init__(self, handler) -> None:
        self.handler = handler
        self.client = handler.client
        self.database = handler.database

    async def give_warn(self, type_warn, *, user, guild, moderator, reason, approve_moderator=None, jump_url):
        action_id = await self.database.give_warn(user_id=user if isinstance(user, int) else user.id,
                                                  guild_id=guild.id,
                                                  moderator_id=moderator,
                                                  reason=reason,
                                                  warn_type=type_warn,
                                                  approve_moderator=approve_moderator,
                                                  jump_url=jump_url)
        if not action_id:
            return

        embed = nextcord.Embed(
            title=f'Вам выдано предупреждение на сервере {guild.name}.',
            description=f'Причина: {reason}\nВыдал модератор: <@{moderator}>',
            color=0xFF0000
        )
        embed.set_author(name=guild.name, icon_url=guild.icon.url)
        embed.set_footer(text=f'Action ID: {action_id}')

        await send_embed(user if isinstance(user, nextcord.Member) else user, embed)

        log_embed = nextcord.Embed(
            title=f'Выдача предупреждения на сервере {guild.name}',
            color=0xFF0000)
        log_embed.add_field(name='Модератор', value=f'<@{moderator}>')
        log_embed.add_field(name='Причина', value=reason)
        log_embed.add_field(name='Ссылка на сообщение', value=jump_url)
        log_embed.set_footer(text=f'ID: {user if isinstance(user, int) else user.id}')

        return action_id

    async def apply_warn(self, interaction: nextcord.Interaction, user: int, count_warns: int, reason: str, embed,
                         moderator_id: int,
                         approve_moderator=None,
                         kick=True, jump_url=None):
        if count_warns == 3:
            await self.handler.bans.give_ban(
                ActionType.WARN_LOCAL,
                user=user,
                guild=interaction.guild,
                moderator=moderator_id,
                approve_moderator=approve_moderator,
                reason=f'[3/3 WARN] {reason}',
                duration=864000,
                jump_url=jump_url
            )
            await self.handler.database.remove_warns(user_id=user,
                                                     guild_id=interaction.guild.id)
        else:
            action_id = await self.handler.warns.give_warn(
                ActionType.WARN_LOCAL,
                user=user,
                guild=interaction.guild,
                moderator=moderator_id,
                approve_moderator=approve_moderator,
                reason=reason,
                jump_url=jump_url
            )
            if kick:
                try:
                    # Пытаемся получить пользователя
                    member = await interaction.guild.fetch_member(user)
                    if member:
                        # Пытаемся кикнуть пользователя
                        await interaction.guild.kick(member, reason=f"Action ID: {action_id}")
                        await interaction.response.send_message(
                            f"Пользователь {member.name} был кикнут. Причина: Action ID {action_id}.", ephemeral=True)
                    else:
                        await interaction.response.send_message(f"Пользователь с ID {user} не найден на сервере.",
                                                                ephemeral=True)

                except nextcord.errors.NotFound:
                    # Обработка случая, когда пользователь не найден
                    await interaction.response.send_message(f"Пользователь с ID {user} не найден на сервере.",
                                                            ephemeral=True)

                except nextcord.errors.Forbidden:
                    # Обработка случая, когда нет прав на кик пользователя
                    await interaction.response.send_message("У меня нет прав для кика этого пользователя.",
                                                            ephemeral=True)

                except Exception as e:
                    # Общая обработка других возможных исключений
                    await interaction.response.send_message(f"Произошла ошибка: {str(e)}", ephemeral=True)


class BanHandler:
    def __init__(self, handler) -> None:
        self.handler = handler
        self.client = handler.client
        self.database = handler.database

    async def give_ban(self, type_ban, *, user, guild: nextcord.Guild, moderator, reason, duration,
                       approve_moderator=None, jump_url):
        action_id = await self.database.give_ban(user_id=user,
                                                 guild_id=guild.id,
                                                 moderator_id=moderator,
                                                 reason=reason,
                                                 duration=duration,
                                                 ban_type=type_ban,
                                                 approve_moderator=approve_moderator,
                                                 jump_url=jump_url)
        if not action_id:
            return

        embed = nextcord.Embed(
            title=f'Вам выдана блокировка на сервере {guild.name}.',
            description=f'Причина: {reason}\nВремя истечения: <t:{int((datetime.datetime.now() + timedelta(seconds=int(duration))).timestamp())}:R>',
            color=0xFF0000
        )
        embed.set_author(name=guild.name, icon_url=guild.icon.url)
        try:
            member = await guild.fetch_member(user)
            if member:
                await guild.ban(member, reason=reason)
        except:
            member = None

        log_embed = nextcord.Embed(
            title=f'Выдача {f"блокировки на сервере {guild.name}" if type_ban != ActionType.BAN_GLOBAL else "глобальной блокировки."}',
            color=0xFF0000)
        log_embed.add_field(name='Пользователь', value=f'<@{user}>')
        log_embed.add_field(name='Модератор', value=f'<@{moderator}>')
        log_embed.add_field(name='Причина', value=reason)
        log_embed.add_field(name='Время истечения',
                            value=f'{"Никогда" if duration == "-1" else f"<t:{int((datetime.datetime.now() + datetime.timedelta(seconds=int(duration))).timestamp())}:R>"}')
        log_embed.add_field(name='Длительность блокировки',
                            value=beautify_seconds(duration) if duration != '-1' else 'Никогда')
        log_embed.add_field(name='Ссылка на сообщение', value=jump_url)
        log_embed.add_field(name='Блокировка',
                            value='Пользователь не был найден на севрере, при попытке захода будет заблокирован',
                            inline=False) if member is None else None
        log_embed.set_footer(text=f'ID: {user}')
        await self.client.db.actions.send_log(action_id, guild, embed=log_embed)

        if duration != '-1':
            self.client.loop.create_task(self.wait_ban(action_id, duration))

    async def apply_ban(self, interaction, user, duration, reason, embed, moderator_id, approve_moderator=None,
                        jump_url=None):
        await self.handler.bans.give_ban(
            ActionType.BAN_LOCAL,
            user=user,
            guild=interaction.guild,
            moderator=moderator_id,
            approve_moderator=approve_moderator,
            reason=reason,
            duration=duration,
            jump_url=jump_url
        )

    async def wait_ban(self, action_id, seconds):
        seconds = int(seconds)
        if seconds > 0:
            await asyncio.sleep(seconds)
        ban = await self.database.get_ban(action_id=action_id)
        if not ban:
            return

        if ban['type'] == 'global':
            for g in self.client.guilds:
                try:
                    await g.unban(nextcord.Object(ban['user_id']), reason=f'Action ID: {action_id}')
                except:
                    pass
        else:
            guild = self.client.get_guild(ban['guild_id'])
            if not guild:
                return
            try:
                await guild.unban(nextcord.Object(ban['user_id']), reason=f'Action ID: {action_id}')
            except nextcord.NotFound:
                pass
        await self.database.remove_ban(action_id=action_id)

        embed = nextcord.Embed(
            title=f'Срок Вашей блокировки {"всех серверах" if ban["type"] == "global" else "на сервере " + guild.name} истек.',
            description=f'Вы снова можете продолжать общение.',
            color=0x00FF00
        )
        embed.set_author(name=guild.name, icon_url=guild.icon.url)

        await send_embed(await self.client.fetch_user(ban['user_id']), embed)

    async def unban(self, user, guild):
        if (not (
                ban := await self.database.get_ban(user_id=user if isinstance(user, int) else user.id,
                                                   guild_id=guild.id)) or
                not await self.database.remove_ban(user if isinstance(user, int) else user.id, guild.id)):
            return False

        try:
            await guild.unban(user)
        except nextcord.NotFound:
            pass
        if guild:
            embed = nextcord.Embed(
                title='Снятие бана',
                description=f'У пользователя {user.mention} снята блокировка на сервере {guild.name}.',
                color=0x00FF00
            )
            await send_embed(user, embed)

        log_embed = nextcord.Embed(title='Снятие блокировки', color=0x00FF00)
        log_embed.set_author(name=user.display_name, icon_url=user.display_avatar.url)
        log_embed.set_footer(text=f'ID: {ban["_id"]}')
        await self.client.db.actions.send_log(ban['_id'], guild, log_embed)
        return True


def create_punishment_embed(user,
                            moderator: nextcord.Member,
                            reason: str,
                            guild: nextcord.Guild,
                            type_punishment: str,
                            duration: int = None,
                            count_warns: int = None,
                            check=None,
                            unwarn: bool = False,
                            warn_data: dict = None) -> nextcord.Embed:
    types_punishment = {
        'ban': 'блокировки',
        'warn': 'предупреждения',
        'mute': 'мута',
        'unwarn': 'снятия предупреждения'
    }

    title = f"Выдача {types_punishment.get(type_punishment)}" if not unwarn else "Снятие предупреждения"
    color = nextcord.Color.red()
    embed = nextcord.Embed(title=title, color=color)

    if isinstance(user, nextcord.Member):
        embed.set_author(name=user.display_name, icon_url=user.display_avatar.url)
    else:
        embed.set_author(name=str(user), icon_url=guild.icon.url if guild.icon else moderator.display_avatar.url)

    embed.add_field(name='Нарушитель', value=f'<@{user.id if isinstance(user, nextcord.Member) else user}>')

    if unwarn and warn_data:
        embed.add_field(name='Выдавал', value=f'<@{warn_data["moderator_id"]}>')
        embed.add_field(name='Причина', value=warn_data["reason"])
    else:
        embed.add_field(name='Модератор', value=f'<@{moderator.id}>')
        embed.add_field(name='Причина', value=reason)
        if type_punishment == 'warn' and count_warns is not None:
            embed.add_field(name='Количество предупреждений:', value=f"{count_warns}/3")
        elif type_punishment == 'ban':
            embed.add_field(name='Длительность',
                            value=f'{beautify_seconds(duration)}' if duration != '-1' else 'Навсегда')
        elif type_punishment == 'mute':
            embed.add_field(name='Время', value=beautify_seconds(duration))

    embed.set_thumbnail(url=guild.icon.url if guild.icon else moderator.display_avatar.url)

    if check:
        embed.add_field(name='Проверил', value=f'{check.mention}')

    if unwarn:
        embed.set_footer(text=f"Модератор: {moderator.id}")

    return embed


class PunishmentsHandler:
    def __init__(self, client, global_db, mongodb, buttons) -> None:
        self.database = PunishmentsDatabase(client, global_db, mongodb)
        self.client = client
        self.mutes = MuteHandler(self)
        self.bans = BanHandler(self)
        self.warns = WarnHandler(self)
        self.block = BlockChannelHandler(self)
        self.buttons = buttons

    async def reload(self):
        current_mutes = await self.database.get_mutes()
        current_bans = await self.database.get_bans()
        if await load_buttons(self.client, self.buttons, type_buttons='Punishments'):
            await self.client.vk.send_message(123123123, 'Подгрузил все кнопки в наказания.')

        for mute in current_mutes:
            role_name = 'Mute » Text' if mute['type'] == 'text' else 'Mute » Voice' if mute[
                                                                                           'type'] == 'voice' else 'Mute » Full'
            self.client.loop.create_task(self.mutes.wait_mute(mute['_id'],
                                                              ((mute['given_at'] + datetime.timedelta(
                                                                  seconds=mute[
                                                                      'duration'])) - datetime.datetime.now()).total_seconds(),
                                                              role_name,
                                                              await self.client.fetch_user(mute['moderator_id'])))
        for ban in current_bans:
            if ban['duration'] == '-1':
                continue
            self.client.loop.create_task(self.bans.wait_ban(ban['_id'],
                                                            ((ban['given_at'] + datetime.timedelta(seconds=ban[
                                                                'duration'])) - datetime.datetime.now()).total_seconds()))
