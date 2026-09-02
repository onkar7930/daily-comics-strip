# Random Daily Comic Viewer

Serves a random comic strip (Calvin and Hobbes, Garfield, Peanuts, etc. via
GoComics) each day, for embedding in an Obsidian daily note iframe — same
idea as [dilbert-viewer](https://github.com/rharish101/dilbert-viewer), but
pulling from many strips instead of just one.

The pick is **seeded by the date**, so it's random day-to-day but stable if
you reload the same note multiple times in one day.

> **Note on Dilbert:** GoComics dropped Dilbert entirely in 2023, so it's not
> in the list below. If you still want it in the rotation, keep running the
> original dilbert-viewer alongside this and add a "source" step that
> sometimes points at it instead — see "Adding Dilbert back" below.

## 1. Deploy

1. Create a new GitHub repo and push this folder to it.
2. Go to [vercel.com](https://vercel.com), sign in with GitHub, "Add New
   Project", pick the repo. No config changes needed — Vercel auto-detects
   the Python function in `api/`.
3. Deploy. You'll get a URL like `https://your-project.vercel.app`.

## 2. Use it in Obsidian

In your daily note template, replace the old iframe with:

```html
<iframe style="height:400px;width:100%;" class="responsive-iframe"
  src="https://your-project.vercel.app/api/comic"></iframe>
```

No date templating needed — the server figures out "today" itself. Clicking
the comic opens the original GoComics page in a new tab.

If you ever want to preview a specific day (e.g. to test), you can pass a
date manually: `.../api/comic?date=2026-09-02`

## 3. Customize the comic list

Edit the `COMICS` list at the top of `api/comic.py`. Each entry needs:

- `slug` — the part of the URL after `gocomics.com/` (check any strip's URL
  to find it)
- `start` / `end` — the range of years that strip actually published, so the
  picker doesn't land on a date with nothing there

Browse [gocomics.com/comics/a-to-z](https://www.gocomics.com/comics/a-to-z)
for slugs and run dates.

## 4. Adding Dilbert back (optional)

Since Dilbert isn't on GoComics anymore, you'd need a second source. One
option: give each entry in `COMICS` a `"source"` field (`"gocomics"` or
`"dilbert"`), and branch in `pick_strip`/`get_comic_image` to build either a
gocomics.com URL or a `dilbert-viewer.herokuapp.com/{{YYYY-MM-DD}}` URL (note
dilbert-viewer only has strips from 1989–2023, so you'd need a year range
like the others). Happy to write that branch if you want it — just say the
word.

## How it works

GoComics strip pages include an `og:image` meta tag pointing at that day's
image. The function fetches the page for a randomly chosen comic/date and
regex-extracts that tag, then returns a barebones HTML page with just the
image — sized to fill the iframe.
