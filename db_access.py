import mysql.connector
from typing import Optional
from dataclasses import dataclass
from contextlib import contextmanager
import logging
import os
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger("user-data")
logger.setLevel(logging.INFO)

@dataclass
class Customer:
    phone: str
    name: str
    points: int

class DatabaseAccess:
    def __init__(self,
                 user: str = os.getenv("DB_USER"),
                 password: str = os.getenv("DB_PASS"),
                 host: str = os.getenv("DB_HOST"),
                 database: str = os.getenv("DB_NAME"),
                 ssl_ca: str = os.getenv("DB_SSL_CA", "./BaltimoreCyberTrustRoot.crt.pem"),
                 port: int = 3306):
        self.db_config = {
            "user": user,
            "password": password,
            "host": host,
            "database": database,
            "port": port,
            "ssl_ca": ssl_ca,
        }
        self._init_db()

    @contextmanager
    def _get_connection(self):
        conn = mysql.connector.connect(**self.db_config)
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS customers (
                    phone VARCHAR(20) PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    points INT DEFAULT 0
                )
            """)
            conn.commit()

    def create_customer(self, phone: str, name: str, points: int) -> Customer:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "INSERT INTO customers (phone, name, points) VALUES (%s, %s, %s)",
                    (phone, name, points)
                )
                conn.commit()
                return Customer(phone=phone, name=name, points=points)
            except mysql.connector.Error as e:
                logger.error("Error inserting customer: %s", e)
                raise

    def get_customer_by_phone(self, phone: str) -> Optional[Customer]:
        logger.info("Querying DB for phone = %r", phone)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT phone, name, points FROM customers WHERE phone = %s",
                (phone,)
            )
            row = cursor.fetchone()
            logger.info("DB row returned: %r", row)

            if row:
                return Customer(phone=row[0], name=row[1], points=row[2])
            return None
