from contextlib import contextmanager


class TestConnection:
    def __init__(self, autocommit=False):
        self.autocommit = autocommit
        self.in_pipeline = False
        self.queue = []

    def __enter__(self):
        if not self.autocommit:
            print("BEGIN")
        return self

    def execute(self, sql):
        if self.in_pipeline:
            self.queue.append(sql)
        else:
            print(sql)

    @contextmanager
    def pipeline(self):
        # While active, execute() queues queries instead of sending them. A
        # clean exit sends the whole queue plus SYNC in one round trip; a
        # raising block sends nothing, but the cleanup in finally still runs.
        self.in_pipeline = True
        try:
            yield
            print(*self.queue, "SYNC", sep="\n")
        finally:
            self.in_pipeline = False
            self.queue.clear()

    def __exit__(self, exc_type, exc_value, tb):
        # In autocommit mode every statement committed as it ran, so there
        # is no open transaction to end, and nothing left to roll back.
        if self.autocommit:
            return
        if exc_type is None:
            print("COMMIT")
        else:
            print("ROLLBACK")


print("-- clean transaction")
with TestConnection() as conn:
    conn.execute("SELECT *")
    conn.execute("SELECT 1")

print("-- failing transaction")
try:
    with TestConnection() as conn:
        conn.execute("SELECT 1")
        raise ValueError("boom")
except ValueError as e:
    print("caller saw:", e)

print("-- autocommit")
with TestConnection(autocommit=True) as conn:
    conn.execute("SELECT *")
    conn.execute("SELECT 1")

print("-- failing autocommit")
try:
    with TestConnection(autocommit=True) as conn:
        conn.execute("INSERT 1")
        raise ValueError("boom")
except ValueError as e:
    print("caller saw:", e)

print("-- pipeline")
conn = TestConnection(autocommit=True)
with conn.pipeline():
    conn.execute("SELECT sessions")
    conn.execute("SELECT sets")
    conn.execute("SELECT profiles")

print("-- failing pipeline, then reusing the connection")
try:
    with conn.pipeline():
        conn.execute("INSERT a")
        raise ValueError("boom")
except ValueError as e:
    print("caller saw:", e)
conn.execute("SELECT after")

print("-- pipeline inside a transaction")
with TestConnection() as conn, conn.pipeline():
    conn.execute("SELECT sessions")
    conn.execute("SELECT sets")
