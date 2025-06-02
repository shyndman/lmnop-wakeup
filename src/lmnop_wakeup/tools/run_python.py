from llm_sandbox import SandboxSession


def run_code(
  lang: str,
  code: str,
  libraries: list[str] | None = None,
  verbose: bool = False,
) -> str:
  """Run code in a sandboxed environment.

  param lang: The language of the code, must be one of ['python', 'java', 'javascript', 'cpp',
    'go', 'ruby'].
  param code: The code to run.
  param libraries: The libraries to use, it is optional.
  return: The output of the code.
  """
  with SandboxSession(lang=lang, verbose=verbose) as session:
    return session.run(code, libraries).stdout
