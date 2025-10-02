from pydantic import BaseModel


class Host(BaseModel):
    hostname: str
    description: str = ""

    def __str__(self) -> str:
        return self.hostname
