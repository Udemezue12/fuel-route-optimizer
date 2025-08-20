
from injector import inject
from ninja.errors import HttpError
from ninja_extra import api_controller, http_post, http_get, throttle
from ninja_extra.permissions import IsAuthenticated
from django.http.request import HttpRequest as Request
from .route_service import GeoapifyService
from .dependencies import CacheDependencies, CacheKeyDependencies, CRUDDependencies
from .schema import  RouteRequest
from .throttling import CustomAnonRateThrottle, CustomUserThrottle
from .tasks import calculate_route_task
from .log import logger


@api_controller(tags=['Calculate Routes'])
@throttle(CustomAnonRateThrottle, CustomUserThrottle)
class RouteController:
    @inject
    def __init__(self, cache_deps: CacheDependencies, cache_key_deps: CacheKeyDependencies, deps: CRUDDependencies):
        self.cache_deps = cache_deps
        self.cache_key_deps = cache_key_deps
        self.deps = deps
        self.route_service = GeoapifyService(
            cache_deps=self.cache_deps, cache_key_deps=self.cache_key_deps)

    @http_post('/calculate/routes',  permissions=[IsAuthenticated])
    async def calculate(self, request: Request, data: RouteRequest):
        try:

            cache_key = await self.cache_key_deps.generate_cache_key(data.dict())

           
            cached_result = await self.cache_deps.get_from_cache(cache_key)
            if cached_result:
                logger.info(f"Cache hit for route {cache_key}")
                return {"cache_key": cache_key, "status": "done", "result": cached_result}

         
            task_id_key = f"{cache_key}:task"
            running_task_id = await self.cache_deps.get_from_cache(task_id_key)
            if running_task_id:
                logger.info(f" Route task already running for {cache_key} (task_id={running_task_id})")
                return {"cache_key": cache_key, "status": "processing", "task_id": running_task_id}

            
            task = calculate_route_task.delay(data.dict())
            await self.cache_deps.set_from_cache(task_id_key, task.id, timeout=600)  
            logger.info(f" Launched new Celery task {task.id} for route {cache_key}")

            return {"cache_key": cache_key, "status": "processing", "task_id": task.id}

        except Exception as e:
            logger.error(f" Error calculating task: {str(e)}", exc_info=True)
            raise HttpError(500, f"Failed to calculate task result: {str(e)}")

    @http_get("/result/{cache_key}", permissions=[IsAuthenticated])
    async def get_route_result(self, request: Request, cache_key: str):
        try:
     
            result = await self.cache_deps.get_from_cache(cache_key)
            if result:
                return {"cache_key": cache_key, "status": "done", "result": result}

           
            return {"cache_key": cache_key, "status": "processing"}

        except Exception as e:
            logger.error(f" Error retrieving task {cache_key}: {str(e)}", exc_info=True)
            raise HttpError(500, f"Failed to retrieve task result: {str(e)}")
