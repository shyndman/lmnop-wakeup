## Brief overview
These guidelines specify the preferred logging style for Python code, based on recent feedback and Loguru documentation.

## Logging style
- Use the `loguru` library for all logging instead of the standard `logging` module.
- Do not use f-strings for log messages.
- Format log messages using brace-style formatting (`{}`) by passing keyword arguments directly to the log method (e.g., `logger.debug("User {user} logged in", user=username)`). Loguru handles the formatting internally; do not call `.format()` explicitly on the message string.
