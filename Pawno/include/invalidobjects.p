/*
	Soly

	isPlayerAndroid(playerId)
	setDeviceInfo(playerId, deviceType)
	isInvalidObject(modelId)

*/

#define INVALID_OBJECTS_VERSION	0x3

#if defined _invalidobjects_included
	#endinput
#endif
#define _invalidobjects_included

#if !defined PAWNCMD_INC_
	#error "plz include Pawn.RakNet"
#endif

#if defined RPC_CREATE_OBJECT
	#undef RPC_CREATE_OBJECT
	#define RPC_CREATE_OBJECT 44
#else
	#define RPC_CREATE_OBJECT 44
#endif

#if defined RPC_WORLDVEHICLE_ADD
	#undef RPC_WORLDVEHICLE_ADD
	#define RPC_WORLDVEHICLE_ADD 164
#else
	#define RPC_WORLDVEHICLE_ADD 164
#endif

#if defined RPC_SET_PLAYER_SKIN
	#undef RPC_SET_PLAYER_SKIN
	#define RPC_SET_PLAYER_SKIN 153
#else
	#define RPC_SET_PLAYER_SKIN 153
#endif

#if defined RPC_CLIENT_JOIN
	#undef RPC_CLIENT_JOIN
	#define RPC_CLIENT_JOIN 25
#else
	#define RPC_CLIENT_JOIN 25
#endif

#if defined RPC_CREATE_PICKUP
	#undef RPC_CREATE_PICKUP
	#define RPC_CREATE_PICKUP 95
#else
	#define RPC_CREATE_PICKUP 95
#endif

#define PICKUP_REPLACE_MODEL 1239

#define PLAYER_DEVICE_PC 0
#define PLAYER_DEVICE_ANDROID 1


enum E_CLIENT_KEY
{
	e_clientVersion,
	e_szAuthKey[44]
}

static const stock m_szClientVersions[][E_CLIENT_KEY] = {
	{90, "E02262CF28BC542486C558D4BE9EFB716592AFAF8B"}
};

static const m_szSampModels[] = {
	18631, 18632, 18633, 18634, 18635, 18636, 18637, 18638, 18639, 18640, 18641, 18642, 18643, 18644, 18645, 18646, 18647, 18648, 18649, 18650, 18651, 18715,
	18652, 18653, 18654, 18655, 18656, 18657, 18658, 18659, 18660, 18661, 18662, 18663, 18664, 18665, 18666, 18667, 18668, 18669, 18670, 18671, 18672, 18716,
	18673, 18674, 18675, 18676, 18677, 18678, 18679, 18680, 18681, 18682, 18683, 18684, 18685, 18686, 18687, 18688, 18689, 18690, 18691, 18692, 18693, 18717,
	18694, 18695, 18696, 18697, 18698, 18699, 18700, 18701, 18702, 18703, 18704, 18705, 18706, 18707, 18708, 18709, 18710, 18711, 18712, 18713, 18714, 18718,
	18719, 18720, 18721, 18722, 18723, 18724, 18725, 18726, 18727, 18728, 18729, 18730, 18731, 18732, 11743, 11744, 11745, 11746, 11747, 11748, 11749, 11750,
	18733, 18734, 18735, 18736, 18737, 18738, 18739, 18740, 18741, 18742, 18743, 18744, 18745, 18746, 18747, 18748, 18749, 18750, 18751, 18752, 18753, 18754,
	18755, 18756, 18757, 18758, 18759, 18760, 18761, 18762, 18763, 18764, 18765, 18766, 18767, 18768, 18769, 18770, 18771, 18772, 18773, 18774, 18775, 18776,
	18777, 18778, 18779, 18780, 18781, 18782, 18783, 18784, 18785, 18786, 18787, 18788, 18789, 18790, 18791, 18792, 18793, 18794, 18795, 18796, 18797, 18798,
	18799, 18800, 18801, 18802, 18803, 18804, 18805, 18806, 18807, 18808, 18809, 18810, 18811, 18812, 18813, 18814, 18815, 18816, 18817, 18818, 18819, 18820,
	18821, 18822, 18823, 18824, 18825, 18826, 18827, 18828, 18829, 18830, 18831, 18832, 18833, 18834, 18835, 18836, 18837, 18838, 18839, 18840, 18841, 18842,
	18843, 18844, 18845, 18846, 18847, 18848, 18849, 18850, 18851, 18852, 18853, 18854, 18855, 18856, 18857, 18858, 18859, 18862, 18863, 18864, 18865, 18866,
	18867, 18868, 18869, 18870, 18871, 18872, 18873, 18874, 18875, 18876, 18877, 18878, 18879, 18880, 18881, 18882, 18883, 18884, 18885, 18886, 18887, 18888,
	18889, 18890, 18891, 18892, 18893, 18894, 18895, 18896, 18897, 18898, 18899, 18900, 18901, 18902, 18903, 18904, 18905, 18906, 18907, 18908, 18909, 18910,
	18911, 18912, 18913, 18914, 18915, 18916, 18917, 18918, 18919, 18920, 18921, 18922, 18923, 18924, 18925, 18926, 18927, 18928, 18929, 18930, 18931, 18932,
	18933, 18934, 18935, 18936, 18937, 18938, 18939, 18940, 18941, 18942, 18943, 18944, 18945, 18946, 18947, 18948, 18949, 18950, 18951, 18952, 18953, 18954,
	18955, 18956, 18957, 18958, 18959, 18960, 18961, 18962, 18963, 18964, 18965, 18966, 18967, 18968, 18969, 18970, 18971, 18972, 18973, 18974, 18975, 18976,
	18977, 18978, 18979, 18980, 18981, 18982, 18983, 18984, 18985, 18986, 18987, 18988, 18989, 18990, 18991, 18992, 18993, 18994, 18995, 18996, 18997, 18998,
	18999, 19000, 19001, 19002, 19003, 19004, 19005, 19006, 19007, 19008, 19009, 19010, 19011, 19012, 19013, 19014, 19015, 19016, 19017, 19018, 19019, 19020,
	19021, 19022, 19023, 19024, 19025, 19026, 19027, 19028, 19029, 19030, 19031, 19032, 19033, 19034, 19035, 19036, 19037, 19038, 19039, 19040, 19041, 19042,
	19043, 19044, 19045, 19046, 19047, 19048, 19049, 19050, 19051, 19052, 19053, 19054, 19055, 19056, 19057, 19058, 19059, 19060, 19061, 19062, 19063, 19064,
	19065, 19066, 19067, 19068, 19069, 19070, 19071, 19072, 19073, 19074, 19075, 19076, 19077, 19078, 19079, 19080, 19081, 19082, 19083, 19084, 19085, 19086,
	19087, 19088, 19089, 19090, 19091, 19092, 19093, 19094, 19095, 19096, 19097, 19098, 19099, 19100, 19101, 19102, 19103, 19104, 19105, 19106, 19107, 19108,
	19109, 19110, 19111, 19112, 19113, 19114, 19115, 19116, 19117, 19118, 19119, 19120, 19121, 19122, 19123, 19124, 19125, 19126, 19127, 19128, 19129, 19130,
	19131, 19132, 19133, 19134, 19135, 19136, 19137, 19138, 19139, 19140, 19141, 19142, 19143, 19144, 19145, 19146, 19147, 19148, 19149, 19150, 19151, 19152,
	19153, 19154, 19155, 19156, 19157, 19158, 19159, 19160, 19161, 19162, 19163, 19164, 19165, 19166, 19167, 19168, 19169, 19170, 19171, 19172, 19173, 19174,
	19175, 19176, 19177, 19178, 19179, 19180, 19181, 19182, 19183, 19184, 19185, 19186, 19187, 19188, 19189, 19190, 19191, 19192, 19193, 19194, 19195, 19196,
	19197, 19198, 19200, 19201, 19202, 19203, 19204, 19205, 19206, 19207, 19208, 19209, 19210, 19211, 19212, 19213, 19214, 19215, 19216, 19217, 19218, 19219,
	19220, 19221, 19222, 19223, 19224, 19225, 19226, 19227, 19228, 19229, 19230, 19231, 19232, 19233, 19234, 19235, 19236, 19237, 19238, 19239, 19240, 19241,
	19242, 19243, 19244, 19245, 19246, 19247, 19248, 19249, 19250, 19251, 19252, 19253, 19254, 19255, 19256, 19257, 19258, 19259, 19260, 19261, 19262, 19263,
	19264, 19265, 19266, 19267, 19268, 19269, 19270, 19271, 19272, 19273, 19274, 19277, 19278, 19279, 19280, 19281, 19282, 19283, 19284, 19285, 19286, 19287,
	19288, 19289, 19290, 19291, 19292, 19293, 19294, 19295, 19296, 19297, 19298, 19299, 19300, 19301, 19302, 19303, 19304, 19305, 19306, 19307, 19308, 19309,
	19310, 19311, 19312, 19313, 19314, 19315, 19316, 19317, 19318, 19319, 19320, 19321, 19322, 19323, 19324, 19325, 19326, 19327, 19328, 19329, 19330, 19331,
	19332, 19333, 19334, 19335, 19336, 19337, 19338, 19339, 19340, 19341, 19342, 19343, 19344, 19345, 19346, 19347, 19348, 19349, 19350, 19351, 19352, 19353,
	19354, 19355, 19356, 19357, 19358, 19359, 19360, 19361, 19362, 19363, 19364, 19365, 19366, 19367, 19368, 19369, 19370, 19371, 19372, 19373, 19374, 19375,
	19376, 19377, 19378, 19379, 19380, 19381, 19382, 19383, 19384, 19385, 19386, 19387, 19388, 19389, 19390, 19391, 19392, 19393, 19394, 19395, 19396, 19397,
	19398, 19399, 19400, 19401, 19402, 19403, 19404, 19405, 19406, 19407, 19408, 19409, 19410, 19411, 19412, 19413, 19414, 19415, 19416, 19417, 19418, 19419,
	19420, 19421, 19422, 19423, 19424, 19425, 19426, 19427, 19428, 19429, 19430, 19431, 19432, 19433, 19434, 19435, 19436, 19437, 19438, 19439, 19440, 19441,
	19442, 19443, 19444, 19445, 19446, 19447, 19448, 19449, 19450, 19451, 19452, 19453, 19454, 19455, 19456, 19457, 19458, 19459, 19460, 19461, 19462, 19463,
	19464, 19465, 19466, 19467, 19468, 19469, 19470, 19471, 19472, 19473, 19474, 19475, 19476, 19477, 19478, 19479, 19480, 19481, 19482, 19483, 19484, 19485,
	19486, 19487, 19488, 19489, 19490, 19491, 19492, 19493, 19494, 19495, 19496, 19497, 19498, 19499, 19500, 19501, 19502, 19503, 19504, 19505, 19506, 19507,
	19508, 19509, 19510, 19511, 19512, 19513, 19514, 19515, 19516, 19517, 19518, 19519, 19520, 19521, 19522, 19523, 19524, 19525, 19526, 19527, 19528, 19529,
	19530, 19531, 19532, 19533, 19534, 19535, 19536, 19537, 19538, 19539, 19540, 19541, 19542, 19543, 19544, 19545, 19546, 19547, 19548, 19549, 19550, 19551,
	19552, 19553, 19554, 19555, 19556, 19557, 19558, 19559, 19560, 19561, 19562, 19563, 19564, 19565, 19566, 19567, 19568, 19569, 19570, 19571, 19572, 19573,
	19574, 19575, 19576, 19577, 19578, 19579, 19580, 19581, 19582, 19583, 19584, 19585, 19586, 19587, 19588, 19589, 19590, 19591, 19592, 19593, 19594, 19595,
	19597, 19598, 19599, 19600, 19601, 19602, 19603, 19604, 19605, 19606, 19607, 19608, 19609, 19610, 19611, 19612, 19613, 19614, 19615, 19616, 19617, 19618,
	19619, 19620, 19621, 19622, 19623, 19624, 19625, 19626, 19627, 19628, 19629, 19630, 19631, 19632, 19633, 19634, 19635, 19636, 19637, 19638, 19639, 19640,
	19641, 19642, 19643, 19644, 19645, 19646, 19647, 19648, 19649, 19650, 19651, 19652, 19653, 19654, 19655, 19656, 19657, 19658, 19659, 19660, 19661, 19662,
	19663, 19664, 19665, 19666, 19667, 19668, 19669, 19670, 19671, 19672, 19673, 19674, 19675, 19676, 19677, 19678, 19679, 19680, 19681, 19682, 19683, 19684,
	19685, 19686, 19687, 19688, 19689, 19690, 19691, 19692, 19693, 19694, 19695, 19696, 19697, 19698, 19699, 19700, 19701, 19702, 19703, 19704, 19705, 19706,
	19707, 19708, 19709, 19710, 19711, 19712, 19713, 19714, 19715, 19716, 19717, 19718, 19719, 19720, 19721, 19722, 19723, 19724, 19725, 19726, 19727, 19728,
	19729, 19730, 19731, 19732, 19733, 19734, 19735, 19736, 19737, 19738, 19739, 19740, 19741, 19742, 19743, 19744, 19745, 19746, 19747, 19748, 19749, 19750,
	19751, 19752, 19753, 19754, 19755, 19756, 19757, 19758, 19759, 19760, 19761, 19762, 19763, 19764, 19765, 19766, 19767, 19768, 19769, 19770, 19771, 19772,
	19773, 19774, 19775, 19776, 19777, 19778, 19779, 19780, 19781, 19782, 19783, 19784, 19785, 19786, 19787, 19788, 19789, 19790, 19791, 19792, 19793, 19794,
	19795, 19796, 19797, 19798, 19799, 19800, 19801, 19802, 19803, 19804, 19805, 19806, 19807, 19808, 19809, 19810, 19811, 19812, 19813, 19814, 19815, 19816,
	19817, 19818, 19819, 19820, 19821, 19822, 19823, 19824, 19825, 19826, 19827, 19828, 19829, 19830, 19831, 19832, 19833, 19834, 19835, 19836, 19837, 19838,
	19839, 19840, 19841, 19842, 19843, 19844, 19845, 19846, 19847, 19848, 19849, 19850, 19851, 19852, 19853, 19854, 19855, 19856, 19857, 19858, 19859, 19860,
	19861, 19862, 19863, 19864, 19865, 19866, 19867, 19868, 19869, 19870, 19871, 19872, 19873, 19874, 19875, 19876, 19877, 19878, 19879, 19880, 19881, 19882,
	19883, 19884, 19885, 19886, 19887, 19888, 19889, 19890, 19891, 19892, 19893, 19894, 19895, 19896, 19897, 19898, 19899, 19900, 19903, 19904, 19905, 19906,
	19907, 19908, 19909, 19910, 19911, 19912, 19913, 19914, 19915, 19916, 19917, 19918, 19919, 19920, 19921, 19922, 19923, 19924, 19925, 19926, 19927, 19928,
	19929, 19930, 19931, 19932, 19933, 19934, 19935, 19936, 19937, 19938, 19939, 19940, 19941, 19942, 19943, 19944, 19945, 19946, 19947, 19948, 19949, 19950,
	19951, 19952, 19953, 19954, 19955, 19956, 19957, 19958, 19959, 19960, 19961, 19962, 19963, 19964, 19965, 19966, 19967, 19968, 19969, 19970, 19971, 19972,
	19973, 19974, 19975, 19976, 19977, 19978, 19979, 19980, 19981, 19982, 19983, 19984, 19985, 19986, 19987, 19988, 19989, 19990, 19991, 19992, 19993, 19994,
	19995, 19996, 19997, 19998, 19999, 11682, 11683, 11684, 11685, 11686, 11687, 11688, 11689, 11690, 11691, 11692, 11693, 11694, 11695, 11696, 11697, 11698,
	11699, 11700, 11701, 11702, 11703, 11704, 11705, 11706, 11707, 11708, 11709, 11710, 11711, 11712, 11713, 11714, 11715, 11716, 11717, 11718, 11719, 11720,
	11721, 11722, 11723, 11724, 11725, 11726, 11727, 11728, 11729, 11730, 11731, 11732, 11733, 11734, 11735, 11736, 11737, 11738, 11739, 11740, 11741, 11742,
	11751, 11752, 11753, 19901, 19902
};

enum E_CLIENT_STRUCT
{
	iVersion, 					// INT32
	byteMod, 					// UINT8
	byteNicknameLen, 			// UINT8
	NickName[MAX_PLAYER_NAME],	// char
	uiClientChallengeResponse,  // UINT32
	byteAuthKeyLen, 			// UINT8
	auth_key[64], 				// char
	iClientVerLen, 				// UINT8
	ClientVersion[12]			// char

};

enum E_PICKUP_STRUCT
{
	dPickupID,  	 // UINT32
	dModelID,  		 // UINT32
    dSpawnType,  	 // UINT32
    Float:pickupX,   // FLOAT
    Float:pickupY,   // FLOAT
    Float:pickupZ    // FLOAT
};

enum E_OBJECT_STRUCT
{
	e_wObjectID, 			// INT16
	e_ModelID,				// UINT32
	Float:e_objectX,		// FLOAT
	Float:e_objectY,		// FLOAT
	Float:e_objectZ,		// FLOAT
	Float:e_rotx,			// FLOAT
	Float:e_roty,			// FLOAT
	Float:e_rotz,			// FLOAT
	float:e_DrawDistance,	// FLOAT
	e_NoCameraCol,			// UINT8
	e_attachedObject,		// UINT16
	e_attachedVehicle,		// UINT16
	float:e_AttachOffsetX,	// FLOAT
	float:e_AttachOffsetY,	// FLOAT
	float:e_AttachOffsetZ,	// FLOAT
	float:e_AttachRotX,		// FLOAT
	float:e_AttachRotY,		// FLOAT
	float:e_AttachRotZ,		// FLOAT
	e_SyncRotation 			// UINT8

};

enum E_VEHICLE_STRUCT
{
	e_vVehicleID, 			// INT16
	e_vModelID,				// UINT32
	Float:e_posX,
	Float:e_posY,
	Float:e_posZ,
	Float:e_rot,
	e_vColor1,
	e_vColor2,
	Float:e_vHealth,
	e_vInterior,
	e_vDoorDamageStatus,
	e_vPanelDamageStatus,
	e_vByteLightDamageStatus,
	e_vByteTimeDamageStatus,
	e_vByteAddSiren

};

enum E_PLAYER_STRUCT
{
	e_usPlayerID,
	e_bTeam,
	e_uiSkin,
	e_pfPosX,
	e_pfPosY,
	e_pfPosZ,
	e_pfRot,
	e_uiColor,
	e_bFighting,
	e_boolVisible
};

static dataObject[E_OBJECT_STRUCT];
static vehicleData[E_VEHICLE_STRUCT];
static playerData[E_PLAYER_STRUCT];

static playerDevice[MAX_PLAYERS char];

stock isPlayerAndroid(playerId)
{
    if(playerId == -1) return 1;
    return playerDevice{playerId};
}

stock setDeviceInfo(playerId, deviceType)
{
	playerDevice{playerId} = deviceType;
	return 1;
}

stock isValidVehicle(modelId)
{
	if(isInvalidVehicle(modelId))
	{
	    if(getReplacableVehicleModel(modelId) == -1)
	    {
	        return 0;
	    }
	}
	return 1;
}

stock isValidSkin(modelId)
{
    if(isInvalidSkin(modelId))
	{
	    if(getReplacableSkinModel(modelId) == -1)
	    {
	        return 0;
	    }
	}
	return 1;
}

stock isInvalidObject(modelId)
{
	if(modelId < 11000)
		return -1;
	new returnval = -1;
	for(new it; it < sizeof(m_szSampModels); it++)
	{
		if(m_szSampModels[it] == modelId)
		{
			returnval = modelId;
			break;
		}
	}
	return returnval;
}


#define MAX_VEH_MODELS_REPLACE  16
static customVehModels[MAX_VEH_MODELS_REPLACE][] = {
{ 3194, 411 },
{ 3195, 408 },
{ 3196, 412 },
{ 3197, 412 },
{ 3198, 412 },
{ 3199, 412 },
{ 3200, 412 },
{ 3201, 412 },
{ 3202, 412 },
{ 3203, 412 },
{ 3204, 412 },
{ 3205, 412 },
{ 3206, 412 },
{ 3207, 412 },
{ 3208, 412 },
{ 3209, 412 }
};/*
static customVehModels[MAX_VEH_MODELS_REPLACE][] = {
{ 3194, 411, 110 },
{ 3195, 408, 110 },
{ 3196, 412, 115 },
{ 3197, 412, 115 },
{ 3198, 412, 115 },
{ 3199, 412, 115 },
{ 3200, 412, 115 },
{ 3201, 412, 115 },
{ 3202, 412, 115 },
{ 3203, 412, 115 },
{ 3204, 412, 115 },
{ 3205, 412, 115 },
{ 3206, 412, 115 },
{ 3207, 412, 115 },
{ 3208, 412, 115 }
};*/

stock isInvalidVehicle(modelId)
{
	if(modelId < 400 || modelId > 611)
	{
		return 1;
	}

	if(modelId < 15000 || modelId > 15100)
	{
		for(new i = 0; i < MAX_VEH_MODELS_REPLACE; i++)
		{
			if(customVehModels[i][0] == modelId)
			{
				return 1;
			}
		}
	}
	else
	{
		return 1;
	}

	return 0;
}

stock getReplacableVehicleModel(modelId)
{
	if(!(15_000 <= modelId <= 15_100))
	{
		for(new i = 0; i < MAX_VEH_MODELS_REPLACE; i++)
		{
			if(customVehModels[i][0] == modelId)
			{
				return customVehModels[i][1];
			}
		}
	}
	else return 412;

	return -1;
}

#define MAX_SKIN_MODELS_REPLACE  31
static skinModels[MAX_SKIN_MODELS_REPLACE][] = {
{ 793, 83, 107}, // morgenshtern
{ 794, 84, 107 }, // xxxtentacion
{ 795, 85, 107 }, // mcgregor
{ 796, 80, 107 }, // scarlxrd
{ 797, 155, 107 }, // santrope club
{ 798, 1, 107 }, // santa
{ 799, 117, 107 }, //yak, yak,
{ 907, 16, 107 }, //waxta1, waxta1,
{ 908, 108, 107 }, //vagos, vagos,
{ 909, 111, 107 }, //russia, russia,
{ 965, 114, 107 }, //rifa, rifa,
{ 999, 262, 107 }, //pris2, pris2, ������� ��� � ������
{ 1194, 42, 107 }, //pris1, pris1,  ������� ��������
{ 1195, 71, 107 }, //pd1, pd1,
{ 1196, 123, 107 }, //lcn1, lcn1,
{ 1197, 124, 107 }, //lcn, lcn,
{ 1198, 106, 107 }, //groov, groov,
{ 1199, 70, 107 }, //doctor, doctor,
{ 1200, 100, 107 }, //biker, biker,
{ 1201, 102, 107 }, //balla1, balla1,
{ 1202, 114, 107 }, //azte, azte,
{ 1203, 72, 107 }, //armyv2, armyv2,
{ 1204, 72, 107 },// armyv1, armyv1,
{ 1205, 72, 110 },// - donald
{ 1206, 72, 110 },// - f1racer
{ 3136, 72, 110 },// - ct1
{ 3137, 72, 110 },// - ct2
{ 3138, 72, 110 },//- ct3
{ 3139, 72, 110 },// - t1
{ 3140, 72, 110 },// - t2
{ 3141, 72, 110 }// - t3
};

#define MAX_SERIAL_LENGTH	64

new g_usSAMPMajorVersions[MAX_PLAYERS];
new g_usSAMPMinorVersions[MAX_PLAYERS];
new g_bSAMPModified[MAX_PLAYERS];
new g_usLauncherVersion[MAX_PLAYERS];
new g_usModpackVersion[MAX_PLAYERS];
new g_szSerialNumbers[MAX_PLAYERS][MAX_SERIAL_LENGTH + 1];
new g_bUsesNewFormatData[MAX_PLAYERS];

stock isInvalidSkin(modelId)
{
	if(modelId < 1 || modelId > 311)
	{
		return 1;
	}
    for(new i = 0; i < MAX_SKIN_MODELS_REPLACE; i++)
	{
	    if(skinModels[i][0] == modelId)
	    {
	        return 1;
	    }
	}
	return 0;
}

stock getReplacableSkinModel(modelId)
{
    for(new i = 0; i < MAX_SKIN_MODELS_REPLACE; i++)
	{
	    if(skinModels[i][0] == modelId)
	    {
	        return skinModels[i][1];
	    }
	}
	return -1;
}

#define MAX_OBJECT_MODELS_REPLACE  3
static objModels[MAX_OBJECT_MODELS_REPLACE] = { 1241, 13182, 9183 };

stock isInvalidObjectModel(modelId)
{
    for(new i = 0; i < MAX_OBJECT_MODELS_REPLACE; i++)
	{
	    if(objModels[i] == modelId)
	    {
	        return 1;
	    }
	}
	return 0;
}

stock getReplacableObjectModel(modelId)
{
    for(new i = 0; i < MAX_OBJECT_MODELS_REPLACE; i++)
	{
	    if(objModels[i][0] == modelId)
	    {
	        return skinModels[i][1];
	    }
	}
	return -1;
}

#if defined _inc_y_hooks || defined _INC_y_hooks
	hook OnIncomingRPC(playerid, rpcid, BitStream:bs)
#else
	public OnIncomingRPC(playerid, rpcid, BitStream:bs)
#endif
	{
		if(rpcid == RPC_CLIENT_JOIN)
		{
			new dataClient[E_CLIENT_STRUCT];
			g_bUsesNewFormatData[playerid] = 0;
			BS_ReadValue(
				bs,
				PR_INT32, dataClient[iVersion],
				PR_UINT8, dataClient[byteMod],
				PR_UINT8, dataClient[byteNicknameLen]);

			if(dataClient[byteNicknameLen] >= MAX_PLAYER_NAME)
			{
				return 0;
			}

			BS_ReadValue(
				bs,
				PR_STRING, dataClient[NickName], dataClient[byteNicknameLen],
				PR_UINT32, dataClient[uiClientChallengeResponse],
				PR_UINT8, dataClient[byteAuthKeyLen]);

			if(dataClient[byteAuthKeyLen] >= 64)
			{
				return 0;
			}

			BS_ReadValue(
				bs,
				PR_STRING, dataClient[auth_key], dataClient[byteAuthKeyLen],
				PR_UINT8, dataClient[iClientVerLen]);

			if(dataClient[iClientVerLen] >= 12)
			{
				return 0;
			}

			BS_ReadValue(
				bs,
				PR_STRING, dataClient[ClientVersion], dataClient[iClientVerLen]
			);

			setDeviceInfo(playerid, PLAYER_DEVICE_PC);
			p_t_info[playerid][cl_vers] = 0;

			if(!strcmp(dataClient[auth_key], "E02262CF28BC542486C558D4BE9EFB716592AFAF8B"))
			{
				new checksum = 0;
				BS_ReadUint16(bs, checksum);

				if(checksum != 0x94D5)
				{
					setDeviceInfo(playerid, PLAYER_DEVICE_PC);
					p_t_info[playerid][cl_vers] = 0;
					setPlayerAndroidVers(playerid, 0);
					return 1;
				}

				BS_ReadUint16(bs, g_usSAMPMajorVersions[playerid]);
				BS_ReadUint16(bs, g_usSAMPMinorVersions[playerid]);
				BS_ReadBool(bs, g_bSAMPModified[playerid]);
				BS_ReadUint16(bs, g_usLauncherVersion[playerid]);
				BS_ReadUint16(bs, g_usModpackVersion[playerid]);
				new length;
				BS_ReadUint16(bs, length);
				if(length >= MAX_SERIAL_LENGTH + 1)
				{
					setDeviceInfo(playerid, PLAYER_DEVICE_PC);
					p_t_info[playerid][cl_vers] = 0;
					setPlayerAndroidVers(playerid, 0);
					return 1;
				}
				for(new i = 0; i < MAX_SERIAL_LENGTH + 1; i++)
				{
					g_szSerialNumbers[playerid][i] = 0;
				}
				BS_ReadString(bs, g_szSerialNumbers[playerid], length);

				new vers = 100 + (g_usSAMPMajorVersions[playerid] - 1);
				setPlayerAndroidVers(playerid, vers);

				g_bUsesNewFormatData[playerid] = 1;
			}

			setDeviceInfo(playerid, PLAYER_DEVICE_PC);

			static iter = 0;
			for(iter = 0; iter < sizeof(m_szClientVersions); iter++)
			{
				if(!strcmp(dataClient[auth_key], m_szClientVersions[iter][e_szAuthKey]))
				{
					setDeviceInfo(playerid, m_szClientVersions[iter][e_clientVersion]);
					break;
				}
			}
		}
		#if defined INCLUDE_OnIncomingRPC
			return INCLUDE_OnIncomingRPC(playerid, rpcid, BitStream:bs);
		#else
			return 1;
		#endif
	}

#if !defined _inc_y_hooks && !defined _INC_y_hooks
	#if defined _ALS_OnIncomingRPC
		#undef OnIncomingRPC
	#else
		#define _ALS_OnIncomingRPC
	#endif

	#define OnIncomingRPC INCLUDE_OnIncomingRPC
	#if defined INCLUDE_OnIncomingRPC
		forward INCLUDE_OnIncomingRPC(playerid, rpcid, BitStream:bs);
	#endif
#endif

#define RPC_ScrGivePlayerWeapon 22
#define RPC_ScrSetPlayerAttachedObject 113
#define RPC_WorldPlayerAdd  32

stock ProcessReplaceSkin(playerid, BitStream:bs)
{
    new player, skinid;
	BS_ReadValue(
		bs,
 		PR_UINT32, player,
		PR_UINT32, skinid);

	if(isInvalidSkin(skinid))
	{
		new bool: yes;
		for(new i; i < MAX_SKIN_MODELS_REPLACE; i++)
		{
			if(skinid == skinModels[i][0])
			{
				if(getPlayerAndroidVers(playerid) < skinModels[i][2])
				{
					new BitStream:bitstream = BS_New();
					BS_WriteValue(
						bitstream,
						PR_UINT32, player, 	//id
						PR_UINT32, 1);
					BS_RPC(bitstream, playerid, RPC_SET_PLAYER_SKIN, PR_HIGH_PRIORITY, PR_RELIABLE_SEQUENCED);
					BS_Delete(bitstream);
					yes = true;
					break;
				}
			}
		}

		if(!yes)
		{
			// ���������� ������
			new BitStream:bitstream = BS_New();
			BS_WriteValue(
				bitstream,
				PR_UINT32, player, 	//id
				PR_UINT32, getReplacableSkinModel(skinid));
			BS_RPC(bitstream, playerid, RPC_SET_PLAYER_SKIN, PR_HIGH_PRIORITY, PR_RELIABLE_SEQUENCED);
			BS_Delete(bitstream);
		}
		return 1;
	}
	return 0;
}

/*

enum E_PLAYER_STRUCT
{
	e_usPlayerID,
	e_bTeam,
	e_uiSkin,
	e_pfPosX,
	e_pfPosY,
	e_pfPosZ,
	e_pfRot,
	e_uiColor,
	e_bFighting,
	e_boolVisible
};

*/

stock ProcessReplaceSkinAdd(playerid, BitStream:bs)
{
    static clearPlayerData[E_PLAYER_STRUCT];
	playerData = clearPlayerData;

	BS_ReadValue(
 		bs,
   		PR_INT16, playerData[e_usPlayerID],
		PR_UINT8, playerData[e_bTeam],
		PR_UINT32, playerData[e_uiSkin],
		PR_FLOAT, playerData[e_pfPosX],
		PR_FLOAT, playerData[e_pfPosY],
		PR_FLOAT, playerData[e_pfPosZ],
		PR_FLOAT, playerData[e_pfRot],
		PR_UINT32, playerData[e_uiColor],
		PR_UINT8, playerData[e_bFighting],
		PR_BOOL, playerData[e_boolVisible]);

	if(isInvalidSkin(playerData[e_uiSkin]))
	{
 		new BitStream:bitstream = BS_New();

		BS_WriteValue(
	 		bitstream,
	   		PR_INT16, playerData[e_usPlayerID],
			PR_UINT8, playerData[e_bTeam],
			PR_UINT32, getReplacableSkinModel(playerData[e_uiSkin]),
			PR_FLOAT, playerData[e_pfPosX],
			PR_FLOAT, playerData[e_pfPosY],
			PR_FLOAT, playerData[e_pfPosZ],
			PR_FLOAT, playerData[e_pfRot],
			PR_UINT32, playerData[e_uiColor],
			PR_UINT8, playerData[e_bFighting],
			PR_BOOL, playerData[e_boolVisible]);

		BS_RPC(bitstream, playerid, RPC_WorldPlayerAdd, PR_HIGH_PRIORITY, PR_RELIABLE_SEQUENCED);
		BS_Delete(bitstream);
		return 1;
	}
	return 0;
}

stock ProcessReplaceVehicle(playerid, BitStream:bs)
{
    static clearVehicleData[E_VEHICLE_STRUCT];
	vehicleData = clearVehicleData;
	new modSlots[14];
	new bytePaintJob;
	new color1, color2;

	BS_ReadValue(
 		bs,
   		PR_INT16, vehicleData[e_vVehicleID],
		PR_UINT32, vehicleData[e_vModelID],
		PR_FLOAT, vehicleData[e_posX],
		PR_FLOAT, vehicleData[e_posY],
		PR_FLOAT, vehicleData[e_posZ],
		PR_FLOAT, vehicleData[e_rot],
		PR_UINT8, vehicleData[e_vColor1],
		PR_UINT8, vehicleData[e_vColor2],
		PR_FLOAT, vehicleData[e_vHealth],
		PR_UINT8, vehicleData[e_vInterior],
		PR_UINT32, vehicleData[e_vDoorDamageStatus],
		PR_UINT32, vehicleData[e_vPanelDamageStatus],
		PR_UINT8, vehicleData[e_vByteLightDamageStatus],
		PR_UINT8, vehicleData[e_vByteTimeDamageStatus],
		PR_UINT8, vehicleData[e_vByteAddSiren]);
	for(new i = 0; i < 14; i++)
	{
 		BS_ReadValue(bs, PR_UINT8, modSlots[i]);
	}
	BS_ReadValue(bs, PR_UINT8, bytePaintJob);
	BS_ReadValue(bs, PR_UINT32, color1, PR_UINT32, color2);

	if(isInvalidVehicle(vehicleData[e_vModelID]))
	{
 		new BitStream:bitstream = BS_New();

		BS_WriteValue(
  			bitstream,
     		PR_INT16, vehicleData[e_vVehicleID],
			PR_UINT32, getReplacableVehicleModel(vehicleData[e_vModelID]),
			PR_FLOAT, vehicleData[e_posX],
			PR_FLOAT, vehicleData[e_posY],
			PR_FLOAT, vehicleData[e_posZ],
			PR_FLOAT, vehicleData[e_rot],
			PR_UINT8, vehicleData[e_vColor1],
			PR_UINT8, vehicleData[e_vColor2],
			PR_FLOAT, vehicleData[e_vHealth],
			PR_UINT8, vehicleData[e_vInterior],
			PR_UINT32, vehicleData[e_vDoorDamageStatus],
			PR_UINT32, vehicleData[e_vPanelDamageStatus],
			PR_UINT8, vehicleData[e_vByteLightDamageStatus],
			PR_UINT8, vehicleData[e_vByteTimeDamageStatus],
			PR_UINT8, vehicleData[e_vByteAddSiren]);

		for(new i = 0; i < 14; i++)
		{
			BS_WriteValue(bitstream, PR_UINT8, modSlots[i]);
		}
		BS_WriteValue(bitstream, PR_UINT8, bytePaintJob);
		BS_WriteValue(bitstream, PR_UINT32, color1, PR_UINT32, color2);

		BS_RPC(bitstream, playerid, RPC_WORLDVEHICLE_ADD, PR_HIGH_PRIORITY, PR_RELIABLE_SEQUENCED);
		BS_Delete(bitstream);
		return 1;
	}
	return 0;
}
/*
stock ProcessReplaceVehicle(playerid, BitStream:bs)
{
    static clearVehicleData[E_VEHICLE_STRUCT];
	vehicleData = clearVehicleData;
	new modSlots[14];
	new bytePaintJob;
	new color1, color2;

	BS_ReadValue(
 		bs,
   		PR_INT16, vehicleData[e_vVehicleID],
		PR_UINT32, vehicleData[e_vModelID],
		PR_FLOAT, vehicleData[e_posX],
		PR_FLOAT, vehicleData[e_posY],
		PR_FLOAT, vehicleData[e_posZ],
		PR_FLOAT, vehicleData[e_rot],
		PR_UINT8, vehicleData[e_vColor1],
		PR_UINT8, vehicleData[e_vColor2],
		PR_FLOAT, vehicleData[e_vHealth],
		PR_UINT8, vehicleData[e_vInterior],
		PR_UINT32, vehicleData[e_vDoorDamageStatus],
		PR_UINT32, vehicleData[e_vPanelDamageStatus],
		PR_UINT8, vehicleData[e_vByteLightDamageStatus],
		PR_UINT8, vehicleData[e_vByteTimeDamageStatus],
		PR_UINT8, vehicleData[e_vByteAddSiren]);

	for(new i = 0; i < 14; i++)
	{
 		BS_ReadValue(bs, PR_UINT8, modSlots[i]);
	}
	BS_ReadValue(bs, PR_UINT8, bytePaintJob);
	BS_ReadValue(bs, PR_UINT32, color1, PR_UINT32, color2);

	if(isInvalidVehicle(vehicleData[e_vModelID]))
	{
		new bool: yes;
		for(new g; g < MAX_VEH_MODELS_REPLACE; g++)
		{
			if(vehicleData[e_vModelID] == customVehModels[g][0])
			{
				if(getPlayerAndroidVers(playerid) < customVehModels[g][2])
				{
					new BitStream:bitstream = BS_New();

					BS_WriteValue(
						bitstream,
						PR_INT16, vehicleData[e_vVehicleID],
						PR_UINT32, customVehModels[g][1],
						PR_FLOAT, vehicleData[e_posX],
						PR_FLOAT, vehicleData[e_posY],
						PR_FLOAT, vehicleData[e_posZ],
						PR_FLOAT, vehicleData[e_rot],
						PR_UINT8, vehicleData[e_vColor1],
						PR_UINT8, vehicleData[e_vColor2],
						PR_FLOAT, vehicleData[e_vHealth],
						PR_UINT8, vehicleData[e_vInterior],
						PR_UINT32, vehicleData[e_vDoorDamageStatus],
						PR_UINT32, vehicleData[e_vPanelDamageStatus],
						PR_UINT8, vehicleData[e_vByteLightDamageStatus],
						PR_UINT8, vehicleData[e_vByteTimeDamageStatus],
						PR_UINT8, vehicleData[e_vByteAddSiren]);

					for(new i = 0; i < 14; i++)
					{
						BS_WriteValue(bitstream, PR_UINT8, modSlots[i]);
					}
					BS_WriteValue(bitstream, PR_UINT8, bytePaintJob);
					BS_WriteValue(bitstream, PR_UINT32, color1, PR_UINT32, color2);

					BS_RPC(bitstream, playerid, RPC_WORLDVEHICLE_ADD, PR_HIGH_PRIORITY, PR_RELIABLE_SEQUENCED);
					BS_Delete(bitstream);
					yes = true;
					break;
				}
			}
		}

		if(!yes)
		{
			new BitStream:bitstream = BS_New();

			BS_WriteValue(
				bitstream,
				PR_INT16, vehicleData[e_vVehicleID],
				PR_UINT32, getReplacableVehicleModel(vehicleData[e_vModelID]),
				PR_FLOAT, vehicleData[e_posX],
				PR_FLOAT, vehicleData[e_posY],
				PR_FLOAT, vehicleData[e_posZ],
				PR_FLOAT, vehicleData[e_rot],
				PR_UINT8, vehicleData[e_vColor1],
				PR_UINT8, vehicleData[e_vColor2],
				PR_FLOAT, vehicleData[e_vHealth],
				PR_UINT8, vehicleData[e_vInterior],
				PR_UINT32, vehicleData[e_vDoorDamageStatus],
				PR_UINT32, vehicleData[e_vPanelDamageStatus],
				PR_UINT8, vehicleData[e_vByteLightDamageStatus],
				PR_UINT8, vehicleData[e_vByteTimeDamageStatus],
				PR_UINT8, vehicleData[e_vByteAddSiren]);

			for(new i = 0; i < 14; i++)
			{
				BS_WriteValue(bitstream, PR_UINT8, modSlots[i]);
			}
			BS_WriteValue(bitstream, PR_UINT8, bytePaintJob);
			BS_WriteValue(bitstream, PR_UINT32, color1, PR_UINT32, color2);

			BS_RPC(bitstream, playerid, RPC_WORLDVEHICLE_ADD, PR_HIGH_PRIORITY, PR_RELIABLE_SEQUENCED);
			BS_Delete(bitstream);
		}
		return 1;
	}
	return 0;
}
*/
stock IsShouldSendCreateObject(playerid, BitStream:bs)
{
    //new dataObject[E_OBJECT_STRUCT];
	static clearDataObject[E_OBJECT_STRUCT];
	dataObject = clearDataObject;
	BS_ReadValue(
		bs,
 		PR_INT16, dataObject[e_wObjectID],
  		PR_UINT32, dataObject[e_ModelID],
   		PR_FLOAT, dataObject[e_objectX],
    	PR_FLOAT, dataObject[e_objectY],
    	PR_FLOAT, dataObject[e_objectZ],
    	PR_FLOAT, dataObject[e_rotx],
    	PR_FLOAT, dataObject[e_roty],
    	PR_FLOAT, dataObject[e_rotz],
    	PR_FLOAT, dataObject[e_DrawDistance],
    	PR_UINT8, dataObject[e_NoCameraCol],
    	PR_UINT16, dataObject[e_attachedObject],
    	PR_UINT16, dataObject[e_attachedVehicle],
    	PR_FLOAT, dataObject[e_AttachOffsetX],
    	PR_FLOAT, dataObject[e_AttachOffsetY],
    	PR_FLOAT, dataObject[e_AttachOffsetZ],
    	PR_FLOAT, dataObject[e_AttachRotX],
    	PR_FLOAT, dataObject[e_AttachRotY],
    	PR_FLOAT, dataObject[e_AttachRotZ],
    	PR_UINT8, dataObject[e_SyncRotation]
		);

	if(isInvalidObjectModel(dataObject[e_ModelID]))
	{
	    return 0;
	}
	return 1;
}

stock IsShouldSendCreateAttached(playerid, BitStream:bs)
{
    new sPlayerID, iSlot, bCreate;
   	BS_ReadValue(
		bs,
		PR_UINT16, sPlayerID,
		PR_UINT32, iSlot,
		PR_BOOL,   bCreate);
	if(bCreate)
	{
 		new modelid;
   		BS_ReadValue(bs, PR_UINT32, modelid);
	    if(isInvalidObjectModel(modelid))
		{
			return 0;
   		}
	}
	return 1;
}

#define WEAPON_SECURE 0x100
#define WEAPON_SECURE_KEY	0x15

#if defined _inc_y_hooks || defined _INC_y_hooks
	hook OnOutcomingRPC(playerid, rpcid, BitStream:bs)
#else
	public OnOutcomingRPC(playerid, rpcid, BitStream:bs)
#endif
	{
		if(rpcid == RPC_CREATE_OBJECT)
		{
			if(isPlayerAndroid(playerid) != 0) // ���� ����� � �����
			{
				if(getPlayerAndroidVers(playerid) < server_invalid_client) // ���� � ������ ������, ������� ���� ������ ������� � ������� � ��������
				{
					if(!IsShouldSendCreateObject(playerid, bs)) // ���� ������ ����������, �� �� ��������
					{
						new _frmtsrt[50];
						format(_frmtsrt, sizeof(_frmtsrt), "[Warning] Bad object model: 32");
						SendClientMessage(playerid, 0xa9c4e4FF, _frmtsrt);
						return 0;
					}
				}
			}
			else // ����� ����� � ��
			{
			    if(!IsShouldSendCreateObject(playerid, bs)) // ���� ������ ����������, �� �� ��������
				{
					new _frmtsrt[50];
					format(_frmtsrt, sizeof(_frmtsrt), "[Warning] Bad object model: 32");
					SendClientMessage(playerid, 0xa9c4e4FF, _frmtsrt);
					return 0;
				}
			}
		}
		else if(rpcid == RPC_ScrGivePlayerWeapon) // ��������� ������
		{
		    new val1, val2;
		    BS_ReadValue(
     			bs,
       			PR_UINT32, val1,
				PR_UINT32, val2);

			new BitStream:bitstream = BS_New();
			BS_WriteValue(
  				bitstream,
	    		PR_UINT32, val1, 	//id
		    	PR_UINT32, val2,		//model
		    	PR_UINT32, WEAPON_SECURE ^ WEAPON_SECURE_KEY
			);
			BS_RPC(bitstream, playerid, RPC_ScrGivePlayerWeapon, PR_HIGH_PRIORITY, PR_RELIABLE_SEQUENCED);
			BS_Delete(bitstream);
			return 0;
		}
		else if(rpcid == RPC_ScrSetPlayerAttachedObject)
		{
		    if(isPlayerAndroid(playerid) != 0) // ���� ����� � �����
			{
				if(getPlayerAndroidVers(playerid) < server_invalid_client) // ���� � ������ ������, ������� ���� ������ ������� � ������� � ��������
				{
				    if(!IsShouldSendCreateAttached(playerid, bs)) // ���� ������ ����������, �� �� ��������
				    {
				        new _frmtsrt[50];
						format(_frmtsrt, sizeof(_frmtsrt), "[Warning] Bad object mode1: 33");
						SendClientMessage(playerid, 0xa9c4e4FF, _frmtsrt);
						return 0;
				    }
				}
			}
			else // ����� ����� � ��
			{
			    if(!IsShouldSendCreateAttached(playerid, bs)) // ���� ������ ����������, �� �� ��������
			    {
       				new _frmtsrt[50];
					format(_frmtsrt, sizeof(_frmtsrt), "[Warning] Bad object model: 33");
					SendClientMessage(playerid, 0xa9c4e4FF, _frmtsrt);
					return 0;
	    		}
			}

		}
		else if(rpcid == RPC_WorldPlayerAdd)
		{
			if(isPlayerAndroid(playerid) != 0) // ���� ����� � �����
			{
				if(getPlayerAndroidVers(playerid) < server_invalid_client) // ���� � ������ ������, ������� ���� ������ ������� � ������� � ��������
				{
					if(ProcessReplaceSkinAdd(playerid, bs)) // ���� ������ ���� �������� �������, �� ������������ ����� �� ��������
					{
					    return 0;
					}
				}
			}
			else // ����� ����� � ��
			{
				if(ProcessReplaceSkinAdd(playerid, bs)) // ���� ������ ���� �������� �������, �� ������������ ����� �� ��������
				{
    				return 0;
				}
			}
		}
		else if(rpcid == RPC_WORLDVEHICLE_ADD)
		{
			if(isPlayerAndroid(playerid) != 0) // ���� ����� � �����
			{
				if(getPlayerAndroidVers(playerid) < server_invalid_client) // ���� � ������ ������, ������� ���� ������ ������� � ������� � ��������
				{
					if(ProcessReplaceVehicle(playerid, bs)) // ���� ������ ���� �������� �������, �� ������������ ����� �� ��������
					{
					    return 0;
					}
				}
			}
			else // ����� ����� � ��
			{
				if(ProcessReplaceVehicle(playerid, bs)) // ���� ������ ���� �������� �������, �� ������������ ����� �� ��������
				{
    				return 0;
				}
			}
		}
		else if(rpcid == RPC_SET_PLAYER_SKIN)
		{
		    if(isPlayerAndroid(playerid) != 0) // ���� ����� � �����
			{
				if(getPlayerAndroidVers(playerid) < server_invalid_client) // ���� � ������ ������, ������� ���� ������ ������� � ������� � ��������
				{
					if(ProcessReplaceSkin(playerid, bs)) // ���� ������ ���� �������� �������, �� ������������ ����� �� ��������
					{
					    return 0;
					}
				}
			}
			else // ����� ����� � ��
			{
                if(ProcessReplaceSkin(playerid, bs)) // ���� ������ ���� �������� �������, �� ������������ ����� �� ��������
				{
    				return 0;
				}
			}
		}
		else if(rpcid == RPC_CREATE_PICKUP)
		{
			if(isPlayerAndroid(playerid) != 0)
			{
				if(getPlayerAndroidVers(playerid) < server_invalid_client)
				{
					new dataPickup[E_PICKUP_STRUCT];
					BS_ReadValue(
			        	bs,
			        	PR_UINT32, dataPickup[dPickupID],
			        	PR_UINT32, dataPickup[dModelID],
			        	PR_UINT32, dataPickup[dSpawnType],
			        	PR_FLOAT, dataPickup[pickupX],
			        	PR_FLOAT, dataPickup[pickupY],
			        	PR_FLOAT, dataPickup[pickupZ]
			    		);

					if(isInvalidObject(dataPickup[dModelID]) != -1)
					{
						new _frmtsrt[50];
						format(_frmtsrt, sizeof(_frmtsrt), "[Warning] Bad pickup model: %d(%d)", dataPickup[dModelID], dataPickup[dPickupID]);
						SendClientMessage(playerid, 0xa9c4e4FF, _frmtsrt);
						// ���������� ������
						new BitStream:bitstream = BS_New();
						BS_WriteValue(
					    	bitstream,
					    	PR_UINT32, dataPickup[dPickupID], 	//id
					    	PR_UINT32, PICKUP_REPLACE_MODEL,	//model
					    	PR_UINT32, dataPickup[dSpawnType],  //type.
					    	PR_FLOAT, dataPickup[pickupX], 	    //x.
					    	PR_FLOAT, dataPickup[pickupY], 		//y.
					    	PR_FLOAT, dataPickup[pickupZ] 		//z.
						);
						BS_RPC(bitstream, playerid, RPC_CREATE_PICKUP, PR_HIGH_PRIORITY, PR_RELIABLE_SEQUENCED);
						BS_Delete(bitstream);
						return 0;
					}
				}
			}
		}
		#if defined INCLUDE_OnOutcomingRPC
			return INCLUDE_OnOutcomingRPC(playerid, rpcid, BitStream:bs);
		#else
			return 1;
		#endif
	}

#if !defined _inc_y_hooks && !defined _INC_y_hooks
	#if defined _ALS_OnOutcomingRPC
		#undef OnOutcomingRPC
	#else
		#define _ALS_OnOutcomingRPC
	#endif

	#define OnOutcomingRPC INCLUDE_OnOutcomingRPC
	#if defined INCLUDE_OnOutcomingRPC
		forward INCLUDE_OnOutcomingRPC(playerid, rpcid, BitStream:bs);
	#endif
#endif
