# Deploying Rules

- Never deploy (`agents-cli deploy`, `gcloud run deploy`, or similar) unless the user explicitly asks for it in their prompt.
- After every code change, test locally using `agents-cli run` or the local Agent Playground (`agents-cli playground`).
- Do NOT redeploy automatically after making edits.
- If a change strictly requires a redeployment to verify, ask the user for explicit approval first.
