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
#include "game.h"

using namespace std;

game::game(void)
{
}

game::~game(void)
{
}

void game::calc_handicapeqv() {

/*
	if (handicap == 0) {
		handicapeqv = 0.580 - 0.0757 * komi;
		sigma_px = 1.0649 - 0.0021976 * komi + 0.00014984 * komi * komi;
	}
	else if (handicap == 1) {
		handicapeqv = 0.580 - 0.0757 * (komi);
		sigma_px = 1.0649 - 0.0021976 * (komi) + 0.00014984 * (komi) * (komi);
	}
	else {
		handicapeqv = handicap - 0.0757*komi;
		sigma_px = -0.0035169 * komi;		
		switch (handicap) {
			case 2:
				sigma_px += 1.13672;
				break;
			case 3: 
				sigma_px += 1.18795;
				break;
			case 4:
				sigma_px += 1.22841;
				break;
			case 5:
				sigma_px += 1.27457;
				break;
			case 6:
				sigma_px += 1.31978;
				break;
			case 7:
				sigma_px += 1.35881;
				break;
			case 8:
				sigma_px += 1.39782;
				break;
			case 9:
				sigma_px += 1.43614;
				break;	
		}	
	}
	
*/
	sigma_px=1.04;
	if (handicap >= 2) {
		handicapeqv = handicap - 0.1 * komi; 
	}
	else {
		handicapeqv = 0.5 - 0.1*komi;
	}
}
