class Routes:
    def __init__(self, path, http_method):
        self.path = path
        self.http_method = http_method

    def __hash__(self):  # makes it usable as a dict key
        return hash((self.path, self.http_method))

    def __eq__(self, other):
        return (self.path, self.http_method) == (other.path, other.http_method)


class Router:
    def __init__(self):
        self.routes = {}  # <- THE TABLE. just a dict.

    def register(self, path, http_method, func):
        self.routes[Routes(path, http_method)] = func
        print(f"    4. REGISTERED ({path!r}, {http_method!r}) -> {func.__name__}")

    def get(self, path):
        print(
            f"1. get({path!r}) called — table: {self.routes}, handler doesn't exist yet"
        )

        def decorator(func):
            print(
                f"3. decorator called with {func.__name__} — first time I have BOTH parts"
            )
            self.register(path, "GET", func)  # side effect: fill the table
            return func  # hand back the original

        print(f"2. get({path!r}) is DONE, returning decorator — table still empty")
        return decorator


app_router = Router()
print("1. right after creation:", app_router.routes)  # {} — empty


@app_router.get("/")  # <- setup happens HERE
def index(request):
    return "hello"


@app_router.get("/health")
def health(request):
    return "ok"


print("2. after the defs:    ", app_router.routes)
print("3. lookup:", app_router.routes[Routes("/", "GET")])
print("4. all paths:", [r.path for r in app_router.routes])
print("5. index is still the plain function:", index)
