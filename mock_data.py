from langchain_core.documents import Document

docs = [
    Document(
        page_content="John Smith prefers evening appointments due to his busy morning schedule.",
        metadata={
            "id": 1,
            "topic": "maintenance",
        },
    ),
    Document(
        page_content="Emily Johnson reported frequent brake issues with her Honda Civic (Vehicle ID: 467) during her last visit.",
        metadata={
            "id": 2,
            "topic": "maintenance",
        },
    ),
    Document(
        page_content="Michael Brown’s Toyota Camry (Vehicle ID: 123) requires an oil change and tire rotation service.",
        metadata={
            "id": 3,
            "topic": "maintenance",
        },
    ),
    Document(
        page_content="Sarah Davis requested a quote for replacing windshield wipers for her Ford Mustang (Vehicle ID: 568).",
        metadata={
            "id": 4,
            "topic": "maintenance",
        },
    ),
    Document(
        page_content="David Wilson has enrolled in a workshop on effective car maintenance tips at the local library.",
        metadata={
            "id": 5,
            "topic": "maintenance",
        },
    ),
    Document(
        page_content="Jessica Martinez has a scheduled service appointment for her Tesla Model 3 (Vehicle ID: 102) on January 15th at 10:00 AM.",
        metadata={
            "id": 6,
            "topic": "maintenance",
        },
    ),
    Document(
        page_content="A special discount on brake pad replacement is available for vehicles like Michael Green’s Chevrolet Camaro (Vehicle ID: 902) this month.",
        metadata={
            "id": 7,
            "topic": "maintenance",
        },
    ),
    Document(
        page_content="Sophia Taylor’s Tesla Model S (Vehicle ID: 910) is due for its annual maintenance check-up next month.",
        metadata={
            "id": 8,
            "topic": "maintenance",
        },
    ),
    Document(
        page_content="Customer Robert Anderson prefers communication via email for updates on his vehicle's service progress.",
        metadata={
            "id": 9,
            "topic": "maintenance",
        },
    ),
    Document(
        page_content="Victoria Clark has asked for recommendations on eco-friendly car maintenance products for her Honda Civic (Vehicle ID: 467).",
        metadata={
            "id": 10,
            "topic": "maintenance",
        },
    ),
]


# Mock data for demonstration purposes
vehicles = {
    "123": {"make": "Toyota", "model": "Camry", "year": 2020},
    "467": {"make": "Honda", "model": "Civic", "year": 2022},
    "102": {"make": "Tesla", "model": "Model 3", "year": 2023},
    "910": {"make": "Tesla", "model": "Model S", "year": 2021},
    "568": {"make": "Ford", "model": "Mustang", "year": 2019},
    "902": {"make": "Chevrolet", "model": "Camaro", "year": 2020},
}
