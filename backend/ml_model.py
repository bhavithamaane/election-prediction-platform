import logging
import math
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

# Fallback check for ML libraries
try:
    import pandas as pd
    import numpy as np
    from sklearn.ensemble import RandomForestRegressor
    HAS_ML_LIBS = True
except ImportError:
    HAS_ML_LIBS = False
    logger.warning("ML libraries (pandas, numpy, scikit-learn) not fully available. Using custom political science swing engine.")

# Karnataka Region-wise historical baseline data (2024 results)
# Format: Region -> { total_seats, party_vote_shares, party_seats }
REGION_BASELINES = {
    "Bengaluru": {
        "seats": 4,
        "vote_share": {"BJP": 0.550, "INC": 0.400, "JD(S)": 0.020, "Others": 0.030},
        "seats_won": {"BJP": 4, "INC": 0, "JD(S)": 0, "Others": 0}
    },
    "Old Mysore": {
        "seats": 7,
        "vote_share": {"BJP": 0.250, "INC": 0.480, "JD(S)": 0.220, "Others": 0.050},
        "seats_won": {"BJP": 1, "INC": 4, "JD(S)": 2, "Others": 0}
    },
    "Coastal Karnataka": {
        "seats": 3,
        "vote_share": {"BJP": 0.600, "INC": 0.350, "JD(S)": 0.010, "Others": 0.040},
        "seats_won": {"BJP": 3, "INC": 0, "JD(S)": 0, "Others": 0}
    },
    "Kittur Karnataka": {
        "seats": 6,
        "vote_share": {"BJP": 0.520, "INC": 0.430, "JD(S)": 0.010, "Others": 0.040},
        "seats_won": {"BJP": 4, "INC": 2, "JD(S)": 0, "Others": 0}
    },
    "Kalyana Karnataka": {
        "seats": 5,
        "vote_share": {"BJP": 0.450, "INC": 0.500, "JD(S)": 0.010, "Others": 0.040},
        "seats_won": {"BJP": 2, "INC": 3, "JD(S)": 0, "Others": 0}
    },
    "Central Karnataka": {
        "seats": 3,
        "vote_share": {"BJP": 0.540, "INC": 0.420, "JD(S)": 0.010, "Others": 0.030},
        "seats_won": {"BJP": 3, "INC": 0, "JD(S)": 0, "Others": 0}
    }
}

class ElectionPredictionEngine:
    def __init__(self):
        # We can store a trained random forest model if HAS_ML_LIBS is True
        self.rf_model = None
        self.is_trained = False
        
    def train(self, historical_data: List[Dict[str, Any]]):
        """
        Trains the ML model based on historical results and poll swings.
        """
        if not HAS_ML_LIBS or not historical_data:
            self.is_trained = True
            logger.info("Custom prediction engine active (no ML training required).")
            return True
            
        try:
            # Feature engineering: Create feature vectors
            # Features: Historical Year, State ID (Encoded), Previous Vote Share, Previous Seats
            records = []
            for item in historical_data:
                records.append({
                    "Year": item.get("Year"),
                    "VoteShare": item.get("VoteShare"),
                    "SeatsWon": item.get("SeatsWon")
                })
            
            df = pd.DataFrame(records)
            if len(df) < 5:
                self.is_trained = True
                return True
                
            # Basic training setup
            X = df[["Year", "VoteShare"]]
            y = df["SeatsWon"]
            
            self.rf_model = RandomForestRegressor(n_estimators=50, random_state=42)
            self.rf_model.fit(X, y)
            self.is_trained = True
            logger.info("Random Forest Regressor trained successfully.")
            return True
        except Exception as e:
            logger.error(f"Error training model: {e}. Falling back to swing engine.")
            self.is_trained = True
            return False

    def predict_state(self, region_name: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Predicts vote shares and seat distribution for a given region.
        inputs expected: 
        - user_percentages: Dict[str, float] (0 to 100)
        - social_popularity: Dict[str, float] (0 to 100)
        """
        if region_name not in REGION_BASELINES:
            # Fallback to general baseline
            region_name = "Bengaluru"
            
        baseline = REGION_BASELINES[region_name]
        total_seats = baseline["seats"]
        historical_shares = baseline["vote_share"].copy()
        
        user_pcts = inputs.get("user_percentages", {})
        social_pop = inputs.get("social_popularity", {})
        
        # New formula: 40% History, 30% Social, 30% User Input
        # Normalize social and user to fractions
        adjusted_shares = {}
        for party in historical_shares.keys():
            hist_w = historical_shares[party]
            social_w = social_pop.get(party, hist_w * 100) / 100.0
            user_w = user_pcts.get(party, hist_w * 100) / 100.0
            
            final_share = (0.40 * hist_w) + (0.30 * social_w) + (0.30 * user_w)
            adjusted_shares[party] = max(0.01, final_share)
            
        # Renormalize to ensure mathematical certainty of summing to 1.0
        total_sum = sum(adjusted_shares.values())
        for p in adjusted_shares:
            adjusted_shares[p] = adjusted_shares[p] / total_sum

        # Seat Allocation using the Cube Law / First-Past-The-Post swing model
        # SeatShare_p = VoteShare_p^k / Sum(VoteShare_q^k)
        # We'll use k=3.0 (Cube Law) to amplify leading party seat share
        k = 2.8
        shares_raised = {p: math.pow(v, k) for p, v in adjusted_shares.items()}
        sum_raised = sum(shares_raised.values())
        
        predicted_seats = {}
        remaining_seats = total_seats
        
        # First pass allocation (integer seats)
        for p in adjusted_shares:
            seat_share = shares_raised[p] / sum_raised if sum_raised > 0 else 0
            allocated = int(seat_share * total_seats)
            predicted_seats[p] = allocated
            remaining_seats -= allocated
            
        # Distribute remaining seats to the parties with the highest decimal remainder
        if remaining_seats > 0:
            remainders = []
            for p in adjusted_shares:
                seat_share = shares_raised[p] / sum_raised if sum_raised > 0 else 0
                decimal_part = (seat_share * total_seats) - predicted_seats[p]
                remainders.append((p, decimal_part))
            remainders.sort(key=lambda x: x[1], reverse=True)
            for i in range(remaining_seats):
                p = remainders[i][0]
                predicted_seats[p] += 1

        # Determine winner
        winner = max(predicted_seats, key=predicted_seats.get)
        
        # Calculate Confidence Score based on margin of victory and poll sample size
        # If winner has a huge margin, confidence is higher
        sorted_seats = sorted(predicted_seats.values(), reverse=True)
        margin = (sorted_seats[0] - sorted_seats[1]) / total_seats if len(sorted_seats) > 1 else 1.0
        
        # Base confidence is proportional to margin, capped at 95% and floored at 55%
        confidence = 0.55 + (margin * 0.40)
        confidence = min(0.95, max(0.55, confidence))

        return {
            "state": region_name,
            "total_seats": total_seats,
            "vote_shares": {p: round(v * 100, 2) for p, v in adjusted_shares.items()},
            "seats": predicted_seats,
            "winner": winner,
            "confidence": round(confidence * 100, 2)
        }

    def predict_national(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Aggregates region predictions into a state prediction (Karnataka)
        """
        state_seats = {}
        state_vote_shares = {}
        total_state_seats = 28
        
        # Run prediction for each region
        region_results = []
        for region_name in REGION_BASELINES.keys():
            res = self.predict_state(region_name, inputs)
            region_results.append(res)
            
            # Aggregate seats
            for party, seats in res["seats"].items():
                state_seats[party] = state_seats.get(party, 0) + seats
                
        # Calculate state weighted vote shares
        total_weight = 0
        party_weighted_shares = {}
        for region_name, baseline in REGION_BASELINES.items():
            seats_weight = baseline["seats"]
            region_res = next(r for r in region_results if r["state"] == region_name)
            for party, share in region_res["vote_shares"].items():
                party_weighted_shares[party] = party_weighted_shares.get(party, 0.0) + (share * seats_weight)
            total_weight += seats_weight
            
        for party, weighted_sum in party_weighted_shares.items():
            state_vote_shares[party] = round(weighted_sum / total_weight, 2)

        # Determine state winner
        winner = max(state_seats, key=state_seats.get)
        
        # State Confidence: Average of region confidences weighted by seats
        avg_confidence = sum(r["confidence"] * r["total_seats"] for r in region_results) / total_weight

        return {
            "total_seats": total_state_seats,
            "seats": state_seats,
            "vote_shares": state_vote_shares,
            "winner": winner,
            "confidence": round(avg_confidence, 2),
            "state_wise": region_results
        }
