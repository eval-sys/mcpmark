Use the GitHub MCP tools to work in the `mcpmark-eval/build-your-own-x` repository.

1. Retrieve the newest five commits on the default branch.
2. Open a new issue titled exactly `Latest 5 Commit Snapshot`.
3. Set the issue body to exactly this format (newest commit first):

```
Latest 5 commits (newest first)
1. <full-sha> | <author name> | <commit subject>
2. <full-sha> | <author name> | <commit subject>
3. <full-sha> | <author name> | <commit subject>
4. <full-sha> | <author name> | <commit subject>
5. <full-sha> | <author name> | <commit subject>
```

Use the full 40-character SHA and only the first line of each commit message. The `<author name>` must come from the commit metadata's author name field (not the GitHub username/login). Leave the issue open and do not touch other issues.
