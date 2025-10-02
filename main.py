import subprocess
from fastmcp import FastMCP

mcp = FastMCP("Glin - Your worklog, without the work")


@mcp.tool
def get_recent_commits(count: int = 10) -> list[dict]:
    """
    Get recent git commits from the current repository.

    Args:
        count: Number of recent commits to retrieve (default: 10)

    Returns:
        List of commit dictionaries with hash, author, date, and message
    """
    try:
        # Format: hash|author|date|message
        result = subprocess.run(
            [
                "git", "log",
                f"-{count}",
                "--pretty=format:%H|%an|%ai|%s"
            ],
            capture_output=True,
            text=True,
            check=True
        )

        commits = []
        for line in result.stdout.strip().split('\n'):
            if line:
                hash, author, date, message = line.split('|', 3)
                commits.append({
                    "hash": hash,
                    "author": author,
                    "date": date,
                    "message": message
                })

        return commits
    except subprocess.CalledProcessError as e:
        return [{"error": f"Git command failed: {e.stderr}"}]
    except Exception as e:
        return [{"error": f"Failed to get commits: {str(e)}"}]


if __name__ == "__main__":
    mcp.run()
