import shlex
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


@unittest.skipUnless(shutil.which("git"), "Git is needed to verify the sync example")
class SyncExampleTests(unittest.TestCase):
    def test_readme_commit_preserves_another_sessions_staged_work(self):
        readme = (Path(__file__).parents[1] / "README.md").read_text(encoding="utf-8")
        example = readme.split("# session end - commit only the paths this session wrote", 1)[1]
        commands = [shlex.split(line) for line in example.split("```", 1)[0].splitlines()
                    if line.startswith("git ") and (" add " in line or " commit " in line)]
        self.assertEqual(2, len(commands))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            def git(*args):
                return subprocess.run(["git", "-C", tmp, *args], check=True,
                                      capture_output=True, text=True).stdout.strip()
            git("init")
            git("config", "user.name", "Example Contributor")
            git("config", "user.email", "security@example.com")
            git("config", "commit.gpgsign", "false")
            git("config", "core.hooksPath", str(root / "no-hooks"))
            paths = commands[0][4:]
            for name in [*paths, "neighbor.md"]:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("initial\n", encoding="utf-8")
            git("add", ".")
            git("commit", "-m", "Initial fictional notes")
            for name in [*paths, "neighbor.md"]:
                (root / name).write_text("changed\n", encoding="utf-8")
            git("add", "neighbor.md")
            for command in commands:
                git(*command[3:])
            self.assertEqual(set(paths), set(git("diff-tree", "--no-commit-id", "--name-only",
                                                 "-r", "HEAD").splitlines()))
            self.assertEqual("neighbor.md", git("diff", "--cached", "--name-only"))


if __name__ == "__main__":
    unittest.main()
