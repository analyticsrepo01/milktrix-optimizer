import pulp
import pandas as pd
import numpy as np
from typing import Dict, Any, List

def run_milktrix_optimization(
    supply_data: List[Dict[str, Any]],
    plant_data: List[Dict[str, Any]],
    product_data: List[Dict[str, Any]],
    demand_data: List[Dict[str, Any]],
    logistics_data: List[Dict[str, Any]],
    global_constraints: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Runs the Milktrix LP Optimization to Maximize Variable Contribution Margin (VCM).
    
    Variables:
    - x[r, p]: Milk volume (Liters) transported from region r to plant p
    - y[p, k]: Quantity of product k produced at plant p (Tons)
    - s[p, k]: Quantity of product k sold from plant p (Tons)
    - inv[p, k]: Quantity of product k held in inventory at plant p (Tons)
    """
    
    # Initialize optimization model
    prob = pulp.LpProblem("Milktrix_VCM_Maximizer", pulp.LpMaximize)
    
    # Extract keys
    regions = [r['region'] for r in supply_data]
    plants = [p['plant'] for p in plant_data]
    products = [pr['product'] for pr in product_data]
    
    # Extract mappings/parameters
    supply_volumes = {r['region']: r['volume'] for r in supply_data}
    # Milk composition percentages
    fat_pct = {r['region']: r['fat'] / 100.0 for r in supply_data}
    protein_pct = {r['region']: r['protein'] / 100.0 for r in supply_data}
    lactose_pct = {r['region']: r['lactose'] / 100.0 for r in supply_data}
    
    plant_capacities = {p['plant']: p['capacity'] for p in plant_data}
    
    # Product BOMs (component kg needed per Ton of finished product)
    bom_fat = {pr['product']: pr['bom_fat'] for pr in product_data}
    bom_protein = {pr['product']: pr['bom_protein'] for pr in product_data}
    bom_lactose = {pr['product']: pr['bom_lactose'] for pr in product_data}
    prod_costs = {pr['product']: pr['production_cost'] for pr in product_data}
    prices = {pr['product']: pr['price'] for pr in product_data}
    
    # Demand limits
    committed_demands = {}
    optional_demands = {}
    for d in demand_data:
        key = (d['plant'], d['product'])
        committed_demands[key] = d['committed']
        optional_demands[key] = d['optional']
        
    # Logistics transport costs ($ per Liter)
    transport_costs = {}
    for l in logistics_data:
        transport_costs[(l['region'], l['plant'])] = l['cost']
        
    # Standard fallback for missing transport costs
    for r in regions:
        for p in plants:
            if (r, p) not in transport_costs:
                transport_costs[(r, p)] = 0.05 # Default 5 cents/L
                
    # Define Decision Variables
    # 1. Milk transport from region r to plant p (liters)
    x = pulp.LpVariable.dicts("transport", ((r, p) for r in regions for p in plants), lowBound=0, cat='Continuous')
    
    # 2. Finished goods production at plant p for product k (tons)
    y = pulp.LpVariable.dicts("produce", ((p, k) for p in plants for k in products), lowBound=0, cat='Continuous')
    
    # 3. Finished goods sales from plant p for product k (tons)
    s = pulp.LpVariable.dicts("sell", ((p, k) for p in plants for k in products), lowBound=0, cat='Continuous')

    # OBJECTIVE FUNCTION: Maximize Variable Contribution Margin (VCM)
    # VCM = Revenue - Milk Procurement - Processing - Transport - Storage/Other Costs
    
    revenue_term = pulp.lpSum(s[p, k] * prices[k] for p in plants for k in products)
    transport_term = pulp.lpSum(x[r, p] * transport_costs[(r, p)] for r in regions for p in plants)
    production_term = pulp.lpSum(y[p, k] * prod_costs[k] for p in plants for k in products)
    
    # Co-op obligation: pay for all supply (fixed procurement cost)
    milk_cost_term = sum(supply_volumes[r] * global_constraints.get('milk_base_price', 0.45) for r in regions)
    
    prob += revenue_term - transport_term - production_term - milk_cost_term, "Total_VCM"
    
    # CONSTRAINTS
    
    # 1. Supply obligation: Process all regional supply (co-op obligation)
    for r in regions:
        prob += pulp.lpSum(x[r, p] for p in plants) == supply_volumes[r], f"Supply_Obligation_{r}"
        
    # 2. Plant capacity constraints (liters of milk processing limit)
    for p in plants:
        prob += pulp.lpSum(x[r, p] for r in regions) <= plant_capacities[p], f"Plant_Capacity_{p}"
        
    # 3. Component Mass Balance at each Plant
    # Liquid milk is converted into finished products.
    # Total components used in production cannot exceed components in the incoming milk.
    # Note: Milk weight ~ 1 kg/Liter, so 1 Liter ~ 1 kg of liquid milk.
    for p in plants:
        # Total fat incoming (kg)
        total_fat_incoming = pulp.lpSum(x[r, p] * fat_pct[r] for r in regions)
        # Total protein incoming (kg)
        total_protein_incoming = pulp.lpSum(x[r, p] * protein_pct[r] for r in regions)
        # Total lactose incoming (kg)
        total_lactose_incoming = pulp.lpSum(x[r, p] * lactose_pct[r] for r in regions)
        
        # Total components used in finished goods
        # y[p, k] is in Tons. 1 Ton = 1000 kg.
        total_fat_used = pulp.lpSum(y[p, k] * bom_fat[k] for k in products)
        total_protein_used = pulp.lpSum(y[p, k] * bom_protein[k] for k in products)
        total_lactose_used = pulp.lpSum(y[p, k] * bom_lactose[k] for k in products)
        
        prob += total_fat_used <= total_fat_incoming, f"Fat_Balance_Plant_{p}"
        prob += total_protein_used <= total_protein_incoming, f"Protein_Balance_Plant_{p}"
        prob += total_lactose_used <= total_lactose_incoming, f"Lactose_Balance_Plant_{p}"
        
    # 4. Sales & Inventory Balance
    # Since this is a single-period/snapshot planning model, Sales <= Production
    for p in plants:
        for k in products:
            prob += s[p, k] <= y[p, k], f"Sales_Limit_Prod_Balance_{p}_{k}"
            
    # 5. Demand Constraints (Committed & Optional)
    for p in plants:
        for k in products:
            comm = committed_demands.get((p, k), 0)
            opt = optional_demands.get((p, k), 0)
            
            # Sales must meet at least committed demand
            prob += s[p, k] >= comm, f"Committed_Demand_Bound_{p}_{k}"
            # Sales cannot exceed total demand (Committed + Optional)
            prob += s[p, k] <= comm + opt, f"Total_Demand_Bound_{p}_{k}"
            
    # Solve model
    solver = pulp.PULP_CBC_CMD(msg=False)
    status = prob.solve(solver)
    
    status_str = pulp.LpStatus[status]
    
    # Process outputs
    results = {
        "status": status_str,
        "vcm": pulp.value(prob.objective) if status_str == "Optimal" else 0.0,
        "transport_cost": sum(x[r, p].varValue * transport_costs[(r, p)] for r in regions for p in plants) if status_str == "Optimal" else 0.0,
        "production_cost": sum(y[p, k].varValue * prod_costs[k] for p in plants for k in products) if status_str == "Optimal" else 0.0,
        "revenue": sum(s[p, k].varValue * prices[k] for p in plants for k in products) if status_str == "Optimal" else 0.0,
        "milk_procurement_cost": milk_cost_term,
        "logistics": [],
        "production": [],
        "sales": [],
        "plant_utilization": [],
        "components": {}
    }
    
    if status_str == "Optimal":
        # 1. Logistics
        for r in regions:
            for p in plants:
                vol = x[r, p].varValue
                if vol > 0.01:
                    results["logistics"].append({
                        "region": r,
                        "plant": p,
                        "volume": round(vol, 2),
                        "cost": round(vol * transport_costs[(r, p)], 2),
                        "fat_delivered": round(vol * fat_pct[r], 2),
                        "protein_delivered": round(vol * protein_pct[r], 2)
                    })
                    
        # 2. Production
        for p in plants:
            for k in products:
                prod = y[p, k].varValue
                if prod > 0.01:
                    results["production"].append({
                        "plant": p,
                        "product": k,
                        "quantity": round(prod, 2),
                        "cost": round(prod * prod_costs[k], 2)
                    })
                    
        # 3. Sales
        for p in plants:
            for k in products:
                sold = s[p, k].varValue
                comm = committed_demands.get((p, k), 0)
                opt = optional_demands.get((p, k), 0)
                if sold > 0.01:
                    results["sales"].append({
                        "plant": p,
                        "product": k,
                        "quantity": round(sold, 2),
                        "revenue": round(sold * prices[k], 2),
                        "committed": comm,
                        "optional": opt,
                        "optional_filled": round(max(0.0, sold - comm), 2)
                    })
                    
        # 4. Plant Utilization & Component Balance
        for p in plants:
            total_milk = sum(x[r, p].varValue for r in regions)
            util_pct = (total_milk / plant_capacities[p]) * 100.0 if plant_capacities[p] > 0 else 0
            results["plant_utilization"].append({
                "plant": p,
                "milk_intake": round(total_milk, 2),
                "capacity": plant_capacities[p],
                "utilization": round(util_pct, 2)
            })
            
            # Component breakdown for details
            fat_in = sum(x[r, p].varValue * fat_pct[r] for r in regions)
            prot_in = sum(x[r, p].varValue * protein_pct[r] for r in regions)
            lac_in = sum(x[r, p].varValue * lactose_pct[r] for r in regions)
            
            fat_used = sum(y[p, k].varValue * bom_fat[k] for k in products)
            prot_used = sum(y[p, k].varValue * bom_protein[k] for k in products)
            lac_used = sum(y[p, k].varValue * bom_lactose[k] for k in products)
            
            results["components"][p] = {
                "fat": {"in": round(fat_in, 2), "out": round(fat_used, 2), "surplus": round(fat_in - fat_used, 2)},
                "protein": {"in": round(prot_in, 2), "out": round(prot_used, 2), "surplus": round(prot_in - prot_used, 2)},
                "lactose": {"in": round(lac_in, 2), "out": round(lac_used, 2), "surplus": round(lac_in - lac_used, 2)}
            }
            
    return results
