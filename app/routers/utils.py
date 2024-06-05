import telethon
from telethon import TelegramClient, events
from uuid import uuid4
from pathlib import Path
import json


base_dir = Path(__file__).parent.parent / 'sessions'
base_file = 'clients.json'

class TelegramBaseClient:
    def __init__(self, api_id, api_hash, recovery: bool = False,
                session_id: str = None, text: str = None):
        if not recovery:
            self.session_id = str(uuid4())
            self.text = None
            self.recovery_mode = False
        else:
            self.session_id = session_id
            self.text = text
            self.recovery_mode = True
        self.client = TelegramClient(base_dir / self.session_id, api_id, api_hash,
                                     system_version='4.16.30-vxCUSTOM', device_model="")

    async def recovery_connect(self):
        await self.client.connect()
        await self.client.get_me() # См. документацию к TelegramClient.connect
        async def answer(event):
            if self.text is not None and type(event.message.peer_id) == telethon.tl.types.PeerUser:
                await event.reply(self.text)
        self.client.add_event_handler(answer, events.NewMessage)


    async def connect(self, phone, code, password=None):
        await self.client.sign_in(code=code, phone=phone, password=password)
        async def answer(event):
            if self.text is not None and type(event.message.peer_id) == telethon.tl.types.PeerUser:
                await event.reply(self.text)
        self.client.add_event_handler(answer, events.NewMessage)


    async def send_code(self, phone):
        await self.client.connect()
        await self.client.send_code_request(phone)


class TelegramClientsRepository:
    def __init__(self):
        self.clients: dict[str, TelegramBaseClient] = {}
        if (base_dir / base_file).exists():
            with open(base_dir / base_file, 'r') as fp:
                data = json.load(fp)
            for client_data in data['clients']:
                client = TelegramBaseClient(client_data['api_id'], client_data['api_hash'], recovery=True,
                                            session_id=client_data['session_id'], text=client_data['text'])
                self.clients[client_data['session_id']] = client

    async def async_init(self):
        for client in self.clients.values():
            if client.recovery_mode:
                await client.recovery_connect()


    def add_client(self, api_id, api_hash) -> TelegramBaseClient:
        '''return: session ID for new client'''
        client = TelegramBaseClient(api_id, api_hash)
        self.clients[client.session_id] = client
        return client

    def get_client(self, session_id: str) -> TelegramClient | None:
        return self.clients.get(session_id)

    def dump(self):
        clients = []
        for client in self.clients.values():
            clients.append({"api_id": client.client.api_id, "api_hash": client.client.api_hash,
                           'session_id': client.session_id, 'text': client.text})
        with open(base_dir / base_file, 'w+') as fp:
            json.dump({'clients': clients}, fp)
