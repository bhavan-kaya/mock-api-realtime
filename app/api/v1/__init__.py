import pkgutil
import importlib
from fastapi import APIRouter
from pathlib import Path

api_v1_router = APIRouter()

# Path to the endpoints directory for dynamic module loading
endpoints_package_path = "app.api.v1"
endpoints_dir_path = Path(__file__).parent

# Discover and include all endpoint routers from the 'endpoints' directory
for module_info in pkgutil.iter_modules([str(endpoints_dir_path)]):
    # Skip private modules
    if not module_info.name.startswith('_'):
        # Dynamically import the endpoint module
        module = importlib.import_module(f".{module_info.name}", package=endpoints_package_path)

        # Check if the module has a 'router' attribute (which should be an APIRouter instance)
        if hasattr(module, "router"):
            # Include the router from the endpoint module.
            # Using the filename as a tag for better documentation in Swagger UI.
            api_v1_router.include_router(
                module.router,
                tags=[module_info.name]
            )
