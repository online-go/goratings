/*************************************************************************************

	Copyright 2010 Philip Waldron
	
    This file is part of BayRate.

    BayRate is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    BayRate is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with BayRate.  If not, see <http://www.gnu.org/licenses/>.
    
***************************************************************************************/

#include <iostream>
#include <vector>
#include <map>
#include <cmath>
#include <algorithm>
#include <gsl/gsl_errno.h>
#include <gsl/gsl_interp.h>
#include <gsl/gsl_multimin.h>
#include <gsl/gsl_sf_erf.h>
#include <gsl/gsl_blas.h>
#include <gsl/gsl_linalg.h>
#include <gsl/gsl_rng.h>
#include <gsl/gsl_randist.h>
#include "collection.h"
#include "player.h"
#include "game.h"
#include "tdListEntry.h"

#include <assert.h>

using namespace std;

double my_new_f (const gsl_vector *v, void *c) {
	double pt;

	collection *collect_ptr = (collection *)c;

	pt = collect_ptr->calc_pt(v);
	return (-pt);
}

void my_new_df (const gsl_vector *v, void *c, gsl_vector *df) {
	collection *collect_ptr = (collection *)c;

	collect_ptr->calc_pt_df(v, df);
	gsl_vector_scale(df, -1.0);
}

void my_new_fdf (const gsl_vector *v, void *c, double *f, gsl_vector *df) {
	*f = my_new_f (v, c);
	my_new_df(v, c, df);
	


}

collection::collection(void)
{	
	// Set necessary constants
	PI = 4.0 * atan(1.0);
	
	// Initialize a random number generator
	T = gsl_rng_default;
	r = gsl_rng_alloc(T);
	
	// Emit messages?
	quiet = false;

	fdfiterations = 0;
	simplexiterations = 0;
}

collection::~collection(void)
{
	gsl_rng_free(r);
}

void collection::reset() {
	playerHash.clear();
	gameList.clear();
}

void collection::setQuiet (bool q) {
	quiet = q;
}

int  collection::getFdfIterations() {
	return fdfiterations;
}

int  collection::getSimplexIterations() {
	return simplexiterations;
}

/****************************************************************

calc_sigma2 () 

Calculate the new sigmas for players.  This function uses numerical 
integration technique to calculate the variances directly.

*****************************************************************/
void collection::calc_sigma2() {
	map<int, double> newSigma;
	double sumX2W, sumW;
	double x, r, z, w;
		
	for (map<int, player>::iterator It=playerHash.begin(); It!=playerHash.end(); It++) {		
		sumX2W = 0;
		sumW   = 0;
		
		for (int i=0; i<100; i++) {
			x = -5.0*It->second.sigma - It->second.sigma/20.0 + i*It->second.sigma/10;
			r = It->second.rating + x;  			
			z = (r - It->second.seed)/It->second.sigma;
			w = exp(-z*z/2)/sqrt(2*PI);
	
			// Inefficient, but fast enough for typical AGA cases.  A more advanced game indexing
			// data structure would be appropriate for larger tournaments 
			for (vector<game>::iterator gameIt=gameList.begin(); gameIt!=gameList.end(); gameIt++) {
				if (gameIt->white == It->second.id) {
					double rd = r - playerHash[gameIt->black].rating - gameIt->handicapeqv;
					if (gameIt->whiteWins)
						w *= gsl_sf_erfc(-rd/gameIt->sigma_px/sqrt(2.0));
					else
						w *= gsl_sf_erfc(rd/gameIt->sigma_px/sqrt(2.0));				
				}					
				else if (gameIt->black == It->second.id) {
					double rd = playerHash[gameIt->white].rating - r - gameIt->handicapeqv;
					if (gameIt->whiteWins)	
						w *= gsl_sf_erfc(-rd/gameIt->sigma_px/sqrt(2.0));
					else
						w *= gsl_sf_erfc(rd/gameIt->sigma_px/sqrt(2.0));				
				}
			}
			sumX2W += x*x*w;
			sumW   += w;
		}
		// Stuff the new sigma into a holding array until all the other sigmas are calculated.
		newSigma[It->second.id] = sqrt(sumX2W/sumW);
	}

	// Copy over the new sigmas now that all the calculations are done
	for (map<int, player>::iterator It=playerHash.begin(); It!=playerHash.end(); It++)		
		It->second.sigma = newSigma[It->second.id];	
}

/****************************************************************

calc_sigma () 

Calculate the new sigmas for players.  This function uses the Laplace
approximation to calculate the sigmas.

TODO: deal with the possibility of the matrix inversion routine failing.  
This can happen if the matrix is not positive definite.  
In that case calc_sigma2() should be used as a backup. 

*****************************************************************/
void collection::calc_sigma() {
	int signum;

	gsl_matrix *A = gsl_matrix_calloc(playerHash.size(), playerHash.size());
	gsl_matrix *B = gsl_matrix_calloc(playerHash.size(), playerHash.size());

	// Contribution from each player is 1/sigma^2	
	for (map<int, player>::iterator playerIt = playerHash.begin(); playerIt != playerHash.end(); playerIt++) {
		gsl_matrix_set(A, playerIt->second.index, playerIt->second.index, 1.0/playerIt->second.sigma/playerIt->second.sigma);  
	}

	for (vector<game>::iterator gameIt = gameList.begin(); gameIt != gameList.end(); gameIt++) {
		if (gameIt->whiteWins) {
			double rd = playerHash[gameIt->white].rating - playerHash[gameIt->black].rating - gameIt->handicapeqv;

			double temp1 = exp(-rd*rd/2.0/gameIt->sigma_px/gameIt->sigma_px);
			double temp2 = gsl_sf_erfc(-rd/sqrt(2.0)/gameIt->sigma_px);

			gsl_matrix_set(A, playerHash[gameIt->white].index, playerHash[gameIt->black].index, -sqrt(2.0/PI)/gameIt->sigma_px/gameIt->sigma_px/gameIt->sigma_px * rd * temp1 / temp2 - 2.0/PI/gameIt->sigma_px/gameIt->sigma_px * temp1 * temp1 / temp2 / temp2 + gsl_matrix_get(A, playerHash[gameIt->white].index, playerHash[gameIt->black].index));
			gsl_matrix_set(A, playerHash[gameIt->black].index, playerHash[gameIt->white].index, -sqrt(2.0/PI)/gameIt->sigma_px/gameIt->sigma_px/gameIt->sigma_px * rd * temp1 / temp2 - 2.0/PI/gameIt->sigma_px/gameIt->sigma_px * temp1 * temp1 / temp2 / temp2 + gsl_matrix_get(A, playerHash[gameIt->black].index, playerHash[gameIt->white].index));
			gsl_matrix_set(A, playerHash[gameIt->white].index, playerHash[gameIt->white].index, sqrt(2.0/PI)/gameIt->sigma_px/gameIt->sigma_px/gameIt->sigma_px * rd * temp1 / temp2 + 2.0/PI/gameIt->sigma_px/gameIt->sigma_px * temp1 * temp1 / temp2 / temp2 + gsl_matrix_get(A, playerHash[gameIt->white].index, playerHash[gameIt->white].index));
			gsl_matrix_set(A, playerHash[gameIt->black].index, playerHash[gameIt->black].index, sqrt(2.0/PI)/gameIt->sigma_px/gameIt->sigma_px/gameIt->sigma_px * rd * temp1 / temp2 + 2.0/PI/gameIt->sigma_px/gameIt->sigma_px * temp1 * temp1 / temp2 / temp2 + gsl_matrix_get(A, playerHash[gameIt->black].index, playerHash[gameIt->black].index));
		}
		// else black wins
		else {
			double rd = playerHash[gameIt->white].rating - playerHash[gameIt->black].rating - gameIt->handicapeqv;

			double temp1 = exp(-rd*rd/2.0/gameIt->sigma_px/gameIt->sigma_px);
			double temp2 = gsl_sf_erfc(rd/sqrt(2.0)/gameIt->sigma_px);

			gsl_matrix_set(A, playerHash[gameIt->white].index, playerHash[gameIt->black].index, sqrt(2.0/PI)/gameIt->sigma_px/gameIt->sigma_px/gameIt->sigma_px * rd * temp1 / temp2 - 2.0/PI/gameIt->sigma_px/gameIt->sigma_px * temp1 * temp1 / temp2 / temp2 + gsl_matrix_get(A, playerHash[gameIt->white].index, playerHash[gameIt->black].index));
			gsl_matrix_set(A, playerHash[gameIt->black].index, playerHash[gameIt->white].index, sqrt(2.0/PI)/gameIt->sigma_px/gameIt->sigma_px/gameIt->sigma_px * rd * temp1 / temp2 - 2.0/PI/gameIt->sigma_px/gameIt->sigma_px * temp1 * temp1 / temp2 / temp2 + gsl_matrix_get(A, playerHash[gameIt->black].index, playerHash[gameIt->white].index));
			gsl_matrix_set(A, playerHash[gameIt->white].index, playerHash[gameIt->white].index, -sqrt(2.0/PI)/gameIt->sigma_px/gameIt->sigma_px/gameIt->sigma_px * rd * temp1 / temp2 + 2.0/PI/gameIt->sigma_px/gameIt->sigma_px * temp1 * temp1 / temp2 / temp2 + gsl_matrix_get(A, playerHash[gameIt->white].index, playerHash[gameIt->white].index));
			gsl_matrix_set(A, playerHash[gameIt->black].index, playerHash[gameIt->black].index, -sqrt(2.0/PI)/gameIt->sigma_px/gameIt->sigma_px/gameIt->sigma_px * rd * temp1 / temp2 + 2.0/PI/gameIt->sigma_px/gameIt->sigma_px * temp1 * temp1 / temp2 / temp2 + gsl_matrix_get(A, playerHash[gameIt->black].index, playerHash[gameIt->black].index));
		}
	}

	gsl_permutation *p = gsl_permutation_alloc(playerHash.size());
	gsl_linalg_LU_decomp(A, p, &signum);
	gsl_linalg_LU_invert(A, p, B);

	for (map<int, player>::iterator playerIt = playerHash.begin(); playerIt != playerHash.end(); playerIt++) {
		playerIt->second.sigma = sqrt(gsl_matrix_get(B, playerIt->second.index, playerIt->second.index));
	}

	gsl_permutation_free(p);
	gsl_matrix_free(A);
	gsl_matrix_free(B);
}

/****************************************************************

calc_pt () 

Calculate the logarithm of the total likelihood of a particular 
set of ratings

*****************************************************************/
double collection::calc_pt(const gsl_vector *v) {
	map<int, player>::iterator playerIt;
	vector<game>::iterator gameIt;

	double z, rd;
	double pt = 0.0;
	double p;

	for (playerIt=playerHash.begin(); playerIt!=playerHash.end(); playerIt++) {
		playerIt->second.rating = gsl_vector_get(v, playerIt->second.index);
		z = (playerIt->second.rating - playerIt->second.seed)/playerIt->second.sigma;

		pt += -z*z/2 - 0.5 * log(2*PI);
	}

	for (gameIt=gameList.begin(); gameIt!=gameList.end(); gameIt++) {
		if ( (playerHash.find(gameIt->white) == playerHash.end()) || (playerHash.find(gameIt->black) == playerHash.end()) ) {
			cout << "Error: game record involves player with no corresponding entry in player list.  id = " << gameIt->white << ' ' << gameIt->black << endl;
			exit(1);
		}  
		
		rd = playerHash[gameIt->white].rating - playerHash[gameIt->black].rating - gameIt->handicapeqv;

		if (gameIt->whiteWins) {
			p = gsl_sf_log_erfc(-rd/gameIt->sigma_px/sqrt(2.0)) - log(2.0);
		}
		else {
			p = gsl_sf_log_erfc(rd/gameIt->sigma_px/sqrt(2.0)) - log(2.0);
		}
		pt += p;
	}

	return pt;
}

/****************************************************************

calc_pt_df () 

Calculate the gradient of the logarithm of the total likelihood of a particular set of ratings

The likelihood function has a player contribution, which is nominally Gaussian
(linear when a logarithm is taken) and depends only on sigma and the deviation from a player's
seed ratings. There is also a game contribution, which depends on the result and game conditions
of a particular contest 

*****************************************************************/

double collection::calc_pt_df(const gsl_vector *v, gsl_vector *df) {
	map<int, player>::iterator playerIt;
	vector<game>::iterator gameIt;

	double z, rd;
	double dp;
	double temp;

	// Zero out the initial gradient vector
	gsl_vector_set_zero (df);

	// Calculate the player contribution to the likelihood
	for (playerIt=playerHash.begin(); playerIt!=playerHash.end(); playerIt++) {
		playerIt->second.rating = gsl_vector_get(v, playerIt->second.index);
		z = (playerIt->second.rating - playerIt->second.seed)/playerIt->second.sigma;

		gsl_vector_set(df, playerIt->second.index, -z/playerIt->second.sigma);	
	}

	// Calculate the game contribution.
	for (gameIt=gameList.begin(); gameIt!=gameList.end(); gameIt++) {
		// Check if somehow a game got inserted without a corresponding player entry
		if ( (playerHash.find(gameIt->white) == playerHash.end()) || (playerHash.find(gameIt->black) == playerHash.end()) ) {
			cout << "Error: game record involves player with no corresponding entry in player list" << endl;
			exit(1);
		}  
					
		rd = playerHash[gameIt->white].rating - playerHash[gameIt->black].rating - gameIt->handicapeqv;

		// Add in the appropriate contribution
		if (gameIt->whiteWins) {
			dp = 1/gameIt->sigma_px * sqrt(2.0/PI) * exp(-rd*rd/(2.0*gameIt->sigma_px*gameIt->sigma_px)) / gsl_sf_erfc(-rd/(sqrt(2.0)*gameIt->sigma_px));

			temp = gsl_vector_get(df, playerHash[gameIt->white].index);
			gsl_vector_set(df, playerHash[gameIt->white].index, dp + temp);

			temp = gsl_vector_get(df, playerHash[gameIt->black].index);
			gsl_vector_set(df, playerHash[gameIt->black].index, -dp + temp);
		}
		else {
			dp = 1/gameIt->sigma_px * sqrt(2.0/PI) * exp(-rd*rd/(2.0*gameIt->sigma_px*gameIt->sigma_px)) / gsl_sf_erfc(rd/(sqrt(2.0)*gameIt->sigma_px));

			temp = gsl_vector_get(df, playerHash[gameIt->white].index);
			gsl_vector_set(df, playerHash[gameIt->white].index, -dp + temp);

			temp = gsl_vector_get(df, playerHash[gameIt->black].index);			
			gsl_vector_set(df, playerHash[gameIt->black].index, dp + temp);
		}
	}

	return 0;
}

/****************************************************************

calc_ratings () 

Calculate ratings using a multidimensional simplex method.  This 
technique is slower than the conjuagate gradient method, but it
is more reliable.

This function should be slow, but foolproof.  If an error occurs here
the program prints an error message and fails.

*****************************************************************/
int collection::calc_ratings() {
	const gsl_multimin_fminimizer_type *T = gsl_multimin_fminimizer_nmsimplex;
	gsl_multimin_fminimizer *s = NULL;
	gsl_vector *ss, *x;
	gsl_multimin_function minex_func;

	size_t iter = 0;
	int status;
	double size;

	for (vector<game>::iterator gameIt=gameList.begin(); gameIt!=gameList.end(); gameIt++) {
		gameIt->calc_handicapeqv();
	}

	// Close the kyu/dan boundary 
	for (map<int, player>::iterator playerIt=playerHash.begin(); playerIt!=playerHash.end(); playerIt++) {
		if (playerIt->second.seed > 0)
			playerIt->second.seed -= 1.0;
		else
			playerIt->second.seed += 1.0; 
	}

	/* Starting point */
	x = gsl_vector_alloc (playerHash.size());

	for (map<int, player>::iterator playerIt=playerHash.begin(); playerIt!=playerHash.end(); playerIt++) {
		playerIt->second.index = distance(playerHash.begin(), playerIt);
		gsl_vector_set (x, playerIt->second.index, playerIt->second.seed);
	}

	/* Set initial step sizes to 2 */
	ss = gsl_vector_alloc (playerHash.size());
	gsl_vector_set_all (ss, 2);

	/* Initialize method and iterate */
	minex_func.n = playerHash.size();
	minex_func.f = &my_new_f;
	minex_func.params = (void *)this;
	
	s = gsl_multimin_fminimizer_alloc (T, playerHash.size());
	
	gsl_multimin_fminimizer_set (s, &minex_func, x, ss);

	do {
		iter++;
		simplexiterations = iter;
		status = gsl_multimin_fminimizer_iterate(s);

		if (status) 
			break;

		size = gsl_multimin_fminimizer_size (s);
		status = gsl_multimin_test_size (size, 0.00001);

		if (!quiet) {
			cout << "Iteration " << iter << "\tf() = " << s->fval << "\tsimplex size = " << size << endl;
		}
	} while ( (status == GSL_CONTINUE) && ( iter <= 1000000) );


	if (status == GSL_SUCCESS) {
		if (!quiet) {
			cout << endl << "Converged to minimum. f() = " << s->fval << endl;
		}
	}
	else {
		cout << "Error in minimization function f()" << endl;

		// Open the kyu/dan boundary back up
		for (map<int, player>::iterator playerIt=playerHash.begin(); playerIt!=playerHash.end(); playerIt++) {
			if (playerIt->second.rating > 0)
				playerIt->second.rating += 1.0;
			else
				playerIt->second.rating -= 1.0; 
		}		
		
		exit(1);
	}

	for (map<int, player>::iterator playerIt=playerHash.begin(); playerIt!=playerHash.end(); playerIt++) {
		playerIt->second.rating = gsl_vector_get (gsl_multimin_fminimizer_x(s), playerIt->second.index);
	}

	calc_sigma2();

	// Open the kyu/dan boundary back up
	for (map<int, player>::iterator playerIt=playerHash.begin(); playerIt!=playerHash.end(); playerIt++) {
		if (playerIt->second.rating > 0)
			playerIt->second.rating += 1.0;
		else
			playerIt->second.rating -= 1.0; 
	}	
	cout << endl;

	gsl_vector_free(x);
	gsl_vector_free(ss);
	gsl_multimin_fminimizer_free(s);

	return status;
}

/****************************************************************

calc_ratings_fdf () 

Calculate ratings using a conjugate gradient method.  Technique fails if the initial guess
happens to be exactly correct, which makes 'easy' test cases a little more difficult.

*****************************************************************/

int collection::calc_ratings_fdf() {
	int status, iter=0;
	const gsl_multimin_fdfminimizer_type *T = gsl_multimin_fdfminimizer_vector_bfgs2;	
	gsl_multimin_fdfminimizer *s;
	gsl_vector *x;
	gsl_multimin_function_fdf minex_func;
	
	// Calculate equivalent handicaps for all the games in the current ratings.
	// This alters the effective rating difference based on the game handicap and komi.
	for (vector<game>::iterator gameIt=gameList.begin(); gameIt!=gameList.end(); gameIt++) {
		gameIt->calc_handicapeqv();
	}
	
	// Close the kyu/dan boundary 
	for (map<int, player>::iterator playerIt=playerHash.begin(); playerIt!=playerHash.end(); playerIt++) {
		if (playerIt->second.seed > 0)
			playerIt->second.seed -= 1.0;
		else
			playerIt->second.seed += 1.0; 
	}		

	// Storage vector for player ratings	
	x = gsl_vector_alloc (playerHash.size());
	
	// Populate the storage vector
	// This function crashes if we happen to seed players at a point where the gradient is
	// identically zero.  This sounds improbable, but two new players entering the rating system
	// at the same rank and who break even in a match against each other will trigger this case.
	// Accordingly, we add a small random offset to each initial guess to take it away from the
	// potential minimum point.
	for (map<int, player>::iterator playerIt=playerHash.begin(); playerIt!=playerHash.end(); playerIt++) {
		playerIt->second.index = distance(playerHash.begin(), playerIt);
		gsl_vector_set (x, playerIt->second.index, playerIt->second.seed + gsl_ran_flat(r, 0, 0.1));
	}

	minex_func.n      = playerHash.size();
	minex_func.f      = &my_new_f;
	minex_func.df     = &my_new_df;
	minex_func.fdf    = &my_new_fdf;
	minex_func.params = (void *)this;
	
	s = gsl_multimin_fdfminimizer_alloc (T, playerHash.size());
	gsl_multimin_fdfminimizer_set(s, &minex_func, x, 2, 0.1);
	
	// Main loop.  Continue iterating until the likelihood function hits an extreme, or
	// until an error occurs.  
	do {
		iter++;	
		fdfiterations = iter;
		status = gsl_multimin_fdfminimizer_iterate(s);

		if (status) {
			break;
		}
		
		status = gsl_multimin_test_gradient (s->gradient, 0.001);
		
		if (!quiet) {
			cout << "Finished iteration " << iter << "\tf() = " << gsl_multimin_fdfminimizer_minimum(s) << "\tnorm = " << gsl_blas_dnrm2(gsl_multimin_fdfminimizer_gradient(s)) << "\tStatus = " << status << endl;
		}
	} while ((status == GSL_CONTINUE) && (iter < 10000));

	if (status == GSL_SUCCESS) {
		if (!quiet) {
			cout << endl << "Converged to minimum. "; 	
			cout << "Norm(gradient) = " << gsl_blas_dnrm2(gsl_multimin_fdfminimizer_gradient(s)) << endl;
		}
	}
	else {
		// Can hit an error by accident if the initial guess on player ratings happens to be exactly right.
		// In that case, the gradient vector vanishes and the suggested update doesn't pass the tolerance
		// threshold.
		cout << "Error in minimization function fdf()" << endl;
		cout << "status = " << status << endl;

		// Open the kyu/dan boundary back up
		for (map<int, player>::iterator playerIt=playerHash.begin(); playerIt!=playerHash.end(); playerIt++) {
			if (playerIt->second.rating > 0)
				playerIt->second.rating += 1.0;
			else
				playerIt->second.rating -= 1.0; 
		}
			
		return(1);
	}

	// Update new ratings
	for (map<int, player>::iterator playerIt=playerHash.begin(); playerIt!=playerHash.end(); playerIt++) {
		playerIt->second.rating = gsl_vector_get (gsl_multimin_fdfminimizer_x(s), playerIt->second.index);
	}

	// Calculate new sigmas
	calc_sigma2();

	// Open the kyu/dan boundary back up
	for (map<int, player>::iterator playerIt=playerHash.begin(); playerIt!=playerHash.end(); playerIt++) {
		if (playerIt->second.rating > 0)
			playerIt->second.rating += 1.0;
		else
			playerIt->second.rating -= 1.0; 
	}			

	gsl_vector_free(x);
	gsl_multimin_fdfminimizer_free (s);

	return 0;	
}

/****************************************************************

initSeeding () 

// Given players playing in a tournament, games in the tournament and the TDList data
// prior to a tournament, set each player's seed rating and sigma and calculate
// the handicap equivalent and sigma_px for each game.  

*****************************************************************/
void collection::initSeeding(map<int, tdListEntry> &tdList) {
	map<int, int> winCount;
	double deltaR;
	
	for (map<int, player>::iterator It = playerHash.begin(); It != playerHash.end(); It++) {
		winCount[It->second.id] = 0;
	}
	for (vector<game>::iterator gameIt = gameList.begin(); gameIt != gameList.end(); gameIt++) {
		if (gameIt->whiteWins)
			winCount[gameIt->white]++;
		else
			winCount[gameIt->black]++;
	}

	// Loop through each player who played a game in the tournament	
	for (map<int, player>::iterator It = playerHash.begin(); It != playerHash.end(); It++) {

		// Do we have a previous record for them in the TDList?
		map<int, tdListEntry>::iterator tdListIt = tdList.find(It->second.id);

		if (tdListIt == tdList.end()) {
			// No we don't.  
			// Player is seeded at the rating they entered the tournament at
			// Sigma is set according to their seed rating
			It->second.sigma = It->second.calc_init_sigma(It->second.seed);	
		}
		// Perhaps we have a legacy entry in the TDList with no actual rating.  
		// If so, treat as a reseeding
		else if (tdListIt->second.rating == 0) {
			It->second.sigma = It->second.calc_init_sigma(It->second.seed);
		}
		// Perhaps we have a legacy entry in the TDList with no sigma
		// If so, treat as a reseeding
		else if (tdListIt->second.sigma == 0) {
			It->second.sigma = It->second.calc_init_sigma(It->second.seed);
		}	
		// We must have a record for them in the TDList?  If so then compute a new sigma
		// a possibly a new seed
		else {
			if (It->second.seed * tdListIt->second.rating > 0)			
				deltaR = It->second.seed - tdListIt->second.rating;
			else
				deltaR = It->second.seed - tdListIt->second.rating - 2;
			
			// We don't let players demote themselves
			if (deltaR < 0) {
				It->second.seed = tdListIt->second.rating;
				int dayCount = boost::gregorian::date_period(tdListIt->second.lastRatingDate, tournamentDate).length().days();	
				It->second.sigma = sqrt(tdListIt->second.sigma * tdListIt->second.sigma + 0.0005 * 0.0005 * dayCount * dayCount);	
			}						
			// Is this a self promotion by more than three stones?
			// If so, treat as a reseeding.  Players must win at least one game
			// to trigger the self-promotion case.  Otherwise they are just seeded
			// at their old rating.			
			else if ( (deltaR >= 3.0) && (winCount[It->second.id] > 0) ) {
				It->second.seed  = It->second.seed;
				It->second.sigma = It->second.calc_init_sigma(It->second.seed);
			}
			// Is it a smaller self promotion?
			else if ( (deltaR >= 1.0) && (winCount[It->second.id] > 0) ) {
				It->second.seed = tdListIt->second.rating + 0.024746 + 0.32127 * deltaR;
				It->second.sigma = sqrt(tdListIt->second.sigma * tdListIt->second.sigma + 0.256 * pow(deltaR, 1.9475)); 
			}
			else {
				It->second.seed  = tdListIt->second.rating;
				int dayCount = boost::gregorian::date_period(tdListIt->second.lastRatingDate, tournamentDate).length().days();
				It->second.sigma = sqrt(tdListIt->second.sigma * tdListIt->second.sigma + 0.0005 * 0.0005 * dayCount * dayCount);	
			}
		}
//		cout << "Seed: " << It->second.id << '\t' << It->second.seed << '\t' << It->second.sigma << endl;
//		cout << "TD List: " << tdListIt->second.id << '\t' << tdListIt->second.rating << '\t' << tdListIt->second.sigma << endl;
//		cout << endl;
	}
	
	// Assign individual handicap equivalents and sigma_px parameters to each game.
	for (vector<game>::iterator gameIt=gameList.begin(); gameIt!=gameList.end(); gameIt++) {
		gameIt->calc_handicapeqv();
	}
}

/****************************************************************

findImprobables () 

Identify games that are highly improbable (<1% chance of occuring)
Improbables usually indicates a data entry error or a player who h
as improved dramatically since their last rating who needs to be reseeded. 

*****************************************************************/
void collection::findImprobables(map<int, tdListEntry> &tdList) {
	double p, rd;
	
	for (vector<game>::iterator gameIt=gameList.begin(); gameIt!=gameList.end(); gameIt++) {
		gameIt->calc_handicapeqv();
		
		rd = (playerHash[gameIt->white].seed > 0 ? playerHash[gameIt->white].seed-1 : playerHash[gameIt->white].seed+1)
			 - (playerHash[gameIt->black].seed > 0 ? playerHash[gameIt->black].seed-1 : playerHash[gameIt->black].seed+1) 
			 - gameIt->handicapeqv;

		if (gameIt->whiteWins) {
			p = gsl_sf_erfc(-rd/gameIt->sigma_px/sqrt(2.0))/2.0;
		}
		else {
			p = gsl_sf_erfc(rd/gameIt->sigma_px/sqrt(2.0))/2.0;
		}
		
		if (p<0.01) {
			cout << "\tWhite: " << tdList[gameIt->white].name << " (" << gameIt->white << "), Rating = " << playerHash[gameIt->white].seed << endl;
			cout << "\tBlack: " << tdList[gameIt->black].name << " (" << gameIt->black << "), Rating = " << playerHash[gameIt->black].seed << endl;
			cout << "\tH/K: " << gameIt->handicap << "/" << gameIt->komi << endl;
			cout << "\tResult: " << (gameIt->whiteWins ? "White wins" : "Black wins") << endl;
			cout << "\tProb: " << p << endl;
			
			cout << endl;
		}
	}
}
