This repository contains the (future) official rating and ranking system for
online-go.com, as well as analysis code and data to develop that system and
compare it to other reference systems.

# Using and developing

There are four main directories to be aware of.

`data` houses raw game record databases. At a minimum we have 12M ranked games
to work with that contains data from Online-Go.com, contributions of other
large data sets are welcome.

`analysis` houses code we use to analyze the performance of different rating
system configurations. This is where we try new things and house useful code
during the our development efforts. Once particular system and configuration 
becomes stable, we can promote it into the `goratings` directory for publishing.

`goratings` and `unit_tests` house the (future) official rating and ranking
code. In these directories at a minimum the official rating and ranking code
and associated tests for online-go.com will be housed, other reference systems
are welcome in here as well. All code in the goratings directory will need to
be fully type annotated, lint and black clean, and have 100% test coverage.
The code under this module will be packaged and published in an official ratings
go ratings/ranking python module.


# Goals

The ideal ranking system for Go will be able to quickly determine a player's strength
and assign a ranking to that player such that the rank difference between two players
can be used to compute an appropriate handicap in game.  

In our quest to find the best rating and ranking system for the game of Go, we
will be attempting to optimize the system to produce the best prediction
results for handicap and non handicap games, and secondarily minimizing the
number of games needed to establish a reasonable confidence of a player's
strength. 

# Quick start

To do test runs you'll want to be editing and running files in the `analysis` directory.
For example, this should work out of the box:

```
analysis/analyze_glicko2_one_game_at_a_time.py
```
