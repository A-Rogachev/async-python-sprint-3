import logging
from typing import Any
import asyncio
import datetime
from collections import namedtuple

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())


ChatUser = namedtuple('ChatUser', ['nickname', 'writer', 'private_messages', 'claims', 'last_visit'])

class Server:
    """
    Асинхронный мессенджер (сервер).
    """
    def __init__(
        self,
        host="127.0.0.1",
        port: int = 8000,
        max_chat_messages: int = 10,
        message_ttl: int = 10,
    ):
        """
        Инициализация экземпляра класса Сервер.
        """
        self.host: str = host
        self.port: int = port
        self.max_chat_messages: int = max_chat_messages
        self.message_ttl = message_ttl
        self.claims = {}

        self.registered_users = {}
        self.chat_messages = []
        self.connected_clients: dict[str, Any] = {}
        self.help_message = (
            'help!@<username> <message> -> send private message to user\n'
            'help!@help -> show this message\n'
            'help!!!<username> -> claim a user\n'
            'help!@exit -> exit from the messenger\n'
        )

    async def client_connected(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """
        Обработка подключения нового клиента к серверу.
        """
        address: str = writer.get_extra_info('peername')

        user_info: str = (await reader.readline()).decode().strip().split()
        connection = False
        if len(user_info) == 2:
            user_nickname, user_password = user_info
            if user_nickname in self.registered_users:
                if self.registered_users[user_nickname].get('password') != user_password:
                    writer.write('AuthError!Wrong password! Try again!\n'.encode())
                    await writer.drain()
                    writer.close()
                else:
                    self.registered_users[user_nickname]['last_visit'] = datetime.datetime.now()
                    writer.write('Connected!'.encode())
                    await writer.drain()
                    connection = True
            else:
                writer.write('AuthError!User not found! Register first!\n'.encode())
                await writer.drain()
                writer.close()
        elif len(user_info) == 3:
            _, user_nickname, user_password = user_info
            if user_nickname in self.registered_users:
                writer.write('AuthError!User already exists! Try another name!\n'.encode())
                await writer.drain()
                writer.close()
            else:
                self.registered_users[user_nickname] = {
                    'password': user_password,
                    'last_visit': datetime.datetime.now(),
                    'claims': [],
                    'private_messages': [],
                }
                # writer.write('Connected!'.encode())
                # await writer.drain()
                connection = True

        if connection:
            self.connected_clients[user_nickname] = {
                'writer': writer,
            }
            logger.info(
                f'---User {user_nickname} is connected--- '
                f'(ip={address[0]}, port={address[1]})'
            )

            if self.chat_messages:
                for message in self.chat_messages[-self.max_chat_messages:]:
                    writer.write(f'History!{message[1]}\n'.encode())
                    await writer.drain()

            while True:
                data = await reader.read(1024)
                if not data:
                    break
                message: str = data.decode().strip()
                if message.startswith('@'):
                    await self.handle_command(message, user_nickname, writer)
                else:
                    self.chat_messages.append(
                        (
                            message_date := datetime.datetime.now(),
                            message_text := (
                                f'({message_date.strftime("%d.%m.%y %H:%M:%S")}) '
                                f'{user_nickname}: {message}'
                            )
                        )
                    )
                    logger.info(f'new message: {message_text}')
                    await self.broadcast_message(message_text)
                await writer.drain()

            logger.info(f'---User {user_nickname} disconnected---')
            writer.close()
            del self.connected_clients[user_nickname]

    async def handle_command(
        self,
        message: str,
        user_nickname: str,
        writer: asyncio.StreamWriter,
    ) -> None:
        """
        Обработка команд мессенджера.
        """
        if message == '@help':
            await self.send_help_message(writer)
        elif message.startswith('@claim'):
            await self.add_claim_to_user(message, user_nickname, writer)
        else:
            await self.send_private_message(message, user_nickname, writer)

    async def add_claim_to_user(
        self,
        message: str,
        user_nickname: str,
        writer: asyncio.StreamWriter,
    ) -> None:
        """
        Добавление жалобы на пользователя.
        """
        tokens = message[1:].split(' ', 1)
        if len(tokens) == 2:
            recipient = tokens[1]
            if recipient in self.connected_clients:
                self.claims[recipient] # TODO : здесь добавить или нет
                self.connected_clients[recipient]['claims'].append(user_nickname)
                writer.write(f'Server!User {recipient} claimed by {user_nickname}\n'.encode())
                await writer.drain()
            else:
                writer.write(f'Server!User {recipient} is not connected\n'.encode())
                await writer.drain()
        else:
            writer.write('Server!Don\'t use @ symbol if its not a command!\n'.encode())
            await writer.drain()

    async def send_private_message(
        self,
        message: str,
        user_nickname: str,
        writer: asyncio.StreamWriter,
    ) -> None:
        """
        Отслыкает пользователю приватное сообщение.
        """
        tokens = message[1:].split(' ', 1)
        if len(tokens) == 2:
            recipient, private_message = tokens
            if recipient in self.connected_clients:
                recipient_writer = self.connected_clients[recipient].get('writer')
                recipient_writer.write(f'Private!{user_nickname}: {private_message}\n'.encode())
                writer.write(f'Server!Private message was sent to {recipient}\n'.encode())
                await recipient_writer.drain()
            else:
                writer.write(f'Server!User {recipient} is not connected\n'.encode())
                await writer.drain()
        else:
            writer.write('Server!Don\'t use @ symbol if its not a command!\n'.encode())
            await writer.drain()

    async def send_help_message(self, writer: asyncio.StreamWriter) -> None:
        """
        Отсылает пользователю сообщение справки.
        """
        writer.write(self.help_message.encode())
        await writer.drain()

    async def broadcast_message(self, message: str) -> None:
        """
        Рассылка сообщения всем пользователям чата.
        """
        for _, client_writer in self.connected_clients.items():
            client_writer.get('writer').write(f'Chat!{message}\n'.encode())
            await client_writer.get('writer').drain()

    async def check_and_delete_old_messages(self) -> None:
        """
        Проверка и удаление старых сообщений.
        """
        while True:
            await asyncio.sleep(10)
            current_time = datetime.datetime.now()
            while True:
                for message in self.chat_messages:
                    if (current_time - message[0]).total_seconds() > self.message_ttl:
                        self.chat_messages.remove(message)
                    else:
                        break
                break

    async def check_users_claims(self) -> None:
        """
        Проверяет пользователей с жалобами.
        Раз в минуту проверяет пользователей с жалобами.
        """
        

    async def listen(self) -> None:
        """
        Запуск сервера.
        """
        srv = await asyncio.start_server(self.client_connected, self.host, self.port)
        async with srv:
            logger.info('Server started on %s:%s', self.host, self.port)
            tasks = [
                asyncio.create_task(self.check_and_delete_old_messages()),
                srv.serve_forever(),
            ]
            await asyncio.gather(*tasks)

if __name__ == '__main__':
    server = Server(host='127.0.0.1', port=8000, max_chat_messages=10)
    asyncio.run(server.listen())

# Регистрация клиента (поле юзеров) - сделать ++++++++++++++++++ добавить запись посл.
# посещения, старых удалять

# Комментирование сообщений (добавить индексы)
# Жалобы на пользователей (поле у юзера) после регистрации
# Отложенные приватные сообщения (поле у юзера) после регистрации
# добавить метод удаленичя давно не заходивших юзеров
