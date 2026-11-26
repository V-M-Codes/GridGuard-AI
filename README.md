# GridGuard AI – Intelligent Microgrid Control Center

GridGuard AI is an intelligent microgrid monitoring and control platform designed to simulate and manage microgrid operations during normal conditions and power outages.

The platform provides real-time telemetry, battery energy storage monitoring, emergency generator management, weather-based solar generation simulation, and automated resilience testing.

## Key Features

- Real-time microgrid status monitoring.
- Battery Energy Storage System (BESS) monitoring.
- Emergency generator control and monitoring.
- Power outage simulation and grid restoration.
- Weather-based solar generation simulation.
- Real-time telemetry using Server-Sent Events (SSE).
- Automated black-start resilience testing.
- Event logs and system reset functionality.

## Technologies Used

- Python
- Flask
- Flask-CORS
- HTML
- CSS
- JavaScript
- Server-Sent Events (SSE)

## Project Structure

```text
GridGuard-AI/
│
├── Backened/
│   ├── app.py
│   ├── config.py
│   ├── microgrid_engine.py
│   ├── gridguard_server.py
│   ├── requirements.txt
│   └── test_gridguard_backened.py
│
├── Frontend/
│   └── index.html
│
├── .gitignore
└── README.md
```

## Local Setup

1. Clone the repository:

```bash
git clone https://github.com/V-M-Codes/GridGuard-AI.git
```

2. Install dependencies:

```bash
pip install -r Backened/requirements.txt
```

3. Start the Flask application from the project root:

```bash
python -m Backened.app
```

4. Open your browser:

```text
http://127.0.0.1:5000
```

## Project Objective

To demonstrate intelligent microgrid monitoring, control, and resilience through a simulated environment that integrates renewable energy generation, battery storage, emergency power management, and real-time system monitoring.

## Project

Developed as part of the Green Pulse Hackathon.

## Live Demo: https://gridguard-ai-2n4m.onrender.com

## Source Code: https://github.com/V-M-Codes/GridGuard-AI
