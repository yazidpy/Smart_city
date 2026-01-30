import numpy as np
from typing import List, Dict, Any, Tuple

def compute_traffic_state(counts: Dict[str, int]) -> str:
    """
    Heuristic to compute traffic state: 'fluid', 'moderate', 'saturated'
    """
    # Weighted vehicle count (cars, buses, trucks, motorcycles)
    vehicle_weight = {
        "Car": 1.0,
        "Bus": 2.5,
        "Truck": 2.0,
        "Motorcycle": 0.5,
        "Bicycle": 0.3,
        "Person": 0.2
    }
    score = sum(counts.get(cls, 0) * vehicle_weight.get(cls, 0) for cls in counts)
    total_score = score
    # Thresholds (tune based on real data)
    if total_score < 5:
        return "fluid"
    elif total_score < 15:
        return "moderate"
    else:
        return "saturated"
