import asyncio
from datetime import datetime

import nextcord
from nextcord import SelectOption

from utils.neccessary import user_visual, send_embed, user_text, grant_level


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
    'Правительство': RoleInfo(['・Правительство', '・Пра-во'], 'Пра-во | {}',
                              ["Водитель", "Охранник", "Нач.Охраны", "Секретарь", "Старший секретарь", "Лицензёр",
                               "Адвокат", "Депутат"]),

    'Министерство Обороны': RoleInfo(['・Министерство Обороны', '・МО'], 'МО | {}',
                                     ["Рядовой", "Ефрейтор", "Сержант", "Прапорщик", "Лейтенант", "Капитан", "Майор",
                                      "Подполковник"]),
    'Министерство Здравоохранения': RoleInfo(['・Министерство Здравоохранения', '・МЗ'], 'МЗ | {}',
                                             ["Интерн", "Фельдшер", "Участковый врач", "Терапевт", "Проктолог",
                                              "Нарколог", "Хирург", "Заведующий отделением"]),
    'Теле-Радио Компания «Ритм»': RoleInfo(['・ТРК "Ритм"', '・ТРК'], 'ТРК | {}',
                                           ["Стажёр", "Светотехник", "Монтажёр", "Оператор", "Дизайнер", "Репортер",
                                            "Ведущий", "Режиссёр"]),
    'Министерство Внутренних Дел': RoleInfo(['・Министерство Внутренних Дел', '・МВД'], 'МВД | {}',
                                            ["Рядовой", "Сержант", "Старшина", "Прапорщик", "Лейтенант", "Капитан",
                                             "Майор", "Подполковник"]),
    'Министерство Чрезвычайных Ситуаций': RoleInfo(['・Министерство Чрезвычайных Ситуаций', '・МЧС'], 'МЧС | {}',
                                                   ["Рядовой", "Сержант", "Старшина", "Прапорщик", "Лейтенант",
                                                    "Капитан",
                                                    "Майор", "Подполковник"]),
    'Федеральная Служба Исполнения Наказаний': RoleInfo(['・Федеральная Служба Исполнения Наказаний', '・ФСИН'],
                                                        'ФСИН | {}',
                                                        ["Охранник", "Конвоир", "Надзиратель", "Инспектор"])
}

reasons_dict = {
    "/c 60": ('⏱️', "На скриншоте не видно точного времени."),
    "24 часа": ('⌛', "Скриншоту больше 24 часов."),
    "Номер сервера": ('🔢', "На скриншоте не видно номера сервера."),
    "Не в организации": ('👓', "На скриншоте не видно док-в пребывания в указанной организации."),
    "Никнейм": ('📛', "На скриншоте не совпадает никнейм с указанным."),
    "Невалид": ('🚫', "Скриншот не с игры либо не видно статистику / удостоверение."),
    "Не совпадает сервер": ('🚫', "Не совпадает номер сервера с тем, что на скриншоте.")
}


def find_role(role_name):
    for key, info in role_info.items():
        if role_name in info.role_names:
            return info
    return None


class WarnModerator(nextcord.ui.Modal):
    def __init__(self, interaction, moderator_id):
        super().__init__(title='Параметры наказания', timeout=300)
        self.bot = interaction.client
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
            await channel.send(embed=embed, view=ApproveDS(self.bot, self.moderator_id, self.warn, self.reason))
        else:
            await self.bot.vk.send_message(interaction.guild.id,
                                           f'/warn {self.moderator_id}* {self.warn.value} {self.reason.value} | DS')
        await interaction.response.send_message('Выданно', ephemeral=True)
        self.stop()


class ApproveDS(nextcord.ui.View):
    def __init__(self, bot, moderator_id, warn, reason):
        super().__init__(timeout=None)
        self.bot = bot
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


class CancelView(nextcord.ui.View):
    def __init__(self, roles_handler):
        super().__init__(timeout=None)
        self.roles_handler = roles_handler

    @nextcord.ui.button(
        label="Одобрить выдачу (GMD | DS)", style=nextcord.ButtonStyle.green, emoji='📗',
        custom_id="role_request:approve_button"
    )
    async def approve_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        if grant_level(interaction.user.roles, interaction.user) < 4:
            return await interaction.send("Вы не можете использовать это", ephemeral=True)
        self.stop()
        await interaction.message.edit(view=None)
        await interaction.message.add_reaction('✅')

    @nextcord.ui.button(
        label="Отменить выдачу (GMD | DS)", style=nextcord.ButtonStyle.red, emoji='📕', custom_id="role_request:cancel"
    )
    async def cancel(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        fields = interaction.message.embeds[0].fields
        moderator_id = None
        for field in fields:
            if field.name == 'Модератор':
                moderator_id = field.value
                break
        moderator_id = moderator_id[moderator_id.find('<@') + 2:moderator_id.find('>', moderator_id.find('<@') + 2)]
        if grant_level(interaction.user.roles, interaction.user) < 4:
            return await interaction.send("Вы не можете использовать это", ephemeral=True)
        self.stop()

        request = await RoleRequest.from_message(interaction.message)
        user, guild = RoleRequest.parse_info(interaction.message)

        if request:
            if '📗 Одобренный запрос на роль' == interaction.message.embeds[0].title:
                await request.cancel_approve(user_text(interaction.user))
            elif '📕 Отказанный запрос на роль' == interaction.message.embeds[0].title:
                await request.cancel_deny(user_text(interaction.user))

        embed = interaction.message.embeds[0]
        embed.colour = nextcord.Colour.red()
        warn_modal = WarnModerator(interaction, moderator_id=interaction.user.id)
        await interaction.response.send_modal(warn_modal)
        await interaction.message.edit(view=None)
        await interaction.message.add_reaction('❌')
        await self.roles_handler.remove_request(user, guild, True, True, moderator_id=moderator_id,
                                                role=request.role_info.role_names[0],
                                                rang=request.rang, nick=request.nickname)


class ReviewView(nextcord.ui.View):
    def __init__(self, roles_handler):
        super().__init__(timeout=None)
        self.roles_handler = roles_handler

    async def reject_process(self, interaction, values):
        await interaction.response.defer()

        reasons = []
        for value in values:
            if value in reasons_dict:
                reasons.append(reasons_dict.get(value))
            else:
                reasons.append(('❔', value))

        reasons_text = "\n".join([f"{emoji} {reason}" for emoji, reason in reasons])

        embed = interaction.message.embeds[0]
        embed.colour = nextcord.Colour.dark_red()
        embed.title = "📕 Отказанный запрос на роль"
        embed.add_field(name='Причины отказа', value=reasons_text, inline=False)

        request = await RoleRequest.from_message(interaction.message)
        user, guild = RoleRequest.parse_info(interaction.message)
        await interaction.edit_original_message(embed=embed, view=CancelView(self.roles_handler))
        if request:
            await request.reject(reasons_text, user_text(interaction.user))
        await self.roles_handler.remove_request(user, guild, False, False, moderator_id=interaction.user.id,
                                                role=request.role_info.role_names[0],
                                                rang=request.rang, nick=request.nickname)

    @nextcord.ui.string_select(
        placeholder="Отказать за...",
        custom_id="role_request:reject",
        options=[
                    SelectOption(
                        label=key,
                        description=value[1],
                        emoji=value[0],
                        value=key
                    ) for key, value in reasons_dict.items()
                ] + [SelectOption(
            label="Другая причина",
            value="own",
            emoji='❔',
            description="Откроет меню для ввода вашей причины."
        )],
        max_values=len(reasons_dict)
    )
    async def reject(self, select: nextcord.ui.Select, interaction: nextcord.Interaction):
        moderator_id = nextcord.utils.parse_raw_mentions(interaction.message.embeds[0].fields[-1].value)[0]
        if moderator_id != interaction.user.id:
            return await interaction.send("Извините, но запросом занимается другой модератор.", ephemeral=True)

        values = select.values
        if "own" in values:
            modal = nextcord.ui.Modal("Отказ роли")
            reason = nextcord.ui.TextInput("Причина")

            async def reject_callback(modal_interaction):
                nonlocal reason
                values.append(reason.value)
                values.remove('own')
                await self.reject_process(modal_interaction, values)

            modal.add_item(reason)
            modal.callback = reject_callback
            await interaction.response.send_modal(modal)
        else:
            self.stop()
            await self.reject_process(interaction, values)

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
        await interaction.edit_original_message(embed=embed, view=CancelView(self.roles_handler))
        if request:
            await request.approve(user_text(interaction.user))
        await self.roles_handler.remove_request(user, guild, True, False, moderator_id=moderator_id,
                                                role=request.role_info.role_names[0],
                                                rang=request.rang, nick=request.nickname)


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
        now = datetime.utcnow().replace(tzinfo=None)
        created_at = interaction.message.created_at.replace(tzinfo=None)

        check_time = now - created_at
        if check_time.total_seconds() > 1 * 60 * 60:
            _ = asyncio.create_task(self.announce_role(interaction, check_time))
        embed.set_footer(text=f'Взято за {int(check_time.total_seconds() * 1000)} мс.')
        embed.add_field(name="Модератор", value=user_visual(interaction.user))
        await interaction.message.edit(view=ReviewView(self.roles_handler), embed=embed)
        await interaction.response.defer()

    async def announce_role(self, interaction: nextcord.Interaction, check_time):
        bot = interaction.client
        await bot.vk.send_message(
            interaction.guild.id,
            f"Server: {interaction.guild.name} \n"
            f"Заявление на роль было проверено за {round(check_time.total_seconds() / 60)} минут.\n"
            f"Модератор - {interaction.user.display_name}"
        )


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
        return [c for c in self.guild.channels if 'заявки-на-роли' in c.name][0]

    @property
    def check_embed(self):
        embed = nextcord.Embed(
            title='📘 Заявление на роль',
            color=nextcord.Color.dark_blue(),
        )
        embed.add_field(name='Никнейм', value=self.nickname)
        embed.add_field(name='Роль', value=self.role_info.find(self.guild.roles).mention)
        embed.add_field(name='Ранг', value=f'{self.rang} [{self.role_info.rang_name(self.rang)}]')
        embed.add_field(name='Пользователь', value=user_visual(self.user))
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
        try:
            await self.user.edit(nick=self.must_nick)
        except:
            pass
        embed = nextcord.Embed(title="📗 Ваше заявление на роль одобрено.", colour=nextcord.Colour.dark_red())
        embed.set_author(name=self.guild.name, icon_url=self.guild.icon.url)
        embed.add_field(name='🧑‍💼 Модератор', value=moderator, inline=False)
        await send_embed(self.user, embed)

    async def cancel_approve(self, moderator):
        await self.user.remove_roles(self.role_info.find(self.guild.roles))
        try:
            await self.user.edit(nick=self.must_nick)
        except:
            pass
        embed = nextcord.Embed(title="📕 Ваше заявление на роль было перепроверено и отказано",
                               colour=nextcord.Colour.dark_red())
        embed.set_author(name=self.guild.name, icon_url=self.guild.icon.url)
        embed.add_field(name='🧑‍💼 Перепроверил модератор', value=moderator, inline=False)
        await send_embed(self.user, embed)

    async def cancel_deny(self, moderator):
        await self.user.add_roles(self.role_info.find(self.guild.roles))
        try:
            await self.user.edit(nick=self.must_nick)
        except:
            pass
        embed = nextcord.Embed(title="📗 Ваше заявление на роль было перепроверено и одобрено",
                               colour=nextcord.Colour.dark_red())
        embed.set_author(name=self.guild.name, icon_url=self.guild.icon.url)
        embed.add_field(name='🧑‍💼 Перепроверил модератор', value=moderator, inline=False)
        await send_embed(self.user, embed)

    async def reject(self, reason, moderator):
        embed = nextcord.Embed(title="📕 Ваше заявление на роль отказано.", colour=nextcord.Colour.dark_red())
        embed.set_author(name=self.guild.name, icon_url=self.guild.icon.url)
        embed.add_field(name=f'', value=reason)
        embed.add_field(name='🧑‍💼 Модератор', value=moderator, inline=False)
        await send_embed(self.user, embed)
