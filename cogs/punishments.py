import datetime

import nextcord
from nextcord.ext import commands

from utils.button_state.views.Punishments import CancelPunishments, PunishmentApprove, MuteModal
from utils.classes.actions import ActionType, human_actions, payload_types
from utils.classes.bot import EsBot
from utils.neccessary import string_to_seconds, checking_presence, restricted_command, print_user, \
    beautify_seconds, copy_message, grant_level


class Punishments(commands.Cog):
    def __init__(self, bot: EsBot) -> None:
        self.bot = bot
        self.handler = bot.db.punishments_handler
        self.client = self.handler.client
        self.handler_buttons = bot.db.state_buttons

    @commands.Cog.listener()
    async def on_ready(self):
        await checking_presence(self.bot)
        await self.handler.reload()

    @commands.Cog.listener()
    async def on_member_join(self, member):
        mutes = await self.handler.mutes.user_muted(member.id, member.guild.id)

        async def give_role(role_name, action_id):
            await member.add_roles(nextcord.utils.get(member.guild.roles, name=role_name),
                                   reason=f'Rejoin. Action ID: {action_id}')

        for mute in mutes:
            if mute['type'] == 'full':
                await give_role('Mute » Text', mute['_id'])
                await give_role('Mute » Voice', mute['_id'])
            elif mute['type'] == 'text':
                await give_role('Mute » Text', mute['_id'])
            elif mute['type'] == 'voice':
                await give_role('Mute » Voice', mute['_id'])

    @nextcord.slash_command(name='tmute', description='Выдать пользователю временный мут (До выяснений)')
    @restricted_command(1)
    async def temp_mute(self, interaction: nextcord.Interaction,
                        user: str = nextcord.SlashOption('пользователь',
                                                         description='Пользователь которому вы хотите выдать временный мут.',
                                                         required=True),
                        duration: str = nextcord.SlashOption('длительность',
                                                             description='Длительность мута. Пример: 10м - 10 минут, 5д - 5 дней. Просто 10 - 10 минут.',
                                                             required=True),
                        reason: str = nextcord.SlashOption('причина', description='Причина мута.', required=True)):
        await self.handler.mutes.give_temp_mute(user,
                                                interaction.guild.id,
                                                interaction.user,
                                                reason,
                                                string_to_seconds(duration))
        embed = nextcord.Embed(
            title=f'Вы выдали временный мут.',
            description=f'Причина: {reason} (До уточнения информации)\nВремя истечения: <t:{int((datetime.datetime.now() + datetime.timedelta(seconds=string_to_seconds(duration))).timestamp())}:R>\nМодератор: {interaction.user.mention}',
            color=0xFF0000
        )
        embed.set_author(name=interaction.guild.name, icon_url=interaction.guild.icon.url)
        await interaction.send(embed=embed)

    @nextcord.slash_command(name='bchannel')
    @restricted_command(2)
    async def block_channel(self, interaction,
                            user: str = nextcord.SlashOption('пользователь',
                                                             description='Пользователь',
                                                             required=True),
                            duration: str = nextcord.SlashOption('длительность',
                                                                 description='Время, на которое будет блокировка каналов',
                                                                 required=True),
                            reason: str = nextcord.SlashOption('причина',
                                                               description='Причина',
                                                               required=True),
                            category: str = nextcord.SlashOption('категория',
                                                                 description='Выбрать категорию для блокировки',
                                                                 choices=["Связь с Discord™", "Связь с Администрацией"],
                                                                 required=True)):
        if isinstance(user, str) and not (user := await self.bot.resolve_user(user, interaction.guild)):
            return await interaction.send('Пользователь не найден.', ephemeral=True)
        seconds = string_to_seconds(duration)
        if not seconds:
            return await interaction.send('Неверный формат длительности мута.')
        category = await self.handler.block.find_categories(interaction.guild, category_name=category)
        if category is None:
            return await interaction.send('Не нашел нужной категории', ephemeral=True)
        await self.handler.block.give_block_channel(interaction, user, interaction.guild, seconds, reason, category)

    @nextcord.slash_command(name='mute')
    @restricted_command(1)
    async def mute_group(self, interaction):
        ...

    async def give_mute(self, interaction, user, duration, reason, role_name, *, message: nextcord.Message = None,
                        message_len: int = None):
        if isinstance(user, str) and not (user := await self.bot.resolve_user(user, interaction.guild)):
            return await interaction.send('Пользователь не найден.', ephemeral=True)
        await interaction.response.defer()
        mute_seconds = string_to_seconds(duration)
        if not mute_seconds:
            return await interaction.send('Неверный формат длительности мута.')
        get, give, remove = self.handler.mutes.mute_info(role_name)
        if await get(user_id=user.id, guild_id=interaction.guild.id):
            return await interaction.send('У пользователя уже есть мут.')
        embed = ((nextcord.Embed(title='Выдача наказания', color=nextcord.Color.red())
                  .set_author(name=user.display_name, icon_url=user.display_avatar.url))
                 .add_field(name='Нарушитель', value=user.mention)
                 .add_field(name='Модератор', value=interaction.user.display_name)
                 .add_field(name='Причина', value=reason)
                 .add_field(name='Время', value=beautify_seconds(mute_seconds))
                 .set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else user.display_avatar.url))
        if message:
            channel = [c for c in interaction.guild.text_channels if 'выдача-наказаний' in c.name][0]
            await interaction.send(embed=embed, ephemeral=True)
            if isinstance(message, nextcord.Message):
                mess = await channel.send(embed=embed, view=CancelPunishments(moderator_id=interaction.user.id,
                                                                              user_id=user.id, role_name=role_name))
                thread = await mess.create_thread(name='📸 Скриншот чата', auto_archive_duration=60)
                jump_url = mess.jump_url
            else:
                mess = await channel.send(embed=embed,
                                          view=CancelPunishments(moderator_id=interaction.user.id,
                                                                 user_id=user.id, role_name=role_name))
                jump_url = mess.jump_url
        else:
            mess = await interaction.send(embed=embed,
                                          view=CancelPunishments(moderator_id=interaction.user.id,
                                                                 user_id=user.id, role_name=role_name))
            jump_url = mess.jump_url

        params = {
            'moderator_id': interaction.user.id,
            'user_id': user.id,
            'role_name': role_name
        }
        await self.bot.buttons.add_button("Punishments", message_id=mess.id,
                                          channel_id=mess.channel.id,
                                          user_request=interaction.user.id,
                                          moderator_id=interaction.user.id,
                                          guild_id=interaction.guild.id,
                                          class_method='CancelPunishments',
                                          params=params)
        await self.handler.mutes.give_mute(role_name, user=user, guild=interaction.guild,
                                           moderator=interaction.user,
                                           reason=reason,
                                           duration=mute_seconds, jump_url=jump_url)
        if isinstance(message, nextcord.Message):
            await copy_message(message, channel, thread, mess, message_len)

    @mute_group.subcommand(name='text', description="Выдать мут пользователю в текстовых каналах.")
    async def mute_text(self, interaction,
                        user: str = nextcord.SlashOption('пользователь',
                                                         description='Пользователь, которому вы хотите выдать мут.',
                                                         required=True),
                        duration: str = nextcord.SlashOption('длительность',
                                                             description='Длительность мута. Пример: 10м - 10 минут, '
                                                                         '5д - 5 дней. Просто 10 - 10 минут.',
                                                             required=True),
                        reason: str = nextcord.SlashOption('причина', description='Причина мута.', required=True)):
        await self.give_mute(interaction, user, duration, reason, 'Mute » Text')

    @nextcord.message_command(name='Выдать текстовый мут', force_global=True)
    @restricted_command(1)
    async def mute_text_on_message(self, interaction: nextcord.Interaction, message: nextcord.Message):
        modal = MuteModal(self, message.author, message)
        await interaction.response.send_modal(modal)

    @nextcord.user_command(name='Выдать голосовой мут')
    @restricted_command(1)
    async def mute_voice_on_message(self, interaction: nextcord.Interaction, user: nextcord.Member):
        modal = MuteModal(self, user, None)
        await interaction.response.send_modal(modal)

    @mute_group.subcommand(name='voice', description="Выдать мут пользователю в голосовых каналах.")
    async def mute_voice(self, interaction,
                         user: str = nextcord.SlashOption('пользователь',
                                                          description='Пользователь которому вы хотите выдать мут.',
                                                          required=True),
                         duration: str = nextcord.SlashOption('длительность',
                                                              description='Длительность мута. Пример: 10м - 10 минут, 5д - 5 дней. Просто 10 - 10 минут.',
                                                              required=True),
                         reason: str = nextcord.SlashOption('причина', description='Причина мута.', required=True)):
        await self.give_mute(interaction, user, duration, reason, 'Mute » Voice')

    @mute_group.subcommand(name='full', description="Выдать полный мут пользователю.")
    @restricted_command(1)
    async def mute_full(
            self,
            interaction,
            user: str = nextcord.SlashOption(
                'пользователь',
                description='Пользователь, которому вы хотите выдать мут.',
                required=True
            ),
            duration: str = nextcord.SlashOption(
                'длительность',
                description='Длительность мута. Пример: 10м - 10 минут, 5д - 5 дней. Просто 10 - 10 минут.',
                required=True
            ),
            reason: str = nextcord.SlashOption('причина', description='Причина мута.', required=True)):
        await self.give_mute(interaction, user, duration, reason, 'Mute » Full')

    @nextcord.slash_command(name='unmute', description="Снять мут с пользователя.")
    @restricted_command(1)
    async def unmute(self, interaction):
        ...

    async def remove_mute(self, interaction, user, role_name):
        if not (user := await self.bot.resolve_user(user)):
            return await interaction.send('Пользователь не найден.', ephemeral=True)

        if not await self.handler.mutes.remove_mute(user.id, interaction.guild, role_name,
                                                    moderator=interaction.user):
            return await interaction.send('У пользователя нет мута.', ephemeral=True)

        embed = nextcord.Embed(
            title='Снятие наказания',
            description=f'У пользователя {user.mention} снят мут.')
        await interaction.send(embed=embed, ephemeral=True)

    @unmute.subcommand(name='text', description="Снять текстовый мут с пользователя.")
    async def unmute_text(self, interaction,
                          user: str = nextcord.SlashOption('пользователь',
                                                           description='Пользователь, у которого вы хотите снять мут.',
                                                           required=True)):
        await self.remove_mute(interaction, user, 'Mute » Text')

    @unmute.subcommand(name='voice', description="Снять голосовой мут с пользователя.")
    async def unmute_voice(self, interaction,
                           user: str = nextcord.SlashOption('пользователь',
                                                            description='Пользователь, у которого вы хотите снять мут.',
                                                            required=True)):
        await self.remove_mute(interaction, user, 'Mute » Voice')

    @unmute.subcommand(name='full', description="Снять полный мут с пользователя.")
    async def unmute_full(self, interaction,
                          user: str = nextcord.SlashOption('пользователь',
                                                           description='Пользователь, у которого вы хотите снять мут.',
                                                           required=True)):
        await self.remove_mute(interaction, user, 'Mute » Full')

    @nextcord.slash_command(name='warn', description="Предупредить пользователя")
    @restricted_command(1)
    async def warn(self, interaction: nextcord.Interaction,
                   user: str = nextcord.SlashOption('пользователь',
                                                    description='Пользователь',
                                                    required=True),
                   reason: str = nextcord.SlashOption('причина',
                                                      description='Причина',
                                                      required=True)):
        resolved_user = await self.bot.resolve_user(user, interaction.guild)
        if not resolved_user:
            return await interaction.send('Пользователь не найден.')

        if isinstance(resolved_user, nextcord.Member) and interaction.user.top_role <= resolved_user.top_role:
            return await interaction.send('Вы не можете наказать этого пользователя.', ephemeral=True)

        count_warns = len(await self.handler.database.get_warns(resolved_user.id, interaction.guild.id)) + 1
        embed = self.handler.warns.create_warn_embed(interaction, resolved_user, count_warns, reason)
        if grant_level(interaction.user.roles, interaction.user) < 2:
            await interaction.send(embed=embed,
                                   view=PunishmentApprove(punishment='warn',
                                                          count_warns=count_warns,
                                                          reason=reason,
                                                          moderator_id=interaction.user.id,
                                                          user_id=resolved_user.id,
                                                          lvl=2))
            message = await interaction.original_message()
            params = {
                'punishment': 'warn',
                'count_warns': count_warns,
                'reason': reason,
                'moderator_id': interaction.user.id,
                'user_id': resolved_user.id,
                'lvl': 2
            }
            await self.bot.buttons.add_button("Punishments", message_id=message.id,
                                              channel_id=interaction.channel_id,
                                              user_request=resolved_user.id,
                                              moderator_id=interaction.user.id,
                                              guild_id=interaction.guild.id,
                                              class_method='PunishmentApprove',
                                              params=params)
        else:
            message = await interaction.send(embed=embed,
                                             view=CancelPunishments(moderator_id=interaction.user.id,
                                                                    user_id=resolved_user.id))
            jump_url = (await message.fetch()).jump_url
            await self.handler.warns.apply_warn(interaction, resolved_user, count_warns, reason, embed,
                                                moderator_id=interaction.user.id, jump_url=jump_url)

    @nextcord.slash_command(name='unwarn', description="Снять предупреждение пользователя")
    @restricted_command(2)
    async def unwarn(self, interaction,
                     user: str = nextcord.SlashOption('пользователь',
                                                      description='Пользователь, которому вы хотите выдать предупреждение.',
                                                      required=True),
                     action_id: int = nextcord.SlashOption('action_id', description='Action ID наказания',
                                                           required=True)):
        if not (user := await self.bot.resolve_user(user)):
            return await interaction.send('Пользователь не найден.')
        if not (warn_data := await self.handler.database.get_warn(user_id=user.id, guild_id=interaction.guild.id,
                                                                  action_id=action_id)):
            return await interaction.send('Предупреждение не найдено.')
        embed = self.handler.warns.create_unwarn_embed(interaction, user, warn_data)
        await interaction.send(embed=embed)
        await self.handler.database.remove_warn(user_id=user.id, guild_id=interaction.guild.id,
                                                moderator_id=interaction.user.id, action_id=action_id)

    @nextcord.slash_command(name='ban', description="Заблокировать пользователя на сервере")
    @restricted_command(1)
    async def ban(self, interaction: nextcord.Interaction,
                  user: str = nextcord.SlashOption('пользователь',
                                                   description='Пользователь',
                                                   required=True),
                  duration: str = nextcord.SlashOption('длительность',
                                                       description='Длительность блокировки. 5 = 5 дней',
                                                       required=True),
                  reason: str = nextcord.SlashOption('причина',
                                                     description='Причина',
                                                     required=True)):
        resolved_user = await self.bot.resolve_user(user, interaction.guild)
        if not resolved_user:
            return await interaction.send('Пользователь не найден.')

        if isinstance(resolved_user, nextcord.Member) and interaction.user.top_role <= resolved_user.top_role:
            return await interaction.send('Вы не можете наказать этого пользователя.', ephemeral=True)

        duration_in_seconds = string_to_seconds(duration, 'd')
        if duration_in_seconds is None:
            return await interaction.send('Неверная длительность блокировки.')

        ban = await self.handler.database.get_ban(user_id=user, guild_id=interaction.guild.id)

        if ban:
            return await interaction.send('У пользователя уже есть блокировка.', ephemeral=True)

        embed = self.handler.bans.create_ban_embed(interaction, resolved_user, duration_in_seconds, reason)
        if grant_level(interaction.user.roles, interaction.user) <= 3:
            await interaction.send(embed=embed, view=PunishmentApprove(punishment='ban', reason=reason,
                                                                       moderator_id=interaction.user.id,
                                                                       user_id=resolved_user.id,
                                                                       lvl=3, duration=duration_in_seconds))
            message = await interaction.original_message()
            params = {
                'punishment': 'ban',
                'reason': reason,
                'moderator_id': interaction.user.id,
                'user_id': resolved_user.id,
                'lvl': 3,
                'duration': duration_in_seconds
            }
            await self.bot.buttons.add_button("Punishments", message_id=message.id,
                                              channel_id=interaction.channel_id,
                                              user_request=resolved_user.id,
                                              moderator_id=interaction.user.id,
                                              guild_id=interaction.guild.id,
                                              class_method='PunishmentApprove',
                                              params=params)
        else:
            message = await interaction.send(embed=embed)
            jump_url = (await message.fetch()).jump_url
            await self.handler.bans.apply_ban(interaction, resolved_user, duration_in_seconds, reason, embed,
                                              moderator_id=interaction.user.id, jump_url=jump_url)

    @nextcord.slash_command(name='unban', description="Разблокировать пользователя")
    @restricted_command(3)
    async def unban(self, interaction,
                    user: str = nextcord.SlashOption('пользователь',
                                                     description='Пользователь, которому вы хотите снять блокировку.',
                                                     required=True)):
        if not (user := await self.bot.resolve_user(user)):
            return await interaction.send('Пользователь не найден.')

        ban = await self.handler.database.get_ban(user_id=user.id, guild_id=interaction.guild.id)
        if ban:
            await self.handler.database.remove_ban(user_id=user.id, guild_id=interaction.guild.id,
                                                   moderator_id=interaction.user.id)
        else:
            return await interaction.send('Блокировка не найдена', ephemeral=True)

        await interaction.guild.unban(user, reason=f"Action ID блокировки: {ban['_id']}")

        embed = ((nextcord.Embed(title='Разблокировка пользователя', color=nextcord.Color.red())
                  .set_author(name=user.display_name, icon_url=user.display_avatar.url))
                 .add_field(name='Пользователь', value=f'<@{user.id}>', inline=False)
                 .add_field(name='Блокировал модератор', value=f'<@{ban["moderator_id"]}>')
                 .add_field(name='Разблокировал:', value=f'<@{interaction.user.id}>')
                 .set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else user.display_avatar.url)
                 .set_footer(text=f"Action ID: {ban['_id']}"))
        return await interaction.send(embed=embed)

    @nextcord.slash_command(name='gban', description="Заблокировать пользователя на всех серверах",
                            default_member_permissions=nextcord.Permissions(administrator=True))
    @restricted_command(5)
    async def gban(self, interaction,
                   user: str = nextcord.SlashOption('пользователь',
                                                    description='Пользователь, которому вы хотите выдать блокировку.',
                                                    required=True),
                   duration: str = nextcord.SlashOption('длительность',
                                                        description='Длительность блокировки. Пример: 5 = 5 дней. -1 = навсегда.',
                                                        required=True),
                   reason: str = nextcord.SlashOption('причина', description='Причина блокировки.', required=True)):

        if not (user := await self.bot.resolve_user(user)):
            return await interaction.send('Пользователь не найден.')

        embed = ((nextcord.Embed(title='Выдача бана на всех серверах', color=nextcord.Color.red())
                  .set_author(name=user.display_name, icon_url=user.display_avatar.url))
                 .add_field(name='Нарушитель', value=f'<@{user.id}>')
                 .add_field(name='Длительность', value=f'{duration} дней' if duration != -1 else 'Навсегда')
                 .add_field(name='Причина', value=reason)
                 .set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else user.display_avatar.url)
                 .set_footer(text=f"Модератор: {interaction.user.id}"))
        mess = await interaction.send(embed=embed)
        jump_url = (await mess.fetch()).jump_url
        await self.handler.bans.give_ban(ActionType.BAN_GLOBAL, user_id=user, guild=interaction.guild.id,
                                         moderator=interaction.user.id, reason=reason, duration=duration,
                                         jump_url=jump_url)

    @nextcord.slash_command(name='act', description="Найти событие по ID")
    @restricted_command(1)
    async def act(self, interaction,
                  action_id: str = nextcord.SlashOption('id', description='Action ID события')):
        data = await self.handler.database.actions.get_action(action_id)
        if not data:
            return await interaction.send(f'Такого ID не существует.', ephemeral=True)
        user = await self.client.fetch_user(data["moderator_id"])
        embed = ((nextcord.Embed(title=human_actions.get(
            data['action_type'].split('.')[-1].lower() if data['action_type'].startswith('ActionType.') else data[
                'action_type'], 'Неизвестное событие'), color=nextcord.Color.red())
                  .set_author(name=interaction.user.display_name, icon_url=user.display_avatar.url))
                 .set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else user.display_avatar.url)
                 .set_footer(text=f'Action ID: {data["_id"]}'))
        embed.add_field(name='Модератор', value=print_user(user))
        embed.add_field(name='Пользователь', value=print_user(await self.client.fetch_user(data['user_id'])))

        for k, v in payload_types.items():
            if k in data['payload']:
                s = data['payload'][k]
                if k == 'duration':
                    s = beautify_seconds(data['payload'][k]) if data['payload'][k] != -1 else 'Навсегда'

                embed.add_field(name=v, value=s)

        return await interaction.send(embed=embed)

    @nextcord.slash_command(name='alist', description="Проверить /alist пользователя")
    @restricted_command(1)
    async def alist(self, interaction,
                    user: str = nextcord.SlashOption('пользователь',
                                                     description='Пользователь, чей список наказаний вы хотите посмотреть.',
                                                     required=True),
                    type_punishment: str = nextcord.SlashOption('тип', description='Тип наказания',
                                                                choices=list(human_actions.values()), default='FULL'),
                    server: str = nextcord.SlashOption('сервер',
                                                       description='Тот на котором запрашиваете (по умолчанию).',
                                                       choices=['Только этот', 'Все'], default='Только этот')):
        if not (user := await self.bot.resolve_user(user)):
            return await interaction.send('Пользователь не найден.')
        if server == 'Только этот':
            server = interaction.guild.id
            punishments_list = await self.handler.database.actions.get_punishments(user_id=user.id, guild_id=server,
                                                                                   type_punishment=type_punishment)
        else:
            punishments_list = await self.handler.database.actions.get_punishments(user_id=user.id,
                                                                                   type_punishment=type_punishment)
        punishments_list.reverse()

        if len(punishments_list) == 0:
            return await interaction.send(f'Нарушений у <@{user.id}> не найдено.', ephemeral=True)

        pages = [punishments_list[i:i + 5] for i in range(0, len(punishments_list), 5)]
        current_page = 1

        async def show_page(page_interaction: nextcord.Interaction, page_num: int, is_create: bool = True):
            embed = nextcord.Embed(title=f'📘 Информация о нарушениях пользователя {user.display_name}',
                                   color=nextcord.Colour.dark_blue())

            for items in pages[page_num - 1]:
                reason = items['payload'].get('reason', None)
                duration = items['payload'].get('duration', None)
                jump_url = items['payload'].get('jump_url', None)
                if server == 'Все':
                    if items['guild_id'] == 690955874008694905:
                        continue
                    guild = await self.bot.fetch_guild(items['guild_id'])
                    server_info = f'Сервер: {guild.name}\n'
                else:
                    server_info = ''
                embed.add_field(
                    name=f'{items["_id"]}: {human_actions.get(items["action_type"].split(".")[-1].lower() if items["action_type"].startswith("ActionType.") else items["action_type"], "Неизвестное событие")}',
                    value=f'{server_info}Время: {items["time"].strftime("%d.%m.%Y %H:%M:%S")}.\n'
                          f'Выдал: <@{items["moderator_id"]}>\n{f"Причина: **[{reason}]({jump_url})**" if reason else "Не указана"}\n{f"Длительность: {beautify_seconds(int(duration))}" if duration else "Не указано"}',
                    inline=False)

            embed.set_footer(text=f'Страница: {page_num} из {len(pages)}')

            view = nextcord.ui.View()
            if page_num > 1:
                button = nextcord.ui.Button(emoji="⬅️")

                async def callback(change_page_interaction):
                    nonlocal page_num
                    await change_page_interaction.response.defer(with_message=False)
                    await show_page(change_page_interaction, page_num - 1)

                button.callback = callback
                view.add_item(button)
            else:
                view.add_item(nextcord.ui.Button(emoji='⬅️', disabled=True))
            if page_num < len(pages):
                button = nextcord.ui.Button(emoji="➡️")

                async def callback(start_page_interaction):
                    nonlocal page_num
                    await start_page_interaction.response.defer(with_message=False)
                    await show_page(start_page_interaction, page_num + 1)

                button.callback = callback
                view.add_item(button)
            else:
                view.add_item(nextcord.ui.Button(emoji='➡️', disabled=True))

            if not is_create:
                await page_interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            else:
                await page_interaction.edit_original_message(embed=embed, view=view)

        await show_page(interaction, current_page, is_create=False)


def setup(bot: EsBot) -> None:
    bot.add_cog(Punishments(bot))
