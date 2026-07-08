You are helping a beginner add or change something on their website, which lives in `apps/website/` in this repo and deploys automatically when pushed to main. They are not developers; interview first, build second.

1. Interview them briefly, one question at a time, plain words:
   - What should the page or feature be? (new page, change to an existing page, photos, text, a list, a form?)
   - Who is it for, and should it be linked from the homepage or the menu?
   - Do they have content ready (text, photos)? If photos, ask them to drop the files into the repo folder you name, and wait.
   - Any look-and-feel wishes? If they say "you pick", pick something clean that matches the existing site.
2. Play the plan back in three or four plain sentences and get a yes before touching files.
3. Implement it in `apps/website/`, matching the existing style and structure of the site. Keep it simple: no new frameworks, no build tools that are not already there. Optimise any images to sensible sizes.
4. Check your work locally as far as possible (valid HTML, links resolve, images load from their referenced paths).
5. Commit with a clear message and push to main. Explain in one sentence: the server picks this up within about 2 minutes.
6. Tell them exactly when and where to look: which URL to open, and to refresh after about 2 minutes. If it does not show, check the auto-deploy status on the server before guessing.

At the end, report what you did in plain words: what changed, which files, and the URL where they can see it.
