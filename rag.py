import os
from typing import Any, Dict, List, Optional

import psycopg2
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVector

COLLECTION_NAME = os.getenv("COLLECTION_NAME", "test-v1")
CONNECTION_STRING = os.getenv(
    "CONNECTION_STRING",
    "postgresql+psycopg://bhavan:mysecretpassword@localhost:5433/new-db",
)
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-ada-002")
DB_HOST = os.getenv(
    "DB_HOST", "/cloudsql/kaya-workloads-dev-397311:us-west1:kaya-dev-pg-d2c4236b"
)
DB_NAME = os.getenv("DB_NAME", "kaya-dev")
DB_USER = os.getenv("DB_USER", "kayadevadmin")
DB_PASSWORD = os.getenv("DB_PASSWORD", "gtAupasSTbA2uPQj7hyYMBqG")
DB_PORT = os.getenv("DB_PORT", "5432")


class PGVectorStore:
    def __init__(self):
        self.collection_name = COLLECTION_NAME
        self.connection_string = CONNECTION_STRING
        self.embedding_function = OpenAIEmbeddings(model=EMBEDDING_MODEL)

        self.store = self.initialize_store()
        self.connection = self.initialize_db()

    def initialize_store(self):
        return PGVector(
            embeddings=self.embedding_function,
            collection_name=self.collection_name,
            connection=self.connection_string,
            use_jsonb=True,
        )

    def initialize_db(self):
        try:
            return psycopg2.connect(
                host=DB_HOST,
                database=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD,
                port=DB_PORT,
            )
        except psycopg2.Error as e:
            raise ConnectionError(f"Failed to connect to database: {str(e)}")

    def add_documents(self, docs: List[Document]):
        # Adding documents to the vector store
        self.store.add_documents(docs, ids=[doc.metadata["id"] for doc in docs])

    def build_filter_query(self, filter_dict: Dict[str, Any]) -> str:
        if not filter_dict:
            return ""

        conditions = []
        for key, value in filter_dict.items():
            if isinstance(value, (int, float)):
                conditions.append(f"cmetadata ->> '{key}' = '{value}'")
            elif isinstance(value, str):
                conditions.append(f"cmetadata ->> '{key}' = '{value}'")
            elif isinstance(value, list):
                values = "','".join(str(v) for v in value)
                conditions.append(f"cmetadata ->> '{key}' IN ('{values}')")

        return " AND ".join(conditions)

    def similarity_search(
        self, query: str, filter: dict, k: Optional[int] = 10, native: bool = False
    ):
        try:
            if not native:
                return self.store.similarity_search(query, k=k, filter=filter)

            embedding = self.store.embeddings.embed_query(query)
            filter_clause = self.build_filter_query(filter)

            query_sql = f"SELECT document, cmetadata, embedding FROM langchain_pg_embedding WHERE collection_id = 'a48cfbe5-f71b-4138-af8a-c0b570445b0b' {f'AND {filter_clause}' if filter_clause else ''} ORDER BY embedding <-> '{embedding}' LIMIT {k};"
            # print("Query SQL: ", query_sql)

            with self.connection.cursor() as cur:
                cur.execute(query_sql)
                results = cur.fetchall()

            # print(results)
            return [
                Document(page_content=row[0], metadata=row[1] if row[1] else {})
                for row in results
            ]
        except Exception as e:
            print(f"Failed fetch: {str(e)}")

    def delete_documents(self):
        pass

    def search_vehicle_inventory(
        self,
        vin: Optional[str] = None,
        stock_number: Optional[str] = None,
        vehicle_type: Optional[str] = None,
        year: Optional[str] = None,
        make: Optional[str] = None,
        model: Optional[str] = None,
        trim: Optional[str] = None,
        style: Optional[str] = None,
        exterior_color: Optional[str] = None,
        interior_color: Optional[str] = None,
        certified: Optional[bool] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        fuel_type: Optional[str] = None,
        transmission: Optional[str] = None,
        drive_type: Optional[str] = None,
        doors: Optional[int] = None,
        description: Optional[str] = None,
    ):
        try:
            # Start building the query
            query = "SELECT * FROM demo_vehicle_inventory WHERE TRUE"
            params: Dict[str, Any] = {}

            # Add filtering conditions based on provided parameters
            if vin:
                query += " AND vin = %(vin)s"
                params["vin"] = vin
            if stock_number:
                query += " AND stock_number ILIKE %(stock_number)s"
                params["stock_number"] = f"%{stock_number}%"
            if vehicle_type:
                query += " AND type ILIKE %(vehicle_type)s"
                params["vehicle_type"] = f"%{vehicle_type}%"
            if year:
                query += " AND year = %(year)s"
                params["year"] = year
            if make:
                query += " AND make ILIKE %(make)s"
                params["make"] = f"%{make}%"
            if model:
                query += " AND model ILIKE %(model)s"
                params["model"] = f"%{model}%"
            if trim:
                query += " AND trim ILIKE %(trim)s"
                params["trim"] = f"%{trim}%"
            if style:
                query += " AND style ILIKE %(style)s"
                params["style"] = f"%{style}%"
            if exterior_color:
                query += " AND exterior_color ILIKE %(exterior_color)s"
                params["exterior_color"] = f"%{exterior_color}%"
            if interior_color:
                query += " AND interior_color ILIKE %(interior_color)s"
                params["interior_color"] = f"%{interior_color}%"
            if certified is not None:
                query += " AND certified = %(certified)s"
                params["certified"] = certified
            if min_price:
                query += " AND selling_price >= %(min_price)s"
                params["min_price"] = min_price
            if max_price:
                query += " AND selling_price <= %(max_price)s"
                params["max_price"] = max_price
            if fuel_type:
                query += " AND fuel_type ILIKE %(fuel_type)s"
                params["fuel_type"] = f"%{fuel_type}%"
            if transmission:
                query += " AND transmission ILIKE %(transmission)s"
                params["transmission"] = f"%{transmission}%"
            if drive_type:
                query += " AND drive_type ILIKE %(drive_type)s"
                params["drive_type"] = f"%{drive_type}%"
            if doors:
                query += " AND doors = %(doors)s"
                params["doors"] = doors
            if description:
                query += " AND description ILIKE %(description)s"
                params["description"] = f"%{description}%"

            # Execute the query
            with self.connection.cursor() as cur:
                print("Query:", query)
                cur.execute(
                    query, params
                )  # Pass params to safely substitute placeholders
                results = cur.fetchall()
                columns = [desc[0] for desc in cur.description]
                data = [dict(zip(columns, row)) for row in results]

            return {"data": data}

        except Exception as e:
            return {"error": str(e)}
