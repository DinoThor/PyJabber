import contextvars

host = contextvars.ContextVar("host")
ip = contextvars.ContextVar("ip")
config_path = contextvars.ContextVar("config_path")
cert_path = contextvars.ContextVar("cert_path")
root_path = contextvars.ContextVar("root_path")
database_path = contextvars.ContextVar("database_path")
database_in_memory = contextvars.ContextVar("database_in_memory", default=None)
message_persistence = contextvars.ContextVar("message_persistence")

tls_queue = contextvars.ContextVar("tls_queue")
connection_queue = contextvars.ContextVar("connection_queue")
message_queue = contextvars.ContextVar("message_queue")
