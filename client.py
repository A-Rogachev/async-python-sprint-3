import asyncio
from server import logger
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
        self.chat_messages: list = []
        self.messages_received: list = []

        self.COLOR_RED: str = '\033[91m'
        self.COLOR_GREEN: str = '\033[92m'
        self.COLOR_YELLOW: str = '\033[93m'
        self.COLOR_BLUE: str = '\033[94m'
        self.COLOR_RESET: str = '\033[0m'
        self.COMMAND_PROMPT: str = self.COLOR_YELLOW + '>>> ' + self.COLOR_RESET

    async def send_message(self, writer):
        """
        Отправка сообщения.
        """
        while True:
            message = await self.get_user_input(self.COMMAND_PROMPT)
            writer.write((message).encode())
            await writer.drain()

            if message == '@exit':
                sys.stdout.write(self.COLOR_RED + f'\r-- Bye! --\n' + self.COLOR_RESET)
                break
        writer.close()

    async def handle_message(self, reader):
        """
        Обработка входящих сообщений.
        """
        sys.stdout.write(
            self.COLOR_RED
            + f'\r-- Welcome to Chat! -> use @help to see instructions.\n'
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
                        + self.COMMAND_PROMPT
                    )
            elif message.startswith('help!'):
                if message.removeprefix("help!").strip() != "":
                    sys.stdout.write(
                        self.COLOR_RED
                        + f'\r-- {message.removeprefix("help!")}\n'
                        + self.COMMAND_PROMPT
                    )
            elif message.startswith('Server!'):
                if message.removeprefix("Server!").strip() != "":
                    sys.stdout.write(
                        self.COLOR_YELLOW
                        + f'\r--SERVER-- {message.removeprefix("Server!")}\n'
                        + self.COMMAND_PROMPT
                    )
            elif message.startswith('History!'):
                if message.removeprefix("History!").strip() != "":
                    sys.stdout.write(
                        self.COLOR_BLUE
                        + f'\r--HISTORY-- {message.removeprefix("History!")}\n'
                        + self.COMMAND_PROMPT
                    )
            else:
                if message.removeprefix("Chat!").strip() != "":
                    sys.stdout.write(
                        self.COLOR_GREEN
                        + f'\r{message.removeprefix("Chat!")}\n'
                        + self.COMMAND_PROMPT
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
        nickname: str = await self.get_user_input(
            "--------------------------------------------------------------\n"
            "Enter your nickname and password '<nickname> <password>'.\n"
            "If you forgot the password, please contact the administrator.\n"
            "If you want to register, enter 'new <nickname> <password>'.\n"
        )

        user_info = nickname.split()
        if len(user_info) != 2 or len(user_info) == 3 and user_info[0] != 'new':
            sys.stdout.write('Wrong command format! Try later!\n')
            writer.close()
            sys.exit(0)

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
