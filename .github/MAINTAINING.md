# Maintaining

Notes for maintainers: the one-time GitHub setup, and how to publish a release. Contributors do not need any of this.

## One-time setup

Run these once, after the repository exists on GitHub. They need the [GitHub CLI](https://cli.github.com/) logged in (`gh auth login`).

```sh
R=sudokhaled/just-in-case

# Create the public repository and push (skip if it already exists).
gh repo create "$R" --public
git push -u origin main

# Description, website and topics: these decide how people find the repo.
gh repo edit "$R" \
  --description 'Offline survival library: water, food, first aid, shelter and disasters. Runs on paper, Kindle, any phone and a $3 ESP32 WiFi hotspot.' \
  --homepage 'https://sudokhaled.github.io/just-in-case/' \
  --enable-issues --enable-discussions --enable-wiki=false \
  --add-topic survival,emergency-preparedness,disaster-preparedness,first-aid,prepping,preparedness \
  --add-topic offline,offline-first,off-grid,homesteading,humanitarian,open-knowledge,knowledge-base \
  --add-topic esp32,esp8266,raspberry-pi,captive-portal,kindle,epub,creative-commons

# Website: publish with the "Website" workflow (Settings > Pages > Source: GitHub Actions).
# The first push ran that workflow before Pages existed, so run it again.
gh api -X POST "repos/$R/pages" -f build_type=workflow
gh workflow run pages.yml --repo "$R"

# Labels used by the issue forms.
gh label create error-report --repo "$R" --force --color B60205 --description "Something in an article is wrong or dangerous"
gh label create review       --repo "$R" --force --color 5319E7 --description "Expert review of an article"
gh label create content      --repo "$R" --force --color 0E8A16 --description "New or changed articles"
gh label create translation  --repo "$R" --force --color 1D76DB --description "Translating the library"
gh label create bug          --repo "$R" --force --color D93F0B --description "A device, the website or the build does not work"

# Lock the repository down, then read every protection back from GitHub.
python3 tools/repo_guard.py apply
python3 tools/repo_guard.py check
```

`repo_guard.py apply` makes sure nobody can change `main` or publish without you:

- Nobody, including you, can force-push or delete `main`.
- Everyone except you (the admin) must open a pull request that passes the build check and that you approve as code owner.
- Only you can create, move or delete `v*` release tags.
- Each release waits for your approval, and the website deploys only from `main`.
- Workflows get a read-only token unless they ask for more, cannot approve pull requests, and may use only GitHub's actions and the pinned ones in our workflows. Pull requests from outside contributors need your approval before their workflows run.
- Private vulnerability reporting is on (SECURITY.md links to it).

Run `check` again any time, for example after changing settings or adding a collaborator. It exits with an error if any protection is missing.

Your account is the last line of defense: use two-factor sign-in (a passkey or an authenticator app), and remove old tokens and apps you no longer use at https://github.com/settings/tokens and https://github.com/settings/applications.

Then, in the repository settings on github.com:

1. **Settings > General > Social preview:** upload [`assets/social-preview.png`](assets/social-preview.png). This is the picture shown when someone shares the repo link.
2. **Discussions:** add a welcome post and pin it, with categories for Q&A, "Show your setup" and Ideas.
3. **Search engines (optional):** add `https://sudokhaled.github.io/just-in-case/` in [Google Search Console](https://search.google.com/search-console) and submit `sitemap.xml` from that address.

## Publishing a release

1. In [CHANGELOG.md](../CHANGELOG.md), move the "Unreleased" notes under a new version heading with today's date, and update the links at the bottom.
2. In [CITATION.cff](../CITATION.cff), update `version` and `date-released`.
3. Commit, then tag and push:

   ```sh
   git tag -a v0.1.0 -m "Just In Case v0.1.0"
   git push origin main v0.1.0
   ```

4. **Approve the release.** The "Release" workflow waits for you: open it in the Actions tab (or the GitHub mobile app), click **Review deployments**, tick **release** and click **Approve and deploy**. It then builds every edition, the PDFs, the Kindle file and the ESP32 flash images, and publishes them with `SHA256SUMS.txt`. Versions starting with `v0.` get a "public preview" note at the top of the release notes.
5. Check the release page: every file listed in the release notes is there, and the [installer page](https://sudokhaled.github.io/just-in-case/flash/) loads.

Version numbers: stay below 1.0 until the critical (★) articles have been reviewed by experts. Bump the middle number for new articles or editions, and the last number for corrections only.
