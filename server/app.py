from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel
from rag_utils import ingest_dir, search, answer_with_rag, COLLECTION, DATA_DIR

app = FastAPI(default_response_class=ORJSONResponse)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryReq(BaseModel):
    query: str
    top_k: int = 4
    collection: str | None = None


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ingest")
def ingest(collection: str = Query(COLLECTION)):
    try:
        n_files, n_chunks = ingest_dir(DATA_DIR, collection)
        return {"collection": collection, "files": n_files, "chunks": n_chunks}
    except Exception as e:
        # temporary: surface root cause
        return ORJSONResponse({"error": str(e)}, status_code=500)


@app.post("/query")
def query(req: QueryReq):
    col = req.collection or COLLECTION
    ctxs = search(req.query, req.top_k, col)
    ans, used = answer_with_rag(req.query, ctxs)
    return {"answer": ans, "contexts": used}
