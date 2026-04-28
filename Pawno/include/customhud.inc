#define CUSTOM_RPC_TOGGLE_HUD_ELEMENT   0x1
#define PACKET_CUSTOMRPC    251

#define HUD_ELEMENT_CHAT    0
#define HUD_ELEMENT_MAP     1
#define HUD_ELEMENT_TAGS    2
#define HUD_ELEMENT_BUTTONS 3
#define HUD_ELEMENT_HUD     4
#define HUD_ELEMENT_VOICE	5
#define HUD_ELEMENT_TEXTLABELS	6

#define MAX_STREAM_SOURCES	1000

#define RPC_STREAM_CREATE	0x2
#define RPC_STREAM_POS		0x3
#define RPC_STREAM_DESTROY	0x4
#define RPC_STREAM_INDIVIDUAL	0x5
#define RPC_STREAM_VOLUME	0x6
#define RPC_STREAM_ISENABLED	0x7
#define RPC_OPEN_LINK	0x8
#define RPC_TIMEOUT_CHAT 0x9
#define RPC_OPEN_SETTINGS	0x15


enum E_STREAM_SOURCE
{
	eStreamID,
	eStreamIsFree,
	Float:eStreamPos[3],
	eStreamInt,
	eStreamVirtualWorld,
	Float:eStreamDistance,
	szUrl[255]
};

static g_aStreamSources[MAX_STREAM_SOURCES][E_STREAM_SOURCE];

stock InitStreamSources()
{
	for(new i = 0; i < MAX_STREAM_SOURCES; i++)
	{
		g_aStreamSources[i][eStreamID] = -1;
		g_aStreamSources[i][eStreamIsFree] = 1;
	}
	print("[STREAM SOURCES] Initialized...");
}

stock PlayerPlayStream(playerid, url[])
{
	new BitStream:bitstream = BS_New();
	BS_WriteValue(bitstream, PR_UINT8, PACKET_CUSTOMRPC);
	BS_WriteValue(bitstream, PR_UINT32, RPC_STREAM_INDIVIDUAL);

	BS_WriteValue(bitstream, PR_UINT8, strlen(url));
	BS_WriteValue(bitstream, PR_STRING, url);

	BS_Send(bitstream, playerid);

	BS_Delete(bitstream);
}

stock CreateAllStreamSourcesForPlayer(playerid)
{
	for(new i = 0; i < MAX_STREAM_SOURCES; i++)
	{
		if(!g_aStreamSources[i][eStreamIsFree])
		{
			new BitStream:bitstream = BS_New();
			BS_WriteValue(bitstream, PR_UINT8, PACKET_CUSTOMRPC);
			BS_WriteValue(bitstream, PR_UINT32, RPC_STREAM_CREATE);

			BS_WriteValue(bitstream, PR_UINT16, g_aStreamSources[i][eStreamID]);
			BS_WriteValue(bitstream, PR_FLOAT, g_aStreamSources[i][eStreamPos][0]);
			BS_WriteValue(bitstream, PR_FLOAT, g_aStreamSources[i][eStreamPos][1]);
			BS_WriteValue(bitstream, PR_FLOAT, g_aStreamSources[i][eStreamPos][2]);
			BS_WriteValue(bitstream, PR_FLOAT, g_aStreamSources[i][eStreamDistance]);
			BS_WriteValue(bitstream, PR_UINT16, g_aStreamSources[i][eStreamInt]);
			BS_WriteValue(bitstream, PR_UINT16, g_aStreamSources[i][eStreamVirtualWorld]);
			BS_WriteValue(bitstream, PR_UINT8, strlen(g_aStreamSources[i][szUrl]));
			BS_WriteValue(bitstream, PR_STRING, g_aStreamSources[i][szUrl]);

			BS_Send(bitstream, playerid);

			BS_Delete(bitstream);
		}
	}
}

stock CreateStreamSource(Float:fPosX, Float:fPosY, Float:fPosZ, Float:fDistance, iInt, iVirtualWorld, url[])
{
	for(new i = 0; i < MAX_STREAM_SOURCES; i++)
	{
		if(g_aStreamSources[i][eStreamIsFree])
		{
			g_aStreamSources[i][eStreamID] = i;
			g_aStreamSources[i][eStreamIsFree] = 0;

			g_aStreamSources[i][eStreamPos][0] = fPosX;
			g_aStreamSources[i][eStreamPos][1] = fPosY;
			g_aStreamSources[i][eStreamPos][2] = fPosZ;

			g_aStreamSources[i][eStreamDistance] = fDistance;

			g_aStreamSources[i][eStreamInt] = iInt;
			g_aStreamSources[i][eStreamVirtualWorld] = iVirtualWorld;

			format(g_aStreamSources[i][szUrl], 255, "%s", url);

			new BitStream:bitstream = BS_New();
			BS_WriteValue(bitstream, PR_UINT8, PACKET_CUSTOMRPC);
			BS_WriteValue(bitstream, PR_UINT32, RPC_STREAM_CREATE);

			BS_WriteValue(bitstream, PR_UINT16, i);
			BS_WriteValue(bitstream, PR_FLOAT, fPosX);
			BS_WriteValue(bitstream, PR_FLOAT, fPosY);
			BS_WriteValue(bitstream, PR_FLOAT, fPosZ);
			BS_WriteValue(bitstream, PR_FLOAT, fDistance);
			BS_WriteValue(bitstream, PR_UINT16, iInt);
			BS_WriteValue(bitstream, PR_UINT16, iVirtualWorld);
			BS_WriteValue(bitstream, PR_UINT8, strlen(url));
			BS_WriteValue(bitstream, PR_STRING, url);

			BS_Send(bitstream, -1);

			BS_Delete(bitstream);

			return i;
		}
	}
	return -1;
}

stock SetStreamPos(iID, Float:fPosX, Float:fPosY, Float:fPosZ)
{
	g_aStreamSources[iID][eStreamPos][0] = fPosX;
	g_aStreamSources[iID][eStreamPos][1] = fPosY;
	g_aStreamSources[iID][eStreamPos][2] = fPosZ;

	SendCustomRPC_Float(-1, RPC_STREAM_POS, fPosX, fPosY, fPosZ);
}

stock DestroyStreamSource(iID)
{
	g_aStreamSources[iID][eStreamIsFree] = 1;
	SendCustomRPC(-1, RPC_STREAM_DESTROY, iID);
}

stock SetStreamSourceVolume(iID, Float:fVolume)
{
	new BitStream:bitstream = BS_New();
	BS_WriteValue(bitstream, PR_UINT8, PACKET_CUSTOMRPC);
	BS_WriteValue(bitstream, PR_UINT32, RPC_STREAM_VOLUME);

	BS_WriteValue(bitstream, PR_UINT16, iID);
	BS_WriteValue(bitstream, PR_FLOAT, fVolume);

	BS_Send(bitstream, -1);

	BS_Delete(bitstream);
}

stock SetStreamEnabledForPlayer(playerid, isEnabled)
{
	SendCustomRPC(playerid, RPC_STREAM_ISENABLED, isEnabled);
}

stock SetTimeoutChatDissappearTime(playerid, startTime, endTime)
{
	SendCustomRPC(playerid, RPC_TIMEOUT_CHAT, startTime, endTime);
}

stock ShowPlayerSettingsClient(playerid)
{
	SendCustomRPC(playerid, RPC_OPEN_SETTINGS);
}

stock OpenLinkForPlayer(playerid, const szLink[])
{
    new BitStream:bitstream = BS_New();
    BS_WriteValue(bitstream, PR_UINT8, PACKET_CUSTOMRPC);
    BS_WriteValue(bitstream, PR_UINT32, RPC_OPEN_LINK);

    BS_WriteValue(bitstream, PR_UINT16, strlen(szLink));
    BS_WriteValue(bitstream, PR_STRING, szLink);

    BS_Send(bitstream, playerid);

    BS_Delete(bitstream);
}

stock SendCustomRPC(playerid, rpcid, ...)
{
    new BitStream:bitstream = BS_New();
    BS_WriteValue(bitstream, PR_UINT8, PACKET_CUSTOMRPC);
	BS_WriteValue(bitstream, PR_UINT32, rpcid);
    for (new i = 0; i < numargs()-2; ++i)
    {
        BS_WriteValue(bitstream, PR_UINT32, getarg(i+2));
    }

    PR_SendPacket(bitstream, playerid);

	BS_Delete(bitstream);
}

stock SendCustomRPC_Float(playerid, rpcid, ...)
{
    new BitStream:bitstream = BS_New();
    BS_WriteValue(bitstream, PR_UINT8, PACKET_CUSTOMRPC);
	BS_WriteValue(bitstream, PR_UINT32, rpcid);
    for (new i = 0; i < numargs()-2; ++i)
    {
        BS_WriteValue(bitstream, PR_FLOAT, getarg(i+2));
    }

    BS_Send(bitstream, playerid);

	BS_Delete(bitstream);
}

stock TogglePlayerHudElement(playerid, hudid, value)
{
    SendCustomRPC(playerid, CUSTOM_RPC_TOGGLE_HUD_ELEMENT, hudid, value);
}

stock TogglePlayerAllHudElements(playerid, value)
{
	for(new i = 0; i < 7; i++)
	{
		SendCustomRPC(playerid, CUSTOM_RPC_TOGGLE_HUD_ELEMENT, i, value);
	}
}

cmd:hudoff(playerid, params[])
{
    TogglePlayerAllHudElements(playerid, 0);
    return 1;
}

cmd:hudon(playerid, params[])
{
    TogglePlayerAllHudElements(playerid, 1);
    return 1;
}

/*
cmd:hud(playerid, params[])
{
    TogglePlayerAllHudElements(playerid, strval(params));
    return 1;
}
cmd:cv(playerid, params[])
{
    if(sscanf(params, "ii", params[0], params[1])) return SendClientMessage(playerid, -1, "Используйте: /cv 100 100");
    SetTimeoutChatDissappearTime(playerid, params[0], params[1]);
    return 1;
}
*/

