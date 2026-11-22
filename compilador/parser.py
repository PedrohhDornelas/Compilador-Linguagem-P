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

Recuperação de erros (modo pânico):
    Ao detectar um erro, o parser registra UMA mensagem e entra em "modo pânico":
    novos erros são suprimidos até o parser se ressincronizar. A ressincronização
    acontece (a) quando um match() é bem-sucedido, ou (b) ao descartar tokens até
    um ponto seguro (';', '}', início de comando ou 'fn'). Assim, um único erro no
    código-fonte gera uma única mensagem, em vez de uma cascata de erros.
"""

from tokens import Token
from erros import ErroSintatico
from tabela_simbolos import (
    TabelaSimbolos, SimboloEntry, FunctionRegister, DataType,
)
from typing import List, Optional, Tuple


# Mapeamento: token de tipo da linguagem → DataType interno
_TIPO_MAP = {
    "INT":   DataType.INT,
    "FLOAT": DataType.FLOAT,
    "CHAR":  DataType.CHAR,
}

# Nomes legíveis dos tokens, usados nas mensagens de erro sintático
_NOME_LEGIVEL = {
    "FUNCTION": "'fn'", "MAIN": "'main'", "LET": "'let'",
    "INT": "'int'", "FLOAT": "'float'", "CHAR": "'char'",
    "IF": "'if'", "ELSE": "'else'", "WHILE": "'while'",
    "PRINTLN": "'println'", "RETURN": "'return'",
    "LBRACKET": "'('", "RBRACKET": "')'", "LBRACE": "'{'", "RBRACE": "'}'",
    "ARROW": "'->'", "COLON": "':'", "SEMICOLON": "';'", "COMMA": "','",
    "ASSIGN": "'='", "EQ": "'=='", "NE": "'!='", "GT": "'>'", "GE": "'>='",
    "LT": "'<'", "LE": "'<='", "PLUS": "'+'", "MINUS": "'-'",
    "MULT": "'*'", "DIV": "'/'",
    "ID": "identificador", "INT_CONST": "constante inteira",
    "FLOAT_CONST": "constante float", "CHAR_LITERAL": "literal de caractere",
    "FMT_STRING": "string de formatação", "EOF": "fim do arquivo",
}

# Tokens que ancoram a recuperação de erros (modo pânico)
_SYNC_COMANDO = {"RBRACE", "EOF", "FUNCTION", "LET", "IF", "WHILE",
                 "PRINTLN", "RETURN"}
_INICIO_COMANDO = {"ID", "IF", "WHILE", "PRINTLN", "RETURN", "LBRACE"}
# Tokens cuja consumição com sucesso encerra o modo pânico
_FIM_PANICO = {"SEMICOLON", "LBRACE", "RBRACE"}

# Nome "legível" de cada token para as mensagens de erro
# (o usuário vê '(' e não LBRACKET).
_NOME_LEGIVEL = {
    "FUNCTION":   "'fn'",
    "MAIN":       "'main'",
    "LET":        "'let'",
    "IF":         "'if'",
    "ELSE":       "'else'",
    "WHILE":      "'while'",
    "PRINTLN":    "'println'",
    "RETURN":     "'return'",
    "LBRACKET":   "'('",
    "RBRACKET":   "')'",
    "LBRACE":     "'{'",
    "RBRACE":     "'}'",
    "COLON":      "':'",
    "SEMICOLON":  "';'",
    "COMMA":      "','",
    "ASSIGN":     "'='",
    "ARROW":      "'->'",
    "ID":         "identificador",
    "FMT_STRING": "string de formatação",
    "EOF":        "fim do arquivo",
}

# Tokens que podem iniciar um Comando
# (ComandoSe → if ... | Bloco, por isso IF e LBRACE entram aqui).
_INICIO_COMANDO = {"ID", "IF", "WHILE", "PRINTLN", "RETURN", "LBRACE"}

# Pontos de ressincronização dentro de um bloco (modo pânico)
_SYNC_COMANDO = _INICIO_COMANDO | {"LET", "RBRACE", "FUNCTION", "EOF"}


class Parser:
    """Parser descendente recursivo preditivo (LL(1)) para a Linguagem P."""

    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0
        self.erros: List[ErroSintatico] = []
        self.modo_panico = False

        # Tabelas de símbolos (uma por função/escopo)
        self.tabelas: List[TabelaSimbolos] = []
        self.tabela_atual: Optional[TabelaSimbolos] = None

        # Redeclarações detectadas na inserção (usadas na fase semântica)
        self.redeclaracoes: List[tuple] = []     # (linha, nome, função)

    # ══════════════════════════════════════════════════════════════════════
    #  Utilitários
    # ══════════════════════════════════════════════════════════════════════

    def token_atual(self) -> Token:
        """Retorna o token na posição corrente ou um sentinela EOF."""
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        linha = self.tokens[-1].linha if self.tokens else 1
        return Token("$", "EOF", linha)

    def match(self, tipo_esperado: str) -> Token:
        """Consome e retorna o token se ele for do tipo esperado.

        Se não casar, registra um erro sintático e **não** consome o token
        (a recuperação fica a cargo de quem chamou / do modo pânico).
        """
        tok = self.token_atual()
        if tok.tipo == tipo_esperado:
            self.pos += 1
            if tipo_esperado in _FIM_PANICO:
                self.modo_panico = False
            return tok
        self._erro(_NOME_LEGIVEL.get(tipo_esperado, tipo_esperado), tok)
        return tok          # devolve o que encontrou, sem avançar

    def _erro(self, esperado: str, tok: Token):
        """Registra um erro sintático (suprimido enquanto em modo pânico).

        Em modo pânico os erros em cascata são descartados: só o primeiro
        erro de cada trecho é reportado, até a próxima sincronização.
        """
        if self.modo_panico:
            return
        self.modo_panico = True
        if tok.tipo == "EOF":
            encontrado = "fim do arquivo"
        else:
            encontrado = f"'{tok.lexema}'"
        self.erros.append(ErroSintatico(
            linha=tok.linha,
            esperado=esperado,
            encontrado=encontrado,
            mensagem=f"Esperado {esperado}, encontrado {encontrado}",
        ))

    # ---- Recuperação de erros (modo pânico) -----------------------------

    def _sincronizar_comando(self):
        """Descarta tokens até um ponto seguro dentro de um bloco.

        Pára (consumindo) após um ';', ou (sem consumir) em '}', 'fn', EOF ou
        no início de uma declaração/comando que não aparece em expressões.
        """
        while True:
            t = self.token_atual().tipo
            if t == "SEMICOLON":
                self.pos += 1
                break
            if t in _SYNC_COMANDO:
                break
            self.pos += 1
        self.modo_panico = False

    def _sincronizar_cabecalho(self):
        """Após erro no cabeçalho da função, avança até '{' ou próximo 'fn'."""
        while self.token_atual().tipo not in ("LBRACE", "FUNCTION", "EOF"):
            self.pos += 1
        self.modo_panico = False

    def _pular_ate_funcao(self):
        """Erro fora de função: descarta tokens até o próximo 'fn' ou EOF."""
        while self.token_atual().tipo not in ("FUNCTION", "EOF"):
            self.pos += 1
        self.modo_panico = False

    # ══════════════════════════════════════════════════════════════════════
    #  Ponto de entrada
    # ══════════════════════════════════════════════════════════════════════

    def parse(self):
        """Inicia a análise sintática (Programa)."""
        self.programa()
        self._resolver_tipos_chamadas()

    # ══════════════════════════════════════════════════════════════════════
    #  Produções da gramática
    # ══════════════════════════════════════════════════════════════════════

    # ---- Programa / Funções --------------------------------------------

    def programa(self):
        # Programa → Funcao FuncaoSeq
        self.funcao()
        self.funcao_seq()

    def funcao_seq(self):
        # FuncaoSeq → Funcao FuncaoSeq | ε   (ε = fim do arquivo)
        # Implementada como laço: tokens que não iniciam função são erro e
        # são descartados até o próximo 'fn'.
        while True:
            tok = self.token_atual()
            if tok.tipo == "FUNCTION":
                self.funcao()
            elif tok.tipo == "EOF":
                break
            else:
                self._erro("'fn' ou fim do arquivo", tok)
                self._pular_ate_funcao()

    def funcao(self):
        # Funcao → fn NomeFuncao ( ListaParams ) TipoRetornoFuncao Bloco
        tok = self.token_atual()
        if tok.tipo != "FUNCTION":
            self._erro("'fn'", tok)
            self._pular_ate_funcao()
            return
        self.pos += 1                   # fn

        # NomeFuncao → ID | MAIN
        tok = self.token_atual()
        if tok.tipo in ("ID", "MAIN"):
            nome = tok.lexema
            self.pos += 1
        else:
            self._erro("identificador ou 'main'", tok)
            nome = "<erro>"

        # Cria uma nova tabela de símbolos para esta função
        self.tabela_atual = TabelaSimbolos(nome)
        self.tabelas.append(self.tabela_atual)

        self.match("LBRACKET")          # (
        self.lista_params()
        self.match("RBRACKET")          # )
        self.tipo_retorno_funcao()
        if self.modo_panico:
            self._sincronizar_cabecalho()
        self.bloco()

    # ---- Parâmetros ----------------------------------------------------

    def _inserir(self, entry: SimboloEntry, linha: int):
        """Insere na tabela atual; guarda redeclarações para a semântica."""
        if not self.tabela_atual.inserir(entry):
            self.redeclaracoes.append(
                (linha, entry.name, self.tabela_atual.nome_funcao))

    def lista_params(self):
        # ListaParams → ID : Type ListaParams2 | ε
        if self.token_atual().tipo == "ID":
            tok_id = self.match("ID")
            self.match("COLON")
            tipo = self.type_rule()
            self._inserir(SimboloEntry(
                name=tok_id.lexema, datatype=tipo,
                is_param=True, pos_param=0,
            ), tok_id.linha)
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
                self._inserir(SimboloEntry(
                    name=tok_id.lexema, datatype=tipo,
                    is_param=True, pos_param=pos,
                ), tok_id.linha)
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
        self._erro("'int', 'float' ou 'char'", tok)
        return DataType.ERROR

    # ---- Bloco / Sequência ---------------------------------------------

    def bloco(self):
        # Bloco → { Sequencia }
        if self.token_atual().tipo != "LBRACE":
            # Sem '{' não há bloco: reporta e não consome o '}' de quem o contém
            self._erro("'{'", self.token_atual())
            return
        self.match("LBRACE")            # {
        self.sequencia()
        self.match("RBRACE")            # }

    def sequencia(self):
        # Sequencia → Declaracao Sequencia | Comando Sequencia | ε
        #
        # Laço com recuperação: ao terminar cada item em modo pânico, os
        # tokens são descartados até um ponto seguro (_sincronizar_comando).
        while True:
            tok = self.token_atual()
            if tok.tipo in ("RBRACE", "EOF", "FUNCTION"):
                break                   # ε — fim da sequência

            pos_antes = self.pos

            if tok.tipo == "LET":
                self.declaracao()
            elif tok.tipo in _INICIO_COMANDO:
                self.comando()
            else:
                self._erro("comando ou '}'", tok)
                self.pos += 1           # garante progresso

            if self.modo_panico:
                self._sincronizar_comando()

            # Segurança: se nenhum token foi consumido, avança um
            if self.pos == pos_antes:
                self.pos += 1

    # ---- Declaração de variáveis ---------------------------------------

    def declaracao(self):
        # Declaracao → let VarList : Type ;
        self.match("LET")
        toks = self.var_list()
        self.match("COLON")
        tipo = self.type_rule()
        self.match("SEMICOLON")

        # Registra cada variável na tabela de símbolos
        for tk in toks:
            self._inserir(SimboloEntry(
                name=tk.lexema, datatype=tipo,
                is_param=False, pos_param=-1,
            ), tk.linha)

    def var_list(self) -> List[Token]:
        # VarList → ID VarList2
        toks: List[Token] = []
        tok = self.match("ID")
        if tok.tipo == "ID":
            toks.append(tok)
        self.var_list2(toks)
        return toks

    def var_list2(self, toks: List[Token]):
        # VarList2 → , ID VarList2 | ε
        if self.token_atual().tipo == "COMMA":
            self.match("COMMA")
            tok = self.match("ID")
            if tok.tipo == "ID":
                toks.append(tok)
            self.var_list2(toks)
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

        elif tok.tipo in ("IF", "LBRACE"):
            # ComandoSe → if ... | Bloco  (bloco solto é comando válido)
            self.comando_se()

        elif tok.tipo == "WHILE":
            self.match("WHILE")
            self.expr()
            self.bloco()

        elif tok.tipo == "PRINTLN":
            self.match("PRINTLN")

            # Registra println na tabela (sem FunctionRegister), antes dos
            # argumentos, na ordem do exemplo da especificação (seção 7.6)
            if self.tabela_atual.buscar("println") is None:
                self.tabela_atual.inserir(SimboloEntry(
                    name="println", datatype=DataType.VOID,
                    is_param=False, pos_param=-1,
                ))

            self.match("LBRACKET")          # (
            self.match("FMT_STRING")
            self.match("COMMA")
            self.lista_args()
            self.match("RBRACKET")          # )
            self.match("SEMICOLON")

        elif tok.tipo == "RETURN":
            self.match("RETURN")
            self.expr()
            self.match("SEMICOLON")

        else:
            self._erro("comando", tok)

    def atribuicao_ou_chamada(self, tok_id: Token):
        # AtribuicaoOuChamada → = Expr ; | ( ListaArgs ) ;
        tok = self.token_atual()

        if tok.tipo == "ASSIGN":
            self.match("ASSIGN")
            self.expr()
            self.match("SEMICOLON")

        elif tok.tipo == "LBRACKET":
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
        # ExprOpc → OpIgual Rel ExprOpc | ε     OpIgual → == | !=
        if self.token_atual().tipo in ("EQ", "NE"):
            self.pos += 1
            self.rel()
            self.expr_opc()

    def rel(self):
        # Rel → Adicao RelOpc
        self.adicao()
        self.rel_opc()

    def rel_opc(self):
        # RelOpc → OpRel Adicao RelOpc | ε      OpRel → < | <= | > | >=
        if self.token_atual().tipo in ("LT", "LE", "GT", "GE"):
            self.pos += 1
            self.adicao()
            self.rel_opc()

    def adicao(self):
        # Adicao → Termo AdicaoOpc
        self.termo()
        self.adicao_opc()

    def adicao_opc(self):
        # AdicaoOpc → OpAdicao Termo AdicaoOpc | ε     OpAdicao → + | -
        if self.token_atual().tipo in ("PLUS", "MINUS"):
            self.pos += 1
            self.termo()
            self.adicao_opc()

    def termo(self):
        # Termo → Fator TermoOpc
        self.fator()
        self.termo_opc()

    def termo_opc(self):
        # TermoOpc → OpMult Fator TermoOpc | ε         OpMult → * | /
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
            # Não consome: quem chamou decide (o modo pânico sincroniza)
            self._erro("expressão (identificador, constante ou '(')", tok)

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
            self._erro("argumento (identificador ou constante)", tok)
            return "<erro>"

    # ══════════════════════════════════════════════════════════════════════
    #  Tabela de símbolos — registro de chamadas de função
    # ══════════════════════════════════════════════════════════════════════

    def _registrar_chamada(self, nome: str, args: List[str]):
        """Cria um FunctionRegister e o associa ao símbolo na tabela atual."""
        fr = FunctionRegister(name=nome, num_args=len(args), args=args)

        entry = self.tabela_atual.buscar(nome)
        if entry is None:
            # Primeira ocorrência: cria entrada; o tipo é resolvido ao final
            # da análise (a função pode ser definida depois da chamada)
            entry = SimboloEntry(
                name=nome, datatype=DataType.VOID,
                is_param=False, pos_param=-1,
            )
            self.tabela_atual.inserir(entry)

        entry.call_refs.append(fr)

    def _resolver_tipos_chamadas(self):
        """Define o datatype dos símbolos de chamada como o ret_type da função
        chamada. Função não definida no programa fica com DataType.ERROR."""
        ret = {}
        for t in self.tabelas:
            ret.setdefault(t.nome_funcao, t.ret_type)   # 1ª definição vale
        for t in self.tabelas:
            for s in t.simbolos.values():
                if s.call_refs:
                    s.datatype = ret.get(s.name, DataType.ERROR)
