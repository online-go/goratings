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
#include "collection.h"
#include "player.h"
#include "game.h"

using namespace std;

databaseConnection::databaseConnection() {

}

databaseConnection::~databaseConnection() {
	db.disconnect();
}

/****************************************************************

makeConnection () 

Establish a connection to the ratings server(s).

*****************************************************************/
bool databaseConnection::makeConnection() {
	db = mysqlpp::Connection(false);

	return db.connect("aga_test_data", "localhost", "aga", "test");;
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

bool getTournamentUpdateList (vector<string> tournamentUpdateList, date tournamentCascadeDate) 

Get the list of tournaments that need (re)rating.  List of 
tournament codes is placed in parameter TournamentUpdateList.
Date of first tournament that need rerating placed in parameter 
tournamentCascadeDate.

Returns true if the operation was successful

*****************************************************************/
bool databaseConnection::getTournamentUpdateList(vector<string> &tournamentUpdateList, boost::gregorian::date &tournamentCascadeDate) {
	mysqlpp::Query query = db.query("SELECT MIN(Game_Date) AS date FROM games WHERE Game_Date>'1900-01-01' AND NOT (Online OR Exclude OR Rated)");

	mysqlpp::StoreQueryResult res = query.store();

	if (!res)
		return false;

	mysqlpp::Date tempDate = res[0]["date"];

	// Check if the response was NULL.  The date gets converted to 0000-00-00 if it is.
	if (tempDate == mysqlpp::Date("0000-00-00"))	{
		return true;
	}
	tournamentCascadeDate = boost::gregorian::date(boost::gregorian::from_simple_string(tempDate.str()));

	mysqlpp::Query query2 = db.query("SELECT Tournament_Code FROM tournaments WHERE Tournament_Date>=%0q ORDER BY Tournament_Date");
	query2.parse();	
	res = query2.store(tempDate);
	
	for (size_t i=0; i<res.num_rows(); i++) {
		tournamentUpdateList.push_back(static_cast<string>(res[i]["Tournament_Code"]));
	}
  
	return true;	 
}


/****************************************************************

bool getTDList () 

Gets the last valid TDList prior to the date given by parameter 
tournamentCascadeDate.  Data placed into map parameter TdList.

Returns true if the operation is successful 

*****************************************************************/
bool databaseConnection::getTDList(boost::gregorian::date &tournamentCascadeDate, map<int, tdListEntry> &tdList) {
	tdListEntry entry;	
	
	mysqlpp::Query query = db.query("SELECT name, x.pin_player, x.rating, x.sigma, x.elab_date FROM ratings x, players, (SELECT MAX(elab_date) AS maxdate, pin_player FROM ratings WHERE elab_date < %0q GROUP BY pin_player) AS maxresults WHERE x.pin_player=maxresults.pin_player AND x.elab_date=maxresults.maxdate and x.pin_player=players.pin_player and x.pin_player!=0");
	query.parse();
	mysqlpp::StoreQueryResult res = query.store(mysqlpp::Date(boost::gregorian::to_iso_extended_string(tournamentCascadeDate)));

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

/****************************************************************

void syncNewRatings (collection &c) 

Pushes new ratings into the ratings database and update appropriate indexes.

*****************************************************************/
void databaseConnection::syncNewRatings (collection &c) {

	map<int, player>::iterator playerIt = c.playerHash.begin();	

	mysqlpp::Transaction trans(db);

	mysqlpp::Query query1 = db.query("INSERT INTO ratings (pin_player, rating, sigma, elab_date) VALUES (%0q, %1q, %2q, %3q) ON DUPLICATE KEY UPDATE rating=%4q, sigma=%5q");
	query1.parse();
		
	mysqlpp::Query query4 = db.query("UPDATE players SET rating=%0q, sigma=%1q, elab_date=%2q WHERE pin_player=%3q");
	query4.parse();	
	
	for (playerIt = c.playerHash.begin(); playerIt != c.playerHash.end(); playerIt++) {
		query1.execute(playerIt->second.id, playerIt->second.rating, playerIt->second.sigma, to_iso_extended_string(c.tournamentDate), playerIt->second.rating, playerIt->second.sigma);
		if (query1.errnum() != 0) {
			cerr << "Query failure in query1 (db.cpp).  Rolling back transaction and exiting program" << endl;
			trans.rollback();
			exit(1);	
		}
		
		query4.execute(playerIt->second.rating, playerIt->second.sigma, to_iso_extended_string(c.tournamentDate), playerIt->second.id);
		if (query4.errnum() != 0) {
			cerr << "Query failure in query4 (db.cpp).  Rolling back transaction and exiting program" << endl;
			trans.rollback();
			exit(1);
		}
	}
	
	mysqlpp::Query query2 = db.query("UPDATE games SET elab_date = %0q WHERE tournament_code=%1q AND Online=0");
	query2.parse();
	query2.execute(to_iso_extended_string(c.tournamentDate), c.tournamentCode);
	if (query2.errnum() != 0) {
		cerr << "Query failure in query2 (db.cpp).  Rolling back transaction and exiting program" << endl;
		trans.rollback();
		exit(1);	
	}
	
	mysqlpp::Query query3 = db.query("UPDATE games SET Rated=1 WHERE tournament_code=%0q AND Online=0");
	query3.parse();
	query3.execute(c.tournamentCode);
	if (query3.errnum() != 0) {
		cerr << "Query failure in (db.cpp).  Rolling back transaction and exiting program" << endl;
		trans.rollback();	
		exit(1);	
	}
	
	trans.commit();
}
