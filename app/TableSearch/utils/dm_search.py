from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.TablePakage.utils.router_utils import to_sql_name_lat


def build_dm_sql(
        table_name: str,
        schema_params: list[str],
        product_id: int,
) -> str:
    unions = []

    for param_name in schema_params:
        col = to_sql_name_lat(param_name)

        unions.append(f"""
            SELECT
                '{param_name}'::text AS param_name,
                array_agg(DISTINCT "{col}") FILTER (WHERE "{col}" IS NOT NULL) AS values,
                COUNT(*) AS matched_rows,
                NOW() AS updated_at
            FROM "{table_name}"
        """)

    union_sql = "\nUNION ALL\n".join(unions)

    return f"""
        CREATE TABLE IF NOT EXISTS dm_product_{product_id} AS
        {union_sql};
    """


async def ensure_dm_exists(
        db: AsyncSession,
        product_id: int,
        table_name: str,
        schema_params: list[str],
):
    # Проверяем существование
    exists = await db.execute(
        text("SELECT to_regclass(:name)"),
        {"name": f"dm_product_{product_id}"}
    )

    if exists.scalar():
        return

    # Создаём витрину
    create_sql = build_dm_sql(
        table_name=table_name,
        schema_params=schema_params,
        product_id=product_id,
    )

    await db.execute(text(create_sql))
    await db.commit()


async def get_full_search_from_dm(
        db: AsyncSession,
        product_id: int,
) -> tuple[dict, int]:
    result = await db.execute(text(f"""
        SELECT param_name, values, matched_rows
        FROM dm_product_{product_id}
    """))

    rows = result.fetchall()

    if not rows:
        return {}, 0

    parameters = {
        row.param_name: sorted(map(str, row.values))
        for row in rows
        if row.values
    }

    return parameters, rows[0].matched_rows
