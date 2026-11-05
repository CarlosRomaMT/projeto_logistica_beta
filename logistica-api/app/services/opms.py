from sqlalchemy import text

from app.core.config import ID_OPM_CONTINGENCIA, STATUS_OPM_ATIVA
from app.core.db import engine


def buscar_opms(termo: str = "", incluir_inativas: bool = False) -> list[dict]:
    """OPMs selecionáveis como destino. A OPM de contingência nunca é oferecida."""
    sql = """
        SELECT id_opm, nome, status FROM tb_opm
        WHERE id_opm <> :contingencia AND nome ILIKE :termo
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
