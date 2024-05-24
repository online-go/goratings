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
- Background: OGS Ratings v5
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

- Step 3: accumulate $v^{-1}$, which describes opponents' relative ratings and
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
\sigma' &= \sigma \\
\phi'^2 &= \phi^2 + \sigma^2 \\
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

Games are accumulated into $v^{-1}$ and $\Gamma$ like this:
```math
\begin{align}
v^{-1} &= \sum_{j=1}^{m}{g(\phi_j)^2\textrm{E}(\mu,\mu_j,\phi_j)
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
\phi' &= \frac{1}{\sqrt{1/\phi^{\ast 2} + v^{-1}}} \\
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
      from the same category as the player.
- Single TallyGameAnalytics instance, which tallies each game exactly once, in
  its most specific rating category
    - Note: Existing ratings-grid scripts have a separate TallyGameAnalytics
      instance for each ratings category.
    - Measures predictive performance of specific rating categories
    - Ignores predictive performance of general rating categories
- Historical rating volatility metrics should look at all 16 rating graphs.
    - Measure volatility of both specific and general rating categories.

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
- Add per-user, fixed-length time periods for ratings updates, using
  incremental computation to mitigate computation costs
- Fine-tune mid-period "observed" rating/deviation
- Add metrics for games-per-period cross-sectioned by rank, by deviation,
  and by rating category, and tune period length of each rating category
- Tune the $\tau$ system constant for each rating category; consider lower
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

#### Per-user, fixed-length time periods with incremental computation

Set a fixed time period, $P$, as a new system constant to use with each
specific rating category.  E.g., setting categories to "one week" is fine, but
allow it to be changed independently for each rating category.

Thus we have system constants:

- $P$: system constant that sets the length of a time period
- $\tau$: system constant that constrains volatility over time

Previously, we stored for each rating:

- $\mu$: rating (or $r = 173.7178\mu + 1500$)
- $\phi$: rating deviation (or $\textrm{RD} = 173.7178\phi$)
- $\sigma$: rating volatility

Instead, store:

- Initial rating for the period
    - $\mu$: rating
    - $\phi$: rating deviation
    - $\sigma$: rating volatility
- Estimated rating at end of period
    - $\mu'$: rating
    - $\phi'$: rating deviation
    - $\sigma'$: rating volatility
- Period details:
    - $t_{e}$: the timestamp for the end of the rating period
    - $v^{-1}$: accumulation of opponent ratings and deviation for the period
    - $\Gamma$: accumulation of user's performance in the period

Perform a ratings update for each game.

First, define:

- the game's timestamp as $t_{g}$,
- this player's last rating subscripted with $p$ (as in $\mu_{p}$, $\mu_{p}'$,
  $t_{ep}$, etc.), and
- the opponent's last rating subscripted with $o$ (as in $\mu_{o}$, $\mu_{o}'$,
  $t_{eo}$, etc.).

Second, determine the opponent's observed rating and deviation, $\mu_{j}$ and
$\phi_{j}$, for the purposes of updating this player's rating.

If the opponent has no previous games, choose appropriate starting values.

Else, take the rating from the opponent's last period, aging the deviation if
the rating is old:

```math
\mu_j =
\begin{cases}
\mu_o & t_g \leq t_{eo}
\\\mu_o' & t_g > t_{eo}
\end{cases}
\quad \quad
\phi_j =
\begin{cases}
\phi_o & t_g \leq t_{eo}
\\\sqrt{\phi_o'^2 + \frac{t_g - t_{eo}}{P}\sigma'^2} & t_g > t_{eo}
\end{cases}
```

Third, determine whether this game starts a new period for this player or
continues an old one, and accumulate the game result in $v^{-1}$ and $\Gamma$:

If there is no previous game, set $\mu$, $\phi$, and $\sigma$ to appropriate
starting values, and start a period at $t_{g}$:

```math
t_e = t_g + P
```

Else if $t_{g} > t_{ep}$, start a new period at $t_{g}$ and age the deviation
for the gap between periods:

```math
\begin{align}
t_e &= t_g + P, \quad
\mu = \mu', \quad
\sigma = \sigma' \\
\phi &= \sqrt{\phi'^2 + \frac{t_g - t_{ep}}{P}\sigma'^2}
\end{align}
```

In both cases so far, this game starts a new period.  Initialize $v^{-1}$ and
$\Gamma$ from this game result:

```math
\begin{align}
v^{-1} &= g(\phi_j)^2\textrm{E}(\mu,\mu_j,\phi_j)
    \lbrace 1 - \textrm{E}(\mu,\mu_j,\phi_j) \rbrace \\
\Gamma &= s_j - \textrm{E}(\mu,\mu_j,\phi_j)
\end{align}
```

Else, $t_{g} \leq t_{ep}$ and this game is part of an existing period.
Accumulate this game's result with the previous $v^{-1}$ and $\Gamma$:

```math
\begin{align}
t_e &= t_{ep}, \quad
\mu = \mu_p, \quad
\phi = \phi_p, \quad
\sigma = \sigma_p \\
v^{-1} &= v_p^{-1} + g(\phi_j)^2\textrm{E}(\mu,\mu_j,\phi_j)
    \lbrace 1 - \textrm{E}(\mu,\mu_j,\phi_j) \rbrace \\
\Gamma &= \Gamma_p + s_j - \textrm{E}(\mu,\mu_j,\phi_j)
\end{align}
```

Fourth, compute $\Delta = v\Gamma$, $\sigma'$, $\phi'$, and $\mu'$, as in the
Glicko-2 background section.

#### Fine-tune mid-period "observed" rating/deviation

Reduce the volatility in the observed rating graph within time periods by
scaling the rating and deviation change according to the proportion of the
period that game accounts for.

- Define $\mu_{N}$ and $\phi_{N}$, the observed rating and deviation at
  timestamp $N$ (now), using one of the alternatives described below.
- Use $\mu_{N}$ and $\phi_{N}$ for:
    - measuring predictive performance and historical volatility
    - eventually, in OGS, for automatch and setting handicap
- Consider using $\mu_{N}$ and $\phi_{N}$ to set $\mu_{j}$ and $\phi_{j}$ when
  observing opponent ratings during a ratings update.

Here are a few alternatives to implement and evaluate:

##### Last full period

As defined above, use the rating from the last completed time period, and age
the deviation to the current timestamp.  This is the formula used above for
$\mu_{j}$ and $\phi_{j}$.

```math
\mu_N =
\begin{cases}
\mu & N \leq t_e
\\\mu' & N > t_e
\end{cases}
\quad \quad
\phi_N =
\begin{cases}
\phi & N \leq t_e
\\\sqrt{\phi'^2 + \frac{N - t_e}{P}\sigma'^2} & N > t_e
\end{cases}
```

##### Estimated new rating

Or, we could use the estimated new rating, and just age the deviation.

```math
\mu_N = \mu'
\quad \quad
\phi_N =
\begin{cases}
\phi & N \leq t_e
\\\sqrt{\phi'^2 + \frac{N - t_e}{P}\sigma'^2} & N > t_e
\end{cases}
```

##### Scale the estimated new rating

Or, we could scale the estimated rating according to how much of the period has
passed by the time of the observation $N$ (typically, at the time of the next
game).

Given $t_{s} = t_{e} - P$, we have:

```math
\mu_N =
\begin{cases}
\frac{(N - t_s)\mu + (t_e - N)\mu'}{P} & N \leq t_e
\\\mu' & N > t_e
\end{cases}
\quad \quad
\phi_N =
\begin{cases}
\sqrt{\frac{(N - t_s)\phi^2 + (t_e - N)\phi'^2}{P}} & N \leq t_e
\\\sqrt{\phi'^2 + \frac{N - t_e}{P}\sigma'^2} & N > t_e
\end{cases}
```

##### Compute a rating for a partial period

Or, we could compute $\mu_{N}$ and $\phi_{N}$ by inserting a scaling factor
$\alpha_{N}$ in the Glicko-2 formulas to evaluate a partial period.

Assuming $N < t_{e}$, we could keep $\sigma$ or $\sigma'$ and estimate a
partial period like this:

```math
\begin{align}
\alpha_N &= \frac{N - (t_e - P)}{P} \\
\Delta_N &= \alpha_Nv\Gamma \\
\sigma_N &= \sigma | \sigma' \\
\phi^\ast_N &= \sqrt{\phi^2 + \alpha_N\sigma_N^2} \\
\phi_N &= \frac{1}{\sqrt{1/\phi^{\ast 2}_N + \alpha_Nv^{-1}}} \\
\mu_N &= \mu + \alpha_N\phi'v\Gamma
\end{align}
```

Or we could compute $\sigma_{N}$ more precisely for the partial period by
defining:

```math
f(x) = \frac{e^x(\Delta^2 - (\alpha_N\phi^2 + v + e^x))}{2(\alpha_N\phi^2 + v + e^x)^2}
    - \frac{x - \ln\sigma^2}{\tau^2}
```

... and using that to compute $\sigma_{N}$.

#### Add games-per-period metrics and tune period length

Add games-per-period metric, which shows the average number of games per period
for all players in each specific rating category.

For each rating category:

- For each player, compute the average games per period by dividing the number
  of total rated games and by the number of new periods that player had.
    - Ignores time between periods, when the player was inactive.
- Compute both the mean and median of those averages, to understand how many
  games per period an average player experiences.
- Show cross-sections for bots-only vs humans-only vs humans+bots.
- Show cross-sections by rank ranges and by deviation ranges.

Using these data, tune the period length separately for each rating category,
in each case aiming to get the mean games-per-period into the 10-15 game range.

Likely, we want to tune the humans-only games-per-period to the 10-15 games
range, but we might also experiment with tuning the humans+bots metric.

#### Tune the $\tau$ system constant for each rating category

Tune the $\tau$ system constant for each rating category, optimizing for low
historical volatility and high predictive performance.

- Consider lower values for correspondence to counteract naturally high
  volatility in playing strength.
- Consider higher values in rating categories that have long time periods to
  ensure ratings adjust quickly enough.


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
