# FastAPI-Boilerplate

This is a FastAPI project boilerplate.
This project is running on FastAPI and Python 3.12+

# Introduction

The goal of this project is to provide a clean and scalable FastAPI architecture with JWT authentication and essential modules.

_This boilerplate covers the following features_

* JWT Authentication
* User Registration & Login
* Password Reset via Email
* Password Change
* SQLAlchemy ORM Integration
* Alembic Migrations
* Environment Configuration
* Modular Project Structure
* Email Support (SMTP)

# Project Setup

To use this project on your own machine, follow these steps.

### Clone repository from GitHub
```
git clone https://github.com/yourusername/fastapi-auth-boilerplate.git
cd fastapi-auth-boilerplate
```

### Create a virtual environment
```
python -m venv venv
source venv/bin/activate #On Windows: venv\Scripts\activate
```

### Install the dependencies
```
pip install -r requirements.txt
```

### Make an .env file

Copy the example environment file.
```
cp .env.example .env
```

Then update it with your own configuration:

```
DATABASE_URL=sqlite:///./test.db
SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
SMTP_SERVER=smtp.example.com
SMTP_PORT=587
SMTP_USER=your-email@example.com
SMTP_PASSWORD=your-password
```

# Running the Application

To run the development server:
```
uvicorn src.main:app --reload
```

Visit the Swagger UI:

[http://localhost:8000/docs](http://localhost:8000/docs)

Visit the ReDoc documentation:

[http://localhost:8000/redoc](http://localhost:8000/redoc)

# Database Setup

Initialize database:
```
alembic upgrade head
```

Create new migration after modifying models:

```
alembic revision --autogenerate -m "Your migration message"
alembic upgrade head
```

# Project Layout
```
fastapi-auth-boilerplate
├── alembic/
├── src/
│ ├── core/ # Configuration and security
│ ├── models/ # SQLAlchemy models
│ ├── routers/ # API routers
│ ├── schemas/ # Pydantic schemas
│ ├── services/ # Business logic
│ ├── utils/ # Utility functions
│ └── main.py # FastAPI application instance
├── .env.example
├── .gitignore
├── alembic.ini
├── requirements.txt
└── README.md
```

# API Endpoints

Swagger UI:
[http://localhost:8000/docs](http://localhost:8000/docs)

ReDoc:
[http://localhost:8000/redoc](http://localhost:8000/redoc)


# License
This project is licensed under the MIT License.