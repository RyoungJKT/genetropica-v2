# GeneTropica, landing page

A standalone editorial landing page for the GeneTropica drug-repurposing study.
It is self-contained: a single `index.html` with no build step, using GSAP from a CDN.

## Preview locally

```bash
cd landing
python3 -m http.server 8700
# then open http://localhost:8700
```

## Deploy on Vercel

1. Go to vercel.com and click **Add New, Project**.
2. Import the GitHub repo `RyoungJKT/genetropica-v2`.
3. Set **Root Directory** to `landing`.
4. **Framework Preset:** Other. It is a static site, so leave the build command and output directory empty.
5. Click **Deploy**. Vercel serves `landing/index.html` at your project URL.

## Deploy on Netlify (alternative)

1. **Add new site, Import an existing project**, pick the repo.
2. **Base directory:** `landing`. Leave the build command empty. **Publish directory:** `landing`.
3. Deploy.

The page links out to the live dashboard at https://genetropica-production.up.railway.app/ and to the source on GitHub.
