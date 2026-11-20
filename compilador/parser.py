"""
Analisador sintático (parser) descendente recursivo para a Linguagem P.

Cada função corresponde a uma produção da gramática fornecida na especificação.
O parser consome o vetor de tokens produzido pelo analisador léxico e, durante
o reconhecimento, constrói as tabelas de símbolos de cada função.

Gramática implementada:
    Programa         → Funcao FuncaoSeq
    FuncaoSeq        → Funcao FuncaoSeq | ε
    Funcao           → fn NomeFuncao ( ListaParams ) TipoRetornoFuncao Bloco
    NomeFuncao       → ID | MAIN
    ListaParams      → ID : Type ListaParams2 | ε
    ListaParams2     → , ID : Type ListaParams2 | ε
    TipoRetornoFuncao → -> Type | ε
    Bloco            → { Sequencia }
    Sequencia        → Declaracao Sequencia | Comando Sequencia | ε
    Declaracao       → let VarList : Type ;
    VarList          → ID VarList2
    VarList2         → , ID VarList2 | ε
    Type             → int | float | char
    Comando          → ID AtribuicaoOuChamada
                     | ComandoSe
                     | while Expr Bloco
                     | println ( FMT_STRING , ListaArgs ) ;
                     | return Expr ;
    AtribuicaoOuChamada → = Expr ; | ( ListaArgs ) ;
    ComandoSe        → if Expr Bloco ComandoSenao | Bloco
    ComandoSenao     → else ComandoSe | ε
    Expr             → Rel ExprOpc
    ExprOpc          → OpIgual Rel ExprOpc | ε
    OpIgual          → == | !=
    Rel              → Adicao RelOpc
    RelOpc           → OpRel Adicao RelOpc | ε
    OpRel            → < | <= | > | >=
    Adicao           → Termo AdicaoOpc
    AdicaoOpc        → OpAdicao Termo AdicaoOpc | ε
    OpAdicao         → + | -
    Termo            → Fator TermoOpc
    TermoOpc         → OpMult Fator TermoOpc | ε
    OpMult           → * | /
    Fator            → ID ChamadaFuncao
                     | INT_CONST | FLOAT_CONST | CHAR_LITERAL
                     | ( Expr )
    ChamadaFuncao    → ( ListaArgs ) | ε
    ListaArgs        → Arg ListaArgs2 | ε
    ListaArgs2       → , Arg ListaArgs2 | ε
    Arg              → ID ChamadaFuncao
                     | INT_CONST | FLOAT_CONST | CHAR_LITERAL
"""

from tokens import Token
from erros import ErroSintatico
from tabela_simbolos import (
    TabelaSimbolos, SimboloEntry, FunctionRegister, DataType,
)
from typing import List, Optional


# Mapeamento: token de tipo da linguagem → DataType interno
_TIPO_MAP = {
    "INT":   DataType.INT,
    "FLOAT": DataType.FLOAT,
    "CHAR":  DataType.CHAR,
}


class Parser:
    """Parser descendente recursivo preditivo (LL(1)) para a Linguagem P."""

    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0
        self.erros: List[ErroSintatico] = []

        # Tabelas de símbolos (uma por função/escopo)
        self.tabelas: List[TabelaSimbolos] = []
        self.tabela_atual: Optional[TabelaSimbolos] = None

    # ══════════════════════════════════════════════════════════════════════
    #  Utilitários
    # ══════════════════════════════════════════════════════════════════════

    def token_atual(self) -> Token:
        """Retorna o token na posição corrente ou um sentinela EOF."""
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        linha = self.tokens[-1].linha if self.tokens else 0
        return Token("$", "EOF", linha)

    def match(self, tipo_esperado: str) -> Token:
        """Consome e retorna o token se ele for do tipo esperado.

        Se não casar, registra um erro sintático e **não** consome o token
        (para que a próxima regra da gramática possa tentar usá-lo).
        """
        tok = self.token_atual()
        if tok.tipo == tipo_esperado:
            self.pos += 1
            return tok
        self._erro(tipo_esperado, tok)
        return tok          # devolve o que encontrou, sem avançar

    def _erro(self, esperado: str, tok: Token):
        """Registra um erro sintático."""
        msg = f"Esperado '{esperado}', encontrado '{tok.lexema}' ({tok.tipo})"
        self.erros.append(ErroSintatico(
            linha=tok.linha,
            esperado=esperado,
            encontrado=tok.tipo,
            mensagem=msg,
        ))

    # ══════════════════════════════════════════════════════════════════════
    #  Ponto de entrada
    # ══════════════════════════════════════════════════════════════════════

    def parse(self):
        """Inicia a análise sintática (Programa)."""
        self.programa()
        # Se sobraram tokens não consumidos, reporta
        if self.pos < len(self.tokens):
            tok = self.token_atual()
            self._erro("fim do arquivo", tok)

    # ══════════════════════════════════════════════════════════════════════
    #  Produções da gramática
    # ══════════════════════════════════════════════════════════════════════

    # ---- Programa / Funções --------------------------------------------

    def programa(self):
        # Programa → Funcao FuncaoSeq
        self.funcao()
        self.funcao_seq()

    def funcao_seq(self):
        # FuncaoSeq → Funcao FuncaoSeq | ε
        if self.token_atual().tipo == "FUNCTION":
            self.funcao()
            self.funcao_seq()
        # senão: ε

    def funcao(self):
        # Funcao → fn NomeFuncao ( ListaParams ) TipoRetornoFuncao Bloco
        self.match("FUNCTION")          # fn

        # NomeFuncao → ID | MAIN
        tok = self.token_atual()
        if tok.tipo in ("ID", "MAIN"):
            nome = tok.lexema
            self.pos += 1
        else:
            self._erro("ID ou MAIN", tok)
            nome = "<erro>"

        # Cria uma nova tabela de símbolos para esta função
        self.tabela_atual = TabelaSimbolos(nome)
        self.tabelas.append(self.tabela_atual)

        self.match("LBRACKET")          # (
        self.lista_params()
        self.match("RBRACKET")          # )
        self.tipo_retorno_funcao()
        self.bloco()

    # ---- Parâmetros ----------------------------------------------------

    def lista_params(self):
        # ListaParams → ID : Type ListaParams2 | ε
        if self.token_atual().tipo == "ID":
            tok_id = self.match("ID")
            self.match("COLON")
            tipo = self.type_rule()

            if tok_id.tipo == "ID":
                self.tabela_atual.inserir(SimboloEntry(
                    name=tok_id.lexema, datatype=tipo,
                    is_param=True, pos_param=0,
                ))

            self.lista_params2(1)
        # senão: ε (sem parâmetros)

    def lista_params2(self, pos: int):
        # ListaParams2 → , ID : Type ListaParams2 | ε
        if self.token_atual().tipo == "COMMA":
            self.match("COMMA")
            tok_id = self.match("ID")
            self.match("COLON")
            tipo = self.type_rule()

            if tok_id.tipo == "ID":
                self.tabela_atual.inserir(SimboloEntry(
                    name=tok_id.lexema, datatype=tipo,
                    is_param=True, pos_param=pos,
                ))

            self.lista_params2(pos + 1)
        # senão: ε

    # ---- Tipo de retorno -----------------------------------------------

    def tipo_retorno_funcao(self):
        # TipoRetornoFuncao → -> Type | ε
        if self.token_atual().tipo == "ARROW":
            self.match("ARROW")
            tipo = self.type_rule()
            self.tabela_atual.ret_type = tipo
        # senão: ε — ret_type permanece VOID

    def type_rule(self) -> DataType:
        # Type → int | float | char
        tok = self.token_atual()
        if tok.tipo in _TIPO_MAP:
            self.pos += 1
            return _TIPO_MAP[tok.tipo]
        self._erro("int, float ou char", tok)
        return DataType.ERROR

    # ---- Bloco / Sequência ---------------------------------------------

    def bloco(self):
        # Bloco → { Sequencia }
        self.match("LBRACE")            # {
        self.sequencia()
        self.match("RBRACE")            # }

    def sequencia(self):
        # Sequencia → Declaracao Sequencia | Comando Sequencia | ε
        #
        # Usa um laço com verificação de progresso para evitar loop infinito
        # caso um erro impeça o consumo de tokens.
        while True:
            tok = self.token_atual()
            if tok.tipo == "EOF":
                break

            pos_antes = self.pos

            if tok.tipo == "LET":
                self.declaracao()
            elif tok.tipo in ("ID", "IF", "WHILE", "PRINTLN", "RETURN"):
                self.comando()
            else:
                break                   # ε — espera-se }

            # Segurança: se nenhum token foi consumido, avança um para não travar
            if self.pos == pos_antes:
                self.pos += 1

    # ---- Declaração de variáveis ---------------------------------------

    def declaracao(self):
        # Declaracao → let VarList : Type ;
        self.match("LET")
        nomes = self.var_list()
        self.match("COLON")
        tipo = self.type_rule()
        self.match("SEMICOLON")

        # Registra cada variável na tabela de símbolos
        for nome in nomes:
            self.tabela_atual.inserir(SimboloEntry(
                name=nome, datatype=tipo,
                is_param=False, pos_param=-1,
            ))

    def var_list(self) -> List[str]:
        # VarList → ID VarList2
        nomes: List[str] = []
        tok = self.match("ID")
        if tok.tipo == "ID":
            nomes.append(tok.lexema)
        self.var_list2(nomes)
        return nomes

    def var_list2(self, nomes: List[str]):
        # VarList2 → , ID VarList2 | ε
        if self.token_atual().tipo == "COMMA":
            self.match("COMMA")
            tok = self.match("ID")
            if tok.tipo == "ID":
                nomes.append(tok.lexema)
            self.var_list2(nomes)
        # senão: ε

    # ---- Comandos ------------------------------------------------------

    def comando(self):
        # Comando → ID AtribuicaoOuChamada
        #         | ComandoSe
        #         | while Expr Bloco
        #         | println ( FMT_STRING , ListaArgs ) ;
        #         | return Expr ;
        tok = self.token_atual()

        if tok.tipo == "ID":
            tok_id = self.match("ID")
            self.atribuicao_ou_chamada(tok_id)

        elif tok.tipo == "IF":
            self.comando_se()

        elif tok.tipo == "WHILE":
            self.match("WHILE")
            self.expr()
            self.bloco()

        elif tok.tipo == "PRINTLN":
            self.match("PRINTLN")
            self.match("LBRACKET")          # (
            self.match("FMT_STRING")
            self.match("COMMA")
            self.lista_args()
            self.match("RBRACKET")          # )
            self.match("SEMICOLON")

            # Registra println na tabela (sem FunctionRegister)
            if self.tabela_atual.buscar("println") is None:
                self.tabela_atual.inserir(SimboloEntry(
                    name="println", datatype=DataType.VOID,
                    is_param=False, pos_param=-1,
                ))

        elif tok.tipo == "RETURN":
            self.match("RETURN")
            self.expr()
            self.match("SEMICOLON")

        else:
            self._erro("comando (ID, if, while, println ou return)", tok)

    def atribuicao_ou_chamada(self, tok_id: Token):
        # AtribuicaoOuChamada → = Expr ; | ( ListaArgs ) ;
        tok = self.token_atual()

        if tok.tipo == "ASSIGN":
            # Atribuição: ID = Expr ;
            self.match("ASSIGN")
            self.expr()
            self.match("SEMICOLON")

        elif tok.tipo == "LBRACKET":
            # Chamada de função: ID ( ListaArgs ) ;
            self.match("LBRACKET")          # (
            args = self.lista_args()
            self.match("RBRACKET")          # )
            self.match("SEMICOLON")

            self._registrar_chamada(tok_id.lexema, args)

        else:
            self._erro("'=' ou '('", tok)

    # ---- Comando if / else ---------------------------------------------

    def comando_se(self):
        # ComandoSe → if Expr Bloco ComandoSenao | Bloco
        tok = self.token_atual()

        if tok.tipo == "IF":
            self.match("IF")
            self.expr()
            self.bloco()
            self.comando_senao()

        elif tok.tipo == "LBRACE":
            # Alternativa: Bloco (usada pelo 'else { … }')
            self.bloco()

        else:
            self._erro("'if' ou '{'", tok)

    def comando_senao(self):
        # ComandoSenao → else ComandoSe | ε
        if self.token_atual().tipo == "ELSE":
            self.match("ELSE")
            self.comando_se()
        # senão: ε

    # ══════════════════════════════════════════════════════════════════════
    #  Expressões — com precedência de operadores embutida na gramática
    # ══════════════════════════════════════════════════════════════════════

    def expr(self):
        # Expr → Rel ExprOpc
        self.rel()
        self.expr_opc()

    def expr_opc(self):
        # ExprOpc → OpIgual Rel ExprOpc | ε
        # OpIgual → == | !=
        if self.token_atual().tipo in ("EQ", "NE"):
            self.pos += 1               # consome == ou !=
            self.rel()
            self.expr_opc()

    def rel(self):
        # Rel → Adicao RelOpc
        self.adicao()
        self.rel_opc()

    def rel_opc(self):
        # RelOpc → OpRel Adicao RelOpc | ε
        # OpRel → < | <= | > | >=
        if self.token_atual().tipo in ("LT", "LE", "GT", "GE"):
            self.pos += 1
            self.adicao()
            self.rel_opc()

    def adicao(self):
        # Adicao → Termo AdicaoOpc
        self.termo()
        self.adicao_opc()

    def adicao_opc(self):
        # AdicaoOpc → OpAdicao Termo AdicaoOpc | ε
        # OpAdicao → + | -
        if self.token_atual().tipo in ("PLUS", "MINUS"):
            self.pos += 1
            self.termo()
            self.adicao_opc()

    def termo(self):
        # Termo → Fator TermoOpc
        self.fator()
        self.termo_opc()

    def termo_opc(self):
        # TermoOpc → OpMult Fator TermoOpc | ε
        # OpMult → * | /
        if self.token_atual().tipo in ("MULT", "DIV"):
            self.pos += 1
            self.fator()
            self.termo_opc()

    def fator(self):
        # Fator → ID ChamadaFuncao
        #        | INT_CONST | FLOAT_CONST | CHAR_LITERAL
        #        | ( Expr )
        tok = self.token_atual()

        if tok.tipo == "ID":
            tok_id = self.match("ID")
            self.chamada_funcao(tok_id)

        elif tok.tipo in ("INT_CONST", "FLOAT_CONST", "CHAR_LITERAL"):
            self.pos += 1

        elif tok.tipo == "LBRACKET":
            self.match("LBRACKET")      # (
            self.expr()
            self.match("RBRACKET")      # )

        else:
            self._erro("expressão (ID, constante ou '(')", tok)
            self.pos += 1               # avança para não travar em recursão

    # ---- Chamada de função em expressão --------------------------------

    def chamada_funcao(self, tok_id: Token):
        # ChamadaFuncao → ( ListaArgs ) | ε
        if self.token_atual().tipo == "LBRACKET":
            self.match("LBRACKET")      # (
            args = self.lista_args()
            self.match("RBRACKET")      # )
            self._registrar_chamada(tok_id.lexema, args)
        # senão: ε — uso simples de variável

    # ---- Argumentos de chamada -----------------------------------------

    def lista_args(self) -> List[str]:
        # ListaArgs → Arg ListaArgs2 | ε
        args: List[str] = []
        tok = self.token_atual()
        if tok.tipo in ("ID", "INT_CONST", "FLOAT_CONST", "CHAR_LITERAL"):
            lexema = self.arg()
            args.append(lexema)
            self.lista_args2(args)
        return args

    def lista_args2(self, args: List[str]):
        # ListaArgs2 → , Arg ListaArgs2 | ε
        if self.token_atual().tipo == "COMMA":
            self.match("COMMA")
            lexema = self.arg()
            args.append(lexema)
            self.lista_args2(args)
        # senão: ε

    def arg(self) -> str:
        # Arg → ID ChamadaFuncao | INT_CONST | FLOAT_CONST | CHAR_LITERAL
        tok = self.token_atual()

        if tok.tipo == "ID":
            tok_id = self.match("ID")
            self.chamada_funcao(tok_id)
            return tok_id.lexema

        elif tok.tipo in ("INT_CONST", "FLOAT_CONST", "CHAR_LITERAL"):
            self.pos += 1
            return tok.lexema

        else:
            self._erro("argumento (ID ou constante)", tok)
            self.pos += 1               # avança para não travar
            return "<erro>"

    # ══════════════════════════════════════════════════════════════════════
    #  Tabela de símbolos — registro de chamadas de função
    # ══════════════════════════════════════════════════════════════════════

    def _registrar_chamada(self, nome: str, args: List[str]):
        """Cria um FunctionRegister e o associa ao símbolo na tabela atual."""
        fr = FunctionRegister(name=nome, num_args=len(args), args=args)

        entry = self.tabela_atual.buscar(nome)
        if entry is None:
            # Primeira ocorrência: cria entrada (tipo será resolvido na semântica)
            entry = SimboloEntry(
                name=nome, datatype=DataType.VOID,
                is_param=False, pos_param=-1,
            )
            self.tabela_atual.inserir(entry)

        entry.call_refs.append(fr)
