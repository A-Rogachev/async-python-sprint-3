from collections import namedtuple
from typing import Any

from pydantic_settings import BaseSettings

Message = namedtuple('Message', ['date', 'index', 'text'])


class AppSettings(BaseSettings):
    """
    Настройки приложения сервера.
    """
    message_current_index: int = 0
    host: str = '127.0.0.1'
    port: int = '8000'
    max_chat_messages: int = 100
    message_ttl: int = 10
    claims: dict[str, int] = {}
    time_of_ban: int = 120
    private_messages: dict[str, Any] = {}
    chat_messages: list[Message | None] = []
    connected_clients: dict[str, Any] = {}
    claimed_users: dict[str, int] = {}
    help_message: str = (
        'help!@<username> <message> -> send private message to user\n'
        'help!@help -> show this message\n'
        'help!@claim<username> -> claim a user\n'
        'help!@comment<message id> <new message> -> comment a message\n'
        'help!@exit -> exit from the messenger\n'
    )
    user_database_filename: str = 'users_database.json'
