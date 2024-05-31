import time
from functools import wraps

import jwt
from fastapi import FastAPI, Request, Response, HTTPException, Depends
from starlette.middleware.cors import CORSMiddleware
from ..context import WebContext
from ..model import Response as ResponseModel
from ..exception import BusinessException
from .. import get_seal


async def verify_token(request: Request = Request):
    if request.method == 'OPTIONS' or request.url.path in ['/login/submit']:
        return None
    try:
        payload = jwt.decode(request.headers['Authorization'],
                             get_seal().get_config('jwt_key'),
                             algorithms=["HS256"])
        WebContext().set({'uid': payload['uid']})
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token is invalid: {e}")


app = FastAPI(dependencies=[Depends(verify_token)])


@app.middleware("http")
async def calc_time(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return Response(status_code=exc.status_code, content=exc.detail)


def response_body(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            result = await func(*args, **kwargs)
            return ResponseModel.build(result).success()
        except BusinessException as e:
            return ResponseModel.build().error(message=e.message, code=e.code)
        except Exception as e:
            return ResponseModel.build().error(message=str(e))

    return wrapper


def get(path: str):
    def decorator(func):
        return app.get(path, response_model=ResponseModel)(response_body(func))

    return decorator


def post(path: str):
    def decorator(func):
        return app.post(path, response_model=ResponseModel)(response_body(func))

    return decorator


def delete(path: str):
    def decorator(func):
        return app.delete(path, response_model=ResponseModel)(response_body(func))

    return decorator


def put(path: str):
    def decorator(func):
        return app.put(path, response_model=ResponseModel)(response_body(func))

    return decorator
