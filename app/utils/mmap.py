

import asyncio
import contextlib
import mmap
import os
import time
import traceback

header_length = 32
footer_length = 20

mmap_directory = "/dev/shm"
pathname_img = f"{mmap_directory}/cam.shm"
pathname_state = f"{mmap_directory}/state.shm"

def mmap_write(mmap_object: mmap.mmap, max_length:int, bytes:bytes):
    while True:
        try:
            body_length = len(bytes)
            if body_length < max_length:
                twelve_char_length = str(float(body_length)).ljust(12, '0').encode('utf-8')
                mmap_object.seek(0)
                mmap_object.write(twelve_char_length+bytes)
                return
            else:
                print(traceback.format_exc())
                print('data too big for mmap2', max_length, "<",body_length)
        except Exception as e:
            print(traceback.format_exc())
            print(e)


async def mmap_read(mmap_object: mmap.mmap):
    try:
        while True:
            mmap_object.seek(0)
            twelve_char_length_raw=mmap_object.read(12)
            
            if twelve_char_length_raw == bytearray(12):
                await asyncio.sleep(0.0001)
                print(111, mmap_object)
                continue
            
            twelve_char_length = int(float(twelve_char_length_raw))
        
            body=mmap_object.read(twelve_char_length)
            return body
    except Exception as e:
        print(traceback.format_exc())
        print(e)
    return bytearray()


@contextlib.contextmanager
def mmap_context(path, max_length:int):
    if not os.path.isfile(path) or os.stat(path).st_size < max_length:
        print("not os.path.isfile(path)",not os.path.isfile(path))
        print("os.stat(path).st_size", os.stat(path).st_size, max_length)
        with open(path, "w+b") as f:
            f.seek(max_length)
            f.write(b"\0")
            print('Initiating mmap shm', path, max_length)

    with open(path, "r+b") as f:
        yield mmap.mmap(f.fileno(), max_length)