#include <iostream>
#include <cmath>
#include <gsl/gsl_multimin.h>
#include <gsl/gsl_sf_erf.h>
#include <mysql++/mysql++.h>
#include "player.h"
#include "game.h"
#include "collection.h"

using namespace std;

int main(void) {
	int tournid;
	collection c;
	player p;
	game g;
	
	mysqlpp::Connection conn(false);

	if (conn.connect("ratings", "localhost", "pwaldron", "Burcan**")) {
		mysqlpp::Query query = conn.query("SELECT Players.agaid AS ID, Players.rating AS EntryRating FROM Players WHERE TournamentIndex=%0q ORDER BY agaid;");
		query.parse();
		
		mysqlpp::StoreQueryResult res = query.store(tournid);
		
		if (res) {
			for (size_t i=0; i<res.num_rows(); i++) {
				p.seed = res[i]["EntryRating"];
				p.id   = res[i]["ID"];
				p.sigma = 0.5;			

				c.playerHash[p.id] = p;
			}
		}		
		
		mysqlpp::Query query2 = conn.query("SELECT * FROM Games WHERE TournamentIndex=%0q ORDER BY idx");
		query2.parse();
		
		mysqlpp::StoreQueryResult res2 = query2.store(tournid);
		
		if (res2) {
			for (size_t i=0; i<res2.num_rows(); i++) {
				g.white     = res2[i]["WhitePlayer"];
				g.black     = res2[i]["BlackPlayer"];
				g.handicap  = res2[i]["Handicap"];
				g.komi      = res2[i]["Komi"];
				g.whiteWins = res2[i]["WhiteWins"];
				
				c.gameList.push_back(g);		
			}
		}	
	}
	
	// Run the faster algorithm first; use the slower one as a backup.
	if (c.calc_ratings_fdf() != 0)
		c.calc_ratings();
		
	for (map<int, player>::iterator It = c.playerHash.begin(); It != c.playerHash.end(); It++) {
		cout << It->second.id << '\t' << It->second.rating << '\t' << It->second.sigma << endl;
	}
		
	return 0;
}
