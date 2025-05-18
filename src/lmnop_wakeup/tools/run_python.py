from pydantic_ai.mcp import MCPServerStdio


def sandboxed_python_mcp_server() -> MCPServerStdio:
  """
  More info:
  * https://github.com/pydantic/pydantic-ai/tree/main/mcp-run-python
  * https://ai.pydantic.dev/mcp/run-python
  * https://ai.pydantic.dev/mcp/client/#mcp-stdio-server
  """
  return MCPServerStdio(
    "deno",
    args=[
      "run",
      "-N",
      "-R=node_modules",
      "-W=node_modules",
      "--node-modules-dir=auto",
      "jsr:@pydantic/mcp-run-python",
      "stdio",
    ],
    log_level="debug",
    cwd="/home/shyndman/dev/projects/lmnop/wakeup",
  )
