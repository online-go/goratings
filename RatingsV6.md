# OGS Ratings v6

This living document describes goals and implementation progress for V6 of the
OGS ratings system.

### Document organization

- Summary of planned changes.
- Overview of OGS Ratings V5, including known and perceived flaws.
- Details of each change.
    - Details initially lacking...

### Legend

- 👍: Approved (maybe not implemented).
- ✅: Implemented and landed (maybe not approved / behind flag).
- 🔃: Implemented in a PR, but not immediately landed.
- 👎: Considered and rejected.

## Summary of planned changes

- Make ratings categories (mostly) independent.
    - Uses the fine-grained rating (e.g., `blitz-9x9`) directly when it's
      trustworthy.
    - Leverages the broader data pool (e.g., blending with `blitz`, `9x9`,
      and/or `overall`) when the fine-grained rating is stale.
    - Enables matchmaking and auto-handicapping based on (mostly) independent
      fine-grained categories.
- Increase rating deviation over time as a rating's timestamp gets older. ✅
    - Command-line option: `--aging-period`
    - Matches the design of Glicko-2, where deviation increases when no
      games are played.
    - Reflects that strength may have atrophied through neglect or improved
      through study elsewhere.
- Update ratings using a sliding, time-based period.
    - Matches the design of Glicko-2, where games within a given time slice are
      analyzed together.
        - Except that it's sliding, to limit cliffs.
    - Smoothes out the rating curve for players that play multiple games in a
      period.
    - Hypotheses:
        - Activates more fully the Glicko-2 volatility metric, which is what
          differentiates Glicko-2 from Glicko-1.
        - Reduces rating volatility from temporary hot and cold streaks, but
          still allows quick rating changes if the streak is long enough.
- Compute fine-grained effective rating of opponent based on handicap, komi,
  and ruleset. 👍✅
    - Increases accuracy of ratings updates.
    - Handles non-standard komi (including handicap via reverse komi) cleanly,
      enabling a policy decision to allow rated games with non-standard komi.
    - Can easily be extended to handle non-standard board sizes (such as 7x7 or
      25x25) by specifying a multiplier.
- Increase effective rating deviation of opponent for larger handicaps and
  strange komi values. 🔃
    - [#70](https://github.com/online-go/goratings/pull/70)
    - Reflects higher uncertainty that opponents' rating is correct, the more
      the board diverges fom "normal".
    - Reduces impact of high handicap games on ratings, enabling a policy
      decision to allow rated 19x19 games with 10+ stones.
    - Reduces impact of reverse-komi games on ratings, enabling a policy
      decision to allow handicap via reverse komi.
- Stop annulling bot games just because a human disappears.
    - Avoids adding noise that can reverberate through the whole rating system.
    - Note: Humans often abandon bot games instead of resigning because they
      don't feel rude doing so.
- Tune the annulment of correspondence games after timeout.
    - Notes:
        - There seem to be more timeouts for lost games than won games. The
          status quo adds noise to the rating system.
        - With independent rating categories, impact from mass timeouts would
          be limited to correspondence ratings categories.
        - With Glicko-2 and no restrictions on rank of opponents, recovering
          mass-timeouters won't need to beat up many opponents on their way.
    - Alternative #1: Don't do anything special. Delete annulling code.
    - Alternative #2: Only protect the mass-timeouter from ratings drop. Allow
      opponents the wins.
    - Alternative #3: Artificially increase the deviation of the
      mass-timeouter. (But maybe Glicko-2 would just do this on its own?)

## OGS Ratings v5

[t.b.d.]

