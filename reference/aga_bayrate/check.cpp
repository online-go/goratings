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
	bool verbose_getTDList = false;

	for (int i=1; i<argc; i++) 
		argList[string(argv[i])] = true;

	if (argList.find(string("--getTDList")) != argList.end())
		verbose_getTDList = true;

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
		cout << "No tournaments to update" << endl;
		exit(1);
	}	
	else {
		cout << "Updating all tournaments after " << to_iso_extended_string(tournamentCascadeDate) << endl;
	}
	
	// Get the TDList immediately prior to the earliest unrated game
	if (!db.getTDListPrior(tournamentCascadeDate, tdList, verbose_getTDList)) {
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
		
		c.findImprobables(tdList);
		cout << endl;		
	}
}
