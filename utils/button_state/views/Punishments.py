import nextcord

from utils.classes.bot import EsBot
from utils.neccessary import grant_level


class MuteModal(nextcord.ui.Modal):
    def __init__(self, punishments, user: nextcord.Member, message):
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


class WarnModerator(nextcord.ui.Modal):
    def __init__(self, moderator_id):
        super().__init__(title='Параметры наказания', timeout=None)
        self.bot = EsBot()
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
            embed = nextcord.Embed(title='Запрос на подтверждение GMD')
            embed.add_field(name='Модератор', value=interaction.guild.get_member(self.moderator_id).mention)
            embed.add_field(name='Количество предупреждений', value=self.warn.value)
            embed.add_field(name='Причины', value=self.reason.value)
            embed.set_footer(text=f'Подал: {interaction.user.id}')
            await channel.send(embed=embed, view=ApproveDS(self.moderator_id, self.warn, self.reason))
        else:
            await self.bot.vk.send_message(interaction.guild.id,
                                           f'/warn {self.moderator_id}* {self.warn.value} {self.reason.value} | DS')

        await interaction.response.send_message('Выданно', ephemeral=True)
        self.stop()


class PunishmentApprove(nextcord.ui.View):
    def __init__(self, moderator_id, user_id, lvl, role_name=None):
        super().__init__(timeout=30000)
        self.bot = EsBot()
        self.handler = self.bot.db.punishments_handler
        self.moderator = moderator_id
        self.user = user_id
        self.role_name = role_name
        self.lvl = lvl

    @nextcord.ui.button(
        label="Подтвердить", style=nextcord.ButtonStyle.green, emoji='📗',
        custom_id="punishment_request:approve_punishment"
    )
    async def approve_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        if grant_level(interaction.user.roles, interaction.user) < self.lvl:
            return await interaction.send("Вы не можете использовать это", ephemeral=True)
        self.stop()
        await interaction.message.edit(view=None)
        await interaction.message.add_reaction('✅')

    @nextcord.ui.button(
        label="Отказать", style=nextcord.ButtonStyle.red, emoji='📕',
        custom_id="punishment_request:reject_punishment"
    )
    async def cancel(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        if grant_level(interaction.user.roles, interaction.user) < self.lvl:
            return await interaction.response.send_message("Вы не можете использовать это", ephemeral=True)
        self.stop()


class ApproveDS(nextcord.ui.View):
    def __init__(self, moderator_id, warn, reason):
        super().__init__(timeout=None)
        self.bot = EsBot()
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
            return await interaction.send("Вы не можете использовать это", ephemeral=True)
        await self.bot.vk.send_message(interaction.guild.id,
                                       f'/warn {self.moderator_id}* {self.warn.value} {self.reason.value} | GMD')
        await interaction.message.edit(view=None)
        await interaction.message.add_reaction('✅')

    @nextcord.ui.button(
        label="Отменить", style=nextcord.ButtonStyle.red, emoji='📕',
        custom_id="punishment_request:cancel_DS"
    )
    async def cancel(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        if grant_level(interaction.user.roles, interaction.user) < 4:
            return await interaction.send("Вы не можете использовать это", ephemeral=True)
        await interaction.message.edit(view=None)
        await interaction.message.add_reaction('❌')


class CancelPunishments(nextcord.ui.View):
    def __init__(self, moderator_id, user_id, role_name=None):
        super().__init__(timeout=30000)
        self.bot = EsBot()
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
            return await interaction.send("Вы не можете использовать это", ephemeral=True)
        self.stop()
        await interaction.message.edit(view=None)
        await interaction.message.add_reaction('✅')

    @nextcord.ui.button(
        label="Отменить выдачу (GMD | DS)", style=nextcord.ButtonStyle.red, emoji='📕',
        custom_id="punishment_request:cancel"
    )
    async def cancel(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        if grant_level(interaction.user.roles, interaction.user) < 4:
            return await interaction.response.send_message("Вы не можете использовать это", ephemeral=True)
        self.stop()

        moderator = await interaction.guild.fetch_member(int(self.moderator))

        if self.role_name:
            await self.handler.mutes.remove_mute(
                user_id=self.user,
                guild=interaction.guild,
                role_name=self.role_name,
                moderator=moderator,
                cancel=True
            )
        else:
            await self.handler.database.remove_warn(
                user_id=self.user,
                guild_id=interaction.guild.id,
                moderator=moderator
            )

        warn_modal = WarnModerator(moderator_id=interaction.user.id)

        if not interaction.response.is_done():
            await interaction.response.send_modal(warn_modal)
        else:
            await interaction.followup.send("Не удалось открыть модальное окно, так как взаимодействие уже обработано.",
                                            ephemeral=True)

        await interaction.message.edit(view=None)
        await interaction.message.add_reaction('❌')
