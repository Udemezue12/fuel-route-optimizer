from asgiref.sync import sync_to_async


async def run_db(fn, *args, **kwargs):
   
    return await sync_to_async(fn, thread_sensitive=True)(*args, **kwargs)


async def run_sync(func, *args, **kwargs):
   
    return await sync_to_async(func)(*args, **kwargs)