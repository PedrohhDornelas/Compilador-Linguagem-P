from dataclasses import dataclass

@dataclass
class ErroLexico:
    linha: int
    lexema: str
    mensagem: str

@dataclass
class Token:
    lexema: str
    tipo: str
    linha: int

PALAVRAS_RESERVADAS = {
    "char": "CHAR",
    "else": "ELSE",
    "float": "FLOAT",
    "fn": "FUNCTION",
    "if": "IF",
    "int": "INT",
    "let": "LET",
    "main": "MAIN",
    "println": "PRINTLN",
    "return": "RETURN",
    "while": "WHILE",
}