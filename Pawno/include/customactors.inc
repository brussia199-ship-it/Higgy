#include <foreach>

/*

SetActorPos - не работает когда актёр помещён в авто
Обязательно надо проверять ид актёра на валидность перед использованием функций (IsActorValid)

* puts actor in vehicle (seat = seat in PutPlayerInVehicle)
stock PutActorInVehicle(actorid, vehicleid, seat)

* returns INVALID_VEHICLE_ID if actor is not in vehicle
stock GetActorVehicleID(actorid)

* removes actor from vehicle
stock RemoveActorFromVehicle(actorid)

* использует перехваты:
OnGameModeInit
OnActorStreamIn
OnActorStreamOut
OnPlayerUpdate
ORPC
CreateActor

* использует итераторы:
g_itStreamedPlayers

*/

#define CUSTOM_ACTOR_VERSION	0x1

#define RPC_CUSTOM_ACTOR_PUT_IN_VEH	0x20
#define RPC_CUSTOM_ACTOR_REMOVE_VEH	0x21
#define RPC_CUSTOM_ACTOR_ADD_ADDITIONAL	0x22

static Iterator:g_itStreamedPlayers[MAX_ACTORS]<MAX_PLAYERS>;

enum E_ACTOR_ADDITIONAL
{
	actVehicleID,
	actSeat
};

static g_iActorAdditionalInfo[MAX_ACTORS][E_ACTOR_ADDITIONAL];

public OnGameModeInit()
{
	printf("[Custom actors] Custom actors %d version initialized", CUSTOM_ACTOR_VERSION);
	Iter_Init(g_itStreamedPlayers);
	
#if	defined	cact__OnGameModeInit
	cact__OnGameModeInit();
#endif
}

#if defined _ALS_OnGameModeInit
	#undef	OnGameModeInit
#else
	#define	_ALS_OnGameModeInit
#endif
#if	defined	cact__OnGameModeInit
forward cact__OnGameModeInit();
#endif
#define	OnGameModeInit	cact__OnGameModeInit

public OnActorStreamIn(actorid, forplayerid)
{
    Iter_Add(g_itStreamedPlayers[actorid], forplayerid);
	
	#if defined debug_mode
	printf("[Custom actors] Added to iter playerid %d actorid %d | veh: %d, seat: %d", forplayerid, actorid, g_iActorAdditionalInfo[actorid][actVehicleID], g_iActorAdditionalInfo[actorid][actSeat]);
	#endif
	
	if(g_iActorAdditionalInfo[actorid][actVehicleID] != INVALID_VEHICLE_ID)
	{
	    new BitStream:bitstream = BS_New();
		BS_WriteValue(bitstream, PR_UINT8, PACKET_CUSTOMRPC);
		BS_WriteValue(bitstream, PR_UINT32, RPC_CUSTOM_ACTOR_ADD_ADDITIONAL);
		BS_WriteValue(bitstream, PR_UINT16, actorid);
		BS_WriteValue(bitstream, PR_UINT16, g_iActorAdditionalInfo[actorid][actVehicleID]);
		BS_WriteValue(bitstream, PR_UINT8, g_iActorAdditionalInfo[actorid][actSeat]);

		BS_Send(bitstream, forplayerid, PR_HIGH_PRIORITY, PR_RELIABLE_SEQUENCED);

		BS_Delete(bitstream);

		#if defined debug_mode
		printf("[Custom actors] Send RPC to %d playerid with actorid %d | veh: %d, seat: %d", forplayerid, actorid, g_iActorAdditionalInfo[actorid][actVehicleID], g_iActorAdditionalInfo[actorid][actSeat]);
		#endif
	}
	
#if defined cact__OnActorStreamIn
    return cact__OnActorStreamIn(actorid, forplayerid);
#endif
}

#if defined _ALS_OnActorStreamIn
    #undef    OnActorStreamIn
#else
    #define    _ALS_OnActorStreamIn
#endif
#define    OnActorStreamIn    cact__OnActorStreamIn
#if defined cact__OnActorStreamIn
forward cact__OnActorStreamIn(actorid, forplayerid);
#endif 

public OnActorStreamOut(actorid, forplayerid)
{
    Iter_Remove(g_itStreamedPlayers[actorid], forplayerid);
	
	#if defined debug_mode
	printf("[Custom actors] Removed from iterator %d %d", actorid, forplayerid);
	#endif
	
#if defined cact__OnActorStreamOut
    return cact__OnActorStreamOut(actorid, forplayerid);
#endif
}

#if defined _ALS_OnActorStreamOut
    #undef    OnActorStreamOut
#else
    #define    _ALS_OnActorStreamOut
#endif
#define    OnActorStreamOut    cact__OnActorStreamOut
#if defined cact__OnActorStreamOut
forward cact__OnActorStreamOut(actorid, forplayerid);
#endif

static g_TimeStart;
public OnPlayerUpdate(playerid)
{
	if(GetTickCount() - g_TimeStart >= 20)
	{
		for(new i = 0; i < MAX_ACTORS; i++)
		{
			if(IsValidActor(i))
			{
				if(g_iActorAdditionalInfo[i][actVehicleID] != INVALID_VEHICLE_ID)
				{
					new Float:pos[3];
					GetVehiclePos(g_iActorAdditionalInfo[i][actVehicleID], pos[0], pos[1], pos[2]);
					SetActorPos(i, pos[0], pos[1], pos[2]);
					
					#if defined debug_mode
					printf("[Custom actors] Set pos for %d %f %f %f", i, pos[0], pos[1], pos[2]);
					#endif
					
				}
			}
		}
		g_TimeStart = GetTickCount();
	}
	
#if defined cact__OnPlayerUpdate
    return cact__OnPlayerUpdate(playerid);
#endif
}

#if defined _ALS_OnPlayerUpdate
    #undef    OnPlayerUpdate
#else
    #define    _ALS_OnPlayerUpdate
#endif
#define    OnPlayerUpdate    cact__OnPlayerUpdate
#if defined cact__OnPlayerUpdate
forward cact__OnPlayerUpdate(playerid);
#endif

const RPC_SetActorPos = 176;

ORPC:RPC_SetActorPos(playerid, BitStream:bs)
{
	new actorid;
	BS_ReadUint16(bs, actorid);
	if(IsValidActor(actorid))
	{
		if(g_iActorAdditionalInfo[actorid][actVehicleID] != INVALID_VEHICLE_ID)
		{
			#if defined debug_mode
			printf("[Custom actors] Packet not send for %d %d", actorid, g_iActorAdditionalInfo[actorid][actVehicleID]);
			#endif
			return 0;
		}
	}
	return 1;
}

stock cact_CreateActor(modelid, Float:X, Float:Y, Float:Z, Float:Rotation)
{
    new actorid = CreateActor(modelid, X, Y, Z, Rotation);
	
	if(actorid == INVALID_ACTOR_ID)
	{
	    #if defined debug_mode
		printf("[Custom actors] Created actor %d | veh: %d", actorid, g_iActorAdditionalInfo[actorid][actVehicleID]);
		#endif
	    return actorid;
	}
	
	g_iActorAdditionalInfo[actorid][actVehicleID] = INVALID_VEHICLE_ID;
	g_iActorAdditionalInfo[actorid][actSeat] = 0;
	
	#if defined debug_mode
	printf("[Custom actors] Created actor %d | veh: %d", actorid, g_iActorAdditionalInfo[actorid][actVehicleID]);
	#endif
	
	return actorid;
}

#if defined _ALS_CreateActor
    #undef    CreateActor
#else
    #define    _ALS_CreateActor
#endif
#define    CreateActor    cact_CreateActor  

// puts actor in vehicle (seat = seat in PutPlayerInVehicle)
stock PutActorInVehicle(actorid, vehicleid, seat)
{
	g_iActorAdditionalInfo[actorid][actVehicleID] = vehicleid;
	g_iActorAdditionalInfo[actorid][actSeat] = seat;

	new BitStream:bitstream = BS_New();
	BS_WriteValue(bitstream, PR_UINT8, PACKET_CUSTOMRPC);
	BS_WriteValue(bitstream, PR_UINT32, RPC_CUSTOM_ACTOR_PUT_IN_VEH);
	BS_WriteValue(bitstream, PR_UINT16, actorid);
	BS_WriteValue(bitstream, PR_UINT16, g_iActorAdditionalInfo[actorid][actVehicleID]);
	BS_WriteValue(bitstream, PR_UINT8, g_iActorAdditionalInfo[actorid][actSeat]);
	
	foreach(new i : g_itStreamedPlayers[actorid])
	{
		BS_Send(bitstream, i, PR_HIGH_PRIORITY, PR_RELIABLE_SEQUENCED);
		
		#if defined debug_mode
		printf("[Custom actors] PutActorInVehicle Sended to %d", i);
		#endif
	}

	#if defined debug_mode
	printf("[Custom actors] PutActorInVehicle %d | veh: %d, seat %d", actorid, g_iActorAdditionalInfo[actorid][actVehicleID], g_iActorAdditionalInfo[actorid][actSeat]);
	#endif

	BS_Delete(bitstream);
}

// removes actor from vehicle
stock RemoveActorFromVehicle(actorid)
{
	g_iActorAdditionalInfo[actorid][actVehicleID] = INVALID_VEHICLE_ID;
	g_iActorAdditionalInfo[actorid][actSeat] = 0;

	new BitStream:bitstream = BS_New();
	BS_WriteValue(bitstream, PR_UINT8, PACKET_CUSTOMRPC);
	BS_WriteValue(bitstream, PR_UINT32, RPC_CUSTOM_ACTOR_REMOVE_VEH);
	BS_WriteValue(bitstream, PR_UINT16, actorid);
	
	foreach(new i : g_itStreamedPlayers[actorid])
	{
		BS_Send(bitstream, i, PR_HIGH_PRIORITY, PR_RELIABLE_SEQUENCED);
		
		#if defined debug_mode
		printf("[Custom actors] RemoveActorFromVehicle Sended to %d", i);
		#endif
	}
	
	#if defined debug_mode
	printf("[Custom actors] RemoveActorFromVehicle %d | veh: %d, seat: %d", actorid, g_iActorAdditionalInfo[actorid][actVehicleID], g_iActorAdditionalInfo[actorid][actSeat]);
	#endif
	
	BS_Delete(bitstream);
}

// returns INVALID_VEHICLE_ID if actor is not in vehicle
stock GetActorVehicleID(actorid)
{
	#if defined debug_mode
	printf("[Custom actors] GetActorVehicleID %d | veh: %d, seat: %d", actorid, g_iActorAdditionalInfo[actorid][actVehicleID], g_iActorAdditionalInfo[actorid][actSeat]);
	#endif
	return g_iActorAdditionalInfo[actorid][actVehicleID];
}
