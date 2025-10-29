## Run server
```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

## Ingest documents (in ./data)
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/ingest?collection=docs" -Method Post 
```

## Invoke questions
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/query" -Method Post -Body '{"query":"what section describes the watchdog timer?","top_k":4}' -ContentType "application/json"
```

## Reset DB
```powershell
Remove-Item -Recurse -Force .\chroma_db
```