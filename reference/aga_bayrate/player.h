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

class player
{
public:
	player(void);
	~player(void);
	double calc_init_sigma (double seed);
	double seed;				// Initial rating
	double sigma;				// Standard deviation of rating
	double rating;				// Current rating in the iteration
	int id;
	int index;				// Index of the GSL vector element that corresponds to the rating of this player
};
