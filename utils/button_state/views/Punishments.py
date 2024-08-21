import nextcord

from utils.classes.bot import EsBot
from utils.neccessary import grant_level, beautify_seconds

bot = EsBot()


class MuteModal(nextcord.ui.Modal):
    def __init__(self, punishments, user: int, message):
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

        self.around = None
        if message:
            self.around = nextcord.ui.TextInput(
                label='Кол-во сообщений',
                placeholder='Введите кол-во сообщений (100 макс.)',
                default_value="20")
            self.add_item(self.around)

    async def callback(self, interaction: nextcord.Interaction):
        if self.message:
            if not self.around.value.isdecimal() or int(self.around.value) > 100:
                return await interaction.response.send_message('Кол-во сообщений должно быть числом от 1 до 100',
                                                               ephemeral=True)
            if self.message.id in self.punishments.bot.deleted_messages:
                return await interaction.response.send_message('Другой модератор уже выдал наказание за это сообщение',
                                                               ephemeral=True)
            self.punishments.bot.deleted_messages.append(self.message.id)
        await self.punishments.give_mute(interaction, self.user, self.duration.value, self.reason.value,
                                         'Mute » Text' if self.message else 'Mute » Voice',
                                         message=self.message if self.message else 'VOICE',
                                         message_len=int(self.around.value) if self.around else None)


class RejectApproveModal(nextcord.ui.Modal):
    def __init__(self, punishments, user: int, message: nextcord.Message, embed: nextcord.Embed):
        super().__init__(title='Параметры наказания', timeout=300)
        self.bot = bot
        self.user = user
        self.message = message
        self.punishments = punishments
        self.embed = embed

        self.reason = nextcord.ui.TextInput(
            label='Причина',
            placeholder='Введите причину',
            required=True
        )
        self.add_item(self.reason)

    async def callback(self, interaction: nextcord.Interaction):
        embed = self.embed
        embed.add_field(name='Отказано', value=f'Причина: {self.reason.value}', inline=False)
        await interaction.message.edit(embed=embed, view=None)
        await interaction.message.add_reaction('❌')
        await interaction.response.send_message('+', ephemeral=True)
        await self.bot.buttons.remove_button("Punishments",
                                             message_id=interaction.message.id,
                                             channel_id=interaction.channel_id,
                                             guild_id=interaction.guild.id)


class WarnModerator(nextcord.ui.Modal):
    def __init__(self, moderator_id: int):
        super().__init__(title='Параметры наказания', timeout=None)
        self.bot = bot
        self.handler = self.bot.db.punishments_handler
        self.moderator_id = moderator_id

        self.warn = nextcord.ui.TextInput(
            label='Количество предупреждений',
            placeholder='Введите количество предупреждений',
            max_length=6,
            required=True
        )
        self.add_item(self.warn)

        self.reason = nextcord.ui.TextInput(
            label='Причина',
            placeholder='Введите причину',
            required=True
        )
        self.add_item(self.reason)

    async def callback(self, interaction: nextcord.Interaction):
        if grant_level(interaction.user.roles, interaction.user) < 4:
            channel = [c for c in interaction.guild.text_channels if 'подтверждение-нарушения' in c.name][0]
            if channel:
                embed = nextcord.Embed(title='Запрос на подтверждение GMD')
                embed.add_field(name='Модератор', value=interaction.guild.get_member(self.moderator_id).mention)
                embed.add_field(name='Количество предупреждений', value=self.warn.value)
                embed.add_field(name='Причины', value=self.reason.value)
                embed.set_footer(text=f'Подал: {interaction.user.mention}')
                await channel.send(embed=embed, view=ApproveDS(self.moderator_id, self.warn, self.reason))
            else:
                await interaction.response.defer(ephemeral=True)
                await interaction.followup.send(
                    "Канал 'подтверждение-нарушения' не найден, GMD - не может использовать эту команду по данной причине.",
                    ephemeral=True)
                return
        else:
            await self.bot.vk.send_message(interaction.guild.id,
                                           f'/warn {self.moderator_id}* {self.warn.value} {self.reason.value} | DS')

        await interaction.response.send_message('Выданно', ephemeral=True)
        self.stop()


class PunishmentApprove(nextcord.ui.View):
    def __init__(self, punishment, reason: str, moderator_id: int, user_id: int, lvl: int, *, kick=False, duration=None,
                 count_warns=None,
                 role_name=None):
        super().__init__(timeout=None)
        self.bot = bot
        self.handler = self.bot.db.punishments_handler
        self.moderator = moderator_id
        self.user = user_id
        self.role_name = role_name
        self.lvl = lvl
        self.punishment = punishment
        self.reason = reason
        self.kick = kick
        if duration:
            self.duration = duration
        if count_warns:
            self.count_warns = count_warns

    @nextcord.ui.button(
        label="Подтвердить", style=nextcord.ButtonStyle.green, emoji='📗',
        custom_id="punishment_request:approve_punishment"
    )
    async def approve_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        if grant_level(interaction.user.roles, interaction.user) < self.lvl:
            await interaction.response.defer(ephemeral=True)
            await interaction.followup.send("Вы не можете использовать это", ephemeral=True)
            return
        embed = None
        moderator = await interaction.guild.fetch_member(self.moderator)
        if self.punishment == 'warn':
            embed = create_punishment_embed(self.user,
                                            moderator,
                                            self.reason,
                                            interaction.guild,
                                            type_punishment='warn',
                                            count_warns=self.count_warns,
                                            check=interaction.user)
            await self.handler.warns.apply_warn(interaction, self.user, self.count_warns, self.reason, embed,
                                                moderator_id=self.moderator, kick=self.kick,
                                                approve_moderator=interaction.user.id)
        elif self.punishment == 'ban':
            ban = await self.handler.database.get_ban(user_id=self.user, guild_id=interaction.guild.id)
            if ban:
                await interaction.response.defer(ephemeral=True)
                await interaction.followup.send(f"У пользователя уже есть блокировка | Action_ID: {ban['_id']}",
                                                ephemeral=True)
                await self.bot.buttons.remove_button("Punishments",
                                                     message_id=interaction.message.id,
                                                     channel_id=interaction.channel_id,
                                                     guild_id=interaction.guild.id)
                return await interaction.message.edit(view=None)
            embed = create_punishment_embed(self.user,
                                            moderator,
                                            self.reason,
                                            interaction.guild,
                                            type_punishment='ban',
                                            duration=self.duration,
                                            check=interaction.user)
            await self.handler.bans.apply_ban(interaction, self.user, self.duration, self.reason, embed,
                                              moderator_id=self.moderator, approve_moderator=interaction.user.id)
        await interaction.message.edit(embed=embed, view=None)
        await interaction.message.add_reaction('✅')
        await self.bot.buttons.remove_button("Punishments",
                                             message_id=interaction.message.id,
                                             channel_id=interaction.channel_id,
                                             guild_id=interaction.guild.id)
        self.stop()

    @nextcord.ui.button(
        label="Отказать", style=nextcord.ButtonStyle.red, emoji='📕',
        custom_id="punishment_request:reject_punishment"
    )
    async def cancel(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        if grant_level(interaction.user.roles, interaction.user) < self.lvl:
            await interaction.response.defer(ephemeral=True)
            await interaction.followup.send("Вы не можете использовать это", ephemeral=True)
            return
        user = await interaction.guild.fetch_member(self.user)
        if user is None:
            user = self.user
        moderator = await interaction.guild.fetch_member(self.moderator)
        await self.bot.buttons.remove_button("Punishments",
                                             message_id=interaction.message.id,
                                             channel_id=interaction.channel_id,
                                             guild_id=interaction.guild.id)

        if self.punishment == 'warn':
            embed = create_punishment_embed(user.id,
                                            moderator,
                                            self.reason,
                                            interaction.guild,
                                            type_punishment='warn',
                                            count_warns=self.count_warns,
                                            check=interaction.user)
            modal = RejectApproveModal(punishments='warn', user=self.user, message=interaction.message.id, embed=embed)
        elif self.punishment == 'ban':
            embed = create_punishment_embed(user.id,
                                            moderator,
                                            self.reason,
                                            interaction.guild,
                                            type_punishment='ban',
                                            duration=self.duration,
                                            check=interaction.user)
            modal = RejectApproveModal(punishments='ban', user=self.user, message=interaction.message.id, embed=embed)

        if not interaction.response.is_done():
            await interaction.response.send_modal(modal)
        else:
            await interaction.followup.send("Не удалось открыть модальное окно, так как взаимодействие уже обработано.")
        self.stop()


class ApproveDS(nextcord.ui.View):
    def __init__(self, moderator_id, warn, reason):
        super().__init__(timeout=None)
        self.bot = bot
        self.handler = self.bot.db.punishments_handler
        self.moderator_id = moderator_id
        self.warn = warn
        self.reason = reason

    @nextcord.ui.button(
        label="Одобрить", style=nextcord.ButtonStyle.green, emoji='📗',
        custom_id="punishment_request:approve_button_DS"
    )
    async def approve_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        if grant_level(interaction.user.roles, interaction.user) < 4:
            await interaction.response.defer(ephemeral=True)
            await interaction.followup.send("Вы не можете использовать это", ephemeral=True)
            return
        await self.bot.vk.send_message(interaction.guild.id,
                                       f'/warn {self.moderator_id}* {self.warn.value} {self.reason.value} | GMD')
        await interaction.message.edit(view=None)
        await interaction.message.add_reaction('✅')
        await self.bot.buttons.remove_button("Punishments",
                                             message_id=interaction.message.id,
                                             channel_id=interaction.channel_id,
                                             guild_id=interaction.guild.id)
        self.stop()

    @nextcord.ui.button(
        label="Отменить", style=nextcord.ButtonStyle.red, emoji='📕',
        custom_id="punishment_request:cancel_DS"
    )
    async def cancel(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        if grant_level(interaction.user.roles, interaction.user) < 4:
            await interaction.response.defer(ephemeral=True)
            await interaction.followup.send("Вы не можете использовать это", ephemeral=True)
            return
        await interaction.message.edit(view=None)
        await interaction.message.add_reaction('❌')
        await self.bot.buttons.remove_button("Punishments",
                                             message_id=interaction.message.id,
                                             channel_id=interaction.channel_id,
                                             guild_id=interaction.guild.id)
        self.stop()


class CancelPunishments(nextcord.ui.View):
    def __init__(self, moderator_id: int, user_id: int, role_name=None):
        super().__init__(timeout=30000)
        self.bot = bot
        self.handler = self.bot.db.punishments_handler
        self.moderator = moderator_id
        self.user = user_id
        self.role_name = role_name

    @nextcord.ui.button(
        label="Одобрить выдачу (GMD | DS)", style=nextcord.ButtonStyle.green, emoji='📗',
        custom_id="punishment_request:approve_button"
    )
    async def approve_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        if grant_level(interaction.user.roles, interaction.user) < 4:
            await interaction.response.defer(ephemeral=True)
            await interaction.followup.send("Вы не можете использовать это", ephemeral=True)
            return
        self.stop()
        await interaction.message.edit(view=None)
        await interaction.message.add_reaction('✅')
        await self.bot.buttons.remove_button("Punishments",
                                             message_id=interaction.message.id,
                                             channel_id=interaction.channel_id,
                                             guild_id=interaction.guild.id)
        self.stop()

    @nextcord.ui.button(
        label="Отменить выдачу (GMD | DS)", style=nextcord.ButtonStyle.red, emoji='📕',
        custom_id="punishment_request:cancel"
    )
    async def cancel(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        if grant_level(interaction.user.roles, interaction.user) < 4:
            await interaction.response.defer(ephemeral=True)
            await interaction.followup.send("Вы не можете использовать это", ephemeral=True)
            return
        await self.bot.buttons.remove_button("Punishments",
                                             message_id=interaction.message.id,
                                             channel_id=interaction.channel_id,
                                             guild_id=interaction.guild.id)
        moderator = await interaction.guild.fetch_member(self.moderator)

        if self.role_name:
            await self.handler.mutes.remove_mute(
                user_id=self.user,
                guild=interaction.guild,
                role_name=self.role_name,
                moderator=moderator.id,
                cancel=True
            )
        else:
            await self.handler.database.remove_warn(
                user_id=self.user,
                guild_id=interaction.guild.id,
                moderator=moderator
            )

        warn_modal = WarnModerator(moderator_id=moderator.id)

        if not interaction.response.is_done():
            await interaction.response.send_modal(warn_modal)
        else:
            await interaction.followup.send("Не удалось открыть модальное окно, так как взаимодействие уже обработано.",
                                            ephemeral=True)
        await self.bot.buttons.remove_button("Punishments",
                                             message_id=interaction.message.id,
                                             channel_id=interaction.channel_id,
                                             guild_id=interaction.guild.id)
        await interaction.message.edit(view=None)
        await interaction.message.add_reaction('❌')
        self.stop()


def create_punishment_embed(user: nextcord.Member or int,
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
    if isinstance(moderator, nextcord.Member):
        embed.set_author(name=moderator.display_name, icon_url=moderator.display_avatar.url)
    else:
        embed.set_author(name=str(moderator), icon_url=guild.icon.url if guild.icon else moderator.display_avatar.url)

    embed.add_field(name='Нарушитель', value=f'<@{user if isinstance(user, int) else user.id}>')

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
