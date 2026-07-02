<!-- MIGRATION NOTE — added 2026-07-02 during OpenSpec seeding. Original content below
     is verbatim from the earlier `rym-jobjob` project, kept for provenance. -->

> **Migration note (2026-07-02).** Much of this doc is **one-time migration history**
> (rym.jobjob → jobjob, TDD origin, model choice) and is NOT spec material — extract
> only the durable requirements. Current state in
> `../build-requirements-and-decisions.md`. Status of the durable items:
> - **Single `data/` dir classification** (JD / LinkedIn / unsupported) with
>   **continue-on-error** — shipped (`classify`).
> - **Sub-command entrypoint** (`jobjob/__main__.py` → apply / enrich / auth / autofill)
>   — shipped.
> - **Reprocessing** — shipped (`apply --reprocess`); GUI rerun doc-regeneration is
>   buggy (#46).
> - **Enrich integration + contacts-sheet column contract** — shipped; UI rename to
>   **Rolodex** pending (#45).
> - **Periodic / cron "new-files-else-exit" run** — an original goal; confirm the
>   current implementation state before spec'ing.
> - **Post-date this doc:** autofill, URL/headless ingestion, `experience.toml`, prompt
>   customization, self-update, Sphinx docs, PyPI packaging.

---

# Requirements: jobjob Refactor

*Original requirements as stated in chat, lightly organized. Verbatim where possible.*

---

## Initial brief

> In this repo, I have been storing the code generated from claude.ai under `./extras/`. There are
> two projects: job application script under `./extras/vibe` and the linkedin connection tracker
> under `./extras/enricher`. I have been migrating the script to a modular format using TDD in the
> repo root. The `rym` directory is an implicit namespace that is used across several projects;
> however, I do not want to continue using it for this project -- it should just be "jobjob", not
> "rym.jobjob".
>
> 1. Please refactor the job application script using the TDD code I wrote as a starting point and
>    an example of the pattern and structure.
> 2. After (1), we'll work through the planned work outlined in CLAUDE.md
> 3. I also want to setup a cron job to run periodically so that I can make better usage of usage
>    limits. Both scripts act on an input directory (and move the target files after processing), so
>    the behavior would be to check if there are any new files and end if not.

## Clarification on TDD starting point

> My TDD code includes a clean google auth pattern, a clean ai query pattern, and a clean document
> loading pattern, and a cache handler. However, parts of it may be incomplete. I was working
> directly from the job_apply script, but applying my own style and patterns. The goal is to
> continue the refactor that I started.
>
> I would prefer to use opus 4.8 for this refactor, but sonnet 4.6 is fine for executing the
> package.

## Enricher integration

> The enricher should utilize as much of the existing functionality as possible -- consider
> re-organizing common into a separate sub-module under the jobjob package (though the structure
> largely follows that already).

> Would it be possible for a single "data/" directory and have the program recognize as (a) JD, (b)
> linkedin profile, or (c) unsupported? Currently, (b) isn't supported -- we need to refactor the
> enrichment script into the code base (should be a separate sub-module from the JD parser with a
> separate `__main__.py` entrypoint; though `jobjob` should have a `__main__.py` with sub-commands
> that direct processing to the specific functionality. Unsupported files should log an error, but
> because multiple files are processed at once, processing on other files should continue.

> `jobjob/__main__.py` would be the single entrypoint -- it would define the apply and enrich
> sub-commands, which basically just call the main functions in the appropriate `__main__.py`.
>
> Also, classify should probably be a directory -- there's likely additional functionality that will
> go in there as we expand.
>
> For the enricher, files should be PDFs in almost all cases, so Claude vision shouldn't be
> necessary except as a fallback (I think).

## Re-processing

> Feature: Allow re-processing if given a specific file. The use case is if a JD was processed but
> with errors or if we want to re-generate with newer features. Then we want to point to the JD
> copied into the output directory and update the files in that directory.

## Contacts sheet

> It's on a "contacts" sheet within the spreadsheet. The header is:
> `location  company  role  name  linkedin_url  Request  1st Msg  2nd  3rd  corporate_url
> shared_connections  notes  last_verified  citations  found_by`

## Next steps (stated at end of this phase)

> Please commit each chunk with the suite green -- smaller chunks are better.
>
> The next step: Documentation. Make sure the `docs/` directory has setup and usage docs (link from
> the README).
>
> Once documentation is updated, create a front end that can be run locally to (a) setup the
> configuration, (b) launch new jobs, and (c) review executed jobs.
