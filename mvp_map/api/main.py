import os
import time
import uuid
from contextlib import asynccontextmanager
from typing import List, Optional

import psycopg2
import psycopg2.extras
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

DATABASE_URL = os.environ["DATABASE_URL"]


def get_conn():
    return psycopg2.connect(DATABASE_URL)


def init_db(retries: int = 10, delay: float = 2.0):
    sql = open("init.sql").read()
    for attempt in range(retries):
        try:
            conn = get_conn()
            with conn:
                with conn.cursor() as cur:
                    cur.execute(sql)
            conn.close()
            return
        except Exception as exc:
            if attempt == retries - 1:
                raise RuntimeError(f"DB init failed after {retries} attempts: {exc}") from exc
            time.sleep(delay)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request models ──────────────────────────────────────────────────────────

class ContiguousSegment(BaseModel):
    sequence_index: int
    route_name: Optional[str] = None
    ogc_fids: List[int]
    lts_perceived: Optional[int] = None
    safety_rating: Optional[int] = None
    stress_factors: Optional[List[str]] = None


class SurveySubmission(BaseModel):
    route_ogc_fids: List[int]
    contiguous_segments: List[ContiguousSegment]
    time_of_day: Optional[str] = None
    overall_satisfaction: Optional[int] = None
    would_ride_again: Optional[str] = None
    trip_purpose: Optional[str] = None
    comments: Optional[str] = None


# ── Endpoints ───────────────────────────────────────────────────────────────

@app.post("/api/submissions", status_code=201)
def create_submission(body: SurveySubmission):
    submission_id = str(uuid.uuid4())
    try:
        conn = get_conn()
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO survey_submissions
                        (submission_id, route_ogc_fids, time_of_day,
                         overall_satisfaction, would_ride_again, trip_purpose, comments)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        submission_id,
                        body.route_ogc_fids,
                        body.time_of_day,
                        body.overall_satisfaction,
                        body.would_ride_again,
                        body.trip_purpose,
                        body.comments,
                    ),
                )

                for seg in body.contiguous_segments:
                    seg_id = str(uuid.uuid4())
                    cur.execute(
                        """
                        INSERT INTO survey_contiguous_segments
                            (id, submission_id, sequence_index, route_name, ogc_fids,
                             lts_perceived, safety_rating, stress_factors)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            seg_id,
                            submission_id,
                            seg.sequence_index,
                            seg.route_name,
                            seg.ogc_fids,
                            seg.lts_perceived,
                            seg.safety_rating,
                            seg.stress_factors,
                        ),
                    )

                    for seq_idx, ogc_fid in enumerate(seg.ogc_fids):
                        cur.execute(
                            """
                            INSERT INTO survey_granular_segments
                                (submission_id, ogc_fid, contiguous_segment_id, sequence_index)
                            VALUES (%s, %s, %s, %s)
                            ON CONFLICT (submission_id, ogc_fid) DO NOTHING
                            """,
                            (submission_id, ogc_fid, seg_id, seq_idx),
                        )

        conn.close()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return {"submission_id": submission_id}


@app.get("/health")
def health():
    try:
        conn = get_conn()
        conn.close()
        return {"status": "ok"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))
