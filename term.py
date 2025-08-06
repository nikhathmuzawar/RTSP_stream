import asyncio
import os
import pty
import select
import subprocess
import threading
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

app = FastAPI()

@app.get("/")
def get_index():
    return FileResponse("term.html")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    print("WebSocket request headers:", websocket.headers)
    await websocket.accept()
    loop = asyncio.get_event_loop()
    pid, master_fd = pty.fork()
    if pid == 0:
        os.execvp("bash", ["bash"])
    else:
        alive = True

        # For writing to PTY (input from browser)
        async def read_from_websocket():
            try:
                while alive:
                    data = await websocket.receive_text()
                    # xterm.js sends resize as JSON
                    if data.startswith("!resize:"):
                        _, cols, rows = data.split(":")
                        # Set window size; ignored if not supported
                        import fcntl, termios, struct
                        sz = struct.pack("HHHH", int(rows), int(cols), 0, 0)
                        fcntl.ioctl(master_fd, termios.TIOCSWINSZ, sz)
                    else:
                        os.write(master_fd, data.encode())
            except Exception:
                pass

        # For streaming PTY output (stdout/stderr) back to browser
        def write_to_websocket():
            try:
                while alive:
                    reads, _, _ = select.select([master_fd], [], [], 0.05)
                    if master_fd in reads:
                        out = os.read(master_fd, 1024)
                        if out:
                            # WebSocket expects str
                            asyncio.run_coroutine_threadsafe(
                                websocket.send_text(out.decode(errors="replace")),
                                loop
                            )
            except Exception:
                pass

        # Start threads for IO
        ws_thread = threading.Thread(target=write_to_websocket, daemon=True)
        ws_thread.start()
        websocket_reader_task = asyncio.create_task(read_from_websocket())

        try:
            await websocket_reader_task
        except WebSocketDisconnect:
            pass
        finally:
            alive = False
            try:
                os.close(master_fd)
            except Exception:
                pass
