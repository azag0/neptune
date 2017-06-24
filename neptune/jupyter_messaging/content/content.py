# Any copyright is dedicated to the Public Domain.
# http://creativecommons.org/publicdomain/zero/1.0/
from enum import Enum
from pprint import pformat
from typing import Dict, List, cast


class Status(Enum):
    OK = 'ok'
    ERROR = 'error'


class StreamName(Enum):
    STDOUT = 'stdout'
    STDERR = 'stderr'


class MIME(Enum):
    TEXT_PLAIN = 'text/plain'
    TEXT_HTML = 'text/html'
    TEXT_MARKDOWN = 'text/markdown'
    TEXT_PYTHON = 'text/python'
    IMAGE_PNG = 'image/png'


class ExecutionState(Enum):
    BUSY = 'busy'
    IDLE = 'idle'
    STARTING = 'starting'


class BaseContent:
    def __repr__(self) -> str:
        return pformat(vars(self))


class ExecuteRequestContent(BaseContent):
    def __init__(self, *, code: str, silent: bool, store_history: bool,
                 user_expressions: Dict, allow_stdin: bool,
                 stop_on_error: bool) -> None:
        self.code = code
        self.silent = silent
        self.store_history = store_history
        self.user_expressions = user_expressions
        self.allow_stdin = allow_stdin
        self.stop_on_error = stop_on_error


class BaseExecuteReplyContent(BaseContent):
    pass


class ExecuteReplyOkContent(BaseExecuteReplyContent):
    def __init__(self, *, status: str, execution_count: int,
                 payload: List[Dict] = None, user_expressions: Dict = None) -> None:
        self.status = Status(status)
        self.execution_count = execution_count
        self.payload = payload
        self.user_expressions = user_expressions


class ExecuteReplyErrorContent(BaseExecuteReplyContent):
    def __init__(self, *, status: str, ename: str, evalue: str, traceback: List[str]) -> None:
        self.status = Status(status)
        self.ename = ename
        self.evalue = evalue
        self.traceback = traceback


def parse_execute_reply(content: Dict) -> BaseExecuteReplyContent:
    status = Status(content['status'])
    if status == Status.OK:
        return ExecuteReplyOkContent(**content)
    if status == Status.ERROR:
        return ExecuteReplyErrorContent(**content)
    assert False


class StreamContent(BaseContent):
    def __init__(self, *, name: str, text: str) -> None:
        self.name = StreamName(name)
        self.text = text


class DisplayDataContent(BaseContent):
    def __init__(self, *, data: Dict, metadata: Dict, transient: Dict = None) -> None:
        self.data = {MIME(k): cast(str, v) for k, v in data.items()}
        self.metadata = metadata
        self.transient = transient


class ExecuteInputContent(BaseContent):
    def __init__(self, *, code: str, execution_count: int) -> None:
        self.code = code
        self.execution_count = execution_count


class ExecuteResultContent(BaseContent):
    def __init__(self, *, execution_count: int, data: Dict, metadata: Dict) -> None:
        self.execution_count = execution_count
        self.data = {MIME(k): cast(str, v) for k, v in data.items()}
        self.metadata = metadata


class KernelStatusContent(BaseContent):
    def __init__(self, *, execution_state: str) -> None:
        self.execution_state = ExecutionState(execution_state)
