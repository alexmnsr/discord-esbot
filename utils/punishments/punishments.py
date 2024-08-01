import asyncio
import datetime
import importlib
from datetime import timedelta

import nextcord

from utils.classes.actions import ActionType
from utils.neccessary import remove_role, send_embed, add_role, user_visual, user_text, mute_name, beautify_seconds, \
    remove_temp_role
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

    async def user_muted(self, user_id, guild_id):
        return await self.database.get_mutes(user_id, guild_id)

    async def give_temp_mute(self, user, guild, moderator, reason, duration):
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

    async def give_mute(self, role_name, *, user, guild, moderator, reason, duration, jump_url):
        get, give, remove = self.mute_info(role_name)
        user_id = user.id
        action_id = await give(user_id=user_id, guild_id=guild.id, moderator_id=moderator.id, reason=reason,
                               duration=duration, jump_url=jump_url)
        if not action_id:
            return
        if role_name == 'Mute » Full':
            role_name = ['Mute » Text', 'Mute » Voice']
        guild, member = await add_role(self.client, user_id, guild.id, role_name, action_id)
        if not guild:
            return

        embed = nextcord.Embed(
            title=f'Вам выдан {mute_name(role_name)} мут.',
            description=f'Причина: {reason}\nВремя истечения: <t:{int((datetime.datetime.now() + datetime.timedelta(seconds=duration)).timestamp())}:R>\nВыдал модератор: <@{moderator.id}>',
            color=0xFF0000
        )
        embed.set_author(name=guild.name, icon_url=guild.icon.url)
        embed.set_footer(text=f'Action ID: {action_id}')

        await send_embed(member, embed)

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

        self.client.loop.create_task(self.wait_mute(action_id['_id'], duration, role_name, moderator, member))

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

        await remove(mute['user_id'], mute['guild_id'], moderator)

        if role_name == 'Mute » Full':
            role_name = ['Mute » Text', 'Mute » Voice']
        guild = self.client.get_guild(mute['guild_id'])
        guild, member = await remove_role(mute['user_id'], guild, action_id, role_name)

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
            print(f"Sent embed notification to {member.display_name}.")
        except nextcord.HTTPException as e:
            print(f"Failed to send embed notification to {member.display_name}: {e}")

    async def remove_mute(self, user_id, guild, role_name, moderator, *, cancel=None):
        get, give, remove = self.mute_info(role_name)

        if not (mute := await get(user_id=user_id, guild_id=guild.id)) or not await remove(user_id, guild.id,
                                                                                           moderator=moderator):
            return False
        if role_name == 'Mute » Full':
            role_name = ['Mute » Text', 'Mute » Voice']
        guild, member = await remove_role(user_id, guild, mute['_id'], role_name)

        if cancel:
            await self.database.cancel_mute(user_id=user_id, guild_id=guild.id, moderator_id=moderator.id)

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
        action_id = await self.database.give_block_channel(user_id=user.id,
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
        await self.database.remove_block_channel(user_id=user.id,
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
        action_id = await self.database.give_warn(user_id=user.id,
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

        await send_embed(user.id, embed)

        log_embed = nextcord.Embed(
            title=f'Выдача предупреждения на сервере {guild.name}',
            color=0xFF0000)
        log_embed.add_field(name='Модератор', value=f'<@{moderator}>')
        log_embed.add_field(name='Причина', value=reason)
        log_embed.add_field(name='Ссылка на сообщение', value=jump_url)
        log_embed.set_footer(text=f'ID: {user.id}')

        return action_id

    async def apply_warn(self, interaction, user, count_warns, reason, embed, moderator_id, approve_moderator=None,
                         jump_url=None):
        if count_warns == 3:
            await self.handler.bans.give_ban(
                ActionType.WARN_LOCAL,
                user=user.id,
                guild=interaction.guild,
                moderator=moderator_id,
                approve_moderator=approve_moderator,
                reason=f'[3/3 WARN] {reason}',
                duration=10,
                jump_url=jump_url
            )
            await self.handler.database.remove_warns(user_id=user.id, guild_id=interaction.guild.id)
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
            try:
                await interaction.guild.kick(user, reason=f"Action ID: {action_id}")
            except:
                print('Net prav')

    @staticmethod
    def create_warn_embed(interaction, user, count_warns, reason):
        embed = (nextcord.Embed(title='Выдача предупреждения', color=nextcord.Color.red())
                 .set_author(name=user.display_name, icon_url=user.display_avatar.url)
                 .add_field(name='Нарушитель', value=f'<@{user.id}>')
                 .add_field(name='Причина', value=reason)
                 .add_field(name='Модератор', value=f'<@{interaction.user.id}>')
                 .add_field(name='Количество предупреждений: ', value=f"{count_warns}/3")
                 .set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else user.display_avatar.url))
        return embed

    @staticmethod
    def create_unwarn_embed(interaction, user, warn_data):
        embed = ((nextcord.Embed(title='Снятие предупреждения', color=nextcord.Color.red())
                  .set_author(name=user.display_name, icon_url=user.display_avatar.url))
                 .add_field(name='Нарушитель', value=f'<@{user.id}>')
                 .add_field(name='Выдавал', value=f'<@{warn_data["moderator_id"]}>')
                 .add_field(name='Причина', value=f'{warn_data["reason"]}')
                 .set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else user.display_avatar.url)
                 .set_footer(text=f"Модератор: {interaction.user.id}"))
        return embed


class BanHandler:
    def __init__(self, handler) -> None:
        self.handler = handler
        self.client = handler.client
        self.database = handler.database

    async def give_ban(self, type_ban, *, user, guild, moderator, reason, duration, approve_moderator=None, jump_url):
        action_id = await self.database.give_ban(user_id=user.id,
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

        await send_embed(user.id, embed)
        try:
            await guild.ban(user, reason=f'Action ID: {action_id}')
        except:
            print('miss premissions ban')

        log_embed = nextcord.Embed(
            title=f'Выдача {f"блокировки на сервере {guild.name}" if type_ban != ActionType.BAN_GLOBAL else "глобальной блокировки."}',
            color=0xFF0000)
        log_embed.add_field(name='Модератор', value=f'<@{moderator}>')
        log_embed.add_field(name='Причина', value=reason)
        log_embed.add_field(name='Время истечения',
                            value=f'{"Никогда" if duration == "-1" else f"<t:{int((datetime.datetime.now() + datetime.timedelta(seconds=int(duration))).timestamp())}:R>"}')
        log_embed.add_field(name='Длительность блокировки',
                            value=beautify_seconds(duration) if duration != '-1' else 'Никогда')
        log_embed.add_field(name='Ссылка на сообщение', value=jump_url)
        log_embed.set_footer(text=f'ID: {user.id}')
        await self.client.db.actions.send_log(action_id, guild, embed=log_embed)

        action_id = await self.database.get_ban(user_id=user.id, guild_id=guild.id)

        if duration != '-1':
            self.client.loop.create_task(self.wait_ban(action_id['_id'], duration))

    @staticmethod
    def create_ban_embed(interaction, user, duration, reason):
        embed = (nextcord.Embed(title='Выдача бана', color=nextcord.Color.red())
                 .set_author(name=user.display_name, icon_url=user.display_avatar.url)
                 .add_field(name='Нарушитель', value=f'<@{user.id}>')
                 .add_field(name='Длительность',
                            value=f'{beautify_seconds(duration)}' if duration != '-1' else 'Навсегда')
                 .add_field(name='Причина', value=reason)
                 .set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else user.display_avatar.url)
                 .set_footer(text=f"Модератор: {interaction.user.id}"))
        return embed

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
        if (not (ban := await self.database.get_ban(user_id=user.id, guild_id=guild.id)) or
                not await self.database.remove_ban(user.id, guild.id)):
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


class PunishmentsHandler:
    def __init__(self, client, global_db, mongodb, buttons) -> None:
        self.database = PunishmentsDatabase(client, global_db, mongodb)
        self.client = client
        self.mutes = MuteHandler(self)
        self.bans = BanHandler(self)
        self.warns = WarnHandler(self)
        self.block = BlockChannelHandler(self)
        self.buttons = buttons

    async def get_class_from_file(self, module_name: str, class_name: str):
        module = importlib.import_module(module_name)
        cls = getattr(module, class_name, None)

        if isinstance(cls, type):
            return cls
        return None

    async def load_buttons(self):
        loaded_buttons = await self.buttons.load_all_buttons()

        for button_data in loaded_buttons['Punishments']:
            module_name = 'utils.button_state.views.Punishments'
            message_id = button_data.get('message_id')
            channel_id = button_data.get('channel_id')
            class_name = button_data.get('class_method')
            selected_class = await self.get_class_from_file(module_name, class_name)
            if selected_class:
                print(f"Класс {selected_class.__name__} найден.")
            else:
                print(f"Класс {selected_class.__name__} не найден.")
            params = button_data.get('params', {})
            view = selected_class(**params)

            channel = self.client.get_channel(channel_id)
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

    async def reload(self):
        current_mutes = await self.database.get_mutes()
        current_bans = await self.database.get_bans()
        await self.load_buttons()

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
