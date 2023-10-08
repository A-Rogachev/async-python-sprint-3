# import asyncio
# from typing import Any


# class Server:
#     def __init__(self, host="127.0.0.1", port=8000):
#         """
#         Инициализация экземпляра класса Сервер.
#         Класс отвечает за обработку запросов от клиентов.
#         """
#         self.chat_messages: list[Any] = []
#         self.connected_clients: list[Any]
#         self.unseen_messages: dict[int, int] = {}
#         self.last_seen_message_index: dict[int, int] = {}
#         self.max_chat_messages: int = 100
#         self.host: str = host
#         self.port: int = port


#     def connect_client(client_id: int):
#         """
#         Добавляет нового клиента в список подключенных клиентов
#         и отправляет последние N сообщений из общего чата.
#         """

#     def disconnect_client(client_id: int):
#         """
#         Удаляет клиента из списка подключенных клиентов.
#         """

#     def send_message(client_id: int, message: str):
#         """
#         Отправляет сообщение от клиента в общий чат.
#         """

#     def send_private_message(sender_id: int, recipient_id: int, message: str):
#         """
#         Отправляет приватное сообщение от отправителя к получателю.
#         """

#     def get_unseen_messages(client_id: int):
#         """
#         Возвращает непрочитанные сообщения для клиента.
#         """

#     def mark_messages_as_seen(client_id: int, message_index: int):
#         """
#         Помечает сообщения от клиента как прочитанные до указанного индекса.
#         """

#     def listen(self):
#         """
#         Запуск сервера на указанном хосте и порту.
#         """


# import asyncio

# class Server:
#     def __init__(self, host='127.0.0.1', port=8000, max_messages=20):
#         self.host = host
#         self.port = port
#         self.max_messages = max_messages
#         self.clients = []
#         self.messages = []

#     async def handle_client(self, reader, writer):
#         # Add new client to the list
#         self.clients.append(writer)

#         # Send last N messages to the client
#         for message in self.messages[-self.max_messages:]:
#             writer.write(message.encode())
#             await writer.drain()

#         while True:
#             data = await reader.read(100)
#             message = data.decode().strip()

#             if message == 'quit':
#                 # Remove client from the list
#                 self.clients.remove(writer)
#                 writer.close()
#                 break
#             else:
#                 # Add message to the list
#                 self.messages.append(message)

#                 # Broadcast message to all clients
#                 for client in self.clients:
#                     client.write(message.encode())
#                     await client.drain()

#     async def start(self):
#         server = await asyncio.start_server(
#             self.handle_client, self.host, self.port)

#         # Get the server address
#         host, port = server.sockets[0].getsockname()
#         print(f'Server started on {host}:{port}')

#         async with server:
#             await server.serve_forever()

# async def main():
#     server = Server()
#     await server.start()

# asyncio.run(main())






import logging
import sys
import asyncio
from asyncio.streams import StreamReader, StreamWriter
from typing import Any


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler(stream=sys.stdout))


class Server:
    def __init__(self, host="127.0.0.1", port=8000, max_chat_messages=20):
        """
        Инициализация экземпляра класса Сервер.
        Класс отвечает за обработку запросов от клиентов.
        """
        self.chat_messages = []
        self.connected_clients: list[Any] = {}
        self.unseen_messages: dict[int, int] = {}
        self.last_seen_message_index: dict[int, int] = {}
        self.max_chat_messages = max_chat_messages
        self.host: str = host
        self.port: int = port

    async def send_chat_history(self, writer):
        for message in self.chat_messages[-self.max_chat_messages:]:
            writer.write(message.encode() + b'\n')
            await writer.drain()

    async def client_connected(self, reader: StreamReader, writer: StreamWriter):
        address = writer.get_extra_info('peername')

        nickname = (await reader.readline()).decode().strip()
        self.connected_clients[writer] = nickname
        logger.info(f'---User {nickname} is connected---')

        await self.send_chat_history(writer)

        for message in self.chat_messages[-self.max_chat_messages:]:
            writer.write(message.encode() + b'\n')
            await writer.drain()

        while True:
            data = await reader.read(1024)
            if not data:
                break
            message = data.decode().strip()
            logger.info(f'{nickname}: {message}')

            self.chat_messages.append(f'{nickname}: {message}')
            
            for client_writer, client_nickname in self.connected_clients.items():
                if client_writer != writer:
                    client_writer.write(f"{nickname}: {message}".encode() + b'\n')
                    await client_writer.drain()

        logger.info(f'---User {nickname} disconnected---')
        writer.close()
        del self.connected_clients[writer]


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


# необходимо сохранять историю сообщений, непрочитанные сообщения отсылать пользователю
# после того как пользователь отослал сообщение, у него должно появиться оно в терминале
# история сообщений 
# приватные сообщения
# возможность пожаловаться на пользователя 2б
# возможность создавать сообщения с ранее указанным временем отправки