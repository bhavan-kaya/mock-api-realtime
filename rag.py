from typing import Any, Dict, List, Optional

import spacy
import psycopg2
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVector
from spacy.cli import download

from config import (
    COLLECTION_NAME,
    CONNECTION_STRING,
    EMBEDDING_MODEL,
    DB_HOST,
    DB_NAME,
    DB_USER,
    DB_PASSWORD,
    DB_PORT,
    SPACY_MODEL,
    COLLECTION_ID,
    REALTIME_MAX_TOKENS,
)
from singleton import SingletonMeta


class PGVectorStore(metaclass=SingletonMeta):
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
            print(
                f"Database: {DB_NAME}, Host: {DB_HOST}, Port: {DB_PORT}m User: {DB_USER}"
            )
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
        for doc in docs:
            try:
                self.store.add_documents([doc], ids=[doc.metadata["id"]])
            except Exception as e:
                print(f"Failed to add document {doc.metadata.get('id')}: {e}")

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

            embedding = self.embedding_function.embed_query(query)
            filter_clause = self.build_filter_query(filter)

            query_sql = f"""
                SELECT document, cmetadata, embedding 
                FROM langchain_pg_embedding 
                WHERE collection_id = %s
                {f'AND {filter_clause}' if filter_clause else ''} 
                ORDER BY embedding <-> %s::vector 
                LIMIT {k};
            """

            with self.connection.cursor() as cur:
                cur.execute(query_sql, (COLLECTION_ID, embedding))
                results = cur.fetchall()

            return [
                Document(page_content=row[0], metadata=row[1] if row[1] else {})
                for row in results
            ]
        except Exception as e:
            print(f"Failed fetch: {str(e)}")

    def hybrid_search(
        self,
        query: str,
        filter: dict,
        k: Optional[int] = 10,
        weight: float = 0.5,
        use_entities: bool = False,
    ):
        try:
            print("Collection ID for current search: ", COLLECTION_ID)
            print("Collection Name for current search: ", COLLECTION_NAME)
            print("Database Name:", DB_NAME)
            print("Query for hybrid search: ", query)
            print("Filter for hybrid search: ", filter)
            print("Weight for hybrid search: ", weight)
            if not (0 <= weight <= 1):
                raise ValueError("Weight must be between 0 and 1.")

            if use_entities:
                entities = self.extract_entities(query)
                print("Extracted Entities: ", entities)
                query = " ".join(entities.values())

            embedding = self.embedding_function.embed_query(query)
            filter_clause = self.build_filter_query(filter)

            sql = f"""
                SELECT document, cmetadata, 
                       (ts_rank_cd(to_tsvector('english', document), plainto_tsquery('english', %s)) * {1 - weight}) +
                       ((1 - (embedding <-> %s::vector)) * {weight}) AS hybrid_score
                FROM langchain_pg_embedding
                WHERE collection_id = %s
                {f'AND {filter_clause}' if filter_clause else ''}
                ORDER BY hybrid_score DESC
                LIMIT {k};
            """

            print("Text for hybrid search: ", query)
            with self.connection.cursor() as cur:
                cur.execute(sql, (query, embedding, COLLECTION_ID))
                results = cur.fetchall()

            return [
                Document(page_content=row[0], metadata=row[1] if row[1] else {})
                for row in results
            ]
        except Exception as e:
            print(f"Failed hybrid search: {str(e)}")

    def delete_documents(self):
        pass

    def search_vehicle_inventory(
        self,
        vin: Optional[str] = None,
        stock_number: Optional[str] = None,
        vehicle_type: Optional[str] = None,
        year: Optional[int] = None,
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
        engine_type: Optional[str] = None,
        features: Optional[str] = None,
        packages: Optional[str] = None,
        fields: Optional[str] = None,
        description: Optional[str] = None,
        options: Optional[str] = None,
        context_limit: int = None,
    ):
        try:
            columns = [field.strip() for field in fields.split(",")] if fields else []
            default_columns = [
                "vin",
                "stock_number",
                "type",
                "year",
                "make",
                "model",
                "trim",
                "style",
                "model_number",
                "mileage",
                "exterior_color",
                "interior_color",
                "msrp",
                "selling_price",
                "drive_type",
                "fuel_type",
                "transmission",
                "wheelbase",
                "body",
                "doors",
                "vehicle_status",
                "city_fuel_economy",
                "highway_fuel_economy",
                "features",
                "packages",
            ]
            all_columns = default_columns + columns
            print("Columns to return: ", all_columns)

            # Start building the query with token count estimation
            query = """
                WITH filtered AS (
                    SELECT
                        vin,
                        stock_number,
                        type,
                        year,
                        make,
                        model,
                        trim,
                        style,
                        model_number,
                        mileage,
                        exterior_color,
                        exterior_color_code,
                        interior_color,
                        interior_color_code,
                        date_in_stock,
                        certified,
                        msrp,
                        invoice,
                        book_value,
                        selling_price,
                        engine_cylinders,
                        engine_displacement,
                        drive_type,
                        fuel_type,
                        transmission,
                        wheelbase,
                        body,
                        doors,
                        description,
                        options,
                        kbb_retail,
                        kbb_valuation_date,
                        kbb_zip_code,
                        added_equipment_pricing,
                        dealer_processing_fee,
                        location,
                        vehicle_status,
                        engine_type,
                        drive_line,
                        transmission_secondary,
                        city_fuel_economy,
                        highway_fuel_economy,
                        features,
                        packages,
                        (
                            COALESCE(LENGTH(vin), 0) +
                            COALESCE(LENGTH(stock_number), 0) +
                            COALESCE(LENGTH(type), 0) +
                            COALESCE(LENGTH(make), 0) +
                            COALESCE(LENGTH(model), 0) +
                            COALESCE(LENGTH(trim), 0) +
                            COALESCE(LENGTH(style), 0) +
                            COALESCE(LENGTH(exterior_color), 0) +
                            COALESCE(LENGTH(interior_color), 0) +
                            COALESCE(LENGTH(fuel_type), 0) +
                            COALESCE(LENGTH(transmission), 0) +
                            COALESCE(LENGTH(drive_type), 0) +
                            COALESCE(LENGTH(engine_type), 0) +
                            COALESCE(LENGTH(features), 0) +
                            COALESCE(LENGTH(packages), 0) +
                            COALESCE(LENGTH(description), 0) +
                            COALESCE(LENGTH(options), 0)
                        ) / 5 AS estimated_token_count
                    FROM demo_vehicle_inventory
                    WHERE TRUE
            """

            params: Dict[str, Any] = {}

            # Dynamic Filtering Based on User Inputs
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
            if engine_type:
                query += " AND engine_type ILIKE %(engine_type)s"
                params["engine_type"] = f"%{engine_type}%"
            if features:
                query += " AND features ILIKE %(features)s"
                params["features"] = f"%{features}%"
            if packages:
                query += " AND packages ILIKE %(packages)s"
                params["packages"] = f"%{packages}%"

            query += """
                )
                , cumulative AS (
                    SELECT
                        *,
                        SUM(estimated_token_count) OVER (ORDER BY date_in_stock ASC) AS cumulative_tokens
                    FROM filtered
                )
                SELECT
                    vin,
                    stock_number,
                    type,
                    year,
                    make,
                    model,
                    trim,
                    style,
                    model_number,
                    mileage,
                    exterior_color,
                    exterior_color_code,
                    interior_color,
                    interior_color_code,
                    date_in_stock,
                    certified,
                    msrp,
                    invoice,
                    book_value,
                    selling_price,
                    engine_cylinders,
                    engine_displacement,
                    drive_type,
                    fuel_type,
                    transmission,
                    wheelbase,
                    body,
                    doors,
                    description,
                    options,
                    kbb_retail,
                    kbb_valuation_date,
                    kbb_zip_code,
                    added_equipment_pricing,
                    dealer_processing_fee,
                    location,
                    vehicle_status,
                    engine_type,
                    drive_line,
                    transmission_secondary,
                    city_fuel_economy,
                    highway_fuel_economy,
                    features,
                    packages
                FROM cumulative
                WHERE cumulative_tokens <= %(context_limit)s
                ORDER BY date_in_stock ASC;
            """

            params["context_limit"] = context_limit

            # Execute the query
            with self.connection.cursor() as cur:
                print("Query:", cur.mogrify(query, params))  # Debugging
                cur.execute(query, params)
                results = cur.fetchall()
                columns = [desc[0] for desc in cur.description]
                data = [dict(zip(columns, row)) for row in results]

            # Filter the columns to return
            data = [{k: v for k, v in d.items() if k in all_columns} for d in data]

            return {"data": data}

        except Exception as e:
            return {"error": str(e)}

    def extract_entities(self, query: str):
        try:
            nlp = spacy.load(SPACY_MODEL)
        except OSError:
            print(f"Model '{SPACY_MODEL}' not found. Downloading...")
            download(SPACY_MODEL)
            nlp = spacy.load(SPACY_MODEL)
        doc = nlp(query)
        entities = {ent.label_: ent.text for ent in doc.ents}
        return entities
