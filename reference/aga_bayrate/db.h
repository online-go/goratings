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

		void excludeBogusGameData();
		bool makeConnection();
		bool getMostRecentRatedGameDate(boost::gregorian::date &tournamentCascadeDate);
		bool getPlayerList (boost::gregorian::date &tournamentCascadeDate, 
			map<int, tdListEntry> &tdList, bool verbose_getTDList);
		bool getTDListAsOfDate (boost::gregorian::date &tournamentCascadeDate, 
			map<int, tdListEntry> &tdList, bool verbose_getTDList);
		bool getTDListCurrent (map<int, tdListEntry> &tdList, bool verbose_getTDList);
		bool getTDListPrior (boost::gregorian::date &tournamentCascadeDate, 
			map<int, tdListEntry> &tdList, bool verbose_getTDList);
		bool getTournamentInfo (string &tournamentCode, collection &c);
		bool getTournamentUpdateList (vector<string> &tournamentUpdateList, 
			boost::gregorian::date &tournamentCascadeDate);
		void syncDBs (map<int, tdListEntry> &tdList, bool commit);
		void syncNewRatings(collection &c, bool commit); 
		
		void onlyOne (bool b);
		void showAGAGD (bool b);
		void showMembersDB (bool b);
		void showRatingsDB (bool b);
		void showTournamentList (bool b);
		void syncShowAllRatedPlayers (bool b);

	private:		
		mysqlpp::Connection db;
		mysqlpp::Connection ratingsdb;
		mysqlpp::Connection membersdb;
		
		bool onlyone;
		bool showagagd;
		bool showmembersdb;
		bool showallratedplayers;
		bool showratingsdb;
		bool showtournamentlist;

		bool getTDList (boost::gregorian::date &tournamentCascadeDate, 
			map<int, tdListEntry> &tdList, mysqlpp::Query &query, bool verbose_getTDList);
		bool updateAGAGD(collection &c, map<int, player>::iterator &playerIt, bool commit);
		bool updateMembers(collection &c, map<int, player>::iterator &playerIt, bool commit);
		bool updateRatings(collection &c, map<int, player>::iterator &playerIt, bool commit);
};
