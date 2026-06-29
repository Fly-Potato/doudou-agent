import os


class Settings:
    host: str
    port: int

    def __init__(self) -> None:
        self.host = os.getenv('HOST', '0.0.0.0')
        port_str = os.getenv('PORT', '8000')
        self.port = int(port_str)


settings = Settings()
