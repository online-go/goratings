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
#include <string>
#include <vector>
#include <algorithm>
#include <mysql++/mysql++.h>
#include <boost/date_time/gregorian/gregorian.hpp>
#include "db.h"
#include "tdListEntry.h"
#include "collection.h"

using namespace std;
using namespace boost::gregorian;

int main(int argc, char *argv[])
{
	
 	databaseConnection db;
 	vector<string> tournamentUpdateList;	// The list of tournaments after the tournamentCascadeDate
	boost::gregorian::date tournamentCascadeDate;		
 	map<int, tdListEntry> tdList;
 	map<string, bool> argList;
 	collection c;
	bool commit = false;
	bool onlyone = false;
	bool showplayerhash = false;
	bool verbose_getTDList = false;

	for (int i=1; i<argc; i++) 
		argList[string(argv[i])] = true;

	if (argList.find(string("--commit")) != argList.end())
		commit = true;

	if (argList.find(string("--getTDList")) != argList.end())
		verbose_getTDList = true;

	if (argList.find(string("--onlyOne")) != argList.end())
		onlyone = true;

 	// Establish the database connection			
	if ( !db.makeConnection() ) {	
		std::cerr << "Fatal error:  db.makeConnection() failed." << std::endl;
		exit (1);
	}

	db.onlyOne(onlyone);
	db.showAGAGD (false);
	db.showRatingsDB (false);
	db.showMembersDB (false);
	db.excludeBogusGameData();

	// Figure out which tournaments need rating
	if ( !db.getTournamentUpdateList(tournamentUpdateList, tournamentCascadeDate) ) {
		std::cerr << "Fatal error: db.getTournamentUpdateList() failed." << std::endl;
		exit(1);
	}
	
	if (tournamentUpdateList.size() == 0) {
		cout << "No tournaments to update." << endl;
		exit(1);
	}	
	else {
		if (not onlyone)
			cout << "Updating all tournaments after " << to_iso_extended_string(tournamentCascadeDate) << endl;
		else 
			cout << "Updating one tournament only " << to_iso_extended_string(tournamentCascadeDate) << endl;
			
	}
	if (onlyone)
		tournamentUpdateList.erase(tournamentUpdateList.begin()+1, tournamentUpdateList.end());
	
	// Get the TDList immediately prior to the earliest unrated game
	if (!db.getTDListPrior(tournamentCascadeDate, tdList, verbose_getTDList)) {
		std::cerr << "Fatal error: db.getTDList() failed." << std::endl;
		exit(1);
	}
	else {
		cout << "Downloaded TDList" << endl;
	}
	
	for (vector<string>::iterator It=tournamentUpdateList.begin(); It!=tournamentUpdateList.end(); It++) {
		
		c.reset();	
		c.setQuiet(true);

		db.getTournamentInfo(*It, c);

		cout << ": Processing " << *It << "...";

		if (c.gameList.size() == 0) {
			cout << "no games...skipping." << endl;
			continue;
		}
		
		c.initSeeding(tdList);
		cout << "initSeeding() complete..." << endl;

		// Start with the fast rating algorithm.  If it fails, then go for the simplex method as a backup. 
		if (c.calc_ratings_fdf() != 0) {
			if (c.calc_ratings() != 0) {
				cerr << "Fatal error processing tournament " << *It << endl;
				exit(1); 
			}	
		}
		cout << "\tcalc_ratings_fdf() complete using " << c.getFdfIterations() << " fdf iterations and "
			<< c.getSimplexIterations() << " simplex iterations..." << endl;
		
		// Overwrite the previous ratings with the new ratings in the internal 
		// TDList to prepare for the next tournament update
		for (map<int, player>::iterator It = c.playerHash.begin(); It != c.playerHash.end(); It++) {
			tdList[It->second.id].id             = It->second.id;

			if (fabs(tdList[It->second.id].rating) < 1.0) {
				tdList[It->second.id].rating_ante = 0.0;
			}
			else {
				tdList[It->second.id].rating_ante    = tdList[It->second.id].rating;
			}

			if (fabs(tdList[It->second.id].sigma) < 0.0000001) {
				tdList[It->second.id].sigma_ante    = 0.0;
			}
			else {
				tdList[It->second.id].sigma_ante     = tdList[It->second.id].sigma;
			}

			tdList[It->second.id].rating         = It->second.rating;
			tdList[It->second.id].sigma          = It->second.sigma;
			tdList[It->second.id].lastRatingDate = c.tournamentDate;
			tdList[It->second.id].tournaments    += " ";
			tdList[It->second.id].tournaments    += c.tournamentCode;
			tdList[It->second.id].ratingUpdated  = true;
		
			if (showplayerhash) {
				cout << It->second.id << '\t' << It->second.rating << ' ' << It->second.sigma <<  '\t' 
					<< tdList[It->second.id].rating_ante << ' ' << tdList[It->second.id].sigma_ante 
					<< '\t' << tdList[It->second.id].name << endl;
			}
		}
	    
		// Update database
		if (commit) {
			cout << "Committing results to database..." << endl;
			db.syncNewRatings(c, commit);		
			cout << "syncNewRatings() complete..." << endl;
		}
		else {
			db.syncNewRatings(c, false);		
		}

		cout << "done." << endl;
		cout << endl;
	}

	cout << "Done ratings" << endl;
	
	cout << setw(6) << "AGA ID" << ' ' 
		<< setw(10) << "New Rating" << ' ' 
		<< setw(9)  << "New Sigma" << "  ::  "
		<< setw(10) << "old rating" << ' ' 
		<< setw(9)  << "old sigma" << ' '
		<< setw(20) << "Player Name" << ' ' 
		<< setw(18)   << "Tournament Code" << endl;

	for (map<int, tdListEntry>::iterator tdListIt = tdList.begin(); tdListIt != tdList.end(); tdListIt++) {

		if (tdListIt->second.ratingUpdated) {
			cout << setw(6) << tdListIt->second.id << ' ' 
				<< setw(10) << tdListIt->second.rating << ' ' 
				<< setw(9)  << tdListIt->second.sigma << "  ::  "
				<< setw(10) << tdListIt->second.rating_ante << ' ' 
				<< setw(9)  << tdListIt->second.sigma_ante << ' '
				<< setw(20) << tdListIt->second.name << ' ' 
				<< setw(18) << tdListIt->second.tournaments << endl;
		}
	}
}
