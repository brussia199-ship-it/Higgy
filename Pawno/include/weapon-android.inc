/*
	About: Weapons in the SA:MP Android
	Author: urKrass (Evgeniy Malik)
*/

#if !defined _samp_included
	#error "Please include a_samp or a_npc before weapon-android"
#endif

#if !defined COLANDREAS_VERSION
	#error "You must have ColAndreas include in order to use this one."
#endif

#if !defined _FOREACH_LOCAL_VERSION
	#error "You must have foreach include in order to use this one."
#endif

#if defined _weapon_android_included_
	#endinput
#endif
#define _weapon_android_included_

/*
	Forwards
*/

forward a_OnPlayerWeaponTimer(playerid);
forward a_OnVehicleWeaponTimer(vehicleid);

/*
	Define const
*/

#if !defined MAX_WEAPON_SKILL
	#define MAX_WEAPON_SKILL 13
#endif

#if !defined MAX_WEAPON_SLOT
	#define MAX_WEAPON_SLOT 13
#endif

#if !defined USING_WEAPON_SELECT
	#if !defined MAX_WEAPON_NAME
		#define MAX_WEAPON_NAME 18
	#endif
#endif

#if !defined WEAPON_FIST
	#define WEAPON_FIST 0
#endif

#if !defined USING_WEAPON_SELECT
	#if !defined WEAPON_DIALOG_ID
		#define WEAPON_DIALOG_ID 12546
	#endif
#endif

/*
	Define functions
*/

#define HOLDING(%0) \
	((newkeys & (%0)) == (%0))

#define PRESSED(%0) \
	(((newkeys & (%0)) == (%0)) && ((oldkeys & (%0)) != (%0)))

#define RELEASED(%0) \
	(((newkeys & (%0)) != (%0)) && ((oldkeys & (%0)) == (%0)))

#define CompRotationFloat360(%0) \
	%0 += (floatcmp(%0, 360.0) >= 0) ? (-360.0) : ((floatcmp(%0, 0.0) == -1) ? (360.0) : (0.0))

#define CompDamageGenerator(%0,%1,%2) \
	%0 = (floatcmp(%1, %2) >= 0) ? (floatsub(%0, floatsub(%1, %2))) : ((floatcmp(%1, %2) == -1) ? (floatsub(%0, floatsub(%2, %1))) : (%0))

/*
	Vars
*/

new
	p_slot[MAX_PLAYERS],
	p_skill[MAX_PLAYERS][MAX_WEAPON_SKILL],
	p_weapon[MAX_PLAYERS][MAX_WEAPON_SLOT],
	p_ammo[MAX_PLAYERS][MAX_WEAPON_SLOT],
	p_jump_tick[MAX_PLAYERS],
	p_object_weapon[MAX_PLAYERS],
	p_shot_timer[MAX_PLAYERS];

static
	p_deatch_tick[MAX_PLAYERS];

#if defined USING_DAMAGE_VEHICLE
static
	v_deatch_timer[MAX_VEHICLES];
#endif

#if !defined USING_WEAPON_SELECT
static
	gPlayerWeaponSlot[MAX_PLAYERS][MAX_WEAPON_SLOT],
	gPlayerWeaponAmount[MAX_PLAYERS char];
#endif

static const
	s_WEAPON_Slot[] = {
    0, 0,
    1, 1, 1, 1, 1, 1, 1, 1,
    10, 10, 10, 10, 10, 10,
    8, 8, 8,
    0, 0, 0,
    2, 2, 2,
    3, 3, 3,
    4, 4,
    5, 5,
    4,
    6, 6,
    7, 7, 7, 7,
    8,
    12,
    9, 9, 9,
    11, 11, 11
};

static const
	s_WEAPON_Modelid[] = {
	0, // 0 - Fist
	331, // 1 - Brass knuckles
	333, // 2 - Golf club
	334, // 3 - Nitestick
	335, // 4 - Knife
	336, // 5 - Bat
	337, // 6 - Shovel
	338, // 7 - Pool cue
	339, // 8 - Katana
	341, // 9 - Chainsaw
	321, // 10 - Dildo
	322, // 11 - Dildo 2
	323, // 12 - Vibrator
	324, // 13 - Vibrator 2
	325, // 14 - Flowers
	326, // 15 - Cane
	342, // 16 - Grenade
	343, // 17 - Teargas
	344, // 18 - Molotov
	0, // 19 - Vehicle M4 (custom)
	0, // 20 - Vehicle minigun (custom)
	0, // 21
	346, // 22 - Colt 45
	347, // 23 - Silenced
	348, // 24 - Deagle
	349, // 25 - Shotgun
	350, // 26 - Sawed-off
	351, // 27 - Spas
	352, // 28 - UZI
	353, // 29 - MP5
	355, // 30 - AK47
	356, // 31 - M4
	372, // 32 - Tec9
	357, // 33 - Cuntgun
	358, // 34 - Sniper
	359, // 35 - Rocket launcher
	360, // 36 - Heatseeker
	361, // 37 - Flamethrower
	362, // 38 - Minigun
	363, // 39 - Satchel
	364, // 40 - Detonator
	365, // 41 - Spraycan
	366, // 42 - Fire extinguisher
	367, // 43 - Camera
	368, // 44 - Night vision
	369, // 45 - Infrared
	371, // 46 - Parachute
	0, // 47 - Fake pistol
	370, // 48 - Pistol whip (custom)
	0, // 49 - Vehicle
	0, // 50 - Helicopter blades
	0, // 51 - Explosion
	0, // 52 - Car park (custom)
	0, // 53 - Drowning
	0 // 54 - Splat
};

static const
	Float:s_WeaponDamage[] = {
	1.0, // 0 - Fist
	1.0, // 1 - Brass knuckles
	1.0, // 2 - Golf club
	1.0, // 3 - Nitestick
	1.0, // 4 - Knife
	1.0, // 5 - Bat
	1.0, // 6 - Shovel
	1.0, // 7 - Pool cue
	1.0, // 8 - Katana
	1.0, // 9 - Chainsaw
	1.0, // 10 - Dildo
	1.0, // 11 - Dildo 2
	1.0, // 12 - Vibrator
	1.0, // 13 - Vibrator 2
	1.0, // 14 - Flowers
	1.0, // 15 - Cane
	82.5, // 16 - Grenade
	0.0, // 17 - Teargas
	1.0, // 18 - Molotov
	9.9, // 19 - Vehicle M4 (custom)
	46.2, // 20 - Vehicle minigun (custom)
	0.0, // 21
	17.0, // 22 - Colt 45 //-22.0
	25.0, // 23 - Silenced //-40.0
	50.0, // 24 - Deagle //-70.0
	30.0, // 25 - Shotgun //-10.0
	50.0, // 26 - Sawed-off //-10.0
	60.0, // 27 - Spas //-15.0
	20.0, // 28 - UZI //6.6
	30.0, // 29 - MP5 //8.25
	25.0, // 30 - AK47 //9.9
	30.0, // 31 - M4 //9.9
	20.0, // 32 - Tec9 //6.6
	70.0, // 33 - Cuntgun //24.75
	80.0, // 34 - Sniper //41.25
	82.5, // 35 - Rocket launcher
	82.5, // 36 - Heatseeker
	1.0, // 37 - Flamethrower
	46.2, // 38 - Minigun
	82.5, // 39 - Satchel
	0.0, // 40 - Detonator
	0.33, // 41 - Spraycan
	0.33, // 42 - Fire extinguisher
	0.0, // 43 - Camera
	0.0, // 44 - Night vision
	0.0, // 45 - Infrared
	0.0, // 46 - Parachute
	0.0, // 47 - Fake pistol
	2.64, // 48 - Pistol whip (custom)
	9.9, // 49 - Vehicle
	330.0, // 50 - Helicopter blades
	82.5, // 51 - Explosion
	1.0, // 52 - Car park (custom)
	1.0, // 53 - Drowning
	165.0  // 54 - Splat
};

static const
	Float:s_WeaponRange[] = {
	0.0, // 0 - Fist
	0.0, // 1 - Brass knuckles
	0.0, // 2 - Golf club
	0.0, // 3 - Nitestick
	0.0, // 4 - Knife
	0.0, // 5 - Bat
	0.0, // 6 - Shovel
	0.0, // 7 - Pool cue
	0.0, // 8 - Katana
	0.0, // 9 - Chainsaw
	0.0, // 10 - Dildo
	0.0, // 11 - Dildo 2
	0.0, // 12 - Vibrator
	0.0, // 13 - Vibrator 2
	0.0, // 14 - Flowers
	0.0, // 15 - Cane
	0.0, // 16 - Grenade
	0.0, // 17 - Teargas
	0.0, // 18 - Molotov
	90.0, // 19 - Vehicle M4 (custom)
	75.0, // 20 - Vehicle minigun (custom)
	0.0, // 21
	35.0, // 22 - Colt 45
	35.0, // 23 - Silenced
	35.0, // 24 - Deagle
	40.0, // 25 - Shotgun
	35.0, // 26 - Sawed-off
	40.0, // 27 - Spas
	35.0, // 28 - UZI
	45.0, // 29 - MP5
	70.0, // 30 - AK47
	90.0, // 31 - M4
	35.0, // 32 - Tec9
	100.0, // 33 - Cuntgun
	320.0, // 34 - Sniper
	0.0, // 35 - Rocket launcher
	0.0, // 36 - Heatseeker
	0.0, // 37 - Flamethrower
	75.0  // 38 - Minigun
};

static const
	s_WeaponShootRate[] = {
	250, // 0 - Fist
	250, // 1 - Brass knuckles
	250, // 2 - Golf club
	250, // 3 - Nitestick
	250, // 4 - Knife
	250, // 5 - Bat
	250, // 6 - Shovel
	250, // 7 - Pool cue
	250, // 8 - Katana
	30, // 9 - Chainsaw
	250, // 10 - Dildo
	250, // 11 - Dildo 2
	250, // 12 - Vibrator
	250, // 13 - Vibrator 2
	250, // 14 - Flowers
	250, // 15 - Cane
	0, // 16 - Grenade
	0, // 17 - Teargas
	0, // 18 - Molotov
	20, // 19 - Vehicle M4 (custom)
	20, // 20 - Vehicle minigun (custom)
	0, // 21
	0, // 22 - Colt 45 //160
	500, // 23 - Silenced //120
	1_000, // 24 - Deagle //120
	500, // 25 - Shotgun //800
	800, // 26 - Sawed-off //120
	1_000, // 27 - Spas //120
	200, // 28 - UZI //50
	500, // 29 - MP5 //90
	0, // 30 - AK47 //90
	0, // 31 - M4 //90
	500, // 32 - Tec9 //70
	2_000, // 33 - Cuntgun //800
	2_500, // 34 - Sniper //900
	0, // 35 - Rocket launcher
	0, // 36 - Heatseeker
	0, // 37 - Flamethrower
	20, // 38 - Minigun
	0, // 39 - Satchel
	0, // 40 - Detonator
	10, // 41 - Spraycan
	10, // 42 - Fire extinguisher
	0, // 43 - Camera
	0, // 44 - Night vision
	0, // 45 - Infrared
	0, // 46 - Parachute
	0, // 47 - Fake pistol
	400 // 48 - Pistol whip (custom)
};

/*
	GetZAngleToPoint
*/

stock Float:GetZAngleToPoint(Float:start_x, Float:start_y, Float:end_x, Float:end_y, &Float:rot_z = 0.0)
{
	rot_z = floatsub(180.0, atan2(floatsub(start_x, end_x), floatsub(start_y, end_y)));
	return CompRotationFloat360(rot_z);
}

/*
	SetPlayerAmmo
*/

stock a_SetPlayerAmmo(playerid, weaponid, ammo)
{
	if (!(WEAPON_COLT45 <= weaponid <= WEAPON_SNIPER)) {
		return 0;
	}
	if (p_weapon[playerid][s_WEAPON_Slot[weaponid]] == 0) {
		return 0;
	}
	p_ammo[playerid][s_WEAPON_Slot[weaponid]] = ammo;
	return 1;
}

/*
	GetPlayerAmmo
*/

stock a_GetPlayerAmmo(playerid)
{
	return p_ammo[playerid][p_slot[playerid]];
}

/*
	GivePlayerWeapon
*/

stock a_GivePlayerWeapon(playerid, weaponid, ammo)
{
	if (!(WEAPON_COLT45 <= weaponid <= WEAPON_SNIPER)) {
		return 0;
	}
	new
		slot = p_slot[playerid] = s_WEAPON_Slot[weaponid];
	if (p_weapon[playerid][slot] != weaponid) {
		p_weapon[playerid][slot] = weaponid;
		p_ammo[playerid][slot] = ammo;
	} else {
		p_ammo[playerid][slot] += ammo;
	}
	return 1;
}

/*
	ResetPlayerWeapons
*/

stock a_ResetPlayerWeapons(playerid)
{
	p_slot[playerid] = 0;
	for (new i; i < MAX_WEAPON_SLOT; i++) {
		p_weapon[playerid][i] =
		p_ammo[playerid][i] = 0;
	}
}

/*
	SetPlayerArmedWeapon
*/

stock a_SetPlayerArmedWeapon(playerid, weaponid)
{
	if (!(weaponid == WEAPON_FIST && WEAPON_COLT45 <= weaponid <= WEAPON_SNIPER)) {
		return 0;
	}
	if (s_WEAPON_Slot[weaponid] != 0 && p_weapon[playerid][s_WEAPON_Slot[weaponid]] == 0) {
		return 0;
	}
	p_slot[playerid] = s_WEAPON_Slot[weaponid];
	return 1;
}

/*
	GetPlayerWeaponData
*/

stock a_GetPlayerWeaponData(playerid, slot, &weapons, &ammo)
{
	if (!(0 <= slot <= MAX_WEAPON_SLOT-1)) {
		return 0;
	}
	weapons = p_weapon[playerid][slot];
	ammo = p_ammo[playerid][slot];
	return 1;
}

/*
	GetPlayerWeapon
*/

stock a_GetPlayerWeapon(playerid)
{
	return p_weapon[playerid][p_slot[playerid]];
}

/*
	SetPlayerSkillLevel
*/

stock a_SetPlayerSkillLevel(playerid, skill, level)
{
	if (!(WEAPONSKILL_PISTOL <= skill <= WEAPONSKILL_SNIPERRIFLE)) {
		return 0;
	}
	if (level >= 999) {
		p_skill[playerid][skill] = 3;
	} else if (level >= 200) {
		p_skill[playerid][skill] = 2;
	} else if (level >= 0) {
		p_skill[playerid][skill] = 1;
	}
	return 1;
}

/*
	ApplyAnimation
*/

stock a_ApplyAnimation(playerid, animlib[], animname[], Float:fDelta, loop, lockx, locky, freeze, time, forcesync = 0)
{
	if (p_shot_timer[playerid] != 0) {
		return 1;
	}
	return ApplyAnimation(playerid, animlib, animname, fDelta, loop, lockx, locky, freeze, time, forcesync);
}

#if defined _ALS_ApplyAnimation
	#undef ApplyAnimation
#else
	#define _ALS_ApplyAnimation
#endif
#define ApplyAnimation a_ApplyAnimation

/*
	ClearAnimations
*/

stock a_ClearAnimations(playerid, forcesync = 0)
{
	if (p_shot_timer[playerid] != 0) {
		return 1;
	}
	return ClearAnimations(playerid, forcesync);
}

#if defined _ALS_ClearAnimations
	#undef ClearAnimations
#else
	#define _ALS_ClearAnimations
#endif
#define ClearAnimations a_ClearAnimations

#if defined USING_DAMAGE_VEHICLE

/*
	DestroyVehicle
*/

stock a_DestroyVehicle(vehicleid)
{
	if (v_deatch_timer[vehicleid] != 0) {
		KillTimer(v_deatch_timer[vehicleid]);
		v_deatch_timer[vehicleid] = 0;
	}
	return DestroyVehicle(vehicleid);
}

#if defined _ALS_DestroyVehicle
	#undef DestroyVehicle
#else
	#define _ALS_DestroyVehicle
#endif
#define DestroyVehicle a_DestroyVehicle

#endif

/*
	OnPlayerConnect
*/

public OnPlayerConnect(playerid)
{
	for (new i; i < MAX_WEAPON_SKILL; i++) {
		p_skill[playerid][i] = 1;
	}
	for (new i; i < MAX_WEAPON_SLOT; i++) {
		p_weapon[playerid][i] =
		p_ammo[playerid][i] = 0;
	}

	#if defined a_OnPlayerConnect
		return a_OnPlayerConnect(playerid);
	#else
		return 1;
	#endif
}

#if defined _ALS_OnPlayerConnect
	#undef OnPlayerConnect
#else
	#define _ALS_OnPlayerConnect
#endif
#define OnPlayerConnect a_OnPlayerConnect
#if defined a_OnPlayerConnect
	forward a_OnPlayerConnect(playerid);
#endif

/*
	OnPlayerDisconnect
*/

public OnPlayerDisconnect(playerid, reason)
{
	p_slot[playerid] = 0;
	if(p_object_weapon[playerid] != 0) {
		DestroyDynamicObject(p_object_weapon[playerid]);
		p_object_weapon[playerid] = 0;
	}
	if (p_shot_timer[playerid] != 0) {
		KillTimer(p_shot_timer[playerid]);
		p_shot_timer[playerid] = 0;
	}
	ClearAnimations(playerid);

	#if defined a_OnPlayerDisconnect
		return a_OnPlayerDisconnect(playerid, reason);
	#else
		return 1;
	#endif
}

#if defined _ALS_OnPlayerDisconnect
	#undef OnPlayerDisconnect
#else
	#define _ALS_OnPlayerDisconnect
#endif
#define OnPlayerDisconnect a_OnPlayerDisconnect
#if defined a_OnPlayerDisconnect
	forward a_OnPlayerDisconnect(playerid, reason);
#endif

/*
	OnPlayerSpawn
*/

public OnPlayerSpawn(playerid)
{
	p_slot[playerid] = 0;
	if(p_object_weapon[playerid] != 0) {
		DestroyDynamicObject(p_object_weapon[playerid]);
		p_object_weapon[playerid] = 0;
	}
	if (p_shot_timer[playerid] != 0) {
		KillTimer(p_shot_timer[playerid]);
		p_shot_timer[playerid] = 0;
	}
	ClearAnimations(playerid);

	#if defined a_OnPlayerSpawn
		return a_OnPlayerSpawn(playerid);
	#else
		return 1;
	#endif
}

#if defined _ALS_OnPlayerSpawn
	#undef OnPlayerSpawn
#else
	#define _ALS_OnPlayerSpawn
#endif
#define OnPlayerSpawn a_OnPlayerSpawn
#if defined a_OnPlayerSpawn
	forward a_OnPlayerSpawn(playerid);
#endif

/*
	OnPlayerKeyStateChange
*/

public OnPlayerKeyStateChange(playerid, newkeys, oldkeys)
{
	if (PRESSED(KEY_FIRE)) {
		if (GetPlayerInterior(playerid) == 0) {
			if (GetPlayerState(playerid) == PLAYER_STATE_ONFOOT) {
				a_OnPlayerBeganToDealDamage(playerid);
			}
		}
	} else if (PRESSED(KEY_JUMP)) {
		if (GetPlayerInterior(playerid) == 0) {
			if (GetPlayerState(playerid) == PLAYER_STATE_ONFOOT) {
				p_jump_tick[playerid] = GetTickCount()+1000;
			}
		}
	}

	#if defined a_OnPlayerKeyStateChange
		return a_OnPlayerKeyStateChange(playerid, newkeys, oldkeys);
	#else
		return 1;
	#endif
}

#if defined _ALS_OnPlayerKeyStateChange
	#undef OnPlayerKeyStateChange
#else
	#define _ALS_OnPlayerKeyStateChange
#endif
#define OnPlayerKeyStateChange a_OnPlayerKeyStateChange
#if defined a_OnPlayerKeyStateChange
	forward a_OnPlayerKeyStateChange(playerid, newkeys, oldkeys);
#endif

#if !defined USING_WEAPON_SELECT

/*
	OnPlayerCommandText
*/

public OnPlayerCommandText(playerid, cmdtext[])
{
	if (!strcmp(cmdtext, "/weapon", true) || !strcmp(cmdtext, "/slot", true)) {
		new
			l = 1,
			weapon, ammo,
			string[((MAX_WEAPON_NAME * MAX_WEAPON_SLOT) +  64) + 1] = "1. Fist\n",
			weapon_name[MAX_WEAPON_NAME + 1];
		for (new i = 1; i < MAX_WEAPON_SLOT; i++) {
			weapon = p_weapon[playerid][i];
			if (weapon != 0) {
				ammo = p_ammo[playerid][i];
				GetWeaponName(weapon, weapon_name, MAX_WEAPON_NAME);
				gPlayerWeaponSlot[playerid][l] = weapon;
				if (ammo != 0) {
					format(string, sizeof(string), "%s%i. %s (%i)\n", string, ++l, weapon_name, ammo);
				} else {
					format(string, sizeof(string), "%s%i. %s\n", string, ++l, weapon_name);
				}
			}
		}
		gPlayerWeaponAmount{playerid} = l;
		ShowPlayerDialog(playerid, WEAPON_DIALOG_ID, DIALOG_STYLE_INPUT, !"Choose weapons", string, !"Select", !"Close");
		return 1;
	}

	#if defined a_OnPlayerCommandText
		return a_OnPlayerCommandText(playerid, cmdtext);
	#else
		return 0;
	#endif
}

#if defined _ALS_OnPlayerCommandText
	#undef OnPlayerCommandText
#else
	#define _ALS_OnPlayerCommandText
#endif
#define OnPlayerCommandText a_OnPlayerCommandText
#if defined a_OnPlayerCommandText
	forward a_OnPlayerCommandText(playerid, cmdtext[]);
#endif

#endif

#if !defined USING_WEAPON_SELECT

/*
	OnDialogResponse
*/

public OnDialogResponse(playerid, dialogid, response, listitem, inputtext[])
{
	if (dialogid == WEAPON_DIALOG_ID) {
		if (response) {
			new
				fix_listitem = strval(inputtext)-1;
			if (!(0 <= fix_listitem <= gPlayerWeaponAmount{playerid}-1)) {
				return 1;
			}
			new
				slot = s_WEAPON_Slot[gPlayerWeaponSlot[playerid][fix_listitem]];
			if ((p_ammo[playerid][slot] == 0) && (fix_listitem != 0)) {
				return 1;
			}
			p_slot[playerid] = slot;
			#if defined a_OnPlayerUpdateWeaponSlot
				a_OnPlayerUpdateWeaponSlot(playerid, gPlayerWeaponSlot[playerid][fix_listitem], p_slot[playerid]);
			#endif
		}
		return 1;
	}

	#if defined a_OnDialogResponse
		return a_OnDialogResponse(playerid, dialogid, response, listitem, inputtext);
	#else
		return 0;
	#endif
}

#if defined _ALS_OnDialogResponse
	#undef OnDialogResponse
#else
	#define _ALS_OnDialogResponse
#endif
#define OnDialogResponse a_OnDialogResponse
#if defined a_OnDialogResponse
	forward a_OnDialogResponse(playerid, dialogid, response, listitem, inputtext[]);
#endif

#endif

/*
	a_OnPlayerBeganToDealDamage
*/

stock a_OnPlayerBeganToDealDamage(playerid)
{
	if (p_shot_timer[playerid] != 0) {
		return 0;
	}

	if (p_jump_tick[playerid] > GetTickCount()) {
		return 0;
	}

	new
		slot = p_slot[playerid];
	if (p_weapon[playerid][slot] == 0 || p_ammo[playerid][slot] == 0) {
		return 0;
	}

	new
		weaponid = p_weapon[playerid][slot];
	if (!(WEAPON_COLT45 <= weaponid <= WEAPON_SNIPER)) {
		return 0;
	}

	new
		Float:m_pos_x, Float:m_pos_y, Float:m_pos_z,
		Float:m_angle;
	GetPlayerPos(playerid, m_pos_x, m_pos_y, m_pos_z);
	GetPlayerFacingAngle(playerid, m_angle);

	new
		Float:ca_pos_z;
	CA_FindZ_For2DCoord(m_pos_x, m_pos_y, ca_pos_z);
	if (floatcmp(floatsub(m_pos_z, 1.2), ca_pos_z) == 1) {
		return 0;
	}

	new
		Float:w_distance,
		Float:w_pos_x, Float:w_pos_y, Float:w_pos_z,
		Float:w_angle,
		Float:w_damage = floatadd(s_WeaponDamage[weaponid], floatmul(p_skill[playerid][weaponid-WEAPON_COLT45], 5.0)),
		Float:w_range = floatadd(s_WeaponRange[weaponid], floatmul(p_skill[playerid][weaponid-WEAPON_COLT45], 5.0));

	if (25 <= weaponid <= 27) {
		w_damage = floatadd(w_damage, float(random(10)));
	}

	SetPlayerPos(playerid, m_pos_x, m_pos_y, m_pos_z);
	SetPlayerFacingAngle(playerid, m_angle);

	ClearAnimations(playerid, 1);
	ApplyAnimation(playerid, "PED", "GUN_STAND", 4.1, 0, 1, 1, 1, 0, 1);

	new
		Float:sin_x = floatadd(m_pos_x, floatmul(0.20, floatsin(floatadd(-m_angle, 44.0), degrees))),
		Float:cos_y = floatadd(m_pos_y, floatmul(0.20, floatcos(floatadd(-m_angle, 44.0), degrees)));

	p_object_weapon[playerid] = CreateDynamicObject(s_WEAPON_Modelid[weaponid], sin_x, cos_y, floatadd(m_pos_z, 0.3), 0.0, -5.5, floatadd(m_angle, 116.0));

	p_shot_timer[playerid] = SetTimerEx("a_OnPlayerWeaponTimer", s_WeaponShootRate[weaponid] + 1_000, false, "i", playerid);
	new
		Float:v_distance = w_range,
		Float:v_pos_x, Float:v_pos_y, Float:v_pos_z,
		#if defined USING_DAMAGE_VEHICLE
			Float:v_angle,
		#endif
		v_id = INVALID_VEHICLE_ID;

	foreach (new v : PlayerVehiclesStream[playerid])
	{
		GetVehiclePos(v, w_pos_x, w_pos_y, w_pos_z);
		w_distance = GetPlayerDistanceFromPoint(playerid, w_pos_x, w_pos_y, w_pos_z);
		if (floatcmp(w_distance, w_range) == 1) {
			continue;
		}
		w_angle = GetZAngleToPoint(m_pos_x, m_pos_y, w_pos_x, w_pos_y);
		if (floatcmp(floatadd(m_angle, 10.0), w_angle) >= 0 && floatcmp(floatsub(m_angle, 10.0), w_angle) <= 0) {
			if (floatcmp(w_distance, v_distance) == -1) {
				v_distance = w_distance;
				v_pos_x = w_pos_x;
				v_pos_y = w_pos_y;
				v_pos_z = w_pos_z;
				#if defined USING_DAMAGE_VEHICLE
					v_angle = w_angle;
				#endif
				v_id = v;
			}
		}
	}

	new
		Float:p_distance = w_range,
		Float:p_pos_x, Float:p_pos_y, Float:p_pos_z,
		Float:p_angle,
		p_id = INVALID_PLAYER_ID;

	foreach (new i : PlayerPlayersStream[playerid])
	{
		GetPlayerPos(i, w_pos_x, w_pos_y, w_pos_z);
		w_distance = GetPlayerDistanceFromPoint(playerid, w_pos_x, w_pos_y, w_pos_z);
		if (floatcmp(w_distance, w_range) == 1) {
			continue;
		}
		w_angle = GetZAngleToPoint(m_pos_x, m_pos_y, w_pos_x, w_pos_y);
		if (floatcmp(floatadd(m_angle, 10.0), w_angle) >= 0 && floatcmp(floatsub(m_angle, 10.0), w_angle) <= 0) {
			if (floatcmp(w_distance, p_distance) == -1) {
				p_distance = w_distance;
				p_pos_x = w_pos_x;
				p_pos_y = w_pos_y;
				p_pos_z = w_pos_z;
				p_angle = w_angle;
				p_id = i;
			}
		}
		PlayerPlaySound(i, 25602, 0.0, 0.0, 0.0);
		Streamer_Update(i);
	}
	PlayerPlaySound(playerid, 25602, 0.0, 0.0, 0.0);
	Streamer_Update(playerid);

	if (v_id != INVALID_VEHICLE_ID) {
		if (CA_RayCastLine(m_pos_x, m_pos_y, m_pos_z, v_pos_x, v_pos_y, v_pos_z, v_pos_x, v_pos_y, v_pos_z)) {
			v_id = INVALID_VEHICLE_ID;
		}
	}
	if (p_id != INVALID_PLAYER_ID) {
		if (CA_RayCastLine(m_pos_x, m_pos_y, m_pos_z, p_pos_x, p_pos_y, p_pos_z, p_pos_x, p_pos_y, p_pos_z)) {
			p_id = INVALID_PLAYER_ID;
		}
	}

	if (v_id == INVALID_VEHICLE_ID && p_id == INVALID_PLAYER_ID) {
		#if defined a_OnPlayerWeaponShot
			a_OnPlayerWeaponShot(playerid, weaponid, BULLET_HIT_TYPE_NONE, 0xFFFF, w_pos_x, w_pos_y, w_pos_z);
		#endif
	} else if (v_id == INVALID_VEHICLE_ID && p_id != INVALID_PLAYER_ID) {
		#if defined a_OnPlayerWeaponShot
			a_OnPlayerWeaponShot(playerid, weaponid, BULLET_HIT_TYPE_PLAYER, p_id, p_pos_x, p_pos_y, p_pos_z);
		#endif
		a_GivePlayerDamage(p_id, CompDamageGenerator(w_damage, p_angle, m_angle), playerid, weaponid);
		GetPlayerFacingAngle(p_id, p_angle);
		if (floatcmp(p_angle, floatsub(m_angle, 45.0)) >= 0 && floatcmp(p_angle, floatadd(m_angle, 45.0)) <= 0) {
			ClearAnimations(p_id, 1);
			ApplyAnimation(p_id, "PED", "SHOT_PARTIAL_B", 4.1, 0, 1, 1, 0, 0, 1);
		} else {
			ClearAnimations(p_id, 1);
			ApplyAnimation(p_id, "PED", "SHOT_PARTIAL", 4.1, 0, 1, 1, 0, 0, 1);
		}
	} else if (v_id != INVALID_VEHICLE_ID && p_id == INVALID_PLAYER_ID) {
		#if defined a_OnPlayerWeaponShot
			a_OnPlayerWeaponShot(playerid, weaponid, BULLET_HIT_TYPE_VEHICLE, v_id, v_pos_x, v_pos_y, v_pos_z);
		#endif
		#if defined USING_DAMAGE_VEHICLE
			a_GiveVehicleDamage(v_id, CompDamageGenerator(w_damage, v_angle, m_angle), playerid, weaponid);
		#endif
	} else {
		if (floatcmp(v_distance, p_distance) >= 0) {
			if (GetPlayerVehicleID(p_id) == v_id) {
				#if defined a_OnPlayerWeaponShot
					a_OnPlayerWeaponShot(playerid, weaponid, BULLET_HIT_TYPE_VEHICLE, v_id, v_pos_x, v_pos_y, v_pos_z);
				#endif
				#if defined USING_DAMAGE_VEHICLE
					a_GiveVehicleDamage(v_id, CompDamageGenerator(w_damage, v_angle, m_angle), playerid, weaponid);
				#endif
			} else {
				#if defined a_OnPlayerWeaponShot
					a_OnPlayerWeaponShot(playerid, weaponid, BULLET_HIT_TYPE_PLAYER, p_id, p_pos_x, p_pos_y, p_pos_z);
				#endif
				a_GivePlayerDamage(p_id, CompDamageGenerator(w_damage, p_angle, m_angle), playerid, weaponid);
				GetPlayerFacingAngle(p_id, p_angle);
				if (floatcmp(p_angle, floatsub(m_angle, 45.0)) >= 0 && floatcmp(p_angle, floatadd(m_angle, 45.0)) <= 0) {
					ClearAnimations(p_id, 1);
					ApplyAnimation(p_id, "PED", "SHOT_PARTIAL_B", 4.1, 0, 1, 1, 0, 0, 1);
				} else {
					ClearAnimations(p_id, 1);
					ApplyAnimation(p_id, "PED", "SHOT_PARTIAL", 4.1, 0, 1, 1, 0, 0, 1);
				}
			}
		} else {
			#if defined a_OnPlayerWeaponShot
				a_OnPlayerWeaponShot(playerid, weaponid, BULLET_HIT_TYPE_PLAYER, p_id, p_pos_x, p_pos_y, p_pos_z);
			#endif
			a_GivePlayerDamage(p_id, CompDamageGenerator(w_damage, p_angle, m_angle), playerid, weaponid);
			GetPlayerFacingAngle(p_id, p_angle);
			if (floatcmp(p_angle, floatsub(m_angle, 45.0)) >= 0 && floatcmp(p_angle, floatadd(m_angle, 45.0)) <= 0) {
				ClearAnimations(p_id, 1);
				ApplyAnimation(p_id, "PED", "SHOT_PARTIAL_B", 4.1, 0, 1, 1, 0, 0, 1);
			} else {
				ClearAnimations(p_id, 1);
				ApplyAnimation(p_id, "PED", "SHOT_PARTIAL", 4.1, 0, 1, 1, 0, 0, 1);
			}
		}
	}

	if (--p_ammo[playerid][slot] == 0) {
		p_slot[playerid] = 0;
	}
	return 1;
}

/*
	a_GivePlayerDamage
*/

stock a_GivePlayerDamage(damagedid, Float:amount, playerid, weaponid)
{
	if (p_deatch_tick[damagedid] > GetTickCount()) {
		return 0;
	}
	if (p_deatch_tick[playerid] > GetTickCount()) {
		return 0;
	}

	#if !defined a_OnPlayerTakeDamage && !defined a_OnPlayerGiveDamage && !defined a_OnPlayerDeath
		#pragma unused playerid
		#pragma unused weaponid
	#endif

	#if defined a_OnPlayerTakeDamage
		a_OnPlayerTakeDamage(damagedid, playerid, amount, weaponid);
	#endif
	#if defined a_OnPlayerGiveDamage
		a_OnPlayerGiveDamage(playerid, damagedid, amount, weaponid);
	#endif

	new
		Float:health,
		Float:armour;
	GetPlayerArmour(damagedid, armour);
	GetPlayerHealth(damagedid, health);

	if (floatcmp(armour, amount) >= 0) {
		SetPlayerArmour(damagedid, floatsub(armour, amount));
	} else if (floatcmp(armour, amount) == -1) {
		amount -= armour;
		SetPlayerArmour(damagedid, 0.0);
		if (floatcmp(floatsub(health, amount), 0.0) <= 0) {
			ClearAnimations(damagedid, 1);
			ApplyAnimation(damagedid, "PED", "KO_SHOT_STOM", 4.1, 0, 1, 1, 0, 0, 1);
			SetPlayerHealth(damagedid, 0.0);
			#if defined a_OnPlayerDeath
				a_OnPlayerDeath(damagedid, playerid, weaponid);
			#endif
			p_deatch_tick[damagedid] = GetTickCount()+900;
		} else {
			SetPlayerHealth(damagedid, floatsub(health, amount));
		}
	} else {
		if (floatcmp(floatsub(health, amount), 0.0) <= 0) {
			ClearAnimations(damagedid, 1);
			ApplyAnimation(damagedid, "PED", "KO_SHOT_STOM", 4.1, 0, 1, 1, 0, 0, 1);
			SetPlayerHealth(damagedid, 0.0);
			#if defined a_OnPlayerDeath
				a_OnPlayerDeath(damagedid, playerid, weaponid);
			#endif
			p_deatch_tick[damagedid] = GetTickCount()+900;
		} else {
			SetPlayerHealth(damagedid, floatsub(health, amount));
		}
	}
	return 1;
}

#if defined USING_DAMAGE_VEHICLE

/*
	a_GiveVehicleDamage
*/

stock a_GiveVehicleDamage(damaged_vehicleid, Float:amount, playerid, weaponid)
{
	if (v_deatch_timer[damaged_vehicleid] != 0) {
		return 1;
	}

	#if !defined a_OnPlayerGiveDamageVehicle
		#pragma unused playerid
		#pragma unused weaponid
	#endif

	#if defined a_OnPlayerGiveDamageVehicle
		a_OnPlayerGiveDamageVehicle(playerid, damaged_vehicleid, amount, weaponid);
	#endif

	new
		Float:health;
	GetVehicleHealth(damaged_vehicleid, health);

	if (floatcmp(floatsub(health, amount), 250.0) >= 0) {
		SetVehicleHealth(damaged_vehicleid, floatsub(health, amount));
	} else {
		v_deatch_timer[damaged_vehicleid] = SetTimerEx("a_OnVehicleWeaponTimer", 1_000 * 10, false, "i", damaged_vehicleid);
	}
	return 1;
}

#endif

/*
	a_OnPlayerWeaponTimer
*/

public a_OnPlayerWeaponTimer(playerid)
{
	if(p_object_weapon[playerid] != 0) {
		DestroyDynamicObject(p_object_weapon[playerid]);
		p_object_weapon[playerid] = 0;
	}
	p_shot_timer[playerid] = 0;
	ClearAnimations(playerid, 1);
	return 1;
}

#if defined USING_DAMAGE_VEHICLE

/*
	a_OnVehicleWeaponTimer
*/

public a_OnVehicleWeaponTimer(vehicleid)
{
	SetVehicleToRespawn(vehicleid);
	v_deatch_timer[vehicleid] = 0;
	return 1;
}

#endif
