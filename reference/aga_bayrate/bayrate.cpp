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

	for (int i=1; i<argc; i++) 
		argList[string(argv[i])] = true;

 	// Establish the database connection			
	if ( !db.makeConnection() ) {	
		std::cerr << "Fatal error:  db.makeConnection() failed." << std::endl;
		exit (1);
	}

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
		cout << "Updating all tournaments after " << to_iso_extended_string(tournamentCascadeDate) << endl;
	}
	
	// Get the TDList immediately prior to the earliest unrated game
	if (!db.getTDList(tournamentCascadeDate, tdList)) {
		std::cerr << "Fatal error: db.getTDList() failed." << std::endl;
		exit(1);
	}
	else {
		cout << "Downloaded TDList" << endl;
	}
	
	for (vector<string>::iterator It=tournamentUpdateList.begin(); It!=tournamentUpdateList.end(); It++) {
		cout << "Processing " << *It << endl;
		
		c.reset();	
		db.getTournamentInfo(*It, c);

		if (c.gameList.size() == 0)
			continue;
		
		c.initSeeding(tdList);
		
		// Start with the fast rating algorithm.  If it fails, then go for the simplex method as a backup. 
		if (c.calc_ratings_fdf() != 0) {
			if (c.calc_ratings() != 0) {
				cerr << "Fatal error processing tournament " << *It << endl;
				exit(1); 
			}	
		}
		
		// Copy the new ratings into the internal TDList for the next tournament update
		for (map<int, player>::iterator It = c.playerHash.begin(); It != c.playerHash.end(); It++) {
			tdList[It->second.id].id     = It->second.id;			
			tdList[It->second.id].rating = It->second.rating;
			tdList[It->second.id].sigma  = It->second.sigma;
			tdList[It->second.id].lastRatingDate = c.tournamentDate;
			tdList[It->second.id].ratingUpdated = true;
		
			cout << It->second.id << '\t' << It->second.rating << '\t' << It->second.sigma << endl;
		}				
	    cout << endl;
	    
		// Update database
		if (argList.find(string("--commit")) != argList.end()) {
			cout << "Committing results to database...";		
			db.syncNewRatings(c);		
			cout << "done." << endl;
		}
	}
	cout << "Done ratings" << endl;
	
	for (map<int, tdListEntry>::iterator tdListIt = tdList.begin(); tdListIt != tdList.end(); tdListIt++) {
		if (tdListIt->second.ratingUpdated)
			cout << tdListIt->second.id << '\t' << tdListIt->second.rating << '\t' << tdListIt->second.sigma << endl;
	}
}
