from fastapi import FastAPI, Request,  WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaPlayer
import uvicorn
import asyncio
import os
import pty
import threading
import select

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

RTSP_URL = "rtsp://192.168.144.100:8554/quality_h264"

@app.get("/", response_class=HTMLResponse)
async def index():
    with open("static/index.html") as f:
        return f.read()

@app.post("/offer")
async def offer(request: Request):
    params = await request.json()
    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])
    pc = RTCPeerConnection()
    player = MediaPlayer(RTSP_URL, format="rtsp", options={
        "rtsp_transport": "tcp",
        "fflags": "nobuffer",
        "flags": "low_delay",
        "threads": "1",
        "framedrop": "1",
        "max_delay": "500000"
    })
    if player.video:
        pc.addTrack(player.video)
    await pc.setRemoteDescription(offer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)
    return {
        "sdp": pc.localDescription.sdp,
        "type": pc.localDescription.type
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
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


if __name__ == "__main__":
    uvicorn.run(app, host='0.0.0.0', port=8000)
