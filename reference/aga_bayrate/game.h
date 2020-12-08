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

class game
{
public:
	game(void);
	~game(void);
	int komi;				// Komi;
	int handicap;			// Actual handicap
	bool whiteWins;			// True if White wins
	int white;				// Player index of White
	int black;				// Player index of Black
	void calc_handicapeqv();
	double handicapeqv;		// Equivalent rating adjustment based on handicap and komi
	double sigma_px;
};
