import subprocess
from packaging.requirements import Requirement
import tomllib

if __name__ == "__main__":
    with open("pyproject.toml", "rb") as file:
        pyproject = tomllib.load(file)

    dependencies = pyproject.get("project", {}).get("dependencies", [])
    update_lines = [f"--upgrade-package={Requirement(dep).name}" for dep in dependencies]
    cmd = [
        "uv",
        "pip",
        "compile",
        "--generate-hashes",
        "--no-annotate",
        "--no-emit-index-url",
        "--no-emit-find-links",
        "--no-header",
        "--all-extras",
        "pyproject.toml",
        "--output-file=requirements.txt",
    ] + update_lines
    subprocess.run(cmd, check=True)
