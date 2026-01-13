Logistics Risk Management System

This is a web application for managing logistics and predicting delivery risks using Machine Learning. It helps companies track orders, manage drivers, and see analytics in real-time.

 Key Features

    User Roles: Different access for Admin, Manager, Driver, and Client.

Order Management: Create, edit, and track orders with statuses like "New", "In Transit", and "Delivered".

AI Risk Assessment: A Machine Learning (Random Forest) model predicts if a delivery is High, Medium, or Low risk .

Dashboard & Analytics: Real-time stats on total orders and risks.

Order Timeline: Automatically logs every status change for history.

Data Export: Download order reports in CSV format.

 Tech Stack

    Backend: FastAPI (Python 3.13).

    Database: PostgreSQL with SQLAlchemy ORM.

    Migrations: Alembic.

    Machine Learning: Scikit-learn (Random Forest Model).

    Security: JWT Authentication.

    Container: Docker & Docker-compose.

 Project Structure
Plaintext

logistics_project/
├── alembic/            # Database migrations
├── app/
│   ├── core/           # Security and Database config
│   ├── models/         # SQLAlchemy models (User, Order)
│   ├── schemas/        # Pydantic schemas
│   ├── services/       # ML logic and .pkl model file
│   └── main.py         # Main API routes
├── ml_research/        # Dataset and model training code
├── docker-compose.yml  # Docker configuration
└── requirements.txt    # Python dependencies

 How to Run

    Clone the project:
    Bash

git clone <your-repository-url>
cd logistics_project

Start with Docker:
Bash

docker-compose up --build

Run Migrations:
Bash

    docker-compose exec app alembic upgrade head

 API Documentation

Once the server is running, you can see the interactive API documentation at:

    Swagger UI: http://127.0.0.1:8000/docs.

 Why Machine Learning?

Instead of using simple math, this system uses a Random Forest Classifier. It analyzes distance, cargo type, and time to give a smart risk level, making the logistics process safer and more predictable.