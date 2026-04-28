/*==============================================================================
                        Player geolocation information
                        player_geolocation.inc v1.0.0
                        Author: whale (a.k.a Twixxx / Twixyck)

Copyright (c) 2018-2019 Nikita Shtimenko (whale)

This software is provided 'as-is', without any express or implied warranty.
In no event will the authors be held liable for any damages arising from the
use of this software.

Permission is granted to anyone to use this software for
any purpose, including commercial applications, and to alter it and
redistribute it freely, subject to the following restrictions:

1.  The origin of this software must not be misrepresented; you must not
    claim that you wrote the original software. If you use this software in
    a product, an acknowledgment in the product documentation would be
    appreciated but is not required.

2.  Altered source versions must be plainly marked as such, and must not be
    misrepresented as being the original software.

3.  This notice may not be removed or altered from any source distribution.
==============================================================================*/
#if defined _player_geolocation_included
    #endinput
#endif
#define _player_geolocation_included

#if !defined _samp_included
    #error Please include <a_samp> first.
#endif

#if !defined sscanf
    #error Please include <sscanf2> first.
#endif

#define GEO_IP_INFO_DETECT_URL             "ip-api.com/csv/"
#define GEO_IP_INFO_DETECT_URL_FIELDS    "?fields=131793"

#define GEO_MAX_IP_LENGTH                 16
#define GEO_MAX_COUNTRY_NAME_LENGTH     32
#define GEO_MAX_CITY_NAME_LENGTH        32
#define GEO_MAX_LAT_LON_LENGTH             12
#define GEO_MAX_PROVIDER_NAME_LENGTH    32
#define GEO_MAX_PROXY_LENGTH            6

enum e_PLAYER_GEO_INFORMATION
{
    player_ip[GEO_MAX_IP_LENGTH + 1],
    player_country[GEO_MAX_COUNTRY_NAME_LENGTH + 1],
    player_city[GEO_MAX_CITY_NAME_LENGTH + 1],
    player_lat[GEO_MAX_LAT_LON_LENGTH + 1],
    player_lon[GEO_MAX_LAT_LON_LENGTH + 1],
    player_provider[GEO_MAX_PROVIDER_NAME_LENGTH + 1],
    player_proxy[GEO_MAX_PROXY_LENGTH + 1]
};
new
    player_geoInfo[MAX_PLAYERS][e_PLAYER_GEO_INFORMATION];

#define GetPlayerCountry(%0)        player_geoInfo[%0][player_country]
#define GetPlayerCity(%0)            player_geoInfo[%0][player_city]
#define GetPlayerLatitude(%0)        player_geoInfo[%0][player_lat]
#define GetPlayerLongtitude(%0)        player_geoInfo[%0][player_lon]
#define GetPlayerProvider(%0)        player_geoInfo[%0][player_provider]
#define GetPlayerProxyStatus(%0)    player_geoInfo[%0][player_proxy]

forward p_geo_OnPlayerInfoRequested(playerid, response_code, data[]);
public p_geo_OnPlayerInfoRequested(playerid, response_code, data[])
{
    if(response_code == 200)
    {
        sscanf(data, "p<,>s[32]s[32]s[12]s[12]s[32]s[6]",
            player_geoInfo[playerid][player_country],
            player_geoInfo[playerid][player_city],
            player_geoInfo[playerid][player_lat],
            player_geoInfo[playerid][player_lon],
            player_geoInfo[playerid][player_provider],
            player_geoInfo[playerid][player_proxy]);
    }
    else
    {
        strmid(player_geoInfo[playerid][player_country], "-", 0, GEO_MAX_COUNTRY_NAME_LENGTH);
        strmid(player_geoInfo[playerid][player_city], "-", 0, GEO_MAX_CITY_NAME_LENGTH);
        strmid(player_geoInfo[playerid][player_lat], "-", 0, GEO_MAX_LAT_LON_LENGTH);
        strmid(player_geoInfo[playerid][player_lon], "-", 0, GEO_MAX_LAT_LON_LENGTH);
        strmid(player_geoInfo[playerid][player_provider], "-", 0, GEO_MAX_PROVIDER_NAME_LENGTH);
        strmid(player_geoInfo[playerid][player_proxy], "-", 0, GEO_MAX_PROXY_LENGTH);
    }
    return 1;
}
