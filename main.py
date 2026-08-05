"""
Entry point. Run with `python main.py` for local dev (uvicorn), or import
`app` from api.routes for deployment.
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run("api.routes:app", host="0.0.0.0", port=8000, reload=True)
