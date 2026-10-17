from afd import INICIAL, ACEITACAO, classificar, transicao
from tokens import Token, ErroLexico, PALAVRAS_RESERVADAS
 
 
def proximo_lexema(codigo, inicio):
    n = len(codigo)
    estado = INICIAL
    j = inicio
    ultimo = None  # (estado_de_aceitacao, posicao_final) mais recente
 
    while True:
        c = codigo[j] if j < n else None          # None = fim do arquivo
        prox = transicao(estado, classificar(c))
        if prox is None:                          # sem transição: para
            break
        estado = prox
        j += 1
        if estado in ACEITACAO:                   # lembra o último ponto válido
            ultimo = (estado, j)
 
    if ultimo is not None:
        return ultimo
    return None, j

def recuperar_erro(codigo, inicio, fim_afd):
    c = codigo[inicio]
    if c in ("'", '"'):
        fim_linha = codigo.find("\n", inicio)
        if fim_linha == -1:
            fim_linha = len(codigo)
        achou = codigo.find(c, inicio + 1, fim_linha)
        return achou + 1 if achou != -1 else fim_linha
    return max(fim_afd, inicio + 1)               # garante progresso
 
 
def mensagem_erro(lexema):
    c = lexema[0]
    if c == '"':
        if lexema == '""':
            return "string de formatação vazia"
        return "string de formatação não fechada"
    if c == "'":
        if lexema == "''":
            return "literal de caractere vazio"
        if lexema.endswith("'") and len(lexema) > 2:
            return "literal de caractere com mais de um caractere"
        return "literal de caractere não fechado"
    if c == "!":
        return "'!' isolado (esperava '!=')"
    if c == ".":
        return "ponto inesperado (float exige dígitos antes e depois)"
    return f"caractere inválido '{c}'"

def analisar(codigo):
    """Percorre todo o código e devolve (tokens, erros)."""
    tokens, erros = [], []
    i, linha, n = 0, 1, len(codigo)
 
    while i < n:
        estado, fim = proximo_lexema(codigo, i)
 
        if estado is not None:                    # reconheceu um lexema
            lexema = codigo[i:fim]
            tipo = ACEITACAO[estado]
            if tipo is None:                      # espaço em branco
                linha += lexema.count("\n")
            else:
                if tipo == "ID":                  # palavra reservada?
                    tipo = PALAVRAS_RESERVADAS.get(lexema, "ID")
                tokens.append(Token(lexema, tipo, linha))
            i = fim
        else:                                     # erro léxico
            fim = recuperar_erro(codigo, i, fim)
            lexema = codigo[i:fim]
            erros.append(ErroLexico(linha, lexema, mensagem_erro(lexema)))
            i = fim
 
    return tokens, erros