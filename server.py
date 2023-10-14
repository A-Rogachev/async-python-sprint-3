import asyncio
import datetime
import json
import logging
from collections import namedtuple
from typing import Any

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())


Message = namedtuple('Message', ['date', 'index', 'text'])


def load_user_database(filename: str) -> list[dict[str, Any]]:
    """
    Возвращает данные из БД пользователей.
    """
    with open(filename, 'r') as file:
        data: list[dict[str, Any]] = json.load(file)
    return data


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
        time_of_ban: int = 3600,
    ):
        """
        Инициализация экземпляра класса Сервер.
        """
        self.message_current_index = 0
        self.host: str = host
        self.port: int = port
        self.max_chat_messages: int = max_chat_messages
        self.message_ttl: int = message_ttl
        self.claims: dict[str, int] = {}
        self.time_of_ban: int = time_of_ban
        self.private_messages: dict[str, Any] = {}
        self.chat_messages: list[Message | None] = []
        self.connected_clients: dict[str, Any] = {}
        self.claimed_users: dict[str, int] = {}
        self.help_message = (
            'help!@<username> <message> -> send private message to user\n'
            'help!@help -> show this message\n'
            'help!@claim<username> -> claim a user\n'
            'help!@comment<message id> <new message> -> comment a message\n'
            'help!@exit -> exit from the messenger\n'
        )
        self.user_database_filename: str = 'users_database.json'

    async def client_connected(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """
        Обработка подключения нового клиента к серверу.
        """
        address: str = writer.get_extra_info('peername')

        user_nickname: str = (await reader.readline()).decode().strip()
        if user_nickname != "":
            self.connected_clients[user_nickname] = {
                'writer': writer,
            }
            logger.info(
                f'---User {user_nickname} is connected--- '
                f'(ip={address[0]}, port={address[1]})'
            )

            if self.chat_messages:
                for message in self.chat_messages[-self.max_chat_messages:]:
                    writer.write(f'History!{message.text}\n'.encode())
                    await writer.drain()
            if self.private_messages.get(user_nickname):
                for message in self.private_messages[user_nickname]:
                    writer.write(f'Private!{message}\n'.encode())
                    await writer.drain()
                del self.private_messages[user_nickname]

            while True:
                data = await reader.read(1024)
                if not data:
                    break
                message: str = data.decode().strip()
                if user_nickname in self.claimed_users:
                    time_left = int(
                        (
                            self.claimed_users[user_nickname]
                            - datetime.datetime.now().timestamp()
                        ) // 60 + 1
                    )
                    writer.write(
                        'Server!You are not allowed to send messages'
                        f' ({time_left} minutes left)\n'.encode()
                    )
                    await writer.drain()
                    continue

                if message.startswith('@'):
                    await self.handle_command(message, user_nickname, writer)
                else:
                    self.chat_messages.append(
                        Message(
                            message_date := datetime.datetime.now(),
                            index := self.message_current_index,
                            text := (
                                f'[{index}] ({message_date.strftime("%d.%m.%y %H:%M:%S")}) '
                                f'{user_nickname}: {message}'
                            )
                        )
                    )
                    self.message_current_index += 1
                    logger.info(f'new message: {text}')
                    await self.broadcast_message(text)
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
        elif message.startswith('@comment'):
            await self.send_comment_message(message, user_nickname, writer)
        elif message.startswith('@claim'):
            await self.add_claim_to_user(message, user_nickname, writer)
        else:
            await self.send_private_message(message, user_nickname, writer)

    async def send_comment_message(
        self,
        message: str,
        user_nickname: str,
        writer: asyncio.StreamWriter,
    ) -> None:
        """
        Комментирование сообщения.
        """
        tokens = message[:].removeprefix('@comment').split(' ', 1)
        if len(tokens) == 2:
            number, comment_text = tokens
            founded_message: bool = False
            for message in self.chat_messages:
                if message.index == int(number):
                    founded_message = True
                    text = message.text
                    self.chat_messages.append(
                        Message(
                            message_date := datetime.datetime.now(),
                            index := self.message_current_index,
                            text := (
                                f'Commenting <{text}>\n'
                                f'[{index}] ({message_date.strftime("%d.%m.%y %H:%M:%S")}) '
                                f'{user_nickname}: {comment_text}'
                            )
                        )
                    )
                    self.message_current_index += 1
                    logger.info(f'new message: {text}')
                    await self.broadcast_message(text)
                await writer.drain()
            if not founded_message:
                writer.write('Server!Message not found or deleted!\n'.encode())
                await writer.drain()
        else:
            writer.write('Server!Don\'t use @ symbol if its not a command!\n'.encode())
            await writer.drain()

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
                self.claims[recipient] = self.claims.get(recipient, 0) + 1
                if self.claims[recipient] == 3:
                    del self.claims[recipient]
                    self.claimed_users[recipient] = (
                        datetime.datetime.now().timestamp()
                        + self.time_of_ban
                    )
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
            private_message: str = (
                f'Private!({datetime.datetime.now().strftime("%d.%m.%y %H:%M:%S")}) '
                f'{user_nickname}: {private_message}\n'
            )
            if recipient in self.connected_clients:
                recipient_writer = self.connected_clients[recipient].get('writer')
                recipient_writer.write(
                    private_message.encode()
                )
                writer.write(f'Server!Private message was sent to {recipient}\n'.encode())
                await recipient_writer.drain()
            else:
                user_exists = False
                for user in load_user_database(self.user_database_filename):
                    if user['username'] == recipient:
                        user_exists = True
                        break
                if not user_exists:
                    writer.write(f'Server!User {recipient} is not registered\n'.encode())
                    await writer.drain()
                else:
                    writer.write(f'Server!User {recipient} is not connected\n'.encode())
                    await writer.drain()
                    self.private_messages.setdefault(recipient, []).append(private_message)
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
        while True:
            await asyncio.sleep(30)
            if self.claimed_users:
                revealed: list[str | None] = []
                for user in self.claimed_users:
                    if (datetime.datetime.now().timestamp() > self.claimed_users[user]):
                        self.claimed_users[user] = None
                        revealed.append(user)
                        logger.info(user)
                if revealed:
                    for revealed_user in revealed:
                        del self.claimed_users[revealed_user]

    async def listen(self) -> None:
        """
        Запуск сервера.
        """
        srv = await asyncio.start_server(self.client_connected, self.host, self.port)
        async with srv:
            logger.info('Server started on %s:%s', self.host, self.port)
            tasks = [
                asyncio.create_task(self.check_and_delete_old_messages()),
                asyncio.create_task(self.check_users_claims()),
                srv.serve_forever(),
            ]
            await asyncio.gather(*tasks)


if __name__ == '__main__':
    server = Server(host='127.0.0.1', port=8000, max_chat_messages=10, time_of_ban=120)
    asyncio.run(server.listen())
