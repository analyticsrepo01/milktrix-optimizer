import os
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from app.services.optimizer import run_milktrix_optimization
from app.services.database import save_run, get_runs_history, get_run_details

app = FastAPI(title="Milktrix S&OP Optimizer API", version="1.0.0")

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request Models
class SupplyItem(BaseModel):
    region: str
    volume: float
    fat: float
    protein: float
    lactose: float

class PlantItem(BaseModel):
    plant: str
    capacity: float
    fixed_cost: float

class ProductItem(BaseModel):
    product: str
    price: float
    production_cost: float
    bom_fat: float
    bom_protein: float
    bom_lactose: float

class DemandItem(BaseModel):
    plant: str
    product: str
    committed: float
    optional: float

class LogisticsItem(BaseModel):
    region: str
    plant: str
    cost: float

class OptimizationRequest(BaseModel):
    supply_data: List[SupplyItem]
    plant_data: List[PlantItem]
    product_data: List[ProductItem]
    demand_data: List[DemandItem]
    logistics_data: List[LogisticsItem]
    global_constraints: Dict[str, Any]

# API Endpoints
@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "milktrix-optimizer-backend"}

@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    from fastapi.responses import Response
    return Response(status_code=204)

@app.post("/api/optimize")
def optimize_milktrix(payload: OptimizationRequest):
    try:
        # Convert Pydantic objects to pure dicts for the optimizer service
        supply_dicts = [item.dict() for item in payload.supply_data]
        plant_dicts = [item.dict() for item in payload.plant_data]
        product_dicts = [item.dict() for item in payload.product_data]
        demand_dicts = [item.dict() for item in payload.demand_data]
        logistics_dicts = [item.dict() for item in payload.logistics_data]
        
        results = run_milktrix_optimization(
            supply_data=supply_dicts,
            plant_data=plant_dicts,
            product_data=product_dicts,
            demand_data=demand_dicts,
            logistics_data=logistics_dicts,
            global_constraints=payload.global_constraints
        )
        
        # Save optimization run in SQLite for future reference
        try:
            save_run(
                vcm=results.get("vcm", 0.0),
                revenue=results.get("revenue", 0.0),
                prod_cost=results.get("production_cost", 0.0),
                trans_cost=results.get("transport_cost", 0.0),
                status=results.get("status", "Failed"),
                inputs=payload.dict(),
                results=results
            )
        except Exception as db_err:
            print(f"Failed to save run to SQLite: {str(db_err)}")
            
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Optimization failed: {str(e)}")

@app.get("/api/history")
def fetch_history():
    try:
        return get_runs_history()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch history: {str(e)}")

@app.get("/api/history/{run_id}")
def fetch_run_details(run_id: int):
    try:
        details = get_run_details(run_id)
        if not details:
            raise HTTPException(status_code=404, detail="Run not found")
        return details
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch run details: {str(e)}")

# Fallback index to serve a beautiful modern dashboard directly
@app.get("/", response_class=HTMLResponse)
def get_dashboard():
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Milktrix S&OP Optimizer</title>
    <!-- Google Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <!-- FontAwesome for Premium Icons -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <!-- Chart.js -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    
    <style>
        :root {
            --bg-primary: #0a0f1d;
            --bg-secondary: #131b2e;
            --bg-tertiary: #1b2644;
            --accent-primary: #3b82f6;
            --accent-glow: rgba(59, 130, 246, 0.4);
            --accent-success: #10b981;
            --accent-success-glow: rgba(16, 185, 129, 0.3);
            --accent-warning: #f59e0b;
            --accent-danger: #ef4444;
            --text-main: #f8fafc;
            --text-secondary: #94a3b8;
            --border-color: rgba(255, 255, 255, 0.08);
            --card-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
            --transition-smooth: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: 'Plus Jakarta Sans', sans-serif;
            background-color: var(--bg-primary);
            color: var(--text-main);
            overflow-x: hidden;
            line-height: 1.5;
        }

        /* Custom Scrollbar */
        ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }
        ::-webkit-scrollbar-track {
            background: var(--bg-primary);
        }
        ::-webkit-scrollbar-thumb {
            background: var(--bg-tertiary);
            border-radius: 4px;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: var(--accent-primary);
        }

        /* Dashboard Header */
        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 1.5rem 3rem;
            background: rgba(19, 27, 46, 0.8);
            backdrop-filter: blur(20px);
            border-bottom: 1px solid var(--border-color);
            position: sticky;
            top: 0;
            z-index: 100;
        }

        .logo-container {
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }

        .logo-icon {
            background: linear-gradient(135deg, var(--accent-primary), #60a5fa);
            color: white;
            width: 40px;
            height: 40px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.25rem;
            box-shadow: 0 0 15px var(--accent-glow);
        }

        .logo-text h1 {
            font-family: 'Outfit', sans-serif;
            font-size: 1.4rem;
            font-weight: 700;
            letter-spacing: -0.5px;
            background: linear-gradient(to right, #ffffff, #94a3b8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .logo-text span {
            font-size: 0.75rem;
            color: var(--accent-primary);
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            display: block;
            margin-top: -2px;
        }

        .header-actions {
            display: flex;
            align-items: center;
            gap: 1.5rem;
        }

        .btn {
            padding: 0.75rem 1.5rem;
            border-radius: 10px;
            font-weight: 600;
            font-size: 0.9rem;
            cursor: pointer;
            transition: var(--transition-smooth);
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            border: none;
            outline: none;
        }

        .btn-primary {
            background: linear-gradient(135deg, var(--accent-primary), #2563eb);
            color: white;
            box-shadow: 0 4px 20px var(--accent-glow);
        }

        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 25px rgba(59, 130, 246, 0.6);
        }

        .btn-secondary {
            background: rgba(255, 255, 255, 0.05);
            color: var(--text-main);
            border: 1px solid var(--border-color);
        }

        .btn-secondary:hover {
            background: rgba(255, 255, 255, 0.1);
            transform: translateY(-2px);
        }

        /* Main Container */
        .dashboard-container {
            max-width: 1400px;
            margin: 2rem auto;
            padding: 0 2rem;
            display: flex;
            flex-direction: column;
            gap: 2rem;
        }

        /* Tabs Nav bar */
        .tabs-nav {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 1rem;
            background: var(--bg-secondary);
            padding: 0.5rem;
            border-radius: 14px;
            border: 1px solid var(--border-color);
            box-shadow: var(--card-shadow);
        }

        .tab-nav-btn {
            padding: 1rem;
            border-radius: 10px;
            font-weight: 600;
            font-size: 0.95rem;
            background: transparent;
            color: var(--text-secondary);
            border: none;
            cursor: pointer;
            transition: var(--transition-smooth);
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0.75rem;
        }

        .tab-nav-btn.active {
            background: var(--bg-tertiary);
            color: white;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
            border: 1px solid rgba(255, 255, 255, 0.05);
        }

        .tab-nav-btn:hover:not(.active) {
            background: rgba(255, 255, 255, 0.02);
            color: white;
        }

        /* Sidebar Section Titles & Inputs */
        .card-section-title {
            font-family: 'Outfit', sans-serif;
            font-size: 1.15rem;
            font-weight: 600;
            color: #ffffff;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            padding-bottom: 0.75rem;
            margin-bottom: 1.25rem;
        }

        .input-group {
            display: flex;
            flex-direction: column;
            gap: 0.4rem;
            margin-bottom: 1rem;
        }

        .input-group label {
            font-size: 0.8rem;
            color: var(--text-secondary);
            font-weight: 500;
        }

        .input-group input, .input-group select {
            background: var(--bg-primary);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 0.6rem 0.8rem;
            color: white;
            font-family: inherit;
            font-size: 0.9rem;
            transition: var(--transition-smooth);
        }

        .input-group input:focus, .input-group select:focus {
            border-color: var(--accent-primary);
            box-shadow: 0 0 10px var(--accent-glow);
            outline: none;
        }

        /* Grid structures inside Tab Content */
        .inputs-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 1.5rem;
        }

        .parameters-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 1.5rem;
        }

        .kpi-row {
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 1.25rem;
            margin-bottom: 1.5rem;
        }

        .kpi-card {
            background: linear-gradient(135deg, var(--bg-secondary), rgba(19, 27, 46, 0.6));
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 1.25rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            box-shadow: var(--card-shadow);
            transition: var(--transition-smooth);
            position: relative;
            overflow: hidden;
        }

        .kpi-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 4px;
            height: 100%;
            background: var(--accent-primary);
        }

        .kpi-card.success::before {
            background: var(--accent-success);
        }

        .kpi-card.warning::before {
            background: var(--accent-warning);
        }

        .kpi-card:hover {
            transform: translateY(-3px);
            border-color: rgba(59, 130, 246, 0.3);
        }

        .kpi-info h4 {
            font-size: 0.8rem;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 0.25rem;
        }

        .kpi-info .kpi-value {
            font-family: 'Outfit', sans-serif;
            font-size: 1.6rem;
            font-weight: 700;
        }

        .kpi-icon-container {
            width: 44px;
            height: 44px;
            border-radius: 12px;
            background: rgba(255, 255, 255, 0.03);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.15rem;
            color: var(--accent-primary);
        }

        .kpi-card.success .kpi-icon-container {
            color: var(--accent-success);
            background: rgba(16, 185, 129, 0.1);
        }

        .kpi-card.warning .kpi-icon-container {
            color: var(--accent-warning);
            background: rgba(245, 158, 11, 0.1);
        }

        /* Dashboard Grid / Charts */
        .dashboard-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 1.5rem;
        }

        .card {
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 20px;
            padding: 1.5rem;
            box-shadow: var(--card-shadow);
        }

        .card-title {
            font-family: 'Outfit', sans-serif;
            font-size: 1.2rem;
            font-weight: 600;
            margin-bottom: 1.5rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        /* Tables style */
        .table-container {
            overflow-x: auto;
            margin-top: 1rem;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            text-align: left;
            font-size: 0.9rem;
        }

        th {
            padding: 0.75rem 1rem;
            color: var(--text-secondary);
            font-weight: 600;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            background: rgba(0, 0, 0, 0.1);
        }

        td {
            padding: 0.75rem 1rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.03);
            color: #cbd5e1;
        }

        tr:hover td {
            background: rgba(255, 255, 255, 0.02);
        }

        .badge {
            padding: 0.25rem 0.5rem;
            border-radius: 6px;
            font-size: 0.75rem;
            font-weight: 600;
            display: inline-block;
        }

        .badge-success {
            background: rgba(16, 185, 129, 0.15);
            color: var(--accent-success);
        }

        .badge-info {
            background: rgba(59, 130, 246, 0.15);
            color: var(--accent-primary);
        }

        /* Loader Overlay */
        .loader-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(10, 15, 29, 0.85);
            backdrop-filter: blur(10px);
            z-index: 1000;
            display: none;
            align-items: center;
            justify-content: center;
            flex-direction: column;
            gap: 1.5rem;
        }

        .spinner {
            width: 60px;
            height: 60px;
            border: 4px solid rgba(59, 130, 246, 0.1);
            border-left-color: var(--accent-primary);
            border-radius: 50%;
            animation: spin 1s linear infinite;
            box-shadow: 0 0 20px var(--accent-glow);
        }

        @keyframes spin {
            100% { transform: rotate(360deg); }
        }

        .loader-text {
            font-family: 'Outfit', sans-serif;
            font-size: 1.2rem;
            font-weight: 600;
            letter-spacing: 0.5px;
        }
    </style>
</head>
<body>

    <!-- Loader -->
    <div id="loader" class="loader-overlay">
        <div class="spinner"></div>
        <div class="loader-text">Solving Milktrix LP Optimization Model...</div>
    </div>

    <!-- Header -->
    <header>
        <div class="logo-container">
            <div class="logo-icon">
                <i class="fa-solid fa-cow"></i>
            </div>
            <div class="logo-text">
                <h1>Milktrix Optimiser</h1>
                <span>S&OP Strategy Engine v4.0</span>
            </div>
        </div>
        <div class="header-actions">
            <button class="btn btn-secondary" onclick="resetToDefaults()">
                <i class="fa-solid fa-rotate-left"></i> Reset Defaults
            </button>
            <button class="btn btn-primary" onclick="runOptimizationAndGoToResults()">
                <i class="fa-solid fa-play"></i> Solve LP Model
            </button>
        </div>
    </header>

    <!-- Main Container -->
    <div class="dashboard-container">
        
        <!-- Tab Navigation Bar -->
        <div class="tabs-nav">
            <button id="nav-btn-inputs" class="tab-nav-btn active" onclick="switchTab('tab-inputs')">
                <i class="fa-solid fa-list-check"></i> 1. Supply & Capacities
            </button>
            <button id="nav-btn-parameters" class="tab-nav-btn" onclick="switchTab('tab-parameters')">
                <i class="fa-solid fa-sliders"></i> 2. Pricing & Demands
            </button>
            <button id="nav-btn-results" class="tab-nav-btn" onclick="switchTab('tab-results')">
                <i class="fa-solid fa-chart-pie"></i> 3. Results Overview
            </button>
            <button id="nav-btn-history" class="tab-nav-btn" onclick="switchTab('tab-history')">
                <i class="fa-solid fa-clock-rotate-left"></i> 4. History Logs
            </button>
        </div>

        <!-- Tab 1 Panel: Inputs -->
        <div id="tab-inputs" class="tab-panel">
            <div class="inputs-grid" style="grid-template-columns: 1fr; gap: 1.5rem;">
                
                <!-- Regional Supply Volumes & Quality Solids Composition -->
                <div class="card">
                    <div class="card-section-title">
                        <i class="fa-solid fa-truck-ramp-box"></i> Regional Milk Supply (Volume & Solids Composition)
                    </div>
                    <p class="text-secondary" style="font-size: 0.85rem; margin-bottom: 1rem;">
                        Adjust the available volume (Liters) and quality (Fat %, Protein %, Lactose %) of raw milk produced in each supplying dairy region.
                    </p>
                    <div style="overflow-x: auto;">
                        <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 0.9rem;">
                            <thead>
                                <tr style="border-bottom: 1px solid var(--border-color); color: var(--text-secondary);">
                                    <th style="padding: 0.75rem;">Supply Region</th>
                                    <th style="padding: 0.75rem;">Available Volume (Liters)</th>
                                    <th style="padding: 0.75rem;">Fat Composition %</th>
                                    <th style="padding: 0.75rem;">Protein Composition %</th>
                                    <th style="padding: 0.75rem;">Lactose Composition %</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.03);">
                                    <td style="padding: 0.75rem; font-weight: 600;"><i class="fa-solid fa-compass text-secondary" style="margin-right: 0.5rem;"></i>North Region</td>
                                    <td style="padding: 0.5rem;"><input type="number" id="supply_north" value="500000" style="width: 100%; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 8px; padding: 0.5rem; color: white;"></td>
                                    <td style="padding: 0.5rem;"><input type="number" id="fat_north" step="0.1" value="4.2" style="width: 100%; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 8px; padding: 0.5rem; color: white;"></td>
                                    <td style="padding: 0.5rem;"><input type="number" id="protein_north" step="0.1" value="3.4" style="width: 100%; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 8px; padding: 0.5rem; color: white;"></td>
                                    <td style="padding: 0.5rem;"><input type="number" id="lactose_north" step="0.1" value="4.8" style="width: 100%; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 8px; padding: 0.5rem; color: white;"></td>
                                </tr>
                                <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.03);">
                                    <td style="padding: 0.75rem; font-weight: 600;"><i class="fa-solid fa-compass text-secondary" style="margin-right: 0.5rem;"></i>South Region</td>
                                    <td style="padding: 0.5rem;"><input type="number" id="supply_south" value="400000" style="width: 100%; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 8px; padding: 0.5rem; color: white;"></td>
                                    <td style="padding: 0.5rem;"><input type="number" id="fat_south" step="0.1" value="4.0" style="width: 100%; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 8px; padding: 0.5rem; color: white;"></td>
                                    <td style="padding: 0.5rem;"><input type="number" id="protein_south" step="0.1" value="3.2" style="width: 100%; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 8px; padding: 0.5rem; color: white;"></td>
                                    <td style="padding: 0.5rem;"><input type="number" id="lactose_south" step="0.1" value="4.7" style="width: 100%; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 8px; padding: 0.5rem; color: white;"></td>
                                </tr>
                                <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.03);">
                                    <td style="padding: 0.75rem; font-weight: 600;"><i class="fa-solid fa-compass text-secondary" style="margin-right: 0.5rem;"></i>East Region</td>
                                    <td style="padding: 0.5rem;"><input type="number" id="supply_east" value="300000" style="width: 100%; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 8px; padding: 0.5rem; color: white;"></td>
                                    <td style="padding: 0.5rem;"><input type="number" id="fat_east" step="0.1" value="4.5" style="width: 100%; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 8px; padding: 0.5rem; color: white;"></td>
                                    <td style="padding: 0.5rem;"><input type="number" id="protein_east" step="0.1" value="3.5" style="width: 100%; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 8px; padding: 0.5rem; color: white;"></td>
                                    <td style="padding: 0.5rem;"><input type="number" id="lactose_east" step="0.1" value="4.6" style="width: 100%; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 8px; padding: 0.5rem; color: white;"></td>
                                </tr>
                                <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.03);">
                                    <td style="padding: 0.75rem; font-weight: 600;"><i class="fa-solid fa-compass text-secondary" style="margin-right: 0.5rem;"></i>West Region</td>
                                    <td style="padding: 0.5rem;"><input type="number" id="supply_west" value="600000" style="width: 100%; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 8px; padding: 0.5rem; color: white;"></td>
                                    <td style="padding: 0.5rem;"><input type="number" id="fat_west" step="0.1" value="3.8" style="width: 100%; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 8px; padding: 0.5rem; color: white;"></td>
                                    <td style="padding: 0.5rem;"><input type="number" id="protein_west" step="0.1" value="3.1" style="width: 100%; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 8px; padding: 0.5rem; color: white;"></td>
                                    <td style="padding: 0.5rem;"><input type="number" id="lactose_west" step="0.1" value="4.9" style="width: 100%; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 8px; padding: 0.5rem; color: white;"></td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>

                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem;">
                    <!-- Plant Capacities & Fixed Costs -->
                    <div class="card">
                        <div class="card-section-title">
                            <i class="fa-solid fa-industry"></i> Plant Capacities & Processing Fixed Costs
                        </div>
                        <p class="text-secondary" style="font-size: 0.85rem; margin-bottom: 1rem;">
                            Configure the maximum liquid milk intake (Liters) and processing base costs for each plant.
                        </p>
                        <div style="overflow-x: auto;">
                            <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 0.9rem;">
                                <thead>
                                    <tr style="border-bottom: 1px solid var(--border-color); color: var(--text-secondary);">
                                        <th style="padding: 0.5rem;">Processing Plant</th>
                                        <th style="padding: 0.5rem;">Intake Limit (L)</th>
                                        <th style="padding: 0.5rem;">Fixed Cost ($)</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.03);">
                                        <td style="padding: 0.5rem; font-weight: 600;">Auckland</td>
                                        <td style="padding: 0.3rem;"><input type="number" id="cap_auckland" value="800000" style="width: 100%; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 6px; padding: 0.4rem; color: white;"></td>
                                        <td style="padding: 0.3rem;"><input type="number" id="fix_auckland" value="15000" style="width: 100%; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 6px; padding: 0.4rem; color: white;"></td>
                                    </tr>
                                    <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.03);">
                                        <td style="padding: 0.5rem; font-weight: 600;">Hamilton</td>
                                        <td style="padding: 0.3rem;"><input type="number" id="cap_hamilton" value="600000" style="width: 100%; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 6px; padding: 0.4rem; color: white;"></td>
                                        <td style="padding: 0.3rem;"><input type="number" id="fix_hamilton" value="12000" style="width: 100%; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 6px; padding: 0.4rem; color: white;"></td>
                                    </tr>
                                    <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.03);">
                                        <td style="padding: 0.5rem; font-weight: 600;">Christchurch</td>
                                        <td style="padding: 0.3rem;"><input type="number" id="cap_christchurch" value="700000" style="width: 100%; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 6px; padding: 0.4rem; color: white;"></td>
                                        <td style="padding: 0.3rem;"><input type="number" id="fix_christchurch" value="14000" style="width: 100%; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 6px; padding: 0.4rem; color: white;"></td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>

                    <!-- Inter-site Logistics Transport Matrix -->
                    <div class="card">
                        <div class="card-section-title">
                            <i class="fa-solid fa-route"></i> Logistics & Shipping Cost Matrix ($/Liter)
                        </div>
                        <p class="text-secondary" style="font-size: 0.85rem; margin-bottom: 1rem;">
                            Define the physical transport fee per Liter of liquid milk shipped from each farm region to each plant.
                        </p>
                        <div style="overflow-x: auto;">
                            <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 0.85rem;">
                                <thead>
                                    <tr style="border-bottom: 1px solid var(--border-color); color: var(--text-secondary);">
                                        <th style="padding: 0.4rem;">From / To</th>
                                        <th style="padding: 0.4rem;">Auckland</th>
                                        <th style="padding: 0.4rem;">Hamilton</th>
                                        <th style="padding: 0.4rem;">Christchurch</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.03);">
                                        <td style="padding: 0.4rem; font-weight: 600;">North</td>
                                        <td style="padding: 0.2rem;"><input type="number" step="0.01" id="log_n_ack" value="0.02" style="width: 100%; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 6px; padding: 0.35rem; color: white;"></td>
                                        <td style="padding: 0.2rem;"><input type="number" step="0.01" id="log_n_ham" value="0.04" style="width: 100%; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 6px; padding: 0.35rem; color: white;"></td>
                                        <td style="padding: 0.2rem;"><input type="number" step="0.01" id="log_n_chch" value="0.09" style="width: 100%; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 6px; padding: 0.35rem; color: white;"></td>
                                    </tr>
                                    <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.03);">
                                        <td style="padding: 0.4rem; font-weight: 600;">South</td>
                                        <td style="padding: 0.2rem;"><input type="number" step="0.01" id="log_s_ack" value="0.05" style="width: 100%; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 6px; padding: 0.35rem; color: white;"></td>
                                        <td style="padding: 0.2rem;"><input type="number" step="0.01" id="log_s_ham" value="0.03" style="width: 100%; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 6px; padding: 0.35rem; color: white;"></td>
                                        <td style="padding: 0.2rem;"><input type="number" step="0.01" id="log_s_chch" value="0.07" style="width: 100%; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 6px; padding: 0.35rem; color: white;"></td>
                                    </tr>
                                    <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.03);">
                                        <td style="padding: 0.4rem; font-weight: 600;">East</td>
                                        <td style="padding: 0.2rem;"><input type="number" step="0.01" id="log_e_ack" value="0.06" style="width: 100%; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 6px; padding: 0.35rem; color: white;"></td>
                                        <td style="padding: 0.2rem;"><input type="number" step="0.01" id="log_e_ham" value="0.05" style="width: 100%; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 6px; padding: 0.35rem; color: white;"></td>
                                        <td style="padding: 0.2rem;"><input type="number" step="0.01" id="log_e_chch" value="0.02" style="width: 100%; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 6px; padding: 0.35rem; color: white;"></td>
                                    </tr>
                                    <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.03);">
                                        <td style="padding: 0.4rem; font-weight: 600;">West</td>
                                        <td style="padding: 0.2rem;"><input type="number" step="0.01" id="log_w_ack" value="0.03" style="width: 100%; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 6px; padding: 0.35rem; color: white;"></td>
                                        <td style="padding: 0.2rem;"><input type="number" step="0.01" id="log_w_ham" value="0.02" style="width: 100%; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 6px; padding: 0.35rem; color: white;"></td>
                                        <td style="padding: 0.2rem;"><input type="number" step="0.01" id="log_w_chch" value="0.08" style="width: 100%; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 6px; padding: 0.35rem; color: white;"></td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>

            </div>
            
            <div style="text-align: right; margin-top: 1.5rem;">
                <button class="btn btn-primary" onclick="switchTab('tab-parameters')">
                    Next: Pricing & Demands <i class="fa-solid fa-arrow-right"></i>
                </button>
            </div>
        </div>

        <!-- Tab 2 Panel: Parameters -->
        <div id="tab-parameters" class="tab-panel" style="display: none;">
            <div class="parameters-grid" style="grid-template-columns: 1fr; gap: 1.5rem;">
                
                <!-- Product Specs, Pricing, & Component Yield BOMs -->
                <div class="card">
                    <div class="card-section-title">
                        <i class="fa-solid fa-vials"></i> Product Specs, Market Pricing, & Yield BOMs (kg/Ton)
                    </div>
                    <p class="text-secondary" style="font-size: 0.85rem; margin-bottom: 1rem;">
                        Specify the global wholesale price, raw processing cost, and constituent solid requirements (kg of solids needed to produce 1 Ton of finished product).
                    </p>
                    <div style="overflow-x: auto;">
                        <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 0.9rem;">
                            <thead>
                                <tr style="border-bottom: 1px solid var(--border-color); color: var(--text-secondary);">
                                    <th style="padding: 0.75rem;">Product Class</th>
                                    <th style="padding: 0.75rem;">Selling Price ($/Ton)</th>
                                    <th style="padding: 0.75rem;">Var. Cost ($/Ton)</th>
                                    <th style="padding: 0.75rem;">Fat BOM (kg/Ton)</th>
                                    <th style="padding: 0.75rem;">Protein BOM (kg/Ton)</th>
                                    <th style="padding: 0.75rem;">Lactose BOM (kg/Ton)</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.03);">
                                    <td style="padding: 0.75rem; font-weight: 600;"><i class="fa-solid fa-box text-secondary" style="margin-right: 0.5rem;"></i>WMP (Whole Milk Powder)</td>
                                    <td style="padding: 0.4rem;"><input type="number" id="price_wmp" value="3200" style="width: 100%; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 6px; padding: 0.4rem; color: white;"></td>
                                    <td style="padding: 0.4rem;"><input type="number" id="cost_wmp" value="400" style="width: 100%; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 6px; padding: 0.4rem; color: white;"></td>
                                    <td style="padding: 0.4rem;"><input type="number" id="bom_fat_wmp" value="260" style="width: 100%; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 6px; padding: 0.4rem; color: white;"></td>
                                    <td style="padding: 0.4rem;"><input type="number" id="bom_prot_wmp" value="250" style="width: 100%; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 6px; padding: 0.4rem; color: white;"></td>
                                    <td style="padding: 0.4rem;"><input type="number" id="bom_lac_wmp" value="380" style="width: 100%; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 6px; padding: 0.4rem; color: white;"></td>
                                </tr>
                                <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.03);">
                                    <td style="padding: 0.75rem; font-weight: 600;"><i class="fa-solid fa-box text-secondary" style="margin-right: 0.5rem;"></i>SMP (Skim Milk Powder)</td>
                                    <td style="padding: 0.4rem;"><input type="number" id="price_smp" value="2800" style="width: 100%; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 6px; padding: 0.4rem; color: white;"></td>
                                    <td style="padding: 0.4rem;"><input type="number" id="cost_smp" value="350" style="width: 100%; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 6px; padding: 0.4rem; color: white;"></td>
                                    <td style="padding: 0.4rem;"><input type="number" id="bom_fat_smp" value="10" style="width: 100%; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 6px; padding: 0.4rem; color: white;"></td>
                                    <td style="padding: 0.4rem;"><input type="number" id="bom_prot_smp" value="360" style="width: 100%; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 6px; padding: 0.4rem; color: white;"></td>
                                    <td style="padding: 0.4rem;"><input type="number" id="bom_lac_smp" value="500" style="width: 100%; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 6px; padding: 0.4rem; color: white;"></td>
                                </tr>
                                <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.03);">
                                    <td style="padding: 0.75rem; font-weight: 600;"><i class="fa-solid fa-box text-secondary" style="margin-right: 0.5rem;"></i>Cheese</td>
                                    <td style="padding: 0.4rem;"><input type="number" id="price_cheese" value="4500" style="width: 100%; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 6px; padding: 0.4rem; color: white;"></td>
                                    <td style="padding: 0.4rem;"><input type="number" id="cost_cheese" value="600" style="width: 100%; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 6px; padding: 0.4rem; color: white;"></td>
                                    <td style="padding: 0.4rem;"><input type="number" id="bom_fat_cheese" value="300" style="width: 100%; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 6px; padding: 0.4rem; color: white;"></td>
                                    <td style="padding: 0.4rem;"><input type="number" id="bom_prot_cheese" value="250" style="width: 100%; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 6px; padding: 0.4rem; color: white;"></td>
                                    <td style="padding: 0.4rem;"><input type="number" id="bom_lac_cheese" value="10" style="width: 100%; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 6px; padding: 0.4rem; color: white;"></td>
                                </tr>
                                <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.03);">
                                    <td style="padding: 0.75rem; font-weight: 600;"><i class="fa-solid fa-box text-secondary" style="margin-right: 0.5rem;"></i>Butter</td>
                                    <td style="padding: 0.4rem;"><input type="number" id="price_butter" value="5200" style="width: 100%; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 6px; padding: 0.4rem; color: white;"></td>
                                    <td style="padding: 0.4rem;"><input type="number" id="cost_butter" value="500" style="width: 100%; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 6px; padding: 0.4rem; color: white;"></td>
                                    <td style="padding: 0.4rem;"><input type="number" id="bom_fat_butter" value="820" style="width: 100%; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 6px; padding: 0.4rem; color: white;"></td>
                                    <td style="padding: 0.4rem;"><input type="number" id="bom_prot_butter" value="10" style="width: 100%; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 6px; padding: 0.4rem; color: white;"></td>
                                    <td style="padding: 0.4rem;"><input type="number" id="bom_lac_butter" value="10" style="width: 100%; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 6px; padding: 0.4rem; color: white;"></td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>

                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem;">
                    <!-- Comprehensive Product Committed & Optional Demand Matrix -->
                    <div class="card">
                        <div class="card-section-title">
                            <i class="fa-solid fa-cart-shopping"></i> Plant Demand Profiles (Committed & Optional)
                        </div>
                        <p class="text-secondary" style="font-size: 0.85rem; margin-bottom: 1rem;">
                            Committed demand must be fully met (can trigger infeasibility if components are insufficient). Optional demand is served to maximize margin.
                        </p>
                        <div style="overflow-x: auto;">
                            <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 0.85rem;">
                                <thead>
                                    <tr style="border-bottom: 1px solid var(--border-color); color: var(--text-secondary);">
                                        <th style="padding: 0.5rem;">Location & Product</th>
                                        <th style="padding: 0.5rem;">Committed (Tons)</th>
                                        <th style="padding: 0.5rem;">Optional Max (Tons)</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.03);">
                                        <td style="padding: 0.5rem; font-weight: 600;">Auckland - WMP</td>
                                        <td style="padding: 0.25rem;"><input type="number" id="demand_ack_wmp" value="10" style="width: 100%; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 6px; padding: 0.35rem; color: white;"></td>
                                        <td style="padding: 0.25rem;"><input type="number" id="demand_ack_wmp_opt" value="200" style="width: 100%; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 6px; padding: 0.35rem; color: white;"></td>
                                    </tr>
                                    <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.03);">
                                        <td style="padding: 0.5rem; font-weight: 600;">Auckland - Butter</td>
                                        <td style="padding: 0.25rem;"><input type="number" id="demand_ack_butter" value="5" style="width: 100%; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 6px; padding: 0.35rem; color: white;"></td>
                                        <td style="padding: 0.25rem;"><input type="number" id="demand_ack_butter_opt" value="100" style="width: 100%; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 6px; padding: 0.35rem; color: white;"></td>
                                    </tr>
                                    <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.03);">
                                        <td style="padding: 0.5rem; font-weight: 600;">Hamilton - Cheese</td>
                                        <td style="padding: 0.25rem;"><input type="number" id="demand_ham_cheese" value="10" style="width: 100%; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 6px; padding: 0.35rem; color: white;"></td>
                                        <td style="padding: 0.25rem;"><input type="number" id="demand_ham_cheese_opt" value="150" style="width: 100%; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 6px; padding: 0.35rem; color: white;"></td>
                                    </tr>
                                    <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.03);">
                                        <td style="padding: 0.5rem; font-weight: 600;">Hamilton - SMP</td>
                                        <td style="padding: 0.25rem;"><input type="number" id="demand_ham_smp" value="10" style="width: 100%; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 6px; padding: 0.35rem; color: white;"></td>
                                        <td style="padding: 0.25rem;"><input type="number" id="demand_ham_smp_opt" value="120" style="width: 100%; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 6px; padding: 0.35rem; color: white;"></td>
                                    </tr>
                                    <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.03);">
                                        <td style="padding: 0.5rem; font-weight: 600;">Christchurch - WMP</td>
                                        <td style="padding: 0.25rem;"><input type="number" id="demand_chch_wmp" value="10" style="width: 100%; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 6px; padding: 0.35rem; color: white;"></td>
                                        <td style="padding: 0.25rem;"><input type="number" id="demand_chch_wmp_opt" value="180" style="width: 100%; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 6px; padding: 0.35rem; color: white;"></td>
                                    </tr>
                                    <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.03);">
                                        <td style="padding: 0.5rem; font-weight: 600;">Christchurch - Cheese</td>
                                        <td style="padding: 0.25rem;"><input type="number" id="demand_chch_cheese" value="10" style="width: 100%; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 6px; padding: 0.35rem; color: white;"></td>
                                        <td style="padding: 0.25rem;"><input type="number" id="demand_chch_cheese_opt" value="110" style="width: 100%; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 6px; padding: 0.35rem; color: white;"></td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>

                    <!-- Pricing & Global Cost Settings -->
                    <div class="card">
                        <div class="card-section-title">
                            <i class="fa-solid fa-dollar-sign"></i> Global Procurement Pricing Settings
                        </div>
                        <p class="text-secondary" style="font-size: 0.85rem; margin-bottom: 1rem;">
                            Set the guaranteed co-operative payment rate for collected supplier milk.
                        </p>
                        <div class="input-group" style="margin-bottom: 1.5rem;">
                            <label>Co-op Milk Base Procurement Price ($/Liter)</label>
                            <input type="number" id="milk_base_price" step="0.01" value="0.45">
                        </div>
                        
                        <div style="border-top: 1px solid var(--border-color); padding-top: 1.5rem; display: flex; flex-direction: column; gap: 0.75rem;">
                            <div style="display: flex; justify-content: space-between; font-size: 0.85rem;">
                                <span class="text-secondary">Committed Constraints:</span>
                                <span class="badge badge-success">CBC Active</span>
                            </div>
                            <div style="display: flex; justify-content: space-between; font-size: 0.85rem;">
                                <span class="text-secondary">Mass Balance Check:</span>
                                <span class="text-main">Fat, Protein, Lactose</span>
                            </div>
                            <div style="display: flex; justify-content: space-between; font-size: 0.85rem;">
                                <span class="text-secondary">Solver Engine:</span>
                                <span class="text-main">PuLP linear optimizer</span>
                            </div>
                        </div>
                    </div>
                </div>

            </div>
            
            <div style="display: flex; justify-content: space-between; margin-top: 1.5rem;">
                <button class="btn btn-secondary" onclick="switchTab('tab-inputs')">
                    <i class="fa-solid fa-arrow-left"></i> Back
                </button>
                <button class="btn btn-primary" onclick="runOptimizationAndGoToResults()">
                    <i class="fa-solid fa-play"></i> Solve & View Results <i class="fa-solid fa-arrow-right"></i>
                </button>
            </div>
        </div>

        <!-- Tab 3 Panel: Results -->
        <div id="tab-results" class="tab-panel" style="display: none;">
            
            <!-- KPI Cards -->
            <div class="kpi-row">
                <div class="kpi-card success">
                    <div class="kpi-info">
                        <h4>Solver Status</h4>
                        <div class="kpi-value" id="kpi-status" style="font-size: 1.5rem; color: var(--accent-success);">OPTIMAL</div>
                    </div>
                    <div class="kpi-icon-container" id="kpi-status-icon">
                        <i class="fa-solid fa-square-check"></i>
                    </div>
                </div>
                <div class="kpi-card success">
                    <div class="kpi-info">
                        <h4>Total VCM</h4>
                        <div class="kpi-value" id="kpi-vcm">$0.00</div>
                    </div>
                    <div class="kpi-icon-container">
                        <i class="fa-solid fa-dollar-sign"></i>
                    </div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-info">
                        <h4>Total Revenue</h4>
                        <div class="kpi-value" id="kpi-revenue">$0.00</div>
                    </div>
                    <div class="kpi-icon-container">
                        <i class="fa-solid fa-chart-line"></i>
                    </div>
                </div>
                <div class="kpi-card warning">
                    <div class="kpi-info">
                        <h4>Production Cost</h4>
                        <div class="kpi-value" id="kpi-prod-cost">$0.00</div>
                    </div>
                    <div class="kpi-icon-container">
                        <i class="fa-solid fa-industry"></i>
                    </div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-info">
                        <h4>Transport Cost</h4>
                        <div class="kpi-value" id="kpi-transport-cost">$0.00</div>
                    </div>
                    <div class="kpi-icon-container">
                        <i class="fa-solid fa-truck"></i>
                    </div>
                </div>
            </div>

            <!-- Infeasible Alert -->
            <div id="infeasible-alert" style="display: none; background: rgba(239, 68, 68, 0.15); border: 1px solid var(--accent-danger); padding: 1rem; border-radius: 12px; color: #fecaca; margin-bottom: 1.5rem;">
                <i class="fa-solid fa-triangle-exclamation" style="color: var(--accent-danger); margin-right: 0.5rem;"></i>
                <strong>Model is Infeasible!</strong> The committed demands exceed the available fat/protein components in the milk. Please reduce the committed demands or increase the milk supply.
            </div>

            <!-- Dashboard Grid / Charts & Tables -->
            <div class="dashboard-grid">
                
                <!-- Product Yields / Sales Chart -->
                <div class="card">
                    <div class="card-title">
                        <span>Production Output by Product (Tons)</span>
                        <i class="fa-solid fa-chart-pie text-secondary"></i>
                    </div>
                    <div style="position: relative; height:300px;">
                        <canvas id="productionChart"></canvas>
                    </div>
                </div>

                <!-- Plant Milk Intake & Capacity Chart -->
                <div class="card">
                    <div class="card-title">
                        <span>Plant Capacity & Utilization</span>
                        <i class="fa-solid fa-gauge-high text-secondary"></i>
                    </div>
                    <div style="position: relative; height:300px;">
                        <canvas id="utilizationChart"></canvas>
                    </div>
                </div>

                <!-- Sales Allocation Table -->
                <div class="card" style="grid-column: span 2;">
                    <div class="card-title">
                        <span>Sales Allocation & Demand Satisfaction</span>
                        <span class="badge badge-success">Optimized Solution</span>
                    </div>
                    <div class="table-container">
                        <table>
                            <thead>
                                <tr>
                                    <th>Plant</th>
                                    <th>Product</th>
                                    <th>Quantity Sold (Tons)</th>
                                    <th>Committed Demand</th>
                                    <th>Optional Demand</th>
                                    <th>Revenue Generated</th>
                                </tr>
                            </thead>
                            <tbody id="sales-table-body">
                                <tr>
                                    <td colspan="6" style="text-align: center;" class="text-secondary">Please click "Solve LP Model" to run the optimization.</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>

            </div>

        </div>

        <!-- Tab 4 Panel: History logs -->
        <div id="tab-history" class="tab-panel" style="display: none;">
            <div class="card">
                <div class="card-section-title">
                    <i class="fa-solid fa-clock-rotate-left"></i> S&OP Optimization Run Archives
                </div>
                <p class="text-secondary" style="margin-bottom: 1.5rem; font-size: 0.9rem;">
                    Every successful or attempted S&OP optimization solve is securely archived in the SQLite datastore. Click "Review Run" to retrieve its historical configuration parameters and outcomes.
                </p>
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>Solve Timestamp (Date)</th>
                                <th>Solver Outcome</th>
                                <th>Total VCM</th>
                                <th>Total Revenue</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody id="history-table-body">
                            <tr>
                                <td colspan="5" style="text-align: center;" class="text-secondary">Loading history logs...</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

    </div>

    <script>
        let productionChart = null;
        let utilizationChart = null;

        // Switch active tab view
        function switchTab(tabId) {
            // Hide all panels
            document.querySelectorAll(".tab-panel").forEach(p => p.style.display = "none");
            // Show active panel
            document.getElementById(tabId).style.display = "block";

            // Remove active classes from buttons
            document.querySelectorAll(".tab-nav-btn").forEach(b => b.classList.remove("active"));
            // Add active class to corresponding nav button
            const targetBtnId = "nav-btn-" + tabId.replace("tab-", "");
            document.getElementById(targetBtnId).classList.add("active");

            // Load history if active tab is history
            if (tabId === "tab-history") {
                loadHistory();
            }
        }

        // Default inputs mapping to standard dataset
        function getPayloadFromForm() {
            return {
                supply_data: [
                    { region: "North", volume: parseFloat(document.getElementById("supply_north").value), fat: parseFloat(document.getElementById("fat_north").value), protein: parseFloat(document.getElementById("protein_north").value), lactose: parseFloat(document.getElementById("lactose_north").value) },
                    { region: "South", volume: parseFloat(document.getElementById("supply_south").value), fat: parseFloat(document.getElementById("fat_south").value), protein: parseFloat(document.getElementById("protein_south").value), lactose: parseFloat(document.getElementById("lactose_south").value) },
                    { region: "East", volume: parseFloat(document.getElementById("supply_east").value), fat: parseFloat(document.getElementById("fat_east").value), protein: parseFloat(document.getElementById("protein_east").value), lactose: parseFloat(document.getElementById("lactose_east").value) },
                    { region: "West", volume: parseFloat(document.getElementById("supply_west").value), fat: parseFloat(document.getElementById("fat_west").value), protein: parseFloat(document.getElementById("protein_west").value), lactose: parseFloat(document.getElementById("lactose_west").value) }
                ],
                plant_data: [
                    { plant: "Auckland", capacity: parseFloat(document.getElementById("cap_auckland").value), fixed_cost: parseFloat(document.getElementById("fix_auckland").value) },
                    { plant: "Hamilton", capacity: parseFloat(document.getElementById("cap_hamilton").value), fixed_cost: parseFloat(document.getElementById("fix_hamilton").value) },
                    { plant: "Christchurch", capacity: parseFloat(document.getElementById("cap_christchurch").value), fixed_cost: parseFloat(document.getElementById("fix_christchurch").value) }
                ],
                product_data: [
                    { product: "WMP", price: parseFloat(document.getElementById("price_wmp").value), production_cost: parseFloat(document.getElementById("cost_wmp").value), bom_fat: parseFloat(document.getElementById("bom_fat_wmp").value), bom_protein: parseFloat(document.getElementById("bom_prot_wmp").value), bom_lactose: parseFloat(document.getElementById("bom_lac_wmp").value) },
                    { product: "SMP", price: parseFloat(document.getElementById("price_smp").value), production_cost: parseFloat(document.getElementById("cost_smp").value), bom_fat: parseFloat(document.getElementById("bom_fat_smp").value), bom_protein: parseFloat(document.getElementById("bom_prot_smp").value), bom_lactose: parseFloat(document.getElementById("bom_lac_smp").value) },
                    { product: "Cheese", price: parseFloat(document.getElementById("price_cheese").value), production_cost: parseFloat(document.getElementById("cost_cheese").value), bom_fat: parseFloat(document.getElementById("bom_fat_cheese").value), bom_protein: parseFloat(document.getElementById("bom_prot_cheese").value), bom_lactose: parseFloat(document.getElementById("bom_lac_cheese").value) },
                    { product: "Butter", price: parseFloat(document.getElementById("price_butter").value), production_cost: parseFloat(document.getElementById("cost_butter").value), bom_fat: parseFloat(document.getElementById("bom_fat_butter").value), bom_protein: parseFloat(document.getElementById("bom_prot_butter").value), bom_lactose: parseFloat(document.getElementById("bom_lac_butter").value) }
                ],
                demand_data: [
                    { plant: "Auckland", product: "WMP", committed: parseFloat(document.getElementById("demand_ack_wmp").value), optional: parseFloat(document.getElementById("demand_ack_wmp_opt").value) },
                    { plant: "Auckland", product: "Butter", committed: parseFloat(document.getElementById("demand_ack_butter").value), optional: parseFloat(document.getElementById("demand_ack_butter_opt").value) },
                    { plant: "Hamilton", product: "Cheese", committed: parseFloat(document.getElementById("demand_ham_cheese").value), optional: parseFloat(document.getElementById("demand_ham_cheese_opt").value) },
                    { plant: "Hamilton", product: "SMP", committed: parseFloat(document.getElementById("demand_ham_smp").value), optional: parseFloat(document.getElementById("demand_ham_smp_opt").value) },
                    { plant: "Christchurch", product: "WMP", committed: parseFloat(document.getElementById("demand_chch_wmp").value), optional: parseFloat(document.getElementById("demand_chch_wmp_opt").value) },
                    { plant: "Christchurch", product: "Cheese", committed: parseFloat(document.getElementById("demand_chch_cheese").value), optional: parseFloat(document.getElementById("demand_chch_cheese_opt").value) }
                ],
                logistics_data: [
                    { region: "North", plant: "Auckland", cost: parseFloat(document.getElementById("log_n_ack").value) },
                    { region: "North", plant: "Hamilton", cost: parseFloat(document.getElementById("log_n_ham").value) },
                    { region: "North", plant: "Christchurch", cost: parseFloat(document.getElementById("log_n_chch").value) },
                    { region: "South", plant: "Auckland", cost: parseFloat(document.getElementById("log_s_ack").value) },
                    { region: "South", plant: "Hamilton", cost: parseFloat(document.getElementById("log_s_ham").value) },
                    { region: "South", plant: "Christchurch", cost: parseFloat(document.getElementById("log_s_chch").value) },
                    { region: "East", plant: "Auckland", cost: parseFloat(document.getElementById("log_e_ack").value) },
                    { region: "East", plant: "Hamilton", cost: parseFloat(document.getElementById("log_e_ham").value) },
                    { region: "East", plant: "Christchurch", cost: parseFloat(document.getElementById("log_e_chch").value) },
                    { region: "West", plant: "Auckland", cost: parseFloat(document.getElementById("log_w_ack").value) },
                    { region: "West", plant: "Hamilton", cost: parseFloat(document.getElementById("log_w_ham").value) },
                    { region: "West", plant: "Christchurch", cost: parseFloat(document.getElementById("log_w_chch").value) }
                ],
                global_constraints: {
                    milk_base_price: parseFloat(document.getElementById("milk_base_price").value)
                }
            };
        }

        function formatCurrency(val) {
            return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(val);
        }

        async function runOptimization() {
            const loader = document.getElementById("loader");
            const alertBox = document.getElementById("infeasible-alert");
            loader.style.display = "flex";
            alertBox.style.display = "none";
            
            try {
                const payload = getPayloadFromForm();
                const response = await fetch("/api/optimize", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload)
                });

                if (!response.ok) {
                    throw new Error("Failed to optimize model");
                }

                const data = await response.json();
                
                // Update Solver Status Display
                const statusEl = document.getElementById("kpi-status");
                const statusIcon = document.getElementById("kpi-status-icon");
                statusEl.innerText = data.status;
                
                if (data.status === "Optimal") {
                    statusEl.style.color = "var(--accent-success)";
                    statusIcon.style.color = "var(--accent-success)";
                    statusIcon.innerHTML = `<i class="fa-solid fa-square-check"></i>`;
                } else {
                    statusEl.style.color = "var(--accent-danger)";
                    statusIcon.style.color = "var(--accent-danger)";
                    statusIcon.innerHTML = `<i class="fa-solid fa-circle-xmark"></i>`;
                    alertBox.style.display = "block";
                }

                // Update KPI Cards
                document.getElementById("kpi-vcm").innerText = formatCurrency(data.vcm);
                document.getElementById("kpi-revenue").innerText = formatCurrency(data.revenue);
                document.getElementById("kpi-prod-cost").innerText = formatCurrency(data.production_cost);
                document.getElementById("kpi-transport-cost").innerText = formatCurrency(data.transport_cost);

                // Update Charts
                updateProductionChart(data.production);
                updateUtilizationChart(data.plant_utilization);

                // Update Table
                updateSalesTable(data.sales);

            } catch (err) {
                alert("Error during optimization solve: " + err.message);
            } finally {
                loader.style.display = "none";
            }
        }

        async function runOptimizationAndGoToResults() {
            await runOptimization();
            switchTab('tab-results');
        }

        function updateProductionChart(prodData) {
            const ctx = document.getElementById('productionChart').getContext('2d');
            
            // Sum products quantities
            const sums = {};
            prodData.forEach(p => {
                sums[p.product] = (sums[p.product] || 0) + p.quantity;
            });

            const labels = Object.keys(sums);
            const values = Object.values(sums);

            if (productionChart) {
                productionChart.destroy();
            }

            productionChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Tons Produced',
                        data: values,
                        backgroundColor: [
                            'rgba(59, 130, 246, 0.7)',
                            'rgba(16, 185, 129, 0.7)',
                            'rgba(245, 158, 11, 0.7)',
                            'rgba(139, 92, 246, 0.7)'
                        ],
                        borderColor: [
                            '#3b82f6',
                            '#10b981',
                            '#f59e0b',
                            '#8b5cf6'
                        ],
                        borderWidth: 1,
                        borderRadius: 8
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: { color: 'rgba(255, 255, 255, 0.05)' },
                            ticks: { color: '#94a3b8' }
                        },
                        x: {
                            grid: { display: false },
                            ticks: { color: '#94a3b8' }
                        }
                    }
                }
            });
        }

        function updateUtilizationChart(utilData) {
            const ctx = document.getElementById('utilizationChart').getContext('2d');
            
            const labels = utilData.map(u => u.plant);
            const utilizationPcts = utilData.map(u => Math.round((u.intake / u.capacity) * 100));

            if (utilizationChart) {
                utilizationChart.destroy();
            }

            utilizationChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Capacity Utilization %',
                        data: utilizationPcts,
                        backgroundColor: 'rgba(16, 185, 129, 0.7)',
                        borderColor: '#10b981',
                        borderWidth: 1,
                        borderRadius: 8
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 100,
                            grid: { color: 'rgba(255, 255, 255, 0.05)' },
                            ticks: { color: '#94a3b8', callback: value => value + "%" }
                        },
                        x: {
                            grid: { display: false },
                            ticks: { color: '#94a3b8' }
                        }
                    }
                }
            });
        }

        function updateSalesTable(salesData) {
            const tbody = document.getElementById("sales-table-body");
            tbody.innerHTML = "";
            
            if (salesData.length === 0) {
                tbody.innerHTML = "<tr><td colspan='6' style='text-align: center;' class='text-secondary'>No sales occurred. Solver state is empty.</td></tr>";
                return;
            }

            salesData.forEach(s => {
                const tr = document.createElement("tr");
                tr.innerHTML = `
                    <td><strong>${s.plant}</strong></td>
                    <td><span class="badge" style="background: rgba(59,130,246,0.15); color: #60a5fa;">${s.product}</span></td>
                    <td><strong class="text-main">${s.quantity.toFixed(1)} Tons</strong></td>
                    <td class="text-secondary">${s.committed} Tons</td>
                    <td class="text-secondary">${s.optional} Tons (Filled: ${s.optional_filled.toFixed(1)})</td>
                    <td class="text-success" style="font-weight: 600;">${formatCurrency(s.revenue)}</td>
                `;
                tbody.appendChild(tr);
            });
        }

        async function loadHistory() {
            const tbody = document.getElementById("history-table-body");
            tbody.innerHTML = "<tr><td colspan='5' style='text-align: center;'>Loading logs...</td></tr>";
            
            try {
                const response = await fetch("/api/history");
                if (!response.ok) throw new Error("Failed to load history list");
                const data = await response.json();
                
                tbody.innerHTML = "";
                if (data.length === 0) {
                    tbody.innerHTML = "<tr><td colspan='5' style='text-align: center;' class='text-secondary'>No past runs archived yet. Runs are auto-saved on click.</td></tr>";
                    return;
                }
                
                data.forEach(r => {
                    const statusBadge = r.status === "Optimal" ? "<span class='badge badge-success'>Optimal</span>" : `<span class='badge' style='background: rgba(239, 68, 68, 0.15); color: var(--accent-danger);'>${r.status}</span>`;
                    const tr = document.createElement("tr");
                    tr.innerHTML = `
                        <td><strong>${r.timestamp}</strong></td>
                        <td>${statusBadge}</td>
                        <td><strong class="text-success">${formatCurrency(r.vcm)}</strong></td>
                        <td>${formatCurrency(r.revenue)}</td>
                        <td>
                            <button class="btn btn-secondary" style="padding: 0.4rem 0.8rem; font-size: 0.8rem;" onclick="loadPastRun(${r.id})">
                                <i class="fa-solid fa-folder-open"></i> Review Run
                            </button>
                        </td>
                    `;
                    tbody.appendChild(tr);
                });
            } catch (err) {
                tbody.innerHTML = `<tr><td colspan='5' style='text-align: center; color: var(--accent-danger);'>Error: ${err.message}</td></tr>`;
            }
        }

        async function loadPastRun(runId) {
            const loader = document.getElementById("loader");
            loader.style.display = "flex";
            
            try {
                const response = await fetch("/api/history/" + runId);
                if (!response.ok) throw new Error("Failed to load archived run details");
                const data = await response.json();
                
                const inputs = data.inputs;
                
                // 1. Populate supply volumes & composition
                inputs.supply_data.forEach(s => {
                    const r = s.region.toLowerCase();
                    document.getElementById(`supply_${r}`).value = s.volume || 0;
                    document.getElementById(`fat_${r}`).value = s.fat || 0;
                    document.getElementById(`protein_${r}`).value = s.protein || 0;
                    document.getElementById(`lactose_${r}`).value = s.lactose || 0;
                });

                // 2. Populate plant capacity & fixed cost
                inputs.plant_data.forEach(p => {
                    const pl = p.plant.toLowerCase();
                    document.getElementById(`cap_${pl}`).value = p.capacity || 0;
                    document.getElementById(`fix_${pl}`).value = p.fixed_cost || 0;
                });

                // 3. Populate logistics costs
                inputs.logistics_data.forEach(l => {
                    const r = l.region.toLowerCase().charAt(0);
                    const plName = l.plant.toLowerCase();
                    const p = plName === "christchurch" ? "chch" : plName.substring(0, 3);
                    const elId = `log_${r}_${p}`;
                    const el = document.getElementById(elId);
                    if (el) el.value = l.cost;
                });

                // 4. Populate milk base price
                document.getElementById("milk_base_price").value = inputs.global_constraints?.milk_base_price || 0.45;

                // 5. Populate Product specs (Prices, costs, BOM)
                inputs.product_data.forEach(p => {
                    const prod = p.product.toLowerCase();
                    document.getElementById(`price_${prod}`).value = p.price;
                    document.getElementById(`cost_${prod}`).value = p.production_cost;
                    document.getElementById(`bom_fat_${prod}`).value = p.bom_fat;
                    document.getElementById(`bom_prot_${prod}`).value = p.bom_protein;
                    document.getElementById(`bom_lac_${prod}`).value = p.bom_lactose;
                });

                // 6. Populate Demands
                inputs.demand_data.forEach(d => {
                    const plName = d.plant.toLowerCase();
                    const pl = plName === "christchurch" ? "chch" : plName.substring(0, 3);
                    const prod = d.product.toLowerCase();
                    const commEl = document.getElementById(`demand_${pl}_${prod}`);
                    const optEl = document.getElementById(`demand_${pl}_${prod}_opt`);
                    if (commEl) commEl.value = d.committed;
                    if (optEl) optEl.value = d.optional;
                });

                // 7. Update results UI directly from the archived results payload
                const results = data.results;
                
                const statusEl = document.getElementById("kpi-status");
                const statusIcon = document.getElementById("kpi-status-icon");
                const alertBox = document.getElementById("infeasible-alert");
                
                statusEl.innerText = results.status;
                alertBox.style.display = "none";
                
                if (results.status === "Optimal") {
                    statusEl.style.color = "var(--accent-success)";
                    statusIcon.style.color = "var(--accent-success)";
                    statusIcon.innerHTML = `<i class="fa-solid fa-square-check"></i>`;
                } else {
                    statusEl.style.color = "var(--accent-danger)";
                    statusIcon.style.color = "var(--accent-danger)";
                    statusIcon.innerHTML = `<i class="fa-solid fa-circle-xmark"></i>`;
                    alertBox.style.display = "block";
                }

                document.getElementById("kpi-vcm").innerText = formatCurrency(results.vcm);
                document.getElementById("kpi-revenue").innerText = formatCurrency(results.revenue);
                document.getElementById("kpi-prod-cost").innerText = formatCurrency(results.production_cost);
                document.getElementById("kpi-transport-cost").innerText = formatCurrency(results.transport_cost);

                // Update charts and table
                updateProductionChart(results.production);
                updateUtilizationChart(results.plant_utilization);
                updateSalesTable(results.sales);
                
                // Go to results tab immediately to see outcomes
                switchTab('tab-results');
                alert("Run loaded successfully from historical archive!");

            } catch (err) {
                alert("Error loading archived run: " + err.message);
            } finally {
                loader.style.display = "none";
            }
        }

        function resetToDefaults() {
            // Reset base values
            document.getElementById("milk_base_price").value = "0.45";
            
            // Supply Defaults
            document.getElementById("supply_north").value = "500000";
            document.getElementById("fat_north").value = "4.2";
            document.getElementById("protein_north").value = "3.4";
            document.getElementById("lactose_north").value = "4.8";

            document.getElementById("supply_south").value = "400000";
            document.getElementById("fat_south").value = "4.0";
            document.getElementById("protein_south").value = "3.2";
            document.getElementById("lactose_south").value = "4.7";

            document.getElementById("supply_east").value = "300000";
            document.getElementById("fat_east").value = "4.5";
            document.getElementById("protein_east").value = "3.5";
            document.getElementById("lactose_east").value = "4.6";

            document.getElementById("supply_west").value = "600000";
            document.getElementById("fat_west").value = "3.8";
            document.getElementById("protein_west").value = "3.1";
            document.getElementById("lactose_west").value = "4.9";

            // Plant Capacities
            document.getElementById("cap_auckland").value = "800000";
            document.getElementById("fix_auckland").value = "15000";
            document.getElementById("cap_hamilton").value = "600000";
            document.getElementById("fix_hamilton").value = "12000";
            document.getElementById("cap_christchurch").value = "700000";
            document.getElementById("fix_christchurch").value = "14000";

            // Logistics defaults
            document.getElementById("log_n_ack").value = "0.02";
            document.getElementById("log_n_ham").value = "0.04";
            document.getElementById("log_n_chch").value = "0.09";
            document.getElementById("log_s_ack").value = "0.05";
            document.getElementById("log_s_ham").value = "0.03";
            document.getElementById("log_s_chch").value = "0.07";
            document.getElementById("log_e_ack").value = "0.06";
            document.getElementById("log_e_ham").value = "0.05";
            document.getElementById("log_e_chch").value = "0.02";
            document.getElementById("log_w_ack").value = "0.03";
            document.getElementById("log_w_ham").value = "0.02";
            document.getElementById("log_w_chch").value = "0.08";

            // Product specifications
            document.getElementById("price_wmp").value = "3200";
            document.getElementById("cost_wmp").value = "400";
            document.getElementById("bom_fat_wmp").value = "260";
            document.getElementById("bom_prot_wmp").value = "250";
            document.getElementById("bom_lac_wmp").value = "380";

            document.getElementById("price_smp").value = "2800";
            document.getElementById("cost_smp").value = "350";
            document.getElementById("bom_fat_smp").value = "10";
            document.getElementById("bom_prot_smp").value = "360";
            document.getElementById("bom_lac_smp").value = "500";

            document.getElementById("price_cheese").value = "4500";
            document.getElementById("cost_cheese").value = "600";
            document.getElementById("bom_fat_cheese").value = "300";
            document.getElementById("bom_prot_cheese").value = "250";
            document.getElementById("bom_lac_cheese").value = "10";

            document.getElementById("price_butter").value = "5200";
            document.getElementById("cost_butter").value = "500";
            document.getElementById("bom_fat_butter").value = "820";
            document.getElementById("bom_prot_butter").value = "10";
            document.getElementById("bom_lac_butter").value = "10";

            // Demands defaults
            document.getElementById("demand_ack_wmp").value = "10";
            document.getElementById("demand_ack_wmp_opt").value = "200";
            document.getElementById("demand_ack_butter").value = "5";
            document.getElementById("demand_ack_butter_opt").value = "100";

            document.getElementById("demand_ham_cheese").value = "10";
            document.getElementById("demand_ham_cheese_opt").value = "150";
            document.getElementById("demand_ham_smp").value = "10";
            document.getElementById("demand_ham_smp_opt").value = "120";

            document.getElementById("demand_chch_wmp").value = "10";
            document.getElementById("demand_chch_wmp_opt").value = "180";
            document.getElementById("demand_chch_cheese").value = "10";
            document.getElementById("demand_chch_cheese_opt").value = "110";

            runOptimization();
        }

        // Auto-run first solve on load
        window.addEventListener("DOMContentLoaded", () => {
            runOptimization();
        });
    </script>
</body>
</html>
"""
    return HTMLResponse(content=html_content)

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
