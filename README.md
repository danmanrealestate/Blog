# DMSellsRE Automated Blog RSS Feed

This system automatically generates real estate blog articles and publishes them into an RSS feed that GoDaddy can read.

## Schedule

- Monday: Residential real estate article
- Friday: Commercial / investor real estate article

The GitHub Action runs at 12:00 and 13:00 UTC on Mondays and Fridays. The script checks America/New_York time and only generates the article when it is 8 AM Eastern.

## Files

- `feed.xml` — your RSS feed file
- `posts.json` — stores generated blog posts
- `scripts/generate_feed.py` — article generator and RSS builder
- `.github/workflows/generate-posts.yml` — scheduled automation
- `requirements.txt` — Python dependencies

## Setup Steps

1. Create a GitHub account if you do not have one.
2. Create a new repository named:

   dmsellsre-blog-feed

3. Upload all files from this package into that repository.
4. Go to repository Settings → Secrets and variables → Actions.
5. Click New repository secret.
6. Add:

   Name: OPENAI_API_KEY  
   Value: your OpenAI API key

7. Go to repository Settings → Pages.
8. Under Build and deployment, set:

   Source: Deploy from a branch  
   Branch: main  
   Folder: /root

9. Save.

10. Your Feed URL will be:

   https://YOUR-GITHUB-USERNAME.github.io/dmsellsre-blog-feed/feed.xml

11. Paste that URL into GoDaddy's Feed URL field.

## Manual Test

In GitHub:

1. Open the repository.
2. Click Actions.
3. Click Generate Real Estate Blog Posts.
4. Click Run workflow.
5. Choose:
   - residential
   - commercial
   - auto

This will create a post immediately and update `feed.xml`.

## Important

GitHub scheduled workflows run on UTC time and may be delayed by a few minutes. This is normal.

OpenAI API usage requires billing to be active on your OpenAI platform account.
