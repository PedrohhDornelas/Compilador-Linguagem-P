from dataclasses import dataclass


@dataclass
class ErroSintatico:
    linha: int
    esperado: str
    encontrado: str
    mensagem: str
