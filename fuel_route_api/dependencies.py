
from hashlib import md5
import json
from django.core.cache import cache
from asgiref.sync import sync_to_async
from ninja.errors import HttpError


class ExistingDependencies:
    async def async_check_existing(self, model, raise_error_if_exists=True, error_field="Record", **kwargs):
        obj = await model.objects.filter(**kwargs).aexists()
        if raise_error_if_exists and obj:
            raise HttpError(status_code=409,
                            message=f"{error_field} already exists.")
        if not raise_error_if_exists and not obj:
            raise HttpError(status_code=404,
                            message=f"{error_field} not found.")
        return obj


class CRUDDependencies:

    async def get_lists(self, model, **kwargs):

        books = await sync_to_async(list)(model.objects.all())
        return books

    async def async_get_object_or_404(self, model, **kwargs):
        obj = await model.objects.filter(**kwargs).afirst()
        # Used for getting a single object, like getting the single book by an author
        return obj

    async def async_get_lists_of_an_object_or_404(self, model, **kwargs):
        queryset = model.objects.filter(**kwargs)
        objs = await sync_to_async(list)(queryset)

        # Used for getting a list of a single object by name, id or anything, like getting the list of books by an author
        return objs

    async def async_create(self, model, **kwargs):
        obj = model(**kwargs)
        await obj.asave()
        return obj

    async def async_update(self, model, **kwargs):
        obj = await model.objects.filter(**kwargs).afirst()
        return obj

    async def partial_update(self, model, data, **kwargs):
        obj = await self.async_get_object_or_404(model, **kwargs)
        for attr, value in data.dict(exclude_unset=True).items():
            setattr(obj, attr, value)
        await obj.asave()
        return obj

    async def async_delete(self, model, **kwargs):
        obj = await model.objects.filter(**kwargs).afirst()
        await obj.adelete()
        return {'success': True}


class CacheDependencies:
    async def get_from_cache(self, key):
        return await sync_to_async(cache.get)(key)

    async def set_from_cache(self, key, value, timeout=60 * 10):
        await sync_to_async(cache.set)(key, value, timeout)

    async def delete_from_cache(self, key):
        await sync_to_async(cache.delete)(key)



class CacheKeyDependencies:
    async def generate_cache_key(self, data: dict) -> str:
        return md5(json.dumps(data, sort_keys=True).encode('utf-8')).hexdigest()
        
    async def validate_usa_coordinates(self, latitude: float, longitude: float) -> bool:
        usa_bounds = {
            'lat_min': 24.396308,
            'lat_max': 49.384358,
            'lon_min': -125.0,
            'lon_max': -66.93457
        }
        return (
            usa_bounds['lat_min'] <= latitude <= usa_bounds['lat_max'] and
            usa_bounds['lon_min'] <= longitude <= usa_bounds['lon_max']
        )
    async def _generate_cache_key(self, start_lat, start_lon, finish_lat, finish_lon, route_points=None):
       
        base_key = f"route_{start_lat}_{start_lon}_{finish_lat}_{finish_lon}"
        if route_points:
            coords = [(p.latitude, p.longitude) for p in route_points]
            hash_part = md5(json.dumps(coords, sort_keys=True).encode("utf-8")).hexdigest()
            return f"{base_key}_{hash_part}"
        return base_key
