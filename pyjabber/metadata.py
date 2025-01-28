import contextvars

host = contextvars.ContextVar("host")
config_path = contextvars.ContextVar("config_path")
root_path = contextvars.ContextVar("root_path")
database_path = contextvars.ContextVar("database_path")
database_in_memory = contextvars.ContextVar("database_in_memory")
