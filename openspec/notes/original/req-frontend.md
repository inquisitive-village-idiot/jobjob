<!-- MIGRATION NOTE — added 2026-07-02 during OpenSpec seeding. Original content below
     is verbatim from the earlier `rym-jobjob` project, kept for provenance. -->

> **Migration note (2026-07-02).** Current state in
> `../build-requirements-and-decisions.md` (§15 Webapp). What changed since this doc:
> - **Architecture as specified** — separate `webapp/` using `jobjob` as a local
>   package, FastAPI + React/TS, security-first — shipped.
> - **#1 Config-in-GUI** (secrets hidden) and **#2 static-content management with AI
>   refine + confirm-before-save** — shipped.
> - **#3 Tracking** is only **partially** met: the queue exists, but listing completed
>   apply/enrich jobs + last-run info + a consolidated row action is open (#44), and
>   GUI **"Rerun" does not regenerate the docs** (bug #46).
> - **#4 ETL** (PDF/docx buttons) — partial / nice-to-have.
> - **#5 "discuss a file with an AI"** — NOT built as chat; effectively superseded by
>   the Prompts editor and résumé-import AI refine.
> - **Added beyond this doc:** Profiles panel, Prompts page, résumé import, self-update,
>   setup wizard, status/notes trail.

---

# Requirements: Frontend (webapp)

*Original requirements as stated in chat. Verbatim where possible.*

---

## Architecture

> For the front end,
> 1. Keep it (somewhat) separate from the other functionality. My preference would be to have it in
>    a separate directory in the repo root -- and have it use jobjob as a local package.
> 2. Use FastAPI for the backend.
> 3. Use whatever is easiest for the front end -- I assume ts and react.
> 4. Ensure a security-first approach.

## Feature requirements

> For the requirements:
>
> 1. **Configuration:** As a user, I want to modify any of the configuration parameters in the GUI
>    (except for secrets, of course -- allow me to update the paths used to generate new scripts,
>    but the secrets shouldn't be visible at all) so that I can manage behavior in the GUI.
>
> 2. **Static data management:** As a user, I want to be able to add, remove, or modify the static
>    content so that I can refine the performance behavior in the GUI. Ideally, I'd be able to
>    manage this via text boxes or by providing a file or a gdoc. It would be nice to have a button
>    to send the content to an AI so that the format and content can be refined for usage -- edits
>    should be confirmed before saving.
>
> 3. **Tracking:** As a user, I want to be able to see tasks that haven't been run so that I can
>    see what I need to process (i.e., an input queue). I'd also like to be able to see executed
>    jobs so that I can easily access and re-run if necessary. (If a user has a google drive sync'd
>    locally, that can be used to determine the available files -- it at least provides the contents
>    of the file system even if it can't see the content. When displayed, the GUI can have each item
>    hyperlinked, so that the document can be opened in a new tab).
>
> 4. **ETL:** It would be really nice to have buttons next to resume and cover letter to convert to
>    PDF or docx if feasible.
>
> 5. **AI Integration:** As a user, I would like to be able to discuss changes and updates to a
>    given file with an AI model.
>
> 1, 2, and 3 are necessary. 4 and 5 are nice to have. The AI mention in 2 is nice to have -- it's
> essentially the same thing as 5.
