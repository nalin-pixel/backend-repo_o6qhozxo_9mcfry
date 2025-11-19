import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from bson import ObjectId

from database import db, create_document, get_documents

app = FastAPI(title="Racing UI Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Utilities
class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid objectid")
        return ObjectId(v)


def to_str_id(doc):
    if doc and "_id" in doc:
        doc["id"] = str(doc.pop("_id"))
    return doc


# Schemas endpoint (read from schemas.py for the viewer tooling)
@app.get("/schema")
async def schema_info():
    try:
        import schemas
        # Return minimal info: class names and fields
        def model_to_dict(model):
            return {
                "name": model.__name__,
                "fields": list(model.model_fields.keys()),
            }
        return {
            "models": [
                model_to_dict(schemas.Vehicle),
                model_to_dict(schemas.Map),
                model_to_dict(schemas.Race),
                model_to_dict(schemas.Entry),
            ]
        }
    except Exception as e:
        return {"error": str(e)}


# Public API models
class RaceCreate(BaseModel):
    map_code: str
    laps: int
    allowed_vehicle_codes: List[str] = []
    created_by: Optional[str] = None


# Seed some default vehicles/maps if empty
@app.post("/seed")
async def seed():
    if db is None:
        raise HTTPException(500, "Database not configured")
    counts = {
        "vehicle": db["vehicle"].count_documents({}),
        "map": db["map"].count_documents({}),
    }
    if counts["vehicle"] == 0:
        defaults = [
            {"name": "Zentorno", "code": "zentorno", "class_name": "Super", "is_enabled": True},
            {"name": "Elegy Retro", "code": "elegy", "class_name": "Sports", "is_enabled": True},
            {"name": "Comet SR", "code": "comet5", "class_name": "Sports", "is_enabled": True},
        ]
        db["vehicle"].insert_many(defaults)
    if counts["map"] == 0:
        maps = [
            {"name": "Downtown Dash", "code": "downtown_dash", "author": "Flames", "is_enabled": True},
            {"name": "Vinewood Loop", "code": "vinewood_loop", "author": "Flames", "is_enabled": True},
            {"name": "Airport Circuit", "code": "airport_circuit", "author": "Flames", "is_enabled": True},
        ]
        db["map"].insert_many(maps)
    return {"status": "ok", "seeded": True}


@app.get("/maps")
async def get_maps():
    if db is None:
        raise HTTPException(500, "Database not configured")
    maps = [to_str_id(m) for m in db["map"].find({"is_enabled": True})]
    return maps


@app.get("/vehicles")
async def get_vehicles():
    if db is None:
        raise HTTPException(500, "Database not configured")
    vehicles = [to_str_id(v) for v in db["vehicle"].find({"is_enabled": True})]
    return vehicles


@app.post("/races")
async def create_race(payload: RaceCreate):
    if db is None:
        raise HTTPException(500, "Database not configured")
    race_doc = payload.model_dump()
    race_doc.update({"status": "pending"})
    race_id = db["race"].insert_one(race_doc).inserted_id
    return {"id": str(race_id)}


@app.get("/races")
async def list_races():
    if db is None:
        raise HTTPException(500, "Database not configured")
    races = [to_str_id(r) for r in db["race"].find({}).sort("_id", -1).limit(50)]
    return races


@app.get("/leaderboard/{race_id}")
async def get_leaderboard(race_id: str):
    if db is None:
        raise HTTPException(500, "Database not configured")
    try:
        oid = ObjectId(race_id)
    except Exception:
        raise HTTPException(400, "Invalid race id")
    entries = list(db["entry"].find({"race_id": race_id}))
    # Sort by total_time_ms asc, then best_lap_ms
    entries.sort(key=lambda e: (e.get("total_time_ms", 1e12), e.get("best_lap_ms", 1e12)))
    # Assign positions
    for idx, e in enumerate(entries, start=1):
        e["position"] = idx
    return [to_str_id(e) for e in entries]


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name
            response["connection_status"] = "Connected"
            collections = db.list_collection_names()
            response["collections"] = collections[:10]
            response["database"] = "✅ Connected & Working"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response


@app.get("/")
async def root():
    return {"message": "Racing UI Backend Ready"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
