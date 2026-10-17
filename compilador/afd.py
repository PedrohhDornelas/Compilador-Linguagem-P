INICIAL = "q0"
ACEITACAO = { # none eh lexema ignorado // id cobre palavras reservadas
    "arrow": "ARROW",
    "assign": "ASSIGN",
    "chr_ok": "CHAR_LITERAL",
    "colon": "COLON",
    "comma": "COMMA",
    "div": "DIV",
    "eq": "EQ",
    "float": "FLOAT_CONST",
    "ge": "GE",
    "gt": "GT",
    "id": "ID",
    "int": "INT_CONST",
    "lb": "LBRACE",
    "le": "LE",
    "lp": "LBRACKET",
    "lt": "LT",
    "minus": "MINUS",
    "mult": "MULT",
    "ne": "NE",
    "plus": "PLUS",
    "rb": "RBRACE",
    "rp": "RBRACKET",
    "semi": "SEMICOLON",
    "str_ok": "FMT_STRING",
    "ws": None,
}

_SIMBOLOS = {
    "!": "bang", ":": "colon", ",": "comma", ".": "dot",
    '"': "dquote", "=": "equals", ">": "gt", "{": "lbrace",
    "(": "lparen", "<": "lt", "-": "minus", "\n": "newline",
    "+": "plus", "}": "rbrace", ")": "rparen", ";": "semi",
    "/": "slash", " ": "space", "\t": "space", "\r": "space",
    "'": "squote", "*": "star", "_": "underscore",
}

def classificar(c): # alfabeto, none eh EOF
    if c is None:
        return "eof"
    if c in _SIMBOLOS:
        return _SIMBOLOS[c]
    if "a" <= c <= "z" or "A" <= c <= "Z":
        return "letter"
    if "0" <= c <= "9":
        return "digit"
    return "other"

TRANSICOES = {
    # estado inicial
    ("q0", "bang"): "bang",
    ("q0", "colon"): "colon",
    ("q0", "comma"): "comma",
    ("q0", "digit"): "int",
    ("q0", "dquote"): "str0",
    ("q0", "equals"): "assign",
    ("q0", "gt"): "gt",
    ("q0", "lbrace"): "lb",
    ("q0", "letter"): "id",
    ("q0", "lparen"): "lp",
    ("q0", "lt"): "lt",
    ("q0", "minus"): "minus",
    ("q0", "newline"): "ws",
    ("q0", "plus"): "plus",
    ("q0", "rbrace"): "rb",
    ("q0", "rparen"): "rp",
    ("q0", "semi"): "semi",
    ("q0", "slash"): "div",
    ("q0", "space"): "ws",
    ("q0", "squote"): "chr1",
    ("q0", "star"): "mult",
    # espaco em branco
    ("ws", "newline"): "ws",
    ("ws", "space"): "ws",
    # identificador: [a-zA-Z]([a-zA-Z0-9_])*
    ("id", "digit"): "id",
    ("id", "letter"): "id",
    ("id", "underscore"): "id",
    # inteiro e float: [0-9]+ e [0-9]+.[0-9]+
    ("float", "digit"): "float",
    ("int", "digit"): "int",
    ("int", "dot"): "int_dot",
    ("int_dot", "digit"): "float",
    # qualquer caractere
    ("chr1", "squote"): None, # '' vazio eh erro
    ("chr2", "squote"): "chr_ok",
    # string de formatação: E+
    ("str0", "dquote"): None, # "" vazia eh erro
    ("str1", "dquote"): "str_ok",
    # operadores de dois caracteres
    ("assign", "equals"): "eq",
    ("bang", "equals"): "ne",
    ("gt", "equals"): "ge",
    ("lt", "equals"): "le",
    ("minus", "gt"): "arrow",
}

PADRAO = { # transicao outros caracteres
    "chr1": "chr2",
    "str0": "str1",
    "str1": "str1",
}

def transicao(estado, classe):
    if (estado, classe) in TRANSICOES:
        return TRANSICOES[(estado, classe)] # retorna prox estado
    if classe in ("newline", "eof"):
        return None
    return PADRAO.get(estado)