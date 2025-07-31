from injector import inject
from ninja.errors import HttpError
from ninja_extra import api_controller, http_post, http_get, throttle
from ninja_extra.permissions import IsAuthenticated
from django.http.request import HttpRequest as Request
from celery.result import AsyncResult
from .route_service import GeoapifyService
from .tasks import CalculateRouteTask
from .dependencies import CacheDependencies, CacheKeyDependencies, CRUDDependencies
from .schema import RouteInput, TaskResponse, TaskResultResponse
from .throttling import CustomAnonRateThrottle, CustomUserThrottle


@api_controller(tags=['Calculate Routes'])
@throttle(CustomAnonRateThrottle, CustomUserThrottle)
class RouteController:
    @inject
    def __init__(self, cache_deps: CacheDependencies, cache_key_deps: CacheKeyDependencies, tasks: CalculateRouteTask, deps: CRUDDependencies):
        self.cache_deps = cache_deps
        self.cache_key_deps = cache_key_deps
        self.tasks = tasks
        self.deps = deps
        self.route_service = GeoapifyService(
            cache_deps=self.cache_deps, cache_key_deps=self.cache_key_deps)

    @http_post('/calculate', response=TaskResponse, permissions=[IsAuthenticated] )
    async def calculate(self, request: Request, data: RouteInput):
        try:
           
            for loc in [data.start, data.finish]:
                if not await self.cache_key_deps.validate_usa_coordinates(loc.latitude, loc.longitude):
                    raise HttpError(422, "Locations must be within the USA")

       
            task = self.tasks.apply_async(args=[
                data.start.latitude,
                data.start.longitude,
                data.finish.latitude,
                data.finish.longitude
            ])
         
            return {"task_id": task.id, "status": task.status}

        except HttpError as e:
            raise e
        except Exception as e:
            print(f"❌ Error triggering task: {str(e)}")
            raise HttpError(
                500, f"Failed to start route calculation: {str(e)}")

    @http_get("/task/{task_id}", response=TaskResultResponse,  permissions=[IsAuthenticated])
    async def get_result(self, request: Request, task_id: str):
        try:
            task = AsyncResult(task_id)
            cache = self.cache_deps
            print(f"📊 Checking status for task {task_id}: {task.state}")
            cached_result = await cache.get_from_cache(f"task_result_{task_id}")
            if cached_result:
                return {
                    "task_id": task_id,
                    "status": "SUCCESS",
                    "result": cached_result,
                    "error": None
                }
            if task.state == 'PENDING':
                return {
                    'task_id': task_id,
                    "status": "FAILURE",
                    "result": None,
                    "error": str(task.result)
                }
            elif task.state == "STARTED":
                return {
                    "task_id": task_id,
                    "status": "STARTED",
                    "result": None,
                    "error": None
                }
            elif task.state == "FAILURE":
                return {
                    "task_id": task_id,
                    "status": "FAILURE",
                    "result": None,
                    "error": str(task.result)
                }
            elif task.state == "SUCCESS":
                return {
                    "task_id": task_id,
                    "status": "SUCCESS",
                    "result": task.result,
                    "error": None
                }
            return {
                "task_id": task_id,
                "status": task.state,
                "result": None,
                "error": "Unexpected task state"
            }
        except Exception as e:
            print(f"❌ Error retrieving task {task_id}: {str(e)}")
            raise HttpError(500, f"Failed to retrieve task result: {str(e)}")
