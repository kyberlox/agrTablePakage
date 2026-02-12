from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.TablePakage.utils.router_utils import to_sql_name_lat


async def rebuild_dm(
    db: AsyncSession,
    product_id: int,
    table_name: str,
    schema_params: list[str],
):
    await db.execute(text("SELECT pg_advisory_lock(:pid)"), {"pid": product_id})

    try:
        dm_table = f"dm_product_{product_id}"

        # 1️⃣ DROP отдельно
        await db.execute(text(f'DROP TABLE IF EXISTS "{dm_table}"'))

        # 2️⃣ CREATE отдельно
        union_queries = []

        for param in schema_params:
            union_queries.append(f"""
                SELECT
                    '{param}'::text AS param_name,
                    array_agg(DISTINCT "{param}")
                        FILTER (WHERE "{param}" IS NOT NULL) AS values,
                    COUNT(*) AS matched_rows
                FROM "{table_name}"
            """)

        final_sql = f"""
            CREATE TABLE "{dm_table}" AS
            {" UNION ALL ".join(union_queries)}
        """

        await db.execute(text(final_sql))

        dm_table = f"dm_product_{product_id}"

        await db.execute(text("""
            INSERT INTO datamart_registry (
                product_id,
                dm_table_name,
                is_dirty,
                updated_at
            )
            VALUES (
                :pid,
                :dm_table_name,
                FALSE,
                now()
            )
            ON CONFLICT (product_id)
            DO UPDATE
            SET is_dirty = FALSE,
                updated_at = now()
        """), {
            "pid": product_id,
            "dm_table_name": dm_table
        })

        await db.commit()

    finally:
        # unlock всегда в finally
        await db.execute(text("SELECT pg_advisory_unlock(:pid)"), {"pid": product_id})


async def ensure_dm_exists(
    db: AsyncSession,
    product_id: int,
    table_name: str,
    schema_params: list[str],
):
    registry = await db.execute(text("""
        SELECT is_dirty
        FROM datamart_registry
        WHERE product_id = :pid
    """), {"pid": product_id})

    row = registry.mappings().first()

    if not row:
        await rebuild_dm(db, product_id, table_name, schema_params)
        return

    if row["is_dirty"]:
        await rebuild_dm(db, product_id, table_name, schema_params)


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
                COUNT(*) AS matched_rows
            FROM "{table_name}"
        """)

    union_sql = "\nUNION ALL\n".join(unions)

    return f"""
        DROP TABLE IF EXISTS dm_product_{product_id};

        CREATE TABLE dm_product_{product_id} AS
        {union_sql};
    """


async def get_full_search_from_dm(
        db: AsyncSession,
        product_id: int,
) -> tuple[dict, int]:
    result = await db.execute(text(f"""
        SELECT param_name, values, matched_rows
        FROM dm_product_{product_id}
    """))

    rows = result.mappings().all()

    parameters = {
        row["param_name"]: sorted(map(str, row["values"]))
        for row in rows
        if row["values"]
    }

    return parameters, rows[0].matched_rows
