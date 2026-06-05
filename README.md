# ECOMPRO Backend

Backend-only enterprise e-commerce order management system built with FastAPI, MySQL, SQLAlchemy ORM, Pydantic, JWT authentication, and bcrypt password hashing.

## Setup

1. Create a MySQL database:

```sql
CREATE DATABASE ecompro;
```

Or run the full manual schema:

```bash
mysql -u root -p < database/schema.sql
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and update the MySQL credentials and JWT secret.

4. Start the API:

```bash
uvicorn main:app --reload
```

5. Open Swagger docs:

```text
http://127.0.0.1:8000/docs
```

## Notes

- Tables are created on startup for a simple project workflow.
- Use a migration tool like Alembic before deploying this to production.
- Access tokens are sent through the `Authorization: Bearer <token>` header.
- Customers can place orders only from available stock. Inventory is reduced only after successful payment.
- Coupons are single-use per customer.
- Duplicate product reviews are blocked at both API and database levels.
- Unpaid orders can be auto-cancelled through `POST /orders/maintenance/auto-cancel-unpaid`.

## Official References Used

- FastAPI security and JWT: https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/
- FastAPI larger applications: https://fastapi.tiangolo.com/tutorial/bigger-applications/
- SQLAlchemy ORM relationships: https://docs.sqlalchemy.org/en/20/orm/basic_relationships.html
- Pydantic models: https://docs.pydantic.dev/latest/concepts/models/
