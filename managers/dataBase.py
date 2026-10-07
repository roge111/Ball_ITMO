from dotenv import load_dotenv
import psycopg2
import os
from psycopg2 import OperationalError, InterfaceError, DatabaseError

load_dotenv()

class DataBaseManager:
    def __init__(self):
        self.connection = None
        try:
            self.connection = self._connect()
        except Exception as e:
            print(f"Ошибка при подключении к БД: {e}")
            raise  # Пробрасываем исключение дальше для обработки на уровне приложения

    def _connect(self):
        try:
            print(os.getenv('DB_NAME'))
            connect = psycopg2.connect(
                host=os.getenv('HOST_DB'),
                port=os.getenv('PORT_DB'),
                dbname=os.getenv('DB_NAME'),
                user=os.getenv('USER_DB'),
                password=os.getenv('PASSWORD_DB'), 
                client_encoding=os.getenv('CLIENT_ENCODING_DB')
                
            )
            print("Успешное подключение к БД")
            return connect
        except OperationalError as e:
            print(f"Ошибка подключения к серверу БД: {e}")
            raise
        except Exception as e:
            print(f"Неизвестная ошибка при подключении: {e}")
            raise

    def query_database(self, query, params=None, fetch_one=False, reg=False):
        if not self.connection:
            raise DatabaseError("Нет подключения к БД")
            
        cursor = None
        try:
            cursor = self.connection.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
                
            if not reg:
                result = cursor.fetchone() if fetch_one else cursor.fetchall()
                self.connection.commit()
                return result
                
            self.connection.commit()
            return None
            
        except (OperationalError, InterfaceError) as e:
            print(f"Ошибка выполнения запроса: {e}")
            self.connection.rollback()
            raise
        except Exception as e:
            print(f"Неизвестная ошибка при выполнении запроса: {e}")
            self.connection.rollback()
            raise
        finally:
            if cursor:
                cursor.close()

    def close(self):
        try:
            if self.connection and not self.connection.closed:
                self.connection.close()
                print("Соединение с БД закрыто")
        except Exception as e:
            print(f"Ошибка при закрытии соединения: {e}")
            raise

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()