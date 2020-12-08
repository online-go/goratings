/*
 * Description: 
 * - Example db_passwords.h file for configuration of the usgo_agagd database.
 */

/* Database for the usgo_agagd. */
const char * usgo_agagd_database	= "";
const char * usgo_agagd_server		= "";

/* Read / Write user for the usgo_agagd database. */
const char * usgo_agagd_user		= "";
const char * usgo_agagd_password 	= "";

/* Read Only user for the usgo_agagd database. */
const char * usgo_agagd_ro_user        = "";
const char * usgo_agagd_ro_password    = "";

/* Ratings Lookup database. */
const char * ratings_database	= "";
const char * ratings_server	= "";

/* Ratings Lookup Read / Write database user. */
const char * ratings_user	= "";
const char * ratings_password	= "";

/* Member's database connection information. */
const char * members_database	= ratings_database;
const char * members_server	= ratings_server;
const char * members_user	= ratings_user;
const char * members_password	= ratings_password;
