import subprocess

from ..mcp_app import mcp


def get_current_branch() -> dict:
    try:
        name_res = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True, check=True
        )
        name = name_res.stdout.strip()
        detached = name == "HEAD"

        upstream = None
        try:
            up_res = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"],
                capture_output=True,
                text=True,
                check=True,
            )
            upstream = up_res.stdout.strip() or None
        except subprocess.CalledProcessError:
            upstream = None

        ahead = 0
        behind = 0
        if upstream:
            try:
                cnt = subprocess.run(
                    ["git", "rev-list", "--left-right", "--count", f"{name}...{upstream}"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                left, right = cnt.stdout.strip().split()
                ahead = int(left)
                behind = int(right)
            except Exception:
                ahead, behind = 0, 0

        return {"name": name, "detached": detached, "upstream": upstream, "ahead": ahead, "behind": behind}
    except subprocess.CalledProcessError as e:  # noqa: BLE001
        return {"error": f"Git command failed: {e.stderr}"}
    except Exception as e:  # noqa: BLE001
        return {"error": f"Failed to get current branch: {str(e)}"}


def list_branches():
    try:
        fmt = (
            "%(refname:short)|%(objectname)|%(upstream:short)|%(authorname)|%(authoremail)|%(authordate:iso8601)|%(subject)"
        )
        res = subprocess.run(
            ["git", "for-each-ref", f"--format={fmt}", "refs/heads"],
            capture_output=True,
            text=True,
            check=True,
        )
        branches: list[dict] = []

        cur_res = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True, check=True
        )
        current = cur_res.stdout.strip()

        for line in res.stdout.strip().split("\n"):
            if not line:
                continue
            name, commit_hash, upstream, author, email, date, subject = line.split("|", 6)
            upstream = upstream or None

            ahead = 0
            behind = 0
            if upstream:
                try:
                    cnt = subprocess.run(
                        ["git", "rev-list", "--left-right", "--count", f"{name}...{upstream}"],
                        capture_output=True,
                        text=True,
                        check=True,
                    )
                    left, right = cnt.stdout.strip().split()
                    ahead = int(left)
                    behind = int(right)
                except Exception:
                    ahead, behind = 0, 0

            last_commit: dict | None = {
                "hash": commit_hash,
                "author": author,
                "email": email.strip("<>")
                if isinstance(email, str)
                else email,
                "date": date,
                "message": subject,
            }

            branches.append(
                {
                    "name": name,
                    "is_current": name == current,
                    "upstream": upstream,
                    "ahead": ahead,
                    "behind": behind,
                    "last_commit": last_commit,
                }
            )

        return branches
    except subprocess.CalledProcessError as e:  # noqa: BLE001
        return [{"error": f"Git command failed: {e.stderr}"}]
    except Exception as e:  # noqa: BLE001
        return [{"error": f"Failed to list branches: {str(e)}"}]


@mcp.tool(
    name="get_current_branch",
    description=(
        "Get the current git branch information, including whether HEAD is detached, the upstream (if any), and ahead/behind counts versus upstream."
    ),
)
def _tool_get_current_branch():  # pragma: no cover
    return get_current_branch()


@mcp.tool(
    name="list_branches",
    description=(
        "List local branches with upstream, ahead/behind counts, and last commit metadata. The current branch is marked in the response."
    ),
)
def _tool_list_branches():  # pragma: no cover
    return list_branches()  # type: ignore[return-value]
