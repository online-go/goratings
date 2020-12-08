#include <iostream>
#include <string>
#include <mysql++/mysql++.h>

using namespace std;

int main() {
 	mysqlpp::Connection db;
 	mysqlpp::Connection ratingsdb;

	db.connect("usgo_agagd", "dosaku.ctipc.com", "usgo_agagd", "sE9Uqd2xGUmCdpzF");
	ratingsdb.connect("usgo", "mysql1.ctipc.com", "usgo_ratings", "9V8Smw2WsLTtJm8A");

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
}
