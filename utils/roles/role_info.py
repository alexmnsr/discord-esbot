import nextcord
from nextcord import SelectOption

from utils.neccessary import user_visual, send_embed, user_text


class RoleInfo:
    def __init__(self, role_names, tag, rangs):
        self.role_names = role_names
        self.tag = tag
        self.rangs = rangs

    def find(self, guild_roles):
        for role in guild_roles:
            if role.name.lower() in [r.lower() for r in self.role_names]:
                return role
        return None

    def rang_name(self, num):
        return self.rangs[num - 1]


role_info = {
    'Правительство': RoleInfo(['Правительство', 'Пра-во'], 'Пра-во | {}',
                              ["Водитель", "Охранник", "Нач.Охраны", "Секретарь", "Старший секретарь", "Лицензёр",
                               "Адвокат", "Депутат"]),

    'Министерство Обороны': RoleInfo(['Министерство Обороны', 'МО'], 'МО | {}',
                                     ["Рядовой", "Ефрейтор", "Сержант", "Прапорщик", "Лейтенант", "Капитан", "Майор",
                                      "Подполковник"]),
    'Министерство Здравоохранения': RoleInfo(['Министерство Здравоохранения', 'МЗ'], 'МЗ | {}',
                                             ["Интерн", "Фельдшер", "Участковый врач", "Терапевт", "Проктолог",
                                              "Нарколог", "Хирург", "Заведующий отделением"]),
    'Теле-Радио Компания «Ритм»': RoleInfo(['Теле-Радио Компания «Ритм»', 'ТРК'], 'ТРК | {}',
                                           ["Стажёр", "Светотехник", "Монтажёр", "Оператор", "Дизайнер", "Репортер",
                                            "Ведущий", "Режиссёр"]),
    'Министерство Внутренних Дел': RoleInfo(['Министерство Внутренних Дел', 'МВД'], 'МВД | {}',
                                            ["Рядовой", "Сержант", "Старшина", "Прапорщик", "Лейтенант", "Капитан",
                                             "Майор", "Подполковник"]),
    'Федеральная Служба Исполнения Наказаний': RoleInfo(['Федеральная Служба Исполнения Наказаний', 'ФСИН'],
                                                        'ФСИН | {}',
                                                        ["Охранник", "Конвоир", "Надзиратель", "Инспектор"])
}

reasons_dict = {
    "/c 60": ('⏱️', "На скриншоте не видно точного времени."),
    "12 часов": ('⌛', "Скриншоту больше 12 часов."),
    "Номер сервера": ('🔢', "На скриншоте не видно номера сервера."),
    "Не в организации": ('👓', "На скриншоте не видно док-в пребывания в указанной организации."),
    "Никнейм": ('📛', "На скриншоте не совпадает никнейм с указанным."),
    "Невалид": ('🚫', "Скриншот не с игры либо не видно статистику / удостоверение.")
}


def find_role(role_name):
    for key, info in role_info.items():
        if role_name in info.role_names:
            return info
    return None


class ReviewView(nextcord.ui.View):
    def __init__(self, roles_handler):
        super().__init__(timeout=None)
        self.roles_handler = roles_handler

    async def reject_process(self, interaction, value):
        await interaction.response.defer()

        reason = reasons_dict.get(value, value)
        if not isinstance(reason, tuple):
            reason = ('', reason)

        emoji, reason = reason

        embed = interaction.message.embeds[0]
        embed.colour = nextcord.Colour.dark_red()
        embed.title = "📕 Отказанный запрос на роль"
        embed.add_field(name=f'Причина отказа {emoji}', value=reason, inline=False)

        request = await RoleRequest.from_message(interaction.message)
        user, guild = RoleRequest.parse_info(interaction.message)
        await interaction.edit_original_message(embed=embed, view=None)
        if request:
            await request.reject(emoji, reason, user_text(interaction.user))
        await self.roles_handler.remove_request(user, guild, interaction.user.id, False)

    @nextcord.ui.string_select(
        placeholder="Отказать за...", custom_id="role_request:reject", options=[
                                                                                   SelectOption(label=key,
                                                                                                description=value[1],
                                                                                                emoji=value[0],
                                                                                                value=key) for
                                                                                   key, value in reasons_dict.items()
                                                                               ] + [SelectOption(label="Другая причина",
                                                                                                 value="own", emoji='❔',
                                                                                                 description="Откроет меню для ввода вашей причины.")]
    )
    async def reject(self, select: nextcord.ui.Select, interaction: nextcord.Interaction):
        moderator_id = nextcord.utils.parse_raw_mentions(interaction.message.embeds[0].fields[-1].value)[0]
        if moderator_id != interaction.user.id:
            return await interaction.send("Извините, но запросом занимается другой модератор.", ephemeral=True)
        value = select.values[0]
        if value != 'own':
            self.stop()
            await self.reject_process(interaction, value)
        else:
            modal = nextcord.ui.Modal("Отказ роли")
            reason = nextcord.ui.TextInput("Причина")

            async def reject_callback(modal_interaction):
                nonlocal reason
                reason = reason.value
                await self.reject_process(modal_interaction, reason)

            modal.add_item(reason)

            modal.callback = reject_callback

            await interaction.response.send_modal(modal)

    @nextcord.ui.button(
        label="Одобрить", style=nextcord.ButtonStyle.green, emoji='✅', custom_id="role_request:approve"
    )
    async def approve(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        moderator_id = nextcord.utils.parse_raw_mentions(interaction.message.embeds[0].fields[-1].value)[0]
        if moderator_id != interaction.user.id:
            return await interaction.send("Запросом занимается другой модератор.", ephemeral=True)
        self.stop()

        await interaction.response.defer()

        embed = interaction.message.embeds[0]
        embed.colour = nextcord.Colour.dark_green()
        embed.title = "📗 Одобренный запрос на роль"

        request = await RoleRequest.from_message(interaction.message)
        user, guild = RoleRequest.parse_info(interaction.message)
        await interaction.edit_original_message(embed=embed, view=None)
        if request:
            await request.approve(user_text(interaction.user))
        await self.roles_handler.remove_request(user, guild, moderator_id, True)


class StartView(nextcord.ui.View):
    def __init__(self, roles_handler):
        super().__init__(timeout=None)
        self.roles_handler = roles_handler

    @nextcord.ui.button(
        label="Взять запрос", style=nextcord.ButtonStyle.blurple, emoji="📘", custom_id="role_request:take"
    )
    async def take_request(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        self.stop()
        embed = interaction.message.embeds[0]
        embed.title = '📙 Заявление на роль на проверке'
        embed.colour = nextcord.Colour.orange()
        embed.add_field(name="Модератор", value=user_visual(interaction.user), inline=True)
        await interaction.message.edit(view=ReviewView(self.roles_handler), embed=embed)
        await interaction.response.defer()


class RoleRequest:
    def __init__(self, user: nextcord.Member, guild, nickname, rang, role_info_, statistics, statistics_hassle=None):
        self.user = user
        self.guild = guild
        self.nickname = nickname
        self.rang = rang
        self.role_info = role_info_
        self.statistics = statistics
        self.statistics_hassle = statistics_hassle

    @staticmethod
    async def from_message(message: nextcord.Message):
        embed = message.embeds[0]
        nickname = embed.fields[0].value
        role = find_role(message.guild.get_role(nextcord.utils.parse_raw_role_mentions(embed.fields[1].value)[0]).name)
        rang = int(embed.fields[2].value.split(" ")[0])
        try:
            user = await message.guild.fetch_member(nextcord.utils.parse_raw_mentions(embed.fields[3].value)[0])
        except:
            return None
        return RoleRequest(user, message.guild, nickname, rang, role, None)

    @staticmethod
    def parse_info(message: nextcord.Message):
        embed = message.embeds[0]
        user = nextcord.utils.parse_raw_mentions(embed.fields[3].value)[0]
        return nextcord.Object(user), message.guild

    @property
    def in_organization(self):
        for key, value in role_info.items():
            if role := value.find(self.user.roles):
                return role
        return

    @property
    def already_roled(self):
        if self.role_info.find(self.user.roles):
            return True

    @property
    def roles_channel(self):
        return [c for c in self.guild.channels if c.name in 'заявки-на-роли'][0]

    @property
    def check_embed(self):
        embed = nextcord.Embed(
            title='📘 Заявление на роль',
            color=nextcord.Color.dark_blue(),
        )
        embed.add_field(name='Никнейм', value=self.nickname, inline=True)
        embed.add_field(name='Роль', value=self.role_info.find(self.guild.roles).mention, inline=True)
        embed.add_field(name='Ранг', value=f'{self.rang} [{self.role_info.rang_name(self.rang)}]', inline=True)
        embed.add_field(name='Пользователь', value=user_visual(self.user), inline=True)
        embed.set_thumbnail(self.user.display_avatar.url)
        return embed

    @property
    def files(self):
        return [self.statistics, self.statistics_hassle] if self.statistics_hassle else [self.statistics]

    @property
    def must_nick(self):
        tag = f'[{self.role_info.tag.format(self.rang)}] '
        tag = tag + self.nickname.replace("_", " ")
        return tag if len(tag) <= 32 else tag[:30] + '…'

    async def send(self, roles_handler):
        await self.roles_channel.send(embed=self.check_embed, files=self.files, view=StartView(roles_handler))

    async def approve(self, moderator):
        await self.user.add_roles(self.role_info.find(self.guild.roles))
        await self.user.edit(nick=self.must_nick)

        embed = nextcord.Embed(title="📗 Ваше заявление на роль одобрено.", colour=nextcord.Colour.dark_red())
        embed.set_author(name=self.guild.name, icon_url=self.guild.icon.url)
        embed.add_field(name='🧑‍💼 Модератор', value=moderator, inline=False)
        await send_embed(self.user, embed)

    async def reject(self, emoji, reason, moderator):
        embed = nextcord.Embed(title="📕 Ваше заявление на роль отказано.", colour=nextcord.Colour.dark_red())
        embed.set_author(name=self.guild.name, icon_url=self.guild.icon.url)
        embed.add_field(name=f'{emoji} Причина', value=reason)
        embed.add_field(name='🧑‍💼 Модератор', value=moderator, inline=False)
        await send_embed(self.user, embed)
