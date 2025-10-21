import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any


class SoilMoistureModel:
    """
    Advanced soil moisture model based on environmental factors
    Implements simplified water balance equation
    """

    def __init__(self):
        self.soil_types = {
            "sand": {"field_capacity": 25, "wilting_point": 5, "k_sat": 100},
            "loam": {"field_capacity": 35, "wilting_point": 10, "k_sat": 25},
            "clay": {"field_capacity": 45, "wilting_point": 20, "k_sat": 5},
            "clay_loam": {"field_capacity": 40, "wilting_point": 15, "k_sat": 15}
        }

    def calculate_soil_moisture(self,
                                current_moisture: float,
                                soil_type: str,
                                temperature: float,
                                humidity: float,
                                precipitation: float,
                                solar_radiation: float,
                                wind_speed: float,
                                hours: int = 1) -> float:
        """
        Calculate soil moisture change over time using water balance
        """
        soil_params = self.soil_types.get(soil_type, self.soil_types["loam"])

        # Evapotranspiration (simplified)
        et = self._calculate_et(temperature, humidity, solar_radiation, wind_speed)

        # Infiltration from precipitation
        infiltration = precipitation * 0.6  # 60% of rain infiltrates

        # Deep percolation (water moving below root zone)
        percolation = max(0, (current_moisture - soil_params["field_capacity"]) * 0.1)

        # Calculate new moisture
        moisture_change = infiltration - et - percolation
        new_moisture = current_moisture + moisture_change

        # Ensure moisture stays within physical limits
        new_moisture = max(soil_params["wilting_point"],
                           min(soil_params["field_capacity"], new_moisture))

        return new_moisture

    def _calculate_et(self, temperature: float, humidity: float,
                      solar_radiation: float, wind_speed: float) -> float:
        """
        Calculate evapotranspiration using simplified method
        """
        # Reference evapotranspiration (simplified)
        et_ref = (0.0023 * (temperature + 17.8) *
                  (solar_radiation ** 0.5) *
                  (max(0.3, (100 - humidity) / 100)))

        # Adjust for wind
        wind_factor = 1 + (wind_speed * 0.05)

        return et_ref * wind_factor * 0.5  # Reduced for simulation

    def predict_irrigation_need(self, current_moisture: float, soil_type: str,
                                crop_type: str, weather_forecast: Dict) -> Dict[str, Any]:
        """
        Predict irrigation needs based on current conditions and forecast
        """
        soil_params = self.soil_types.get(soil_type, self.soil_types["loam"])

        # Crop coefficients (water needs)
        crop_coefficients = {
            "vegetables": 1.0,
            "flowers": 0.8,
            "fruits": 1.2,
            "grains": 0.9
        }

        crop_factor = crop_coefficients.get(crop_type, 1.0)

        # Calculate optimal moisture range
        optimal_min = soil_params["wilting_point"] + 20
        optimal_max = soil_params["field_capacity"] - 5

        # Determine irrigation need
        moisture_deficit = optimal_min - current_moisture
        needs_irrigation = moisture_deficit > 5

        # Calculate suggested irrigation amount
        irrigation_amount = max(0, moisture_deficit * 2) if needs_irrigation else 0

        return {
            "needs_irrigation": needs_irrigation,
            "moisture_deficit": max(0, moisture_deficit),
            "suggested_irrigation": irrigation_amount,
            "optimal_range": (optimal_min, optimal_max),
            "current_status": "optimal" if optimal_min <= current_moisture <= optimal_max else "needs_attention"
        }