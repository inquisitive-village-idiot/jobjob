<!-- MIGRATION NOTE — added 2026-07-02 during OpenSpec seeding. Original content below
     is verbatim from the earlier `rym-jobjob` project (where these design
     conversations happened) and kept for provenance. -->

> **Migration note (2026-07-02).** Current state and full traceability live in
> `../build-requirements-and-decisions.md` (§3 Config, §7 AI client). What changed
> since this doc:
> - **Config injected value-by-value** was adopted (a single `Settings` built at the
>   entry point; functions take concrete params).
> - **Two-tier config + profiles** were added later and are NOT described here: app
>   `config/.env` vs profile `config/.profile`, plus a profile registry / active profile.
> - **env location:** this doc proposes `./env/.env`; **shipped as `config/.env`** —
>   the spec should assert the shipped location.
> - **Thin AI adapters** adopted, and extended with `ANTHROPIC_BASE_URL` (proxy / free
>   backend); a native non-Anthropic adapter is still open (#26).
> - **`None`-over-empty** adopted for `Applicant`, but some structured records (e.g.
>   `Role`) still default string fields to `""` — a known inconsistency to reconcile.

---

# Requirements: Design Conventions

*Original requirements as stated in chat. Verbatim where possible.*

---

## Config: centralized but injected value-by-value

> A centralized config (1A) makes the most sense, but I'm not a huge fan of propagating a settings
> instance across the script. I propose that each function takes the parameters it needs as input,
> and the top-level function passes the relevant settings through. This keeps the pros of 1A while
> negating the cons, which also keeps the individual function calls cleaner and more modular.

## AI client: thin adapters

> I saw some module constants defined such as name and email. There was some duplication of the
> variables. Also, the script defined these in a config file that the script used at runtime (vs
> defining defaults in the modules themselves).
>
> The client modules were intended to be very light adapters around specific implementations. The
> goal was to easily support additional AI clients, even though anthropic is the only one currently
> used.

## Defaults and None

> I noticed that the applicant fields default to an empty string. In cases like this, either the
> field should be required without a default _or_ allow (and default to) None. Generally, iterables
> should default to None in a function signature and have a line at the top of the function to set
> to an empty of its type, e.g., `names: Iterable[str] | None = None` and `names = names or []`
> (and prefer types from `collections.abc` over `typing`). For dataclasses, use `default_factory`
> where needed for iterable types, and use the same logic as the functions: Either make it required
> without a default or default to None.
>
> Generally, integrations should define a specific default. In cases where a value of None may be
> passed in, use None in the signature and set at the first line of the function (same as the
> example above). Default values should generally only be declared once (so as to avoid confusion of
> which value was used).

## env file

> The `.env` file should live in `./env/.env`; the README should indicate how to create this file
> and point to a template example, and none of the contents of `env/` should be committed except
> for a `.template` (add to `.gitignore`).
