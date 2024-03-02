import nextcord


class AbstractChannel:
    def __init__(self, id: int, name: str) -> None:
        self.id = id
        self.name = name


class AbstractUser:
    def __init__(self, id: int, guild: nextcord.Guild) -> None:
        self.id = id
        self.guild = guild
