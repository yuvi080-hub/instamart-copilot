# Submit to GitHub (steps)

1. Replace `generate_data.py` and `mock_llm.py` with the exact code copied from the PDF (they must be unmodified), then run `python generate_data.py` and check the last line.
2. In VS Code terminal, from this folder:

```
git remote add origin https://github.com/<your-username>/<repo-name>.git
git add .
git commit -m "Use exact supplied files"
git branch -M main
git push -u origin main
```

3. Open the repo in an incognito window: it must be public and the branch must be `main`.
4. Submit: `https://github.com/<your-username>/<repo-name>/tree/main`
