import json

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from config import settings

app = FastAPI(title='agent-server')


@app.get('/health')
async def health():
    return {'status': 'ok'}


@app.websocket('/chat')
async def chat(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            data = await ws.receive_text()
            msg = json.loads(data)
            content = msg.get('content', '')
            await ws.send_text(
                json.dumps(
                    {
                        'type': 'message',
                        'content': f'Echo: {content}',
                    }
                )
            )
    except WebSocketDisconnect:
        pass


def main() -> None:
    import uvicorn

    uvicorn.run(
        'main:app',
        host=settings.host,
        port=settings.port,
        reload=True,
    )


if __name__ == '__main__':
    main()
