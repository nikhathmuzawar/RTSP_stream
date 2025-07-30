# RTSP STREAM  
Stream video from a rtsp url to a webpage using WebRTC.  
## TO USE  
Replace the following line with the rtsp URL in main.py.  
``RTSP_URL = "rtsp://rtspurl"``   
Run main.py:  
``python3 main.py``  

## TO STREAM WEBCAM AS RTSP  
Install the approprite mediamtx server from https://github.com/bluenviron/mediamtx/releases  
Run the following commands:  
``cd mediamtx_v1.13.1_linux_amd64``  
``./mediamtx``  
``ffmpeg -f v4l2 -i /dev/video0 -vf "scale=640:480" -c:v libx264 -preset veryfast -tune zerolatency -f rtsp rtsp://localhost:8554/mystream``
