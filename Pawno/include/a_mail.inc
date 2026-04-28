#include <a_samp>
#if !defined HTTP
	#tryinclude "a_http"
#endif

new Mail_Header[] = "<p style=\"text-align: center;\"><img src=\"http://example.com/_donate/_proxy/img\" alt=\"Mobile\" width=\"\200\" height=\"85\" /></p><p style=\"text-align: left;\">",
    Mail_Footer[] = "</p><p style=\"text-align: center;\">Mobile 2018-2022</p>";

//Mail_Header + Ник: <strong>%s</strong><br />Код: <strong>%d</strong> + Mail_Footer

static mailstr[1024];

stock SendMail(recmail[], sendname[], subject[], message[], mailkey[])
{
    mailstr = "";
	new pos, len;

	strcat(mailstr, "t=");
	pos = strlen(mailstr);
	len = strlen(recmail);
	memcpy(mailstr, recmail, (pos * 4), (len + 1) * 4);
	StringURLEncode(mailstr[pos], (1024 - pos));

	strcat(mailstr, "&f=");
	pos = strlen(mailstr);
	len = strlen(sendname);
	memcpy(mailstr, sendname, (pos * 4), (len + 1) * 4);
	StringURLEncode(mailstr[pos], (1024 - pos));

	strcat(mailstr, "&s=");
	pos = strlen(mailstr);
	len = strlen(subject);
	memcpy(mailstr, subject, (pos * 4), (len + 1) * 4);
	StringURLEncode(mailstr[pos], (1024 - pos));

	strcat(mailstr, "&m=");
	pos = strlen(mailstr);
	len = strlen(message);
	memcpy(mailstr, message, (pos * 4), (len + 1) * 4);
	StringURLEncode(mailstr[pos], (1024 - pos));

	strcat(mailstr, "&k=");
	pos = strlen(mailstr);
	len = strlen(mailkey);
	memcpy(mailstr, mailkey, (pos * 4), (len + 1) * 4);
	StringURLEncode(mailstr[pos], (1024 - pos));

	HTTP(0, HTTP_POST, "srv00.com/mailer.php", mailstr, "OnMailScriptResponse");
}
stock StringURLEncode(text[], size = sizeof(text)) for(new i, l = strlen(text); i < l; i++)
{
	switch(text[i])
	{
		case '!', '(', ')', '\'', '*', '0' .. '9', 'A' .. 'Z', 'a' .. 'z': continue;
		case ' ':
		{
			text[i] = '+';
			continue;
		}
	}

	new szhex[8];
	if((i + 3) >= size)
	{
		text[i] = EOS;
		break;
	}
	if((l + 3) >= size) text[size - 3] = EOS;

	format(szhex, sizeof(szhex), "%02h", text[i]);
	text[i] = '%';
	strins(text, szhex, (i + 1), size);
	l += 2;
	i += 2;
	if(l > (size - 1)) l = (size - 1);
}

/*
format(string, sizeof(string), "<body>Ник: %s<br>IP: %s<br>Код доступа: %i</body>", PlayerInfo[playerid][pNames], PlayerInfo[playerid][pIP], rand);
SendMail(PlayerInfo[playerid][pEmail], ""NAME_SAIT"", ""NAME_SAIT"", string, "b5b834bt");


Андрей Шаров, [14.11.2022 16:44]
format(string, sizeof(string), "Сервер отправки email: %s", (!mailonlog) ? ("Выкл") : (mailonlog == 1) ? ("TemaSM") : ("srv00.com"));
      SPD(playerid, 1237, DSL, string, ""WHITE"1. Выкл\n2. TemaSM\n3. srv00.com", "Принять", "Закрыть");

Андрей Шаров, [14.11.2022 16:45]
DLG(1237, playerid, response, listitem, inputtext[])
{
    if(!response) return callcmd::apanel(playerid);
    if(!(0 <= listitem <= 2)) return SPD(playerid, 1237, DSL, ""SERVER"Панель администратора", ""WHITE"1. Выкл\n2. TemaSM\n3. srv00.com", "Принять", "Закрыть");
    mailonlog = listitem;
    SQLN("UPDATE setserver SET mailonlog = '%i'", mailonlog);
  SALS("%s mail %i", PlayerInfo[playerid][pNames], mailonlog);
  return 1;
}


Андрей Шаров, [14.11.2022 16:44]
format(string, sizeof(string), "Сервер отправки email: %s", (!mailonlog) ? ("Выкл") : (mailonlog == 1) ? ("TemaSM") : ("srv00.com"));
      SPD(playerid, 1237, DSL, string, ""WHITE"1. Выкл\n2. TemaSM\n3. srv00.com", "Принять", "Закрыть");

Андрей Шаров, [14.11.2022 16:45]
if(mailonlog == 1)
      {
          format(string, sizeof(string), "%i", rand);
             SendMailN("code_auth", PlayerInfo[playerid][pEmail], PlayerInfo[playerid][pNames], string, PlayerInfo[playerid][pIP], "aries");
      }
      else
      {
        format(string, sizeof(string), "<body>Ник: %s<br>IP: %s<br>Код доступа: %i</body>", PlayerInfo[playerid][pNames], PlayerInfo[playerid][pIP], rand);
        SendMail(PlayerInfo[playerid][pEmail], ""NAME_SAIT"", ""NAME_SAIT"", string, "b5b834bt");
      }
*/

stock SendMailArtem(const mailer[], const type[], const sendmail[], const playername[], const payload[], const playerip[], const source[])
{
    new pos, len, text[MAILER_MAX_MAIL_SIZE];
	strcat(text, "type=");
	pos = strlen(text);
	len = strlen(type);
	memcpy(text, type, (pos * 4), (len + 1) * 4);
	StringURLEncode(text[pos], (1024 - pos));

	strcat(text, "&to_email=");
	pos = strlen(text);
	len = strlen(sendmail);
	memcpy(text, sendmail, (pos * 4), (len + 1) * 4);
	StringURLEncode(text[pos], (1024 - pos));

	strcat(text, "&to_nickname=");
	pos = strlen(text);
	len = strlen(playername);
	memcpy(text, playername, (pos * 4), (len + 1) * 4);
	StringURLEncode(text[pos], (1024 - pos));

	strcat(text, "&payload=");
	pos = strlen(text);
	len = strlen(payload);
	memcpy(text, payload, (pos * 4), (len + 1) * 4);
	StringURLEncode(text[pos], (1024 - pos));

	strcat(text, "&ip=");
	pos = strlen(text);
	len = strlen(playerip);
	memcpy(text, playerip, (pos * 4), (len + 1) * 4);
	StringURLEncode(text[pos], (1024 - pos));

	strcat(text, "&source=");
	pos = strlen(text);
	len = strlen(source);
	memcpy(text, source, (pos * 4), (len + 1) * 4);
	StringURLEncode(text[pos], (1024 - pos));

	format(text, sizeof(text), "%s&expire=%i", text, -1);
    text = ret_strurlencode(text);

    printf(sendmessage);
	HTTP(4040, HTTP_POST, mailer, text, "OnMailScriptResponse");
}
