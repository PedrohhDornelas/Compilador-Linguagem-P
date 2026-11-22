# Compilador da Linguagem P — Entrega 2: Análise Sintática + Tabela de Símbolos


## Requisitos
Python 3 (sem dependências externas)
```
sudo pacman -S python
```

## Como executar
Funciona a partir de qualquer pasta:
```
python3 compilador/main.py <arquivo.p> [-q]
```
`-q` não imprime no terminal, só grava os arquivos.

Exemplos:
```
python3 compilador/main.py compilador/entradas/exemplo1.p
python3 compilador/main.py compilador/entradas/sintatico_erros.p -q
```

Para regenerar as saídas dos testes de todas as entradas:
```
for f in compilador/entradas/*.p; do python3 compilador/main.py "$f" -q; done
```

## Saídas (`compilador/saidas/`)
Para uma entrada `x.p`:

| Arquivo | Conteúdo |
|---|---|
| `x_tokens.txt` | vetor de tokens (linha, tipo, lexema) |
| `x_erros_lexicos.txt` | erros léxicos |
| `x_erros_sintaticos.txt` | erros sintáticos (`Linha N: Esperado ..., encontrado ...`) |
| `x_tabela_simbolos.txt` | uma tabela de símbolos por função, com `ret_type` e os `FunctionRegister` |

## Como funciona
| Arquivo | Função |
|---|---|
| `compilador/main.py` | lê o `.p`, chama léxico e parser, grava as 4 saídas |
| `compilador/tokens.py` | `Token` (lexema, tipo, linha), `ErroLexico`, palavras reservadas |
| `compilador/afd.py` | AFD do analisador léxico |
| `compilador/lexer.py` | analisador léxico guiado pelo AFD |
| `compilador/erros.py` | `ErroSintatico` (linha, esperado, encontrado, mensagem) |
| `compilador/tabela_simbolos.py` | `DataType`, `SimboloEntry`, `FunctionRegister`, `TabelaSimbolos` |
| `compilador/parser.py` | parser descendente recursivo: cada produção da gramática é um método |

**Parser:** consome o vetor de tokens; cada produção da gramática da seção 5 da
especificação é um método de `Parser`. Durante o reconhecimento são preenchidas as
tabelas de símbolos (parâmetros com `pos_param`, variáveis com `pos_param = -1`,
`println` e chamadas de função com seus `FunctionRegister`; `ret_type` vem de
`-> Type`, ou `void`). Depois do parse, o `datatype` de cada função chamada é
resolvido com o `ret_type` da função correspondente (a função pode ser definida
depois da chamada); função chamada mas não definida fica `ERROR`.

**Erros sintáticos e recuperação (modo pânico):** ao encontrar um erro, o parser
registra uma mensagem e ignora os erros seguintes até sincronizar, para não gerar
erros em cascata. Pontos de sincronização: `;` (consumido), `}`, `fn`, fim do arquivo
e início de `let`/`if`/`while`/`println`/`return`. Erros no cabeçalho da função
sincronizam em `{`; erros fora de função sincronizam no próximo `fn`. Assim a análise
continua e as demais funções ainda são analisadas.

Pontos da gramática seguidos à risca: `println` exige `FMT_STRING , ListaArgs`
(a vírgula é obrigatória) e argumentos (`Arg`) são só `ID`, constantes ou chamadas, não
expressões; um bloco `{ ... }` solto é comando válido (`Comando → ComandoSe → Bloco`).

## Testes (`compilador/entradas/` e `compilador/saidas/`)
| Entrada | O que testa |
|---|---|
| `exemplo1.p`, `exemplo2.p`, `exemplo3.p` | os 3 exemplos da especificação |
| `sintatico_ok.p` | exemplo 7.6 + bloco solto, sem erros |
| `tabela_chamadas.p` | `call_refs`, vários `FunctionRegister`, chamada antes da definição, args char/float |
| `redeclaracao.p` | parâmetro e variável repetidos (sem erro sintático; semântica na Entrega 3) |
| `sintatico_erros.p` | vários erros sintáticos em 3 funções, um erro por trecho |
| `sintatico_erros2.p` | `else` solto, `}` extra, lixo entre funções, falta de `}` no fim |
| `sintatico_vazio.p`, `arquivo_vazio.p` | arquivo vazio |
| `chamadas.p` | chamadas como comando e em expressão, chamada aninhada (`soma3(r, dobro(1), 3)`), 3 parâmetros |
| `chamada_antes_da_definicao.p` | `main` chama função definida depois (tipo resolvido no fim do parse) |
| `erro_sintatico_declaracao.p` | `let x int;`, `let : int;`, expressão faltando |
| `erro_sintatico_estrutura.p` | `)` faltando no cabeçalho, `else` solto, `while` sem condição, duas `}` faltando (o erro aparece duas vezes na linha 16: uma para o `if` e outra para `main`) |
| `erro_sintatico_fora_de_funcao.p` | comandos fora de função e `}` extra, com recuperação até o próximo `fn` |
| `erro_sintatico_ponto_virgula.p` | `;` faltando no meio e antes de `}` |
| `erro_sintatico_println.p` | `println` com expressão, sem vírgula, sem string e `(` sem `)` |
| `chars_strings.p`, `identificadores.p`, `numeros.p`, `operadores.p`, `reservadas.p` | testes léxicos (Entrega 1) |

Obs.: as saídas dos testes léxicos (`chars_strings`, `identificadores`, `numeros`,
`operadores`, `reservadas`) são as da Entrega 1; para esses arquivos não há saídas
sintáticas, pois não são programas completos.
