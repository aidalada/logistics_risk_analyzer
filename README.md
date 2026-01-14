# Logistics Risk Management System

This is a web application for managing logistics and predicting delivery risks using **Machine Learning**. It helps companies track orders, manage drivers, and see analytics in real-time.



## Key Features

**User Roles**: Different access levels for Admin, Manager, Driver, and Client.
**Order Management**: Create, search, and track orders with statuses like "New", "In Transit", "Delivered", and "Cancelled".
**AI Risk Assessment**: A **Machine Learning (Random Forest)** model predicts if a delivery is High, Medium, or Low risk based on distance, cargo type, and timing.
**Dashboard & Analytics**: Real-time stats on total orders and risk distribution.
**Order Timeline**: Automatically logs every status change for a full history of the order.
**Data Export**: Download order reports in **CSV** format for business analysis.

## Tech Stack

* **Backend**: FastAPI (Python 3.13).
* **Database**: PostgreSQL with SQLAlchemy ORM.
* **Migrations**: Alembic.
* **Machine Learning**: Scikit-learn (Random Forest Classifier).
* **Security**: JWT Authentication (Login/Register/Protected Routes).
* **Infrastructure**: Docker & Docker-compose.

## Project Structure

```text
logistics_project/
├── alembic/            # Database migrations and version control
├── app/
│   ├── core/           # Security, JWT, and Database connection
│   ├── models/         # Database models (User, Order, OrderHistory)
│   ├── schemas/        # Pydantic data validation schemas
│   ├── services/       # ML service and .pkl model files
│   └── main.py         # Main API routes and logic
├── ml_research/        # Dataset and model training notebooks/scripts
├── docker-compose.yml  # Docker environment setup
└── requirements.txt    # Project dependencies
```


## How to Run
1) Clone the repository:
Bash

git clone <your-repository-url>
cd logistics_project

2) Start the system with Docker:
Bash

docker-compose up --build

3) Apply database migrations:
Bash

docker-compose exec app alembic upgrade head

## API Documentation
The API documentation is automatically generated. Once the server is running, visit:
* **Swagger UI**: http://127.0.0.1:8000/docs

##  Why use Machine Learning?
Instead of using fixed rules, this system uses a Random Forest model trained on historical data. It provides a percentage-based risk score, helping managers prioritize high-risk deliveries and reduce potential delays.
