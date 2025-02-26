# To run the playground:

```bash
cd frontend
npm install #if not already installed
npm run dev
```

# To host the livekit server (for local development):

```bash
cd recruiter-playground
brew update && brew install livekit #if not already installed
livekit-server --dev
```

# To run the agent:

```bash
cd app
python3 main.py start
```

For this to work, you need to set the following environment variables in the .env file in the root of the repo:

```bash
LIVEKIT_API_KEY=devkey
LIVEKIT_API_SECRET=secret
NEXT_PUBLIC_LIVEKIT_URL=ws://localhost:7880
LIVEKIT_URL=ws://localhost:7880
```
