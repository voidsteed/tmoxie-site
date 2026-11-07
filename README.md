# tmoxie site

Public, dependency-free product, pricing, tutorial, documentation, legal, and support site for the tmoxie iPhone app.

- [Product](https://tmoxie.app/)
- [Pricing](https://tmoxie.app/pricing/)
- [Tutorials](https://tmoxie.app/tutorials/)
- [Documentation](https://tmoxie.app/docs/)
- [Privacy policy](https://tmoxie.app/privacy/)
- [Terms of use](https://tmoxie.app/terms/)
- [Support](https://tmoxie.app/support/)

GitHub Pages deploys the `main` branch at `https://tmoxie.app/`. Keep `CNAME` and trailing-slash canonical page URLs. The app source remains in its separate private repository.

## Check site changes

Run the dependency-free validator from the checkout.

```sh
python3 -B tools/validate_seo.py
```

The validator checks the exact page tree, unique metadata, canonical URLs, social metadata, structured data, internal resources and fragments, robots, sitemap, and the plain-text `llms.txt` guide. Update the page registry when adding a useful public page. Update a sitemap `lastmod` only when that page actually changes. Do not refresh dates merely because the validator runs.

For browser verification, serve the checkout with a local static server. Keep server logs, browser state, screenshots, and reports on the verified mac-ssd task directory. Use an isolated gstack browse profile. The optional check compares the actual served bytes of every page and linked resource with source, checks indexability, and exercises slash redirects and a missing URL.

```sh
python3 -B tools/validate_seo.py --browser /absolute/path/to/isolated-browse --base-url http://127.0.0.1:8765
```

After publishing, repeat the same check with `--base-url https://tmoxie.app`. A local pass does not verify the deployment. `llms.txt` is an assistive reading guide, not a crawler permission policy or a guarantee of inclusion in AI search. `robots.txt` is the crawler directive file.

## Request indexing after publication

1. Verify the deployed source with the browser check above.
2. In [Google Search Console](https://search.google.com/search-console), use an existing verified `tmoxie.app` property or have the domain owner complete verification. Submit `https://tmoxie.app/sitemap.xml`, inspect the product, tutorial, and documentation URLs, and request indexing for those pages.
3. In [Bing Webmaster Tools](https://www.bing.com/webmasters/), use an existing verified property or complete owner verification. Submit the same sitemap and inspect crawl results.

Do not create ownership tokens or make submissions without the owner's verified property. IndexNow is optional. Configure it only after an owned key file is actually served and validated for this host. Neither a sitemap submission nor IndexNow guarantees indexing or rankings.

Keep the App Store launch statement and the app's documented limits accurate. Add a public download link only after that destination is released and verified. Do not add invented reviews, ratings, prices, or unsupported compatibility claims to structured data.
