# OGS Ratings v6

This living document describes goals and implementation progress for V6 of the
OGS ratings system.

### Goals

- Enable rating system to be used with non-standard komi and board sizes
- Extend metrics analyzed when evaluating rating system to enable more
  experiments
- Improve predictive performance of specific rating categories, enabling their
  use for automatch and handicap (instead of the general "overall" category)
- Make ratings less volatile for players that play lots of games (and play at a
  consistent strength)
- Re-evaluate conditions for annullment of games after timeouts (bot games and
  mass timeout)

### Document organization

- Summary of proposed changes
- Background: Glicko-2
- Backgorund: OGS Ratings v5
- Details of each proposed change

### Legend

- 👍: Approved (maybe not implemented).
- ✅: Implemented and landed (maybe not approved / behind flag).
- 🔃: Implemented in a PR, but not immediately landed.
- 👎: Considered and rejected.

## Summary of proposed changes to rating system

- Compute fine-grained effective rating of opponent based on handicap, komi,
  and ruleset 👍✅
- Increase effective rating deviation of opponent for larger handicaps and
  strange komi values 🔃
- Increase rating deviation as rating ages ✅
- Extend metrics analyzed when tallying
- Add cohesive-ratings-grid script, with the goal of eventually using
  specific ratings categories for matching and handicaps
- Improve predictive performance and volatility of cohesive-ratings-grid
- Evaluate changes to how timeouts are handled, for each of correspondence and
  bots
- Evaluate and/or increase correlation of ratings categories

## Background: Glicko-2

Here's a quick editorialized summary of the Glicko-2 rating system, based on
the [Glicko-2 paper](http://www.glicko.net/glicko/glicko2.pdf) dated March 22,
2022.

### Basic definitions

- $\mu$: the rating, an estimate of the mean of the playing strength
  based on past performance
    - $r = 173.7178\mu + 1500$: a user-friendly view of the rating
- $\phi$: the rating deviation, a standard error for $\mu$
    - $\textrm{RD} = 173.7178\phi$: a user-friendly view of the rating deviation
    - $\phi^2$: the rating variance
- $\sigma$: the rating volatility, how much the rating changes over time
- $\tau$: system constant that constrains volatility over time; higher values
  allow higher volatility

### System constant

Typically, reasonable values of $\tau$ are between 0.3 and 1.2.  Lower values
such as $\tau = 0.2$ are reasonable if extremely improbable collections of game
outcomes are expected.

### New players

The default is to initialize new players to a rating of 1500 ($\mu = 0$), RD of
350 ($\phi = 2.01476$), and $\sigma = 0.6$.  Given prior knowledge about playing
strength, it's okay to set other starting values.

### Rating time periods

Glicko-2 is designed to run periodically (e.g., once per day, week, or month).
$\mu$, $\phi$, and $\sigma$ are updated based on game results over the period,
based on actual game records.

The ideal period length would have 10-15 games per active player.

### Ratings update at end of period

Ratings are updated at the end of each period, computing new values $\mu'$,
$\phi'$, and $\sigma'$ based on the old values ($\mu$, $\phi$, and $\sigma$),
game outcomes, and the rating and deviation of opponents in those games.

A few definitions for the update:

- $m$: the number of games played
- $\mu_{1},...,\mu_{m}$: ratings of opponents in each game, taken from the beginning of
  the rating period
- $\phi_{1},...,\phi_{m}$: rating deviation of opponents in each game, taken from
  the beginning of the rating period
- $s_{1},...,s_{m}$: scores in each game ($0$ for a loss, $0.5$ for a tie, and
  $1$ for a win)

The basic update procedure (editorialized) is:

- Step 3: accumulate $1/v$, which describes opponents' relative ratings and
  their deviation;
- Step 4a: accumulate $\Gamma$ (not in paper), which compares actual scores to expected scores;
- Step 4b: compute $\Delta = v\Gamma$, an estimate of the ratings change;
- Step 5: compute $\sigma'$, the new volatility, using $v$ and $\Delta$;
- Step 6-7a: compute $\phi'$, the new deviation;
- Step 7b: compute $\mu' = \mu + \phi'v\Gamma$, the new rating.

#### Age the deviation using volatility if no games have been played

If the player hasn't played any games in the period, the deviation should
increase by the volatility.  All the steps reduce to the following:
```math
\begin{align}
\sigma' &= \sigma
\phi'^2 &= \phi^2 + \sigma^2
\mu' &= \mu
\end{align}
```

#### Accumulation of games

$g()$, an opponent deviation scale, and $\textrm{E}()$, expected score, are
helpers for the accumulators:
```math
\begin{align}
g(\phi) &= \frac{1}{\sqrt{1 + 3\phi^2/\pi^2}} \\
\textrm{E}(\mu, \mu_j, \phi_j) &=
    \frac{1}{1 + e^{-g(\phi_j)(\mu - \mu_j)}}
\end{align}
```

Games are accumulated into $1/v$ and $\Gamma$ like this:
```math
\begin{align}
\frac{1}{v} &= \sum_{j=1}^{m}{g(\phi_j)^2\textrm{E}(\mu,\mu_j,\phi_j)
    \lbrace 1 - \textrm{E}(\mu,\mu_j,\phi_j) \rbrace} \\
\Gamma &= \sum_{j=1}^{m}{s_j - \textrm{E}(\mu,\mu_j,\phi_j)}
\end{align}
```

#### Compute estimate of rating change

Estimated rating change is:
```math
\Delta = v\Gamma
```

#### Compute new volatility

Define $f()$:
```math
f(x) = \frac{e^x(\Delta^2 - (\phi^2 + v + e^x))}{2(\phi^2 + v + e^x)^2}
    - \frac{x - \ln\sigma^2}{\tau^2}
```
Then set constants $A=\ln\sigma^2$ and $B=...$ to bracket $\ln(\sigma'^2)$, and
run an iterative procedure until $f(A)=f(B)$ to find the new volatility
$\sigma'$.

See Step 5 of [Glicko-2 paper](http://www.glicko.net/glicko/glicko2.pdf) for
the details omitted here.

#### Compute new deviation

The deviation is expanded by the new volatility, $\sigma'$, and then compressed
by the game experiences, $v$:

```math
\begin{align}
\phi^\ast &= \sqrt{\phi^2 + \sigma'^2} \\
\phi' &= \frac{1}{\sqrt{1/\phi^{\ast 2} + 1/v}} \\
\end{align}
```

#### Compute new rating

Finally, the rating is computed using the new deviation:
```math
\mu' = \mu + \phi'v\Gamma
```

## Background: OGS Ratings v5

OGS ratings (v5) uses a modified version of Glicko-2, where rating periods are
variable-length.  A player's rating is updated after each game.  The ratings
period has exactly one game in it, and the period's length is the time since
the last game.

Note that Glicko-2 documentation suggests it works best when active players
have 10-15 games on average in each period, but on OGS every period has exactly
one game.

A few notes about this system:

- Easy to compute.
- Easy to understand/predict the effect of each individual game on ratings.
- Every period looks to Glicko-2 like an "outlier", where the player has
  "surprisingly" either won or lost *all* of their games.
    - Ideally, a rating should be stable if there's lots of data and the
      player's strength is consistent.
    - On OGS, the deviation stays relatively high and ratings are volatile
      (move around a lot) as a result.
- Deviation ought to increase after a long time with no games, but doesn't.

### The ratings grid and ratings categories

Most players have different strengths at different board sizes and game speeds.
OGS ratings (v5) has a grid of ratings for different rating categories.

The primary rating is the general rating category:

- overall

"Overall" is used for match-making (automatch) and for setting handicaps.

There are also nine "specific" rating categories, representing board size and
game speed:

- blitz-9x9
- blitz-13x13
- blitz-19x19
- live-9x9
- live-13x13
- live-19x19
- correspondence-9x9
- correspondence-13x13
- correspondence-19x19

... and six general categories in the middle:

- blitz
- live
- correspondence
- 9x9
- 13x13
- 19x19

... for 16 ratings total.

These are each separately maintained ratings:

- After a player finishes a game, their rating is update in the three relevant
  categories.
- For "overall", the ratings are updated as specified above.
- The other two ratings use take the opponent's rating and deviation ($\mu_{j}$
  and $\phi_{j}$) from the "overall" category.

A few notes about the rating categories:

- Players get some visibility into their playing strength in different
  categories.
- Overall has a recency bias, dominated by the player's most recent games.
  Thus, automatch and handicap settings are based on the recent games as well.
    - Great if the player has had a dramatic change in strength while only
      playing with one specific category.
    - Not great if the player consistently has a different strength in
      different categories.
    - OGS forum regulars recommend maintaining multiple accounts, one for each
      specific rating category, as standard practice to work around this.

## Details of proposed changes for Ratings v6

### Compute fine-grained effective rating of opponent based on handicap, komi, and ruleset

- Increases accuracy of ratings updates.
- Handles non-standard komi (including handicap via reverse komi) cleanly,
  enabling a policy decision to allow rated games with non-standard komi.
- Can easily be extended to handle non-standard board sizes (such as 7x7 or
  25x25) by specifying a multiplier.

#### Details

- Computes a fractional effective handicap for game
- Assumes a territorial value of 12 for each stone at start of game
    - Komi of 6 considered perfect for territory
    - Komi of 7 considered perfect for area, since black usually gets extra
      play
- Combines value of handicap stones and effective komi (including handicap
  bonus), and compares against perfect komi to determine black's advantage
- Divides by territorial value of stones to get effect rank difference
    - Multiplier of 3 for 13x13
    - Multiplier of 6 for 9x9
- Extensible to other board sizes.  For example, we could try:
    - Multiplier of 12 for 7x7
    - Multiplier of 0.5 for 25x25

### Increase effective rating deviation of opponent for larger handicaps and strange komi values

- Reflects higher uncertainty that opponents' rating is correct, the more
  the board diverges fom "normal".
- Reduces impact of high handicap games on ratings, enabling a policy
  decision to allow rated 19x19 games with 10+ stones.
- Reduces impact of reverse-komi games on ratings, enabling a policy
  decision to allow handicap via reverse komi.

#### Details

- [#70](https://github.com/online-go/goratings/pull/70)
- An error value is computed based on how "strange" the handicap is.
- For each rating update, the opponent's rating deviation is expanded by error
  using root-of-sum-of-squares

### Increase rating deviation as rating ages

- More closely matches the design of Glicko-2, where deviation increases when
  no games are played.
- Reflects that strength may have atrophied through neglect or improved
  through study elsewhere.

#### Details

- Command-line option: `--aging-period`
- Before using a rating, checks if its timestamp is older than the length of
  the aging period.
    - If so, increases deviation according using the formula to "age" it to 1
      period old.
    - Else, uses it as-is.

### Extend metrics analyzed when tallying

Goals:

- Show whether and how much predictions improve when we expect them to (higher
  rank difference, lower deviation, etc.)
- Show rating volatility
- Clean up noise in the analysis output for metrics we don't know how to use

#### Details

- Tally all rated games (stop ignoring rank diff greater than ±1)
- Show black win rate cross-sectioned by rank (as now!), by deviation, and
  by rating category; still limited to rank diff ±1
- Show expected-winner-wins rates cross-sectioned by effective rank diff,
  by rank, by deviation, and by rating category
- Show daily/weekly/monthly historical rating volatility cross-sectioned by
  rank, by deviation, by game frequency, and by rating category
- Remove old metrics we don't look at any more

### Add cohesive-ratings-grid script

Goals:

- Enable analysis of using specific rating categories (rather than "overall")
  as the primary rating(s)
- Add foundation for improving predictive performance of a ratings system
  centered on specific rating categories
- Land this script whether or not it's better than using "overall" as the
  primary rating. (It probably won't be, initially!)

#### Details

- For bring-up, each rating category is updated in isolation
    - Note: Initially, like ratings v5, except opponent rating/deviation come
      from the same category.
- Single TallyGameAnalytics instance, which tallies each game exactly once, in
  its most specific rating category
    - Note: Existing ratings-grid scripts have a separate TallyGameAnalytics
      instance for each ratings category.
    - Measures predictive performance of specific rating categories
    - Ignores predictive performance of general rating categories
- Historical rating volatility metrics should look at all 16 rating graphs.

### Improve predictive performance and volatility of cohesive-ratings-grid

Goals:

- Improve the predictive performance of specific rating categories, beating
  "overall"
- Reduce the volatility of ratings without compromising predictive performance
    - If a player's strength changes, we still want the system to respond
      quickly!

#### Details

- Change general rating categories to be weighted averages of specific
  categories, instead of independently computed Glicko-2 ratings
- For stale rating categories, blend in general rating categories

***TODO: add subsections / math explainers for the bullets below***

- Add per-user time periods for ratings updates, using incremental math to
  avoid high computation costs for periods with many games
- When adding a new game, lock in rating/deviation of previous game to
  reflect how much of its period it represents
- Add metrics for games-per-period cross-sectioned by rank, by deviation,
  and by rating category, and tune period length of each rating category
- Tune the τ system constant for each rating category; consider lower
  values for correspondence to counteract naturally high volatility

#### Ratings flow: general vs. specific, last vs. effective, and aging

This proposal differentiates between:

- "last" rating, which is the most recent rating after rating a game; and
- "effective" rating, which is the rating used as input for the next ratings
  update, and should be used for matching, handicap, and the UI.

This distinction clarifies the relationship between general and specific rating
categories.

- For the "last" rating, the flow is upward: specific ratings are averaged to
  compute a new general rating.
- For "effective" ratings, the flow is downward: general ratings can be blended
  into the specific rating.

Also, either type of rating can be aged to a newer timestamp by expanding its
deviation.  Unless otherwise stated, it's assumed that a "last" rating has not
been aged, but an "effective" rating has been.

#### Compute last general rating as weighted average of last specific ratings

After rating a game in a specific rating category, compute all relevant general
rating categories by combining the new specific rating with the last ratings in
other specific categories from previous games, using a weighted average.  If
there is no "last" rating, since no games have yet been rated, that category
should be excluded.

The new general rating will have the timestamp of the just-rated game.  Other
ratings should be aged to the same timestamp (expanding their deviation) before
combining them.

This proposal bases the weights on the deviation; specifically, the inverse of
the variance, $\frac{1}{\phi^2}$.  The lower the deviation, the more confident
the rating system is in the rating.  Because old ratings are aged, fresher
ratings can have a bigger impact, but they don't necessarily dominate.

For example, to compute the general blitz rating, $\mu_{b}$, first compute
weights for combining the specific blitz-9x9, blitz-13x13, and blitz-19x19
ratings:
```math
w_{b_9}    = \frac{1}{\phi^2_{b_{ 9}}} \quad
w_{b_{13}} = \frac{1}{\phi^2_{b_{13}}} \quad
w_{b_{19}} = \frac{1}{\phi^2_{b_{19}}}
```
Note: if this player has no rated blitz 9x9 games, then $w_{b_{9}}=0$,
regardless of the default value for $\phi$.

Then compute the general rating, variance, and volatility as weighted averages:
```math
\begin{align}
\mu_b &= \frac{w_{b_9}\mu_{b_9} + w_{b_{13}}\mu_{b_{13}}
                                + w_{b_{19}}\mu_{b_{19}}}
              {w_{b_9} + w_{b_{13}} + w_{b_{19}}} \\
\phi^2_b &= \frac{w_{b_9}\phi^2_{b_9} + w_{b_{13}}\phi^2_{b_{13}}
                                      + w_{b_{19}}\phi^2_{b_{19}}}
                 {w_{b_9} + w_{b_{13}} + w_{b_{19}}} \\
\sigma^2_b &= \frac{w_{b_9}\sigma^2_{b_9} + w_{b_{13}}\sigma^2_{b_{13}}
                                          + w_{b_{19}}\sigma^2_{b_{19}}}
                   {w_{b_9} + w_{b_{13}} + w_{b_{19}}} \\
\end{align}
```
Note: the deviation, $\phi$, is the square root of the variance, $\phi^2$.

At least initially, the overall rating should be computed in the same way,
directly from the specific rating categories. Perhaps in the future we'll want
to experiment with another option:

- cascade up, combining 9x9, 13x13, and 19x19;
- cascade up, combining blitz, live, and correspondence; or
- average of the those two possibilities.

#### Compute effective specific rating using blend of effective overall rating

When a rating category is stale -- it has a high deviation and/or hasn't been
used recently -- other rating categories with more recent games may be better
predictors of performance.  This proposal dynamically blends the effective
overall rating into the specific rating when it seems stale enough.

The blend is weighted by age and deviation, it's gradual (to prevent cliffs),
and it cascades from the overall rating through the midpoints to the specific
rating.

Blending has two scaling factors:

- $w_{t}$ (time) starts when the last specific rating is at least 30
  days older than the last general rating; and
- $w_{\phi}$ (deviation) starts when, after aging, the last specific rating has
  a $\phi$ at least 0.3 (~50 RD) higher than the last general rating.

```math
w_t =
\begin{cases}
0 & \textnormal{if $t_g - t_s \leq 30 \cdot 24 \cdot 3600$}
\\1 & \textnormal{if $t_g - t_s - 30 \geq 365 \cdot 24 \cdot 3600$}
\\\frac{t_g - t_s - 30}{365} & \textnormal{otherwise}
\end{cases}
\quad \quad
w_\phi =
\begin{cases}
0 & \textnormal{if $\phi_s - \phi_g \leq 0.3$}
\\1 & \textnormal{if $\phi_s - \phi_g - 0.3 \geq 1.2$}
\\\frac{\phi_s - \phi_g - 0.3}{1.2} & \textnormal{otherwise}
\end{cases}
```
These scaling factors are combined and must both be active for $w_{g}$ to be
greater than 0:
```math
w_g = w_t \cdot w_\phi \quad \quad w_s = 1 - w_g \\
```
The effective specific rating is the weighted average of the specific and
general ratings. The deviation and volatility are increased by the weight of
the general rating.
```math
\begin{align}
\mu &= w_s\mu_s + w_g\mu_g \\
\phi^2 &= \phi^2_s +
\begin{cases}
0 & \textnormal{if $\phi_s \geq 1.43911$}
\\w_g\phi^2_g & \textnormal{otherwise}
\end{cases} \\
\sigma^2 &= \sigma^2_s +
\begin{cases}
0 & \textnormal{if $\sigma_s \geq 1.2$}
\\w_g\sigma^2_g & \textnormal{otherwise}
\end{cases} \\
\end{align}
```


### Evaluate changes to how timeouts are handled, for each of correspondence and bots

- Alternative #1: Annull all games lost by timeout (status quo for bots)
- Alternative #2: Annull games 2+ mass timeout (status quo for correspondence)
- Alternative #3: Annull games 4+ mass timeout
- Alternative #4: Do nothing (treat as normal result)
- Alternative #5: Add error/deviation to all timeouts
- Alternative #6: Add error/deviation to 2+ mass timeouts

### Evaluate and/or increase correlation of ratings categories

- Add metrics for similarity across time, using deviation cut-offs to
  filter out stale ratings
- Compare blitz vs live vs correspondence; consider whether there are
  options for increasing correlation
- Compare 9x9 vs 13x13 vs 19x19; tune rank-to-stone multipliers, and
  consider other options for increasing correlation
