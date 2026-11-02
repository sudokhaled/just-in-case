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

# Private security reports (SECURITY.md links to this form).
gh api -X PUT "repos/$R/private-vulnerability-reporting"

# Labels used by the issue forms.
gh label create error-report --repo "$R" --force --color B60205 --description "Something in an article is wrong or dangerous"
gh label create review       --repo "$R" --force --color 5319E7 --description "Expert review of an article"
gh label create content      --repo "$R" --force --color 0E8A16 --description "New or changed articles"
gh label create translation  --repo "$R" --force --color 1D76DB --description "Translating the library"
gh label create bug          --repo "$R" --force --color D93F0B --description "A device, the website or the build does not work"
```

Then, in the repository settings on github.com:

1. **Settings > General > Social preview:** upload [`assets/social-preview.png`](assets/social-preview.png). This is the picture shown when someone shares the repo link.
2. **Settings > Moderation options > Reported content:** allow reports, so people can report conduct problems privately (see [CODE_OF_CONDUCT.md](../CODE_OF_CONDUCT.md)).
3. **Settings > Rules > Rulesets:** protect `main`. Require a pull request, and require the "Check and build" workflow to pass.
4. **Discussions:** add a welcome post and pin it, with categories for Q&A, "Show your setup" and Ideas.
5. **Search engines (optional):** add `https://sudokhaled.github.io/just-in-case/` in [Google Search Console](https://search.google.com/search-console) and submit `sitemap.xml` from that address.

## Publishing a release

1. In [CHANGELOG.md](../CHANGELOG.md), move the "Unreleased" notes under a new version heading with today's date, and update the links at the bottom.
2. In [CITATION.cff](../CITATION.cff), update `version` and `date-released`.
3. Commit, then tag and push:

   ```sh
   git tag -a v0.1.0 -m "Just In Case v0.1.0"
   git push origin main v0.1.0
   ```

4. The "Release" workflow builds every edition, the PDFs, the Kindle file and the ESP32 flash images, and publishes them with `SHA256SUMS.txt`. Versions starting with `v0.` get a "public preview" note at the top of the release notes.
5. Check the release page: every file listed in the release notes is there, and the [installer page](https://sudokhaled.github.io/just-in-case/flash/) loads.

Version numbers: stay below 1.0 until the critical (★) articles have been reviewed by experts. Bump the middle number for new articles or editions, and the last number for corrections only.
