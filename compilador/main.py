"""
COMO USAR (a partir de qualquer pasta):
    python3 compilador/main.py arquivo.p
    python3 compilador/main.py arquivo.p -q        (não imprime no terminal)

Fluxo: código-fonte -> análise léxica -> vetor de tokens
                    -> análise sintática (+ tabelas de símbolos)

Saídas (pasta 'saidas/' ao lado deste arquivo):
    <nome>_tokens.txt           vetor de tokens
    <nome>_erros_lexicos.txt    erros léxicos
    <nome>_erros_sintaticos.txt erros sintáticos
    <nome>_tabela_simbolos.txt  tabela de símbolos de cada função
"""
import os
import sys

from lexer import analisar
from parser import Parser

PASTA_SAIDA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saidas")


def formatar_tokens(tokens):
    linhas = [f"{'LINHA':<6}{'TIPO':<14}LEXEMA", "-" * 40]
    for t in tokens:
        linhas.append(f"{t.linha:<6}{t.tipo:<14}{t.lexema}")
    linhas.append("-" * 40)
    linhas.append(f"Total: {len(tokens)} token(s)")
    return "\n".join(linhas)


def formatar_erros(erros):
    if not erros:
        return "Nenhum erro léxico encontrado."
    linhas = [f"Linha {e.linha}: {e.mensagem} -> {e.lexema}" for e in erros]
    linhas.append(f"Total: {len(erros)} erro(s) léxico(s)")
    return "\n".join(linhas)


def formatar_erros_sintaticos(erros):
    if not erros:
        return "Nenhum erro sintático encontrado."
    linhas = [f"Linha {e.linha}: {e.mensagem}" for e in erros]
    linhas.append(f"Total: {len(erros)} erro(s) sintático(s)")
    return "\n".join(linhas)


def formatar_tabelas(tabelas):
    if not tabelas:
        return "Nenhuma função definida; nenhuma tabela de símbolos criada."
    blocos = [t.formatar() for t in tabelas]
    blocos.append(f"Total: {len(tabelas)} tabela(s) de símbolos")
    return "\n\n".join(blocos)


def gravar(caminho, texto):
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(texto + "\n")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    silencioso = "-q" in sys.argv

    if not args:
        print("uso: python3 compilador/main.py arquivo.p [-q]")
        sys.exit(1)

    caminho = args[0]
    try:
        with open(caminho, encoding="utf-8") as f:
            codigo = f.read()
    except FileNotFoundError:
        print(f"erro: arquivo '{caminho}' não encontrado")
        sys.exit(1)

    # 1) Análise léxica: código -> vetor de tokens (+ erros léxicos)
    tokens, erros_lex = analisar(codigo)

    # 2) Análise sintática: consome o vetor de tokens, constrói as tabelas
    parser = Parser(tokens)
    parser.parse()

    texto_tokens = formatar_tokens(tokens)
    texto_lex = formatar_erros(erros_lex)
    texto_sint = formatar_erros_sintaticos(parser.erros)
    texto_tab = formatar_tabelas(parser.tabelas)

    os.makedirs(PASTA_SAIDA, exist_ok=True)
    nome = os.path.splitext(os.path.basename(caminho))[0]
    saidas = {
        "tokens": (f"{nome}_tokens.txt", texto_tokens),
        "erros_lexicos": (f"{nome}_erros_lexicos.txt", texto_lex),
        "erros_sintaticos": (f"{nome}_erros_sintaticos.txt", texto_sint),
        "tabela_simbolos": (f"{nome}_tabela_simbolos.txt", texto_tab),
    }
    for arquivo, texto in saidas.values():
        gravar(os.path.join(PASTA_SAIDA, arquivo), texto)

    if not silencioso:
        print("=== TOKENS ===")
        print(texto_tokens)
        print("\n=== ERROS LÉXICOS ===")
        print(texto_lex)
        print("\n=== ERROS SINTÁTICOS ===")
        print(texto_sint)
        print("\n=== TABELAS DE SÍMBOLOS ===")
        print(texto_tab)
        print()
    print("Arquivos gerados em", PASTA_SAIDA + ":")
    for arquivo, _ in saidas.values():
        print("  ", arquivo)


if __name__ == "__main__":
    main()
