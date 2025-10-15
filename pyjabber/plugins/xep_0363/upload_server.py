import os
import tempfile
from enum import IntEnum
from typing import Union

import aiofiles
from aiohttp import web
from nanoid import generate

TEMP_DIR = tempfile.mkdtemp(prefix="pyjabber_xep0363_")

class SlotIndex(IntEnum):
    TMPDIR = 0,
    FILENAME = 1,
    CONTENT_TYPE = 2,
    CONTENT_LENGTH = 3,
    IS_UPLOADED_YET = 4

class UploadHttpServer:
    def __init__(self):
        self._slots: dict[str,  # Slot ID
        tuple[
            str,    # Temporal directory to store the file for the slot
            str,    # Filename
            str,    # Content-type (optional)
            int,    # Content-length (optional)
            bool    # Is-uploaded-yet bool
        ]] = {}

        self._root = '/upload'
        self._app = web.Application()
        self._app.router.add_put('/{slot_id}/{file_name}', self.handle_upload)
        self._app.router.add_get('/{slot_id}/{file_name}', self.handle_download)

    @property
    def app(self):
        return self._app

    @property
    def root(self):
        return self._root

    def get_aiohttp_webapp(self) -> tuple[str, web.Application]:
        return self._root, self._app

    def slot_request(self, filename: str, content_type: str = None, content_length: int = None) -> Union[str, None]:
        slot_id = generate(size=8)
        tmpdir = os.path.join(TEMP_DIR, slot_id)

        os.mkdir(tmpdir)
        self._slots[slot_id] = (tmpdir, filename, content_type, content_length, False)

        return slot_id

    async def handle_upload(self, request: web.Request):
        slot_id = request.match_info['slot_id']
        file_name = request.match_info['file_name']
        content_length = request.content_length
        content_type = request.content_type

        if slot_id not in self._slots.keys():
            return web.Response(text=f'{slot_id} not exists. Please first request an available slot via XMPP', status=404)
        if self._slots[slot_id][SlotIndex.IS_UPLOADED_YET.value]:
            return web.Response(text=f'{slot_id} is already filled with a previous upload. Please request a new slot', status=400)
        if file_name != self._slots[slot_id][SlotIndex.FILENAME]:
            return web.Response(text=f'{slot_id} exists, but it is not bound with the file_name: f{file_name}', status=404)

        if (content_length
            and self._slots[slot_id][SlotIndex.CONTENT_LENGTH]
            and content_length != self._slots[slot_id][SlotIndex.CONTENT_LENGTH]
        ):
            return web.Response(text=f'Invalid content-length', status=400)
        if (content_type
            and self._slots[slot_id][SlotIndex.CONTENT_TYPE]
            and content_type != self._slots[slot_id][SlotIndex.CONTENT_TYPE]
        ):
            return web.Response(text=f'Invalid file type', status=400)

        save_path = os.path.join(TEMP_DIR, slot_id, file_name)

        expected_size = self._slots[slot_id][SlotIndex.CONTENT_LENGTH]
        total_size = 0
        invalid = False
        async with aiofiles.open(save_path, 'wb') as f:
            async for chunk in request.content.iter_chunked(8192):
                total_size += len(chunk)
                if expected_size and total_size > expected_size:
                    invalid = True
                    break
                await f.write(chunk)

        if invalid or total_size != expected_size:
            os.remove(save_path)
            return web.Response(status=400, text="Invalid file size")

        self._slots[slot_id] = (*self._slots[slot_id][:-1], True)   # type: ignore

        return web.Response(text=f'{file_name} successfully uploaded in {slot_id} slot')

    async def handle_download(self, request: web.Request):
        slot_id = request.match_info['slot_id']
        file_name_req = request.match_info['file_name']

        if slot_id not in self._slots.keys():
            return web.Response(text=f"Slot {slot_id} not Found", status=404)
        if self._slots[slot_id][SlotIndex.IS_UPLOADED_YET] is False:
            return web.Response(text=f"Slot {slot_id} exists, but no file were found", status=204)
        if file_name_req != self._slots[slot_id][SlotIndex.FILENAME]:
            return web.Response(text=f'{slot_id} exists, but it is not bound with the file_name: f{file_name_req}', status=404)

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
