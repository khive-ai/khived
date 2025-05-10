## Getting Started

### 1. Install Khive

- set up virtual environment
  ```
  uv venv
  source .venv/bin/activate
  ```

- install khive
  ```
  uv pip install "khive[all]"
  ```

- or add it to your development requirements
  ```
  uv add --dev "khive[all]"
  ```

### 2. Input Environment Variables (optional)

- create a `.env` file in the root directory of your project
- add the following environment variables to the `.env` file
  ```
  OPENROUTER_API_KEY=your_openrouter_api_key
  PERPLEXITY_API_KEY=your_perplexity_api_key
  EXA_API_KEY=your_exa_api_key
  ```
- you can get the API keys from the respective websites
- all API keys are optional, but you will need them in order to use features
  like `khive info search` and `khive info consult`

### 3. Set up Roo

#### 3.1 Set up Roo rules in your project

run the following command to set up the Roo rules in your project.

```
khive roo
```

This will create a `.khive` dictory in your project root directory, (consider
adding it to your .gitignore). Then open
`.khive/prompts/roo_rules/rules/000_project_info.md` and replace the project
info,

```
# project: {{project}}

- repo owner: {{repo_owner}}
- repo name: {{repo_name}}
```

Then run `khive roo` again to update roo rules

#### 3.2 Configure Roo

you will need API keys for Roo to work. Khive works best with
`claude-sonnet-3.7` models.

Then open roo settings,

- under `Auto-Apporve` section, add the following commands to allow auto
  execution of the commands: `khive`, `uv`, `git`, `gh`, `cd`, `mkdir`, `ls`,
  `cat`, `python`, `chmod +x`, ... and more as you need.
- for auto approve, allow everything except `Mode` switching, khive do not
  support mode switching features, they will confuse the khive dev team.
- Under context, set file auto truncate threshold to 500-2000 lines to avoid
  crashing the context window.
- check detailed documentation on how to set up roo at https://docs.roocode.com/

### 4. Set up MCP (optional)

It is a good idea to set up a Github MCP server and provide to roo in case
command line isn't working or available. You can add this into your
`.roo/mcp.json` file. You will need to set up a Github personal access token
with repo and workflow permissions. You can do this by going to your Github
settings, then Developer settings, then Personal access tokens, and creating a
new token.

```json
{
  "mcpServers": {
    "fetch": {
      "command": "uvx",
      "args": [
        "mcp-server-fetch"
      ],
      "alwaysAllow": [
        "fetch"
      ],
      "autoApprove": [
        "fetch"
      ]
    },
    "github": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-e",
        "GITHUB_PERSONAL_ACCESS_TOKEN",
        "ghcr.io/github/github-mcp-server"
      ],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_y4raJxxxxxxxxxxxxxxxxxxxxxxx"
      },
      "alwaysAllow": [
        "add_issue_comment",
        "create_branch",
        "create_issue",
        "create_or_update_file",
        "create_pull_request",
        "get_file_contents",
        "get_issue",
        "get_issue_comments",
        "get_me",
        "get_pull_request",
        "get_pull_request_comments",
        "get_pull_request_files",
        "get_pull_request_reviews",
        "get_pull_request_status",
        "list_commits",
        "list_issues",
        "list_pull_requests",
        "merge_pull_request",
        "push_files",
        "search_code",
        "search_issues",
        "search_repositories",
        "search_users",
        "update_issue",
        "update_pull_request_branch",
        "add_pull_request_review_comment",
        "create_pull_request_review",
        "list_branches",
        "get_commit",
        "add_pull_request_comment",
        "update_pull_request"
      ],
      "disabled": true
    }
  }
}
```

### 5. Give it a spin

add some issues to your repo, then

open roo, and text `khive-orchestrator`:

```
thoughtfully resolve all issues
```

and hit enter.

### Conclusion

That's it! You are all set up to use Khive.
