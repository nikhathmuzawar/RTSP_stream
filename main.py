from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaPlayer
import uvicorn

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

RTSP_URL = "rtsp://localhost:8554/mystream"

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

if __name__ == "__main__":
    uvicorn.run(app, host='0.0.0.0', port=8000)
