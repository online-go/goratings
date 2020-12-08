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
    along with Foobar.  If not, see <http://www.gnu.org/licenses/>.
    
***************************************************************************************/

#pragma once
#include <string>
#include <vector>
#include <map>
#include <gsl/gsl_math.h>
#include <gsl/gsl_multimin.h>
#include <gsl/gsl_chebyshev.h>
#include <gsl/gsl_rng.h>
#include <gsl/gsl_randist.h>
#include <boost/date_time/gregorian/gregorian.hpp>
#include "player.h"
#include "game.h"
#include "tdListEntry.h"

using namespace std;

class collection
{
public:
	collection(void);
	~collection(void);
	string tournamentCode;
	map<int, player> playerHash;
	vector<game> gameList;
	std::string tournamentName;
	boost::gregorian::date tournamentDate;
	
	double calc_pt(const gsl_vector *v);
	double calc_pt_df(const gsl_vector *x, gsl_vector *df);
	void calc_sigma();
	void calc_sigma2();	
	int calc_ratings();
	int calc_ratings_fdf();

	void reset();
	void initSeeding(map<int, tdListEntry> &tdList);
	void findImprobables(map<int, tdListEntry> &tdList);
	void setQuiet(bool q);
	int  getFdfIterations();
	int  getSimplexIterations();
	
private:
	double PI;
	const gsl_rng_type *T;
	gsl_rng *r;
	bool quiet;
	int  fdfiterations;
	int  simplexiterations;
};
