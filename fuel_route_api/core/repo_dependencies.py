

from typing import Optional, Type, TypeVar

from asgiref.sync import sync_to_async
from django.db.models import Model
from ninja.errors import HttpError

T = TypeVar("T", bound=Model)
class ExistingDependencies:
    async def async_check_existing(
        self, model:Type[T], raise_error_if_exists=True, error_field="Record", **kwargs
    ):
        obj = await model.objects.filter(**kwargs).aexists()
        if raise_error_if_exists and obj:
            raise HttpError(status_code=409,
                            message=f"{error_field} already exists.")
        if not raise_error_if_exists and not obj:
            raise HttpError(status_code=404,
                            message=f"{error_field} not found.")
        return obj


class CRUDDependencies:
    async def get_lists(self, model: Type[T], **kwargs)-> list[T]:
        books: list[T] = await sync_to_async(list)(model.objects.all())
        return books

    async def async_get_object_or_404(self, model:Type[T], **kwargs)->Optional[T]:
        obj = await model.objects.filter(**kwargs).afirst()
        # Used for getting a single object, like getting the single book by an author
        return obj

    async def async_get_lists_of_an_object_or_404(self, model, **kwargs):
        queryset = model.objects.filter(**kwargs)
        objs = await sync_to_async(list)(queryset)

        # Used for getting a list of a single object by name, id or anything,
        #  like getting the
        #  list of books by an author
        return objs

    async def async_create(self, model:Type[T], **kwargs):
        obj = model(**kwargs)
        await obj.asave()
        return obj

    async def async_update(self, model:Type[T], **kwargs):
        obj = await model.objects.filter(**kwargs).afirst()
        return obj

    async def partial_update(self, model, data, **kwargs):
        obj = await self.async_get_object_or_404(model, **kwargs)
        for attr, value in data.dict(exclude_unset=True).items():
            setattr(obj, attr, value)
        await obj.asave()
        return obj
    async def asave(self, obj):
        await obj.asave()
        return obj

    async def async_delete(self, model:Type[T], **kwargs):
        obj = await model.objects.filter(**kwargs).afirst()
        await obj.adelete()
        return {"success": True}