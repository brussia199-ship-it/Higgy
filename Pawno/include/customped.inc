#define CUSTOM_PED_VERSION	0x3

enum E_CUSTOM_PED
{
	pedMoveAnim
};

#define PED_ANIM_DEFAULT	0

#define RPC_CUSTOM_ADD_PED			0x12

static g_PedCustomInfo[MAX_PLAYERS][E_CUSTOM_PED];

stock cp_OnPlayerConnect(playerid)
{
	g_PedCustomInfo[playerid][pedMoveAnim] = PED_ANIM_DEFAULT;
}

stock cp_OnPlayerStreamIn(playerid, forplayerid)
{
	SendCustomPedAddData(playerid, forplayerid);
}

stock SetPlayerMoveAnim(playerid, anim)
{
	g_PedCustomInfo[playerid][pedMoveAnim] = anim;
	
	SendCustomPedAddData(playerid, playerid);
	
	foreach(new i : streamed_players[playerid])
	{
		SendCustomPedAddData(playerid, i);
	}
}

stock SendCustomPedAddData(playerid, toplayerid)
{
	new BitStream:bitstream = BS_New();
	
	BS_WriteValue(bitstream, PR_UINT8, PACKET_CUSTOMRPC);
	BS_WriteValue(bitstream, PR_UINT32, RPC_CUSTOM_ADD_PED);
	BS_WriteValue(bitstream, PR_UINT16, playerid);
	
	BS_WriteValue(bitstream, PR_UINT8, g_PedCustomInfo[playerid][pedMoveAnim]);
	
	BS_Send(bitstream, toplayerid, PR_HIGH_PRIORITY, PR_RELIABLE_ORDERED);
	BS_Delete(bitstream);
}
