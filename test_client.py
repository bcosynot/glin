import asyncio
import json

from fastmcp import Client


def extract_result(result):
    """Extract data from CallToolResult or return as-is."""
    if hasattr(result, "content"):
        data = result.content[0].text
        return json.loads(data) if isinstance(data, str) else data
    return result


async def test_server():
    """Test all git_tools MCP functions."""
    client = Client("http://localhost:8000/mcp")

    async with client:
        print("=" * 80)
        print("Testing Glin MCP Server")
        print("=" * 80)

        # Test 1: Get tracked email configuration
        print("\n1. Testing get_tracked_email_config...")
        try:
            result = await client.call_tool("get_tracked_email_config", {})
            config = extract_result(result)
            print(f"   ✅ Config: {json.dumps(config, indent=2)}")
        except Exception as e:
            print(f"   ❌ Error: {e}")

        # Test 2: Get recent commits
        print("\n2. Testing get_recent_commits...")
        try:
            result = await client.call_tool("get_recent_commits", {"count": 5})
            commits = extract_result(result)
            print(f"   ✅ Found {len(commits)} commits")
            for i, commit in enumerate(commits[:3], 1):
                if "error" in commit:
                    print(f"   ❌ Error: {commit['error']}")
                    break
                print(f"   {i}. {commit.get('hash', 'N/A')[:8]} - {commit.get('message', 'N/A')}")
        except Exception as e:
            print(f"   ❌ Error: {e}")

        # Test 3: Get commits by date
        print("\n3. Testing get_commits_by_date...")
        try:
            result = await client.call_tool(
                "get_commits_by_date", {"since": "1 week ago", "until": "now"}
            )
            commits = extract_result(result)
            print(f"   ✅ Found {len(commits)} commits in the last week")
            for i, commit in enumerate(commits[:3], 1):
                if "error" in commit:
                    print(f"   ❌ Error: {commit['error']}")
                    break
                if "info" in commit:
                    print(f"   ℹ️  {commit['info']}")
                    break
                print(f"   {i}. {commit.get('hash', 'N/A')[:8]} - {commit.get('message', 'N/A')}")
        except Exception as e:
            print(f"   ❌ Error: {e}")

        # Test 4: Get commit diff (using first commit from recent commits)
        print("\n4. Testing get_commit_diff...")
        try:
            # First get a commit hash
            result = await client.call_tool("get_recent_commits", {"count": 1})
            commits = extract_result(result)
            if commits and "hash" in commits[0]:
                commit_hash = commits[0]["hash"]
                result = await client.call_tool(
                    "get_commit_diff", {"commit_hash": commit_hash, "context_lines": 3}
                )
                diff_data = extract_result(result)
                if "error" in diff_data:
                    print(f"   ❌ Error: {diff_data['error']}")
                else:
                    print(f"   ✅ Diff for {diff_data.get('hash', 'N/A')[:8]}")
                    print(f"   Author: {diff_data.get('author', 'N/A')}")
                    print(f"   Message: {diff_data.get('message', 'N/A')}")
                    stats = diff_data.get("stats", "N/A")
                    print(f"   Stats: {stats[:100] if len(stats) > 100 else stats}...")
            else:
                print("   ⚠️  No commits available to test diff")
        except Exception as e:
            print(f"   ❌ Error: {e}")

        # Test 5: Get commit files (using first commit from recent commits)
        print("\n5. Testing get_commit_files...")
        try:
            # First get a commit hash
            result = await client.call_tool("get_recent_commits", {"count": 1})
            commits = extract_result(result)
            if commits and "hash" in commits[0]:
                commit_hash = commits[0]["hash"]
                result = await client.call_tool("get_commit_files", {"commit_hash": commit_hash})
                files_data = extract_result(result)
                if "error" in files_data:
                    print(f"   ❌ Error: {files_data['error']}")
                else:
                    print(f"   ✅ Files for {files_data.get('hash', 'N/A')[:8]}")
                    print(f"   Files changed: {files_data.get('files_changed', 0)}")
                    print(f"   Additions: +{files_data.get('total_additions', 0)}")
                    print(f"   Deletions: -{files_data.get('total_deletions', 0)}")
                    for file in files_data.get("files", [])[:5]:
                        print(
                            f"   {file['status']} {file['path']} "
                            f"(+{file['additions']}/-{file['deletions']})"
                        )
            else:
                print("   ⚠️  No commits available to test files")
        except Exception as e:
            print(f"   ❌ Error: {e}")

        # Test 6: Configure tracked emails (environment variable method)
        print("\n6. Testing configure_tracked_emails (env method)...")
        try:
            result = await client.call_tool(
                "configure_tracked_emails",
                {"emails": ["test@example.com", "test2@example.com"], "method": "env"},
            )
            config_result = extract_result(result)
            if config_result.get("success"):
                print(f"   ✅ {config_result.get('message', 'Success')}")
            else:
                print(f"   ❌ Error: {config_result.get('error', 'Unknown error')}")
        except Exception as e:
            print(f"   ❌ Error: {e}")

        # Test 7: Append to markdown (worklog)
        print("\n7. Testing append_to_markdown...")
        try:
            content = """Tested MCP server integration
Verified all git_tools functions
Added comprehensive test coverage"""
            result = await client.call_tool("append_to_markdown", {"content": content})
            md_result = extract_result(result)
            if "error" in md_result:
                print(f"   ❌ Error: {md_result['error']}")
            else:
                print(f"   ✅ Appended to {md_result.get('path', 'N/A')}")
                print(f"   Bullets added: {md_result.get('bullets_added', 0)}")
                print(f"   Heading added: {md_result.get('heading_added', False)}")
        except Exception as e:
            print(f"   ❌ Error: {e}")

        print("\n" + "=" * 80)
        print("Testing complete!")
        print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_server())
