native CreateBarrierObject(modelid, Float: PosX, Float: PosY, Float: PosZ, Float: RotX, Float: RotY, Float: RotZ, Float: DrawDistance = 0.0);
native MoveBarrierObject(objectid, Float: PosX, Float: PosY, Float: PosZ, Float: SpeedMove, Float: RotX = -1000.0, Float: RotY = -1000.0, Float: RotZ = -1000.0);
native IsPlayerToAreaBarrier(playerid, Float: radius);
native StopMovedBarrierObject(objectid);
native IsMovedBarrierObject(objectid);



/*
* CreateBarrierObject
* Создает объект предназначенный для смещения его в будущем
* Возращает ID созданного объекта
*/


/*
* MoveBarrierObject
* Функция смещает объект по опям с определенной скоростью
* Возращает 1 если функция выполнена | 0 если объект к которому обращаетесь не существует
*/


/*
* StopMovedBarrierObject
* Функция останавливает объект который смещается
* Возращает 1 если функция выполнена | 0 если объект не создан | -1 если объект не смещался
*/


/*
* IsPlayerToAreaBarrier
* Функция проверяет находится ли игрок в определенном радиусе к одному из объектов
* Возращает ID объекта если игрок в определенном радиусе от объекта и -1 если игрок не в указанном радиусе от объекта
*/

/*
* IsMovedBarrierObject
* Функция проверяет находится ли объект в смещение
* Возращает 1 если объект в движение | 0 если объект не создан | -1 если не в движение
*/