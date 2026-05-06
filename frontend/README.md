# RAG Scanner Frontend

Static frontend for RAG Scanner, deployed on GitHub Pages.

## Usage

Access: https://jasond2019.github.io/rag-scanner

## API Backend

The frontend connects to Vercel Serverless API:
- API URL: `https://rag-scanner-api.vercel.app`

## Local Development

```bash
# Serve locally
npx serve frontend/

# Or use Python
python -m http.server 8080 --directory frontend/
```

## Configuration

Edit `app.js` to change API URL:

```javascript
const API_URL = 'https://your-api-url.vercel.app';
```