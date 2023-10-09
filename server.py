import logging
import sys
import asyncio
from asyncio.streams import StreamReader, StreamWriter
import datetime


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler(stream=sys.stdout))


class Server:
    def __init__(self, host="127.0.0.1", port=8000, max_messages=20):
        """
        Инициализация объекта класса Сервер.
        Сервис обрабатывает поступающие запросы от клиентов.
        """
        self.host = host
        self.port = port
        self.messages = []
        self.max_messages = max_messages
        self.clients = []

    async def client_connected(self, reader: StreamReader, writer: StreamWriter):
        """
        Подключение клиентов к серверу.
        """
        address = writer.get_extra_info('peername')
        logger.info('Start serving %s', address)
        writer.write('Welcome to the CHAT!\n'.encode())

        if self.messages:
            for message in self.messages[-self.max_messages:]:
                writer.write(message)

        self.clients.append(writer)

        while True:
            data = await reader.read(1024)
            self.messages.append(data)

            if not data:
                break
            else: 
                logger.info('New message from %s: %s', address, data.decode())

                for client in self.clients:
                    if client != writer:
                        client.write(data)
                        await client.drain()
            await writer.drain()

        logger.info('Stop serving %s', address)
        writer.close()
        self.clients.remove(writer)

    async def listen(self):
        """
        Запуск сервера.
        """
        srv = await asyncio.start_server(
            self.client_connected, self.host, self.port)

        async with srv:
            await srv.serve_forever()


if __name__ == '__main__':
    server = Server(host='127.0.0.1', port=8000, max_messages=3)
    asyncio.run(server.listen())
