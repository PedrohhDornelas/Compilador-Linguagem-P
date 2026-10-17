"""
COMO USAR:
    python main.py arquivo.p
    python main.py arquivo.p -q        (não imprime no terminal, só grava arquivos)

Saídas (pasta 'saidas/'):
    <nome>_tokens.txt          vetor de tokens
    <nome>_erros_lexicos.txt   erros léxicos
"""
import os
import sys

from lexer import analisar

PASTA_SAIDA = "saidas"


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


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    silencioso = "-q" in sys.argv

    if not args:
        print("uso: python main.py arquivo.p [-q]")
        sys.exit(1)

    caminho = args[0]
    try:
        with open(caminho, encoding="utf-8") as f:
            codigo = f.read()
    except FileNotFoundError:
        print(f"erro: arquivo '{caminho}' não encontrado")
        sys.exit(1)

    tokens, erros = analisar(codigo)

    texto_tokens = formatar_tokens(tokens)
    texto_erros = formatar_erros(erros)

    os.makedirs(PASTA_SAIDA, exist_ok=True)
    nome = os.path.splitext(os.path.basename(caminho))[0]
    arq_tokens = os.path.join(PASTA_SAIDA, f"{nome}_tokens.txt")
    arq_erros = os.path.join(PASTA_SAIDA, f"{nome}_erros_lexicos.txt")

    with open(arq_tokens, "w", encoding="utf-8") as f:
        f.write(texto_tokens + "\n")
    with open(arq_erros, "w", encoding="utf-8") as f:
        f.write(texto_erros + "\n")

    if not silencioso:
        print("=== TOKENS ===")
        print(texto_tokens)
        print("\n=== ERROS LÉXICOS ===")
        print(texto_erros)
        print()
    print(f"Arquivos gerados: {arq_tokens} e {arq_erros}")


if __name__ == "__main__":
    main()