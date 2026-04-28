#if defined _pawnbots_included
	#endinput
#endif
#define _pawnbots_included

stock IsPlayerPBot(playerid) return (CallRemoteFunction("IsPlayerPBot", "i", playerid) == 1);

// Убираем все макросы и ALS систему полностью
// Вместо переопределения стандартных функций,
// создаем новые функции с префиксом PB_

// Используйте эти функции в моде вместо стандартных
stock PB_Kick(playerid)
{
    if(!IsPlayerPBot(playerid)) 
        return Kick(playerid);
    return 1;
}

stock PB_Ban(playerid)
{
    if(!IsPlayerPBot(playerid)) 
        return Ban(playerid);
    return 1;
}

stock PB_BanEx(playerid, const reason[])
{
    if(!IsPlayerPBot(playerid)) 
        return BanEx(playerid, reason);
    return 1;
}

#if defined BlockIpAddress
	stock PB_BlockIpAddress(ip_address[], timems)
	{
		new ip[20];
	    for(new i = GetMaxPlayers()-1; i >= 0; i--) 
	    {
	        if(IsPlayerConnected(i))
	        {
	            GetPlayerIp(i, ip, sizeof(ip));
	            if(ip[0] && ip_address[0] && !strcmp(ip, ip_address)) 
	            { 
	                if(!IsPlayerPBot(i)) 
	                    BlockIpAddress(ip_address, timems); 
	            }
	        }
	    }
		return 1;
	}
#endif