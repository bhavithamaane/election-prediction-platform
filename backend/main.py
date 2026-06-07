import os
import sys
import jwt
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List
from fastapi import FastAPI, Depends, HTTPException, status, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Add parent directory to path so we can import database and ml_model
# Path adjustment removed; imports use package context

from backend.database import get_db_conn, row_to_dict
from backend.ml_model import ElectionPredictionEngine, REGION_BASELINES
from backend.seed_data import hash_password
from backend.social_scraper import get_realtime_social_scores, get_scores_simple

app = FastAPI(title="Karnataka VoteCast - Election Prediction Platform API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# JWT Secret and Configuration
JWT_SECRET = os.getenv("JWT_SECRET", "election_prediction_super_secret_key_8492")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# Instantiate prediction engine
predictor = ElectionPredictionEngine()

# Default social media popularity scores
DEFAULT_SOCIAL_POPULARITY = {"BJP": 46.0, "INC": 44.0, "JD(S)": 7.0, "Others": 3.0}

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        return payload
    except jwt.PyJWTError:
        raise credentials_exception

def get_social_popularity():
    """
    Fetch real-time social media popularity scores (Google Trends + News Sentiment).
    Falls back to DB-stored scores, then to hardcoded defaults.
    """
    try:
        scores = get_scores_simple()
        if scores:
            return scores
    except Exception as e:
        logger.warning(f"Real-time social scraper failed: {e}. Falling back to DB.")

    # Fallback: DB-stored scores
    try:
        with get_db_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT PartyID, AVG(Score) as AvgScore FROM social_popularity GROUP BY PartyID;")
            rows = cursor.fetchall()
            if rows:
                result = {}
                for r in rows:
                    row_dict = row_to_dict(r)
                    result[row_dict["PartyID"]] = round(row_dict["AvgScore"], 2)
                return result
    except Exception:
        pass

    return DEFAULT_SOCIAL_POPULARITY

# --- API Endpoints ---

@app.get("/api/prediction/national")
def get_national_prediction():
    """
    Returns aggregated Karnataka state predicted seats, vote shares, and confidence.
    Uses default social popularity + default user inputs (based on historical).
    """
    try:
        social = get_social_popularity()
        inputs = {
            "social_popularity": social,
            "user_percentages": social.copy()  # Default user input mirrors social
        }
        res = predictor.predict_national(inputs)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/prediction/region/{region_name}")
def get_region_prediction(region_name: str):
    """
    Returns predicted seats and vote share for a specific Karnataka region.
    """
    try:
        social = get_social_popularity()
        inputs = {
            "social_popularity": social,
            "user_percentages": social.copy()
        }
        res = predictor.predict_state(region_name, inputs)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Keep backward compat
@app.get("/api/prediction/state/{state_name}")
def get_state_prediction(state_name: str):
    """Alias for region prediction."""
    return get_region_prediction(state_name)

@app.post("/api/prediction/simulate")
def simulate_prediction(payload: Dict[str, Any]):
    """
    Simulates predictions based on user-provided expected winning percentages
    and social popularity scores.
    Payload: { "user_percentages": {"BJP": 46, ...}, "social_popularity": {"BJP": 46, ...} }
    """
    try:
        inputs = {
            "user_percentages": payload.get("user_percentages", DEFAULT_SOCIAL_POPULARITY),
            "social_popularity": payload.get("social_popularity", get_social_popularity())
        }
        res = predictor.predict_national(inputs)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/social/realtime")
def get_realtime_social_endpoint(force_refresh: bool = False):
    """
    Returns live real-time social media popularity scores for Karnataka parties.
    Sources: Google Trends (IN-KA) + Google News RSS sentiment analysis.
    Results are cached for 15 minutes; pass ?force_refresh=true to bust cache.
    """
    try:
        data = get_realtime_social_scores(force_refresh=force_refresh)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/social/popularity")
def get_social_popularity_endpoint():
    """
    Returns current social media popularity scores (alias for /api/social/realtime).
    """
    try:
        data = get_realtime_social_scores()
        return {
            "aggregate": data.get("scores", {}),
            "sources": data.get("sources", []),
            "fetched_at": data.get("fetched_at"),
            "cached": data.get("cached", False)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/historical")
def get_historical_results():
    """
    Returns historical results for charts (2014, 2019, 2024) - Karnataka.
    """
    try:
        with get_db_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM historical_results;")
            rows = cursor.fetchall()
            
            res_list = []
            for r in rows:
                row_dict = row_to_dict(r)
                res_list.append({
                    "ResultID": row_dict["ResultID"],
                    "Year": row_dict["Year"],
                    "State": row_dict["State"],
                    "PartyID": row_dict["PartyID"],
                    "VoteShare": round(row_dict["VoteShare"] * 100, 2),
                    "SeatsWon": row_dict["SeatsWon"]
                })
            return res_list
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/polls")
def get_opinion_polls():
    """
    Returns historical and current opinion polls (Karnataka).
    """
    try:
        with get_db_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM polls ORDER BY Date DESC;")
            rows = cursor.fetchall()
            
            poll_list = []
            for r in rows:
                row_dict = row_to_dict(r)
                # Parse JSON string stored in column
                shares = json.loads(row_dict["PartyVoteShare"])
                poll_list.append({
                    "PollID": row_dict["PollID"],
                    "Agency": row_dict["Agency"],
                    "Date": row_dict["Date"],
                    "SampleSize": row_dict["SampleSize"],
                    "PartyVoteShare": shares
                })
            return poll_list
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/admin/login")
def admin_login(payload: Dict[str, str]):
    """
    Authenticates admin users.
    """
    email = payload.get("email")
    password = payload.get("password")
    
    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password required")
        
    with get_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE Email = ?;", (email,))
        row = cursor.fetchone()
        
        if not row:
            raise HTTPException(status_code=401, detail="Invalid email or password")
            
        user = row_to_dict(row)
        if user["PasswordHash"] != hash_password(password):
            raise HTTPException(status_code=401, detail="Invalid email or password")
            
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user["Email"], "role": user["Role"], "name": user["Name"]}, 
            expires_delta=access_token_expires
        )
        return {"access_token": access_token, "token_type": "bearer", "role": user["Role"], "name": user["Name"]}

@app.post("/api/admin/polls/upload")
async def upload_poll(
    agency: str = Form(...),
    sample_size: int = Form(...),
    date: str = Form(...),
    bjp: float = Form(...),
    inc: float = Form(...),
    others: float = Form(...),
    jds: float = Form(0.0),
    token: str = Form(...)
):
    """
    Uploads new poll data (analyst/admin only) - Karnataka parties.
    """
    try:
        # Verify token
        payload = verify_token(token)
        user_email = payload.get("sub")
        user_role = payload.get("role")
        
        if user_role not in ["Admin", "Analyst"]:
            raise HTTPException(status_code=403, detail="Not authorized")
            
        party_shares = {
            "BJP": round(bjp / 100.0, 4),
            "INC": round(inc / 100.0, 4),
            "JD(S)": round(jds / 100.0, 4),
            "Others": round(others / 100.0, 4)
        }
            
        # Ensure shares sum up close to 1.0
        tot = sum(party_shares.values())
        if abs(tot - 1.0) > 0.05:
            # Normalize to 1.0
            for k in party_shares:
                party_shares[k] = round(party_shares[k] / tot, 4)
                
        # Insert into sqlite3
        with get_db_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO polls (Agency, Date, SampleSize, PartyVoteShare) VALUES (?, ?, ?, ?);",
                (agency, date, sample_size, json.dumps(party_shares))
            )
            conn.commit()
            
        return {"status": "success", "message": "Poll uploaded successfully"}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/admin/model/retrain")
def retrain_model(token: str):
    """
    Triggers prediction model retraining using database results.
    """
    try:
        # Verify token
        payload = verify_token(token)
        user_role = payload.get("role")
        
        if user_role != "Admin":
            raise HTTPException(status_code=403, detail="Only admins can trigger model training")
            
        # Gather all historical results
        with get_db_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM historical_results;")
            rows = cursor.fetchall()
            
            data = []
            for r in rows:
                row_dict = row_to_dict(r)
                data.append({
                    "Year": row_dict["Year"],
                    "State": row_dict["State"],
                    "PartyID": row_dict["PartyID"],
                    "VoteShare": row_dict["VoteShare"],
                    "SeatsWon": row_dict["SeatsWon"]
                })
            
        success = predictor.train(data)
        if success:
            return {"status": "success", "message": "Model retrained successfully with Karnataka historical data"}
        else:
            return {"status": "partial", "message": "Model retrained using analytical fallbacks"}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Serve frontend static assets
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
else:
    print(f"Frontend directory '{frontend_dir}' does not exist. Serving only API endpoints.")
