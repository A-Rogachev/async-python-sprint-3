import asyncio

import os
import sys

def clear_console():
    os.system('cls' if os.name == 'nt' else 'clear')

class Client:
    def __init__(self, server_host="127.0.0.1", server_port=8000):
        """
        Инициализация объекта класса Клиент.
        """
        self.server_host: str = server_host
        self.server_port: int = server_port
        self.client_id: int = 0
        self.chat_messages = []

    async def send_message(self, writer):
        while True:
            message = input('Enter a message (or "quit" to exit): ')
            writer.write(message.encode() + b'\n')
            await writer.drain()

            if message == 'quit':
                break

    async def handle_message(self, reader):
        while True:
            data = await reader.readline()
            if not data:
                break
            message = data.decode().strip()
            print(f'Received message: {message}')
            self.chat_messages.append(message)

            sys.stdout.write("\033c")

            for message in self.chat_messages[-3:]:
                print(message)
            print("Enter a message (or 'quit' to exit): ", end="", flush=True)

            user_input = await self.get_user_input()
            if user_input.lower() == "quit":
                break
            self.send_message(user_input)

    async def start(self):
        reader, writer = await asyncio.open_connection(self.server_host, self.server_port)

        nickname = input("Enter your nickname: ")
        writer.write(nickname.encode() + b'\n')
        await writer.drain()

        send_task = asyncio.create_task(self.send_message(writer))
        receive_task = asyncio.create_task(self.handle_message(reader))

        await asyncio.gather(send_task, receive_task)

        writer.close()


async def main():
    client = Client()
    await client.start()

if __name__ == '__main__':
    asyncio.run(main())




#     def connect(self):
#         """
#         Подключает клиента к серверу.
#         """

#     def disconnect(self):
#         """
#         Отключает клиента от сервера.
#         """

#     def send_private_message(self, sender_id, recipient_id, message):
#         """
#         Отправляет приватное сообщение другому клиенту.
#         """

#     def get_unseen_messages(self):
#         """
#         Возвращает непрочитанные сообщения для клиента.
#         """

#     def mark_messages_as_seen(self, message_index):
#         """
#         Помечает сообщения от клиента как прочитанные до указанного индекса.
#         """

