import os

INGESTION_TEMPLATE_ONE = """You are a highly knowledgeable assistant tasked with creating a detailed vehicle profile for vector search optimization. Use the provided data and enrich it by incorporating publicly available information and relevant details about the specific car type to make the profile more comprehensive and search-friendly. Ensure the profile is written in a natural language format, includes enriched details, and generates hashtags dynamically based on the vehicle's unique features.
              ### Template for Vehicle Profile:
                1. **Basic Information:**
                   - **VIN:** {{VIN}}
                   - **Stock Number:** {{StockNumber}}
                   - **Type:** {{Type}} (e.g., New, Used)
                   - **Year:** {{Year}}
                   - **Make:** {{Make}} (e.g., BMW, Audi)
                   - **Model:** {{Model}}
                   - **Trim:** {{Trim}}
                   - **Style:** {{Style}}
                   - **Model Number:** {{ModelNumber}}
                   - **Mileage:** {{Mileage}} miles
                
                2. **Description:**
                   This {{Year}} {{Make}} {{Model}} {{Trim}} offers {{unique selling points or features}}. It is equipped with {{key features and options, e.g., ventilated seats, 3D parking assistance, advanced driver-assist systems}}. The vehicle style is {{Style}}, and it comes in {{Color (if available)}} with {{interior features}}.
                
                3. **Key Features:**
                   - Engine: {{Engine specifications, if available}}
                   - Transmission: {{Transmission type, e.g., Automatic, Manual}}
                   - Drive: {{e.g., All-wheel drive, Rear-wheel drive}}
                   - Seating: {{Seating capacity and material}}
                   - Technology: {{List of technology features, e.g., touchscreen, navigation, premium sound system}}
                   - Safety: {{Safety features, e.g., airbags, lane assist, blind-spot monitoring}}
                
                4. **Customization and Options:**
                   - Packages: {{Optional packages or customizations included}}
                   - Accessories: {{List accessories, e.g., black wheels, roof rails}}
                
                5. **Pricing and Availability:**
                   - Retail Price: ${{KBBRetail}} (as of {{KBBValuationDate}})
                   - Dealer Processing Fee: ${{DealerProcessingFee}}
                   - Test Drive: Available upon request. Contact us to schedule.
                
                6. **Additional Metadata:**
                   - Last Updated: {{DateImagesModified}}
                   - Comments: {{Comment6, Comment7}}
                
                7. **Hashtags for Vector Search:**
                   #{{Make}} #{{Model}} #{{Trim}} #{{Year}} #{{Style}} #{{Key Features (e.g., #VentilatedSeats, #3DParkingAssist)}}
                
                ### Example Vehicle Profile:
                
                **Basic Information:**
                - VIN: WBA53FJ08SCU33689
                - Stock Number: U33689
                - Type: New
                - Year: 2025
                - Make: BMW
                - Model: 5 Series
                - Trim: 530i xDrive
                - Style: 530i xDrive Sedan
                - Model Number: 255B
                - Mileage: 0 miles
                
                **Description:**
                This 2025 BMW 5 Series 530i xDrive offers luxurious comfort and cutting-edge technology. It is equipped with ventilated seats, 3D parking assistance, and advanced driver-assist systems. The vehicle style is a sedan, featuring a sleek black exterior and premium leather interior.
                
                **Key Features:**
                - Engine: 2.0L Turbocharged I4
                - Transmission: Automatic
                - Drive: All-wheel drive
                - Seating: 5-passenger, premium leather seats
                - Technology: 10.25" touchscreen, navigation, Harman Kardon sound system
                - Safety: Adaptive cruise control, lane departure warning, blind-spot monitoring
                
                **Customization and Options:**
                - Packages: M Sport Package
                - Accessories: Black wheels, panoramic sunroof
                
                **Pricing and Availability:**
                - Retail Price: $52,000 (as of 12/5/2024)
                - Dealer Processing Fee: $0
                - Test Drive: Available upon request. Contact us to schedule.
                
                **Additional Metadata:**
                - Last Updated: 12/5/2024 1:47:01 AM
                - Comments: N/A
                #BMW #5Series #530iXDrive #2025 #Sedan #VentilatedSeats #3DParkingAssist
                
                
              ## For your use:
              Information: {information}
              """

INGESTION_TEMPLATE_TWO = """### Prompt Template:

You are an advanced assistant specializing in creating enriched vehicle profiles optimized for vector database search. Based on the given data, generate a detailed and descriptive profile for a vehicle. The profile should integrate all provided details and enrich them with additional context or related information. Ensure the content is natural, engaging, and includes hashtags to improve search relevance.

---

### Example Template:

"Introducing the {Year} {Make} {Model} {Trim}, a masterpiece of engineering and design tailored for those who demand excellence. This {Style} features a {Engine specifications, if available} engine paired with a {Transmission type} transmission, delivering exceptional performance and efficiency. With {Mileage} miles on the odometer, this {Type} vehicle showcases cutting-edge technology, including {key technology features like ventilated seats, 3D parking assistance, and a premium sound system}. Safety is paramount, with features like {safety features, e.g., adaptive cruise control, blind-spot monitoring, and lane assist} ensuring peace of mind on every journey. The {interior material and seating capacity, e.g., 5-passenger premium leather interior} complements the sleek {Color (if available)} exterior, creating an aura of sophistication and comfort. Optional packages, such as {list packages}, and accessories like {list accessories, e.g., black wheels and roof rails}, enhance the versatility and appeal of this vehicle. Available for a retail price of ${KBBRetail} (as of {KBBValuationDate}), with no additional dealer processing fee, this vehicle offers unbeatable value. Schedule a test drive today to experience its unparalleled features and performance. Updated as of {DateImagesModified}, this vehicle is ready to redefine your driving experience. #{Make} #{Model} #{Trim} #{Year} #{Style} #{Key Features (e.g., #VentilatedSeats, #3DParkingAssist, #LuxurySedan)}."

---

### Sample Vehicle Profile:

"Introducing the 2025 BMW 5 Series 530i xDrive, a masterpiece of engineering and design tailored for those who demand excellence. This sleek sedan features a 2.0L turbocharged I4 engine paired with an automatic transmission, delivering exceptional performance and efficiency. With just 0 miles on the odometer, this new vehicle showcases cutting-edge technology, including ventilated seats, 3D parking assistance, and a premium Harman Kardon sound system. Safety is paramount, with features like adaptive cruise control, blind-spot monitoring, and lane departure warning ensuring peace of mind on every journey. The 5-passenger premium leather interior complements the sleek black exterior, creating an aura of sophistication and comfort. Optional packages, such as the M Sport Package, and accessories like black wheels and a panoramic sunroof, enhance the versatility and appeal of this vehicle. Available for a retail price of $52,000 (as of 12/5/2024), with no additional dealer processing fee, this vehicle offers unbeatable value. Schedule a test drive today to experience its unparalleled features and performance. Updated as of 12/5/2024, this vehicle is ready to redefine your driving experience. #BMW #5Series #530iXDrive #2025 #Sedan #VentilatedSeats #3DParkingAssist #LuxurySedan."

---

This single-paragraph format integrates all relevant data points while enriching the content with additional descriptions, making it suitable for vector-based search and retrieval. Let me know if you need further refinements!

##For your use:
Information: {information}
"""

RAG_TEMPLATE = """You are a professional call agent for Sonic Automobile, specialized in providing precise and accurate information to customers. Based on the provided context retrieved from the vehicle inventory database, answer the customer's query concisely and confidently. Use the retrieved context to provide an on-point response. If the information is not available in the given context, acknowledge that the exact answer is unavailable and offer assistance in finding alternative solutions.

Instructions for LLM:
Analyze the Context: Use the retrieved information to generate an accurate and helpful response to the customer’s query.
Respond Professionally: Maintain a polite and professional tone throughout the interaction.
Handle Missing Information Gracefully: If the retrieved context does not contain the requested information, respond clearly and offer alternatives or further assistance.

### Example Interaction 1:
Human Query:
"Does BMW offer ventilated seats and advanced parking features, such as 3D parking assistance?"

Context:
"The 2025 BMW 5 Series 530i xDrive features ventilated seats and advanced parking assistance with 3D surround view. The 540i xDrive trim also includes these features as part of the Premium Package."

LLM Response:
"Yes, BMW offers ventilated seats and advanced parking features, including 3D parking assistance, in the 2025 BMW 5 Series. These features are available in the 530i xDrive and 540i xDrive trims, with the latter including them as part of the Premium Package. Would you like to explore these models further or arrange a test drive?"

### Example Interaction 2:
Human Query:
"Can I find a white BMW X5 with black wheels in your inventory?"

Context:
"The benz 2025 S series offers a variety of colors, including white and black, with customizable wheel options. The Benz S model features a range of exterior colors and wheel designs to choose from."

LLM Response:
"I’m sorry, but I couldn’t find a white BMW X5 with black wheels in our current inventory. Would you like me to assist you in exploring similar options or notify you when one becomes available?


##For your use:
Human Query: {query}

Context: {information}
"""

COLLECTION_NAME = os.getenv("COLLECTION_NAME", "test-v1")
CONNECTION_STRING = os.getenv(
    "CONNECTION_STRING",
    "postgresql+psycopg://sandeesh:mysecretpassword@localhost:5433/voice-demo",
)
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "voice-demo")
DB_USER = os.getenv("DB_USER", "sandeesh")
DB_PASSWORD = os.getenv("DB_PASSWORD", "mysecretpassword")
DB_PORT = os.getenv("DB_PORT", "5433")
INGESTION_TEMPLATE = os.getenv("INGESTION_TEMPLATE", INGESTION_TEMPLATE_ONE)
COHERE_API_KEY = os.getenv("COHERE_API_KEY")
SPACY_MODEL = os.getenv("SPACY_MODEL", "en_core_web_sm")
