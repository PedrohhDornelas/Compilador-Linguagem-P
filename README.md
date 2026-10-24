# Compilador da Linguagem P - Entrega 1: Análise Léxica

## Requisitos
Python 3 (sem dependências externas)

```
sudo pacman -S python      # EndeavourOS / Arch
```

## Como executar
```
python3 main.py <arquivo.p> [diretorio_de_saida]
```
Exemplo:
```
python3 main.py tests/entradas/exemplo1_soma.p
```

Para rodar todos os testes e regenerar as saídas:
```
for f in tests/entradas/*.p; do python3 main.py "$f" tests/saidas; done
```

## O que esperar de saída
Para `x.p`, é gerado o arquivo `x_lexica.txt` com duas seções:

1. **Vetor de tokens**, na ordem de reconhecimento: índice, linha, tipo e lexema
2. **Erros léxicos**: linha, mensagem e lexema. Se não houver, aparece "Nenhum erro léxico encontrado."

Exemplo:
```
=== VETOR DE TOKENS ===
Índice  Linha   Tipo           Lexema
0       1       FUNCTION       fn
1       1       MAIN           main
...
=== ERROS LÉXICOS ===
Linha 3: caractere inválido '@' (lexema: @)
```

## Como funciona
| Arquivo | Função |
|---|---|
| `main.py` | Lê o arquivo de entrada e grava a saída |
| `compilador/tokens.py` | Estrutura `Token` (lexema, tipo, linha), `ErroLexico` e palavras reservadas |
| `compilador/afd.py` | AFD: estados, estados de aceitação e tabela de transições |
| `compilador/lexer.py` | Percorre o código seguindo o AFD, gera tokens e registra erros |
| `compilador/saida.py` | Formata o arquivo de saída |

**Etapas da análise:**
1. O código é lido e cada caractere é classificado (letra, dígito, símbolo etc.)
2. O AFD faz transições a partir do estado inicial até não haver mais transição possível
3. Se parou em um estado de aceitação, o lexema vira um `Token`. Identificadores são comparados com as palavras reservadas para definir o tipo final. Espaços e quebras de linha são descartados, mas as quebras são contadas para o número da linha
4. Se parou em um estado não aceitador, registra-se o erro léxico e a análise continua do ponto seguinte

**Erros léxicos tratados:** caractere inválido (inclui `.` isolado, `_` no início, `@`, `#`, `[`, `]` etc.); float malformado (`12.`); `!` isolado; char vazio, com mais de um caractere ou não fechado; string de formatação vazia ou não fechada (deve fechar na mesma linha)

## Testes (`tests/`)
`entradas/` contém os `.p` (os 3 exemplos da especificação, palavras reservadas, operadores e pontuação, identificadores e constantes, erros léxicos) e `saidas/` contém os `_lexica.txt` correspondentes
