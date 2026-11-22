from dataclasses import dataclass, field
from enum import IntEnum
from typing import List, Optional


# ---------------------------------------------------------------------------
# Representação interna dos tipos 
# ---------------------------------------------------------------------------

class DataType(IntEnum):
    ERROR = -1
    INT   = 0
    FLOAT = 1
    CHAR  = 2
    VOID  = 3


# ---------------------------------------------------------------------------
# Registro de chamada de função 
# ---------------------------------------------------------------------------

@dataclass
class FunctionRegister:
    name: str               # lexema com o nome da função chamada
    num_args: int            # número de argumentos da chamada
    args: List[str]          # lexemas dos argumentos

    def __str__(self):
        return f"FuncReg(name={self.name}, num_args={self.num_args}, args={self.args})"


# ---------------------------------------------------------------------------
# Entrada da tabela de símbolos
# ---------------------------------------------------------------------------

@dataclass
class SimboloEntry:
    """Uma entrada (registro) na tabela de símbolos."""
    name: str                                               # nome da variável ou função
    datatype: DataType                                      # int, float, char (ou void/error)
    is_param: bool = False                         # é parâmetro?
    pos_param: int = -1                            # -1 = local; 0,1,2… = posição do parâmetro
    call_refs: List[FunctionRegister] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Tabela de símbolos — uma por função/escopo (seção 7.1)
# ---------------------------------------------------------------------------

class TabelaSimbolos:
    """Tabela de símbolos associada a uma função."""

    def __init__(self, nome_funcao: str, ret_type: DataType = DataType.VOID):
        self.nome_funcao = nome_funcao
        self.ret_type = ret_type
        self.simbolos: dict[str, SimboloEntry] = {}

    # ---- operações --------------------------------------------------------

    def inserir(self, entry: SimboloEntry) -> bool:
        """Insere um símbolo. Retorna False se já existia (redeclaração)."""
        if entry.name in self.simbolos:
            return False
        self.simbolos[entry.name] = entry
        return True

    def buscar(self, nome: str) -> Optional[SimboloEntry]:
        """Busca um símbolo pelo nome. Retorna None se não existir."""
        return self.simbolos.get(nome)

    # ---- impressão formatada (seção 17.4 — impressão organizada) ----------

    def formatar(self) -> str:
        linhas = []
        linhas.append(f"=== Tabela: {self.nome_funcao}  |  ret_type = {self.ret_type.name} ===")

        # Largura da coluna de nomes se ajusta ao maior identificador
        larg = max([len(k) for k in self.simbolos] + [len("Chave")]) + 2
        linhas.append(
            f"  {'Chave':<{larg}}{'Name':<{larg}}{'DataType':<10}"
            f"{'is_param':<10}{'pos_param':<11}call_refs"
        )
        linhas.append("  " + "-" * (2 * larg + 10 + 10 + 11 + 40))

        for chave, s in self.simbolos.items():
            if s.call_refs:
                refs = "; ".join(str(r) for r in s.call_refs)
            else:
                refs = "NULL"
            linhas.append(
                f"  {chave:<{larg}}{s.name:<{larg}}{s.datatype.name:<10}"
                f"{str(s.is_param):<10}{s.pos_param:<11}{refs}"
            )

        # FunctionRegisters detalhados
        todos_regs = [
            r
            for s in self.simbolos.values()
            for r in s.call_refs
        ]
        if todos_regs:
            linhas.append("")
            linhas.append("  Registros de chamadas de função:")
            for r in todos_regs:
                linhas.append(f"    {r}")

        return "\n".join(linhas)

    def __repr__(self):
        return self.formatar()
