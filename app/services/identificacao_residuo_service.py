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
    codigo = normalizar_codigo_barras(codigo_barras)

    if sem_rotulo and codigo:
        raise ValueError("Uma embalagem sem rótulo não pode ter código de barras.")
    if not sem_rotulo and not codigo:
        raise ValueError("Informe o código de barras ou marque a embalagem como sem rótulo.")

    return codigo


def validar_identificacao_confirmacao(
    *,
    codigo_cadastrado: str | None,
    item_sem_rotulo: bool,
    codigo_validado: str | None,
    confirmado_sem_rotulo: bool,
    identificacao_manual: str | None,
) -> tuple[str | None, bool, str | None]:
    codigo_lido = normalizar_codigo_barras(codigo_validado)
    descricao_manual = (identificacao_manual or "").strip() or None

    if item_sem_rotulo:
        if not confirmado_sem_rotulo:
            raise ValueError("Confirme que a embalagem está sem rótulo.")
        if codigo_lido:
            raise ValueError("Não informe código de barras para uma embalagem sem rótulo.")
        if not descricao_manual:
            raise ValueError("Descreva manualmente o produto sem rótulo.")
        return None, True, descricao_manual

    codigo_esperado = normalizar_codigo_barras(codigo_cadastrado)
    if confirmado_sem_rotulo:
        raise ValueError("Este item foi cadastrado com código de barras.")
    if not codigo_lido:
        raise ValueError("Escaneie o código de barras antes de confirmar o descarte.")
    if codigo_lido != codigo_esperado:
        raise ValueError("O código de barras lido não corresponde ao item cadastrado.")
    if descricao_manual:
        raise ValueError("A identificação manual só é permitida para embalagens sem rótulo.")

    return codigo_lido, False, None
