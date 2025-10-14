import os
import tempfile

import aiofiles
from aiohttp import web
from nanoid import generate

TEMP_DIR = tempfile.mkdtemp(prefix="xep0363_")

class UploadHttpServer:
    def __init__(self):
        # Slots are stored in dicts, with key = storeID, and value
        # as tuples in the format:
        #   Index 0: Stores the path to the temporal directory of the file
        #   Index 1: Stores a boolean representing if the reserved slot is filled with
        #   the corresponding file
        self._slots: dict[str, tuple[str, bool]] = {}

        self._root = '/upload'
        self._app = web.Application()
        self._app.router.add_post('/{slot_id}', self.handle_upload)
        self._app.router.add_get('/{slot_id}', self.handle_download)

    @property
    def app(self):
        return self._app

    @property
    def root(self):
        return self._root

    def get_aiohttp_webapp(self) -> tuple[str, web.Application]:
        return self._root, self._app

    async def slot_request(self):
        slot_id = generate(size=8)
        if slot_id in self._slots.keys():
            slot_id = generate(size=8)

        tmpdir = os.path.join(TEMP_DIR, slot_id)
        self._slots[slot_id] = tmpdir

        return slot_id

    async def handle_upload(self, request: web.Request):
        slot_id = request.match_info['slot_id']

        reader = await request.multipart()
        field = await reader.next()

        if field.name != 'file':
            return web.Response(text='"file" field required', status=400)

        file_name = field.filename

        if slot_id not in self._slots.keys():
            return web.Response(text=f'{slot_id} not exists. Please first request an available slot via XMPP', status=404)

        if self._slots[slot_id][1]:
            return web.Response(text='\"slot_id\" is already filled with a previous upload. Please request a new slot', status=400)

        save_path = os.path.join(TEMP_DIR, slot_id, file_name)

        async with aiofiles.open(save_path, 'wb') as f:
            while True:
                chunk = await field.read_chunk()
                if not chunk:
                    break
                await f.write(chunk)

        self._slots[slot_id] = (self._slots[slot_id][0], True)

        return web.Response(text=f'{file_name} successfully uploaded in {slot_id} slot')

    async def handle_download(self, request: web.Request):
        slot_id = request.match_info['slot_id']

        if slot_id not in self._slots.keys():
            return web.Response(text=f"Slot {slot_id} not Found", status=404)
        if self._slots[slot_id][1] is False:
            return web.Response(text=f"Slot {slot_id} exists, but no file were found", status=204)

        file_dir = os.path.join(TEMP_DIR, slot_id)
        files = os.listdir(file_dir)
        file_name = files[0]
        file_path = os.path.join(file_dir, file_name)

        return web.FileResponse(
            path=file_path,
            headers={
                "Content-Disposition": f'attachment; filename="{file_name}"'
            }
        )
