from disnake.ext import commands
from disnake import Embed, Color
from database import execute_operation
from datetime import datetime as dt
from commands.accesses import access_commands as is_access_command
from commands.get_info_moderate import get_user_info


class OnlineCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(name='access', description='выдача личного доступа')
    async def access(self, ctx, cmd, user_id, sys=None):
        if is_access_command(ctx, cmd):
            user = await get_user_info(ctx, user_id)
            if not user:
                await ctx.send(f'Пользователь с ID {user_id} не найден на сервере.')
                return
            if sys == '-d':
                execute_operation('discord-esbot', 'delete', table_name='personal_access_cmd',
                                  where=f'`cmd` = "{cmd}" AND `id_user` = {user_id} AND `server_id` = {ctx.guild.id}',
                                  commit=True)
                embed = Embed(
                    title=f'Снятие личного доступа',
                    description=f'Команда: /{cmd}\n↳ Пользователь: {user.display_name} (ID: {user_id})',
                    color=Color.red())
                await ctx.send(embed=embed)
            else:
                values = {
                    'cmd': cmd,
                    'id_user': user_id,
                    'server_id': ctx.guild.id
                }
                execute_operation('discord-esbot', 'insert', 'personal_access_cmd', values=values,
                                  commit=True)
                embed = Embed(
                    title=f'Выдача личного доступа',
                    description=f'Команда: /{cmd}\n↳ Пользователь: {user.name} (ID: {user_id})',
                    color=Color.red())
                await ctx.send(embed=embed)
        else:
            await ctx.send('Вы не имеете доступа к данной команде.')

    async def process_moderator_command(self, ctx, *args):
        if len(args) < 3:
            await ctx.send(
                'Не указаны необходимые аргументы. Пример использования: /moderator user_id nick_name role (удалить: -d)')
            return

        sys_flag = args[-1] if args[-1] == "-d" else None
        id_user = args[-3] if not sys_flag else args[-4]
        nickname = args[-2] if not sys_flag else args[-3]
        role = args[-1] if not sys_flag else args[-2]
        if role == "SYS" and ctx.author.id != 479244541858152449:
            await ctx.send(f'Данную роль может выдать только системный администратор (vk.com/alexmnsr)')
            return
        user_info = await get_user_info(ctx, id_user)
        select_md = execute_operation('discord-esbot', 'select', 'moderator_servers',
                                      columns='id_user, role_user',
                                      where=f'`server_id`={ctx.guild.id}')
        if sys_flag == '-d':
            if not select_md:
                await ctx.send(f'Пользователь с ID {id_user} не найден в списке модераторов.')
                return
            execute_operation('discord-esbot', 'delete', 'moderator_servers',
                              where=f'`id_user`={id_user} AND `id_server`={ctx.guild.id}',
                              commit=True)
            embed = Embed(
                title=f'Удаление модератора:',
                description=f'↳ID: {id_user}\n↳Ник дискорда: {user_info.name}\n↳Ник на сервере: {user_info.display_name}',
                color=Color.green())
            await ctx.send(embed=embed)
        else:
            if select_md:
                await ctx.send(f'Пользователь с ID {id_user} уже находится списке модераторов.')
                return
            values = {
                'id_user': id_user,
                'id_server': ctx.guild.id,
                'nickname_user': nickname,
                'role_user': role
            }
            execute_operation('discord-esbot', 'insert', 'moderator_servers', values=values,
                              commit=True)
        embed = Embed(
            title=f'Добавление модератора:',
            description=f'↳ID: {id_user}\n↳Ник дискорда: {user_info.name}\n↳Ник на сервере: {user_info.display_name}',
            color=Color.green())
        await ctx.send(embed=embed)

    @commands.command(name='moderator', description='добавить модератора')
    async def moderator(self, ctx, *args):
        if is_access_command(ctx, cmd='moderator'):
            await self.process_moderator_command(ctx, *args)
        else:
            await ctx.send('Вы не имеете доступа к данной команде.')

    @commands.slash_command(name='moderator', description='добавить модератора')
    async def slash_moderator(self, ctx, *args):
        await self.moderator(ctx, *args)

    async def process_add_exception_command(self, ctx, *args):
        if len(args) < 1:
            await ctx.send(
                'Не указаны необходимые аргументы. Пример использования: /exception channel_id++ (удалить: -d)')
            return
        sys_flag = args[-1] if args[-1] == "-d" else None
        channels = args[0:] if not sys_flag else args[:-1]

        for channel_id in channels:
            try:
                id_channel = int(channel_id)
                name_channel = self.bot.get_channel(id_channel)
                select_except = execute_operation('discord-esbot', 'select', 'servers_exceptions',
                                                  columns='id',
                                                  where=f'`id`={id_channel} AND `id_server`={ctx.guild.id}')
                if sys_flag and sys_flag == '-d':
                    if not select_except:
                        await ctx.send(f'Такого канала не было найдено в исключениях. Список /exceptions')
                        return
                    else:
                        execute_operation('discord-esbot', 'delete', 'servers_exceptions',
                                          where=f'`id`={id_channel} AND `id_server`={ctx.guild.id}',
                                          commit=True)
                        embed = Embed(
                            title=f'Удалил исключение:',
                            description=f'↳ID канала: {id_channel}\n↳Название канала: {name_channel}',
                            color=Color.green())
                        await ctx.send(embed=embed)
                else:
                    if select_except:
                        await ctx.send(f'Такой канал уже состоит в исключениях. Список /exceptions')
                        return
                    values = {
                        'id': id_channel,
                        'name_channel': name_channel.name,
                        'id_server': ctx.guild.id
                    }
                    execute_operation('discord-esbot', 'insert', 'servers_exceptions', values=values,
                                      commit=True)
                    embed = Embed(
                        title=f'Добавил исключение:',
                        description=f'↳ID канала: {id_channel}\n↳Название канала: {name_channel}',
                        color=Color.green())
                    await ctx.send(embed=embed)

            except ValueError:
                await ctx.send(f'Неверный формат ID канала: {channel_id}')

    @commands.command(name='exception', description='добавление исключения') # fix
    async def exception(self, ctx, *args):
        if is_access_command(ctx, cmd='exception'):
            await self.process_add_exception_command(ctx, *args)
        else:
            await ctx.send('Вы не имеете доступа к данной команде.')

    @commands.slash_command(name='a_role', description='доступ по роли')
    async def a_role(self, ctx, *args):
        if is_access_command(ctx, cmd='a_role'):
            await self.process_access_role(ctx, *args)
        else:
            await ctx.send('Вы не имеете доступа к данной команде.')

    async def process_access_role(self, ctx, *args):
        if len(args) < 2:
            await ctx.send(
                'Не указаны необходимые аргументы. Пример использования: /add_exception channel_id1 channel_id2 -d')
            return
        sys_flag = args[-1] if len(args) == 3 else None
        role = args[-1] if not sys_flag else args[-2]
        cmd = args[-2] if not sys_flag else args[-3]
        select_role = execute_operation('discord-esbot', 'select', 'access_roles',
                                        columns='role, cmd',
                                        where=f'`server_id`={ctx.guild.id}')
        if sys_flag and sys_flag == '-d':
            if not select_role:
                await ctx.send(f'Такая роль не имеет доступа к команде /{cmd}.')
                return
            execute_operation('discord-esbot', 'delete', 'access_roles',
                              where=f'`role`="{role}" AND `server_id`={ctx.guild.id} AND `cmd`="{cmd}"',
                              commit=True)
            embed = Embed(
                title=f'Снятие доступа по роли',
                description=f'Команда: /{cmd}\n↳ Роль: {role}',
                color=Color.red())
            await ctx.send(embed=embed)
        else:
            if select_role:
                await ctx.send(f'Такая роль уже имеет доступ к команде /{cmd}.')
                return
            values = {
                'role': role,
                'server_id': ctx.guild.id,
                'cmd': cmd
            }
            execute_operation('discord-esbot', 'insert', 'access_roles', values=values,
                              commit=True)
            embed = Embed(
                title=f'Выдача доступа по роли',
                description=f'Команда: /{cmd}\n↳ Роль: {role}',
                color=Color.red())
            await ctx.send(embed=embed)

    @commands.slash_command(name='stats', description='статистика онлайна')
    async def online_user(self, ctx, user_id=None, date=None):
        if is_access_command(ctx, cmd='stats'):
            if user_id is None:
                user_id = ctx.author.id
                date = dt.now().strftime("%d-%m-%Y")
            member = await get_user_info(ctx, user_id)
            if not member:
                await ctx.send(f'Пользователь с ID {user_id} не найден на сервере.')
                return
            query = execute_operation('discord-esbot', 'select', 'logs_users_time_on_voice',
                                      columns='*',
                                      where=f'`user_id`={user_id} AND `date` = \'{date}\' AND `id_server`={ctx.guild.id}')

            query_exception = execute_operation('discord-esbot', 'select', 'servers_exceptions', columns='id',
                                                where=f'`id_server` = {ctx.guild.id}')

            if not query:
                await ctx.send(
                    f'Нет статистики за {date} для пользователя  {member.name} "{member.display_name}" (ID: {user_id})')
                return

            channel_stats = {}
            total_time = 0

            for info_user in query:
                if info_user['id_channel'] not in [exc['id'] for exc in query_exception]:
                    real = info_user['time_leave_voice'] - info_user['time_start']
                    total_time += real

                    channel_name = info_user["name_channel"]
                    channel_stats[channel_name] = channel_stats.get(channel_name, 0) + real

            embed = Embed(title=f'Статистика {query[0]["user_name"]} за {date}', color=Color.green())

            for channel, channel_time in channel_stats.items():
                embed.add_field(name=f'В канале "{channel}":',
                                value=f'{dt.utcfromtimestamp(channel_time).strftime("%H ч. %M м. %S с.")}',
                                inline=False)

            embed.add_field(name='Итоговое время в каналах:',
                            value=f'{dt.utcfromtimestamp(total_time).strftime("%H ч. %M м. %S с.")}', inline=False)

            await ctx.send(embed=embed)
        else:
            print("Не имеете доступа к данной команде")
