"""CMOTS-alt API — FastAPI orchestration layer over the data pipelines.

    python -m cmots_alt.api        # run dev server (uvicorn)
    cmots_alt.api.main:app         # ASGI app for uvicorn/gunicorn

Folder layout:
    config.py        API settings (CMOTS_API_* env)
    main.py          app factory + middleware + router wiring
    dependencies.py  shared deps / scaffold helpers
    pipelines.py     pipeline registry (name -> gold domain / run path)
    routers/         system, admin, stocks, mutual_funds, scheduler
    schemas/         pydantic response models
    services/        gold-output access (path resolution now; reads next)
"""
