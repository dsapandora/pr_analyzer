# PR Analyzer

AI-powered GitHub Pull Request intelligence. Automatically cluster PRs by topic, detect duplicates, score quality, and chat with your codebase using Claude AI.

**Author:** Ariel Vernaza ([@dsapandora](https://github.com/dsapandora)) - ariel.vernaza@rocketride.ai

## Overview

PR Analyzer connects to your GitHub repositories and runs an AI pipeline that:

1. Fetches all open pull requests via GitHub API
2. Sends each PR (title, description, diff, files) through a **Rocketride pipeline**
3. Claude AI analyzes each PR: assigning topics, a quality score (0-100), and a recommendation (Merge / Keep / Discard / Combine)
4. OpenAI generates vector embeddings to detect semantically similar (duplicate) PRs
5. Results are stored in **Qdrant Cloud** for fast retrieval
6. The frontend displays PRs grouped by topic with full chat support

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Browser (Next.js)                       │
│  Landing Page → Dashboard (Topics/PRs) → PR Detail + Chat       │
└─────────────────────┬───────────────────────────────────────────┘
                       │ HTTPS / JWT Auth
┌─────────────────────▼───────────────────────────────────────────┐
│                    FastAPI Backend (Heroku)                      │
│  /auth  /repos  /prs  /analyze  /chat                           │
└──────┬──────────────┬──────────────┬────────────────────────────┘
       │              │              │
  GitHub API    Rocketride       Qdrant Cloud
  (PyGithub)    Pipeline         (vector store)
                Server
              ┌───────────┐
              │  Nodes:   │
              │  - Claude │
              │  - OpenAI │
              └───────────┘
```

## Tech Stack

| Layer      | Technology                                |
|------------|-------------------------------------------|
| Frontend   | Next.js 14 (App Router), TypeScript, Tailwind CSS |
| Backend    | FastAPI (Python 3.11+), Pydantic v2       |
| Auth       | GitHub OAuth → JWT                        |
| Pipeline   | Rocketride-server (hosted on Fly.io)      |
| Vector DB  | Qdrant Cloud                              |
| LLM        | Anthropic Claude (via Rocketride)         |
| Embeddings | OpenAI text-embedding-3-small (via Rocketride) |
| Hosting    | Heroku (web) + Fly.io (rocketride)        |

## Local Development

### Prerequisites

- Node.js 20+
- Python 3.11+
- A GitHub OAuth App
- Qdrant Cloud account (or run Qdrant locally with Docker)
- Rocketride server running (or use direct API fallback)

### 1. Clone and Configure

```bash
cd projects/pr-analyzer
cp .env.example .env
# Edit .env with your credentials
```

### 2. Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run development server
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend Setup

```bash
cd frontend
npm install

# Run development server
npm run dev
```

App is available at http://localhost:3000

### 4. Docker Compose (All-in-One)

```bash
# Start backend + frontend
docker-compose up

# Start with local Qdrant (no cloud needed)
docker-compose --profile local-qdrant up
```

## Environment Variables

### Backend (`.env`)

| Variable | Required | Description |
|----------|----------|-------------|
| `GITHUB_CLIENT_ID` | Yes | GitHub OAuth App client ID |
| `GITHUB_CLIENT_SECRET` | Yes | GitHub OAuth App client secret |
| `JWT_SECRET_KEY` | Yes | Random secret for JWT signing (32+ chars) |
| `ROCKETRIDE_URL` | Yes | URL of your Rocketride server |
| `ROCKETRIDE_API_KEY` | No | API key for Rocketride (if enabled) |
| `QDRANT_URL` | Yes | Qdrant Cloud cluster URL |
| `QDRANT_API_KEY` | No | Qdrant API key (required for cloud) |
| `ANTHROPIC_API_KEY` | Yes | Anthropic API key (fallback if Rocketride down) |
| `OPENAI_API_KEY` | Yes | OpenAI API key for embeddings |

### Frontend (`.env.local`)

| Variable | Required | Description |
|----------|----------|-------------|
| `NEXTAUTH_URL` | Yes | Full URL of your Next.js app |
| `NEXTAUTH_SECRET` | Yes | Random secret for NextAuth |
| `NEXT_PUBLIC_API_URL` | Yes | URL of your FastAPI backend |
| `GITHUB_CLIENT_ID` | Yes | Same GitHub OAuth App client ID |
| `GITHUB_CLIENT_SECRET` | Yes | Same GitHub OAuth App client secret |

## GitHub OAuth App Setup

1. Go to https://github.com/settings/developers
2. Click "New OAuth App"
3. Fill in:
   - **Application name**: PR Analyzer
   - **Homepage URL**: `http://localhost:3000` (or your production URL)
   - **Authorization callback URL**: `http://localhost:8000/auth/github/callback`
4. Copy the **Client ID** and **Client Secret** to `.env`

## Deployment

### Backend → Heroku

```bash
# Install Heroku CLI
heroku create your-pr-analyzer-api

# Set environment variables
heroku config:set GITHUB_CLIENT_ID=...
heroku config:set GITHUB_CLIENT_SECRET=...
heroku config:set JWT_SECRET_KEY=$(openssl rand -hex 32)
heroku config:set ROCKETRIDE_URL=https://your-rocketride.fly.dev
heroku config:set QDRANT_URL=https://your-cluster.qdrant.io
heroku config:set QDRANT_API_KEY=...
heroku config:set ANTHROPIC_API_KEY=...
heroku config:set OPENAI_API_KEY=...

# Deploy
cd backend
git init
heroku git:remote -a your-pr-analyzer-api
git add .
git commit -m "Deploy PR Analyzer backend"
git push heroku main
```

### Frontend → Heroku (or Vercel)

**Vercel (recommended):**
```bash
cd frontend
npx vercel
# Set environment variables in Vercel dashboard
```

**Heroku:**
```bash
heroku create your-pr-analyzer-app
heroku buildpacks:set heroku/nodejs

heroku config:set NEXTAUTH_URL=https://your-pr-analyzer-app.herokuapp.com
heroku config:set NEXTAUTH_SECRET=$(openssl rand -hex 32)
heroku config:set NEXT_PUBLIC_API_URL=https://your-pr-analyzer-api.herokuapp.com
heroku config:set GITHUB_CLIENT_ID=...
heroku config:set GITHUB_CLIENT_SECRET=...

cd frontend
git push heroku main
```

### Rocketride → Fly.io

```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh

# Deploy Rocketride server
cd /path/to/rocketride-server
fly launch
fly secrets set ANTHROPIC_API_KEY=...
fly secrets set OPENAI_API_KEY=...

# Upload pipeline configs
fly ssh console
# Copy pr_analyzer.pipe and pr_chat.pipe to the pipelines directory
```

### Qdrant Cloud

1. Go to https://cloud.qdrant.io
2. Create a free cluster
3. Copy the **Cluster URL** and **API Key** to your `.env`
4. The collection `pr_analyzer` is created automatically on first analysis

## API Reference

### Authentication
All endpoints (except `/health` and `/auth/*`) require a JWT Bearer token.

```
Authorization: Bearer <jwt_token>
```

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/auth/github/login` | Redirect to GitHub OAuth |
| `GET` | `/auth/github/callback` | OAuth callback → redirect with JWT |
| `GET` | `/repos` | List user's GitHub repositories |
| `GET` | `/prs?repo=owner/repo` | List analyzed PRs |
| `GET` | `/prs/{number}?repo=owner/repo` | Single PR details |
| `GET` | `/prs/topics?repo=owner/repo` | List unique topics |
| `GET` | `/prs/stats?repo=owner/repo` | Aggregate statistics |
| `POST` | `/analyze` | Trigger analysis pipeline |
| `GET` | `/analyze/status/{job_id}` | Check analysis progress |
| `POST` | `/chat` | Chat about a specific PR |

### POST /analyze
```json
{
  "repo": "owner/repository-name"
}
```

### POST /chat
```json
{
  "pr_number": 42,
  "repo": "owner/repository-name",
  "message": "Is this PR safe to merge?",
  "history": [
    {"role": "user", "content": "What does this PR do?"},
    {"role": "assistant", "content": "This PR adds..."}
  ]
}
```

## Pipeline Configuration

The `pipeline/` directory contains Rocketride pipeline definitions:

- **`pr_analyzer.pipe`**: Analyzes a PR with Claude + generates OpenAI embeddings
- **`pr_chat.pipe`**: Chat pipeline with full PR context

Upload these to your Rocketride server to enable AI features.

## Features

- **Topic Clustering**: Automatically groups PRs by domain (vectordb, engine, llms, integrations, ui, bugfix, docs, testing, devops)
- **Quality Scoring**: 0-100 score based on code quality, clarity, test coverage, and purpose
- **Duplicate Detection**: Vector similarity search finds PRs that overlap in scope
- **Recommendations**: Merge / Keep / Discard / Combine based on AI analysis
- **AI Chat**: Ask any question about a PR in natural language
- **Dark UI**: Professional dark theme with smooth animations
- **Responsive**: Works on desktop and mobile

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit changes: `git commit -m 'Add my feature'`
4. Push: `git push origin feature/my-feature`
5. Open a Pull Request

## License

MIT
