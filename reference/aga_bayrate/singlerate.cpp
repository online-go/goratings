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
 	map<int, tdListEntry> tdList;
 	map<string, bool> argList;
 	string tournamentCode;
 	collection c;

	if (argc != 2) {
		cout << "Usage: singlerate <tournamentCode>" << endl;
		exit(1);
	}
	else {
		tournamentCode = argv[1];
	}

 	// Establish the database connection			
	if ( !db.makeConnection() ) {	
		std::cerr << "Fatal error:  db.makeConnection() failed." << std::endl;
		exit (1);
	}

	db.excludeBogusGameData();

	// Get tournament info, player and game lists
	db.getTournamentInfo(tournamentCode, c);

	// Get the TDList immediately prior to the earliest unrated game
	if (!db.getTDList(c.tournamentDate, tdList)) {
		std::cerr << "Fatal error: db.getTDList() failed." << std::endl;
		exit(1);
	}
	else {
		cout << "Downloaded TDList" << endl << endl;
	}
	
	if (c.gameList.size() == 0) {
		cout << "No games to rate" << endl;
		
	}
		
	c.initSeeding(tdList);
	
	// Start with the fast rating algorithm.  If it fails, then go for the simplex method as a backup. 
	if (c.calc_ratings_fdf() != 0) {
		if (c.calc_ratings() != 0) {
			cerr << "Fatal error processing tournament " << argv[1] << endl;
			exit(1); 
		}	
	}
	
	cout << endl << "New ratings:" << endl;
	cout << setw(5) << "ID" << setw(10) << "Rating" << setw(10) << "Sigma" << endl;
	
	// Copy the new ratings into the internal TDList for the next tournament update
	for (map<int, player>::iterator It = c.playerHash.begin(); It != c.playerHash.end(); It++) {
		tdList[It->second.id].id     = It->second.id;			
		tdList[It->second.id].rating = It->second.rating;
		tdList[It->second.id].sigma  = It->second.sigma;
		tdList[It->second.id].lastRatingDate = c.tournamentDate;
		tdList[It->second.id].ratingUpdated = true;
		
		cout << setw(5) << It->second.id << setw(10) << It->second.rating << setw(10) << It->second.sigma << endl;
	}				
	cout << endl;
}
