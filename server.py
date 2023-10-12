import logging
from typing import Any
import asyncio

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

    async def client_connected(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """
        Обработка подключения нового клиента к серверу.
        """
        address: str = writer.get_extra_info('peername')

        user_nickname: str = (await reader.readline()).decode().strip()
        self.connected_clients[user_nickname] = writer
        logger.info(f'---User {user_nickname} is connected--- (ip={address[0]}, port={address[1]})')

        while True:
            data = await reader.read(1024)
            if not data:
                break
            else:
                message = data.decode().strip()
                
                if message.startswith('@'):
                    # Для обработки личных сообщений.
                    tokens = message[1:].split(' ', 1)
                    if len(tokens) == 2:
                        recipient, private_message = tokens
                        if recipient in self.connected_clients:
                            recipient_writer = self.connected_clients[recipient]
                            recipient_writer.write(f'Private message from {user_nickname}: {private_message}\n'.encode())
                            await recipient_writer.drain()
                        else:
                            writer.write(f'Server!User {recipient} is not connected\n'.encode())
                            await writer.drain()
                elif message.startswith('!!!'):
                    # Для обработки жалоб на клиента.
                    ...
                else:
                    logger.info(f'{user_nickname}: {message}')
                    self.chat_messages.append(f'{user_nickname}: {message}')


                    for client_nickname, client_writer in self.connected_clients.items():
                        client_writer.write(f'Chat!{user_nickname}: {message}\n'.encode())
                        await client_writer.drain()
            # await writer.drain()

        # Отключение клиента из списка подключенных клиентов.
        logger.info(f'---User {user_nickname} disconnected---')
        writer.close()
        del self.connected_clients[user_nickname]

    async def listen(self):
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