# Python for Phase 4c2

There is no new Python in Part 4c2. All the changes are in `web/` (TypeScript and React), which you know.

The Python this part depends on:

- `domain/locate.py` (4a2) gives each quote its `page`, `page_size` and line `rects`, in PDF points, with y counted
  from the bottom of the page. `web/src/lib/boxes.ts` turns them into pixels.
- `api/routes.py` serves each sample PDF at `/v1/samples/{id}/pdf` with `FileResponse` (4a). The PDF pane loads it
  from there.

The next part, 4c3, has a little Python: `web/e2e/fixtures.py` (see `py/phase-4c3.md`).
