import asyncio

import os
import sys

def clear_console():
    """
    Очистка окна терминала клиента после введения логина.
    """
    os.system('cls' if os.name == 'nt' else 'clear')


class Client:
    def __init__(self, server_host, server_port):
        """
        Инициализация объекта класса Клиент.
        """
        self.server_host: str = server_host
        self.server_port: int = server_port
        self.client_id: int = 0
        self.chat_messages = []
        self.messages_received = []

        self.COLOR_RED = '\033[91m'
        self.COLOR_GREEN = '\033[92m'
        self.COLOR_YELLOW = '\033[93m'
        self.COLOR_BLUE = '\033[94m'
        self.COLOR_RESET = '\033[0m'

    async def send_message(self, writer):
        """
        Отправка сообщения.
        """
        while True:
            message = await self.get_user_input('>>> ')
            writer.write((message).encode())
            await writer.drain()

            if message == 'exit':
                break

    async def handle_message(self, reader):
        """
        Обработка входящих сообщений.
        """
        input_prompt: str = (
            '-- Welcome to Chat! If you want to send a private message, '
            'type @<username> and space before your message - it will be '
            'send only to this user. '
        )
        sys.stdout.write(
            self.COLOR_RED
            + f'\r{input_prompt}\n'
            + self.COLOR_RESET
        )
        sys.stdout.flush()
        while True:
            data = await reader.readline()
            if not data:
                break
            message = data.decode().strip()
            
            if message.startswith('Private!'):
                if message.removeprefix("Private!").strip() != "":
                    sys.stdout.write(
                        self.COLOR_YELLOW
                        + f'\r--PRIVATE-- {message.removeprefix("Private!")}\n'
                        + self.COLOR_RESET
                        + '>>> ' 
                    )
            elif message.startswith('Server!'):
                if message.removeprefix("Server!").strip() != "":
                    sys.stdout.write(
                        self.COLOR_YELLOW
                        + f'\r--SERVER-- {message.removeprefix("Server!")}\n'
                        + self.COLOR_RESET
                        + '>>> '
                    )
            else:
                if message.removeprefix("Chat!").strip() != "":
                    sys.stdout.write(
                        self.COLOR_BLUE
                        + f'\r--CHAT-- {message.removeprefix("Chat!")}\n'
                        + self.COLOR_RESET
                        + '>>> '
                    )

            self.messages_received.append(message)
            if message == 'exit':
                break

    async def get_user_input(self, prompt):
        """
        Получение ввода пользователя.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, input, prompt)

    async def start(self):
        """
        Запуск клиента, установка связи с сервером.
        """
        reader, writer = await asyncio.open_connection(self.server_host, self.server_port)
        nickname: str = await self.get_user_input("Enter your nickname: ")
        writer.write(nickname.encode() + b'\n')
        await writer.drain()

        clear_console()

        send_task = asyncio.create_task(self.send_message(writer))
        receive_task = asyncio.create_task(self.handle_message(reader))
        await asyncio.gather(send_task, receive_task)

        writer.close()

if __name__ == '__main__':
    client = Client(server_host='127.0.0.1', server_port=8000)
    asyncio.run(client.start())
