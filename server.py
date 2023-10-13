import logging
from typing import Any
import asyncio
import datetime

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())


class Server:
    """
    Асинхронный мессенджер (сервер).
    """
    def __init__(
        self,
        host="127.0.0.1",
        port: int = 8000,
        max_chat_messages: int = 20,
        message_ttl: int = 10,
    ):
        """
        Инициализация экземпляра класса Сервер.
        """
        self.host: str = host
        self.port: int = port
        self.max_chat_messages: int = max_chat_messages
        self.message_ttl = message_ttl

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

        user_nickname: str = (await reader.readline()).decode().strip()
        self.connected_clients[user_nickname] = {
            'writer': writer,
            'private_messages': [],
            'claims': [],
        }
        logger.info(
            f'---User {user_nickname} is connected--- '
            f'(ip={address[0]}, port={address[1]})'
        )

        if self.chat_messages:
            for message in self.chat_messages:
                writer.write(f'History!{message[1]}\n'.encode())
                await writer.drain()

        while True:
            data = await reader.read(1024)
            if not data:
                break
            else:
                message: str = data.decode().strip()

                if message == '@help':
                    writer.write(
                        self.help_message.encode()
                    )
                    await writer.drain()
                elif message.startswith('@claim'):
                    # Для обработки жалоб на клиента.
                    ...
                elif message.startswith('@'):
                    tokens = message[1:].split(' ', 1)
                    if len(tokens) == 2:
                        recipient, private_message = tokens
                        if recipient in self.connected_clients:
                            recipient_writer = self.connected_clients[
                                recipient
                            ].get('writer')
                            recipient_writer.write(
                                f'Private!{user_nickname}: '
                                f'{private_message}\n'.encode()
                            )
                            writer.write(
                                f'Server!Private message was '
                                f'sent to {recipient}\n'.encode()
                            )
                            await recipient_writer.drain()
                        else:
                            writer.write(
                                f'Server!User {recipient} '
                                f'is not connected\n'.encode()
                            )
                            await writer.drain()
                    else:
                        logger.info('wrongsy')
                        writer.write('Server!sdfsd'.encode())
                        await writer.drain()
                else:
                    self.chat_messages.append(
                        (
                            message_date := datetime.datetime.now(),
                            message_text := (
                                f'({message_date.strftime("%d.%m.%y %H:%M")})'
                                f' {user_nickname}: {message}'
                            )
                        )
                    )
                    logger.info(f'new message: {message_text}')

                    for _, client_writer in self.connected_clients.items():
                        client_writer.get('writer').write(
                            f'Chat!{message_text}\n'.encode()
                        )
                        await client_writer.get('writer').drain()
                await writer.drain()

        # Отключение клиента из списка подключенных клиентов.
        logger.info(f'---User {user_nickname} disconnected---')
        writer.close()
        del self.connected_clients[user_nickname]

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

    async def listen(self) -> None:
        """
        Запуск сервера.
        """
        srv = await asyncio.start_server(
            self.client_connected, self.host, self.port)
        async with srv:
            logger.info('Server started on %s:%s', self.host, self.port)
            tasks = [
                asyncio.create_task(self.check_and_delete_old_messages()),
                srv.serve_forever(),
            ]
            await asyncio.gather(*tasks)

if __name__ == '__main__':
    server = Server(host='127.0.0.1', port=8000, max_chat_messages=3)
    asyncio.run(server.listen())

# Регистрация клиента (поле юзеров)
# Комментирование сообщений (добавить индексы)
# Жалобы на пользователей (поле у юзера)
# Отложенные приватные сообщения (поле у юзера)
