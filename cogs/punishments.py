import nextcord
from nextcord.ext import commands

from utils.classes.actions import ActionType, human_actions, payload_types
from utils.classes.bot import EsBot
from utils.neccessary import string_to_seconds, add_role, checking_presence, restricted_command, print_user, \
    beautify_seconds, copy_message


class MuteModal(nextcord.ui.Modal):
    def __init__(self, punishments: 'Punishments', user: nextcord.Member, message):
        super().__init__(title='Параметры наказания', timeout=300)
        self.user = user
        self.message = message
        self.punishments = punishments

        self.duration = nextcord.ui.TextInput(
            label='Длительность',
            placeholder='Введите длительность наказания',
            max_length=8,
            required=True
        )
        self.add_item(self.duration)

        self.reason = nextcord.ui.TextInput(
            label='Причина',
            placeholder='Введите причину',
            required=True
        )
        self.add_item(self.reason)

    async def callback(self, interaction: nextcord.Interaction):
        await self.punishments.give_mute(interaction, self.user, self.duration.value, self.reason.value,
                                         'Mute » Text', message=self.message)


class Punishments(commands.Cog):
    def __init__(self, bot: EsBot) -> None:
        self.bot = bot
        self.handler = bot.db.punishments_handler
        self.client = self.handler.client

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
                await give_role('Mute » Text', mute['action_id'])
                await give_role('Mute » Voice', mute['action_id'])
            elif mute['type'] == 'text':
                await give_role('Mute » Text', mute['action_id'])
            elif mute['type'] == 'voice':
                await give_role('Mute » Voice', mute['action_id'])

    @nextcord.slash_command(name='mute')
    @restricted_command(1)
    async def mute_group(self, interaction):
        ...

    async def give_mute(self, interaction, user, duration, reason, role_name, *, message: nextcord.Message=None):
        if isinstance(user, str) and not (user := await self.bot.resolve_user(user)):
            return await interaction.send('Пользователь не найден.')

        mute_seconds = string_to_seconds(duration)
        if not mute_seconds:
            return await interaction.send('Неверный формат длительности мута.')
        get, give, remove = self.handler.mutes.mute_info(role_name)
        if await get(user_id=user.id, guild_id=interaction.guild.id):
            return await interaction.send('У пользователя уже есть мут.')
        embed = ((nextcord.Embed(title='Выдача наказания', color=nextcord.Color.red())
                  .set_author(name=user.display_name, icon_url=user.display_avatar.url))
                 .add_field(name='Нарушитель', value=f'<@{user.id}>', inline=True)
                 .add_field(name='Причина', value=reason, inline=True)
                 .add_field(name='Время', value=beautify_seconds(mute_seconds), inline=True)
                 .set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else user.display_avatar.url)
                 .set_footer(text=f"Модератор: {interaction.user.id}"))

        if message:
            channel = [c for c in message.guild.text_channels if 'выдача-наказаний' in c.name][0]
            await interaction.send(embed=embed, ephemeral=True)
            mess = await channel.send(embed=embed)
            thread = await mess.create_thread(name='📸 Скриншот чата', auto_archive_duration=60)
            jump_url = mess.jump_url
        else:
            mess = await interaction.send(embed=embed)
            jump_url = (await mess.fetch()).jump_url
        await self.handler.mutes.give_mute(role_name, user=user, guild=interaction.guild,
                                           moderator=interaction.user,
                                           reason=reason,
                                           duration=mute_seconds, jump_url=jump_url)
        if message:
            await copy_message(interaction.user, user, message, channel, thread)

    @mute_group.subcommand(name='text', description="Выдать мут пользователю в текстовых каналах.")
    async def mute_text(self, interaction,
                        user: str = nextcord.SlashOption('пользователь',
                                                         description='Пользователь, которому вы хотите выдать мут.',
                                                         required=True),
                        duration: str = nextcord.SlashOption('длительность',
                                                             description='Длительность мута. Пример: 10м - 10 минут, 5д - 5 дней. Просто 10 - 10 минут.',
                                                             required=True),
                        reason: str = nextcord.SlashOption('причина', description='Причина мута.', required=True)):
        await self.give_mute(interaction, user, duration, reason, 'Mute » Text')

    @nextcord.message_command(name='Выдать текстовый мут')
    @restricted_command(1)
    async def mute_text_on_message(self, interaction: nextcord.Interaction, message: nextcord.Message):
        modal = MuteModal(self, message.author, message)
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
    async def mute_full(self, interaction,
                        user: str = nextcord.SlashOption('пользователь',
                                                         description='Пользователь, которому вы хотите выдать мут.',
                                                         required=True),
                        duration: str = nextcord.SlashOption('длительность',
                                                             description='Длительность мута. Пример: 10м - 10 минут, 5д - 5 дней. Просто 10 - 10 минут.',
                                                             required=True),
                        reason: str = nextcord.SlashOption('причина', description='Причина мута.', required=True)):
        await self.give_mute(interaction, user, duration, reason, 'Mute » Full')

    @nextcord.slash_command(name='unmute', description="Снять мут с пользователя.")
    @restricted_command(1)
    async def unmute(self, interaction):
        ...

    async def remove_mute(self, interaction, user, role_name):
        if not (user := await self.bot.resolve_user(user)):
            return await interaction.send('Пользователь не найден.')

        if not await self.handler.mutes.remove_mute(user.id, interaction.guild.id, role_name, interaction.user):
            return await interaction.send('У пользователя нет мута.')

        embed = nextcord.Embed(
            title='Снятие наказания',
            description=f'У пользователя {user.mention} снят мут.')
        await interaction.send(embed=embed)

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
    @restricted_command(2)
    async def warn(self, interaction,
                   user: str = nextcord.SlashOption('пользователь',
                                                    description='Пользователь, которому вы хотите выдать предупреждение.',
                                                    required=True),
                   reason: str = nextcord.SlashOption('причина', description='Причина предупреждения.', required=True)):
        if not (user := await self.bot.resolve_user(user)):
            return await interaction.send('Пользователь не найден.')
        count_warns = len(await self.handler.database.get_warns(user.id, interaction.guild.id)) + 1
        embed = ((nextcord.Embed(title='Выдача предупреждения', color=nextcord.Color.red())
                  .set_author(name=user.display_name, icon_url=user.display_avatar.url))
                 .add_field(name='Нарушитель', value=f'<@{user.id}>', inline=True)
                 .add_field(name='Причина', value=reason, inline=True)
                 .add_field(name='Количество предупреждений: ', value=f"{count_warns}/3", inline=True)
                 .set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else user.display_avatar.url)
                 .set_footer(text=f"Модератор: {interaction.user.id}"))
        message = await interaction.send(embed=embed)
        jump_url = (await message.fetch()).jump_url
        if count_warns == 3:
            await self.handler.bans.give_ban(ActionType.BAN_LOCAL, user=user, guild=interaction.guild,
                                             moderator=interaction.user, reason=f'[3/3 WARN] {reason}', duration=10,
                                             jump_url=jump_url)
            return await self.handler.database.remove_warns(user_id=user.id, guild_id=interaction.guild.id)
        action_id = await self.handler.warns.give_warn(ActionType.WARN_LOCAL, user=user, guild=interaction.guild,
                                                       moderator=interaction.user, reason=reason, jump_url=jump_url)
        await interaction.guild.kick(user, reason=f"Action ID: {action_id}")

    @nextcord.slash_command(name='unwarn', description="Снять предупреждение пользователя")
    @restricted_command(2)
    async def unwarn(self, interaction,
                   user: str = nextcord.SlashOption('пользователь',
                                                    description='Пользователь, которому вы хотите выдать предупреждение.',
                                                    required=True),
                   action_id: int = nextcord.SlashOption('action_id', description='Action ID наказания', required=True)):
        if not (user := await self.bot.resolve_user(user)):
            return await interaction.send('Пользователь не найден.')
        if not (warn_data := await self.handler.database.get_warn(user_id=user.id, guild_id=interaction.guild.id, action_id=action_id)):
            return await interaction.send('Предупреждение не найдено.')
        embed = ((nextcord.Embed(title='Снятие предупреждения', color=nextcord.Color.red())
                  .set_author(name=user.display_name, icon_url=user.display_avatar.url))
                 .add_field(name='Нарушитель', value=f'<@{user.id}>', inline=True)
                 .add_field(name='Выдавал', value=f'<@{warn_data["moderator_id"]}>', inline=True)
                 .add_field(name='Причина', value=f'{warn_data["reason"]}', inline=True)
                 .set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else user.display_avatar.url)
                 .set_footer(text=f"Модератор: {interaction.user.id}"))
        await interaction.send(embed=embed)
        await self.handler.database.remove_warn(user_id=user.id, guild_id=interaction.guild.id, action_id=action_id)

    @nextcord.slash_command(name='ban', description="Заблокировать пользователя на сервере")
    @restricted_command(3)
    async def ban(self, interaction,
                  user: str = nextcord.SlashOption('пользователь',
                                                   description='Пользователь, которому вы хотите выдать блокировку.',
                                                   required=True),
                  duration: int = nextcord.SlashOption('длительность',
                                                       description='Длительность блокировки. Пример: 5 = 5 дней. -1 = навсегда.',
                                                       required=True, min_value=-1, max_value=30),
                  reason: str = nextcord.SlashOption('причина', description='Причина блокировки.', required=True)):
        if not (user := await self.bot.resolve_user(user)):
            return await interaction.send('Пользователь не найден.')

        embed = ((nextcord.Embed(title='Выдача бана', color=nextcord.Color.red())
                  .set_author(name=user.display_name, icon_url=user.display_avatar.url))
                 .add_field(name='Нарушитель', value=f'<@{user.id}>', inline=True)
                 .add_field(name='Длительность', value=f'{duration} дней' if duration != -1 else 'Навсегда',
                            inline=True)
                 .add_field(name='Причина', value=reason, inline=True)
                 .set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else user.display_avatar.url)
                 .set_footer(text=f"Модератор: {interaction.user.id}"))
        mess = await interaction.send(embed=embed)
        jump_url = (await mess.fetch()).jump_url
        await self.handler.bans.give_ban(ActionType.BAN_LOCAL, user=user, guild=interaction.guild,
                                         moderator=interaction.user, reason=reason, duration=duration,
                                         jump_url=jump_url)

    @nextcord.slash_command(name='unban', description="Разблокировать пользователя")
    @restricted_command(3)
    async def unban(self, interaction,
                    user: str = nextcord.SlashOption('пользователь',
                                                     description='Пользователь, которому вы хотите выдать блокировку.',
                                                     required=True),
                    action_id: int = nextcord.SlashOption('номер',
                                                          description='Номер выданного наказания - Action ID  ',
                                                          required=True)):
        if not (user := await self.bot.resolve_user(user)):
            return await interaction.send('Пользователь не найден.')

        ban = await self.handler.database.get_ban(user_id=user.id, guild_id=interaction.guild.id, action_id=action_id,
                                                  type_ban='local')
        if ban:
            await self.handler.database.remove_ban(user_id=user.id, guild_id=interaction.guild.id, action_id=action_id,
                                                   type_ban='local')
        else:
            return interaction.send('Блокировка не найдена')

        await interaction.guild.unban(user, reason=f"Action ID блокировки: {action_id}")

        embed = ((nextcord.Embed(title='Разблокировка пользователя', color=nextcord.Color.red())
                  .set_author(name=user.display_name, icon_url=user.display_avatar.url))
                 .add_field(name='Пользователь', value=f'<@{user.id}>', inline=False)
                 .add_field(name='Блокировал модератор', value=f'<@{ban["moderator_id"]}>', inline=True)
                 .add_field(name='Разблокировал:', value=f'<@{interaction.user.id}>', inline=True)
                 .set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else user.display_avatar.url)
                 .set_footer(text=f"Action ID: {action_id}"))
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
                 .add_field(name='Нарушитель', value=f'<@{user.id}>', inline=True)
                 .add_field(name='Длительность', value=f'{duration} дней' if duration != -1 else 'Навсегда',
                            inline=True)
                 .add_field(name='Причина', value=reason, inline=True)
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
                  action_id: int = nextcord.SlashOption('id', min_value=1000, description='Action ID события')):
        data = await self.handler.database.actions.get_action(action_id)
        if not data:
            return await interaction.send(f'Такого ID не существует.\n'
                                          f'Доступные ID: 1000 - {await self.handler.database.actions.max_id}',
                                          ephemeral=True)
        user = await self.client.fetch_user(data["moderator_id"])
        embed = ((nextcord.Embed(title=human_actions.get(
            data['action_type'].split('.')[-1].lower() if data['action_type'].startswith('ActionType.') else data[
                'action_type'], 'Неизвестное событие'), color=nextcord.Color.red())
                  .set_author(name=interaction.user.display_name, icon_url=user.display_avatar.url))
                 .set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else user.display_avatar.url)
                 .set_footer(text=f'Action ID: {data["_id"]}'))
        embed.add_field(name='Модератор', value=print_user(user), inline=True)
        embed.add_field(name='Пользователь', value=print_user(await self.client.fetch_user(data['user_id'])),
                        inline=True)

        for k, v in payload_types.items():
            if k in data['payload']:
                s = data['payload'][k]
                if k == 'duration':
                    s = beautify_seconds(data['payload'][k])

                embed.add_field(name=v, value=s, inline=True)

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
        list = await self.handler.database.actions.get_punishments(user_id=user.id, guild_id=server,
                                                                   type_punishment=type_punishment)
        list.reverse()

        if len(list) == 0:
            return await interaction.send('Нарушений не найдено.', ephemeral=True)

        pages = [list[i:i + 10] for i in range(0, len(list), 10)]
        current_page = 1

        async def show_page(page_interaction: nextcord.Interaction, page_num: int, is_create: bool = True):
            embed = nextcord.Embed(title=f'📘 Информация о нарушениях пользователя {user.display_name}',
                                   color=nextcord.Colour.dark_blue())

            for items in pages[page_num - 1]:
                reason = items['payload'].get('reason', None)
                duration = items['payload'].get('duration', None)
                embed.add_field(
                    name=f'№{items["_id"]}: {human_actions.get(items["action_type"].split(".")[-1].lower() if items["action_type"].startswith("ActionType.") else items["action_type"], "Неизвестное событие")}',
                    value=f'Время: {items["time"].strftime("%d.%m.%Y %H:%M:%S")}.\n'
                          f'Выдал: <@{items["moderator_id"]}>\n{f"Причина: {reason}" if reason else ""}\n{f"Длительность: {beautify_seconds(duration)}" if duration else ""}',
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
