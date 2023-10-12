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
    def __init__(self, host="127.0.0.1", port: int = 8000, max_chat_messages: int = 20):
        """
        Инициализация экземпляра класса Сервер.
        """
        self.host: str = host
        self.port: int = port
        self.max_chat_messages: int = max_chat_messages

        self.chat_messages = []
        self.connected_clients: dict[str, Any] = {}

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
        # self.connected_clients[user_nickname] = {
        #     'writer': writer,
        #     'private_messages': [],
        #     'claims': [],
        # }
        self.connected_clients[user_nickname] = writer
        logger.info(
            f'---User {user_nickname} is connected--- '
            f'(ip={address[0]}, port={address[1]})'
        )

        if self.chat_messages:
            for message in self.chat_messages:
                writer.write(f'Chat!{user_nickname}: {message}\n'.encode())
                await writer.drain()

        while True:
            data = await reader.read(1024)
            if not data:
                break
            else:
                message = data.decode().strip()
                
                if message.startswith('@'):
                    tokens = message[1:].split(' ', 1)
                    if len(tokens) == 2:
                        recipient, private_message = tokens
                        if recipient in self.connected_clients:
                            recipient_writer = self.connected_clients[
                                recipient
                            ]
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
                elif message.startswith('!!'):
                    # Для обработки жалоб на клиента.
                    ...
                else:
                    logger.info(f'{user_nickname}: {message}')
                    self.chat_messages.append(
                        (
                            message_date := datetime.datetime.now(),
                            f'{message_date.strftime("%d.%m.%y %H:%M")} {user_nickname}: {message}',
                        )
                    )

                    for _, client_writer in self.connected_clients.items():
                        client_writer.write(
                            f'Chat!{user_nickname}: {message}\n'.encode()
                        )
                        await client_writer.drain()
            # await writer.drain()

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
            self.chat_messages = [
                (message_time, message)
                for message_time, message in self.chat_messages
                if (current_time - message_time).total_seconds() < 10
            ]

    async def listen(self) -> None:
        """
        Запуск сервера.
        """
        srv = await asyncio.start_server(
            self.client_connected, self.host, self.port)
        async with srv:
            logger.info('Server started on %s:%s', self.host, self.port)
            await srv.serve_forever()

if __name__ == '__main__':
    server = Server(host='127.0.0.1', port=8000, max_chat_messages=3)
    asyncio.run(server.listen())
