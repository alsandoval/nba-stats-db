"""
routes_arrow.py - High-Throughput Apache Arrow IPC Streaming Endpoints.

Streams binary Arrow IPC RecordBatch streams directly from DuckDB / Parquet
for zero-copy analytical consumption:
    Content-Type: application/vnd.apache.arrow.stream
"""

import io
from fastapi import APIRouter, HTTPException, Query, Response
import pyarrow as pa
import pyarrow.ipc as ipc

from ..possession.olap import DuckDBPossessionEngine

router = APIRouter(prefix="/api/arrow", tags=["Arrow IPC"])

_engine = DuckDBPossessionEngine(parquet_dir="data/gold/possessions")


@router.get("/possessions")
def stream_possessions_arrow(
    season: str = Query(default="2023-24"),
    limit: int = Query(default=1000, ge=1, le=100000),
) -> Response:
    """
    Streams zero-copy binary Apache Arrow RecordBatches for possession tables.
    MediaType: application/vnd.apache.arrow.stream
    """
    try:
        parquet_path = f"data/gold/possessions/season={season}/*.parquet"
        arrow_table = _engine.conn.execute(
            f"SELECT * FROM read_parquet('{parquet_path}') LIMIT {limit}"
        ).to_arrow_table()

        sink = io.BytesIO()
        with ipc.new_stream(sink, arrow_table.schema) as writer:
            writer.write_table(arrow_table)

        sink.seek(0)
        return Response(
            content=sink.getvalue(),
            media_type="application/vnd.apache.arrow.stream",
            headers={
                "Content-Disposition": f"attachment; filename=possessions_{season}.arrow",
                "X-Record-Count": str(len(arrow_table)),
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Arrow serialization failed: {str(e)}")


@router.get("/stints")
def stream_stints_arrow(
    season: str = Query(default="2023-24"),
) -> Response:
    """Streams compressed lineup stints in Apache Arrow binary format."""
    try:
        stints = _engine.extract_lineup_stints(season)
        if not stints:
            # Empty table fallback schema
            arrow_table = pa.Table.from_arrays(
                [pa.array([], type=pa.string()), pa.array([], type=pa.int64())],
                names=["game_id", "possessions"],
            )
        else:
            arrow_table = pa.Table.from_pylist(stints)

        sink = io.BytesIO()
        with ipc.new_stream(sink, arrow_table.schema) as writer:
            writer.write_table(arrow_table)

        sink.seek(0)
        return Response(
            content=sink.getvalue(),
            media_type="application/vnd.apache.arrow.stream",
            headers={"Content-Disposition": f"attachment; filename=stints_{season}.arrow"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Arrow stints streaming failed: {str(e)}")
