# JobLens Frontend

React/Vite frontend for the JobLens chat API.

## Setup

Install Node.js 20+ first. Then run:

```powershell
cd src/frontend
npm install
copy .env.example .env
npm run dev
```

The backend should be running at:

```text
http://127.0.0.1:8000
```

Frontend env lives in `src/frontend/.env` and uses Vite variables:

```text
VITE_API_BASE_URL=http://127.0.0.1:8000
```
