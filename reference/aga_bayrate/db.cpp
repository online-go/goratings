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

#include <vector>
#include <string>
#include <map>
#include <iostream>
#include <sstream>
#include <assert.h>
#include <mysql++/mysql++.h>
#include <ctime>
#include <boost/date_time/gregorian/gregorian.hpp>
#include "db.h"
#include "db_passwords.h"
#include "collection.h"
#include "player.h"
#include "game.h"

using namespace std;
//using namespace boost::gregorian;

databaseConnection::databaseConnection() {
	onlyone = false;
	showagagd = false;
	showallratedplayers = false;
	showmembersdb = false;
	showratingsdb = false;
	showtournamentlist = false;
}

databaseConnection::~databaseConnection() {
	db.disconnect();
	ratingsdb.disconnect();
	membersdb.disconnect();
}

void databaseConnection::onlyOne (bool b) {
	onlyone = b;
}
void databaseConnection::showAGAGD (bool b) {
	showagagd = b;
}
void databaseConnection::syncShowAllRatedPlayers (bool b) {
	showallratedplayers = b;
}
void databaseConnection::showMembersDB (bool b) {
	showmembersdb = b;
}
void databaseConnection::showRatingsDB (bool b) {
	showratingsdb = b;
}
void databaseConnection::showTournamentList (bool b) {
	showtournamentlist = b;
}

/****************************************************************

makeConnection () 

Establish a connection to the ratings server(s).

*****************************************************************/
bool databaseConnection::makeConnection() {
	db = mysqlpp::Connection(false);

//	return db.connect("database", "host", "user", "password") &&
//			ratingsdb.connect("database", "host", "user", "password");

	return db.connect(usgo_agagd_database, usgo_agagd_server, usgo_agagd_user, usgo_agagd_password) 
		&& ratingsdb.connect(ratings_database, ratings_server, ratings_user, ratings_password)
		&& membersdb.connect(members_database, members_server, members_user, members_password);

//	return db.connect("usgo_agagd", "localhost", "root", "Burcan**") && ratingsdb.connect("usgo", "localhost", "root", "Burcan**");
}

// Set exclude flags on any games for which player rank data is bogus
// Bogus ranks are anything that isn't a kyu/dan indicator
// Blank ranks will be dealt with later
void databaseConnection::excludeBogusGameData() {
	mysqlpp::Query query(&db, false);

	query.exec("UPDATE games SET exclude = 1 WHERE NOT (rank_1 LIKE '%k%' OR rank_1 LIKE '%K%' OR rank_1 LIKE '%d%' OR rank_1 LIKE '%D%')");
	query.exec("UPDATE games SET exclude = 1 WHERE NOT (rank_2 LIKE '%k%' OR rank_2 LIKE '%K%' OR rank_2 LIKE '%d%' OR rank_2 LIKE '%D%')");
	query.exec("UPDATE games SET exclude = 1 WHERE (rank_1 = '0k' OR rank_1 = '0K' OR rank_1 = '0d' OR rank_1 = '0D')");
	query.exec("UPDATE games SET exclude = 1 WHERE (rank_2 = '0k' OR rank_2 = '0K' OR rank_2 = '0d' OR rank_2 = '0D')");
	query.exec("UPDATE games SET exclude = 1 WHERE handicap>9");
	query.exec("UPDATE games SET exclude = 1 WHERE handicap>=2 and komi>=10");
	query.exec("UPDATE games SET exclude = 1 WHERE handicap>=2 and komi<=-10");
	query.exec("UPDATE games SET exclude = 1 WHERE (handicap=0 or handicap=1) and komi<=-20");
	query.exec("UPDATE games SET exclude = 1 WHERE (handicap=0 or handicap=1) and komi<=-20");
	query.exec("UPDATE games SET exclude = 1 WHERE (game_date < '1900-01-01')");
	query.exec("UPDATE games SET exclude = 1 WHERE pin_player_1 = 0 or pin_player_2 = 0");
}

/****************************************************************

bool databaseConnection::getMostRecentRatedGameDate(boost::gregorian::date &tournamentCascadeDate)

****************************************************************/
bool databaseConnection::getMostRecentRatedGameDate(boost::gregorian::date &tournamentCascadeDate) {
	mysqlpp::Query query = db.query("SELECT MAX(Game_Date) AS date FROM games WHERE Rated = 1");

	cout << query.str() << endl;
	cout << endl;

	mysqlpp::StoreQueryResult res = query.store();

	if (!res)
		return false;

	mysqlpp::Date tempDate = res[0]["date"];

	// Check if the response was NULL.  The date gets converted to 0000-00-00 if it is.
	if (tempDate == mysqlpp::Date("0000-00-00"))	{
		return true;
	}
	tournamentCascadeDate = boost::gregorian::date(boost::gregorian::from_simple_string(tempDate.str()));

	return true;
}

/****************************************************************

bool databaseConnection::getTournamentUpdateList (vector<string> &tournamentUpdateList, date &tournamentCascadeDate) 

Get the list of tournaments that need (re)rating.  List of 
tournament codes is placed in parameter TournamentUpdateList.
Date of first tournament that need rerating placed in parameter 
tournamentCascadeDate.

Returns true if the operation was successful

*****************************************************************/
bool databaseConnection::getTournamentUpdateList(vector<string> &tournamentUpdateList, boost::gregorian::date &tournamentCascadeDate) {
	mysqlpp::Query query = db.query("SELECT MIN(Game_Date) AS date FROM games WHERE Game_Date > '1950-01-01' AND NOT (Online OR Exclude OR Rated)");

	if (showtournamentlist) {
		cout << "getTournamentUpdateList: AGAGD: " << query.str() << endl;
		cout << endl;
	}

	mysqlpp::StoreQueryResult res = query.store();

	if (!res)
		return false;

	mysqlpp::Date tempDate = res[0]["date"];

	// Check if the response was NULL.  The date gets converted to 0000-00-00 if it is.
	if (tempDate == mysqlpp::Date("0000-00-00"))	{
		return true;
	}
	tournamentCascadeDate = boost::gregorian::date(boost::gregorian::from_simple_string(tempDate.str()));

	mysqlpp::Query query2 = db.query("SELECT DISTINCT t.Tournament_Code, t.Tournament_Date FROM tournaments t, games g WHERE t.Tournament_Date >= %0q AND t.Tournament_Code = g.Tournament_Code AND NOT (g.Online OR g.Exclude) ORDER BY Tournament_Date");

	if (showtournamentlist) {
		cout << "getTournamentUpdateList: AGAGD: " << query2.str(tempDate) << endl;
		cout << endl;
	}

	query2.parse();	
	res = query2.store(tempDate);

	for (size_t i=0; i<res.num_rows(); i++) {
		tournamentUpdateList.push_back(static_cast<string>(res[i]["Tournament_Code"]));
		if (showtournamentlist)
			cout << res[i]["Tournament_Code"] << endl;
	}
	cout << endl;
  
	return true;	 
}


/****************************************************************

bool getTDList () 

Gets the last valid TDList prior to the date given by parameter 
tournamentCascadeDate.  Data placed into map parameter TdList.

USES "ratings" table

Returns true if the operation is successful 

*****************************************************************/
bool databaseConnection::getTDList(boost::gregorian::date &tournamentCascadeDate, map<int, tdListEntry> &tdList, mysqlpp::Query &query, bool verbose_getTDList) {
	tdListEntry entry;	
	
	if (verbose_getTDList) {
		cout << "databaseConnection::getTDList: " << query.str() << endl;
		cout << endl;
	}
	query.parse();

	mysqlpp::StoreQueryResult res = query.store(mysqlpp::Date(boost::gregorian::to_iso_extended_string(tournamentCascadeDate)));

	for (size_t i=0; i<res.num_rows(); ++i) {
		entry.id             = res[i]["pin_player"];
		entry.rating         = res[i]["rating"];
		entry.rating_ante    = res[i]["rating"];
		entry.sigma          = res[i]["sigma"];
		entry.sigma_ante     = res[i]["sigma"];
		entry.name           = string(res[i]["name"]);

		mysqlpp::Date tempDate = res[i]["elab_date"];
		if (tempDate == mysqlpp::Date("0000-00-00")) {
			entry.lastRatingDate = boost::gregorian::date(1900, 1, 1);
		}
		else {
			entry.lastRatingDate = boost::gregorian::date(boost::gregorian::from_simple_string(tempDate.str()));
		}
		entry.ratingUpdated  = false;
		
		tdList[entry.id] = entry;
		
		if (verbose_getTDList) 
			cout << res.num_rows() << ':' << i+1 << '\t' << entry.id << '\t' << entry.rating << '\t' 
				<< entry.sigma << '\t' << entry.name << endl;
	}
 		
	return true;
}

/****************************************************************

bool getTDListAsOfDate () 

Gets the TDList as of the date given by parameter tournamentCascadeDate.  
Data placed into map parameter TdList.

Returns true if the operation is successful 

*****************************************************************/
bool databaseConnection::getTDListAsOfDate(boost::gregorian::date &tournamentCascadeDate, map<int, tdListEntry> &tdList, bool verbose_getTDList) {
	tdListEntry entry;	
	
	mysqlpp::Query query = db.query("SELECT CONCAT(players.name, ' ', players.last_name) AS name, x.pin_player, x.rating, x.sigma, x.elab_date FROM ratings x, players, (SELECT MAX(elab_date) AS maxdate, pin_player FROM ratings WHERE elab_date <= %0q GROUP BY pin_player) AS maxresults WHERE x.pin_player = maxresults.pin_player AND x.elab_date = maxresults.maxdate AND x.pin_player = players.pin_player AND x.pin_player != 0");

	return databaseConnection::getTDList(tournamentCascadeDate, tdList, query, verbose_getTDList);
}

/****************************************************************

bool getTDListCurrent () 

Gets the current TDList.  Data placed into map parameter TdList.

Returns true if the operation is successful 

*****************************************************************/
bool databaseConnection::getTDListCurrent(map<int, tdListEntry> &tdList, bool verbose_getTDList) {
	boost::gregorian::date tournamentCascadeDate = boost::gregorian::date(boost::gregorian::max_date_time);
	tdListEntry entry;	
	
	mysqlpp::Query query = db.query("SELECT CONCAT(players.name, ' ', players.last_name) AS name, x.pin_player, x.rating, x.sigma, x.elab_date FROM ratings x, players, (SELECT MAX(elab_date) AS maxdate, pin_player FROM ratings WHERE elab_date <= %0q GROUP BY pin_player) AS maxresults WHERE x.pin_player = maxresults.pin_player AND x.elab_date = maxresults.maxdate AND x.pin_player = players.pin_player AND x.pin_player != 0");

	return databaseConnection::getTDList(tournamentCascadeDate, tdList, query, verbose_getTDList);
}

/****************************************************************

bool getTDListPrior () 

Gets the last valid TDList PRIOR to the date given by parameter 
tournamentCascadeDate.  Data placed into map parameter TdList.

Returns true if the operation is successful 

*****************************************************************/
bool databaseConnection::getTDListPrior(boost::gregorian::date &tournamentCascadeDate, map<int, tdListEntry> &tdList, bool verbose_getTDList) {
	tdListEntry entry;	
	
	mysqlpp::Query query = db.query("SELECT CONCAT(players.name, ' ', players.last_name) AS name, x.pin_player, x.rating, x.sigma, x.elab_date FROM ratings x, players, (SELECT MAX(elab_date) AS maxdate, pin_player FROM ratings WHERE elab_date < %0q GROUP BY pin_player) AS maxresults WHERE x.pin_player = maxresults.pin_player AND x.elab_date = maxresults.maxdate AND x.pin_player = players.pin_player AND x.pin_player != 0");

	return databaseConnection::getTDList(tournamentCascadeDate, tdList, query, verbose_getTDList);
}

/****************************************************************

bool getPlayerList () 

Gets the last valid TDList prior to the date given by parameter 
tournamentCascadeDate.  Data placed into map parameter TdList.

Does NOT use "ratings" table;

Returns true if the operation is successful 

*****************************************************************/
bool databaseConnection::getPlayerList(boost::gregorian::date &tournamentCascadeDate, map<int, tdListEntry> &tdList, bool verbose_getTDList) {
	tdListEntry entry;	

	mysqlpp::Query query = db.query("SELECT CONCAT(players.name, ' ', players.last_name) AS name, players.pin_player, players.rating, players.sigma, players.elab_date FROM players WHERE players.rating IS NOT NULL AND players.sigma IS NOT NULL");
	if (verbose_getTDList) {
		cout << "databaseConnection::getPlayerList: " << query.str() << endl;
		cout << endl;
	}

	query.parse();
	mysqlpp::StoreQueryResult res = query.store();

	if (!res)
		return false;

	for (size_t i=0; i<res.num_rows(); ++i) {
		entry.id             = res[i]["pin_player"];
		entry.rating         = res[i]["rating"];
		entry.sigma          = res[i]["sigma"];
		entry.name           = string(res[i]["name"]);

		mysqlpp::Date tempDate = res[i]["elab_date"];
		if (tempDate == mysqlpp::Date("0000-00-00")) {
			entry.lastRatingDate = boost::gregorian::date(1900, 1, 1);
		}
		else {
			entry.lastRatingDate = boost::gregorian::date(boost::gregorian::from_simple_string(tempDate.str()));
		}
		entry.ratingUpdated  = false;
		
		tdList[entry.id] = entry;
		
		if (verbose_getTDList) 
			cout << res.num_rows() << ':' << i+1 << '\t' << entry.id << '\t' << entry.rating << '\t' 
				<< entry.sigma << '\t' << entry.name << endl;
	}
 		
	return true;
}
/****************************************************************

bool getTournamentInfo (string &tournamentCode, collection &c) 

Gets players and games from tournament indexed by parameters
tournamentCode, and place the information in parameter collection.

Returns true if operation is successful.

*****************************************************************/

bool databaseConnection::getTournamentInfo (string &tournamentCode, collection &c) {
	player p;
	game g;
	stringstream ss(stringstream::in | stringstream::out);
	int rankPartNumber;
	char rankPartKyuDan;

	std::string test;

	mysqlpp::Query dateQuery = db.query("SELECT Tournament_Date, Tournament_Descr FROM tournaments WHERE tournament_code=%0q LIMIT 1");
	dateQuery.parse();
	mysqlpp::StoreQueryResult dateResult = dateQuery.store(tournamentCode);
	mysqlpp::Date tempDate = dateResult[0]["Tournament_Date"];

	if (tempDate == mysqlpp::Date("0000-00-00")) {
		return false;
	}
	
	c.tournamentCode = tournamentCode;
	dateResult[0]["Tournament_Descr"].to_string(c.tournamentName);	
	c.tournamentDate = boost::gregorian::date(boost::gregorian::from_simple_string(tempDate.str()));
	
	cout << c.tournamentCode << '\t' << c.tournamentDate << '\t' << c.tournamentName << endl;
	
	mysqlpp::Query gameQuery = db.query("SELECT pin_player_1, rank_1, color_1, pin_player_2, rank_2, color_2, handicap, komi, result FROM games WHERE Tournament_Code=%0q AND NOT (Online OR Exclude)");
	gameQuery.parse();
	mysqlpp::StoreQueryResult gameRes=gameQuery.store(tournamentCode);

	for (size_t i=0; i<gameRes.num_rows(); i++) {
		// Process and locally store the game information 
		if (string(gameRes[i]["color_1"]) == string("W")) {
			g.white = gameRes[i]["pin_player_1"];
			g.black = gameRes[i]["pin_player_2"];
		}
		else if (string(gameRes[i]["color_1"]) == string("B")) {
			g.white = gameRes[i]["pin_player_2"];
			g.black = gameRes[i]["pin_player_1"];
		}
		else {
			cout << "Fatal error: unknown player colour " << gameRes[i]["color_1"] << endl;
			exit (1);
		}

		if (string(gameRes[i]["result"]) == string("W")) {
			g.whiteWins = true;
		}
		else if (string(gameRes[i]["result"]) == string("B")) {
			g.whiteWins = false;
		}
		else {
			cout << "Fatal error: unknown game result " << gameRes[i]["result"] << endl;
			exit (1);
		}
		
		g.handicap  = gameRes[i]["handicap"];
		g.komi      = gameRes[i]["komi"];
		
		c.gameList.push_back(g);

		// Process and locally store the player information 
		p.id = gameRes[i]["pin_player_1"];
		
		if (c.playerHash.find(p.id) == c.playerHash.end()) {		
		
			ss.str(string(gameRes[i]["rank_1"]));				
			ss >> rankPartNumber >> rankPartKyuDan;
		
			if  ( (rankPartKyuDan == 'k') || (rankPartKyuDan == 'K') ) {
				p.seed = -(rankPartNumber+0.5);
			}  		
			else if  ( (rankPartKyuDan == 'd') || (rankPartKyuDan == 'd') ) {
				p.seed = rankPartNumber+0.5;		
			}
			else {
				cout << "Fatal error: player " << gameRes[i]["pin_player_1"] << "    unknown rank format: " << gameRes[i]["rank_1"] << endl;
				exit(1);	
			}
						
			c.playerHash[p.id] = p;
		}
		
		p.id = gameRes[i]["pin_player_2"];
		
		if (c.playerHash.find(p.id) == c.playerHash.end()) {		
		
			ss.str(string(gameRes[i]["rank_2"]));				
			ss >> rankPartNumber >> rankPartKyuDan;
		
			if  ( (rankPartKyuDan == 'k') || (rankPartKyuDan == 'K') ) {
				p.seed = -(rankPartNumber+0.5);
			}  		
			else if  ( (rankPartKyuDan == 'd') || (rankPartKyuDan == 'd') ) {
				p.seed = rankPartNumber+0.5;		
			}
			else {
				cout << "Fatal error: player " << gameRes[i]["pin_player_2"] << "    unknown rank format: " << gameRes[i]["rank_2"] << endl;
				exit(1);	
			}
			
			c.playerHash[p.id] = p;		
		}
	}
	
	return true;
}

bool databaseConnection::updateAGAGD(collection &c, map<int, player>::iterator &playerIt, bool commit) {

	// mysqlpp::Query query1 = db.query("INSERT INTO ratings (pin_player, rating, sigma, elab_date) VALUES (%0q, %1q, %2q, %3q) ON DUPLICATE KEY UPDATE rating=%4q, sigma=%5q");
	mysqlpp::Query query1 = db.query("INSERT INTO ratings (pin_player, rating, sigma, elab_date, tournament_code) VALUES (%0q, %1q, %2q, %3q, %4q) ON DUPLICATE KEY UPDATE rating=%5q, sigma=%6q, tournament_code=%7q");
	query1.parse();
		
	if (showagagd) {
		cout << "updateAGAGD: " << query1.str(playerIt->second.id, playerIt->second.rating, playerIt->second.sigma, to_iso_extended_string(c.tournamentDate), c.tournamentCode, playerIt->second.rating, playerIt->second.sigma, c.tournamentCode) << ";" << endl;
	}
	if (commit) {
		query1.execute(playerIt->second.id, playerIt->second.rating, 
			playerIt->second.sigma, to_iso_extended_string(c.tournamentDate), 
			c.tournamentCode, playerIt->second.rating, playerIt->second.sigma, 
			c.tournamentCode);
		if (query1.errnum() != 0) {
			cerr << "Query failure in db.cpp.  Rolling back transaction and exiting program due to: " 
				<< query1.error() <<endl;
			return false;
		}
	}

	mysqlpp::Query query2 = db.query("UPDATE players SET rating=%0q, sigma=%1q, elab_date=%2q, Last_Appearance=%3q WHERE pin_player=%4q");
	query2.parse();
	
	if (showagagd) {
		cout << "updateAGAGD: " << query2.str(playerIt->second.rating, playerIt->second.sigma, to_iso_extended_string(c.tournamentDate), c.tournamentCode, playerIt->second.id) << ";" << endl;
	}
	if (commit) { //  and not onlyone) {										// XXX
		query2.execute(playerIt->second.rating, playerIt->second.sigma, 
			to_iso_extended_string(c.tournamentDate), c.tournamentCode, playerIt->second.id);
		if (query2.errnum() != 0) {
			cerr << "Query failure in db.cpp.  Rolling back transaction and exiting program due to: " 
			<< query2.error() <<endl;
			return false;
		}
	}
	return true;
}

bool databaseConnection::updateRatings(collection &c, map<int, player>::iterator &playerIt, bool commit) {
	mysqlpp::Query query5 = ratingsdb.query("INSERT INTO ratings (ID, Rating, Sigma, Date) VALUES (%0q, %1q, %2q, UNIX_TIMESTAMP(%3q)) ON DUPLICATE KEY UPDATE rating=%4q, sigma=%5q, date=UNIX_TIMESTAMP(%6q)");
	query5.parse();

	if (showratingsdb) {
		cout << "updateRatings: " << query5.str(playerIt->second.id, playerIt->second.rating, playerIt->second.sigma, to_iso_extended_string(c.tournamentDate), playerIt->second.rating, playerIt->second.sigma, to_iso_extended_string(c.tournamentDate)) << ";" << endl;
	}
	if (commit) {
		query5.execute(playerIt->second.id, playerIt->second.rating, playerIt->second.sigma, to_iso_extended_string(c.tournamentDate), 
			playerIt->second.rating, playerIt->second.sigma, to_iso_extended_string(c.tournamentDate));
		if (query5.errnum() != 0) {
			cerr << "Query failure in db.cpp.  Rolling back transaction and exiting program due to: " 
				<< query5.error() << endl;
			return false;
		}
	}
	return true;
}

bool databaseConnection::updateMembers(collection &c, map<int, player>::iterator &playerIt, bool commit) {
/*
	mysqlpp::Query query5 = membersdb.query("INSERT INTO ratings (ID, Rating, Sigma, Date) VALUES (%0q, %1q, %2q, UNIX_TIMESTAMP(%3q)) ON DUPLICATE KEY UPDATE rating=%4q, sigma=%5q, date=UNIX_TIMESTAMP(%6q)");
 */
	mysqlpp::Query query5 = membersdb.query("UPDATE ratings SET rating=%0q, sigma=%1q, date=UNIX_TIMESTAMP(%2q) WHERE ID=%3q");
	query5.parse();

	if (showmembersdb) {
/*
		cout << "updateMembers: " << query5.str(playerIt->second.id, playerIt->second.rating, playerIt->second.sigma, 
			to_iso_extended_string(c.tournamentDate), playerIt->second.rating, 
			playerIt->second.sigma, to_iso_extended_string(c.tournamentDate)) << endl;
 */
		cout << "updateMembers: " << query5.str(playerIt->second.rating, playerIt->second.sigma, to_iso_extended_string(c.tournamentDate), playerIt->second.id) << ";" << endl;
	}
	if (commit) { //  and not onlyone) {										// XXX
/* 
		query5.execute(playerIt->second.id, playerIt->second.rating, playerIt->second.sigma, 
			to_iso_extended_string(c.tournamentDate), playerIt->second.rating, 
			playerIt->second.sigma, to_iso_extended_string(c.tournamentDate));
 */
		query5.execute(playerIt->second.rating, playerIt->second.sigma, 
			to_iso_extended_string(c.tournamentDate), playerIt->second.id);
		if (query5.errnum() != 0) {
			cerr << "Query failure in db.cpp.  Rolling back transaction and exiting program due to: " 
				<< query5.error() << endl;
			return false;
		}
	}
	return true;
}

/****************************************************************

void syncNewRatings (collection &c) 

Pushes new ratings onto the various ratings databases and updates
appropriate indexes.

*****************************************************************/
void databaseConnection::syncNewRatings (collection &c, bool commit) {

	map<int, player>::iterator playerIt = c.playerHash.begin();	

	mysqlpp::Transaction trans_agagd(db);
	mysqlpp::Transaction trans_ratings(ratingsdb);
	mysqlpp::Transaction trans_members(membersdb);

	for (playerIt = c.playerHash.begin(); playerIt != c.playerHash.end(); playerIt++) {
        cout << "Updating records for ID: " << playerIt->second.id << endl;
		if ( updateAGAGD(c, playerIt, commit) == false ) {			// commit or &commit ?
			trans_agagd.rollback();
			exit(1);
		}
		if ( updateRatings(c, playerIt, commit) == false ) {                     // commit or &commit ?
			trans_ratings.rollback();
			trans_agagd.rollback();
			exit(1);
		}
		if ( updateMembers(c, playerIt, commit) == false ) {                     // commit or &commit ?
			trans_members.rollback();
			trans_ratings.rollback();
			trans_agagd.rollback();
			exit(1);
		}
		if (showagagd or showratingsdb or showmembersdb) 
			cout << endl;
	}

	// Finish updating AGAGD
	mysqlpp::Query query2 = db.query("UPDATE games SET elab_date = %0q, Rated = 1 WHERE tournament_code=%1q AND Online=0");
	query2.parse();

	// Update the elab_dates for tournaments
	mysqlpp::Query tournaments_query = db.query("UPDATE tournaments SET elab_date = %0q, Status = 1 WHERE tournament_code=%1q");
	tournaments_query.parse();

	if (showagagd) {
		cout << "syncNewRatings: AGAGD Games: " << query2.str(to_iso_extended_string(c.tournamentDate), c.tournamentCode) << ";" << endl;
		cout << "syncNewRatings: AGAGD Tournaments: " << tournaments_query.str(to_iso_extended_string(c.tournamentDate), c.tournamentCode) << ";" << endl;
	}
	if (commit) {
		query2.execute(to_iso_extended_string(c.tournamentDate), c.tournamentCode);
		if (query2.errnum() != 0) {
			cerr << "Query failure in db.cpp.  Rolling back transaction and exiting program due to: " 
				<< query2.error() << endl;
			trans_agagd.rollback();
			exit(1);
		}

		tournaments_query.execute(to_iso_extended_string(c.tournamentDate), c.tournamentCode);
	    if (tournaments_query.errnum() != 0) {
			cerr << "Query failure in db.cpp.  Rolling back transaction and exiting program due to: " 
				<< tournaments_query.error() << endl;
			trans_agagd.rollback();
			exit(1);	
		}
	}
	cout << endl;

	// Finish updating Ratings
	tm d_tm = to_tm(c.tournamentDate);
	mysqlpp::Query query6 = ratingsdb.query("INSERT INTO ratings_tourneys (Year, Month, Day, Label) VALUES (%0q, %1q, %2q, %3q)");
	query6.parse();
	if (showratingsdb) {
		cout << "syncNewRatings: Ratings DB: " << query6.str(1900+d_tm.tm_year, 1+d_tm.tm_mon, d_tm.tm_mday, c.tournamentName) << ";" << endl;
	}
	if (commit) {
		query6.execute(1900+d_tm.tm_year, 1+d_tm.tm_mon, d_tm.tm_mday, c.tournamentName);
		if (query6.errnum() != 0) {
			cerr << "Query failure in db.cpp.  Rolling back transaction and exiting program due to: " 
				<< query6.error() << endl;
			trans_ratings.rollback();
			trans_agagd.rollback();
			exit(1);	
		}
	}
	mysqlpp::Query query7 = ratingsdb.query("INSERT INTO ratings_log (Name, User, Date, Seq, Extra) VALUES ('RatingsUpdate', 0, NOW(), 0, 'Bayrate Update')");
	query7.parse();
	if (showratingsdb) {
		cout << "syncNewRatings: Ratings DB: " << query7.str() << ";" << endl;
	}
	if (commit) {
		query7.execute();
		if (query7.errnum() != 0) {
			cerr << "Query failure in db.cpp.  Rolling back transaction and exiting program due to: " 
				<< query7.error() << endl;
			trans_ratings.rollback();
			trans_agagd.rollback();
			exit(1);	
		}
	}
	cout << endl;

	// Finish updating Members
	mysqlpp::Query query6a = membersdb.query("INSERT INTO ratings_tourneys (Year, Month, Day, Label) VALUES (%0q, %1q, %2q, %3q)");
	query6a.parse();
	if (showmembersdb) {
		cout << "syncNewRatings: Members DB: " << query6.str(1900+d_tm.tm_year, 1+d_tm.tm_mon, d_tm.tm_mday, c.tournamentName) << ";" << endl;
	}
	if (commit) {
		query6a.execute(1900+d_tm.tm_year, 1+d_tm.tm_mon, d_tm.tm_mday, c.tournamentName);
		if (query6a.errnum() != 0) {
			cerr << "Query failure in db.cpp.  Rolling back transaction and exiting program due to: " 
				<< query6a.error() << endl;
			trans_members.rollback();
			trans_ratings.rollback();
			trans_agagd.rollback();
			exit(1);	
		}
	}
	mysqlpp::Query query7a = membersdb.query("INSERT INTO ratings_log (Name, User, Date, Seq, Extra) VALUES ('RatingsUpdate', 0, NOW(), 0, 'Bayrate Update')");
	query7a.parse();
	if (showmembersdb) {
		cout << "syncNewRatings: Members DB: " << query7.str() << ";" << endl;
	}
	if (commit) {
		query7a.execute();
		if (query7a.errnum() != 0) {
			cerr << "Query failure in db.cpp.  Rolling back transaction and exiting program due to: " 
				<< query7a.error() << endl;
			trans_members.rollback();
			trans_ratings.rollback();
			trans_agagd.rollback();
			exit(1);	
		}
	}
	cout << endl;

	trans_members.commit();
	trans_ratings.commit();
	trans_agagd.commit();

	return;
}

/****************************************************************

void syncDBs (map<int, tdListEntry> &tdList)

Pushes new ratings onto the various ratings databases and updates
appropriate indexes.

*****************************************************************/
void databaseConnection::syncDBs (map<int, tdListEntry> &tdList, bool commit) {

	bool show = false;

	mysqlpp::Query agagdquery = db.query("SELECT rating, sigma, Elab_Date AS date FROM players WHERE Pin_Player = %0q");
	agagdquery.parse();

	mysqlpp::Query ratingsdbquery = ratingsdb.query("SELECT rating, sigma, FROM_UNIXTIME(date, '%Y-%m-%d') AS date FROM ratings WHERE ID = %0q");
	ratingsdbquery.parse();

	mysqlpp::Query membersdbquery = membersdb.query("SELECT rating, sigma, FROM_UNIXTIME(date, '%Y-%m-%d') AS date FROM ratings WHERE ID = %0q");
	membersdbquery.parse();

	mysqlpp::Query update = db.query("UPDATE players SET rating = %0q, sigma = %1q, Elab_Date = %2q WHERE Pin_Player = %3q");
	update.parse();

	for (map<int, tdListEntry>::iterator tdListIt = tdList.begin(); tdListIt != tdList.end(); tdListIt++) {

		// Get data from the AGAGD
		mysqlpp::StoreQueryResult agagd_res = agagdquery.store(tdListIt->second.id);
		if (!agagd_res) {
			cerr << "mysqlpp::StoreQueryResult() failed: " << agagdquery.errnum() 
				<< " : " << agagdquery.error() << endl;
			exit(-1);
		}
		double agagd_rating = 0;
		if (strcmp((const char*)agagd_res[0]["rating"], "NULL") == 0)
			agagd_rating = 0;
		else
			agagd_rating = agagd_res[0]["rating"];
		double agagd_sigma  = 0;
		if (strcmp((const char*)agagd_res[0]["sigma"], "NULL") == 0)
			agagd_sigma = 0;
		else
			agagd_sigma = agagd_res[0]["sigma"];
//		string agagd_date   = agagd_res[0]["date"];

		// Get data from the ratings database
		mysqlpp::StoreQueryResult ratings_res = ratingsdbquery.store(tdListIt->second.id);
		if (!ratings_res) {
			cerr << "mysqlpp::StoreQueryResult() failed: " << ratingsdbquery.errnum() 
				<< " : " << ratingsdbquery.error() << endl;
			exit(-1);
		}
		double ratings_rating = ratings_res[0]["rating"];
		double ratings_sigma  = ratings_res[0]["sigma"];
//		string ratings_date   = ratings_res[0]["date"];				Grrr....const_reference splat!#$*(!

		if (ratings_rating == 0 or ratings_sigma == 0)
			continue;

		// Get data from the members database
		mysqlpp::StoreQueryResult members_res = membersdbquery.store(tdListIt->second.id);
		if (!members_res) {
			cerr << "mysqlpp::StoreQueryResult() failed: " << membersdbquery.errnum() 
				<< " : " << membersdbquery.error() <<endl;
			exit(-1);
		}
		double members_rating = members_res[0]["rating"];
		double members_sigma  = members_res[0]["sigma"];
		mysqlpp::Date md      = members_res[0]["date"];
		string members_date   = md.str();
		
		if (ratings_rating != members_rating or ratings_sigma != members_sigma or ratings_res[0]["date"] != members_res[0]["date"]) {
			cout << "Update Members to match Ratings: " << tdListIt->second.id 
				<< "\tratings_date: " << ratings_res[0]["date"] << "\tmembers_date: " << members_res[0]["date"] << endl;
			exit(-1);
		}

// value obtained by iteration.  this value prevents certain ineffective database updates
//	SIGMA: precision: 1e-05, difference: 1e-05
//	Update AGAGD to match Ratings: 6
//	6       r:  5.009620    r:0.391880      2007-07-01              m:  5.009620    m:0.391880        5.009620      0.391870
//	AGAGD: UPDATE players SET rating = 5.00962, sigma = 0.39188000000000001, Elab_Date = '2007-07-01' WHERE Pin_Player = 6

		double precision = 0.000010000000001;			
// #ifdef REPORT_PRECISION		 
		if  ( (fabs(ratings_rating) - fabs(agagd_rating)) > precision ) 
			cout << setprecision(10) << "RATING: precision: " << precision << ", difference: " 
				<< (fabs(ratings_rating) - fabs(agagd_rating)) << endl;
		if  ( (fabs(ratings_sigma) - fabs(agagd_sigma)) > precision ) 
			cout << setprecision(10) << "SIGMA: precision: " << precision << ", difference: " 
				<< (fabs(ratings_sigma) - fabs(agagd_sigma)) << endl;
// #endif

		if ( (fabs(ratings_rating) - fabs(agagd_rating)) > precision or
			(fabs(ratings_sigma) - fabs(agagd_sigma)) > precision) {

			cout << "Update AGAGD to match Ratings: " << tdListIt->second.id << endl;
			cout << fixed << setprecision(6) << tdListIt->second.id 
				<< "\tr:" << setw(10) << ratings_rating << "\tr:" << ratings_sigma << '\t' << members_date << '\t'
				<< "\tm:" << setw(10) << members_rating << "\tm:" << members_sigma << '\t' 
				<< setw(10) << agagd_rating << '\t' << agagd_sigma << endl;
			cout << "AGAGD: " << update.str(ratings_rating, ratings_sigma, ratings_res[0]["date"], tdListIt->second.id) << endl;
			cout << endl;
			show = false;
cout << "commit: " << commit << endl;
			if (commit) {
				mysqlpp::Transaction trans_update(db);
				// update.execute(ratings_rating, ratings_sigma, ratings_res[0]["date"], tdListIt->second.id);
				update.execute(ratings_rating, ratings_sigma, ratings_res[0]["date"], tdListIt->second.id);

				if (update.errnum() != 0) {
					cerr << "update Query failure in db.cpp.  Rolling back transaction and exiting program due to: " 
						<< update.error() << endl;
					trans_update.rollback();
					exit(1);
				}
				trans_update.commit();
			}
// cerr << update.error() << endl;
// exit(0);
		}

//		if (tdListIt->second.id > 1620)
//			break;
	}
}
