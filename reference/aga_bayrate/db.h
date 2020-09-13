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

#pragma once

#include <vector>
#include <map>
#include <string>
#include <mysql++/mysql++.h>
#include <boost/date_time/gregorian/gregorian.hpp>
#include "tdListEntry.h"
#include "collection.h"

using namespace std;

class databaseConnection {
	public:
		databaseConnection();
		~databaseConnection();
		bool makeConnection();
		bool getTournamentUpdateList(vector<string> &tournamentUpdateList, boost::gregorian::date &tournamentCascadeDate);
		bool getTDList (boost::gregorian::date &tournamentCascadeDate, map<int, tdListEntry> &tdList);
		bool getTournamentInfo (string &tournamentCode, collection &c);
		void excludeBogusGameData();
		void syncNewRatings(collection &c); 
		
	private:		
		mysqlpp::Connection db;

};
