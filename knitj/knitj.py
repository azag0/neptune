# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import os
from pathlib import Path
import asyncio
import sys
import webbrowser

import ansi2html
from bs4 import BeautifulSoup

from .Kernel import Kernel
from .Source import Source
from .Server import Server
from .Parser import Parser
from .Cell import CodeCell
from . import jupyter_messaging as jupy
from .jupyter_messaging.content import MIME

from typing import Set, Dict, List, Optional, Any  # noqa
from .Cell import BaseCell, Hash  # noqa

_ansi_convert = ansi2html.Ansi2HTMLConverter().convert


class KnitJ:
    def __init__(self, source: os.PathLike, report: os.PathLike = None,
                 browser: webbrowser.BaseBrowser = None, quiet: bool = False) -> None:
        self.source = Path(source)
        self._report_given = bool(report)
        self.report = Path(report) if report else self.source.with_suffix('.html')
        self.quiet = quiet
        self._kernel = Kernel(self._kernel_handler)
        self._server = Server(self._get_html, self._nb_msg_handler, browser=browser)
        if self.source.exists():
            cells = Parser().parse(self.source.read_text())
        else:
            cells = []
        self._cell_order = [cell.hashid for cell in cells]
        self._cells = {cell.hashid: cell for cell in cells}
        if not self.report or not self.report.exists():
            return
        soup = BeautifulSoup(self.report.read_text(), 'html.parser')
        cells_tag = soup.find(id='cells')
        if not cells_tag:
            return
        for cell_tag in cells_tag.find_all('div', class_='code-cell'):
            if cell_tag.attrs['class'][0] in self._cells:
                cell = self._cells[Hash(cell_tag.attrs['class'][0])]
                assert isinstance(cell, CodeCell)
                cell.set_output({
                    MIME.TEXT_HTML: str(cell_tag.find(class_='output'))
                })
                if 'done' in cell_tag.attrs['class']:
                    cell.set_done()
                if 'hide' in cell_tag.attrs['class']:
                    cell.flags.add('hide')

    def _nb_msg_handler(self, msg: Dict) -> None:
        if msg['kind'] == 'reevaluate':
            self.log('Will reevaluate a cell')
            hashid = msg['hashid']
            cell = self._cells[hashid]
            assert isinstance(cell, CodeCell)
            cell.reset()
            self._kernel.execute(hashid, cell.code)
        elif msg['kind'] == 'restart_kernel':
            self.log('Restarting kernel')
            self._kernel.restart()
        elif msg['kind'] == 'ping':
            pass
        else:
            raise ValueError(f'Unkonwn message: {msg["kind"]}')

    def log(self, o: Any) -> None:
        if not self.quiet:
            print(o)

    def _broadcast(self, msg: Dict) -> None:
        self._server.broadcast(msg)
        self._save_report()

    def _kernel_handler(self, msg: jupy.Message, hashid: Optional[Hash]) -> None:
        if not hashid:
            return
        cell = self._cells[hashid]
        assert isinstance(cell, CodeCell)
        if isinstance(msg, jupy.EXECUTE_RESULT):
            self.log('Got an execution result')
            cell.set_output(msg.content.data)
        elif isinstance(msg, jupy.STREAM):
            cell.append_stream(msg.content.text)
        elif isinstance(msg, jupy.DISPLAY_DATA):
            self.log('Got a picture')
            cell.set_output(msg.content.data)
        elif isinstance(msg, jupy.EXECUTE_REPLY):
            if isinstance(msg.content, jupy.content.ERROR):
                self.log('Got an error execution reply')
                html = _ansi_convert(
                    '\n'.join(msg.content.traceback), full=False
                )
                cell.set_output({MIME.TEXT_HTML: f'<pre>{html}</pre>'})
            elif isinstance(msg.content, jupy.content.OK):
                self.log('Got an execution reply')
                cell.set_done()
        elif isinstance(msg, jupy.ERROR):
            self.log('Got an error')
            html = _ansi_convert(
                '\n'.join(msg.content.traceback), full=False
            )
            cell.set_output({MIME.TEXT_HTML: f'<pre>{html}</pre>'})
        elif isinstance(msg, (jupy.STATUS,
                              jupy.EXECUTE_INPUT)):
            return
        else:
            assert False
        self._broadcast(dict(
            kind='cell',
            hashid=cell.hashid,
            html=cell.html,
        ))

    def _source_handler(self, src: str) -> None:
        cells = Parser().parse(src)
        new_cells = []
        updated_cells: List[BaseCell] = []
        for cell in cells:
            if cell.hashid in self._cells:
                old_cell = self._cells[cell.hashid]
                if isinstance(old_cell, CodeCell):
                    assert isinstance(cell, CodeCell)
                    if old_cell.update_flags(cell):
                        updated_cells.append(old_cell)
            else:
                if isinstance(cell, CodeCell):
                    cell._flags.add('evaluating')
                new_cells.append(cell)
        self.log(
            f'File change: {len(new_cells)}/{len(cells)} new cells, '
            f'{len(updated_cells)}/{len(cells)} updated cells'
        )
        self._cell_order = [cell.hashid for cell in cells]
        self._cells = {
            cell.hashid: self._cells.get(cell.hashid, cell) for cell in cells
        }
        self._broadcast(dict(
            kind='document',
            hashids=self._cell_order,
            htmls={cell.hashid: cell.html for cell in new_cells + updated_cells},
        ))
        for cell in new_cells:
            if isinstance(cell, CodeCell):
                self._kernel.execute(cell.hashid, cell.code)

    def _save_report(self) -> None:
        if self.report:
            self.report.write_text(self._server.get_index())

    def _get_html(self) -> str:
        return '\n'.join(self._cells[hashid].html for hashid in self._cell_order)

    async def _printer(self) -> None:
        index = self._server.get_index('__CELLS__')
        front, back = index.split('__CELLS__')
        await self._kernel.wait_for_start()
        for hashid in self._cell_order:
            cell = self._cells[hashid]
            if isinstance(cell, CodeCell):
                self._kernel.execute(cell.hashid, cell.code)
        f = self.report.open('w') if self._report_given else sys.stdout
        f.write(front)
        try:
            for hashid in self._cell_order:
                cell = self._cells[hashid]
                if isinstance(cell, CodeCell):
                    await cell.wait_for()
                f.write(cell.html)
        except:
            raise
        else:
            f.write(back)
        finally:
            if self.report:
                f.close()
        raise AllProcessed

    async def run(self) -> None:
        await asyncio.gather(
            self._kernel.run(),
            self._server.run(),
            Source(self._source_handler, self.source).run(),
        )

    async def static(self) -> None:
        try:
            await asyncio.gather(self._kernel.run(), self._printer())
        except AllProcessed:
            self._kernel._client.shutdown()


class AllProcessed(Exception):
    pass