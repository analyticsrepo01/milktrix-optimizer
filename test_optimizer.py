import sys
import os
from typing import Dict, Any, List

# Add backend directory to path so we can import services
sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))

from app.services.optimizer import run_milktrix_optimization

# Setup standard mock test datasets
SUPPLY_DATA = [
    { "region": "North", "volume": 500000, "fat": 4.2, "protein": 3.4, "lactose": 4.8 },
    { "region": "South", "volume": 400000, "fat": 4.0, "protein": 3.2, "lactose": 4.7 }
]

PLANT_DATA = [
    { "plant": "Auckland", "capacity": 800000, "fixed_cost": 15000 },
    { "plant": "Hamilton", "capacity": 600000, "fixed_cost": 12000 }
]

PRODUCT_DATA = [
    { "product": "WMP", "price": 3200, "production_cost": 400, "bom_fat": 260, "bom_protein": 250, "bom_lactose": 380 },
    { "product": "Butter", "price": 5200, "production_cost": 500, "bom_fat": 820, "bom_protein": 10, "bom_lactose": 10 }
]

LOGISTICS_DATA = [
    { "region": "North", "plant": "Auckland", "cost": 0.02 },
    { "region": "North", "plant": "Hamilton", "cost": 0.04 },
    { "region": "South", "plant": "Auckland", "cost": 0.05 },
    { "region": "South", "plant": "Hamilton", "cost": 0.03 }
]

GLOBAL_CONSTRAINTS = {
    "milk_base_price": 0.45
}

def test_feasible_case():
    print("🧪 Running Test Case 1: Feasible Baseline Inputs...")
    
    # Realistic small committed demands
    demand_data = [
        { "plant": "Auckland", "product": "WMP", "committed": 10, "optional": 200 },
        { "plant": "Auckland", "product": "Butter", "committed": 5, "optional": 100 }
    ]
    
    results = run_milktrix_optimization(
        supply_data=SUPPLY_DATA,
        plant_data=PLANT_DATA,
        product_data=PRODUCT_DATA,
        demand_data=demand_data,
        logistics_data=LOGISTICS_DATA,
        global_constraints=GLOBAL_CONSTRAINTS
    )
    
    status = results.get("status")
    print(f"   - Solver Status: {status}")
    print(f"   - Variable Contribution Margin (VCM): ${results.get('vcm'):,.2f}")
    print(f"   - Total Revenue: ${results.get('revenue'):,.2f}")
    
    assert status == "Optimal", f"Expected Optimal solution, got: {status}"
    assert results.get("vcm") is not None, "Expected VCM to be computed"
    print("✅ Feasible Case Passed Successfully!\n")

def test_infeasible_case():
    print("🧪 Running Test Case 2: Infeasible Case (Extreme Demands)...")
    
    # Extreme committed demand that cannot be met by component fat/protein
    extreme_demand_data = [
        { "plant": "Auckland", "product": "Butter", "committed": 5000, "optional": 100 }
    ]
    
    results = run_milktrix_optimization(
        supply_data=SUPPLY_DATA,
        plant_data=PLANT_DATA,
        product_data=PRODUCT_DATA,
        demand_data=extreme_demand_data,
        logistics_data=LOGISTICS_DATA,
        global_constraints=GLOBAL_CONSTRAINTS
    )
    
    status = results.get("status")
    print(f"   - Solver Status: {status}")
    
    assert status != "Optimal", f"Expected solver to fail (Infeasible), but it got: {status}"
    print("✅ Infeasibility Handling Passed Successfully!\n")

if __name__ == "__main__":
    print("=== STARTING MILKTRIX LP OPTIMIZATION ENGINE TEST SUITE ===\n")
    try:
        test_feasible_case()
        test_infeasible_case()
        print("🎉 ALL TESTS PASSED SUCCESSFULLY! The LP optimization engine is robust.")
    except AssertionError as e:
        print(f"❌ TEST FAILED: {str(e)}")
        sys.exit(1)
