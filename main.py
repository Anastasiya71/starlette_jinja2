import databases
import sqlalchemy
from sqlalchemy.orm import mapper
from sqlalchemy import Table, Column, String
from starlette.applications import Starlette
from starlette.responses import RedirectResponse
from starlette.routing import Route
from starlette.templating import Jinja2Templates
from starlette.endpoints import HTTPEndpoint
from starlette.config import Config
from starlette.middleware import Middleware
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.authentication import (
    AuthenticationBackend, AuthCredentials, requires
)

templates = Jinja2Templates(directory='templates')

# DATABASE

config = Config('.env')
DATABASE_URL = config('DATABASE_URL')
SECRET_KEY = config('SECRET_KEY')
database = databases.Database(DATABASE_URL)
metadata = sqlalchemy.MetaData()

# TABLES

users = Table(
    'users',
    metadata,
    Column('username', String(50), primary_key=True),
    Column('password', String(12))
)


class User(object):
    def __init__(self, username):
        self.username = username

    def is_authenticated(self):
        return True

    def display_name(self):
        return self.username


mapper(User, users)


# ROUTES

class Dashboard(HTTPEndpoint):
    @requires('authenticated')
    async def get(self, request):
        return templates.TemplateResponse('dashboard.html', {'request': request})

    @requires('authenticated')
    async def post(self, request):
        return templates.TemplateResponse('dashboard.html', {'request': request})


class Register(HTTPEndpoint):
    async def get(self, request):
        return templates.TemplateResponse('register.html', {'request': request})

    async def post(self, request):
        form = dict(await request.form())
        if form['password'] != form['confirmation']:
            return templates.TemplateResponse('register.html', {
                'request': request,
                'not_confirmed': True,
            })
        usrs = sqlalchemy.select([users]).where(users.c.username == form['username'])
        result = await database.fetch_all(usrs)
        if len(result) != 0:
            return templates.TemplateResponse('already_exist.html', {'request': request})
        inserting = users.insert().values(username=form['username'], password=form['password'])
        result = await database.execute(inserting)
        request.session.update({'user': form['username']})
        return templates.TemplateResponse('success_registration.html', {'request': request})


class Homepage(HTTPEndpoint):
    async def get(self, request):
        return templates.TemplateResponse('index.html', {'request': request})

    async def post(self, request):
        form = dict(await request.form())
        usrs = sqlalchemy.select([users]).where(users.c.username.like(form['username']))
        result = await database.fetch_all(usrs)
        print(result)
        if len(result) == 0:
            return templates.TemplateResponse('register_first.html', {'request': request})
        print(result[0].password)
        print(form['password'])
        if result[0].password != form['password']:
            return templates.TemplateResponse('index.html', {
                'request': request,
                'invalid': True,
            })
        request.session.update({'user': form['username']})
        return RedirectResponse(url='/dashboard')


@requires('authenticated')
async def logout(request):
    request.session.clear()
    return templates.TemplateResponse('logged_out.html', {'request': request})


routes = [
    Route('/', Homepage),
    Route('/register', Register),
    Route('/dashboard', Dashboard),
    Route('/logout', logout),
]


# EXCEPTIONS

async def forbiden(request, exc):
    return templates.TemplateResponse('authenticate_first.html', {'request': request})


exception_handlers = {
    403: forbiden,
}


# SESSION AUTH HOLDER

class SessionAuthBackend(AuthenticationBackend):
    async def authenticate(self, request):
        username = request.session.get("user")
        if username == None:
            return
        credentials = ["authenticated"]
        return AuthCredentials(credentials), User(username)


# MIDDLEWARE

middleware = [
    Middleware(SessionMiddleware, secret_key=SECRET_KEY, session_cookie="task_session"),
    Middleware(AuthenticationMiddleware, backend=SessionAuthBackend()),
]

# APP INIT

app = Starlette(
    debug=True,
    routes=routes,
    middleware=middleware,
    on_startup=[database.connect],
    on_shutdown=[database.disconnect],
    exception_handlers=exception_handlers
)
