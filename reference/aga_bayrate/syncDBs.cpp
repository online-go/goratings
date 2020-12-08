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

int main(int argc, char *argv[]) {
 	databaseConnection db;
	boost::gregorian::date tournamentCascadeDate;		
 	map<int, tdListEntry> tdList;
 	map<string, bool> argList;
 	collection c;
	bool commit = false;
	bool verbose_getTDList = false;

	// Process command line
	for (int i=1; i<argc; i++) 
		argList[string(argv[i])] = true;
	if (argList.find(string("--commit")) != argList.end())
		commit = true;
	if (argList.find(string("--getTDList")) != argList.end())
		verbose_getTDList = true;

	// Connect to database
	if ( !db.makeConnection() ) {	
		std::cerr << "Fatal error:  db.makeConnection() failed." << std::endl;
		exit (1);
	}

	// Get most recent game's date
	if (!db.getMostRecentRatedGameDate(tournamentCascadeDate)) {
		std::cerr << "Fatal error: getMostRecentRatedGameDate() failed." << std::endl;
		exit(1);
	}
	else {
		std::cout << "Most recent RATED game date: " << to_iso_extended_string(tournamentCascadeDate) << std::endl;
	}

	// Get the TDList updated based upon the most recently rated game
	if (!db.getTDListCurrent(tdList, verbose_getTDList)) {
		std::cerr << "Fatal error: getTDList() failed." << std::endl;
		exit(1);
	}
	else {
		cout << "Downloaded TDList: " << tdList.size() << endl;
	}
	// Update the AGAGD players table with the values obtained from db.getTDList()
	db.syncDBs(tdList, commit);

	return true;
exit(0);
}


/* ------------------------------------------------------------------------
	
	mysqlpp::Query query1 = db.query("select concat(last_Name,', ',Name) as name, pin_player as id, MType as mtype, Club as chapter, State_Code as state, MExp as expiry from players where pin_player!=0;");	
	mysqlpp::StoreQueryResult res = query1.store();

	mysqlpp::Query query2 = ratingsdb.query("insert into ratings (ID, Name, MType, Chapter, State, MExp, MExp2) VALUES (%0q, %1q, %2q, %3q, %4q, UNIX_TIMESTAMP(%5q), DATE_FORMAT(%6q, '%m/%d/%y')) on duplicate key update name=%7q, MType=%8q, Chapter=%9q, State=%10q, MExp=UNIX_TIMESTAMP(%11q), MExp2= DATE_FORMAT(%12q, '%m/%d/%y')");
	query2.parse();

	for (size_t i=0; i<res.num_rows(); i++) {				
		query2.execute(res[i]["id"], res[i]["name"], res[i]["mtype"], res[i]["chapter"], res[i]["state"], res[i]["expiry"], res[i]["expiry"], res[i]["name"], res[i]["mtype"], res[i]["chapter"], res[i]["state"], res[i]["expiry"], res[i]["expiry"]);
		cout << "Finished id: " << res[i]["id"] << "\t" << res[i]["name"] << endl;
	}
	
	mysqlpp::Query query3 = ratingsdb.query("insert into ratings_log (name, user, date, seq, extra) values ('MembershipUpdate', 0, NOW(), 0, 'Transfer from AGAGD')");
	query3.execute();
	
	return 0;
------------------------------------------------------------------------ */
