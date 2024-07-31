import ast

import nextcord
from nextcord.ui import Button

from utils.classes.bot import EsBot


class PointsAdd_View(nextcord.ui.View):
    def __init__(self, moderator_ids, date):
        super().__init__(timeout=None)
        self.bot = EsBot()
        self.moderator_ids = ast.literal_eval(moderator_ids)
        self.date = date

    @nextcord.ui.button(
        label="Выдать поинты", style=nextcord.ButtonStyle.green, emoji='📕', custom_id="points_request:give_points"
    )
    async def add_points_vk(self, button: Button, interaction: nextcord.Interaction):
        member = interaction.guild.get_member(interaction.user.id)
        roles = [r.name.lower() for r in member.roles]
        if 'главный модератор' in roles:
            send_button = '| GMD'
        elif 'следящий за discord' in roles:
            send_button = '| DS'
        else:
            send_button = ''
        for moderator_id, details in self.moderator_ids.items():
            points = details['points']
            reasons = details['reasons']
            if points == 0:
                continue
            reasons_text = " | ".join(reasons)
            await self.bot.vk.send_message(506143782509740052,
                                           f'/point {moderator_id}* {points} {reasons_text} | {self.date}{send_button}')
        await interaction.edit_original_message(view=None)
        await interaction.response.send_message("Поинты были выданы!", ephemeral=True)