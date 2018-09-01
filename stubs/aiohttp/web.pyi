from typing import Awaitable, Callable, AsyncIterable, List, Any

from . import WSMessage, WSCloseCode


class HTTPNotFound(Exception):
    ...


class BaseRequest:
    path: str


class Request(BaseRequest):
    app: 'Application'


class Response:
    def __init__(self, *, text: str = None, content_type: str = None) -> None: ...


Handler = Callable[[Request], Awaitable[Response]]


class Server:
    def __init__(self, handler: Handler) -> None: ...


class Router:
    def add_static(self, prefix: str, path: str, append_version: bool = False
                   ) -> None: ...
    def add_get(self, path: str, handler: Handler) -> None: ...


class Application:
    router: Router
    on_shutdown: List[Callable[['Application'], Awaitable[None]]]
    def __init__(self) -> None: ...
    def __getitem__(self, key: str) -> Any: ...
    def __setitem__(self, key: str, value: Any) -> None: ...


class AppRunner:
    def __init__(self, app: Application) -> None: ...
    async def setup(self) -> None: ...
    async def cleanup(self) -> None: ...


class WebSocketResponse(Response, AsyncIterable[WSMessage]):
    def __init__(self, autoclose: bool = True) -> None: ...
    def __aiter__(self) -> 'WebSocketResponse': ...
    async def __anext__(self) -> WSMessage: ...
    async def prepare(self, request: BaseRequest) -> None: ...
    async def send_str(self, data: str) -> None: ...
    async def close(self, code: WSCloseCode, message: str) -> None: ...


class TCPSite:
    def __init__(self, runner: AppRunner, address: str, port: int) -> None: ...
    async def start(self) -> None: ...
