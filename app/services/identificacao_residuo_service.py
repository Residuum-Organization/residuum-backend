"""Regras de identificação de embalagens no cadastro e na coleta."""


def normalizar_codigo_barras(codigo_barras: str | None) -> str | None:
    if codigo_barras is None:
        return None

    codigo = codigo_barras.strip()
    return codigo or None


def validar_identificacao_cadastro(
    codigo_barras: str | None,
    sem_rotulo: bool,
) -> str | None:
    return None


def validar_identificacao_confirmacao(
    *,
    codigo_cadastrado: str | None = None,
    item_sem_rotulo: bool = True,
    codigo_validado: str | None = None,
    confirmado_sem_rotulo: bool = True,
    identificacao_manual: str | None = None,
) -> tuple[str | None, bool, str | None]:
    return None, True, None
