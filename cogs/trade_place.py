import nextcord
from nextcord.ext import commands

from utils.classes.bot import EsBot
from utils.neccessary import restricted_command


class TradePlace(commands.Cog):
    def __init__(self, bot: EsBot) -> None:
        self.bot = bot

    @nextcord.slash_command(name='trade', description="tp")
    @restricted_command(5)
    async def start(self, interaction: nextcord.Interaction):
        view = TradeView()
        await interaction.send("Пожалуйста, выберите торговую площадку:", view=view, ephemeral=True)


class TradeModal(nextcord.ui.Modal):
    def __init__(self, trade_info):
        super().__init__(title="Заявление на торговую площадку")
        self.add_item(nextcord.ui.TextInput(label="Введите текст"))
        self.trade_info = trade_info  # Сохраняем информацию о торговле

    async def callback(self, interaction: nextcord.Interaction):
        await interaction.send(f"Вы ввели: {self.children[0].value}\nИнформация о торговле: {self.trade_info}",
                               ephemeral=True)


class SelectTradePlace(nextcord.ui.Select):
    def __init__(self):
        trade_places = [
            nextcord.SelectOption(label="Транспорт", value="car", description='Автомобили, вертолеты и.т.д'),
            nextcord.SelectOption(label="Недвижимость", value="house", description='Дом, квартира, гараж, огород'),
            nextcord.SelectOption(label="Бизнес", value="business"),
        ]
        super().__init__(placeholder="Выберите торговую площадку...", min_values=1, max_values=1, options=trade_places)

    async def callback(self, interaction: nextcord.Interaction):
        selected_label = next(option.label for option in self.options if option.value == self.values[0])
        self.disabled = True
        self.placeholder = selected_label
        self.view.selected_trade_place = self.values[0]
        self.view.add_item(SelectTypeTrade())
        await interaction.edit(view=self.view)


class SelectTypeTrade(nextcord.ui.Select):
    def __init__(self):
        trade_types = [
            nextcord.SelectOption(label="Покупка", value="buy", description='Если Вы хотите что-то купить'),
            nextcord.SelectOption(label="Продажа", value="sell", description='Если Вы хотите что-то продать'),
            nextcord.SelectOption(label="Обмен", value="trade", description='Если Вы хотите что-то обменять'),
            nextcord.SelectOption(label="Аренда", value="rent", description='Если Вы хотите что-то арендовать'),
        ]
        super().__init__(placeholder="Выберите тип сделки...", min_values=1, max_values=1, options=trade_types)

    async def callback(self, interaction: nextcord.Interaction):
        selected_label = next(option.label for option in self.options if option.value == self.values[0])
        self.disabled = True
        self.placeholder = selected_label
        self.view.selected_trade_type = self.values[0]
        if self.values[0] == 'trade':
            self.view.add_item(SelectTrade())
        else:
            self.view.add_item(SelectPrice(self.values[0]))
        await interaction.edit(view=self.view)


class SelectTrade(nextcord.ui.Select):
    def __init__(self):
        trade_types = []

        trade_types.append(nextcord.SelectOption(label="500.000", value="500000"))
        trade_types.append(nextcord.SelectOption(label="1.000.000", value="1000000"))
        trade_types.append(nextcord.SelectOption(label="5.000.000", value="5000000"))
        trade_types.append(nextcord.SelectOption(label="10.000.000", value="10000000"))
        trade_types.append(nextcord.SelectOption(label="Своя цена / бюджет", value="custom",
                                                 description='Выбираете, если хотите указать свою цену'))

        super().__init__(placeholder="Выберите цену/бюджет сделки...", min_values=1, max_values=1, options=trade_types)


class SelectPrice(nextcord.ui.Select):
    def __init__(self, trade_type):
        trade_types = []

        # Условная логика для добавления опций в зависимости от типа сделки
        if trade_type == 'buy' or trade_type == 'rent':
            trade_types.append(nextcord.SelectOption(label="Свободный", value="free"))
        elif trade_type == 'sell':
            trade_types.append(nextcord.SelectOption(label="Договорная", value="negotiable"))

        trade_types.append(nextcord.SelectOption(label="500.000", value="500000"))
        trade_types.append(nextcord.SelectOption(label="1.000.000", value="1000000"))
        trade_types.append(nextcord.SelectOption(label="5.000.000", value="5000000"))
        trade_types.append(nextcord.SelectOption(label="10.000.000", value="10000000"))
        trade_types.append(nextcord.SelectOption(label="Своя цена / бюджет", value="custom",
                                                 description='Выбираете, если хотите указать свою цену'))

        super().__init__(placeholder="Выберите цену/бюджет сделки...", min_values=1, max_values=1, options=trade_types)

    async def callback(self, interaction: nextcord.Interaction):
        selected_label = next(option.label for option in self.options if option.value == self.values[0])
        self.disabled = True
        self.placeholder = selected_label
        self.view.selected_trade_price = self.values[0]
        self.view.add_item(SelectMethodTrade())
        await interaction.edit(view=self.view)


class SelectMethodTrade(nextcord.ui.Select):
    def __init__(self):
        trade_types = [
            nextcord.SelectOption(label="Discord",
                                  value="ds",
                                  description='В заявке будет указан Ваш Discord для связи'),
            nextcord.SelectOption(label="Сим-карта",
                                  value="number",
                                  description='В заявке будет указан Ваш номер для связи'),
            nextcord.SelectOption(label="Discord и Сим-карта",
                                  value="dsnumber",
                                  description='В заявке будет указан номер и Discord')
        ]
        super().__init__(placeholder="Выберите способ связи с Вами...", min_values=1, max_values=1, options=trade_types)

    async def callback(self, interaction: nextcord.Interaction):
        selected_label = next(option.label for option in self.options if option.value == self.values[0])
        self.disabled = True
        self.placeholder = selected_label
        await interaction.edit(view=self.view)

        trade_info = {
            "trade_place": self.view.selected_trade_place,
            "trade_type": self.view.selected_trade_type,
            "trade_price": self.view.selected_trade_price,
            "method_trade": self.values[0],
        }
        await interaction.response.send(modal=TradeModal(trade_info))


class TradeView(nextcord.ui.View):
    def __init__(self):
        super().__init__()
        self.selected_trade_place = None
        self.selected_trade_type = None
        self.selected_trade_price = None
        self.selected_method_trade = None
        self.add_item(SelectTradePlace())


def setup(bot: EsBot) -> None:
    bot.add_cog(TradePlace(bot))
