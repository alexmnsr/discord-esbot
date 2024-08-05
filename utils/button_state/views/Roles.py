import asyncio

from datetime import datetime
import nextcord
from nextcord import SelectOption

from utils.button_state.views.Punishments import WarnModerator
from utils.classes.bot import EsBot
from utils.neccessary import user_visual, send_embed, user_text, grant_level
from utils.roles.role_info import role_info
from utils.roles.role_info import reasons_dict, find_role

bot = EsBot()


# views
class StartView(nextcord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.roles_handler = bot.db.roles_handler
        self.bot = bot

    @nextcord.ui.button(
        label="Взять запрос", style=nextcord.ButtonStyle.blurple, emoji="📘", custom_id="role_request:take"
    )
    async def take_request(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        self.stop()
        await self.bot.buttons.remove_button("Roles",
                                             message_id=interaction.message.id,
                                             channel_id=interaction.channel_id,
                                             guild_id=interaction.guild.id)
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
        await interaction.message.edit(view=ReviewView(), embed=embed)
        params = {}
        await self.bot.buttons.add_button("Roles", message_id=interaction.message.id,
                                          channel_id=interaction.channel.id,
                                          user_request=interaction.user.id,
                                          moderator_id=interaction.user.id,
                                          guild_id=interaction.guild.id,
                                          class_method='ReviewView',
                                          params=params)
        await interaction.response.defer()

    async def announce_role(self, interaction: nextcord.Interaction, check_time):
        bot = interaction.client
        await bot.vk.send_message(
            interaction.guild.id,
            f"Server: {interaction.guild.name} \n"
            f"Заявление на роль было проверено за {round(check_time.total_seconds() / 60)} минут.\n"
            f"Модератор - {interaction.user.display_name}"
        )


class ReviewView(nextcord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.roles_handler = bot.db.roles_handler
        self.bot = bot

    async def reject_process(self, interaction, values):
        await interaction.response.defer()
        await self.bot.buttons.remove_button("Roles",
                                             message_id=interaction.message.id,
                                             channel_id=interaction.channel_id,
                                             guild_id=interaction.guild.id)

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
        action_id = await self.roles_handler.remove_request(user, guild, False, False, moderator_id=interaction.user.id,
                                                role=request.role_info.role_names[0],
                                                rang=request.rang, nick=request.nickname)
        date = datetime.now().strftime('%d.%m.%Y')
        await interaction.edit_original_message(embed=embed, view=CancelRoles(date=date, action_id=action_id))
        params = {
            'date': date,
            'action_id': action_id
        }
        await self.bot.buttons.add_button("Roles", message_id=interaction.message.id,
                                          channel_id=interaction.channel.id,
                                          user_request=interaction.user.id,
                                          moderator_id=interaction.user.id,
                                          guild_id=interaction.guild.id,
                                          class_method='CancelRoles',
                                          params=params)
        if request:
            await request.reject(reasons_text, user_text(interaction.user))

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
            await interaction.response.defer(ephemeral=True)
            await interaction.followup.send("Запросом занимается другой модератор", ephemeral=True)
            return

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
        await self.bot.buttons.remove_button("Roles",
                                             message_id=interaction.message.id,
                                             channel_id=interaction.channel_id,
                                             guild_id=interaction.guild.id)
        moderator_id = nextcord.utils.parse_raw_mentions(interaction.message.embeds[0].fields[-1].value)[0]
        if moderator_id != interaction.user.id:
            await interaction.response.defer(ephemeral=True)
            await interaction.followup.send("Запросом занимается другой модератор", ephemeral=True)
            return
        self.stop()

        await interaction.response.defer()

        embed = interaction.message.embeds[0]
        embed.colour = nextcord.Colour.dark_green()
        embed.title = "📗 Одобренный запрос на роль"

        request = await RoleRequest.from_message(interaction.message)
        user, guild = RoleRequest.parse_info(interaction.message)
        action_id = await self.roles_handler.remove_request(user, guild, True, False, moderator_id=moderator_id,
                                                            role=request.role_info.role_names[0],
                                                            rang=request.rang, nick=request.nickname)
        date = datetime.now().strftime('%d.%m.%Y')
        await interaction.edit_original_message(embed=embed, view=CancelRoles(date=date, action_id=action_id))
        params = {
            'date': date,
            'action_id': action_id
        }
        await self.bot.buttons.add_button("Roles", message_id=interaction.message.id,
                                          channel_id=interaction.channel.id,
                                          user_request=interaction.user.id,
                                          moderator_id=interaction.user.id,
                                          guild_id=interaction.guild.id,
                                          class_method='CancelRoles',
                                          params=params)
        if request:
            await request.approve(user_text(interaction.user))


class CancelRoles(nextcord.ui.View):
    def __init__(self, date, action_id):
        super().__init__(timeout=None)
        self.roles_handler = bot.db.roles_handler
        self.bot = bot
        self.date = date
        self.action_id = action_id

    @nextcord.ui.button(
        label="Одобрить выдачу (GMD | DS)", style=nextcord.ButtonStyle.green, emoji='📗',
        custom_id="role_request:approve_button"
    )
    async def approve_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await self.bot.buttons.remove_button("Roles",
                                             message_id=interaction.message.id,
                                             channel_id=interaction.channel_id,
                                             guild_id=interaction.guild.id)
        if grant_level(interaction.user.roles, interaction.user) < 4:
            await interaction.response.defer(ephemeral=True)
            await interaction.followup.send("Вы не можете использовать это", ephemeral=True)
            return
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
            await interaction.response.defer(ephemeral=True)
            await interaction.followup.send("Вы не можете использовать это", ephemeral=True)
            return
        self.stop()
        await self.bot.buttons.remove_button("Roles",
                                             message_id=interaction.message.id,
                                             channel_id=interaction.channel_id,
                                             guild_id=interaction.guild.id)

        request = await RoleRequest.from_message(interaction.message)
        user, guild = RoleRequest.parse_info(interaction.message)

        if request:
            if '📗 Одобренный запрос на роль' == interaction.message.embeds[0].title:
                await request.cancel_approve(user_text(interaction.user))
            elif '📕 Отказанный запрос на роль' == interaction.message.embeds[0].title:
                await request.cancel_deny(user_text(interaction.user))
        await self.roles_handler.cancel(action_id=self.action_id, moderator_id=interaction.user.id, guild_id=interaction.guild.id)

        embed = interaction.message.embeds[0]
        embed.colour = nextcord.Colour.red()
        warn_modal = WarnModerator(moderator_id=interaction.user.id)
        await interaction.response.send_modal(warn_modal)
        await interaction.message.edit(view=None)
        await interaction.message.add_reaction('❌')
        await self.roles_handler.remove_request(user, guild, True, True, moderator_id=moderator_id,
                                                role=request.role_info.role_names[0],
                                                rang=request.rang, nick=request.nickname)


class RoleRequest:
    def __init__(self, user: nextcord.Member, guild, nickname, rang, role_info_, statistics, statistics_hassle=None):
        self.user = user
        self.guild = guild
        self.nickname = nickname
        self.rang = rang
        self.role_info = role_info_
        self.statistics = statistics
        self.statistics_hassle = statistics_hassle
        self.bot = bot

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

    async def send(self, user_id, guild_id):
        message = await self.roles_channel.send(embed=self.check_embed, files=self.files, view=StartView())
        params = {}
        await self.bot.buttons.add_button("Roles", message_id=message.id,
                                          channel_id=self.roles_channel.id,
                                          user_request=user_id,
                                          moderator_id=None,
                                          guild_id=guild_id,
                                          class_method='StartView',
                                          params=params)

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
