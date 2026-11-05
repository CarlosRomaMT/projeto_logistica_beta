from sqlalchemy import text

from app.core.config import ID_OPM_CONTINGENCIA, STATUS_OPM_ATIVA
from app.core.db import engine


# Remove acentos no próprio SQL (sem depender da extensão unaccent).
_COM_ACENTO = "áàâãäéèêëíìîïóòôõöúùûüçÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇºª"
_SEM_ACENTO = "aaaaaeeeeiiiiooooouuuucAAAAAEEEEIIIIOOOOOUUUUCoa"
_SEM_ACENTO_SQL = f"translate({{}}, '{_COM_ACENTO}', '{_SEM_ACENTO}')"


def buscar_opms(termo: str = "", incluir_inativas: bool = False) -> list[dict]:
    """OPMs selecionáveis como destino. A OPM de contingência nunca é oferecida.

    A busca ignora acentos e maiúsculas e considera também a abreviatura ("Trânsito" acha TRANSITO).
    """
    nome, abreviatura = _SEM_ACENTO_SQL.format("nome"), _SEM_ACENTO_SQL.format("coalesce(abreviatura, '')")
    termo_sql = _SEM_ACENTO_SQL.format(":termo")
    sql = f"""
        SELECT id_opm, nome, status FROM tb_opm
        WHERE id_opm <> :contingencia AND ({nome} ILIKE {termo_sql} OR {abreviatura} ILIKE {termo_sql})
    """
    if not incluir_inativas:
        sql += " AND status = :ativa"
    with engine.connect() as conn:
        linhas = conn.execute(
            text(sql + " ORDER BY nome LIMIT 20"),
            {"contingencia": ID_OPM_CONTINGENCIA, "termo": f"%{termo}%",
             "ativa": STATUS_OPM_ATIVA},
        ).mappings()
        return [dict(linha) for linha in linhas]
