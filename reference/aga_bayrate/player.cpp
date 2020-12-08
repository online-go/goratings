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

#include <gsl/gsl_spline.h>
#include "player.h"

player::player(void)
{
}

player::~player(void)
{
}

/****************************************************************

calc_init_sigma (double seed) 

Provides a sigma value for a new player entering the rating
system for the first time.  Value depends on the seed rating of
the player, with the sigma increasing as the nominal rating
decreases.

Data is interpolated for points away from the ratings corresponding
to the midpoints of each rank. 

*****************************************************************/
double player::calc_init_sigma (double seed) {
	/* Data is extracted from Accelrat output, with ratings (r[])
	   offset by 1.0 towards 0 (i.e., -5.5 -> -4.5, +4.5->+3.5) in
	   order to compensate for the jump across the dan boundary  */
	double r[] = {-49.5, -48.5, -47.5, -46.5, -45.5,
						-44.5, -43.5, -42.5, -41.5, -40.5,
						-39.5, -38.5, -37.5, -36.5, -35.5,
						-34.5, -33.5, -32.5, -31.5, -30.5,
						-29.5, -28.5, -27.5, -26.5, -25.5,
						-24.5, -23.5, -22.5, -21.5, -20.5,
						-19.5, -18.5, -17.5, -16.5, -15.5,
						-14.5, -13.5, -12.5, -11.5, -10.5,
						-9.5, -8.5, -7.5, -6.5, -5.5,
						-4.5, -3.5, -2.5, -1.5, -0.5,
						0.5, 1.5, 2.5, 3.5, 4.5,
						5.5, 6.5, 7.5, 8.5};
					
	double s[] = {5.73781, 5.63937, 5.54098, 5.44266, 5.34439,
						5.24619, 5.14806, 5.05000, 4.95202, 4.85412,
						4.75631, 4.65859, 4.56098, 4.46346, 4.36606,
						4.26878, 4.17163, 4.07462, 3.97775, 3.88104,
						3.78451, 3.68816, 3.59201, 3.49607, 3.40037,
						3.30492, 3.20975, 3.11488, 3.02035, 2.92617,
						2.83240, 2.73907, 2.64622, 2.55392, 2.46221,
						2.37118, 2.28090, 2.19146, 2.10297, 2.01556,
						1.92938, 1.84459, 1.76139, 1.68003, 1.60078,
						1.52398, 1.45000, 1.37931, 1.31244, 1.25000,
						1.19269, 1.14127, 1.09659, 1.05948, 1.03078,
						1.01119, 1.00125, 1.00000, 1.00000};
	double result;
						
	if (seed > 7.5)
		return 1.0;
	else if (seed < -50.5)
		// If you're seeding someone below 50 kyu, you're up to no good. :)
		return 6.0;
		
	gsl_interp_accel *acc    = gsl_interp_accel_alloc ();
	gsl_spline       *spline = gsl_spline_alloc (gsl_interp_cspline, 59);
     
   gsl_spline_init (spline, r, s, 59);
   
   if (seed > 0)  
   	result = gsl_spline_eval (spline, seed-1.0, acc);
   else
   	result = gsl_spline_eval (spline, seed+1.0, acc);
   
   gsl_spline_free (spline);
   gsl_interp_accel_free (acc);

	return result;
}

