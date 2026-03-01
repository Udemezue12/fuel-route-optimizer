from django.http.request import HttpRequest as Request
from injector import inject
from ninja.errors import HttpError
from fuel_route_api.core.compression import decompress_data
from fuel_route_api.core.cache_dependencies import (AsyncCacheDependencies,
                                                    CacheKeyDependencies)
from fuel_route_api.core.log import logger
from fuel_route_api.core.repo_dependencies import CRUDDependencies
from fuel_route_api.tasks.calculate_route_tasks import calculate_route_task
from fuel_project.celery import app as task_app
from .geoapify_service import GeoapifyServiceAsync


class GeoapifyControllerService:
    @inject
    def __init__(self):
        self.cache_deps = AsyncCacheDependencies()
        self.cache_key_deps = CacheKeyDependencies()
        self.deps = CRUDDependencies()

    async def calculate(self,  data):
        try:
            cache_key = await self.cache_key_deps.generate_cache_key(data.dict())

            cached_result = await self.cache_deps.get_from_cache(cache_key)
            if cached_result:
                logger.info(f"Cache hit for route {cache_key}")
                return {
                    "cache_key": cache_key,
                    "status": "done",
                    "result": cached_result,
                }

            task_id_key = f"{cache_key}:task"
            was_added = await self.cache_deps.add_from_cache(task_id_key, "LOCK",  timeout=600)
            if not was_added:

                existing_task_id = await self.cache_deps.get_from_cache(task_id_key)
                return {
                    "status": "processing",
                    "task_id": existing_task_id,
                }
            task = task_app.send_task("calculate_geo_routes", args=[data.dict()])
            await self.cache_deps.set_from_cache(task_id_key, task.id, timeout=600)

            return {"cache_key": cache_key, "status": "processing", "task_id": task.id}

        except Exception as e:

            raise HttpError(500, f"Failed to calculate task result: {str(e)}")

    async def get_route_result(self, request: Request, cache_key: str):
        try:
            result = await self.cache_deps.get_from_cache(cache_key)
            if result:
                return {"cache_key": cache_key, "status": "done", "result": result}

            return {"cache_key": cache_key, "status": "processing"}

        except Exception as e:
            logger.error(
                f" Error retrieving task {cache_key}: {str(e)}", exc_info=True)
            raise HttpError(500, f"Failed to retrieve task result: {str(e)}")
    async def get_route_summary(self, cache_key: str):

        summary_key = f"route:{cache_key}:summary"
        compressed = await self.cache_deps.get_from_cache(summary_key)

        if not compressed:
            return {"status": "processing"}

        return {
            "status": "done",
            "summary": decompress_data(compressed),
        }

    async def get_route_geometry(self, cache_key: str):

        geometry_key = f"route:{cache_key}:geometry"
        compressed = await self.cache_deps.get_from_cache(geometry_key)

        if not compressed:
            raise HttpError(404, "Geometry not found")

        return {
            "geometry": decompress_data(compressed)
        }
