```markdown
# gitpulse

Analyze GitHub user activity from the command line.

## Install

With [pipx](https://pipx.pypa.io/):

```sh
pipx install gitpulse
```

For development:

```sh
git clone https://github.com/A-creator-collab/gitpulse
cd gitpulse
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate # macOS / Linux
pip install -r requirements.txt
pip install -e .
```

## Usage

```sh
# Profile card
gitpulse user A-creator-collab

# Contribution streaks
gitpulse streak A-creator-collab

# List repositories
gitpulse repos A-creator-collab --sort stars

# Filter repos by language
gitpulse repos A-creator-collab --lang python --sort updated

# Language breakdown
gitpulse langs A-creator-collab

# Compare two users
gitpulse compare A-creator-collab torvalds
```

## Requirements

- Python 3.10 or newer
- Optional: a `GITHUB_TOKEN` environment variable. When set, the GitHub API
  rate limit is 5000 requests per hour. Without it, unauthenticated runs are
  limited to 60 requests per hour.

To set a token in PowerShell:

```powershell
$env:GITHUB_TOKEN = "ghp_your_token_here"
```

No scopes are needed for public data.

## Caching

API responses are cached as JSON under `~/.cache/gitpulse/`, keyed by a SHA-256
hash of the request URL, with a 15-minute TTL.

## License

MIT. See [LICENSE](LICENSE).
```
